
"""Recursive 7/14-day retail demand forecasting and backtesting."""

from pathlib import Path

import numpy as np
import pandas as pd

from models.rolling_origin_cv import (
    INPUT_FILE,
    create_folds,
)


ROOT = Path(__file__).resolve().parents[1]
MODEL_DIR = ROOT / "models"

FORECAST_FILE = MODEL_DIR / "recursive_14day_forecasts.csv"
BACKTEST_FILE = MODEL_DIR / "recursive_backtest_results.csv"


def recursive_rolling7(history, horizon=14):
    """Forecast future days using previous predictions recursively."""

    values = np.asarray(history, dtype=float)

    if len(values) < 7:
        raise ValueError("At least 7 historical days are required.")

    if not np.isfinite(values).all() or (values < 0).any():
        raise ValueError("Historical demand must be valid and nonnegative.")

    if horizon < 1:
        raise ValueError("Forecast horizon must be positive.")

    recent = values[-7:].tolist()
    forecasts = []

    for _ in range(horizon):
        prediction = max(0.0, float(np.mean(recent[-7:])))

        forecasts.append(prediction)

        # Future actual sales are unknown.
        # Add our prediction to the next day's history.
        recent.append(prediction)

    return forecasts


def forecast_from_cutoff(df, cutoff, horizon=14):
    """Make predictions using only observations on/before cutoff."""

    cutoff = pd.Timestamp(cutoff)

    history = df.loc[df["date"] <= cutoff].copy()

    expected_dates = list(
        pd.date_range(end=cutoff, periods=7)
    )

    results = []

    for (store_id, product_id), group in history.groupby(
        ["store_id", "product_id"], sort=True
    ):
        last_seven = (
            group.sort_values("date").tail(7)
        )

        if list(last_seven["date"]) != expected_dates:
            raise ValueError(
                f"Incomplete recent history: {store_id}/{product_id}"
            )

        predictions = recursive_rolling7(
            last_seven["quantity"], horizon=horizon
        )

        product = last_seven.iloc[-1]

        for day, quantity in enumerate(predictions, start=1):
            results.append({
                "as_of_date": cutoff,
                "date": cutoff + pd.Timedelta(days=day),
                "horizon_day": day,
                "store_id": store_id,
                "product_id": product_id,
                "product_name": product["product_name"],
                "category": product["category"],
                "forecast_quantity": quantity,
                "model": "Recursive Rolling-7",
            })

    return pd.DataFrame(results)


def calculate_metrics(actual, predicted):
    errors = np.asarray(actual) - np.asarray(predicted)

    return {
        "MAE": float(np.mean(np.abs(errors))),
        "RMSE": float(np.sqrt(np.mean(errors ** 2))),
        "Bias": float(np.mean(-errors)),
    }


def backtest(df):
    """Evaluate genuine multi-step forecasts before final holdout."""

    results = []

    for fold, train, validation in create_folds(df):
        cutoff = train["date"].max()

        predictions = forecast_from_cutoff(
            df, cutoff, horizon=14
        )

        actual = validation[
            ["date", "store_id", "product_id", "quantity"]
        ]

        comparison = predictions.merge(
            actual,
            on=["date", "store_id", "product_id"],
            how="left",
            validate="one_to_one",
        )

        if comparison["quantity"].isna().any():
            raise ValueError(
                f"Missing actual observations in fold {fold}"
            )

        for horizon in [7, 14]:
            subset = comparison[
                comparison["horizon_day"] <= horizon
            ]

            metrics = calculate_metrics(
                subset["quantity"],
                subset["forecast_quantity"],
            )

            results.append({
                "fold": fold,
                "cutoff_date": cutoff.date().isoformat(),
                "horizon_days": horizon,
                "observations": len(subset),
                **metrics,
            })

            print(
                f"Fold {fold} | {horizon}-day forecast | "
                f"MAE={metrics['MAE']:.4f} | "
                f"RMSE={metrics['RMSE']:.4f}"
            )

    return pd.DataFrame(results)


def main():
    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            "Missing processed demand data. "
            "Run: python -m etl.build_features"
        )

    df = pd.read_csv(INPUT_FILE, parse_dates=["date"])
    df = df.sort_values(
        ["store_id", "product_id", "date"]
    ).reset_index(drop=True)

    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    print("RECURSIVE FORECAST BACKTEST")
    print("-" * 50)

    backtest_results = backtest(df)

    backtest_results.to_csv(
        BACKTEST_FILE, index=False
    )

    print("\nAVERAGE BACKTEST PERFORMANCE")
    print(
        backtest_results.groupby("horizon_days")[
            ["MAE", "RMSE", "Bias"]
        ].mean().round(4).to_string()
    )

    latest_date = df["date"].max()

    print("\nGENERATING AS-OF-DATE FORECAST")
    print(f"Latest available sales: {latest_date.date()}")

    forecast = forecast_from_cutoff(
        df, latest_date, horizon=14
    )

    forecast["forecast_quantity"] = (
        forecast["forecast_quantity"].round(3)
    )

    forecast.to_csv(FORECAST_FILE, index=False)

    print(
        f"Forecast dates: "
        f"{forecast['date'].min().date()} to "
        f"{forecast['date'].max().date()}"
    )

    print(f"Generated rows: {len(forecast):,}")

    print("\nSaved:")
    print(f"- {BACKTEST_FILE}")
    print(f"- {FORECAST_FILE}")

    print("\nRecursive forecast experiment complete.")


if __name__ == "__main__":
    main()
