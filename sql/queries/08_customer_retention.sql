-- ============================================================
-- BharatCommerce — Query 08: Customer Retention & Cohort Analysis
-- ============================================================
-- Business Question:
--   What's our repeat purchase rate? How long until second
--   purchase? Cohort analysis — are newer cohorts stickier?
--
-- SQL Concepts Used:
--   ✓ Window Function: MIN() OVER() — first purchase per customer
--   ✓ Window Function: ROW_NUMBER() — order sequence per customer
--   ✓ Window Function: LEAD() — time to next purchase
--   ✓ Multiple CTEs — 4 chained steps
--   ✓ Date arithmetic — month differences
--   ✓ CASE WHEN + pivot — cohort retention matrix
--   ✓ Correlated logic — comparing order dates to cohort date
--
-- IMPORTANT: Uses customer_unique_id for true repeat tracking
-- ============================================================

-- ──────────────────────────────────────────
-- PART A: Repeat Purchase Metrics
-- ──────────────────────────────────────────

WITH customer_orders AS (
    -- Step 1: Get every delivered order per unique customer
    -- Use MIN() OVER() to get first purchase date on every row
    -- Use ROW_NUMBER() to sequence their orders
    SELECT
        c.customer_unique_id,
        o.order_id,
        o.order_purchase_timestamp,
        MIN(o.order_purchase_timestamp) OVER (
            PARTITION BY c.customer_unique_id
        ) AS first_purchase_date,
        ROW_NUMBER() OVER (
            PARTITION BY c.customer_unique_id
            ORDER BY o.order_purchase_timestamp
        ) AS order_sequence,
        -- LEAD() looks at the NEXT row's value
        -- Gives us the next purchase date for this customer
        LEAD(o.order_purchase_timestamp) OVER (
            PARTITION BY c.customer_unique_id
            ORDER BY o.order_purchase_timestamp
        ) AS next_purchase_date
    FROM customers c
    JOIN orders o ON c.customer_id = o.customer_id
    WHERE o.order_status = 'delivered'
),

repeat_metrics AS (
    -- Step 2: Calculate repeat purchase stats
    SELECT
        customer_unique_id,
        MAX(order_sequence) AS total_orders,
        first_purchase_date,
        -- Days until second purchase (only for customers who bought again)
        CASE
            WHEN MAX(order_sequence) >= 2 THEN
                CAST(julianday(
                    MIN(CASE WHEN order_sequence = 2
                        THEN order_purchase_timestamp END)
                ) - julianday(first_purchase_date) AS INTEGER)
        END AS days_to_second_purchase
    FROM customer_orders
    GROUP BY customer_unique_id, first_purchase_date
)

SELECT
    -- Overall repeat rate
    COUNT(*) AS total_customers,
    SUM(CASE WHEN total_orders > 1 THEN 1 ELSE 0 END) AS repeat_customers,
    ROUND(
        SUM(CASE WHEN total_orders > 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*),
        2
    ) AS repeat_rate_pct,
    -- Among repeaters, how quickly do they come back?
    ROUND(AVG(days_to_second_purchase), 1) AS avg_days_to_2nd_purchase,
    MIN(days_to_second_purchase) AS min_days_to_2nd,
    MAX(days_to_second_purchase) AS max_days_to_2nd,
    -- Breakdown by order count
    SUM(CASE WHEN total_orders = 1 THEN 1 ELSE 0 END) AS one_time_buyers,
    SUM(CASE WHEN total_orders = 2 THEN 1 ELSE 0 END) AS two_time_buyers,
    SUM(CASE WHEN total_orders = 3 THEN 1 ELSE 0 END) AS three_time_buyers,
    SUM(CASE WHEN total_orders >= 4 THEN 1 ELSE 0 END) AS four_plus_buyers
FROM repeat_metrics;
