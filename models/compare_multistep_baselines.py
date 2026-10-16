
"""Compare genuine multi-step demand forecasting baselines."""

from pathlib import Path

import pandas as pd

from models.rolling_origin_cv import INPUT_FILE, create_folds
from models.recursive_demand_forecast import (
    forecast_from_cutoff,
    calculate_metrics,
)


ROOT = Path(__file__).resolve().parents[1]
RESULT_FILE = ROOT / "models" / "multistep_baseline_comparison.csv"
SUMMARY_FILE = ROOT / "models" / "multistep_baseline_summary.csv"


def make_baselines(df, cutoff):
    """Use only demand observed through the forecast cutoff."""

    rolling = forecast_from_cutoff(df, cutoff, horizon=14)

    history = df[df["date"] <= cutoff]

    patterns = {
        key: group.sort_values("date").tail(7)[
            "quantity"
        ].to_numpy()
        for key, group in history.groupby(
            ["store_id", "product_id"]
        )
    }

    seasonal = rolling.copy()
    seasonal["forecast_quantity"] = [
        float(patterns[(store, product)][(int(day) - 1) % 7])
        for store, product, day in zip(
            rolling["store_id"],
            rolling["product_id"],
            rolling["horizon_day"],
        )
    ]

    zero = rolling.copy()
    zero["forecast_quantity"] = 0.0

    return {
        "Recursive Rolling-7": rolling,
        "Seasonal Naive-7": seasonal,
        "Zero Forecast": zero,
    }


def main():
    df = pd.read_csv(INPUT_FILE, parse_dates=["date"])
    df = df.sort_values("date").reset_index(drop=True)

    results = []

    for fold, train, validation in create_folds(df):
        cutoff = train["date"].max()

        print(f"\nFOLD {fold} | Cutoff: {cutoff.date()}")

        baselines = make_baselines(df, cutoff)

        actual = validation[
            ["date", "store_id", "product_id", "quantity"]
        ]

        for name, forecast in baselines.items():
            comparison = forecast.merge(
                actual,
                on=["date", "store_id", "product_id"],
                how="left",
                validate="one_to_one",
            )

            if comparison["quantity"].isna().any():
                raise ValueError(
                    f"Missing validation actuals: {name}"
                )

            for horizon in (7, 14):
                subset = comparison[
                    comparison["horizon_day"] <= horizon
                ]

                metrics = calculate_metrics(
                    subset["quantity"],
                    subset["forecast_quantity"],
                )

                actual_total = subset["quantity"].sum()
                predicted_total = subset[
                    "forecast_quantity"
                ].sum()

                volume_ratio = (
                    predicted_total / actual_total
                    if actual_total > 0
                    else float("nan")
                )

                results.append({
                    "fold": fold,
                    "method": name,
                    "horizon_days": horizon,
                    "observations": len(subset),
                    **metrics,
                    "volume_ratio": volume_ratio,
                })

                print(
                    f"{name:22} | {horizon:2} days | "
                    f"MAE={metrics['MAE']:.4f} | "
                    f"RMSE={metrics['RMSE']:.4f} | "
                    f"Bias={metrics['Bias']:+.4f}"
                )

    result_df = pd.DataFrame(results)

    summary = (
        result_df.groupby(
            ["horizon_days", "method"], as_index=False
        )
        .agg(
            mean_mae=("MAE", "mean"),
            mean_rmse=("RMSE", "mean"),
            mean_bias=("Bias", "mean"),
            mean_volume_ratio=("volume_ratio", "mean"),
        )
        .sort_values(["horizon_days", "mean_mae"])
    )

    result_df.to_csv(RESULT_FILE, index=False)
    summary.to_csv(SUMMARY_FILE, index=False)

    print("\n" + "=" * 60)
    print("MULTI-STEP FORECAST COMPARISON")
    print(summary.round(4).to_string(index=False))

    print("\nVolume ratio:")
    print("1.0 = predicted total equals actual total")
    print("Below 1.0 = underforecasting total demand")
    print("Above 1.0 = overforecasting total demand")
    print("\nFinal 90-day holdout remains untouched.")


if __name__ == "__main__":
    main()
