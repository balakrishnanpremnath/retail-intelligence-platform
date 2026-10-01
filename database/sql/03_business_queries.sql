-- =========================================================
-- RETAIL INTELLIGENCE PLATFORM
-- BUSINESS ANALYSIS QUERIES
-- =========================================================


-- ---------------------------------------------------------
-- 1. OVERALL BUSINESS KPIs
-- ---------------------------------------------------------

SELECT
    COUNT(DISTINCT transaction_id) AS total_transactions,
    SUM(quantity) AS total_units_sold,
    ROUND(SUM(revenue), 2) AS total_revenue,
    ROUND(SUM(cost), 2) AS total_cost,
    ROUND(SUM(profit), 2) AS total_profit,
    ROUND(
        100.0 * SUM(profit) /
        NULLIF(SUM(revenue), 0),
        2
    ) AS profit_margin_pct
FROM warehouse.fact_sales;


-- ---------------------------------------------------------
-- 2. MONTHLY REVENUE AND PROFIT TREND
-- ---------------------------------------------------------

SELECT
    d.year,
    d.month,
    d.month_name,
    ROUND(SUM(f.revenue), 2) AS revenue,
    ROUND(SUM(f.profit), 2) AS profit,
    SUM(f.quantity) AS units_sold
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


-- ---------------------------------------------------------
-- 3. MONTH-OVER-MONTH REVENUE GROWTH
-- Uses CTE + LAG window function
-- ---------------------------------------------------------

WITH monthly_sales AS (

    SELECT
        DATE_TRUNC(
            'month',
            d.full_date
        ) AS month_start,

        SUM(f.revenue) AS revenue

    FROM warehouse.fact_sales f

    JOIN warehouse.dim_date d
        ON f.date_key = d.date_key

    GROUP BY
        DATE_TRUNC(
            'month',
            d.full_date
        )
),

monthly_growth AS (

    SELECT
        month_start,
        revenue,

        LAG(revenue) OVER (
            ORDER BY month_start
        ) AS previous_month_revenue

    FROM monthly_sales
)

SELECT
    month_start,

    ROUND(
        revenue,
        2
    ) AS revenue,

    ROUND(
        previous_month_revenue,
        2
    ) AS previous_month_revenue,

    ROUND(
        100.0 *
        (
            revenue -
            previous_month_revenue
        )
        /
        NULLIF(
            previous_month_revenue,
            0
        ),
        2
    ) AS mom_growth_pct

FROM monthly_growth

ORDER BY month_start;


-- ---------------------------------------------------------
-- 4. TOP 10 PRODUCTS BY REVENUE
-- ---------------------------------------------------------

SELECT
    p.product_name,
    p.category,

    SUM(f.quantity) AS units_sold,

    ROUND(
        SUM(f.revenue),
        2
    ) AS revenue,

    ROUND(
        SUM(f.profit),
        2
    ) AS profit,

    ROUND(
        100.0 *
        SUM(f.profit)
        /
        NULLIF(
            SUM(f.revenue),
            0
        ),
        2
    ) AS profit_margin_pct

FROM warehouse.fact_sales f

JOIN warehouse.dim_product p
    ON f.product_key = p.product_key

GROUP BY
    p.product_name,
    p.category

ORDER BY revenue DESC

LIMIT 10;


-- ---------------------------------------------------------
-- 5. CATEGORY PERFORMANCE
-- ---------------------------------------------------------

SELECT
    p.category,

    SUM(f.quantity) AS units_sold,

    ROUND(
        SUM(f.revenue),
        2
    ) AS revenue,

    ROUND(
        SUM(f.profit),
        2
    ) AS profit,

    ROUND(
        100.0 *
        SUM(f.profit)
        /
        NULLIF(
            SUM(f.revenue),
            0
        ),
        2
    ) AS profit_margin_pct

FROM warehouse.fact_sales f

JOIN warehouse.dim_product p
    ON f.product_key = p.product_key

GROUP BY
    p.category

ORDER BY revenue DESC;


-- ---------------------------------------------------------
-- 6. STORE PERFORMANCE RANKING
-- Uses DENSE_RANK window function
-- ---------------------------------------------------------

WITH store_performance AS (

    SELECT
        s.store_name,
        s.region,

        COUNT(
            DISTINCT f.transaction_id
        ) AS transactions,

        SUM(f.quantity) AS units_sold,

        SUM(f.revenue) AS revenue,

        SUM(f.profit) AS profit

    FROM warehouse.fact_sales f

    JOIN warehouse.dim_store s
        ON f.store_key = s.store_key

    GROUP BY
        s.store_name,
        s.region
)

SELECT
    store_name,
    region,
    transactions,
    units_sold,

    ROUND(
        revenue,
        2
    ) AS revenue,

    ROUND(
        profit,
        2
    ) AS profit,

    DENSE_RANK() OVER (
        ORDER BY revenue DESC
    ) AS revenue_rank

FROM store_performance

ORDER BY revenue_rank;


-- ---------------------------------------------------------
-- 7. TOP 20 CUSTOMERS BY LIFETIME REVENUE
-- ---------------------------------------------------------

