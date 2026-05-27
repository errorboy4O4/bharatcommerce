-- ============================================================
-- BharatCommerce — Query 02: RFM Customer Segmentation
-- ============================================================
-- Business Question:
--   Who are our best customers? Who is about to churn?
--   Segment all customers by Recency, Frequency, Monetary value.
--
-- SQL Concepts Used:
--   ✓ Multiple CTEs — 3 chained steps
--   ✓ Window Function: NTILE() — split into quintiles
--   ✓ CASE WHEN — complex segmentation logic
--   ✓ Multi-table JOIN — orders + order_items + customers
--   ✓ Aggregation — COUNT(DISTINCT), SUM, julianday()
--   ✓ Subquery — reference date for recency calculation
--
-- IMPORTANT: We use customer_unique_id, NOT customer_id.
--   The same person can have multiple customer_id values
--   across different orders. customer_unique_id is the
--   true unique identifier for a person.
-- ============================================================

WITH rfm_raw AS (
    -- Step 1: Calculate raw R, F, M values per customer
    -- Recency  = days since last purchase (from the dataset's max date)
    -- Frequency = number of distinct orders
    -- Monetary  = total amount spent (price + freight)
    SELECT
        c.customer_unique_id,
        CAST(
            julianday((SELECT MAX(order_purchase_timestamp) FROM orders))
            - julianday(MAX(o.order_purchase_timestamp))
        AS INTEGER) AS recency_days,
        COUNT(DISTINCT o.order_id) AS frequency,
        ROUND(SUM(oi.price + oi.freight_value), 2) AS monetary
    FROM customers c
    JOIN orders o ON c.customer_id = o.customer_id
    JOIN order_items oi ON o.order_id = oi.order_id
    WHERE o.order_status = 'delivered'
    GROUP BY c.customer_unique_id
),

rfm_scores AS (
    -- Step 2: Score each dimension 1-5 using NTILE
    -- Recency: ORDER BY DESC because MORE days = WORSE (score 1)
    -- Frequency: ORDER BY ASC because MORE orders = BETTER (score 5)
    -- Monetary: ORDER BY ASC because MORE spend = BETTER (score 5)
    SELECT
        customer_unique_id,
        recency_days,
        frequency,
        monetary,
        NTILE(5) OVER (ORDER BY recency_days DESC) AS r_score,
        NTILE(5) OVER (ORDER BY frequency ASC) AS f_score,
        NTILE(5) OVER (ORDER BY monetary ASC) AS m_score
    FROM rfm_raw
)

-- Step 3: Assign business segments based on score combinations
SELECT
    customer_unique_id,
    recency_days,
    frequency,
    monetary,
    r_score,
    f_score,
    m_score,
    CASE
        -- Champions: bought recently, buy often, spend a lot
        WHEN r_score >= 4 AND f_score >= 4 AND m_score >= 4
            THEN 'Champions'

        -- Loyal Customers: good across all dimensions
        WHEN r_score >= 3 AND f_score >= 3 AND m_score >= 3
            THEN 'Loyal Customers'

        -- Potential Loyalists: recent buyers with decent spend but low frequency
        WHEN r_score >= 4 AND f_score <= 2 AND m_score >= 3
            THEN 'Potential Loyalists'

        -- New Customers: very recent, first purchase
        WHEN r_score >= 4 AND f_score = 1
            THEN 'New Customers'

        -- At Risk: were good customers, haven't bought recently
        WHEN r_score <= 2 AND f_score >= 3 AND m_score >= 3
            THEN 'At Risk'

        -- Can't Lose Them: used to spend big, disappearing
        WHEN r_score <= 2 AND f_score >= 4 AND m_score >= 4
            THEN 'Cant Lose Them'

        -- Hibernating: low on everything
        WHEN r_score <= 2 AND f_score <= 2 AND m_score <= 2
            THEN 'Hibernating'

        -- Need Attention: middle of the road, could go either way
        WHEN r_score = 3 AND f_score >= 2 AND m_score >= 2
            THEN 'Need Attention'

        -- About to Sleep: below average recency, low engagement
        WHEN r_score <= 2 AND f_score <= 2
            THEN 'About to Sleep'

        -- Everyone else
        ELSE 'Others'
    END AS segment
FROM rfm_scores
ORDER BY monetary DESC;
