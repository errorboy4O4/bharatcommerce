-- ============================================================
-- BharatCommerce — Query 10: Delivery vs Reviews Correlation
-- ============================================================
-- Business Question:
--   Quantify: for every 1 extra day of late delivery, how
--   much does the average review score drop? What's the
--   financial cost of late deliveries?
--
-- SQL Concepts Used:
--   ✓ Computed columns — date arithmetic for late days
--   ✓ CASE WHEN — bucketing continuous variable
--   ✓ Window Function: SUM() OVER() — percentage calculations
--   ✓ Multi-table JOIN — 4 tables
--   ✓ Subquery — for overall averages
--   ✓ GROUP BY on computed expression
--   ✓ HAVING — filter for statistical validity
--
-- NOTE: The Pearson correlation coefficient (r) will be
--   calculated in Python using scipy.stats.pearsonr().
--   SQL handles the aggregation; Python handles the stats.
-- ============================================================

-- ──────────────────────────────────────────
-- PART A: Order-Level Data (for scatter plot + correlation)
-- ──────────────────────────────────────────

WITH order_delivery AS (
    -- Step 1: Calculate delivery metrics per order
    SELECT
        o.order_id,
        c.customer_state,
        r.review_score,
        -- Total delivery time in days
        CAST(
            julianday(o.order_delivered_customer_date)
            - julianday(o.order_purchase_timestamp)
        AS INTEGER) AS total_delivery_days,
        -- Days late (positive = late, negative = early)
        CAST(
            julianday(o.order_delivered_customer_date)
            - julianday(o.order_estimated_delivery_date)
        AS INTEGER) AS days_late,
        -- Was it late?
        CASE
            WHEN julianday(o.order_delivered_customer_date)
                 > julianday(o.order_estimated_delivery_date)
            THEN 'Late'
            ELSE 'On Time'
        END AS delivery_status
    FROM orders o
    JOIN customers c ON o.customer_id = c.customer_id
    JOIN order_reviews r ON o.order_id = r.order_id
    WHERE o.order_status = 'delivered'
      AND o.order_delivered_customer_date IS NOT NULL
      AND o.order_estimated_delivery_date IS NOT NULL
      AND r.review_score IS NOT NULL
)

-- ──────────────────────────────────────────
-- PART B: Bucketed Analysis (for bar chart)
-- Shows clear linear drop in reviews as late days increase
-- ──────────────────────────────────────────

SELECT
    CASE
        WHEN days_late <= -15 THEN '15+ days early'
        WHEN days_late <= -8  THEN '8-14 days early'
        WHEN days_late <= -3  THEN '3-7 days early'
        WHEN days_late <= -1  THEN '1-2 days early'
        WHEN days_late = 0    THEN 'On time (exact)'
        WHEN days_late <= 2   THEN '1-2 days late'
        WHEN days_late <= 5   THEN '3-5 days late'
        WHEN days_late <= 10  THEN '6-10 days late'
        WHEN days_late <= 20  THEN '11-20 days late'
        WHEN days_late <= 40  THEN '21-40 days late'
        ELSE '40+ days late'
    END AS delivery_bucket,
    -- Sort key for proper ordering
    CASE
        WHEN days_late <= -15 THEN 1
        WHEN days_late <= -8  THEN 2
        WHEN days_late <= -3  THEN 3
        WHEN days_late <= -1  THEN 4
        WHEN days_late = 0    THEN 5
        WHEN days_late <= 2   THEN 6
        WHEN days_late <= 5   THEN 7
        WHEN days_late <= 10  THEN 8
        WHEN days_late <= 20  THEN 9
        WHEN days_late <= 40  THEN 10
        ELSE 11
    END AS sort_order,
    COUNT(*) AS order_count,
    ROUND(AVG(review_score), 2) AS avg_review,
    ROUND(AVG(CASE WHEN review_score = 5 THEN 1.0 ELSE 0.0 END) * 100, 1)
        AS pct_5_star,
    ROUND(AVG(CASE WHEN review_score <= 2 THEN 1.0 ELSE 0.0 END) * 100, 1)
        AS pct_1_or_2_star,
    -- Percentage of total orders in this bucket
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 1) AS pct_of_orders,
    -- Average late days in this bucket (for plotting)
    ROUND(AVG(days_late), 1) AS avg_days_late
FROM order_delivery
GROUP BY delivery_bucket, sort_order
HAVING order_count >= 20
ORDER BY sort_order;