SELECT
    c.customer_id,
    c.customer_name,
    c.customer_type,

    COUNT(
        DISTINCT f.transaction_id
    ) AS transactions,

    SUM(f.quantity) AS units_purchased,

    ROUND(
        SUM(f.revenue),
        2
    ) AS lifetime_revenue,

    ROUND(
        SUM(f.profit),
        2
    ) AS lifetime_profit

FROM warehouse.fact_sales f

JOIN warehouse.dim_customer c
    ON f.customer_key = c.customer_key

GROUP BY
    c.customer_id,
    c.customer_name,
    c.customer_type

ORDER BY lifetime_revenue DESC

LIMIT 20;


-- ---------------------------------------------------------
-- 8. PROMOTION VS NON-PROMOTION PERFORMANCE
-- ---------------------------------------------------------

SELECT
    CASE
        WHEN promotion = TRUE
            THEN 'Promotion'
        ELSE 'No Promotion'
    END AS promotion_type,

    COUNT(*) AS transactions,

    SUM(quantity) AS units_sold,

    ROUND(
        AVG(discount_pct) * 100,
        2
    ) AS avg_discount_pct,

    ROUND(
        SUM(revenue),
        2
    ) AS revenue,

    ROUND(
        SUM(profit),
        2
    ) AS profit,

    ROUND(
        100.0 *
        SUM(profit)
        /
        NULLIF(
            SUM(revenue),
            0
        ),
        2
    ) AS margin_pct

FROM warehouse.fact_sales

GROUP BY promotion

ORDER BY revenue DESC;


-- ---------------------------------------------------------
-- 9. INVENTORY REORDER ALERTS
-- ---------------------------------------------------------

SELECT
    s.store_name,
    p.product_name,
    p.category,

    i.stock_on_hand,
    i.reorder_level,

    CASE

        WHEN i.stock_on_hand
             <= i.reorder_level
            THEN 'REORDER'

        WHEN i.stock_on_hand
             <= i.reorder_level * 1.25
            THEN 'LOW STOCK'

        ELSE 'OK'

    END AS stock_status

FROM warehouse.fact_inventory i

JOIN warehouse.dim_product p
    ON i.product_key = p.product_key

JOIN warehouse.dim_store s
    ON i.store_key = s.store_key

ORDER BY

    CASE

        WHEN i.stock_on_hand
             <= i.reorder_level
            THEN 1

        WHEN i.stock_on_hand
             <= i.reorder_level * 1.25
            THEN 2

        ELSE 3

    END,

    i.stock_on_hand ASC;


-- ---------------------------------------------------------
-- 10. CUSTOMER RFM BASE DATA
-- Used later for customer segmentation
-- ---------------------------------------------------------

WITH customer_summary AS (

    SELECT
        c.customer_id,

        MAX(
            d.full_date
        ) AS last_purchase_date,

        COUNT(
            DISTINCT f.transaction_id
        ) AS frequency,

        SUM(
            f.revenue
        ) AS monetary

    FROM warehouse.fact_sales f

    JOIN warehouse.dim_customer c
        ON f.customer_key = c.customer_key

    JOIN warehouse.dim_date d
        ON f.date_key = d.date_key

    GROUP BY
        c.customer_id
),

reference_date AS (

    SELECT
        MAX(full_date) + INTERVAL '1 day'
            AS analysis_date

    FROM warehouse.dim_date
)

SELECT
    cs.customer_id,

    (
        r.analysis_date -
        cs.last_purchase_date
    )::INTEGER AS recency_days,

    cs.frequency,

    ROUND(
        cs.monetary,
        2
    ) AS monetary_value

FROM customer_summary cs

CROSS JOIN reference_date r

ORDER BY monetary_value DESC;


-- ---------------------------------------------------------
-- 11. WEEKDAY VS WEEKEND SALES
-- ---------------------------------------------------------

SELECT
    CASE
        WHEN d.is_weekend
            THEN 'Weekend'
        ELSE 'Weekday'
    END AS day_type,

    COUNT(
        DISTINCT f.transaction_id
    ) AS transactions,

    SUM(f.quantity) AS units_sold,

    ROUND(
        SUM(f.revenue),
        2
    ) AS revenue,

    ROUND(
        SUM(f.profit),
        2
    ) AS profit

FROM warehouse.fact_sales f

JOIN warehouse.dim_date d
    ON f.date_key = d.date_key

GROUP BY d.is_weekend

ORDER BY revenue DESC;


-- ---------------------------------------------------------
-- 12. TOP PRODUCT IN EACH CATEGORY
-- Uses ROW_NUMBER window function
-- ---------------------------------------------------------

WITH product_performance AS (

    SELECT
        p.category,
        p.product_name,

        SUM(
            f.revenue
        ) AS revenue,

        SUM(
            f.profit
        ) AS profit

    FROM warehouse.fact_sales f

    JOIN warehouse.dim_product p
        ON f.product_key = p.product_key

    GROUP BY
        p.category,
        p.product_name
),

ranked_products AS (

    SELECT
        category,
        product_name,
        revenue,
        profit,

        ROW_NUMBER() OVER (
            PARTITION BY category
            ORDER BY revenue DESC
        ) AS product_rank

    FROM product_performance
)

SELECT
    category,
    product_name,

    ROUND(
        revenue,
        2
    ) AS revenue,

    ROUND(
        profit,
        2
    ) AS profit

FROM ranked_products

WHERE product_rank = 1

ORDER BY revenue DESC;