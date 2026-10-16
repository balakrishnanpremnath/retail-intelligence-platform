
import pandas as pd
import pytest

from etl.build_features import (
    create_demand_features,
    create_customer_rfm,
    create_inventory_features,
)


@pytest.fixture
def demand_data():
    dates = pd.date_range("2026-01-01", periods=21)
    rows = []

    for store_id, start_qty in [("S1", 1), ("S2", 101)]:
        for i, date in enumerate(dates):
            # S1 has no transaction on day 6.
            if store_id == "S1" and i == 5:
                continue

            quantity = start_qty + i
            rows.append({
                "date": date,
                "store_id": store_id,
                "product_id": "P1",
                "quantity": quantity,
                "revenue": quantity * 100,
                "profit": quantity * 20,
                "discount_pct": 0.0,
                "promotion": 0,
            })

    sales = pd.DataFrame(rows)

    products = pd.DataFrame([{
        "product_id": "P1",
        "product_name": "Test Product",
        "category": "Grocery",
    }])

    stores = pd.DataFrame({
        "store_id": ["S1", "S2"],
    })

    return sales, products, stores


def get_row(df, store, date):
    return df.loc[
        (df["store_id"] == store)
        & (df["date"] == pd.Timestamp(date))
    ].iloc[0]


def test_historical_lags_and_rolling_averages(demand_data):
    features = create_demand_features(*demand_data)
    row = get_row(features, "S1", "2026-01-21")

    assert row["quantity"] == 21
    assert row["lag_1_qty"] == 20
    assert row["lag_7_qty"] == 14
    assert row["lag_14_qty"] == 7
    assert row["rolling_7_avg"] == pytest.approx(17.0)
    assert row["rolling_28_avg"] == pytest.approx(10.2)


def test_missing_sales_day_becomes_zero(demand_data):
    features = create_demand_features(*demand_data)

    # January 20's 14-day lag points to January 6,
    # when store S1 had no sale.
    row = get_row(features, "S1", "2026-01-20")

    assert row["lag_14_qty"] == 0


def test_store_history_is_not_mixed(demand_data):
    features = create_demand_features(*demand_data)
    row = get_row(features, "S2", "2026-01-21")

    assert row["quantity"] == 121
    assert row["lag_1_qty"] == 120
    assert row["rolling_7_avg"] == pytest.approx(117.0)


def test_current_target_does_not_change_history(demand_data):
    sales, products, stores = demand_data

    original = create_demand_features(
        sales, products, stores
    )

    changed_sales = sales.copy()
    mask = (
        (changed_sales["store_id"] == "S1")
        & (changed_sales["date"] == pd.Timestamp("2026-01-21"))
    )
    changed_sales.loc[mask, "quantity"] += 1000

    updated = create_demand_features(
        changed_sales, products, stores
    )

    before = get_row(original, "S1", "2026-01-21")
    after = get_row(updated, "S1", "2026-01-21")

    assert after["quantity"] == before["quantity"] + 1000

    history_columns = [
        "lag_1_qty",
        "lag_7_qty",
        "lag_14_qty",
        "rolling_7_avg",
        "rolling_28_avg",
    ]

    for column in history_columns:
        assert after[column] == pytest.approx(before[column])


def test_customer_rfm_calculations():
    sales = pd.DataFrame({
        "customer_id": ["C1", "C1", "C2"],
        "transaction_id": ["T1", "T2", "T3"],
        "date": pd.to_datetime([
            "2026-01-02",
            "2026-01-05",
            "2026-01-01",
        ]),
        "revenue": [100.0, 60.0, 30.0],
    })

    result = create_customer_rfm(sales).set_index("customer_id")

    assert result.loc["C1", "recency"] == 1
    assert result.loc["C1", "frequency"] == 2
    assert result.loc["C1", "monetary"] == pytest.approx(160.0)

    assert result.loc["C2", "recency"] == 5
    assert result.loc["C2", "frequency"] == 1
    assert result.loc["C2", "monetary"] == pytest.approx(30.0)


def test_customer_frequency_counts_unique_transactions():
    sales = pd.DataFrame({
        "customer_id": ["C1", "C1", "C1"],
        "transaction_id": ["T1", "T1", "T2"],
        "date": pd.to_datetime([
            "2026-01-02",
            "2026-01-02",
            "2026-01-05",
        ]),
        "revenue": [100.0, 50.0, 60.0],
    })

    result = create_customer_rfm(sales)

    assert result.iloc[0]["frequency"] == 2
    assert result.iloc[0]["monetary"] == pytest.approx(210.0)


def test_inventory_uses_recent_30_day_demand():
    sales = pd.DataFrame({
        "date": pd.to_datetime([
            "2026-01-01",
            "2026-01-31",
            "2026-02-01",
        ]),
        "store_id": ["S1", "S1", "S1"],
        "product_id": ["P1", "P1", "P1"],
        "quantity": [90, 30, 30],
    })

    inventory = pd.DataFrame({
        "store_id": ["S1", "S1"],
        "product_id": ["P1", "P2"],
        "stock_on_hand": [8, 40],
        "reorder_level": [10, 10],
    })

    products = pd.DataFrame({
        "product_id": ["P1", "P2"],
        "product_name": ["Product 1", "Product 2"],
        "category": ["Grocery", "Grocery"],
    })

    stores = pd.DataFrame({
        "store_id": ["S1"],
        "store_name": ["Test Store"],
        "region": ["Western"],
    })

    result = create_inventory_features(
        inventory, sales, products, stores
    ).set_index("product_id")

    # January 1 must be excluded from the last 30 days.
    assert result.loc["P1", "units_last_30_days"] == 60
    assert result.loc["P1", "avg_daily_demand_30d"] == 2
    assert result.loc["P1", "estimated_days_cover"] == 4
    assert result.loc["P1", "stock_status"] == "REORDER"

    assert result.loc["P2", "units_last_30_days"] == 0
    assert pd.isna(result.loc["P2", "estimated_days_cover"])
