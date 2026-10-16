
"""Tests for forecast-based replenishment scenarios."""

import pandas as pd
import pytest

from models.replenishment_scenarios import (
    build_replenishment_scenarios,
)


@pytest.fixture
def sample_risk():
    rows = [
        # Expected demand exceeds stock: urgent review
        ("P001", 5, 10, 12.0),

        # Stock covers demand but is below planning target
        ("P002", 18, 20, 4.2),

        # Stock is sufficient
        ("P003", 80, 10, 2.0),

        # Zero forecast and stock below reorder level
        ("P004", 2, 8, 0.0),

        # Zero forecast and stock at reorder level
        ("P005", 10, 10, 0.0),
    ]

    data = []

    for product, stock, reorder, demand in rows:
        data.append({
            "store_id": "S001",
            "product_id": product,
            "product_name": f"Test {product}",
            "snapshot_date": "2026-09-30",
            "horizon_days": 14,
            "stock_on_hand": stock,
            "reorder_level": reorder,
            "expected_demand": demand,
        })

    # A 7-day record must not affect 14-day scenarios.
    data.append({
        "store_id": "S001",
        "product_id": "P001",
        "product_name": "Test P001",
        "snapshot_date": "2026-09-30",
        "horizon_days": 7,
        "stock_on_hand": 5,
        "reorder_level": 10,
        "expected_demand": 999.0,
    })

    return pd.DataFrame(data)


def get_product(result, product_id):
    return result.set_index("product_id").loc[product_id]


def test_action_classifications(sample_risk):
    result = build_replenishment_scenarios(sample_risk)

    assert len(result) == 5

    expected = {
        "P001": "URGENT REVIEW",
        "P002": "PLAN REPLENISHMENT",
        "P003": "MONITOR",
        "P004": "MANUAL REVIEW",
        "P005": "MONITOR",
    }

    for product, action in expected.items():
        assert get_product(
            result, product
        )["planning_action"] == action


def test_order_quantity_calculations(sample_risk):
    result = build_replenishment_scenarios(sample_risk)

    urgent = get_product(result, "P001")

    assert urgent["planning_target_units"] == 22
    assert urgent["scenario_order_units"] == 17
    assert urgent["forecast_gap_units"] == 7

    planned = get_product(result, "P002")

    assert planned["planning_target_units"] == 25
    assert planned["scenario_order_units"] == 7
    assert planned["forecast_gap_units"] == 0


def test_zero_demand_manual_review(sample_risk):
    result = build_replenishment_scenarios(sample_risk)

    review = get_product(result, "P004")

    assert review["planning_action"] == "MANUAL REVIEW"
    assert review["scenario_order_units"] == 0


def test_only_14_day_records_used(sample_risk):
    result = build_replenishment_scenarios(sample_risk)

    assert len(result) == 5
    assert (result["horizon_days"] == 14).all()

    urgent = get_product(result, "P001")
    assert urgent["expected_demand"] == 12.0


def test_input_dataframe_is_unchanged(sample_risk):
    original = sample_risk.copy(deep=True)

    build_replenishment_scenarios(sample_risk)

    pd.testing.assert_frame_equal(sample_risk, original)


def test_inconsistent_snapshot_dates_rejected(sample_risk):
    invalid = sample_risk.copy()
    invalid.loc[0, "snapshot_date"] = "2026-09-29"

    with pytest.raises(ValueError, match="snapshot dates"):
        build_replenishment_scenarios(invalid)


def test_duplicate_store_product_rejected(sample_risk):
    invalid = pd.concat(
        [sample_risk, sample_risk.iloc[[0]]],
        ignore_index=True,
    )

    with pytest.raises(ValueError, match="Duplicate"):
        build_replenishment_scenarios(invalid)


def test_no_14_day_data_rejected(sample_risk):
    invalid = sample_risk[
        sample_risk["horizon_days"] == 7
    ]

    with pytest.raises(ValueError, match="No 14-day"):
        build_replenishment_scenarios(invalid)


def test_missing_required_column_rejected(sample_risk):
    invalid = sample_risk.drop(columns="stock_on_hand")

    with pytest.raises(ValueError, match="Missing"):
        build_replenishment_scenarios(invalid)


@pytest.mark.parametrize(
    "column",
    ["stock_on_hand", "reorder_level", "expected_demand"],
)
def test_negative_values_rejected(sample_risk, column):
    invalid = sample_risk.copy()
    invalid.loc[0, column] = -1

    with pytest.raises(ValueError, match="Invalid"):
        build_replenishment_scenarios(invalid)
