-- ============================================================
-- BharatCommerce — Query 09: Revenue Concentration Risk
-- ============================================================
-- Business Question:
--   What % of revenue comes from top 10% of sellers/customers?
--   How dangerous is this concentration? What happens if we
--   lose our top sellers?
--
-- SQL Concepts Used:
--   ✓ Window Frame: SUM() OVER (ROWS BETWEEN ... AND ...)
--   ✓ Window Function: PERCENT_RANK() — percentile position
--   ✓ Window Function: NTILE() — bucket into deciles
--   ✓ Multiple CTEs — seller + customer concentration
--   ✓ Cumulative distribution — running % of total
--   ✓ CASE WHEN — risk tier labeling
-- ============================================================

-- ──────────────────────────────────────────
-- PART A: Seller Revenue Concentration
-- ──────────────────────────────────────────

WITH seller_revenue AS (
    -- Step 1: Total revenue per seller
    SELECT
        oi.seller_id,
        s.seller_state,
        COUNT(DISTINCT o.order_id) AS total_orders,
        ROUND(SUM(oi.price + oi.freight_value), 2) AS revenue
    FROM order_items oi
    JOIN orders o ON oi.order_id = o.order_id
    JOIN sellers s ON oi.seller_id = s.seller_id
    WHERE o.order_status = 'delivered'
    GROUP BY oi.seller_id, s.seller_state
),

seller_ranked AS (
    -- Step 2: Rank sellers and calculate cumulative revenue
    SELECT
        seller_id,
        seller_state,
        total_orders,
        revenue,
        -- What percentile is this seller in? (0 = bottom, 1 = top)
        PERCENT_RANK() OVER (ORDER BY revenue ASC) AS percentile,
        -- Row number for position tracking
        ROW_NUMBER() OVER (ORDER BY revenue DESC) AS rank_position,
        -- Total number of sellers
        COUNT(*) OVER () AS total_sellers,
        -- Cumulative revenue from top down
        SUM(revenue) OVER (
            ORDER BY revenue DESC
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS cumulative_revenue,
        -- Grand total for percentage calculation
        SUM(revenue) OVER () AS grand_total
    FROM seller_revenue
),

seller_concentration AS (
    -- Step 3: Calculate cumulative percentage
    SELECT
        seller_id,
        seller_state,
        total_orders,
        revenue,
        rank_position,
        total_sellers,
        ROUND(percentile * 100, 1) AS percentile_pct,
        ROUND(cumulative_revenue * 100.0 / grand_total, 2) AS cumulative_revenue_pct,
        ROUND(rank_position * 100.0 / total_sellers, 2) AS pct_of_sellers
    FROM seller_ranked
)

-- Step 4: Show concentration at key thresholds
SELECT
    'Sellers' AS entity_type,
    -- Top 1% of sellers
    MAX(CASE
        WHEN pct_of_sellers <= 1 THEN cumulative_revenue_pct
    END) AS top_1_pct_revenue,
    -- Top 5% of sellers
    MAX(CASE
        WHEN pct_of_sellers <= 5 THEN cumulative_revenue_pct
    END) AS top_5_pct_revenue,
    -- Top 10% of sellers
    MAX(CASE
        WHEN pct_of_sellers <= 10 THEN cumulative_revenue_pct
    END) AS top_10_pct_revenue,
    -- Top 20% of sellers (classic Pareto threshold)
    MAX(CASE
        WHEN pct_of_sellers <= 20 THEN cumulative_revenue_pct
    END) AS top_20_pct_revenue,
    -- Top 50%
    MAX(CASE
        WHEN pct_of_sellers <= 50 THEN cumulative_revenue_pct
    END) AS top_50_pct_revenue,
    total_sellers AS total_entities
FROM seller_concentration
GROUP BY total_sellers

UNION ALL

-- ──────────────────────────────────────────
-- PART B: Customer Revenue Concentration
-- ──────────────────────────────────────────

SELECT
    'Customers' AS entity_type,
    MAX(CASE WHEN pct_of_customers <= 1 THEN cum_rev_pct END),
    MAX(CASE WHEN pct_of_customers <= 5 THEN cum_rev_pct END),
    MAX(CASE WHEN pct_of_customers <= 10 THEN cum_rev_pct END),
    MAX(CASE WHEN pct_of_customers <= 20 THEN cum_rev_pct END),
    MAX(CASE WHEN pct_of_customers <= 50 THEN cum_rev_pct END),
    total_customers
FROM (
    SELECT
        customer_unique_id,
        revenue,
        ROW_NUMBER() OVER (ORDER BY revenue DESC) AS rank_pos,
        COUNT(*) OVER () AS total_customers,
        ROUND(
            ROW_NUMBER() OVER (ORDER BY revenue DESC)
            * 100.0 / COUNT(*) OVER (),
            2
        ) AS pct_of_customers,
        ROUND(
            SUM(revenue) OVER (
                ORDER BY revenue DESC
                ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
            ) * 100.0 / SUM(revenue) OVER (),
            2
        ) AS cum_rev_pct
    FROM (
        SELECT
            c.customer_unique_id,
            ROUND(SUM(oi.price + oi.freight_value), 2) AS revenue
        FROM customers c
        JOIN orders o ON c.customer_id = o.customer_id
        JOIN order_items oi ON o.order_id = oi.order_id
        WHERE o.order_status = 'delivered'
        GROUP BY c.customer_unique_id
    )
)
GROUP BY total_customers;
