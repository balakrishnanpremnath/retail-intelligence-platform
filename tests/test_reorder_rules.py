
import pandas as pd
import pytest

from models.build_reorder_recommendations import create_recommendations


@pytest.mark.parametrize(
    "stock,level,demand,cover,expected_action,expected_qty",
    [
        (4, 20, 1.0, 4.0, "URGENT", 23),
        (16, 20, 1.0, 16.0, "REORDER", 11),
        (24, 20, 0.5, 48.0, "WATCH", 0),
        (5, 20, 0.0, float("nan"), "REVIEW", 0),
        (50, 20, 0.5, 100.0, "OK", 0),
    ],
)
def test_reorder_business_rules(
    stock, level, demand, cover, expected_action, expected_qty
):
    data = pd.DataFrame({
        "stock_on_hand": [stock],
        "reorder_level": [level],
        "avg_daily_demand_30d": [demand],
        "estimated_days_cover": [cover],
    })

    result = create_recommendations(data)

    assert result.iloc[0]["inventory_action"] == expected_action
    assert result.iloc[0]["recommended_reorder_qty"] == expected_qty


def test_recommendations_do_not_modify_input():
    original = pd.DataFrame({
        "stock_on_hand": [4],
        "reorder_level": [20],
        "avg_daily_demand_30d": [1.0],
        "estimated_days_cover": [4.0],
    })

    before = original.copy(deep=True)
    create_recommendations(original)

    pd.testing.assert_frame_equal(original, before)


def test_recommendation_reasons():
    data = pd.DataFrame({
        "stock_on_hand": [4, 5],
        "reorder_level": [20, 20],
        "avg_daily_demand_30d": [1.0, 0.0],
        "estimated_days_cover": [4.0, float("nan")],
    })

    result = create_recommendations(data)

    assert "7 days or less" in result.iloc[0]["recommendation_reason"]
    assert "Manual review" in result.iloc[1]["recommendation_reason"]


def test_invalid_urgent_order_is_rejected():
    # Inconsistent source data should trigger validation.
    data = pd.DataFrame({
        "stock_on_hand": [18],
        "reorder_level": [0],
        "avg_daily_demand_30d": [0.1],
        "estimated_days_cover": [3.0],
    })

    with pytest.raises(ValueError):
        create_recommendations(data)
