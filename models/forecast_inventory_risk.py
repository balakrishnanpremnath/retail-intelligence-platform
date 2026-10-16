
"""Compare saved demand forecasts with the matching inventory snapshot."""

from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]

INVENTORY_FILE = ROOT / "data/raw/inventory.csv"
FORECAST_FILE = ROOT / "models/recursive_poisson_14day_forecasts.csv"
OUTPUT_FILE = ROOT / "models/forecast_inventory_risk.csv"


def analyze_inventory_risk(inventory, forecasts, horizon):
    """Estimate stock coverage as of a historical forecast cutoff."""

    if horizon not in (7, 14):
        raise ValueError("Horizon must be 7 or 14 days")

    stock = inventory.copy()
    fc = forecasts.copy()

    stock["snapshot_date"] = pd.to_datetime(
        stock["snapshot_date"]
    )
    fc["as_of_date"] = pd.to_datetime(fc["as_of_date"])
    fc["date"] = pd.to_datetime(fc["date"])

    for column in ["stock_on_hand", "reorder_level"]:
        stock[column] = pd.to_numeric(stock[column], errors="raise")

    fc["forecast_quantity"] = pd.to_numeric(
        fc["forecast_quantity"], errors="raise"
    )
    fc["horizon_day"] = pd.to_numeric(
        fc["horizon_day"], errors="raise"
    )

    if stock.empty or fc.empty:
        raise ValueError("Inventory and forecast data cannot be empty")

    if (
        stock["snapshot_date"].nunique() != 1
        or fc["as_of_date"].nunique() != 1
        or stock["snapshot_date"].iloc[0] != fc["as_of_date"].iloc[0]
    ):
        raise ValueError("Inventory and forecast snapshot dates differ")

    if (
        not np.isfinite(
            stock[["stock_on_hand", "reorder_level"]].to_numpy()
        ).all()
        or (stock[["stock_on_hand", "reorder_level"]] < 0).any().any()
        or not np.isfinite(fc["forecast_quantity"]).all()
        or (fc["forecast_quantity"] < 0).any()
    ):
        raise ValueError("Invalid inventory or forecast quantities")

    expected_dates = (
        fc["as_of_date"]
        + pd.to_timedelta(fc["horizon_day"], unit="D")
    )

    if not fc["date"].eq(expected_dates).all():
        raise ValueError("Forecast dates do not match horizon days")

    if stock.duplicated(["store_id", "product_id"]).any():
        raise ValueError("Duplicate inventory records")

    fc = fc[
        (fc["horizon_day"] >= 1)
        & (fc["horizon_day"] <= horizon)
    ].copy()

    if fc.duplicated(
        ["store_id", "product_id", "horizon_day"]
    ).any():
        raise ValueError("Duplicate forecast days")

    coverage = fc.groupby(
        ["store_id", "product_id"]
    )["horizon_day"].agg(["count", "min", "max"])

    if not (
        (coverage["count"] == horizon)
        & (coverage["min"] == 1)
        & (coverage["max"] == horizon)
    ).all():
        raise ValueError("Incomplete forecast horizon")

    demand = (
        fc.groupby(
            ["store_id", "product_id", "product_name", "category"],
            as_index=False
        )["forecast_quantity"]
        .sum()
        .rename(columns={"forecast_quantity": "expected_demand"})
    )

    risk = stock.merge(
        demand,
        on=["store_id", "product_id"],
        how="outer",
        validate="one_to_one",
        indicator=True,
    )

    if not risk["_merge"].eq("both").all():
        raise ValueError("Inventory and forecast products do not match")

    risk = risk.drop(columns="_merge")

    risk["horizon_days"] = horizon

    # Negative net stock represents expected unmet demand,
    # not physically negative inventory.
    risk["projected_net_stock"] = (
        risk["stock_on_hand"] - risk["expected_demand"]
    )

    risk["expected_coverage_gap_units"] = np.ceil(
        np.maximum(0, -risk["projected_net_stock"])
    ).astype(int)

    risk["stock_signal"] = np.select(
        [
            risk["projected_net_stock"] < 0,
            risk["projected_net_stock"] <= risk["reorder_level"],
        ],
        [
            "EXPECTED DEMAND GAP",
            "REORDER LEVEL RISK",
        ],
        default="ADEQUATE BY POLICY",
    )

    return risk.sort_values(
        ["stock_signal", "store_id", "product_id"]
    ).reset_index(drop=True)


def main():
    inventory = pd.read_csv(INVENTORY_FILE)
    forecasts = pd.read_csv(FORECAST_FILE)

    reports = []

    for horizon in (7, 14):
        report = analyze_inventory_risk(
            inventory, forecasts, horizon
        )
        reports.append(report)

        print(f"\n{horizon}-DAY INVENTORY RISK")
        print("-" * 45)

        print(
            report["stock_signal"]
            .value_counts()
            .to_string()
        )

        print(
            f"\nTotal expected demand: "
            f"{report['expected_demand'].sum():.2f} units"
        )

        print(
            f"Potential coverage gap: "
            f"{report['expected_coverage_gap_units'].sum():,} "
            f"rounded units across store-products"
        )

    combined = pd.concat(reports, ignore_index=True)
    combined.to_csv(OUTPUT_FILE, index=False)

    print(f"\nSaved: {OUTPUT_FILE}")
    print(f"Records: {len(combined):,}")
    print(
        "Analysis uses the historical inventory snapshot. "
        "It does not include replenishments or supplier lead times."
    )


if __name__ == "__main__":
    main()
