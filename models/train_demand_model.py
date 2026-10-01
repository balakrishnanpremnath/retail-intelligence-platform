from pathlib import Path
import json

import joblib
import numpy as np
import pandas as pd

from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder


# ---------------------------------------------------------
# PROJECT PATHS
# ---------------------------------------------------------

ROOT_DIR = Path(__file__).resolve().parents[1]

DATA_FILE = (
    ROOT_DIR
    / "data"
    / "processed"
    / "daily_store_product_features.csv"
)

MODEL_DIR = ROOT_DIR / "models"
MODEL_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------
# MODEL FEATURES
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

    df = df.sort_values(
        "date"
    ).reset_index(drop=True)

    return df


# ---------------------------------------------------------
# TIME-BASED TRAIN / TEST SPLIT
# ---------------------------------------------------------

def time_split(df):

    # Last 90 days are kept completely unseen
    # during model training.

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

    return (
        train,
        test,
        test_start_date
    )


# ---------------------------------------------------------
# EVALUATION
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
# BASELINE MODELS
# ---------------------------------------------------------

def evaluate_baselines(test):

    actual = test[TARGET]

    # Baseline 1:
    # assume today's demand will be
    # the same as 7 days ago

    lag_7_predictions = (
        test["lag_7_qty"]
        .clip(lower=0)
    )

    lag_7_metrics = (
        calculate_metrics(
            actual,
            lag_7_predictions
        )
    )


    # Baseline 2:
    # predict using the average demand
    # from the previous 7 days

    rolling_predictions = (
        test["rolling_7_avg"]
        .clip(lower=0)
    )

    rolling_metrics = (
        calculate_metrics(
            actual,
            rolling_predictions
        )
    )

    return {
        "Lag 7 Baseline":
            lag_7_metrics,

        "Rolling 7 Baseline":
            rolling_metrics
    }


# ---------------------------------------------------------
# BUILD RANDOM FOREST PIPELINE
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
                "passthrough",
                NUMERIC_FEATURES
            )
        ]
    )

    model = RandomForestRegressor(
        n_estimators=250,
        max_depth=18,
        min_samples_leaf=2,
        random_state=42,
        n_jobs=-1
    )

    pipeline = Pipeline(
        steps=[
            (
                "preprocessor",
                preprocessor
            ),
            (
                "model",
                model
            )
        ]
    )

    return pipeline


# ---------------------------------------------------------
# FEATURE IMPORTANCE
# ---------------------------------------------------------

