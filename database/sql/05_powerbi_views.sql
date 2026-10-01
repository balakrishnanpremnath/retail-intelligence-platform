-- =========================================================
-- POWER BI ANALYTICS VIEWS
-- =========================================================


-- ---------------------------------------------------------
-- 1. SALES DETAIL VIEW
-- ---------------------------------------------------------

CREATE OR REPLACE VIEW analytics.vw_sales_detail AS

SELECT
    f.transaction_id,
    d.full_date,
    d.year,
    d.month,
    d.month_name,
    d.quarter,
    d.day_name,
    d.is_weekend,

    p.product_id,
    p.product_name,
    p.category,

    c.customer_id,
    c.customer_name,
    c.customer_type,

    s.store_id,
    s.store_name,
    s.region,

    f.quantity,
    f.unit_price,
    f.unit_cost,
    f.discount_pct,
    f.revenue,
    f.cost,
    f.profit,
    f.promotion

FROM warehouse.fact_sales f

JOIN warehouse.dim_date d
    ON f.date_key = d.date_key

JOIN warehouse.dim_product p
    ON f.product_key = p.product_key

JOIN warehouse.dim_customer c
    ON f.customer_key = c.customer_key

JOIN warehouse.dim_store s
    ON f.store_key = s.store_key;


-- ---------------------------------------------------------
-- 2. CUSTOMER SEGMENT VIEW
-- ---------------------------------------------------------

CREATE OR REPLACE VIEW analytics.vw_customer_segments AS

SELECT
    cs.customer_id,
    c.customer_name,
    c.customer_type,
    c.join_date,

    cs.recency,
    cs.frequency,
    cs.monetary,
    cs.cluster,
    cs.segment

FROM analytics.customer_segments cs

LEFT JOIN warehouse.dim_customer c
    ON cs.customer_id = c.customer_id;


-- ---------------------------------------------------------
-- 3. INVENTORY INTELLIGENCE VIEW
-- ---------------------------------------------------------

CREATE OR REPLACE VIEW analytics.vw_inventory_intelligence AS

SELECT
    store_id,
    store_name,
    region,

    product_id,
    product_name,
    category,

    snapshot_date,
    stock_on_hand,
    reorder_level,

    units_last_30_days,
    avg_daily_demand_30d,
    estimated_days_cover,

    forecast_14d_demand,
    safety_stock,
    demand_based_target,
    policy_target_stock,
    target_stock,

    recommended_reorder_qty,
    inventory_action,
    recommendation_reason

FROM analytics.reorder_recommendations;


-- ---------------------------------------------------------
-- 4. MONTHLY SALES SUMMARY VIEW
-- ---------------------------------------------------------

CREATE OR REPLACE VIEW analytics.vw_monthly_sales AS

SELECT
    d.year,
    d.month,
    d.month_name,

    ROUND(
        SUM(f.revenue),
        2
    ) AS revenue,

    ROUND(
        SUM(f.cost),
        2
    ) AS cost,

    ROUND(
        SUM(f.profit),
        2
    ) AS profit,

    SUM(
        f.quantity
    ) AS units_sold,

    COUNT(
        DISTINCT f.transaction_id
    ) AS transactions

FROM warehouse.fact_sales f

JOIN warehouse.dim_date d
    ON f.date_key = d.date_key

GROUP BY
    d.year,
    d.month,
    d.month_name

ORDER BY
    d.year,
    d.month;