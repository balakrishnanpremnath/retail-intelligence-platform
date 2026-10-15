from pathlib import Path

import numpy as np
import pandas as pd
import pytest


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "raw"

DATASETS = [
    "products",
    "stores",
    "customers",
    "sales",
    "inventory",
]


@pytest.fixture(scope="module")
def data():
    return {
        name: pd.read_csv(DATA_DIR / f"{name}.csv")
        for name in DATASETS
    }


def test_all_raw_files_exist():
    for name in DATASETS:
        assert (DATA_DIR / f"{name}.csv").is_file()


def test_primary_keys_are_unique(data):
    keys = {
        "products": "product_id",
        "stores": "store_id",
        "customers": "customer_id",
        "sales": "transaction_id",
    }

    for name, key in keys.items():
        assert data[name][key].notna().all()
        assert data[name][key].is_unique


def test_sales_foreign_keys(data):
    sales = data["sales"]

    for table, column in [
        ("products", "product_id"),
        ("stores", "store_id"),
        ("customers", "customer_id"),
    ]:
        assert sales[column].notna().all()
        assert set(sales[column]).issubset(
            set(data[table][column])
        )


def test_sales_calculations(data):
    sales = data["sales"]

    expected_revenue = (
        sales["unit_price"]
        * sales["quantity"]
        * (1 - sales["discount_pct"])
    )

    expected_cost = (
        sales["unit_cost"] * sales["quantity"]
    )

    expected_profit = (
        sales["revenue"] - sales["cost"]
    )

    assert np.allclose(
        sales["revenue"], expected_revenue, atol=0.011
    )

    assert np.allclose(
        sales["cost"], expected_cost, atol=0.011
    )

    assert np.allclose(
        sales["profit"], expected_profit, atol=0.011
    )


def test_promotion_values(data):
    sales = data["sales"]

    assert sales["promotion"].isin([0, 1]).all()
    assert sales["discount_pct"].between(0, 1).all()
    assert (sales["quantity"] > 0).all()

    non_promo = sales[sales["promotion"] == 0]
    assert (non_promo["discount_pct"] == 0).all()


def test_inventory_integrity(data):
    inventory = data["inventory"]

    assert not inventory.duplicated(
        ["store_id", "product_id"]
    ).any()

    assert (inventory["stock_on_hand"] >= 0).all()
    assert (inventory["reorder_level"] >= 0).all()

    assert set(inventory["store_id"]).issubset(
        set(data["stores"]["store_id"])
    )

    assert set(inventory["product_id"]).issubset(
        set(data["products"]["product_id"])
    )


def test_sales_dates(data):
    dates = pd.to_datetime(data["sales"]["date"])

    assert dates.notna().all()
    assert dates.between(
        "2025-01-01", "2026-09-30"
    ).all()