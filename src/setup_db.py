"""
BharatCommerce — Database Setup
Loads 8 Olist CSV files into a single SQLite database.

Usage:
  1. Download dataset from: https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce
  2. Extract all CSVs into data/raw/
  3. Run: python src/setup_db.py

The script will:
  - Create bharatcommerce.db in data/
  - Create typed tables (not just text columns)
  - Merge Portuguese product category names with English translations
  - Print row counts and sample data for verification
"""

import sqlite3
import pandas as pd
import os
import sys

# ── Paths ────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(BASE_DIR, "data", "raw")
DB_PATH = os.path.join(BASE_DIR, "data", "bharatcommerce.db")


# ── Table Definitions ────────────────────────────────────────────────
# Each entry: (csv_filename, table_name, SQL CREATE statement)
# We define explicit types so SQL queries behave correctly (dates, numbers).

TABLES = [
    (
        "olist_customers_dataset.csv",
        "customers",
        """
        CREATE TABLE IF NOT EXISTS customers (
            customer_id TEXT PRIMARY KEY,
            customer_unique_id TEXT,
            customer_zip_code_prefix TEXT,
            customer_city TEXT,
            customer_state TEXT
        )
        """
    ),
    (
        "olist_orders_dataset.csv",
        "orders",
        """
        CREATE TABLE IF NOT EXISTS orders (
            order_id TEXT PRIMARY KEY,
            customer_id TEXT,
            order_status TEXT,
            order_purchase_timestamp TEXT,
            order_approved_at TEXT,
            order_delivered_carrier_date TEXT,
            order_delivered_customer_date TEXT,
            order_estimated_delivery_date TEXT,
            FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
        )
        """
    ),
    (
        "olist_order_items_dataset.csv",
        "order_items",
        """
        CREATE TABLE IF NOT EXISTS order_items (
            order_id TEXT,
            order_item_id INTEGER,
            product_id TEXT,
            seller_id TEXT,
            shipping_limit_date TEXT,
            price REAL,
            freight_value REAL,
            PRIMARY KEY (order_id, order_item_id),
            FOREIGN KEY (order_id) REFERENCES orders(order_id),
            FOREIGN KEY (product_id) REFERENCES products(product_id),
            FOREIGN KEY (seller_id) REFERENCES sellers(seller_id)
        )
        """
    ),
    (
        "olist_order_payments_dataset.csv",
        "order_payments",
        """
        CREATE TABLE IF NOT EXISTS order_payments (
            order_id TEXT,
            payment_sequential INTEGER,
            payment_type TEXT,
            payment_installments INTEGER,
            payment_value REAL,
            FOREIGN KEY (order_id) REFERENCES orders(order_id)
        )
        """
    ),
    (
        "olist_order_reviews_dataset.csv",
        "order_reviews",
        """
        CREATE TABLE IF NOT EXISTS order_reviews (
            review_id TEXT,
            order_id TEXT,
            review_score INTEGER,
            review_comment_title TEXT,
            review_comment_message TEXT,
            review_creation_date TEXT,
            review_answer_timestamp TEXT,
            FOREIGN KEY (order_id) REFERENCES orders(order_id)
        )
        """
    ),
    (
        "olist_products_dataset.csv",
        "products",
        """
        CREATE TABLE IF NOT EXISTS products (
            product_id TEXT PRIMARY KEY,
            product_category_name TEXT,
            product_category_name_english TEXT,
            product_name_lenght REAL,
            product_description_lenght REAL,
            product_photos_qty REAL,
            product_weight_g REAL,
            product_length_cm REAL,
            product_height_cm REAL,
            product_width_cm REAL
        )
        """
    ),
    (
        "olist_sellers_dataset.csv",
        "sellers",
        """
        CREATE TABLE IF NOT EXISTS sellers (
            seller_id TEXT PRIMARY KEY,
            seller_zip_code_prefix TEXT,
            seller_city TEXT,
            seller_state TEXT
        )
        """
    ),
    (
        "olist_geolocation_dataset.csv",
        "geolocation",
        """
        CREATE TABLE IF NOT EXISTS geolocation (
            geolocation_zip_code_prefix TEXT,
            geolocation_lat REAL,
            geolocation_lng REAL,
            geolocation_city TEXT,
            geolocation_state TEXT
        )
        """
    ),
]


def check_csv_files():
    """Verify all required CSVs exist in data/raw/."""
    missing = []
    for csv_file, _, _ in TABLES:
        path = os.path.join(RAW_DIR, csv_file)
        if not os.path.exists(path):
            missing.append(csv_file)

    # Also check for translation file
    trans_path = os.path.join(RAW_DIR, "product_category_name_translation.csv")
    if not os.path.exists(trans_path):
        missing.append("product_category_name_translation.csv")

    return missing


