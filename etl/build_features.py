from pathlib import Path

import numpy as np
import pandas as pd


# ---------------------------------------------------------
# PROJECT PATHS
# ---------------------------------------------------------

ROOT_DIR = Path(__file__).resolve().parents[1]

RAW_DIR = ROOT_DIR / "data" / "raw"
PROCESSED_DIR = ROOT_DIR / "data" / "processed"

PROCESSED_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------
# LOAD RAW DATA
# ---------------------------------------------------------

def load_data():

    sales = pd.read_csv(
        RAW_DIR / "sales.csv",
        parse_dates=["date"]
    )

    products = pd.read_csv(
        RAW_DIR / "products.csv"
    )

    stores = pd.read_csv(
        RAW_DIR / "stores.csv"
    )

    customers = pd.read_csv(
        RAW_DIR / "customers.csv",
        parse_dates=["join_date"]
    )

    inventory = pd.read_csv(
        RAW_DIR / "inventory.csv",
        parse_dates=["snapshot_date"]
    )

    return (
        sales,
        products,
        stores,
        customers,
        inventory
    )


# ---------------------------------------------------------
# 1. ENRICH SALES DATA
# ---------------------------------------------------------

def create_enriched_sales(
    sales,
    products,
    stores,
    customers
):

    enriched = (
        sales
        .merge(
            products[
                [
                    "product_id",
                    "product_name",
                    "category"
                ]
            ],
            on="product_id",
            how="left"
        )
        .merge(
            stores[
                [
                    "store_id",
                    "store_name",
                    "region"
                ]
            ],
            on="store_id",
            how="left"
        )
        .merge(
            customers[
                [
                    "customer_id",
                    "customer_type"
                ]
            ],
            on="customer_id",
            how="left"
        )
    )

    enriched["year"] = (
        enriched["date"].dt.year
    )

    enriched["month"] = (
        enriched["date"].dt.month
    )

    enriched["day_of_week"] = (
        enriched["date"].dt.dayofweek
    )

    enriched["is_weekend"] = (
        enriched["day_of_week"] >= 5
    ).astype(int)

    return enriched


# ---------------------------------------------------------
# 2. DAILY PRODUCT-STORE DEMAND FEATURES
# ---------------------------------------------------------

def create_demand_features(
    enriched_sales,
    products,
    stores
):

    daily_sales = (
        enriched_sales
        .groupby(
            [
                "date",
                "store_id",
                "product_id"
            ],
            as_index=False
        )
        .agg(
            quantity=("quantity", "sum"),
            revenue=("revenue", "sum"),
            profit=("profit", "sum"),
            avg_discount=("discount_pct", "mean"),
            promotion_rate=("promotion", "mean")
        )
    )

    # -----------------------------------------------------
    # Create every date × store × product combination
    # Missing sales days become quantity = 0
    # -----------------------------------------------------

    all_dates = pd.DataFrame({
        "date": pd.date_range(
            enriched_sales["date"].min(),
            enriched_sales["date"].max(),
            freq="D"
        )
    })

    all_dates["key"] = 1

    store_ids = stores[
        ["store_id"]
    ].copy()

    store_ids["key"] = 1

    product_info = products[
        [
            "product_id",
            "product_name",
            "category"
        ]
    ].copy()

    product_info["key"] = 1

    full_grid = (
        all_dates
        .merge(
            store_ids,
            on="key"
        )
        .merge(
            product_info,
            on="key"
        )
        .drop(
            columns="key"
        )
    )

    demand = (
        full_grid
        .merge(
            daily_sales,
            on=[
                "date",
                "store_id",
                "product_id"
            ],
            how="left"
        )
    )

    # Zero means no units sold on that date
    demand["quantity"] = (
        demand["quantity"]
        .fillna(0)
        .astype(int)
    )

    demand["revenue"] = (
        demand["revenue"]
        .fillna(0)
    )

    demand["profit"] = (
        demand["profit"]
        .fillna(0)
    )

    demand["avg_discount"] = (
        demand["avg_discount"]
        .fillna(0)
    )

    demand["promotion_rate"] = (
        demand["promotion_rate"]
        .fillna(0)
    )

    demand = demand.sort_values(
        [
            "store_id",
            "product_id",
            "date"
        ]
    ).reset_index(drop=True)


    # -----------------------------------------------------
    # TIME FEATURES
    # -----------------------------------------------------

    demand["day_of_week"] = (
        demand["date"].dt.dayofweek
    )

    demand["month"] = (
        demand["date"].dt.month
    )

    demand["quarter"] = (
        demand["date"].dt.quarter
    )

    demand["year"] = (
        demand["date"].dt.year
    )

    demand["is_weekend"] = (
        demand["day_of_week"] >= 5
    ).astype(int)


    # -----------------------------------------------------
    # HISTORICAL LAG FEATURES
    # -----------------------------------------------------

    group_columns = [
        "store_id",
        "product_id"
    ]

    demand["lag_1_qty"] = (
        demand
        .groupby(group_columns)["quantity"]
        .shift(1)
    )

    demand["lag_7_qty"] = (
        demand
        .groupby(group_columns)["quantity"]
        .shift(7)
    )

    demand["lag_14_qty"] = (
        demand
        .groupby(group_columns)["quantity"]
        .shift(14)
    )


    # -----------------------------------------------------
    # ROLLING DEMAND FEATURES
    # shift(1) avoids using today's target
    # -----------------------------------------------------

    demand["rolling_7_avg"] = (
        demand
        .groupby(group_columns)["quantity"]
        .transform(
            lambda x:
            x.shift(1)
            .rolling(
                window=7,
                min_periods=1
            )
            .mean()
        )
    )

    demand["rolling_28_avg"] = (
        demand
        .groupby(group_columns)["quantity"]
        .transform(
            lambda x:
            x.shift(1)
            .rolling(
                window=28,
                min_periods=1
            )
            .mean()
        )
    )


    # First 14 days do not have enough lag history
    demand = (
        demand
        .dropna()
        .reset_index(drop=True)
    )

    return demand


