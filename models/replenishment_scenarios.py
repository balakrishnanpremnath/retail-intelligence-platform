
"""Forecast-based replenishment planning scenarios.

Uses saved 14-day demand forecasts and inventory snapshots.
These are illustrative planning quantities, not purchase orders.
"""

from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "models/forecast_inventory_risk.csv"
OUTPUT = ROOT / "models/replenishment_scenarios.csv"


def build_replenishment_scenarios(risk):
    required = {
        "store_id", "product_id", "product_name",
        "snapshot_date", "horizon_days",
        "stock_on_hand", "reorder_level",
        "expected_demand",
    }

    if not required.issubset(risk.columns):
        raise ValueError("Missing required inventory columns")

    df = risk.loc[risk["horizon_days"] == 14].copy()

    if df.empty:
        raise ValueError("No 14-day inventory records")

    if df.duplicated(["store_id", "product_id"]).any():
        raise ValueError("Duplicate store-product records")

    dates = pd.to_datetime(df["snapshot_date"])

    if dates.isna().any() or dates.nunique() != 1:
        raise ValueError("Inconsistent inventory snapshot dates")

    numeric = [
        "stock_on_hand",
        "reorder_level",
        "expected_demand",
    ]

    for column in numeric:
        df[column] = pd.to_numeric(
            df[column], errors="raise"
        )

    if (
        not np.isfinite(df[numeric].to_numpy()).all()
        or (df[numeric] < 0).any().any()
    ):
        raise ValueError("Invalid stock or demand values")

    df["planning_target_units"] = np.ceil(
        df["expected_demand"] + df["reorder_level"]
    ).astype(int)

    df["scenario_order_units"] = np.maximum(
        0,
        df["planning_target_units"] - df["stock_on_hand"]
    ).astype(int)

    df["forecast_gap_units"] = np.ceil(
        np.maximum(
            0,
            df["expected_demand"] - df["stock_on_hand"],
        )
    ).astype(int)

    no_demand_review = (
        (df["expected_demand"] == 0)
        & (df["stock_on_hand"] < df["reorder_level"])
    )

    # Do not automatically suggest buying products
    # with zero expected demand.
    df.loc[
        no_demand_review, "scenario_order_units"
    ] = 0

    df["planning_action"] = np.select(
        [
            no_demand_review,
            df["forecast_gap_units"] > 0,
            df["scenario_order_units"] > 0,
        ],
        [
            "MANUAL REVIEW",
            "URGENT REVIEW",
            "PLAN REPLENISHMENT",
        ],
        default="MONITOR",
    )

    reasons = {
        "URGENT REVIEW":
            "Expected demand exceeds current stock.",
        "PLAN REPLENISHMENT":
            "Additional stock may be needed to maintain "
            "the planning target.",
        "MANUAL REVIEW":
            "Stock is below policy level, but forecast "
            "demand is zero.",
        "MONITOR":
            "Current stock covers the planning target.",
    }

    df["planning_reason"] = (
        df["planning_action"].map(reasons)
    )

    priority = {
        "URGENT REVIEW": 0,
        "MANUAL REVIEW": 1,
        "PLAN REPLENISHMENT": 2,
        "MONITOR": 3,
    }

    df["priority"] = df["planning_action"].map(priority)

    return (
        df.sort_values(
            ["priority", "scenario_order_units"],
            ascending=[True, False],
        )
        .drop(columns="priority")
        .reset_index(drop=True)
    )


def main():
    risk = pd.read_csv(INPUT)

    plan = build_replenishment_scenarios(risk)

    plan.to_csv(OUTPUT, index=False)

    print("\nFORECAST-BASED REPLENISHMENT SCENARIOS")
    print("-" * 50)

    print(
        plan["planning_action"]
        .value_counts()
        .to_string()
    )

    print("\nTotal scenario units:",
          int(plan["scenario_order_units"].sum()))

    print("\nTop 10 planning priorities:")

    print(
        plan[[
            "store_id",
            "product_name",
            "stock_on_hand",
            "expected_demand",
            "scenario_order_units",
            "planning_action",
        ]]
        .head(10)
        .to_string(index=False)
    )

    print(f"\nSaved: {OUTPUT}")
    print(f"Records: {len(plan)}")
    print(
        "\nSimulation only: no supplier lead times, "
        "incoming deliveries, or purchasing costs."
    )


if __name__ == "__main__":
    main()