def load_products_with_translation(raw_dir):
    """
    Load products CSV and merge with English category name translations.
    This is done BEFORE inserting into the DB so the products table
    has both Portuguese and English category names.
    """
    products_path = os.path.join(raw_dir, "olist_products_dataset.csv")
    translation_path = os.path.join(raw_dir, "product_category_name_translation.csv")

    products = pd.read_csv(products_path)
    translation = pd.read_csv(translation_path)

    # Merge: add English name column
    products = products.merge(
        translation,
        on="product_category_name",
        how="left"
    )

    print(f"  Products: {len(products)} rows")
    print(f"  Categories translated: {products['product_category_name_english'].notna().sum()}/{len(products)}")

    untranslated = products[products["product_category_name_english"].isna()]["product_category_name"].unique()
    if len(untranslated) > 0:
        print(f"  ⚠ Untranslated categories ({len(untranslated)}): {list(untranslated)[:5]}")

    return products


def build_database():
    """Main function: create SQLite DB and load all tables."""

    print("=" * 60)
    print("BharatCommerce — Database Setup")
    print("=" * 60)

    # Step 1: Check CSVs exist
    print("\n[1/4] Checking CSV files...")
    missing = check_csv_files()
    if missing:
        print(f"\n❌ Missing files in {RAW_DIR}:")
        for f in missing:
            print(f"   - {f}")
        print(f"\nDownload from: https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce")
        print(f"Extract all CSVs into: {RAW_DIR}")
        sys.exit(1)
    print("  ✓ All 9 CSV files found")

    # Step 2: Delete old DB if exists
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print(f"\n  Removed old database")

    # Step 3: Create tables and load data
    print("\n[2/4] Creating database and loading tables...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Enable foreign keys
    cursor.execute("PRAGMA foreign_keys = ON;")

    for csv_file, table_name, create_sql in TABLES:
        # Create table
        cursor.execute(create_sql)

        # Load data
        csv_path = os.path.join(RAW_DIR, csv_file)

        if table_name == "products":
            # Special handling: merge with translation first
            df = load_products_with_translation(RAW_DIR)
        else:
            df = pd.read_csv(csv_path)

        # Insert into DB
        df.to_sql(table_name, conn, if_exists="replace", index=False)
        print(f"  ✓ {table_name}: {len(df):,} rows loaded")

    conn.commit()

    # Step 4: Verify with counts and samples
    print("\n[3/4] Verifying data...")
    print("-" * 50)

    for _, table_name, _ in TABLES:
        count = cursor.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        sample = cursor.execute(f"SELECT * FROM {table_name} LIMIT 1").fetchone()
        cols = [desc[0] for desc in cursor.description]
        print(f"\n  {table_name}: {count:,} rows, {len(cols)} columns")
        print(f"  Columns: {', '.join(cols)}")

    # Step 5: Quick sanity checks
    print("\n[4/4] Sanity checks...")

    # Check date range
    date_range = cursor.execute("""
        SELECT
            MIN(order_purchase_timestamp) as first_order,
            MAX(order_purchase_timestamp) as last_order
        FROM orders
        WHERE order_status = 'delivered'
    """).fetchone()
    print(f"  Order date range: {date_range[0][:10]} to {date_range[1][:10]}")

    # Check order statuses
    statuses = cursor.execute("""
        SELECT order_status, COUNT(*) as cnt
        FROM orders
        GROUP BY order_status
        ORDER BY cnt DESC
    """).fetchall()
    print(f"  Order statuses: {dict(statuses)}")

    # Check payment types
    payments = cursor.execute("""
        SELECT payment_type, COUNT(*) as cnt
        FROM order_payments
        GROUP BY payment_type
        ORDER BY cnt DESC
    """).fetchall()
    print(f"  Payment types: {dict(payments)}")

    # Check review score distribution
    reviews = cursor.execute("""
        SELECT review_score, COUNT(*) as cnt
        FROM order_reviews
        GROUP BY review_score
        ORDER BY review_score
    """).fetchall()
    print(f"  Review scores: {dict(reviews)}")

    # DB file size
    db_size = os.path.getsize(DB_PATH) / (1024 * 1024)
    print(f"\n  Database size: {db_size:.1f} MB")
    print(f"  Database path: {DB_PATH}")

    conn.close()

    print("\n" + "=" * 60)
    print("✅ Database ready! You can now write SQL queries against it.")
    print("=" * 60)


if __name__ == "__main__":
    build_database()
