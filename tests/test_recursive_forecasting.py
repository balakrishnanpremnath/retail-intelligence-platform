
"""Tests for recursive multi-step demand forecasting."""

import numpy as np
import pandas as pd
import pytest

from models.recursive_demand_forecast import (
    recursive_rolling7,
    forecast_from_cutoff,
)


@pytest.fixture
def sales_history():
    """Two store-product series with known daily demand."""
    dates = pd.date_range("2026-09-23", periods=8)
    rows = []

    for store, quantity in [("S001", 0), ("S002", 3)]:
        for date in dates:
            rows.append({
                "date": date,
                "store_id": store,
                "product_id": "P001",
                "product_name": "Test Rice",
                "category": "Staples",
                "quantity": quantity,
            })

    return pd.DataFrame(rows)


def test_first_day_is_last_seven_average():
    history = [1, 2, 3, 4, 5, 6, 7]

    forecast = recursive_rolling7(history, horizon=1)

    assert len(forecast) == 1
    assert forecast[0] == pytest.approx(4.0)


def test_second_day_uses_first_prediction():
    history = [1, 2, 3, 4, 5, 6, 7]

    forecast = recursive_rolling7(history, horizon=2)

    assert forecast[0] == pytest.approx(4.0)

    # Day 2 uses 2,3,4,5,6,7 and predicted Day 1 (4).
    assert forecast[1] == pytest.approx(31 / 7)


def test_only_last_seven_historical_values_matter():
    recent = [1, 2, 3, 4, 5, 6, 7]

    short = recursive_rolling7(recent, horizon=14)
    long = recursive_rolling7(
        [999, 999, 999] + recent,
        horizon=14,
    )

    assert long == pytest.approx(short)


def test_zero_demand_remains_zero():
    forecast = recursive_rolling7([0] * 7, horizon=14)

    assert len(forecast) == 14
    assert all(quantity == 0 for quantity in forecast)


@pytest.mark.parametrize(
    "invalid_history",
    [
        [1, 2, 3, 4, 5, 6, -1],
        [1, 2, 3, 4, 5, 6, np.nan],
        [1, 2, 3, 4, 5, 6, np.inf],
    ],
)
def test_rejects_invalid_demand(invalid_history):
    with pytest.raises(ValueError):
        recursive_rolling7(invalid_history)


def test_rejects_insufficient_history():
    with pytest.raises(ValueError):
        recursive_rolling7([1, 2, 3, 4, 5, 6])


def test_rejects_invalid_horizon():
    with pytest.raises(ValueError):
        recursive_rolling7([1] * 7, horizon=0)


def test_forecasts_are_independent_by_store(sales_history):
    forecast = forecast_from_cutoff(
        sales_history,
        "2026-09-30",
        horizon=14,
    )

    assert len(forecast) == 28

    store1 = forecast[forecast["store_id"] == "S001"]
    store2 = forecast[forecast["store_id"] == "S002"]

    assert (store1["forecast_quantity"] == 0).all()
    assert (store2["forecast_quantity"] == 3).all()


def test_forecast_dates_and_horizon(sales_history):
    forecast = forecast_from_cutoff(
        sales_history,
        "2026-09-30",
        horizon=14,
    )

    assert forecast["date"].min() == pd.Timestamp("2026-10-01")
    assert forecast["date"].max() == pd.Timestamp("2026-10-14")

    for _, group in forecast.groupby(["store_id", "product_id"]):
        assert group["horizon_day"].tolist() == list(range(1, 15))


def test_future_actual_sales_cannot_leak(sales_history):
    """Changing future actual sales must not alter the forecast."""

    cutoff = pd.Timestamp("2026-09-30")

    original = forecast_from_cutoff(
        sales_history,
        cutoff,
        horizon=14,
    )

    future = sales_history.copy()
    future["date"] = future["date"] + pd.Timedelta(days=8)
    future["quantity"] = 10000

    augmented = pd.concat(
        [sales_history, future],
        ignore_index=True,
    )

    updated = forecast_from_cutoff(
        augmented,
        cutoff,
        horizon=14,
    )

    pd.testing.assert_frame_equal(
        original.reset_index(drop=True),
        updated.reset_index(drop=True),
    )


def test_missing_recent_day_is_rejected(sales_history):
    incomplete = sales_history[
        ~(
            (sales_history["store_id"] == "S001")
            & (sales_history["date"] == pd.Timestamp("2026-09-28"))
        )
    ]

    with pytest.raises(ValueError, match="Incomplete recent history"):
        forecast_from_cutoff(
            incomplete,
            "2026-09-30",
            horizon=7,
        )
