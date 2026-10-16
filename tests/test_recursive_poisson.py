
"""Tests for recursive Poisson-style multi-step forecasting."""

import numpy as np
import pandas as pd
import pytest

from models.recursive_poisson_forecast import forecast_poisson


class IncrementModel:
    """Simple test model: predicts previous demand plus one."""

    def __init__(self):
        self.calls = []

    def predict(self, features):
        self.calls.append(features.copy())
        return features["lag_1_qty"].to_numpy() + 1


@pytest.fixture
def demand_history():
    dates = pd.date_range("2026-09-03", periods=28)
    rows = []

    for store_id, quantity in [("S001", 1), ("S002", 4)]:
        for date in dates:
            rows.append({
                "date": date,
                "store_id": store_id,
                "product_id": "P001",
                "product_name": "Test Product",
                "category": "Staples",
                "quantity": quantity,
            })

    return pd.DataFrame(rows)


def test_uses_previous_predictions_for_future_lags(demand_history):
    model = IncrementModel()

    forecast = forecast_poisson(
        model, demand_history, "2026-09-30", horizon=15
    )

    s1 = forecast[
        forecast["store_id"] == "S001"
    ].sort_values("horizon_day")

    assert s1["forecast_quantity"].tolist() == pytest.approx(
        list(range(2, 17))
    )

    # Day 8's lag-7 must be predicted Day 1.
    assert model.calls[7].iloc[0]["lag_7_qty"] == pytest.approx(2)

    # Day 15's lag-14 must also be predicted Day 1.
    assert model.calls[14].iloc[0]["lag_14_qty"] == pytest.approx(2)

    # Day 8 uses predicted Days 1-7: 2,3,4,5,6,7,8.
    assert model.calls[7].iloc[0]["rolling_7_avg"] == pytest.approx(5)


def test_store_histories_are_independent(demand_history):
    original = forecast_poisson(
        IncrementModel(), demand_history, "2026-09-30"
    )

    changed = demand_history.copy()
    changed.loc[
        changed["store_id"] == "S002", "quantity"
    ] = 1000

    updated = forecast_poisson(
        IncrementModel(), changed, "2026-09-30"
    )

    original_s1 = original.loc[
        original["store_id"] == "S001", "forecast_quantity"
    ].reset_index(drop=True)

    updated_s1 = updated.loc[
        updated["store_id"] == "S001", "forecast_quantity"
    ].reset_index(drop=True)

    pd.testing.assert_series_equal(original_s1, updated_s1)


def test_future_actuals_cannot_change_predictions(demand_history):
    original = forecast_poisson(
        IncrementModel(), demand_history, "2026-09-30"
    )

    future = demand_history.copy()
    future["date"] += pd.Timedelta(days=28)
    future["quantity"] = 9999

    extended = pd.concat(
        [demand_history, future], ignore_index=True
    )

    updated = forecast_poisson(
        IncrementModel(), extended, "2026-09-30"
    )

    pd.testing.assert_frame_equal(original, updated)


def test_negative_predictions_are_clipped(demand_history):
    class NegativeModel:
        def predict(self, features):
            return np.full(len(features), -10.0)

    forecast = forecast_poisson(
        NegativeModel(), demand_history, "2026-09-30", horizon=3
    )

    assert (forecast["forecast_quantity"] == 0).all()


def test_invalid_model_output_is_rejected(demand_history):
    class InvalidModel:
        def predict(self, features):
            return np.full(len(features), np.nan)

    with pytest.raises(ValueError, match="invalid predictions"):
        forecast_poisson(
            InvalidModel(), demand_history, "2026-09-30"
        )


def test_missing_history_is_rejected(demand_history):
    incomplete = demand_history[
        ~(
            (demand_history["store_id"] == "S001")
            & (
                demand_history["date"]
                == pd.Timestamp("2026-09-27")
            )
        )
    ]

    with pytest.raises(ValueError, match="Incomplete 28-day"):
        forecast_poisson(
            IncrementModel(), incomplete, "2026-09-30"
        )


@pytest.mark.parametrize("horizon", [0, -1])
def test_invalid_horizon_is_rejected(demand_history, horizon):
    with pytest.raises(ValueError):
        forecast_poisson(
            IncrementModel(),
            demand_history,
            "2026-09-30",
            horizon=horizon,
        )
