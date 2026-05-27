-- ============================================================
-- BharatCommerce — Query 04: Delivery Performance Analysis
-- ============================================================
-- Business Question:
--   What's the average delivery time by state? Which states
--   have the worst late-delivery rates? How does late delivery
--   affect customer review scores?
--
-- SQL Concepts Used:
--   ✓ Date arithmetic — julianday() for day differences
--   ✓ CASE WHEN — flag late vs on-time deliveries
--   ✓ Multiple CTEs — chained calculations
--   ✓ Window Function: AVG() OVER() — running averages
--   ✓ Multi-table JOIN — 4 tables
--   ✓ GROUP BY with HAVING — filter small sample states
--   ✓ ROUND, CAST — clean numerical output
--
-- NOTE: In PostgreSQL/BigQuery, replace julianday() math with
--   DATEDIFF() or DATE_DIFF(). The logic is identical.
-- ============================================================

-- ──────────────────────────────────────────
-- PART A: Delivery Metrics by State
-- ──────────────────────────────────────────

WITH delivery_facts AS (
    -- Step 1: Calculate delivery metrics for every delivered order
    -- We compute actual delivery days, estimated days, and whether
    -- the delivery was late (actual > estimated)
    SELECT
        o.order_id,
        c.customer_state,
        CAST(
            julianday(o.order_delivered_customer_date)
            - julianday(o.order_purchase_timestamp)
        AS INTEGER) AS actual_delivery_days,
        CAST(
            julianday(o.order_estimated_delivery_date)
            - julianday(o.order_purchase_timestamp)
        AS INTEGER) AS estimated_delivery_days,
        CAST(
            julianday(o.order_delivered_customer_date)
            - julianday(o.order_estimated_delivery_date)
        AS INTEGER) AS days_vs_estimate,
        CASE
            WHEN julianday(o.order_delivered_customer_date)
                 > julianday(o.order_estimated_delivery_date)
            THEN 1
            ELSE 0
        END AS is_late,
        r.review_score
    FROM orders o
    JOIN customers c ON o.customer_id = c.customer_id
    LEFT JOIN order_reviews r ON o.order_id = r.order_id
    WHERE o.order_status = 'delivered'
      AND o.order_delivered_customer_date IS NOT NULL
      AND o.order_estimated_delivery_date IS NOT NULL
),

state_performance AS (
    -- Step 2: Aggregate delivery metrics by state
    SELECT
        customer_state AS state,
        COUNT(*) AS total_orders,
        ROUND(AVG(actual_delivery_days), 1) AS avg_delivery_days,
        ROUND(AVG(estimated_delivery_days), 1) AS avg_estimated_days,
        ROUND(AVG(days_vs_estimate), 1) AS avg_days_vs_estimate,
        ROUND(SUM(is_late) * 100.0 / COUNT(*), 1) AS late_delivery_pct,
        SUM(is_late) AS late_orders,
        ROUND(AVG(review_score), 2) AS avg_review_score,
        -- Average review for late vs on-time (for comparison)
        ROUND(AVG(CASE WHEN is_late = 1 THEN review_score END), 2)
            AS avg_review_when_late,
        ROUND(AVG(CASE WHEN is_late = 0 THEN review_score END), 2)
            AS avg_review_when_ontime
    FROM delivery_facts
    GROUP BY customer_state
    HAVING total_orders >= 100
)

SELECT
    state,
    total_orders,
    avg_delivery_days,
    avg_estimated_days,
    avg_days_vs_estimate,
    late_delivery_pct,
    late_orders,
    avg_review_score,
    avg_review_when_late,
    avg_review_when_ontime,
    ROUND(avg_review_when_ontime - avg_review_when_late, 2) AS review_drop_when_late
FROM state_performance
ORDER BY late_delivery_pct DESC;
