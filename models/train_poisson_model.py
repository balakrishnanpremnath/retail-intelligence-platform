from pathlib import Path
import json

import joblib
import numpy as np
import pandas as pd

from sklearn.compose import ColumnTransformer
from sklearn.linear_model import PoissonRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


# ---------------------------------------------------------
# PATHS
# ---------------------------------------------------------

ROOT_DIR = Path(__file__).resolve().parents[1]

DATA_FILE = (
    ROOT_DIR
    / "data"
    / "processed"
    / "daily_store_product_features.csv"
)

MODEL_DIR = ROOT_DIR / "models"

RF_METRICS_FILE = (
    MODEL_DIR
    / "demand_metrics.json"
)


# ---------------------------------------------------------
# FEATURES
# ---------------------------------------------------------

CATEGORICAL_FEATURES = [
    "store_id",
    "product_id",
    "category"
]

NUMERIC_FEATURES = [
    "day_of_week",
    "month",
    "quarter",
    "year",
    "is_weekend",
    "lag_1_qty",
    "lag_7_qty",
    "lag_14_qty",
    "rolling_7_avg",
    "rolling_28_avg"
]

FEATURES = (
    CATEGORICAL_FEATURES
    + NUMERIC_FEATURES
)

TARGET = "quantity"


# ---------------------------------------------------------
# LOAD DATA
# ---------------------------------------------------------

def load_data():

    df = pd.read_csv(
        DATA_FILE,
        parse_dates=["date"]
    )

    return (
        df
        .sort_values("date")
        .reset_index(drop=True)
    )


# ---------------------------------------------------------
# TIME-BASED SPLIT
# ---------------------------------------------------------

def time_split(df):

    max_date = df["date"].max()

    test_start_date = (
        max_date
        - pd.Timedelta(days=89)
    )

    train = df[
        df["date"] < test_start_date
    ].copy()

    test = df[
        df["date"] >= test_start_date
    ].copy()

    return train, test


# ---------------------------------------------------------
# METRICS
# ---------------------------------------------------------

def calculate_metrics(
    actual,
    predicted
):

    mae = mean_absolute_error(
        actual,
        predicted
    )

    rmse = np.sqrt(
        mean_squared_error(
            actual,
            predicted
        )
    )

    return {
        "MAE": float(mae),
        "RMSE": float(rmse)
    }


# ---------------------------------------------------------
# BASELINE
# ---------------------------------------------------------

def evaluate_rolling_baseline(test):

    predictions = (
        test["rolling_7_avg"]
        .clip(lower=0)
    )

    return calculate_metrics(
        test[TARGET],
        predictions
    )


# ---------------------------------------------------------
# BUILD POISSON MODEL
# ---------------------------------------------------------

def build_model():

    preprocessor = ColumnTransformer(
        transformers=[

            (
                "categorical",
                OneHotEncoder(
                    handle_unknown="ignore"
                ),
                CATEGORICAL_FEATURES
            ),

            (
                "numeric",
                StandardScaler(),
                NUMERIC_FEATURES
            )
        ]
    )

    poisson = PoissonRegressor(
        alpha=0.1,
        max_iter=1000
    )

    pipeline = Pipeline(
        steps=[
            (
                "preprocessor",
                preprocessor
            ),
            (
                "model",
                poisson
            )
        ]
    )

    return pipeline


# ---------------------------------------------------------
# SAVE COEFFICIENTS
# ---------------------------------------------------------

def save_coefficients(
    pipeline
):

    preprocessor = (
        pipeline
        .named_steps[
            "preprocessor"
        ]
    )

    model = (
        pipeline
        .named_steps[
            "model"
        ]
    )

    feature_names = (
        preprocessor
        .get_feature_names_out()
    )

    coefficient_df = pd.DataFrame({
        "feature":
            feature_names,

        "coefficient":
            model.coef_
    })

    coefficient_df[
        "absolute_coefficient"
    ] = (
        coefficient_df[
            "coefficient"
        ].abs()
    )

    coefficient_df = (
        coefficient_df
        .sort_values(
            "absolute_coefficient",
            ascending=False
        )
        .reset_index(drop=True)
    )

    coefficient_df.to_csv(
        MODEL_DIR
        / "poisson_coefficients.csv",
        index=False
    )

    return coefficient_df


# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------

