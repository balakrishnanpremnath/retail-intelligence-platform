
"""Evaluate Poisson Regression in genuine recursive 7/14-day forecasting."""

from pathlib import Path

import numpy as np
import pandas as pd

from models.compare_multistep_baselines import make_baselines
from models.rolling_origin_cv import INPUT_FILE, create_folds
from models.recursive_demand_forecast import calculate_metrics
from models.train_poisson_model import FEATURES, TARGET, build_model


ROOT = Path(__file__).resolve().parents[1]
MODEL_DIR = ROOT / "models"

RESULTS_FILE = MODEL_DIR / "recursive_poisson_cv_results.csv"
SUMMARY_FILE = MODEL_DIR / "recursive_poisson_cv_summary.csv"
FORECAST_FILE = MODEL_DIR / "recursive_poisson_14day_forecasts.csv"


def forecast_poisson(model, data, cutoff, horizon=14):
    """Predict forward using only history and earlier predictions."""

    if not isinstance(horizon, int) or horizon < 1:
        raise ValueError("horizon must be a positive integer")

    cutoff = pd.Timestamp(cutoff)
    past = data.loc[data["date"] <= cutoff].copy()
    expected_dates = list(pd.date_range(end=cutoff, periods=28))

    series_info = []
    histories = []

    for (store, product), group in past.groupby(
        ["store_id", "product_id"], sort=True
    ):
        recent = group.sort_values("date").tail(28)

        if recent["date"].tolist() != expected_dates:
            raise ValueError(
                f"Incomplete 28-day history: {store}/{product}"
            )

        quantities = recent["quantity"].to_numpy(dtype=float)

        if not np.isfinite(quantities).all() or (quantities < 0).any():
            raise ValueError(
                f"Invalid demand history: {store}/{product}"
            )

        latest = recent.iloc[-1]

        series_info.append({
            "store_id": store,
            "product_id": product,
            "product_name": latest["product_name"],
            "category": latest["category"],
        })

        histories.append(quantities.tolist())

    if not series_info:
        raise ValueError("No historical store-product series found")

    forecast_rows = []

    for step in range(1, horizon + 1):
        target_date = cutoff + pd.Timedelta(days=step)
        feature_rows = []

        for info, history in zip(series_info, histories):
            feature_rows.append({
                "store_id": info["store_id"],
                "product_id": info["product_id"],
                "category": info["category"],
                "day_of_week": target_date.dayofweek,
                "month": target_date.month,
                "quarter": target_date.quarter,
                "year": target_date.year,
                "is_weekend": int(target_date.dayofweek >= 5),
                "lag_1_qty": history[-1],
                "lag_7_qty": history[-7],
                "lag_14_qty": history[-14],
                "rolling_7_avg": float(np.mean(history[-7:])),
                "rolling_28_avg": float(np.mean(history[-28:])),
            })

        feature_table = pd.DataFrame(feature_rows)

        prediction = np.asarray(
            model.predict(feature_table[FEATURES]),
            dtype=float,
        )

        if (
            len(prediction) != len(series_info)
            or not np.isfinite(prediction).all()
        ):
            raise ValueError("Model produced invalid predictions")

        prediction = np.maximum(prediction, 0.0)

        for i, (info, amount) in enumerate(
            zip(series_info, prediction)
        ):
            amount = float(amount)

            # Update history with predicted, not actual, demand.
            histories[i].append(amount)

            forecast_rows.append({
                "as_of_date": cutoff,
                "date": target_date,
                "horizon_day": step,
                **info,
                "forecast_quantity": amount,
                "model": "Recursive Poisson",
            })

    return pd.DataFrame(forecast_rows)


def main():
    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            "Missing processed demand features"
        )

    df = pd.read_csv(INPUT_FILE, parse_dates=["date"])
    df = df.sort_values("date").reset_index(drop=True)

    results = []

    for fold, train, validation in create_folds(df):
        cutoff = train["date"].max()

        # Train only on data before this validation fold.
        model = build_model()
        model.fit(train[FEATURES], train[TARGET])

        methods = make_baselines(df, cutoff)
        methods["Recursive Poisson"] = forecast_poisson(
            model, df, cutoff, horizon=14
        )

        actual = validation[
            ["date", "store_id", "product_id", "quantity"]
        ]

        print(
            f"\nFold {fold} | as of {cutoff.date()}",
            flush=True,
        )

        for name, forecast in methods.items():
            comparison = forecast.merge(
                actual,
                on=["date", "store_id", "product_id"],
                how="left",
                validate="one_to_one",
            )

            if comparison["quantity"].isna().any():
                raise ValueError(
                    f"Missing actual demand for {name}"
                )

            for days in (7, 14):
                sample = comparison[
                    comparison["horizon_day"] <= days
                ]

                metrics = calculate_metrics(
                    sample["quantity"],
                    sample["forecast_quantity"],
                )

                actual_total = sample["quantity"].sum()
                predicted_total = sample[
                    "forecast_quantity"
                ].sum()

                results.append({
                    "fold": fold,
                    "method": name,
                    "horizon_days": days,
                    "observations": len(sample),
                    **metrics,
                    "volume_ratio": (
                        predicted_total / actual_total
                        if actual_total > 0
                        else float("nan")
                    ),
                })

                print(
                    f"{name:22s} | {days:2d} days | "
                    f"MAE={metrics['MAE']:.4f} "
                    f"RMSE={metrics['RMSE']:.4f}",
                    flush=True,
                )

    results_df = pd.DataFrame(results)

    summary = (
        results_df.groupby(
            ["horizon_days", "method"], as_index=False
        )
        .agg(
            mean_mae=("MAE", "mean"),
            mean_rmse=("RMSE", "mean"),
            mean_bias=("Bias", "mean"),
            mean_volume_ratio=("volume_ratio", "mean"),
        )
        .sort_values(["horizon_days", "mean_rmse"])
    )

    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    results_df.to_csv(RESULTS_FILE, index=False)
    summary.to_csv(SUMMARY_FILE, index=False)

    # Latest forecast: use all observed data through Sep 30.
    latest_model = build_model()
    latest_model.fit(df[FEATURES], df[TARGET])

    as_of = df["date"].max()

    latest = forecast_poisson(
        latest_model, df, as_of, horizon=14
    )

    latest["forecast_quantity"] = (
        latest["forecast_quantity"].round(3)
    )

    latest.to_csv(FORECAST_FILE, index=False)

    print("\nMEAN MULTI-STEP BACKTEST RESULTS")
    print(summary.round(4).to_string(index=False))

    print(
        f"\nForecast as of {as_of.date()}: "
        f"{len(latest):,} rows"
    )

    print(
        f"Forecast period: "
        f"{latest['date'].min().date()} to "
        f"{latest['date'].max().date()}"
    )

    print(
        "Backtests excluded the final 90-day holdout."
    )
    print(
        "Latest forecast model fitted on all observed history."
    )

    print("\nSaved:")
    print(f"- {RESULTS_FILE}")
    print(f"- {SUMMARY_FILE}")
    print(f"- {FORECAST_FILE}")


if __name__ == "__main__":
    main()
