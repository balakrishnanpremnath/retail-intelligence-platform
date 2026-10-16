
"""Analyze rolling-origin forecast errors by store and product."""

from pathlib import Path

import numpy as np
import pandas as pd

from models.rolling_origin_cv import (
    INPUT_FILE,
    create_folds,
)
from models.train_poisson_model import (
    FEATURES,
    TARGET,
    build_model,
)


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "models"
PROCESSED_DIR = ROOT / "data" / "processed"


def summarize_errors(df, group_columns):
    summary = (
        df.groupby(["model"] + group_columns, as_index=False)
        .agg(
            observations=("absolute_error", "size"),
            MAE=("absolute_error", "mean"),
            Bias=("signed_error", "mean"),
            MSE=("squared_error", "mean"),
        )
    )

    summary["RMSE"] = np.sqrt(summary["MSE"])
    return summary.drop(columns="MSE")


def main():
    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            "Run feature engineering before error analysis."
        )

    df = pd.read_csv(INPUT_FILE, parse_dates=["date"])
    df = df.sort_values("date").reset_index(drop=True)

    predictions = []

    for fold, train, validation in create_folds(df):
        print(f"Evaluating validation fold {fold}...")

        poisson = build_model()
        poisson.fit(train[FEATURES], train[TARGET])

        forecasts = {
            "Rolling 7 Baseline":
                validation["rolling_7_avg"].to_numpy(),
            "Poisson Regression":
                poisson.predict(validation[FEATURES]),
        }

        for name, predicted in forecasts.items():
            result = validation[
                [
                    "date",
                    "store_id",
                    "product_id",
                    "product_name",
                    "category",
                    "quantity",
                ]
            ].copy()

            result["fold"] = fold
            result["model"] = name
            result["predicted_qty"] = np.maximum(predicted, 0)

            result["signed_error"] = (
                result["predicted_qty"] - result["quantity"]
            )
            result["absolute_error"] = result["signed_error"].abs()
            result["squared_error"] = result["signed_error"] ** 2

            result["demand_type"] = np.where(
                result["quantity"] == 0,
                "Zero Sales",
                "Positive Sales",
            )

            predictions.append(result)

    all_predictions = pd.concat(
        predictions, ignore_index=True
    )

    by_store = summarize_errors(
        all_predictions, ["store_id"]
    ).sort_values(["model", "MAE"], ascending=[True, False])

    by_product = summarize_errors(
        all_predictions,
        ["product_id", "product_name", "category"]
    ).sort_values(["model", "MAE"], ascending=[True, False])

    by_demand = summarize_errors(
        all_predictions, ["demand_type"]
    ).sort_values(["model", "demand_type"])

    overall = summarize_errors(all_predictions, [])

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    # Detailed predictions remain local.
    all_predictions.to_csv(
        PROCESSED_DIR / "cv_error_predictions.csv",
        index=False,
    )

    # Aggregated reports can be version controlled.
    by_store.to_csv(
        OUTPUT_DIR / "cv_error_by_store.csv", index=False
    )
    by_product.to_csv(
        OUTPUT_DIR / "cv_error_by_product.csv", index=False
    )
    by_demand.to_csv(
        OUTPUT_DIR / "cv_error_by_demand.csv", index=False
    )

    print("\nOVERALL PERFORMANCE")
    print(overall.round(4).to_string(index=False))

    print("\nERROR BY STORE")
    print(by_store.round(4).to_string(index=False))

    print("\nERROR BY DEMAND TYPE")
    print(by_demand.round(4).to_string(index=False))

    print("\nTOP 10 DIFFICULT PRODUCTS - ROLLING 7")
    difficult = by_product[
        by_product["model"] == "Rolling 7 Baseline"
    ].head(10)

    print(
        difficult[
            ["product_name", "category", "MAE", "Bias"]
        ].round(4).to_string(index=False)
    )

    print("\nForecast error analysis completed.")
    print("Final 90-day holdout was not evaluated.")


if __name__ == "__main__":
    main()