# ---------------------------------------------------------
# 3. CUSTOMER RFM FEATURES
# ---------------------------------------------------------

def create_customer_rfm(
    enriched_sales
):

    reference_date = (
        enriched_sales["date"].max()
        + pd.Timedelta(days=1)
    )

    customer_rfm = (
        enriched_sales
        .groupby(
            "customer_id",
            as_index=False
        )
        .agg(
            last_purchase=(
                "date",
                "max"
            ),

            frequency=(
                "transaction_id",
                "nunique"
            ),

            monetary=(
                "revenue",
                "sum"
            )
        )
    )

    customer_rfm["recency"] = (
        reference_date
        - customer_rfm["last_purchase"]
    ).dt.days

    customer_rfm["monetary"] = (
        customer_rfm["monetary"]
        .round(2)
    )

    return customer_rfm


# ---------------------------------------------------------
# 4. INVENTORY INTELLIGENCE FEATURES
# ---------------------------------------------------------

def create_inventory_features(
    inventory,
    enriched_sales,
    products,
    stores
):

    max_date = (
        enriched_sales["date"].max()
    )

    start_date = (
        max_date
        - pd.Timedelta(days=29)
    )

    recent_sales = enriched_sales[
        enriched_sales["date"] >= start_date
    ]

    recent_demand = (
        recent_sales
        .groupby(
            [
                "store_id",
                "product_id"
            ],
            as_index=False
        )
        .agg(
            units_last_30_days=(
                "quantity",
                "sum"
            )
        )
    )

    recent_demand[
        "avg_daily_demand_30d"
    ] = (
        recent_demand[
            "units_last_30_days"
        ] / 30
    )

    inventory_analysis = (
        inventory
        .merge(
            products[
                [
                    "product_id",
                    "product_name",
                    "category"
                ]
            ],
            on="product_id",
            how="left"
        )
        .merge(
            stores[
                [
                    "store_id",
                    "store_name",
                    "region"
                ]
            ],
            on="store_id",
            how="left"
        )
        .merge(
            recent_demand,
            on=[
                "store_id",
                "product_id"
            ],
            how="left"
        )
    )

    inventory_analysis[
        "units_last_30_days"
    ] = (
        inventory_analysis[
            "units_last_30_days"
        ]
        .fillna(0)
    )

    inventory_analysis[
        "avg_daily_demand_30d"
    ] = (
        inventory_analysis[
            "avg_daily_demand_30d"
        ]
        .fillna(0)
    )

    inventory_analysis[
        "estimated_days_cover"
    ] = np.where(

        inventory_analysis[
            "avg_daily_demand_30d"
        ] > 0,

        inventory_analysis[
            "stock_on_hand"
        ]
        /
        inventory_analysis[
            "avg_daily_demand_30d"
        ],

        np.nan
    )

    inventory_analysis[
        "estimated_days_cover"
    ] = (
        inventory_analysis[
            "estimated_days_cover"
        ]
        .round(1)
    )


    # Current rule-based inventory status
    inventory_analysis[
        "stock_status"
    ] = np.select(

        [
            inventory_analysis[
                "stock_on_hand"
            ]
            <=
            inventory_analysis[
                "reorder_level"
            ],

            inventory_analysis[
                "stock_on_hand"
            ]
            <=
            inventory_analysis[
                "reorder_level"
            ] * 1.25
        ],

        [
            "REORDER",
            "LOW STOCK"
        ],

        default="OK"
    )

    return inventory_analysis


