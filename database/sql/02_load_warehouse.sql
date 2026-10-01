-- --------------------------------------------------
-- RESET WAREHOUSE TABLES
-- --------------------------------------------------

TRUNCATE TABLE
    warehouse.fact_inventory,
    warehouse.fact_sales,
    warehouse.dim_date,
    warehouse.dim_product,
    warehouse.dim_customer,
    warehouse.dim_store
RESTART IDENTITY CASCADE;


-- --------------------------------------------------
-- LOAD PRODUCT DIMENSION
-- --------------------------------------------------

INSERT INTO warehouse.dim_product (
    product_id,
    product_name,
    category,
    unit_cost,
    unit_price,
    reorder_level
)
SELECT
    product_id,
    product_name,
    category,
    unit_cost::NUMERIC,
    unit_price::NUMERIC,
    reorder_level::INTEGER
FROM staging.stg_products;


-- --------------------------------------------------
-- LOAD CUSTOMER DIMENSION
-- --------------------------------------------------

INSERT INTO warehouse.dim_customer (
    customer_id,
    customer_name,
    customer_type,
    join_date
)
SELECT
    customer_id,
    customer_name,
    customer_type,
    join_date::DATE
FROM staging.stg_customers;


-- --------------------------------------------------
-- LOAD STORE DIMENSION
-- --------------------------------------------------

INSERT INTO warehouse.dim_store (
    store_id,
    store_name,
    region
)
SELECT
    store_id,
    store_name,
    region
FROM staging.stg_stores;


-- --------------------------------------------------
-- LOAD DATE DIMENSION
-- --------------------------------------------------

INSERT INTO warehouse.dim_date (
    date_key,
    full_date,
    day,
    month,
    month_name,
    quarter,
    year,
    day_of_week,
    day_name,
    is_weekend
)
SELECT DISTINCT
    TO_CHAR(date::DATE, 'YYYYMMDD')::INTEGER,
    date::DATE,
    EXTRACT(DAY FROM date::DATE)::INTEGER,
    EXTRACT(MONTH FROM date::DATE)::INTEGER,
    TO_CHAR(date::DATE, 'FMMonth'),
    EXTRACT(QUARTER FROM date::DATE)::INTEGER,
    EXTRACT(YEAR FROM date::DATE)::INTEGER,
    EXTRACT(ISODOW FROM date::DATE)::INTEGER,
    TO_CHAR(date::DATE, 'FMDay'),
    EXTRACT(ISODOW FROM date::DATE) IN (6, 7)
FROM staging.stg_sales
ORDER BY 1;


-- --------------------------------------------------
-- LOAD SALES FACT TABLE
-- --------------------------------------------------

INSERT INTO warehouse.fact_sales (
    transaction_id,
    date_key,
    product_key,
    customer_key,
    store_key,
    quantity,
    unit_price,
    unit_cost,
    discount_pct,
    revenue,
    cost,
    profit,
    promotion
)
SELECT
    s.transaction_id,

    TO_CHAR(
        s.date::DATE,
        'YYYYMMDD'
    )::INTEGER,

    p.product_key,

    c.customer_key,

    st.store_key,

    s.quantity::INTEGER,

    s.unit_price::NUMERIC,

    s.unit_cost::NUMERIC,

    s.discount_pct::NUMERIC,

    s.revenue::NUMERIC,

    s.cost::NUMERIC,

    s.profit::NUMERIC,

    s.promotion::INTEGER = 1

FROM staging.stg_sales s

JOIN warehouse.dim_product p
    ON p.product_id = s.product_id

JOIN warehouse.dim_customer c
    ON c.customer_id = s.customer_id

JOIN warehouse.dim_store st
    ON st.store_id = s.store_id;


-- --------------------------------------------------
-- LOAD INVENTORY FACT TABLE
-- --------------------------------------------------

INSERT INTO warehouse.fact_inventory (
    snapshot_date,
    product_key,
    store_key,
    stock_on_hand,
    reorder_level
)
SELECT
    i.snapshot_date::DATE,

    p.product_key,

    st.store_key,

    i.stock_on_hand::INTEGER,

    i.reorder_level::INTEGER

FROM staging.stg_inventory i

JOIN warehouse.dim_product p
    ON p.product_id = i.product_id

JOIN warehouse.dim_store st
    ON st.store_id = i.store_id;


-- --------------------------------------------------
-- FINAL ROW COUNTS
-- --------------------------------------------------

SELECT 'dim_date' AS table_name,
       COUNT(*) AS row_count
FROM warehouse.dim_date

UNION ALL

SELECT 'dim_product',
       COUNT(*)
FROM warehouse.dim_product

UNION ALL

SELECT 'dim_customer',
       COUNT(*)
FROM warehouse.dim_customer

UNION ALL

SELECT 'dim_store',
       COUNT(*)
FROM warehouse.dim_store

UNION ALL

SELECT 'fact_sales',
       COUNT(*)
FROM warehouse.fact_sales

UNION ALL

SELECT 'fact_inventory',
       COUNT(*)
FROM warehouse.fact_inventory;