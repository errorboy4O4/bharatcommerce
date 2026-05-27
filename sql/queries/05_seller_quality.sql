-- ============================================================
-- BharatCommerce — Query 05: Seller Quality Scorecard
-- ============================================================
-- Business Question:
--   Which sellers have the most complaints? Highest cancellation
--   rates? Slowest shipping? Who should be removed from the
--   platform?
--
-- SQL Concepts Used:
--   ✓ Window Function: ROW_NUMBER() — unique ranking
--   ✓ Multiple CTEs — build metrics step by step
--   ✓ CASE WHEN — cancellation and late shipping flags
--   ✓ Multi-table JOIN — 5 tables joined
--   ✓ Correlated subquery — for cancellation rate
--   ✓ HAVING — filter to meaningful sample sizes
--   ✓ Composite scoring — combine multiple metrics
-- ============================================================

WITH seller_delivery AS (
    -- Step 1: Calculate delivery and shipping metrics per seller
    SELECT
        oi.seller_id,
        s.seller_city,
        s.seller_state,
        COUNT(DISTINCT o.order_id) AS total_orders,
        -- Shipping speed: how fast does the seller hand off to carrier?
        ROUND(AVG(
            CAST(julianday(o.order_delivered_carrier_date)
                 - julianday(o.order_purchase_timestamp) AS REAL)
        ), 1) AS avg_days_to_ship,
        -- Delivery time: total days customer waits
        ROUND(AVG(
            CAST(julianday(o.order_delivered_customer_date)
                 - julianday(o.order_purchase_timestamp) AS REAL)
        ), 1) AS avg_delivery_days,
        -- Late delivery rate
        ROUND(
            SUM(CASE
                WHEN julianday(o.order_delivered_customer_date)
                     > julianday(o.order_estimated_delivery_date)
                THEN 1 ELSE 0
            END) * 100.0 / COUNT(*),
            1
        ) AS late_delivery_pct
    FROM order_items oi
    JOIN orders o ON oi.order_id = o.order_id
    JOIN sellers s ON oi.seller_id = s.seller_id
    WHERE o.order_status = 'delivered'
      AND o.order_delivered_customer_date IS NOT NULL
      AND o.order_delivered_carrier_date IS NOT NULL
    GROUP BY oi.seller_id, s.seller_city, s.seller_state
),

seller_reviews AS (
    -- Step 2: Average review score and bad review % per seller
    SELECT
        oi.seller_id,
        ROUND(AVG(r.review_score), 2) AS avg_review_score,
        ROUND(
            SUM(CASE WHEN r.review_score <= 2 THEN 1 ELSE 0 END)
            * 100.0 / COUNT(*),
            1
        ) AS bad_review_pct,
        COUNT(*) AS total_reviews
    FROM order_items oi
    JOIN orders o ON oi.order_id = o.order_id
    JOIN order_reviews r ON o.order_id = r.order_id
    WHERE o.order_status = 'delivered'
    GROUP BY oi.seller_id
),

seller_cancellations AS (
    -- Step 3: Cancellation rate per seller
    -- This counts ALL orders (not just delivered) to find canceled ones
    SELECT
        oi.seller_id,
        COUNT(DISTINCT o.order_id) AS all_orders,
        SUM(CASE WHEN o.order_status = 'canceled' THEN 1 ELSE 0 END)
            AS canceled_orders,
        ROUND(
            SUM(CASE WHEN o.order_status = 'canceled' THEN 1 ELSE 0 END)
            * 100.0 / COUNT(DISTINCT o.order_id),
            1
        ) AS cancellation_pct
    FROM order_items oi
    JOIN orders o ON oi.order_id = o.order_id
    GROUP BY oi.seller_id
),

seller_revenue AS (
    -- Step 4: Revenue per seller
    SELECT
        oi.seller_id,
        ROUND(SUM(oi.price + oi.freight_value), 2) AS total_revenue,
        ROUND(AVG(oi.price), 2) AS avg_item_price,
        COUNT(DISTINCT oi.product_id) AS unique_products
    FROM order_items oi
    JOIN orders o ON oi.order_id = o.order_id
    WHERE o.order_status = 'delivered'
    GROUP BY oi.seller_id
),

seller_scorecard AS (
    -- Step 5: Combine all metrics into one scorecard
    SELECT
        sd.seller_id,
        sd.seller_city,
        sd.seller_state,
        sd.total_orders,
        sr.total_revenue,
        sr.avg_item_price,
        sr.unique_products,
        sd.avg_days_to_ship,
        sd.avg_delivery_days,
        sd.late_delivery_pct,
        COALESCE(rv.avg_review_score, 0) AS avg_review_score,
        COALESCE(rv.bad_review_pct, 0) AS bad_review_pct,
        COALESCE(sc.cancellation_pct, 0) AS cancellation_pct,
        -- Quality score: weighted composite (lower = worse)
        -- Penalize: low reviews, high late %, high cancellation %
        ROUND(
            COALESCE(rv.avg_review_score, 0) * 20       -- 0-100 from reviews
            - sd.late_delivery_pct * 0.5                 -- penalty for late
            - COALESCE(sc.cancellation_pct, 0) * 1.0    -- penalty for cancels
            - COALESCE(rv.bad_review_pct, 0) * 0.3,     -- penalty for bad reviews
            1
        ) AS quality_score
    FROM seller_delivery sd
    JOIN seller_revenue sr ON sd.seller_id = sr.seller_id
    LEFT JOIN seller_reviews rv ON sd.seller_id = rv.seller_id
    LEFT JOIN seller_cancellations sc ON sd.seller_id = sc.seller_id
    WHERE sd.total_orders >= 10
)

-- Step 6: Rank sellers and flag bottom performers
SELECT
    ROW_NUMBER() OVER (ORDER BY quality_score ASC) AS worst_rank,
    seller_id,
    seller_city,
    seller_state,
    total_orders,
    total_revenue,
    avg_days_to_ship,
    late_delivery_pct,
    avg_review_score,
    bad_review_pct,
    cancellation_pct,
    quality_score,
    CASE
        WHEN quality_score < 30 THEN 'REMOVE — Critical issues'
        WHEN quality_score < 50 THEN 'WARNING — Needs improvement'
        WHEN quality_score < 70 THEN 'MONITOR — Below average'
        ELSE 'GOOD'
    END AS action_flag
FROM seller_scorecard
ORDER BY quality_score ASC;
