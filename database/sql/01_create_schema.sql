CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS warehouse;


-- --------------------------------------------------
-- DATE DIMENSION
-- --------------------------------------------------

CREATE TABLE IF NOT EXISTS warehouse.dim_date (
    date_key INTEGER PRIMARY KEY,
    full_date DATE UNIQUE NOT NULL,
    day INTEGER NOT NULL,
    month INTEGER NOT NULL,
    month_name VARCHAR(20) NOT NULL,
    quarter INTEGER NOT NULL,
    year INTEGER NOT NULL,
    day_of_week INTEGER NOT NULL,
    day_name VARCHAR(20) NOT NULL,
    is_weekend BOOLEAN NOT NULL
);


-- --------------------------------------------------
-- PRODUCT DIMENSION
-- --------------------------------------------------

CREATE TABLE IF NOT EXISTS warehouse.dim_product (
    product_key SERIAL PRIMARY KEY,
    product_id VARCHAR(20) UNIQUE NOT NULL,
    product_name VARCHAR(120) NOT NULL,
    category VARCHAR(80) NOT NULL,
    unit_cost NUMERIC(12, 2),
    unit_price NUMERIC(12, 2),
    reorder_level INTEGER
);


-- --------------------------------------------------
-- CUSTOMER DIMENSION
-- --------------------------------------------------

CREATE TABLE IF NOT EXISTS warehouse.dim_customer (
    customer_key SERIAL PRIMARY KEY,
    customer_id VARCHAR(20) UNIQUE NOT NULL,
    customer_name VARCHAR(120),
    customer_type VARCHAR(40),
    join_date DATE
);


-- --------------------------------------------------
-- STORE DIMENSION
-- --------------------------------------------------

CREATE TABLE IF NOT EXISTS warehouse.dim_store (
    store_key SERIAL PRIMARY KEY,
    store_id VARCHAR(20) UNIQUE NOT NULL,
    store_name VARCHAR(120),
    region VARCHAR(80)
);


-- --------------------------------------------------
-- SALES FACT TABLE
-- --------------------------------------------------

CREATE TABLE IF NOT EXISTS warehouse.fact_sales (
    sales_key BIGSERIAL PRIMARY KEY,

    transaction_id VARCHAR(30) UNIQUE NOT NULL,

    date_key INTEGER
        REFERENCES warehouse.dim_date(date_key),

    product_key INTEGER
        REFERENCES warehouse.dim_product(product_key),

    customer_key INTEGER
        REFERENCES warehouse.dim_customer(customer_key),

    store_key INTEGER
        REFERENCES warehouse.dim_store(store_key),

    quantity INTEGER NOT NULL,

    unit_price NUMERIC(12, 2),

    unit_cost NUMERIC(12, 2),

    discount_pct NUMERIC(6, 4),

    revenue NUMERIC(14, 2),

    cost NUMERIC(14, 2),

    profit NUMERIC(14, 2),

    promotion BOOLEAN
);


-- --------------------------------------------------
-- INVENTORY FACT TABLE
-- --------------------------------------------------

CREATE TABLE IF NOT EXISTS warehouse.fact_inventory (
    inventory_key BIGSERIAL PRIMARY KEY,

    snapshot_date DATE NOT NULL,

    product_key INTEGER
        REFERENCES warehouse.dim_product(product_key),

    store_key INTEGER
        REFERENCES warehouse.dim_store(store_key),

    stock_on_hand INTEGER,

    reorder_level INTEGER
);