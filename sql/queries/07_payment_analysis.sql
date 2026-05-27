-- ============================================================
-- BharatCommerce — Query 07: Payment Analysis
-- ============================================================
-- Business Question:
--   What payment methods are most popular? How do installments
--   affect order value? Which payment types correlate with
--   higher spending and better reviews?
--
-- SQL Concepts Used:
--   ✓ Pivot-style aggregation — CASE WHEN to turn rows into columns
--   ✓ CTE — multi-step analysis
--   ✓ Window Function: PERCENT_RANK() — percentile positioning
--   ✓ Multi-table JOIN — orders + payments + reviews
--   ✓ GROUP BY with multiple aggregations
--   ✓ HAVING — filter meaningful groups
--   ✓ Subquery — for installment bucketing
-- ============================================================

-- ──────────────────────────────────────────
-- PART A: Payment Method Overview
-- ──────────────────────────────────────────

WITH payment_overview AS (
    -- Step 1: Metrics per payment type
    SELECT
        p.payment_type,
        COUNT(*) AS total_payments,
        COUNT(DISTINCT p.order_id) AS total_orders,
        ROUND(SUM(p.payment_value), 2) AS total_value,
        ROUND(AVG(p.payment_value), 2) AS avg_payment_value,
        ROUND(AVG(p.payment_installments), 1) AS avg_installments,
        MAX(p.payment_installments) AS max_installments,
        -- What % of payments use installments (>1)?
        ROUND(
            SUM(CASE WHEN p.payment_installments > 1 THEN 1 ELSE 0 END)
            * 100.0 / COUNT(*),
            1
        ) AS pct_using_installments
    FROM order_payments p
    JOIN orders o ON p.order_id = o.order_id
    WHERE o.order_status = 'delivered'
    GROUP BY p.payment_type
)

SELECT
    payment_type,
    total_payments,
    total_orders,
    total_value,
    avg_payment_value,
    -- Share of total revenue
    ROUND(total_value * 100.0 / SUM(total_value) OVER (), 1) AS pct_revenue,
    avg_installments,
    max_installments,
    pct_using_installments
FROM payment_overview
ORDER BY total_value DESC;
