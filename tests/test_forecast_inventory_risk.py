
"""Unit tests for forecast-based inventory risk analysis."""

import pandas as pd
import pytest

from models.forecast_inventory_risk import analyze_inventory_risk


@pytest.fixture
def sample_inputs():
    snapshot = pd.Timestamp("2026-09-30")

    inventory = pd.DataFrame([
        {
            "store_id": "S001",
            "product_id": "P001",
            "snapshot_date": snapshot,
            "stock_on_hand": 5,
            "reorder_level": 2,
        },
        {
            "store_id": "S001",
            "product_id": "P002",
            "snapshot_date": snapshot,
            "stock_on_hand": 12,
            "reorder_level": 10,
        },
        {
            "store_id": "S002",
            "product_id": "P001",
            "snapshot_date": snapshot,
            "stock_on_hand": 50,
            "reorder_level": 10,
        },
    ])

    rows = []

    for store, product, daily_demand in [
        ("S001", "P001", 0.8),
        ("S001", "P002", 0.5),
        ("S002", "P001", 1.0),
    ]:
        for day in range(1, 15):
            rows.append({
                "as_of_date": snapshot,
                "date": snapshot + pd.Timedelta(days=day),
                "horizon_day": day,
                "store_id": store,
                "product_id": product,
                "product_name": f"Test {product}",
                "category": "Staples",
                "forecast_quantity": daily_demand,
            })

    return inventory, pd.DataFrame(rows)


def test_7_day_risk_classification(sample_inputs):
    inventory, forecasts = sample_inputs

    result = analyze_inventory_risk(
        inventory, forecasts, 7
    ).set_index(["store_id", "product_id"])

    assert len(result) == 3

    shortage = result.loc[("S001", "P001")]
    assert shortage["expected_demand"] == pytest.approx(5.6)
    assert shortage["expected_coverage_gap_units"] == 1
    assert shortage["stock_signal"] == "EXPECTED DEMAND GAP"

    reorder = result.loc[("S001", "P002")]
    assert reorder["stock_signal"] == "REORDER LEVEL RISK"

    healthy = result.loc[("S002", "P001")]
    assert healthy["stock_signal"] == "ADEQUATE BY POLICY"
    assert healthy["expected_coverage_gap_units"] == 0


def test_14_day_demand_and_shortage(sample_inputs):
    inventory, forecasts = sample_inputs

    result = analyze_inventory_risk(
        inventory, forecasts, 14
    ).set_index(["store_id", "product_id"])

    shortage = result.loc[("S001", "P001")]

    assert shortage["expected_demand"] == pytest.approx(11.2)
    assert shortage["projected_net_stock"] == pytest.approx(-6.2)
    assert shortage["expected_coverage_gap_units"] == 7
    assert (result["horizon_days"] == 14).all()


def test_original_inputs_are_not_modified(sample_inputs):
    inventory, forecasts = sample_inputs

    original_inventory = inventory.copy(deep=True)
    original_forecasts = forecasts.copy(deep=True)

    analyze_inventory_risk(inventory, forecasts, 7)

    pd.testing.assert_frame_equal(
        inventory, original_inventory
    )
    pd.testing.assert_frame_equal(
        forecasts, original_forecasts
    )


def test_mismatched_snapshot_is_rejected(sample_inputs):
    inventory, forecasts = sample_inputs

    inventory = inventory.copy()
    inventory["snapshot_date"] = "2026-09-29"

    with pytest.raises(ValueError, match="snapshot dates"):
        analyze_inventory_risk(inventory, forecasts, 7)


def test_missing_forecast_day_is_rejected(sample_inputs):
    inventory, forecasts = sample_inputs

    incomplete = forecasts[
        ~(
            (forecasts["store_id"] == "S001")
            & (forecasts["product_id"] == "P001")
            & (forecasts["horizon_day"] == 3)
        )
    ]

    with pytest.raises(ValueError, match="Incomplete"):
        analyze_inventory_risk(inventory, incomplete, 7)


def test_duplicate_forecast_day_is_rejected(sample_inputs):
    inventory, forecasts = sample_inputs

    duplicate = pd.concat(
        [forecasts, forecasts.iloc[[0]]],
        ignore_index=True,
    )

    with pytest.raises(ValueError, match="Duplicate"):
        analyze_inventory_risk(inventory, duplicate, 7)


def test_unmatched_inventory_is_rejected(sample_inputs):
    inventory, forecasts = sample_inputs

    incomplete_stock = inventory[
        inventory["store_id"] != "S002"
    ]

    with pytest.raises(ValueError, match="do not match"):
        analyze_inventory_risk(
            incomplete_stock, forecasts, 7
        )


@pytest.mark.parametrize("source", ["stock", "forecast"])
def test_negative_quantities_are_rejected(sample_inputs, source):
    inventory, forecasts = sample_inputs

    inventory = inventory.copy()
    forecasts = forecasts.copy()

    if source == "stock":
        inventory.loc[0, "stock_on_hand"] = -1
    else:
        forecasts.loc[0, "forecast_quantity"] = -1

    with pytest.raises(ValueError, match="Invalid"):
        analyze_inventory_risk(inventory, forecasts, 7)


def test_invalid_horizon_is_rejected(sample_inputs):
    inventory, forecasts = sample_inputs

    with pytest.raises(ValueError, match="Horizon"):
        analyze_inventory_risk(inventory, forecasts, 30)
