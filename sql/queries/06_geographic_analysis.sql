-- ============================================================
-- BharatCommerce — Query 06: Geographic Analysis
-- ============================================================
-- Business Question:
--   Revenue by state? Where are the underserved markets with
--   growth potential? Which states punch above/below their
--   weight in revenue vs order volume?
--
-- SQL Concepts Used:
--   ✓ Scalar subquery in SELECT — inline calculations
--   ✓ Window Function: SUM() OVER() — percentage of total
--   ✓ Window Function: RANK() — state rankings
--   ✓ Multiple CTEs — layered analysis
--   ✓ Multi-table JOIN — orders + order_items + customers + sellers
--   ✓ CASE WHEN — market tier classification
--   ✓ ROUND, CAST — clean output
-- ============================================================

WITH state_orders AS (
    -- Step 1: Revenue and order metrics per customer state
    SELECT
        c.customer_state AS state,
        COUNT(DISTINCT o.order_id) AS total_orders,
        COUNT(DISTINCT c.customer_unique_id) AS unique_customers,
        ROUND(SUM(oi.price + oi.freight_value), 2) AS total_revenue,
        ROUND(AVG(oi.price + oi.freight_value), 2) AS avg_order_item_value,
        ROUND(AVG(r.review_score), 2) AS avg_review_score,
        ROUND(AVG(
            CAST(julianday(o.order_delivered_customer_date)
                 - julianday(o.order_purchase_timestamp) AS REAL)
        ), 1) AS avg_delivery_days
    FROM orders o
    JOIN customers c ON o.customer_id = c.customer_id
    JOIN order_items oi ON o.order_id = oi.order_id
    LEFT JOIN order_reviews r ON o.order_id = r.order_id
    WHERE o.order_status = 'delivered'
      AND o.order_delivered_customer_date IS NOT NULL
    GROUP BY c.customer_state
),

state_sellers AS (
    -- Step 2: Count sellers per state (supply side)
    SELECT
        s.seller_state AS state,
        COUNT(DISTINCT s.seller_id) AS seller_count
    FROM sellers s
    GROUP BY s.seller_state
),

state_analysis AS (
    -- Step 3: Combine demand + supply and calculate shares
    SELECT
        so.state,
        so.total_orders,
        so.unique_customers,
        so.total_revenue,
        so.avg_order_item_value,
        so.avg_review_score,
        so.avg_delivery_days,
        COALESCE(ss.seller_count, 0) AS seller_count,

        -- Percentage of total (using window functions)
        ROUND(so.total_revenue * 100.0
              / SUM(so.total_revenue) OVER (), 2) AS pct_revenue,
        ROUND(so.total_orders * 100.0
              / SUM(so.total_orders) OVER (), 2) AS pct_orders,
        ROUND(so.unique_customers * 100.0
              / SUM(so.unique_customers) OVER (), 2) AS pct_customers,

        -- Revenue per customer (spending intensity)
        ROUND(so.total_revenue / so.unique_customers, 2) AS revenue_per_customer,

        -- Customers per seller ratio (market saturation)
        -- High ratio = many buyers, few sellers = opportunity
        CASE
            WHEN COALESCE(ss.seller_count, 0) > 0
            THEN ROUND(so.unique_customers * 1.0 / ss.seller_count, 1)
            ELSE NULL
        END AS customers_per_seller,

        -- Rankings
        RANK() OVER (ORDER BY so.total_revenue DESC) AS revenue_rank,
        RANK() OVER (ORDER BY so.unique_customers DESC) AS customer_rank

    FROM state_orders so
    LEFT JOIN state_sellers ss ON so.state = ss.state
)

-- Step 4: Final output with market tier and opportunity flag
SELECT
    state,
    revenue_rank,
    total_orders,
    unique_customers,
    total_revenue,
    pct_revenue,
    avg_order_item_value,
    revenue_per_customer,
    seller_count,
    customers_per_seller,
    avg_delivery_days,
    avg_review_score,

    -- Market tier based on revenue
    CASE
        WHEN pct_revenue >= 10 THEN 'Tier 1 — Core Market'
        WHEN pct_revenue >= 3  THEN 'Tier 2 — Growth Market'
        WHEN pct_revenue >= 1  THEN 'Tier 3 — Emerging Market'
        ELSE 'Tier 4 — Frontier Market'
    END AS market_tier,

    -- Opportunity flag: high customer-to-seller ratio means
    -- demand outpaces supply — room for more sellers
    CASE
        WHEN customers_per_seller > 100 AND pct_revenue >= 1
            THEN 'HIGH OPPORTUNITY — Needs more sellers'
        WHEN customers_per_seller > 50 AND pct_revenue >= 0.5
            THEN 'MODERATE OPPORTUNITY — Growing demand'
        WHEN avg_delivery_days > 20
            THEN 'LOGISTICS GAP — Slow deliveries hurting growth'
        ELSE 'STABLE'
    END AS opportunity_flag

FROM state_analysis
ORDER BY total_revenue DESC;