def main():

    print(
        "Loading demand features..."
    )

    df = load_data()

    train, test = time_split(df)

    print()
    print(
        "Time-based split"
    )

    print(
        f"Training period : "
        f"{train['date'].min().date()} "
        f"to "
        f"{train['date'].max().date()}"
    )

    print(
        f"Testing period  : "
        f"{test['date'].min().date()} "
        f"to "
        f"{test['date'].max().date()}"
    )

    print(
        f"Training rows   : "
        f"{len(train):,}"
    )

    print(
        f"Testing rows    : "
        f"{len(test):,}"
    )


    # -----------------------------------------------------
    # BASELINE
    # -----------------------------------------------------

    baseline_metrics = (
        evaluate_rolling_baseline(
            test
        )
    )

    print()
    print(
        "Rolling 7 Baseline"
    )

    print(
        f"MAE  : "
        f"{baseline_metrics['MAE']:.4f}"
    )

    print(
        f"RMSE : "
        f"{baseline_metrics['RMSE']:.4f}"
    )


    # -----------------------------------------------------
    # TRAIN POISSON
    # -----------------------------------------------------

    print()
    print(
        "Training Poisson Regression..."
    )

    pipeline = build_model()

    pipeline.fit(
        train[FEATURES],
        train[TARGET]
    )

    predictions = (
        pipeline.predict(
            test[FEATURES]
        )
    )

    predictions = np.maximum(
        predictions,
        0
    )

    poisson_metrics = (
        calculate_metrics(
            test[TARGET],
            predictions
        )
    )

    print()
    print(
        "Poisson Regression Results"
    )

    print(
        f"MAE  : "
        f"{poisson_metrics['MAE']:.4f}"
    )

    print(
        f"RMSE : "
        f"{poisson_metrics['RMSE']:.4f}"
    )


    # -----------------------------------------------------
    # COMPARE WITH BASELINE
    # -----------------------------------------------------

    improvement_pct = (
        (
            baseline_metrics["MAE"]
            -
            poisson_metrics["MAE"]
        )
        /
        baseline_metrics["MAE"]
        * 100
    )

    print()
    print(
        "Comparison with Rolling 7 Baseline"
    )

    print(
        f"Baseline MAE : "
        f"{baseline_metrics['MAE']:.4f}"
    )

    print(
        f"Poisson MAE  : "
        f"{poisson_metrics['MAE']:.4f}"
    )

    print(
        f"MAE improvement: "
        f"{improvement_pct:.2f}%"
    )


    # -----------------------------------------------------
    # RANDOM FOREST RESULT
    # -----------------------------------------------------

    random_forest_metrics = None

    if RF_METRICS_FILE.exists():

        with open(
            RF_METRICS_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            rf_results = json.load(
                file
            )

        random_forest_metrics = (
            rf_results[
                "random_forest"
            ]
        )


    # -----------------------------------------------------
    # LEADERBOARD
    # -----------------------------------------------------

    leaderboard = [
        {
            "Model":
                "Rolling 7 Baseline",

            "MAE":
                baseline_metrics[
                    "MAE"
                ],

            "RMSE":
                baseline_metrics[
                    "RMSE"
                ]
        },

        {
            "Model":
                "Poisson Regression",

            "MAE":
                poisson_metrics[
                    "MAE"
                ],

            "RMSE":
                poisson_metrics[
                    "RMSE"
                ]
        }
    ]

    if random_forest_metrics:

        leaderboard.append({
            "Model":
                "Random Forest",

            "MAE":
                random_forest_metrics[
                    "MAE"
                ],

            "RMSE":
                random_forest_metrics[
                    "RMSE"
                ]
        })


    leaderboard_df = pd.DataFrame(
        leaderboard
    )

    leaderboard_df = (
        leaderboard_df
        .sort_values(
            "MAE"
        )
        .reset_index(drop=True)
    )

    leaderboard_df[
        "Rank"
    ] = (
        leaderboard_df.index + 1
    )

    leaderboard_df = (
        leaderboard_df[
            [
                "Rank",
                "Model",
                "MAE",
                "RMSE"
            ]
        ]
    )

    print()
    print(
        "Model Leaderboard"
    )

    print(
        leaderboard_df.to_string(
            index=False
        )
    )


    # -----------------------------------------------------
    # SAVE OUTPUTS
    # -----------------------------------------------------

    joblib.dump(
        pipeline,
        MODEL_DIR
        / "poisson_demand_model.joblib"
    )

    coefficient_df = (
        save_coefficients(
            pipeline
        )
    )

    results = {
        "rolling_7_baseline":
            baseline_metrics,

        "poisson_regression":
            poisson_metrics,

        "mae_improvement_vs_baseline_pct":
            float(
                improvement_pct
            ),

        "best_model_by_mae":
            leaderboard_df.iloc[0][
                "Model"
            ]
    }

    with open(
        MODEL_DIR
        / "poisson_metrics.json",
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            results,
            file,
            indent=4
        )


    leaderboard_df.to_csv(
        MODEL_DIR
        / "model_leaderboard.csv",
        index=False
    )


    print()
    print(
        "Top Poisson Coefficients"
    )

    print(
        coefficient_df
        .head(10)
        [
            [
                "feature",
                "coefficient"
            ]
        ]
        .to_string(
            index=False
        )
    )


    print()
    print(
        "Experiment completed."
    )

    print(
        "Saved:"
    )

    print(
        "- models/poisson_metrics.json"
    )

    print(
        "- models/model_leaderboard.csv"
    )

    print(
        "- models/poisson_coefficients.csv"
    )

    print(
        "- models/poisson_demand_model.joblib"
    )


if __name__ == "__main__":
    main()