# ---------------------------------------------------------
# 5. DATA QUALITY CHECKS
# ---------------------------------------------------------

def validate_outputs(
    enriched_sales,
    demand_features,
    customer_rfm,
    inventory_analysis
):

    assert not enriched_sales.empty
    assert not demand_features.empty
    assert not customer_rfm.empty
    assert not inventory_analysis.empty

    assert (
        demand_features["quantity"] >= 0
    ).all()

    assert (
        customer_rfm["recency"] >= 0
    ).all()

    assert (
        customer_rfm["frequency"] > 0
    ).all()

    print(
        "Processed data validation passed."
    )


# ---------------------------------------------------------
# 6. SAVE PROCESSED DATA
# ---------------------------------------------------------

def save_outputs(
    enriched_sales,
    demand_features,
    customer_rfm,
    inventory_analysis
):

    enriched_sales.to_csv(
        PROCESSED_DIR /
        "sales_enriched.csv",
        index=False
    )

    demand_features.to_csv(
        PROCESSED_DIR /
        "daily_store_product_features.csv",
        index=False
    )

    customer_rfm.to_csv(
        PROCESSED_DIR /
        "customer_rfm.csv",
        index=False
    )

    inventory_analysis.to_csv(
        PROCESSED_DIR /
        "inventory_analysis.csv",
        index=False
    )


# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------

def main():

    print(
        "Loading raw retail datasets..."
    )

    (
        sales,
        products,
        stores,
        customers,
        inventory
    ) = load_data()

    print(
        "Creating enriched sales data..."
    )

    enriched_sales = (
        create_enriched_sales(
            sales,
            products,
            stores,
            customers
        )
    )

    print(
        "Creating demand forecasting features..."
    )

    demand_features = (
        create_demand_features(
            enriched_sales,
            products,
            stores
        )
    )

    print(
        "Creating customer RFM features..."
    )

    customer_rfm = (
        create_customer_rfm(
            enriched_sales
        )
    )

    print(
        "Creating inventory intelligence features..."
    )

    inventory_analysis = (
        create_inventory_features(
            inventory,
            enriched_sales,
            products,
            stores
        )
    )

    validate_outputs(
        enriched_sales,
        demand_features,
        customer_rfm,
        inventory_analysis
    )

    save_outputs(
        enriched_sales,
        demand_features,
        customer_rfm,
        inventory_analysis
    )

    print()
    print(
        "Feature engineering completed successfully."
    )

    print()
    print(
        f"Enriched Sales : "
        f"{len(enriched_sales):,}"
    )

    print(
        f"Demand Features: "
        f"{len(demand_features):,}"
    )

    print(
        f"Customer RFM   : "
        f"{len(customer_rfm):,}"
    )

    print(
        f"Inventory Rows : "
        f"{len(inventory_analysis):,}"
    )

    print()
    print(
        f"Files saved to: "
        f"{PROCESSED_DIR}"
    )


if __name__ == "__main__":
    main()