-- ============================================================
-- BharatCommerce — Database Schema
-- Source: Olist Brazilian E-Commerce Dataset (Kaggle)
-- Database: SQLite
-- ============================================================

-- Customers: one row per customer
CREATE TABLE IF NOT EXISTS customers (
    customer_id TEXT PRIMARY KEY,
    customer_unique_id TEXT,           -- same person can have multiple customer_ids
    customer_zip_code_prefix TEXT,
    customer_city TEXT,
    customer_state TEXT                -- 2-letter state code (e.g., SP, RJ, MG)
);

-- Orders: one row per order
CREATE TABLE IF NOT EXISTS orders (
    order_id TEXT PRIMARY KEY,
    customer_id TEXT,
    order_status TEXT,                 -- delivered, shipped, canceled, etc.
    order_purchase_timestamp TEXT,     -- when customer placed order
    order_approved_at TEXT,            -- when payment was approved
    order_delivered_carrier_date TEXT, -- when seller handed to carrier
    order_delivered_customer_date TEXT,-- when customer received it
    order_estimated_delivery_date TEXT,-- promised delivery date
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);

-- Order Items: one row per item in an order (an order can have multiple items)
CREATE TABLE IF NOT EXISTS order_items (
    order_id TEXT,
    order_item_id INTEGER,            -- 1, 2, 3... for items within same order
    product_id TEXT,
    seller_id TEXT,
    shipping_limit_date TEXT,
    price REAL,                       -- item price in BRL
    freight_value REAL,               -- shipping cost for this item in BRL
    PRIMARY KEY (order_id, order_item_id),
    FOREIGN KEY (order_id) REFERENCES orders(order_id),
    FOREIGN KEY (product_id) REFERENCES products(product_id),
    FOREIGN KEY (seller_id) REFERENCES sellers(seller_id)
);

-- Payments: one row per payment (an order can be split across multiple payments)
CREATE TABLE IF NOT EXISTS order_payments (
    order_id TEXT,
    payment_sequential INTEGER,       -- 1, 2, 3... for multiple payment methods
    payment_type TEXT,                 -- credit_card, boleto, voucher, debit_card
    payment_installments INTEGER,     -- number of installments (credit card)
    payment_value REAL,               -- amount paid in BRL
    FOREIGN KEY (order_id) REFERENCES orders(order_id)
);

-- Reviews: one review per order
CREATE TABLE IF NOT EXISTS order_reviews (
    review_id TEXT,
    order_id TEXT,
    review_score INTEGER,             -- 1 to 5 stars
    review_comment_title TEXT,
    review_comment_message TEXT,
    review_creation_date TEXT,
    review_answer_timestamp TEXT,
    FOREIGN KEY (order_id) REFERENCES orders(order_id)
);

-- Products: one row per product
CREATE TABLE IF NOT EXISTS products (
    product_id TEXT PRIMARY KEY,
    product_category_name TEXT,              -- Portuguese
    product_category_name_english TEXT,      -- English (merged from translation CSV)
    product_name_lenght REAL,               -- yes, "lenght" is a typo in the dataset
    product_description_lenght REAL,
    product_photos_qty REAL,
    product_weight_g REAL,
    product_length_cm REAL,
    product_height_cm REAL,
    product_width_cm REAL
);

-- Sellers: one row per seller
CREATE TABLE IF NOT EXISTS sellers (
    seller_id TEXT PRIMARY KEY,
    seller_zip_code_prefix TEXT,
    seller_city TEXT,
    seller_state TEXT
);

-- Geolocation: zip code to lat/lng mapping (has duplicates per zip)
CREATE TABLE IF NOT EXISTS geolocation (
    geolocation_zip_code_prefix TEXT,
    geolocation_lat REAL,
    geolocation_lng REAL,
    geolocation_city TEXT,
    geolocation_state TEXT
);


-- ============================================================
-- KEY RELATIONSHIPS (for JOIN queries)
-- ============================================================
-- orders.customer_id        → customers.customer_id
-- order_items.order_id      → orders.order_id
-- order_items.product_id    → products.product_id
-- order_items.seller_id     → sellers.seller_id
-- order_payments.order_id   → orders.order_id
-- order_reviews.order_id    → orders.order_id
--
-- IMPORTANT: customers.customer_unique_id is the TRUE unique customer.
-- The same person can appear with different customer_id values across
-- different orders. For repeat purchase analysis, always use
-- customer_unique_id, not customer_id.
-- ============================================================