def save_feature_importance(
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

    importance = pd.DataFrame({
        "feature":
            feature_names,

        "importance":
            model.feature_importances_
    })

    importance = (
        importance
        .sort_values(
            "importance",
            ascending=False
        )
        .reset_index(drop=True)
    )

    importance.to_csv(
        MODEL_DIR
        / "demand_feature_importance.csv",
        index=False
    )

    return importance


# ---------------------------------------------------------
# SAVE PREDICTIONS
# ---------------------------------------------------------

def save_predictions(
    test,
    predictions
):

    output = test[
        [
            "date",
            "store_id",
            "product_id",
            "product_name",
            "category",
            "quantity"
        ]
    ].copy()

    output[
        "predicted_quantity"
    ] = np.maximum(
        predictions,
        0
    )

    output[
        "predicted_quantity"
    ] = (
        output[
            "predicted_quantity"
        ]
        .round(2)
    )

    output[
        "absolute_error"
    ] = (
        output["quantity"]
        -
        output[
            "predicted_quantity"
        ]
    ).abs()

    output.to_csv(
        MODEL_DIR
        / "demand_test_predictions.csv",
        index=False
    )


# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------

def main():

    print(
        "Loading demand features..."
    )

    df = load_data()

    (
        train,
        test,
        test_start_date
    ) = time_split(df)


    print()
    print(
        "Time-based data split"
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
    # BASELINES
    # -----------------------------------------------------

    print()
    print(
        "Evaluating baseline models..."
    )

    baseline_results = (
        evaluate_baselines(
            test
        )
    )

    for (
        baseline_name,
        metrics
    ) in baseline_results.items():

        print(
            f"{baseline_name}"
        )

        print(
            f"  MAE  : "
            f"{metrics['MAE']:.4f}"
        )

        print(
            f"  RMSE : "
            f"{metrics['RMSE']:.4f}"
        )


    # -----------------------------------------------------
    # RANDOM FOREST
    # -----------------------------------------------------

    print()
    print(
        "Training Random Forest..."
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

    random_forest_metrics = (
        calculate_metrics(
            test[TARGET],
            predictions
        )
    )


    print()
    print(
        "Random Forest Results"
    )

    print(
        f"MAE  : "
        f"{random_forest_metrics['MAE']:.4f}"
    )

    print(
        f"RMSE : "
        f"{random_forest_metrics['RMSE']:.4f}"
    )


    # -----------------------------------------------------
    # COMPARE WITH BEST BASELINE
    # -----------------------------------------------------

    best_baseline_name = min(
        baseline_results,
        key=lambda name:
        baseline_results[
            name
        ]["MAE"]
    )

    best_baseline_metrics = (
        baseline_results[
            best_baseline_name
        ]
    )

    improvement_pct = (
        (
            best_baseline_metrics[
                "MAE"
            ]
            -
            random_forest_metrics[
                "MAE"
            ]
        )
        /
        best_baseline_metrics[
            "MAE"
        ]
        * 100
    )


    print()
    print(
        "Model Comparison"
    )

    print(
        f"Best baseline : "
        f"{best_baseline_name}"
    )

    print(
        f"Baseline MAE  : "
        f"{best_baseline_metrics['MAE']:.4f}"
    )

    print(
        f"Random Forest : "
        f"{random_forest_metrics['MAE']:.4f}"
    )

    print(
        f"MAE improvement: "
        f"{improvement_pct:.2f}%"
    )


    if (
        random_forest_metrics["MAE"]
        <
        best_baseline_metrics["MAE"]
    ):

        conclusion = (
            "Random Forest outperformed "
            "the best baseline."
        )

    else:

        conclusion = (
            "Random Forest did not outperform "
            "the best baseline."
        )

    print(
        conclusion
    )


    # -----------------------------------------------------
    # SAVE MODEL + RESULTS
    # -----------------------------------------------------

    joblib.dump(
        pipeline,
        MODEL_DIR
        / "demand_model.joblib"
    )

    save_predictions(
        test,
        predictions
    )

    feature_importance = (
        save_feature_importance(
            pipeline
        )
    )

    metrics_output = {
        "training_start":
            str(
                train[
                    "date"
                ].min().date()
            ),

        "training_end":
            str(
                train[
                    "date"
                ].max().date()
            ),

        "testing_start":
            str(
                test[
                    "date"
                ].min().date()
            ),

        "testing_end":
            str(
                test[
                    "date"
                ].max().date()
            ),

        "training_rows":
            int(len(train)),

        "testing_rows":
            int(len(test)),

        "baselines":
            baseline_results,

        "random_forest":
            random_forest_metrics,

        "best_baseline":
            best_baseline_name,

        "mae_improvement_pct":
            float(
                improvement_pct
            ),

        "conclusion":
            conclusion
    }

    with open(
        MODEL_DIR
        / "demand_metrics.json",
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            metrics_output,
            file,
            indent=4
        )


    print()
    print(
        "Top 10 Important Features"
    )

    print(
        feature_importance
        .head(10)
        .to_string(
            index=False
        )
    )


    print()
    print(
        "Model training completed."
    )

    print(
        "Saved:"
    )

    print(
        "- models/demand_model.joblib"
    )

    print(
        "- models/demand_metrics.json"
    )

    print(
        "- models/demand_feature_importance.csv"
    )

    print(
        "- models/demand_test_predictions.csv"
    )


if __name__ == "__main__":
    main()