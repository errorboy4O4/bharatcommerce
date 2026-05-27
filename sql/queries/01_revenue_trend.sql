-- ============================================================
-- BharatCommerce — Query 01: Monthly Revenue Trend
-- ============================================================
-- Business Question:
--   What's our monthly revenue trend? Which months show
--   growth or decline? Are there seasonality patterns?
--
-- SQL Concepts Used:
--   ✓ CTE (WITH clause) — break complex logic into steps
--   ✓ Window Function: LAG() — month-over-month comparison
--   ✓ Multi-table JOIN — orders + order_items
--   ✓ Date functions — strftime() for month extraction
--   ✓ ROUND() — clean output formatting
--   ✓ CASE WHEN — label growth vs decline
-- ============================================================

WITH monthly_revenue AS (
    -- Step 1: Calculate total revenue per month
    -- We join orders with order_items to get the price
    -- Only count delivered orders (not canceled/returned)
    SELECT
        strftime('%Y-%m', o.order_purchase_timestamp) AS month,
        COUNT(DISTINCT o.order_id) AS total_orders,
        ROUND(SUM(oi.price + oi.freight_value), 2) AS revenue,
        ROUND(AVG(oi.price + oi.freight_value), 2) AS avg_order_item_value
    FROM orders o
    JOIN order_items oi ON o.order_id = oi.order_id
    WHERE o.order_status = 'delivered'
    GROUP BY strftime('%Y-%m', o.order_purchase_timestamp)
),

revenue_with_growth AS (
    -- Step 2: Use LAG() to get previous month's revenue
    -- Then calculate month-over-month growth percentage
    SELECT
        month,
        total_orders,
        revenue,
        avg_order_item_value,
        LAG(revenue, 1) OVER (ORDER BY month) AS prev_month_revenue,
        ROUND(
            (revenue - LAG(revenue, 1) OVER (ORDER BY month))
            / LAG(revenue, 1) OVER (ORDER BY month) * 100,
            1
        ) AS mom_growth_pct
    FROM monthly_revenue
)

-- Step 3: Final output with trend labels
SELECT
    month,
    total_orders,
    revenue,
    avg_order_item_value,
    prev_month_revenue,
    mom_growth_pct,
    CASE
        WHEN mom_growth_pct IS NULL THEN 'First Month'
        WHEN mom_growth_pct > 10 THEN '📈 Strong Growth'
        WHEN mom_growth_pct > 0 THEN '📈 Growth'
        WHEN mom_growth_pct > -10 THEN '📉 Slight Decline'
        ELSE '📉 Sharp Decline'
    END AS trend
FROM revenue_with_growth
ORDER BY month;
