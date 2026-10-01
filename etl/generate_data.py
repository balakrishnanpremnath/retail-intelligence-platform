from pathlib import Path
import numpy as np
import pandas as pd


# ---------------------------------------------------------
# PROJECT PATHS
# ---------------------------------------------------------

ROOT_DIR = Path(__file__).resolve().parents[1]
RAW_DATA_DIR = ROOT_DIR / "data" / "raw"

RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)


# Same random seed = same dataset every time
RNG = np.random.default_rng(42)


# ---------------------------------------------------------
# 1. PRODUCTS DATA
# ---------------------------------------------------------

def create_products():

    products_data = [
        ("Rice 5kg", "Staples"),
        ("Rice 10kg", "Staples"),
        ("Dhal 1kg", "Staples"),
        ("Sugar 1kg", "Staples"),
        ("Flour 1kg", "Staples"),
        ("Milk Powder 400g", "Dairy"),
        ("Milk Powder 1kg", "Dairy"),
        ("Tea 200g", "Beverages"),
        ("Coffee 100g", "Beverages"),
        ("Biscuits Pack", "Snacks"),
        ("Noodles Pack", "Convenience"),
        ("Canned Fish", "Canned Goods"),
        ("Coconut Milk", "Canned Goods"),
        ("Cooking Oil 1L", "Staples"),
        ("Cooking Oil 5L", "Staples"),
        ("Soap Bar", "Personal Care"),
        ("Shampoo 180ml", "Personal Care"),
        ("Toothpaste 120g", "Personal Care"),
        ("Detergent 1kg", "Household"),
        ("Dishwash Liquid", "Household"),
        ("Soft Drink 1.5L", "Beverages"),
        ("Bottled Water 1.5L", "Beverages"),
        ("Fruit Juice 1L", "Beverages"),
        ("Yoghurt Cup", "Dairy"),
        ("Cheese Pack", "Dairy"),
        ("Eggs 10 Pack", "Fresh Food"),
        ("Chicken 1kg", "Fresh Food"),
        ("Frozen Fish 1kg", "Frozen Food"),
        ("Onions 1kg", "Fresh Food"),
        ("Potatoes 1kg", "Fresh Food"),
    ]

    products = pd.DataFrame(
        products_data,
        columns=["product_name", "category"]
    )

    products.insert(
        0,
        "product_id",
        [f"P{i:03d}" for i in range(1, len(products) + 1)]
    )

    products["unit_cost"] = np.round(
        RNG.uniform(100, 2500, len(products)),
        2
    )

    markup = RNG.uniform(
        1.15,
        1.40,
        len(products)
    )

    products["unit_price"] = np.round(
        products["unit_cost"] * markup,
        2
    )

    products["reorder_level"] = RNG.integers(
        20,
        70,
        len(products)
    )

    return products


# ---------------------------------------------------------
# 2. STORE DATA
# ---------------------------------------------------------

def create_stores():

    stores = pd.DataFrame({
        "store_id": [
            "S001",
            "S002",
            "S003",
            "S004"
        ],

        "store_name": [
            "Colombo Central",
            "Kandy City",
            "Galle Town",
            "Jaffna North"
        ],

        "region": [
            "Western",
            "Central",
            "Southern",
            "Northern"
        ]
    })

    return stores


# ---------------------------------------------------------
# 3. CUSTOMER DATA
# ---------------------------------------------------------

def create_customers():

    number_of_customers = 500

    customers = pd.DataFrame({
        "customer_id": [
            f"C{i:04d}"
            for i in range(1, number_of_customers + 1)
        ]
    })

    customers["customer_name"] = [
        f"Customer {i:04d}"
        for i in range(1, number_of_customers + 1)
    ]

    customers["customer_type"] = RNG.choice(
        [
            "Retail",
            "Loyalty",
            "Wholesale"
        ],
        size=number_of_customers,
        p=[
            0.55,
            0.35,
            0.10
        ]
    )

    start_date = pd.Timestamp("2024-01-01")

    random_days = RNG.integers(
        0,
        730,
        number_of_customers
    )

    customers["join_date"] = (
        start_date +
        pd.to_timedelta(random_days, unit="D")
    ).date

    return customers


# ---------------------------------------------------------
# 4. SALES TRANSACTIONS
# ---------------------------------------------------------

