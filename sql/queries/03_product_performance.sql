-- ============================================================
-- BharatCommerce — Query 03: Product Performance Analysis
-- ============================================================
-- Business Question:
--   Which product categories generate the most revenue?
--   Which are trending up vs down? Which have best margins?
--
-- SQL Concepts Used:
--   ✓ Window Functions: RANK(), DENSE_RANK(), SUM() OVER()
--   ✓ Multiple CTEs — 4 chained steps
--   ✓ CASE WHEN — period bucketing and trend labeling
--   ✓ Multi-table JOIN — 3 tables (orders + order_items + products)
--   ✓ COALESCE — handle NULLs from LEFT JOIN
--   ✓ HAVING — filter after aggregation
--   ✓ Percentage of total — SUM() OVER() for running totals
-- ============================================================

-- ──────────────────────────────────────────
-- PART A: Overall Category Rankings
-- ──────────────────────────────────────────

WITH category_metrics AS (
    -- Step 1: Aggregate revenue, orders, and avg price per category
    SELECT
        COALESCE(p.product_category_name_english, 'uncategorized') AS category,
        COUNT(DISTINCT o.order_id) AS total_orders,
        COUNT(DISTINCT oi.product_id) AS unique_products,
        ROUND(SUM(oi.price), 2) AS revenue,
        ROUND(AVG(oi.price), 2) AS avg_price,
        ROUND(AVG(r.review_score), 2) AS avg_review_score
    FROM orders o
    JOIN order_items oi ON o.order_id = oi.order_id
    JOIN products p ON oi.product_id = p.product_id
    LEFT JOIN order_reviews r ON o.order_id = r.order_id
    WHERE o.order_status = 'delivered'
    GROUP BY COALESCE(p.product_category_name_english, 'uncategorized')
    HAVING total_orders >= 20
),

ranked_categories AS (
    -- Step 2: Rank categories by revenue
    -- DENSE_RANK so ties don't skip positions
    -- Also calculate % of total revenue using SUM() OVER()
    SELECT
        category,
        total_orders,
        unique_products,
        revenue,
        avg_price,
        avg_review_score,
        DENSE_RANK() OVER (ORDER BY revenue DESC) AS revenue_rank,
        RANK() OVER (ORDER BY total_orders DESC) AS volume_rank,
        ROUND(
            revenue * 100.0 / SUM(revenue) OVER (),
            2
        ) AS pct_of_total_revenue,
        ROUND(
            SUM(revenue) OVER (ORDER BY revenue DESC
                ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)
            * 100.0 / SUM(revenue) OVER (),
            2
        ) AS cumulative_pct
    FROM category_metrics
)

SELECT *
FROM ranked_categories
ORDER BY revenue_rank
LIMIT 20;
