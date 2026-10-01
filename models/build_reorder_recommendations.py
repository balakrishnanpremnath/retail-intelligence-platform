from pathlib import Path

import numpy as np
import pandas as pd


# ---------------------------------------------------------
# PATHS
# ---------------------------------------------------------

ROOT_DIR = Path(__file__).resolve().parents[1]

INPUT_FILE = (
    ROOT_DIR
    / "data"
    / "processed"
    / "inventory_analysis.csv"
)

OUTPUT_FILE = (
    ROOT_DIR
    / "models"
    / "reorder_recommendations.csv"
)


# ---------------------------------------------------------
# LOAD DATA
# ---------------------------------------------------------

def load_data():

    return pd.read_csv(INPUT_FILE)


# ---------------------------------------------------------
# BUILD REORDER RECOMMENDATIONS
# ---------------------------------------------------------

def create_recommendations(df):

    df = df.copy()

    # Expected demand for next 14 days
    df["forecast_14d_demand"] = (
        df["avg_daily_demand_30d"] * 14
    )

    # Extra 7 days of demand as safety stock
    df["safety_stock"] = (
        df["avg_daily_demand_30d"] * 7
    )

    # Demand-based target = 21 days of expected demand
    df["demand_based_target"] = (
        df["forecast_14d_demand"]
        + df["safety_stock"]
    )

    # Inventory policy target
    df["policy_target_stock"] = (
        df["reorder_level"]
        + df["safety_stock"]
    )

    # Final target respects both demand and reorder policy
    df["target_stock"] = np.maximum(
        df["policy_target_stock"],
        df["demand_based_target"]
    )

    # Reorder amount required to reach target stock
    df["recommended_reorder_qty"] = np.maximum(
        0,
        np.ceil(
            df["target_stock"]
            - df["stock_on_hand"]
        )
    ).astype(int)


    # -----------------------------------------------------
    # INVENTORY ACTION RULES
    # -----------------------------------------------------

    zero_demand = (
        df["avg_daily_demand_30d"] == 0
    )

    urgent = (
        (~zero_demand)
        &
        (df["estimated_days_cover"] <= 7)
    )

    reorder = (
        (~zero_demand)
        &
        (
            (
                df["stock_on_hand"]
                <= df["reorder_level"]
            )
            |
            (
                df["estimated_days_cover"]
                <= 14
            )
        )
    )

    review = (
        zero_demand
        &
        (
            df["stock_on_hand"]
            <= df["reorder_level"]
        )
    )

    watch = (
        (~zero_demand)
        &
        (
            df["stock_on_hand"]
            <= df["reorder_level"] * 1.25
        )
    )

    df["inventory_action"] = np.select(
        [
            urgent,
            reorder,
            review,
            watch
        ],
        [
            "URGENT",
            "REORDER",
            "REVIEW",
            "WATCH"
        ],
        default="OK"
    )


    # Items with no recent demand require manual review.
    # Do not automatically suggest a purchase quantity.
    df.loc[
        df["inventory_action"] == "REVIEW",
        "recommended_reorder_qty"
    ] = 0


    # -----------------------------------------------------
    # RECOMMENDATION REASON
    # -----------------------------------------------------

    def create_reason(row):

        action = row["inventory_action"]

        if action == "URGENT":
            return (
                "Estimated stock cover is "
                "7 days or less."
            )

        if action == "REORDER":
            return (
                "Recent demand and stock levels "
                "indicate replenishment is required."
            )

        if action == "REVIEW":
            return (
                "Stock is below the reorder level, "
                "but no demand was recorded in the "
                "last 30 days. Manual review is recommended."
            )

        if action == "WATCH":
            return (
                "Inventory is approaching "
                "the reorder threshold."
            )

        return (
            "Current inventory level is healthy."
        )

    df["recommendation_reason"] = df.apply(
        create_reason,
        axis=1
    )


    # -----------------------------------------------------
    # VALIDATION
    # -----------------------------------------------------

    invalid_reorders = df[
        df["inventory_action"].isin(
            ["URGENT", "REORDER"]
        )
        &
        (
            df["recommended_reorder_qty"] <= 0
        )
    ]

    if not invalid_reorders.empty:

        raise ValueError(
            "URGENT or REORDER items found "
            "with zero reorder quantity."
        )


    # -----------------------------------------------------
    # ROUND DISPLAY VALUES
    # -----------------------------------------------------

    columns_to_round = [
        "avg_daily_demand_30d",
        "forecast_14d_demand",
        "safety_stock",
        "demand_based_target",
        "policy_target_stock",
        "target_stock"
    ]

    for column in columns_to_round:

        df[column] = (
            df[column]
            .round(2)
        )

    return df


# ---------------------------------------------------------
# PRINT SUMMARY
# ---------------------------------------------------------

def print_summary(df):

    print()
    print("Inventory Action Summary")

    summary = (
        df["inventory_action"]
        .value_counts()
        .rename_axis("inventory_action")
        .reset_index(name="records")
    )

    print(
        summary.to_string(
            index=False
        )
    )

    print()
    print("Top Reorder Recommendations")

    priority_order = {
        "URGENT": 1,
        "REORDER": 2,
        "REVIEW": 3,
        "WATCH": 4,
        "OK": 5
    }

    display = df.copy()

    display["priority"] = (
        display["inventory_action"]
        .map(priority_order)
    )

    display = (
        display
        .sort_values(
            [
                "priority",
                "recommended_reorder_qty"
            ],
            ascending=[
                True,
                False
            ]
        )
        .head(15)
    )

    columns = [
        "store_name",
        "product_name",
        "stock_on_hand",
        "reorder_level",
        "avg_daily_demand_30d",
        "estimated_days_cover",
        "recommended_reorder_qty",
        "inventory_action"
    ]

    print(
        display[columns]
        .to_string(
            index=False
        )
    )


# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------

def main():

    print(
        "Loading inventory features..."
    )

    inventory = load_data()

    recommendations = (
        create_recommendations(
            inventory
        )
    )

    recommendations.to_csv(
        OUTPUT_FILE,
        index=False
    )

    print_summary(
        recommendations
    )

    print()
    print(
        "Reorder recommendations created."
    )

    print(
        "Saved:"
    )

    print(
        "- models/reorder_recommendations.csv"
    )


if __name__ == "__main__":
    main()