def create_sales(products, stores, customers):

    dates = pd.date_range(
        start="2025-01-01",
        end="2026-09-30",
        freq="D"
    )

    sales_records = []

    transaction_number = 1

    # Makes some products naturally more popular than others
    product_weights = RNG.dirichlet(
        np.ones(len(products)) * 1.5
    )

    for date in dates:

        # Higher sales during April and December
        if date.month in [4, 12]:
            seasonal_factor = 1.30
        else:
            seasonal_factor = 1.00

        # Slightly higher sales during weekends
        if date.dayofweek >= 5:
            weekend_factor = 1.15
        else:
            weekend_factor = 1.00

        average_orders = (
            28 *
            seasonal_factor *
            weekend_factor
        )

        number_of_orders = max(
            8,
            int(RNG.poisson(average_orders))
        )

        for _ in range(number_of_orders):

            # Select product
            product_index = RNG.choice(
                len(products),
                p=product_weights
            )

            product = products.iloc[product_index]

            # Select store
            store_index = RNG.integers(
                0,
                len(stores)
            )

            store = stores.iloc[store_index]

            # Select customer
            customer_index = RNG.integers(
                0,
                len(customers)
            )

            customer = customers.iloc[customer_index]

            # Quantity sold
            quantity = max(
                1,
                int(RNG.poisson(2.3))
            )

            # Promotion
            promotion = int(
                RNG.random() < 0.14
            )

            # Discount
            if promotion == 1:

                discount_pct = float(
                    RNG.choice(
                        [
                            0.05,
                            0.10,
                            0.15
                        ],
                        p=[
                            0.45,
                            0.40,
                            0.15
                        ]
                    )
                )

            else:

                discount_pct = 0.00

            unit_price = float(
                product["unit_price"]
            )

            unit_cost = float(
                product["unit_cost"]
            )

            revenue = (
                unit_price *
                quantity *
                (1 - discount_pct)
            )

            cost = (
                unit_cost *
                quantity
            )

            profit = (
                revenue -
                cost
            )

            sales_records.append({

                "transaction_id":
                    f"T{transaction_number:07d}",

                "date":
                    date.date(),

                "store_id":
                    store["store_id"],

                "customer_id":
                    customer["customer_id"],

                "product_id":
                    product["product_id"],

                "quantity":
                    quantity,

                "unit_price":
                    round(unit_price, 2),

                "unit_cost":
                    round(unit_cost, 2),

                "discount_pct":
                    round(discount_pct, 2),

                "revenue":
                    round(revenue, 2),

                "cost":
                    round(cost, 2),

                "profit":
                    round(profit, 2),

                "promotion":
                    promotion
            })

            transaction_number += 1

    sales = pd.DataFrame(
        sales_records
    )

    return sales


# ---------------------------------------------------------
# 5. INVENTORY DATA
# ---------------------------------------------------------

def create_inventory(products, stores):

    inventory_records = []

    for _, store in stores.iterrows():

        for _, product in products.iterrows():

            stock_on_hand = int(
                RNG.integers(
                    5,
                    180
                )
            )

            inventory_records.append({

                "store_id":
                    store["store_id"],

                "product_id":
                    product["product_id"],

                "snapshot_date":
                    "2026-09-30",

                "stock_on_hand":
                    stock_on_hand,

                "reorder_level":
                    int(
                        product[
                            "reorder_level"
                        ]
                    )
            })

    inventory = pd.DataFrame(
        inventory_records
    )

    return inventory


# ---------------------------------------------------------
# 6. DATA QUALITY CHECKS
# ---------------------------------------------------------

def validate_data(
    products,
    stores,
    customers,
    sales,
    inventory
):

    assert products["product_id"].is_unique
    assert stores["store_id"].is_unique
    assert customers["customer_id"].is_unique
    assert sales["transaction_id"].is_unique

    assert not sales[
        "product_id"
    ].isna().any()

    assert not sales[
        "customer_id"
    ].isna().any()

    assert not sales[
        "store_id"
    ].isna().any()

    assert (
        sales["quantity"] > 0
    ).all()

    assert (
        sales["revenue"] >= 0
    ).all()

    assert (
        sales["cost"] >= 0
    ).all()

    profit_difference = (
        sales["profit"] -
        (
            sales["revenue"] -
            sales["cost"]
        )
    ).abs()

    assert (
        profit_difference < 0.02
    ).all()

    print(
        "Data quality checks passed."
    )


# ---------------------------------------------------------
# 7. SAVE CSV FILES
# ---------------------------------------------------------

def save_datasets(
    products,
    stores,
    customers,
    sales,
    inventory
):

    products.to_csv(
        RAW_DATA_DIR / "products.csv",
        index=False
    )

    stores.to_csv(
        RAW_DATA_DIR / "stores.csv",
        index=False
    )

    customers.to_csv(
        RAW_DATA_DIR / "customers.csv",
        index=False
    )

    sales.to_csv(
        RAW_DATA_DIR / "sales.csv",
        index=False
    )

    inventory.to_csv(
        RAW_DATA_DIR / "inventory.csv",
        index=False
    )


# ---------------------------------------------------------
# MAIN PROGRAM
# ---------------------------------------------------------

def main():

    print(
        "Generating retail dataset..."
    )

    products = create_products()

    stores = create_stores()

    customers = create_customers()

    sales = create_sales(
        products,
        stores,
        customers
    )

    inventory = create_inventory(
        products,
        stores
    )

    validate_data(
        products,
        stores,
        customers,
        sales,
        inventory
    )

    save_datasets(
        products,
        stores,
        customers,
        sales,
        inventory
    )

    print()
    print(
        "Retail dataset generated successfully."
    )

    print()
    print(
        f"Products     : {len(products):,}"
    )

    print(
        f"Stores       : {len(stores):,}"
    )

    print(
        f"Customers    : {len(customers):,}"
    )

    print(
        f"Transactions : {len(sales):,}"
    )

    print(
        f"Inventory    : {len(inventory):,}"
    )

    print()

    print(
        f"Files saved to: {RAW_DATA_DIR}"
    )


if __name__ == "__main__":
    main()