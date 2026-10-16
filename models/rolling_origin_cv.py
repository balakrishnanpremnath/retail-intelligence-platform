
"""Rolling-origin validation of historical demand baselines."""

from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]

INPUT_FILE = (
    ROOT / "data" / "processed"
    / "daily_store_product_features.csv"
)

OUTPUT_FILE = (
    ROOT / "models" / "rolling_cv_baseline_results.csv"
)

FINAL_HOLDOUT_DAYS = 90
CV_FOLDS = 3
FOLD_DAYS = 30


def create_folds(df):
    """Create expanding training and non-overlapping validation windows."""

    final_test_start = (
        df["date"].max()
        - pd.Timedelta(days=FINAL_HOLDOUT_DAYS - 1)
    )

    for fold in range(CV_FOLDS):
        validation_start = (
            final_test_start
            - pd.Timedelta(days=FOLD_DAYS * (CV_FOLDS - fold))
        )

        validation_end = (
            validation_start
            + pd.Timedelta(days=FOLD_DAYS - 1)
        )

        train = df[
            df["date"] < validation_start
        ].copy()

        validation = df[
            df["date"].between(
                validation_start,
                validation_end
            )
        ].copy()

        if train.empty or validation.empty:
            raise ValueError(
                f"Insufficient data for fold {fold + 1}"
            )

        assert train["date"].max() < validation["date"].min()
        assert validation["date"].max() < final_test_start

        yield fold + 1, train, validation


def calculate_metrics(actual, predicted):
    actual = np.asarray(actual, dtype=float)
    predicted = np.asarray(predicted, dtype=float)

    errors = actual - predicted

    return {
        "MAE": float(np.mean(np.abs(errors))),
        "RMSE": float(np.sqrt(np.mean(errors ** 2))),
    }


def main():
    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            "Processed demand features missing. "
            "Run: python -m etl.build_features"
        )

    df = pd.read_csv(INPUT_FILE, parse_dates=["date"])
    df = df.sort_values("date").reset_index(drop=True)

    results = []

    for fold, train, validation in create_folds(df):
        print(f"\nFold {fold}")
        print(
            f"Train: {train['date'].min().date()} "
            f"to {train['date'].max().date()}"
        )
        print(
            f"Validate: {validation['date'].min().date()} "
            f"to {validation['date'].max().date()}"
        )

        for model_name, feature in [
            ("Lag 7 Baseline", "lag_7_qty"),
            ("Rolling 7 Baseline", "rolling_7_avg"),
        ]:
            actual = validation["quantity"]
            predicted = validation[feature].clip(lower=0)

            metrics = calculate_metrics(actual, predicted)

            results.append({
                "fold": fold,
                "model": model_name,
                "validation_start": str(
                    validation["date"].min().date()
                ),
                "validation_end": str(
                    validation["date"].max().date()
                ),
                "rows": len(validation),
                **metrics,
            })

            print(
                f"{model_name}: "
                f"MAE={metrics['MAE']:.4f}, "
                f"RMSE={metrics['RMSE']:.4f}"
            )

    result_df = pd.DataFrame(results)

    result_df.to_csv(OUTPUT_FILE, index=False)

    print("\nAverage validation metrics:")
    print(
        result_df.groupby("model")[["MAE", "RMSE"]]
        .mean()
        .round(4)
        .to_string()
    )

    print(f"\nSaved: {OUTPUT_FILE}")
    print("Final 90-day holdout not used for validation.")


if __name__ == "__main__":
    main()
