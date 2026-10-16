
"""Tests for multi-step baseline forecasting comparison."""

import numpy as np
import pandas as pd
import pytest

from models.compare_multistep_baselines import make_baselines
from models.recursive_demand_forecast import calculate_metrics


@pytest.fixture
def history():
    dates = pd.date_range("2026-09-21", periods=10)
    rows = []

    for store_id, quantities in [
        ("S001", list(range(1, 11))),
        ("S002", [2] * 10),
    ]:
        for date, quantity in zip(dates, quantities):
            rows.append({
                "date": date,
                "store_id": store_id,
                "product_id": "P001",
                "product_name": "Test Product",
                "category": "Staples",
                "quantity": quantity,
            })

    return pd.DataFrame(rows)


def test_returns_all_three_baselines(history):
    results = make_baselines(history, "2026-09-30")

    assert set(results) == {
        "Recursive Rolling-7",
        "Seasonal Naive-7",
        "Zero Forecast",
    }


def test_each_method_produces_14_days_per_store(history):
    results = make_baselines(history, "2026-09-30")

    for forecast in results.values():
        assert len(forecast) == 28
        assert forecast["date"].min() == pd.Timestamp("2026-10-01")
        assert forecast["date"].max() == pd.Timestamp("2026-10-14")
        assert not forecast.duplicated(
            ["date", "store_id", "product_id"]
        ).any()


def test_zero_baseline_predicts_zero(history):
    results = make_baselines(history, "2026-09-30")

    forecast = results["Zero Forecast"]

    assert (forecast["forecast_quantity"] == 0).all()


def test_seasonal_baseline_repeats_last_week(history):
    results = make_baselines(history, "2026-09-30")

    forecast = results["Seasonal Naive-7"]

    store = forecast[
        forecast["store_id"] == "S001"
    ].sort_values("horizon_day")

    expected = [4, 5, 6, 7, 8, 9, 10] * 2

    assert store["forecast_quantity"].tolist() == expected


def test_recursive_baseline_uses_mean(history):
    results = make_baselines(history, "2026-09-30")

    forecast = results["Recursive Rolling-7"]

    first_day = forecast[
        (forecast["store_id"] == "S001")
        & (forecast["horizon_day"] == 1)
    ]

    assert first_day.iloc[0]["forecast_quantity"] == pytest.approx(7.0)


def test_future_actual_sales_do_not_affect_forecasts(history):
    cutoff = "2026-09-30"

    original = make_baselines(history, cutoff)

    future = history.copy()
    future["date"] += pd.Timedelta(days=10)
    future["quantity"] = 999

    augmented = pd.concat(
        [history, future],
        ignore_index=True,
    )

    updated = make_baselines(augmented, cutoff)

    for method in original:
        pd.testing.assert_frame_equal(
            original[method].reset_index(drop=True),
            updated[method].reset_index(drop=True),
        )


def test_signed_bias_identifies_underprediction():
    actual = np.array([0, 2])
    predicted = np.array([0, 0])

    metrics = calculate_metrics(actual, predicted)

    assert metrics["MAE"] == pytest.approx(1.0)
    assert metrics["RMSE"] == pytest.approx(np.sqrt(2))
    assert metrics["Bias"] == pytest.approx(-1.0)
