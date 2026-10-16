
"""Rolling-origin validation of baseline and ML demand models."""

from pathlib import Path
from time import perf_counter

import numpy as np
import pandas as pd

from models.rolling_origin_cv import (
    INPUT_FILE,
    create_folds,
    calculate_metrics,
)

from models.train_demand_model import (
    FEATURES,
    TARGET,
    build_model as build_random_forest,
)

from models.train_poisson_model import (
    build_model as build_poisson,
)


ROOT = Path(__file__).resolve().parents[1]
MODEL_DIR = ROOT / "models"

RESULTS_FILE = MODEL_DIR / "rolling_cv_all_models.csv"
SUMMARY_FILE = MODEL_DIR / "rolling_cv_model_summary.csv"


def main():
    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            "Demand features missing. "
            "Run: python -m etl.build_features"
        )

    df = pd.read_csv(INPUT_FILE, parse_dates=["date"])
    df = df.sort_values("date").reset_index(drop=True)

    results = []

    for fold, train, validation in create_folds(df):
        print(f"\n{'=' * 50}", flush=True)
        print(f"FOLD {fold}", flush=True)
        print(
            f"Training: {train['date'].min().date()} "
            f"to {train['date'].max().date()}",
            flush=True,
        )
        print(
            f"Validation: {validation['date'].min().date()} "
            f"to {validation['date'].max().date()}",
            flush=True,
        )

        actual = validation[TARGET]

        methods = [
            (
                "Lag 7 Baseline",
                validation["lag_7_qty"].clip(lower=0),
            ),
            (
                "Rolling 7 Baseline",
                validation["rolling_7_avg"].clip(lower=0),
            ),
        ]

        for name, predictions in methods:
            metrics = calculate_metrics(actual, predictions)

            results.append({
                "fold": fold,
                "model": name,
                "train_rows": len(train),
                "validation_rows": len(validation),
                "MAE": metrics["MAE"],
                "RMSE": metrics["RMSE"],
            })

            print(
                f"{name}: MAE={metrics['MAE']:.4f}, "
                f"RMSE={metrics['RMSE']:.4f}",
                flush=True,
            )

        ml_models = [
            ("Poisson Regression", build_poisson()),
            ("Random Forest", build_random_forest()),
        ]

        for name, model in ml_models:
            print(f"\nTraining {name}...", flush=True)
            start = perf_counter()

            model.fit(train[FEATURES], train[TARGET])

            predictions = model.predict(validation[FEATURES])
            predictions = np.maximum(predictions, 0)

            metrics = calculate_metrics(actual, predictions)
            duration = perf_counter() - start

            results.append({
                "fold": fold,
                "model": name,
                "train_rows": len(train),
                "validation_rows": len(validation),
                "MAE": metrics["MAE"],
                "RMSE": metrics["RMSE"],
            })

            print(
                f"{name}: MAE={metrics['MAE']:.4f}, "
                f"RMSE={metrics['RMSE']:.4f}, "
                f"Time={duration:.1f}s",
                flush=True,
            )

    result_df = pd.DataFrame(results)

    summary = (
        result_df
        .groupby("model", as_index=False)
        .agg(
            folds=("fold", "nunique"),
            mean_mae=("MAE", "mean"),
            std_mae=("MAE", "std"),
            mean_rmse=("RMSE", "mean"),
        )
        .sort_values("mean_mae")
        .reset_index(drop=True)
    )

    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    result_df.to_csv(RESULTS_FILE, index=False)
    summary.to_csv(SUMMARY_FILE, index=False)

    print(f"\n{'=' * 50}")
    print("CROSS-VALIDATION MODEL COMPARISON")
    print(
        summary.round(4).to_string(index=False)
    )

    print("\nSaved:")
    print(f"- {RESULTS_FILE}")
    print(f"- {SUMMARY_FILE}")

    print("\nFinal 90-day holdout remains untouched.")


if __name__ == "__main__":
    main()
