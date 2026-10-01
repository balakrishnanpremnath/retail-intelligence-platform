-- =====================================================
-- RETAIL INTELLIGENCE PLATFORM
-- KEY BUSINESS INSIGHT SUMMARY
-- =====================================================


-- 1. OVERALL KPIs
SELECT
    COUNT(DISTINCT transaction_id) AS transactions,
    SUM(quantity) AS units_sold,
    ROUND(SUM(revenue), 2) AS revenue,
    ROUND(SUM(profit), 2) AS profit,
    ROUND(
        100.0 * SUM(profit) /
        NULLIF(SUM(revenue), 0),
        2
    ) AS margin_pct
FROM warehouse.fact_sales;


-- 2. TOP 5 PRODUCTS
SELECT
    p.product_name,
    p.category,
    SUM(f.quantity) AS units_sold,
    ROUND(SUM(f.revenue), 2) AS revenue,
    ROUND(SUM(f.profit), 2) AS profit
FROM warehouse.fact_sales f
JOIN warehouse.dim_product p
    ON f.product_key = p.product_key
GROUP BY
    p.product_name,
    p.category
ORDER BY revenue DESC
LIMIT 5;


-- 3. STORE PERFORMANCE
SELECT
    s.store_name,
    s.region,
    ROUND(SUM(f.revenue), 2) AS revenue,
    ROUND(SUM(f.profit), 2) AS profit
FROM warehouse.fact_sales f
JOIN warehouse.dim_store s
    ON f.store_key = s.store_key
GROUP BY
    s.store_name,
    s.region
ORDER BY revenue DESC;


-- 4. PROMOTION PERFORMANCE
SELECT
    CASE
        WHEN promotion THEN 'Promotion'
        ELSE 'No Promotion'
    END AS sale_type,

    COUNT(*) AS transactions,

    ROUND(SUM(revenue), 2) AS revenue,

    ROUND(SUM(profit), 2) AS profit,

    ROUND(
        100.0 * SUM(profit) /
        NULLIF(SUM(revenue), 0),
        2
    ) AS margin_pct

FROM warehouse.fact_sales
GROUP BY promotion
ORDER BY revenue DESC;


-- 5. INVENTORY STATUS
SELECT
    CASE
        WHEN i.stock_on_hand <= i.reorder_level
            THEN 'REORDER'

        WHEN i.stock_on_hand <= i.reorder_level * 1.25
            THEN 'LOW STOCK'

        ELSE 'OK'
    END AS stock_status,

    COUNT(*) AS product_store_records

FROM warehouse.fact_inventory i

GROUP BY 1
ORDER BY 2 DESC;


-- 6. TOP 5 CATEGORIES
SELECT
    p.category,
    ROUND(SUM(f.revenue), 2) AS revenue,
    ROUND(SUM(f.profit), 2) AS profit
FROM warehouse.fact_sales f
JOIN warehouse.dim_product p
    ON f.product_key = p.product_key
GROUP BY p.category
ORDER BY revenue DESC
LIMIT 5;