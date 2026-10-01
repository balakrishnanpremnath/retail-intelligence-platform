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

    df = pd.read_csv(
        INPUT_FILE
    )

    return df


# ---------------------------------------------------------
# REORDER LOGIC
# ---------------------------------------------------------

def create_recommendations(df):

    df = df.copy()

    # Expected demand for the next 14 days
    df["forecast_14d_demand"] = (
        df["avg_daily_demand_30d"] * 14
    )

    # Extra 7 days as safety stock
    df["safety_stock"] = (
        df["avg_daily_demand_30d"] * 7
    )

    # Demand-based requirement = 21 days of stock
    df["demand_based_target"] = (
        df["forecast_14d_demand"]
        + df["safety_stock"]
    )

    # Final target must respect both:
    # 1. historical demand
    # 2. existing reorder policy
    df["target_stock"] = np.maximum(
        df["reorder_level"],
        df["demand_based_target"]
    )

    # Recommended quantity
    df["recommended_reorder_qty"] = np.maximum(
        0,
        np.ceil(
            df["target_stock"]
            - df["stock_on_hand"]
        )
    ).astype(int)


    # ---------------------------------------------
    # INVENTORY ACTION
    # ---------------------------------------------

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
                df["estimated_days_cover"] <= 14
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


    # Don't automatically reorder items
    # with no recent demand.
    df.loc[
        df["inventory_action"] == "REVIEW",
        "recommended_reorder_qty"
    ] = 0


    # ---------------------------------------------
    # BUSINESS EXPLANATION
    # ---------------------------------------------

    def create_reason(row):

        if row["inventory_action"] == "URGENT":
            return (
                "Estimated stock cover is "
                "7 days or less."
            )

        if row["inventory_action"] == "REORDER":
            return (
                "Recent demand indicates that "
                "inventory replenishment is required."
            )

        if row["inventory_action"] == "REVIEW":
            return (
                "Stock is below the reorder level, "
                "but no demand was recorded in the "
                "last 30 days. Manual review is recommended."
            )

        if row["inventory_action"] == "WATCH":
            return (
                "Inventory is approaching the "
                "reorder threshold."
            )

        return (
            "Current inventory level is healthy."
        )


    df["recommendation_reason"] = (
        df.apply(
            create_reason,
            axis=1
        )
    )


    # ---------------------------------------------
    # ROUND DISPLAY VALUES
    # ---------------------------------------------

    columns_to_round = [
        "avg_daily_demand_30d",
        "forecast_14d_demand",
        "safety_stock",
        "demand_based_target",
        "target_stock"
    ]

    for column in columns_to_round:

        df[column] = (
            df[column]
            .round(2)
        )

    return df


    # -----------------------------------------------------
    # INVENTORY RISK
    # -----------------------------------------------------

    conditions = [

        # Less than or equal to 7 days cover
        (
            df[
                "estimated_days_cover"
            ] <= 7
        ),

        # Below reorder level
        (
            df[
                "stock_on_hand"
            ]
            <=
            df[
                "reorder_level"
            ]
        ),

        # 8-14 days cover
        (
            df[
                "estimated_days_cover"
            ] <= 14
        ),

        # Slightly above reorder level
        (
            df[
                "stock_on_hand"
            ]
            <=
            df[
                "reorder_level"
            ] * 1.25
        )
    ]


    choices = [
        "URGENT",
        "REORDER",
        "WATCH",
        "WATCH"
    ]


    df[
        "inventory_action"
    ] = np.select(
        conditions,
        choices,
        default="OK"
    )


    # -----------------------------------------------------
    # HUMAN-READABLE REASON
    # -----------------------------------------------------

    def create_reason(row):

        if row[
            "inventory_action"
        ] == "URGENT":

            return (
                "Estimated stock cover is "
                "7 days or less."
            )

        if row[
            "inventory_action"
        ] == "REORDER":

            return (
                "Stock is at or below "
                "the reorder level."
            )

        if row[
            "inventory_action"
        ] == "WATCH":

            return (
                "Stock level should be "
                "monitored closely."
            )

        return (
            "Current stock level is healthy."
        )


    df[
        "recommendation_reason"
    ] = df.apply(
        create_reason,
        axis=1
    )


    # -----------------------------------------------------
    # ROUND DISPLAY VALUES
    # -----------------------------------------------------

    df[
        "avg_daily_demand_30d"
    ] = (
        df[
            "avg_daily_demand_30d"
        ]
        .round(2)
    )

    df[
        "forecast_14d_demand"
    ] = (
        df[
            "forecast_14d_demand"
        ]
        .round(2)
    )

    df[
        "safety_stock"
    ] = (
        df[
            "safety_stock"
        ]
        .round(2)
    )

    df[
        "target_stock"
    ] = (
        df[
            "target_stock"
        ]
        .round(2)
    )

    return df


# ---------------------------------------------------------
# SUMMARY
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