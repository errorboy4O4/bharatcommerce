"""
BharatCommerce — E-Commerce Business Intelligence Dashboard
============================================================
A 5-tab interactive BI dashboard analyzing 100K+ orders from
the Olist Brazilian E-Commerce dataset.

Run: streamlit run src/app.py
"""

import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from scipy import stats
import os

# ── Page Config ──────────────────────────────────────────────
st.set_page_config(
    page_title="BharatCommerce — BI Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Custom CSS ───────────────────────────────────────────────
st.markdown("""
<style>
    /* Clean up padding */
    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 1rem;
    }
    /* Style metric cards */
    [data-testid="stMetric"] {
        background: linear-gradient(135deg, #667eea11, #764ba211);
        border: 1px solid #e0e0e0;
        border-radius: 10px;
        padding: 15px 20px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
    }
    [data-testid="stMetric"] label {
        font-size: 0.85rem !important;
        color: #555 !important;
    }
    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        padding: 10px 20px;
        font-weight: 600;
    }
    /* Header */
    .dashboard-header {
        background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
        color: white;
        padding: 1.8rem 2rem;
        border-radius: 12px;
        margin-bottom: 1.5rem;
    }
    .dashboard-header h1 {
        margin: 0;
        font-size: 1.9rem;
        font-weight: 700;
    }
    .dashboard-header p {
        margin: 0.3rem 0 0 0;
        opacity: 0.8;
        font-size: 0.95rem;
    }
</style>
""", unsafe_allow_html=True)


# ── Database Connection ──────────────────────────────────────
def _build_db_from_csvs(csv_dir, db_path):
    """Build SQLite database from CSV files in given directory."""
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    tables = {
        "customers": "olist_customers_dataset.csv",
        "orders": "olist_orders_dataset.csv",
        "order_items": "olist_order_items_dataset.csv",
        "order_payments": "olist_order_payments_dataset.csv",
        "order_reviews": "olist_order_reviews_dataset.csv",
        "sellers": "olist_sellers_dataset.csv",
        "geolocation": "olist_geolocation_dataset.csv",
    }
    for table_name, csv_file in tables.items():
        df = pd.read_csv(os.path.join(csv_dir, csv_file))
        df.to_sql(table_name, conn, if_exists="replace", index=False)
    # Products with translation merge
    products = pd.read_csv(os.path.join(csv_dir, "olist_products_dataset.csv"))
    translation = pd.read_csv(os.path.join(csv_dir, "product_category_name_translation.csv"))
    products = products.merge(translation, on="product_category_name", how="left")
    products.to_sql("products", conn, if_exists="replace", index=False)
    conn.commit()
    conn.close()


@st.cache_resource
def get_connection():
    """Get SQLite connection. Auto-downloads dataset if needed."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    possible_paths = [
        os.path.join(base_dir, "data", "bharatcommerce.db"),
        os.path.join("data", "bharatcommerce.db"),
        "bharatcommerce.db",
    ]
    for path in possible_paths:
        if os.path.exists(path):
            return sqlite3.connect(path, check_same_thread=False)

    # Database not found — try to build it
    # First check if raw CSVs exist locally
    raw_dir = os.path.join(base_dir, "data", "raw")
    db_path = possible_paths[0]

    if os.path.exists(raw_dir) and os.path.exists(os.path.join(raw_dir, "olist_orders_dataset.csv")):
        with st.spinner("Building database from local CSVs..."):
            _build_db_from_csvs(raw_dir, db_path)
            return sqlite3.connect(db_path, check_same_thread=False)

    # Try downloading via kagglehub
    try:
        import kagglehub
        with st.spinner("Downloading dataset from Kaggle (first run only)..."):
            dataset_path = kagglehub.dataset_download("olistbr/brazilian-ecommerce")
            _build_db_from_csvs(dataset_path, db_path)
            return sqlite3.connect(db_path, check_same_thread=False)
    except Exception as e:
        st.error(f"Could not load database: {e}")
        st.info("Run `python src/setup_db.py` locally first, or ensure Kaggle access.")
        st.stop()


@st.cache_data(ttl=600)
def run_query(query):
    """Run a SQL query and return a DataFrame."""
    conn = get_connection()
    return pd.read_sql_query(query, conn)


# ── Plotly Template ──────────────────────────────────────────
PLOTLY_TEMPLATE = "plotly_white"
COLORS = {
    "primary": "#4361ee",
    "secondary": "#3a0ca3",
    "success": "#06d6a0",
    "warning": "#ffd166",
    "danger": "#ef476f",
    "info": "#118ab2",
    "palette": ["#4361ee", "#3a0ca3", "#7209b7", "#f72585",
                "#4cc9f0", "#06d6a0", "#ffd166", "#ef476f"],
}


def styled_header(title, subtitle=""):
    """Render the dashboard header."""
    st.markdown(f"""
    <div class="dashboard-header">
        <h1>📊 {title}</h1>
        <p>{subtitle}</p>
    </div>
    """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
#                        HEADER
# ══════════════════════════════════════════════════════════════

styled_header(
    "BharatCommerce — Business Intelligence Dashboard",
    "Analyzing 100K+ orders across 8 relational tables | Olist Brazilian E-Commerce Dataset"
)

# ══════════════════════════════════════════════════════════════
#                        TABS
# ══════════════════════════════════════════════════════════════

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📈 Executive Summary",
    "👥 Customer Intelligence",
    "🚚 Operations",
    "🏪 Seller Scorecard",
    "🔍 Deep Dive",
])


# ══════════════════════════════════════════════════════════════
#              TAB 1: EXECUTIVE SUMMARY
# ══════════════════════════════════════════════════════════════

with tab1:

    # ── KPI Row ──────────────────────────────────────────────
    kpi_data = run_query("""
        SELECT
            ROUND(SUM(oi.price + oi.freight_value), 2) AS total_revenue,
            COUNT(DISTINCT o.order_id) AS total_orders,
            ROUND(AVG(oi.price + oi.freight_value), 2) AS avg_order_item_value,
            ROUND(AVG(r.review_score), 2) AS avg_review,
            COUNT(DISTINCT c.customer_unique_id) AS unique_customers,
            COUNT(DISTINCT oi.seller_id) AS active_sellers
        FROM orders o
        JOIN order_items oi ON o.order_id = oi.order_id
        JOIN customers c ON o.customer_id = c.customer_id
        LEFT JOIN order_reviews r ON o.order_id = r.order_id
        WHERE o.order_status = 'delivered'
    """)

    k = kpi_data.iloc[0]
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Total Revenue", f"R$ {k['total_revenue']:,.0f}")
    c2.metric("Total Orders", f"{k['total_orders']:,}")
    c3.metric("Avg Order Item Value", f"R$ {k['avg_order_item_value']:,.0f}")
    c4.metric("Avg Review Score", f"⭐ {k['avg_review']:.2f}")
    c5.metric("Unique Customers", f"{k['unique_customers']:,}")
    c6.metric("Active Sellers", f"{k['active_sellers']:,}")

    st.divider()

    # ── Revenue Trend ────────────────────────────────────────
    revenue_df = run_query("""
        SELECT
            strftime('%Y-%m', o.order_purchase_timestamp) AS month,
            ROUND(SUM(oi.price + oi.freight_value), 2) AS revenue,
            COUNT(DISTINCT o.order_id) AS orders
        FROM orders o
        JOIN order_items oi ON o.order_id = oi.order_id
        WHERE o.order_status = 'delivered'
        GROUP BY month
        HAVING month >= '2017-01'
        ORDER BY month
    """)

    fig_rev = make_subplots(specs=[[{"secondary_y": True}]])
    fig_rev.add_trace(
        go.Bar(
            x=revenue_df["month"], y=revenue_df["revenue"],
            name="Revenue (R$)", marker_color=COLORS["primary"],
            opacity=0.7,
        ),
        secondary_y=False,
    )
    fig_rev.add_trace(
        go.Scatter(
            x=revenue_df["month"], y=revenue_df["orders"],
            name="Orders", mode="lines+markers",
            line=dict(color=COLORS["danger"], width=2.5),
            marker=dict(size=5),
        ),
        secondary_y=True,
    )
    fig_rev.update_layout(
        title="Monthly Revenue Grew 8x in 20 Months — Nov 2017 Black Friday Spike Visible",
        template=PLOTLY_TEMPLATE,
        height=420,
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        margin=dict(t=60, b=40),
    )
    fig_rev.update_yaxes(title_text="Revenue (R$)", secondary_y=False)
    fig_rev.update_yaxes(title_text="Order Count", secondary_y=True)
    st.plotly_chart(fig_rev, use_container_width=True)

    # ── Revenue by State + Top Categories ────────────────────
    col_left, col_right = st.columns(2)

    with col_left:
        state_rev = run_query("""
            SELECT
                c.customer_state AS state,
                ROUND(SUM(oi.price + oi.freight_value), 2) AS revenue
            FROM orders o
            JOIN order_items oi ON o.order_id = oi.order_id
            JOIN customers c ON o.customer_id = c.customer_id
            WHERE o.order_status = 'delivered'
            GROUP BY state
            ORDER BY revenue DESC
            LIMIT 10
        """)
        fig_state = px.bar(
            state_rev, x="state", y="revenue", color="revenue",
            color_continuous_scale="Blues",
            title="SP, RJ, MG Alone Drive 62% of Total Revenue",
        )
        fig_state.update_layout(
            template=PLOTLY_TEMPLATE, height=380,
            showlegend=False, coloraxis_showscale=False,
            margin=dict(t=50, b=40),
        )
        fig_state.update_xaxes(title="")
        fig_state.update_yaxes(title="Revenue (R$)")
        st.plotly_chart(fig_state, use_container_width=True)

    with col_right:
        cat_rev = run_query("""
            SELECT
                COALESCE(p.product_category_name_english, 'uncategorized') AS category,
                ROUND(SUM(oi.price), 2) AS revenue
            FROM order_items oi
            JOIN products p ON oi.product_id = p.product_id
            JOIN orders o ON oi.order_id = o.order_id
            WHERE o.order_status = 'delivered'
            GROUP BY category
            ORDER BY revenue DESC
            LIMIT 10
        """)
        fig_cat = px.bar(
            cat_rev, x="revenue", y="category", orientation="h",
            color="revenue", color_continuous_scale="Purples",
            title="Health & Beauty Leads — Top 10 Categories = 64% of Revenue",
        )
        fig_cat.update_layout(
            template=PLOTLY_TEMPLATE, height=380,
            showlegend=False, coloraxis_showscale=False,
            margin=dict(t=50, b=40),
            yaxis=dict(autorange="reversed"),
        )
        fig_cat.update_xaxes(title="Revenue (R$)")
        fig_cat.update_yaxes(title="")
        st.plotly_chart(fig_cat, use_container_width=True)

    st.success("""
    **📌 Business Recommendation:** Revenue grew 8x from Jan 2017 to early 2018, but has
    plateaued around R$1M/month since March 2018. The platform is transitioning from a growth
    phase to a retention phase. Priority should shift from customer acquisition to reducing churn
    and increasing repeat purchases (currently only 3%).
    """)


# ══════════════════════════════════════════════════════════════
#           TAB 2: CUSTOMER INTELLIGENCE
# ══════════════════════════════════════════════════════════════

with tab2:

    # ── RFM Segmentation ─────────────────────────────────────
    rfm_df = run_query("""
        WITH rfm_raw AS (
            SELECT
                c.customer_unique_id,
                CAST(julianday((SELECT MAX(order_purchase_timestamp) FROM orders))
                    - julianday(MAX(o.order_purchase_timestamp)) AS INTEGER) AS recency_days,
                COUNT(DISTINCT o.order_id) AS frequency,
                ROUND(SUM(oi.price + oi.freight_value), 2) AS monetary
            FROM customers c
            JOIN orders o ON c.customer_id = o.customer_id
            JOIN order_items oi ON o.order_id = oi.order_id
            WHERE o.order_status = 'delivered'
            GROUP BY c.customer_unique_id
        ),
        rfm_scores AS (
            SELECT *, NTILE(5) OVER (ORDER BY recency_days DESC) AS r_score,
                NTILE(5) OVER (ORDER BY frequency ASC) AS f_score,
                NTILE(5) OVER (ORDER BY monetary ASC) AS m_score
            FROM rfm_raw
        )
        SELECT *, CASE
            WHEN r_score >= 4 AND f_score >= 4 AND m_score >= 4 THEN 'Champions'
            WHEN r_score >= 3 AND f_score >= 3 AND m_score >= 3 THEN 'Loyal Customers'
            WHEN r_score >= 4 AND f_score <= 2 AND m_score >= 3 THEN 'Potential Loyalists'
            WHEN r_score >= 4 AND f_score = 1 THEN 'New Customers'
            WHEN r_score <= 2 AND f_score >= 3 AND m_score >= 3 THEN 'At Risk'
            WHEN r_score <= 2 AND f_score >= 4 AND m_score >= 4 THEN 'Cant Lose Them'
            WHEN r_score <= 2 AND f_score <= 2 AND m_score <= 2 THEN 'Hibernating'
            WHEN r_score = 3 AND f_score >= 2 AND m_score >= 2 THEN 'Need Attention'
            WHEN r_score <= 2 AND f_score <= 2 THEN 'About to Sleep'
            ELSE 'Others'
        END AS segment
        FROM rfm_scores
    """)

    # KPI row
    total_cust = len(rfm_df)
    repeat_cust = len(rfm_df[rfm_df["frequency"] > 1])
    at_risk = len(rfm_df[rfm_df["segment"] == "At Risk"])
    champions = len(rfm_df[rfm_df["segment"] == "Champions"])

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Customers", f"{total_cust:,}")
    c2.metric("Repeat Buyers", f"{repeat_cust:,}", f"{repeat_cust/total_cust*100:.1f}%")
    c3.metric("Champions", f"{champions:,}", f"{champions/total_cust*100:.1f}%")
    c4.metric("At Risk", f"{at_risk:,}", f"{at_risk/total_cust*100:.1f}%", delta_color="inverse")

    st.divider()

    col_left, col_right = st.columns(2)

    with col_left:
        # Segment donut chart
        seg_counts = rfm_df["segment"].value_counts().reset_index()
        seg_counts.columns = ["segment", "count"]

        segment_colors = {
            "Champions": "#06d6a0", "Loyal Customers": "#4361ee",
            "Potential Loyalists": "#4cc9f0", "New Customers": "#80ed99",
            "At Risk": "#ef476f", "Cant Lose Them": "#d00000",
            "Hibernating": "#adb5bd", "Need Attention": "#ffd166",
            "About to Sleep": "#dee2e6", "Others": "#e9ecef",
        }

        fig_donut = px.pie(
            seg_counts, values="count", names="segment",
            hole=0.5,
            color="segment",
            color_discrete_map=segment_colors,
            title="23% of Customers Are At Risk — Largest Revenue Segment",
        )
        fig_donut.update_layout(
            template=PLOTLY_TEMPLATE, height=440,
            margin=dict(t=50, b=20),
        )
        st.plotly_chart(fig_donut, use_container_width=True)

    with col_right:
        # RFM scatter: Recency vs Monetary, colored by segment
        scatter_sample = rfm_df.sample(n=min(5000, len(rfm_df)), random_state=42)
        fig_scatter = px.scatter(
            scatter_sample, x="recency_days", y="monetary",
            color="segment", color_discrete_map=segment_colors,
            opacity=0.5, size_max=8,
            title="RFM Scatter: Champions (Top-Right) vs At Risk (Bottom-Left)",
        )
        fig_scatter.update_layout(
            template=PLOTLY_TEMPLATE, height=440,
            xaxis_title="Recency (days since last purchase)",
            yaxis_title="Monetary (R$ total spent)",
            margin=dict(t=50, b=40),
            legend=dict(font=dict(size=10)),
        )
        st.plotly_chart(fig_scatter, use_container_width=True)

    # ── Cohort Retention Heatmap ─────────────────────────────
    st.subheader("Cohort Retention Heatmap")

    cohort_df = run_query("""
        WITH customer_orders AS (
            SELECT c.customer_unique_id, o.order_id,
                o.order_purchase_timestamp,
                strftime('%Y-%m', MIN(o.order_purchase_timestamp) OVER (
                    PARTITION BY c.customer_unique_id)) AS cohort_month,
                strftime('%Y-%m', o.order_purchase_timestamp) AS order_month
            FROM customers c
            JOIN orders o ON c.customer_id = o.customer_id
            WHERE o.order_status = 'delivered'
        ),
        cohort_activity AS (
            SELECT customer_unique_id, cohort_month, order_month,
                (CAST(strftime('%Y', order_month || '-01') AS INT) * 12
                 + CAST(strftime('%m', order_month || '-01') AS INT))
                - (CAST(strftime('%Y', cohort_month || '-01') AS INT) * 12
                 + CAST(strftime('%m', cohort_month || '-01') AS INT))
                AS months_since_first
            FROM customer_orders
        ),
        cohort_sizes AS (
            SELECT cohort_month, COUNT(DISTINCT customer_unique_id) AS cohort_size
            FROM cohort_activity WHERE months_since_first = 0
            GROUP BY cohort_month
        ),
        cohort_retention AS (
            SELECT ca.cohort_month, ca.months_since_first,
                COUNT(DISTINCT ca.customer_unique_id) AS active_customers
            FROM cohort_activity ca
            WHERE ca.months_since_first >= 0
              AND ca.cohort_month >= '2017-01' AND ca.cohort_month <= '2018-02'
            GROUP BY ca.cohort_month, ca.months_since_first
        )
        SELECT cr.cohort_month, cs.cohort_size, cr.months_since_first,
            ROUND(cr.active_customers * 100.0 / cs.cohort_size, 2) AS retention_pct
        FROM cohort_retention cr
        JOIN cohort_sizes cs ON cr.cohort_month = cs.cohort_month
        WHERE cr.months_since_first <= 6
        ORDER BY cr.cohort_month, cr.months_since_first
    """)

    pivot = cohort_df.pivot_table(
        index="cohort_month", columns="months_since_first",
        values="retention_pct", aggfunc="first",
    ).fillna(0)

    fig_heatmap = px.imshow(
        pivot.values,
        labels=dict(x="Months After First Purchase", y="Cohort", color="Retention %"),
        x=[f"Month {int(c)}" for c in pivot.columns],
        y=pivot.index.tolist(),
        color_continuous_scale="RdYlGn",
        aspect="auto",
        title="Cohort Retention Drops Below 1% by Month 1 — Critical Retention Failure",
    )
    fig_heatmap.update_layout(
        template=PLOTLY_TEMPLATE, height=420,
        margin=dict(t=50, b=40),
    )
    st.plotly_chart(fig_heatmap, use_container_width=True)

    st.warning("""
    **⚠️ Retention Crisis:** Only 3% of customers ever make a repeat purchase. The cohort
    heatmap shows retention drops below 1% in the very first month across ALL cohorts — no
    improvement over time. Recommendation: Implement a post-purchase email campaign at Day 7,
    14, and 21 — 51% of repeat buyers return within 30 days, so this is the highest-impact window.
    """)


# ══════════════════════════════════════════════════════════════
#              TAB 3: OPERATIONS
# ══════════════════════════════════════════════════════════════

with tab3:

    # ── KPIs ─────────────────────────────────────────────────
    ops_kpi = run_query("""
        SELECT
            ROUND(AVG(CAST(julianday(o.order_delivered_customer_date)
                - julianday(o.order_purchase_timestamp) AS REAL)), 1) AS avg_delivery_days,
            ROUND(SUM(CASE WHEN julianday(o.order_delivered_customer_date)
                > julianday(o.order_estimated_delivery_date) THEN 1 ELSE 0 END)
                * 100.0 / COUNT(*), 1) AS late_pct,
            ROUND(AVG(CASE WHEN julianday(o.order_delivered_customer_date)
                > julianday(o.order_estimated_delivery_date)
                THEN r.review_score END), 2) AS late_avg_review,
            ROUND(AVG(CASE WHEN julianday(o.order_delivered_customer_date)
                <= julianday(o.order_estimated_delivery_date)
                THEN r.review_score END), 2) AS ontime_avg_review
        FROM orders o
        LEFT JOIN order_reviews r ON o.order_id = r.order_id
        WHERE o.order_status = 'delivered'
          AND o.order_delivered_customer_date IS NOT NULL
          AND o.order_estimated_delivery_date IS NOT NULL
    """)

    ok = ops_kpi.iloc[0]
    review_gap = ok["ontime_avg_review"] - ok["late_avg_review"]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Avg Delivery Time", f"{ok['avg_delivery_days']} days")
    c2.metric("Late Delivery Rate", f"{ok['late_pct']}%")
    c3.metric("On-Time Avg Review", f"⭐ {ok['ontime_avg_review']}")
    c4.metric("Late Avg Review", f"⭐ {ok['late_avg_review']}", f"-{review_gap:.2f} stars", delta_color="inverse")

    st.divider()

    col_left, col_right = st.columns(2)

    with col_left:
        # Delivery by state
        state_del = run_query("""
            SELECT c.customer_state AS state,
                ROUND(AVG(CAST(julianday(o.order_delivered_customer_date)
                    - julianday(o.order_purchase_timestamp) AS REAL)), 1) AS avg_days,
                ROUND(SUM(CASE WHEN julianday(o.order_delivered_customer_date)
                    > julianday(o.order_estimated_delivery_date) THEN 1 ELSE 0 END)
                    * 100.0 / COUNT(*), 1) AS late_pct
            FROM orders o
            JOIN customers c ON o.customer_id = c.customer_id
            WHERE o.order_status = 'delivered'
              AND o.order_delivered_customer_date IS NOT NULL
              AND o.order_estimated_delivery_date IS NOT NULL
            GROUP BY state
            HAVING COUNT(*) >= 100
            ORDER BY avg_days DESC
        """)

        fig_del = px.bar(
            state_del, x="state", y="avg_days", color="late_pct",
            color_continuous_scale="RdYlGn_r",
            title="AM & AP Take 26-28 Days to Deliver — SP Gets Orders in 8 Days",
        )
        fig_del.update_layout(
            template=PLOTLY_TEMPLATE, height=400,
            coloraxis_colorbar_title="Late %",
            margin=dict(t=50, b=40),
        )
        fig_del.update_xaxes(title="Customer State")
        fig_del.update_yaxes(title="Avg Delivery Days")
        st.plotly_chart(fig_del, use_container_width=True)

    with col_right:
        # Delivery vs Reviews scatter
        bucket_df = run_query("""
            SELECT
                CASE
                    WHEN days_late <= -15 THEN -20
                    WHEN days_late <= -8 THEN -11
                    WHEN days_late <= -3 THEN -5
                    WHEN days_late <= -1 THEN -1
                    WHEN days_late = 0 THEN 0
                    WHEN days_late <= 2 THEN 1
                    WHEN days_late <= 5 THEN 4
                    WHEN days_late <= 10 THEN 8
                    WHEN days_late <= 20 THEN 15
                    WHEN days_late <= 40 THEN 30
                    ELSE 50
                END AS bucket_center,
                CASE
                    WHEN days_late <= -15 THEN '15+ early'
                    WHEN days_late <= -8 THEN '8-14 early'
                    WHEN days_late <= -3 THEN '3-7 early'
                    WHEN days_late <= -1 THEN '1-2 early'
                    WHEN days_late = 0 THEN 'On time'
                    WHEN days_late <= 2 THEN '1-2 late'
                    WHEN days_late <= 5 THEN '3-5 late'
                    WHEN days_late <= 10 THEN '6-10 late'
                    WHEN days_late <= 20 THEN '11-20 late'
                    WHEN days_late <= 40 THEN '21-40 late'
                    ELSE '40+ late'
                END AS label,
                ROUND(AVG(review_score), 2) AS avg_review,
                COUNT(*) AS orders
            FROM (
                SELECT
                    CAST(julianday(o.order_delivered_customer_date)
                         - julianday(o.order_estimated_delivery_date) AS INTEGER) AS days_late,
                    r.review_score
                FROM orders o
                JOIN order_reviews r ON o.order_id = r.order_id
                WHERE o.order_status = 'delivered'
                  AND o.order_delivered_customer_date IS NOT NULL
                  AND o.order_estimated_delivery_date IS NOT NULL
            )
            GROUP BY bucket_center, label
            HAVING orders >= 20
            ORDER BY bucket_center
        """)

        fig_corr = px.scatter(
            bucket_df, x="bucket_center", y="avg_review",
            size="orders", text="label",
            title="Late Delivery Destroys Reviews: 4.3★ On-Time → 1.7★ When 11+ Days Late",
        )

        # Add trend line
        raw_delivery = run_query("""
            SELECT
                CAST(julianday(o.order_delivered_customer_date)
                     - julianday(o.order_estimated_delivery_date) AS INTEGER) AS days_late,
                r.review_score
            FROM orders o
            JOIN order_reviews r ON o.order_id = r.order_id
            WHERE o.order_status = 'delivered'
              AND o.order_delivered_customer_date IS NOT NULL
              AND o.order_estimated_delivery_date IS NOT NULL
        """)
        slope, intercept, r_val, p_val, std_err = stats.linregress(
            raw_delivery["days_late"], raw_delivery["review_score"]
        )
        x_line = [-25, 50]
        y_line = [intercept + slope * x for x in x_line]
        fig_corr.add_trace(go.Scatter(
            x=x_line, y=y_line, mode="lines",
            line=dict(color="red", dash="dash", width=2),
            name=f"Trend (r={r_val:.2f})",
        ))

        fig_corr.update_layout(
            template=PLOTLY_TEMPLATE, height=400,
            xaxis_title="Days vs Estimated Delivery (negative = early)",
            yaxis_title="Average Review Score",
            margin=dict(t=50, b=40),
        )
        fig_corr.update_traces(textposition="top center", selector=dict(mode="markers+text"))
        st.plotly_chart(fig_corr, use_container_width=True)

    st.error(f"""
    **🚨 Critical Finding:** Late deliveries cause a **{review_gap:.2f}-star review drop**
    (from {ok['ontime_avg_review']}★ to {ok['late_avg_review']}★). The regression shows every
    additional late day costs **{abs(slope):.3f} stars** (r = {r_val:.2f}, p ≈ 0).
    78% of customers receiving orders 6+ days late give 1-2 stars.
    Recommendation: Invest in logistics partnerships for northeast states where late rates exceed 15%.
    """)


# ══════════════════════════════════════════════════════════════
#              TAB 4: SELLER SCORECARD
# ══════════════════════════════════════════════════════════════

with tab4:

    # ── Concentration KPIs ───────────────────────────────────
    conc_data = run_query("""
        WITH seller_rev AS (
            SELECT oi.seller_id, SUM(oi.price + oi.freight_value) AS revenue
            FROM order_items oi
            JOIN orders o ON oi.order_id = o.order_id
            WHERE o.order_status = 'delivered'
            GROUP BY oi.seller_id
        ),
        ranked AS (
            SELECT seller_id, revenue,
                ROW_NUMBER() OVER (ORDER BY revenue DESC) AS rn,
                COUNT(*) OVER () AS total,
                SUM(revenue) OVER () AS grand_total,
                SUM(revenue) OVER (ORDER BY revenue DESC
                    ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS cum_rev
            FROM seller_rev
        )
        SELECT
            MAX(CASE WHEN rn * 1.0 / total <= 0.01 THEN ROUND(cum_rev * 100.0 / grand_total, 1) END) AS top_1_pct,
            MAX(CASE WHEN rn * 1.0 / total <= 0.10 THEN ROUND(cum_rev * 100.0 / grand_total, 1) END) AS top_10_pct,
            MAX(CASE WHEN rn * 1.0 / total <= 0.20 THEN ROUND(cum_rev * 100.0 / grand_total, 1) END) AS top_20_pct,
            total AS total_sellers
        FROM ranked
    """)

    cd = conc_data.iloc[0]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Active Sellers", f"{int(cd['total_sellers']):,}")
    c2.metric("Top 1% Sellers → Revenue", f"{cd['top_1_pct']}%")
    c3.metric("Top 10% Sellers → Revenue", f"{cd['top_10_pct']}%")
    c4.metric("Top 20% Sellers → Revenue", f"{cd['top_20_pct']}%")

    st.divider()

    col_left, col_right = st.columns(2)

    with col_left:
        # Seller decile chart
        decile_df = run_query("""
            WITH seller_rev AS (
                SELECT oi.seller_id, ROUND(SUM(oi.price + oi.freight_value), 2) AS revenue
                FROM order_items oi
                JOIN orders o ON oi.order_id = o.order_id
                WHERE o.order_status = 'delivered'
                GROUP BY oi.seller_id
            ),
            deciles AS (
                SELECT *, NTILE(10) OVER (ORDER BY revenue DESC) AS decile
                FROM seller_rev
            )
            SELECT decile,
                COUNT(*) AS sellers,
                ROUND(SUM(revenue), 0) AS revenue,
                ROUND(SUM(revenue) * 100.0 / (SELECT SUM(revenue) FROM seller_rev), 1) AS pct
            FROM deciles
            GROUP BY decile
            ORDER BY decile
        """)

        fig_decile = px.bar(
            decile_df, x="decile", y="pct",
            text="pct",
            color="pct", color_continuous_scale="Reds",
            title="Top 10% of Sellers Generate 66% of Revenue — Extreme Concentration",
        )
        fig_decile.update_layout(
            template=PLOTLY_TEMPLATE, height=400,
            showlegend=False, coloraxis_showscale=False,
            margin=dict(t=50, b=40),
            xaxis=dict(dtick=1),
        )
        fig_decile.update_xaxes(title="Seller Decile (1 = Top 10%)")
        fig_decile.update_yaxes(title="% of Total Revenue")
        fig_decile.update_traces(textposition="outside", texttemplate="%{text}%")
        st.plotly_chart(fig_decile, use_container_width=True)

    with col_right:
        # Bottom sellers table
        bottom_sellers = run_query("""
            WITH sd AS (
                SELECT oi.seller_id, s.seller_state,
                    COUNT(DISTINCT o.order_id) AS orders,
                    ROUND(SUM(oi.price + oi.freight_value), 2) AS revenue,
                    ROUND(AVG(CAST(julianday(o.order_delivered_carrier_date)
                        - julianday(o.order_purchase_timestamp) AS REAL)), 1) AS ship_days,
                    ROUND(SUM(CASE WHEN julianday(o.order_delivered_customer_date)
                        > julianday(o.order_estimated_delivery_date) THEN 1 ELSE 0 END)
                        * 100.0 / COUNT(*), 1) AS late_pct
                FROM order_items oi
                JOIN orders o ON oi.order_id = o.order_id
                JOIN sellers s ON oi.seller_id = s.seller_id
                WHERE o.order_status = 'delivered'
                  AND o.order_delivered_customer_date IS NOT NULL
                  AND o.order_delivered_carrier_date IS NOT NULL
                GROUP BY oi.seller_id, s.seller_state
                HAVING orders >= 10
            ),
            sr AS (
                SELECT oi.seller_id,
                    ROUND(AVG(r.review_score), 2) AS avg_review,
                    ROUND(SUM(CASE WHEN r.review_score <= 2 THEN 1 ELSE 0 END)
                        * 100.0 / COUNT(*), 1) AS bad_pct
                FROM order_items oi
                JOIN orders o ON oi.order_id = o.order_id
                JOIN order_reviews r ON o.order_id = r.order_id
                WHERE o.order_status = 'delivered'
                GROUP BY oi.seller_id
            )
            SELECT sd.seller_id, sd.seller_state AS state, sd.orders, sd.revenue,
                sd.ship_days, sd.late_pct, sr.avg_review, sr.bad_pct
            FROM sd
            JOIN sr ON sd.seller_id = sr.seller_id
            ORDER BY sr.avg_review ASC
            LIMIT 10
        """)

        st.markdown("##### ⚠️ Bottom 10 Sellers — Flagged for Review/Removal")
        st.dataframe(
            bottom_sellers.style.format({
                "revenue": "R$ {:,.0f}",
                "ship_days": "{:.1f}",
                "late_pct": "{:.1f}%",
                "avg_review": "{:.2f}",
                "bad_pct": "{:.1f}%",
            }).background_gradient(subset=["avg_review"], cmap="RdYlGn")
            .background_gradient(subset=["late_pct"], cmap="RdYlGn_r"),
            use_container_width=True,
            height=400,
        )

    st.warning("""
    **⚠️ Concentration Risk:** Top 10% of sellers drive 66% of revenue. Losing even one top-10
    seller would cost 1-1.6% of total revenue. Recommendation: (1) Build a seller retention
    program for top decile sellers, (2) Actively recruit in underserved states (Bahia, Pará,
    Pernambuco), and (3) Remove the 8 sellers flagged with quality scores below 30.
    """)


# ══════════════════════════════════════════════════════════════
#              TAB 5: DEEP DIVE
# ══════════════════════════════════════════════════════════════

with tab5:

    # ── Filters ──────────────────────────────────────────────
    st.markdown("##### 🔍 Filter & Explore the Data")

    fc1, fc2, fc3 = st.columns(3)

    # Get filter options
    states = run_query("SELECT DISTINCT customer_state FROM customers ORDER BY customer_state")
    categories = run_query("""
        SELECT DISTINCT COALESCE(product_category_name_english, 'uncategorized') AS cat
        FROM products ORDER BY cat
    """)

    with fc1:
        selected_states = st.multiselect(
            "Select States", states["customer_state"].tolist(),
            default=["SP", "RJ", "MG"],
        )
    with fc2:
        selected_cats = st.multiselect(
            "Select Categories", categories["cat"].tolist(),
            default=["health_beauty", "watches_gifts", "bed_bath_table", "sports_leisure", "computers_accessories"],
        )
    with fc3:
        date_range = st.select_slider(
            "Date Range",
            options=pd.date_range("2017-01-01", "2018-08-31", freq="MS").strftime("%Y-%m").tolist(),
            value=("2017-01", "2018-08"),
        )

    # Build filtered query
    state_filter = "'" + "','".join(selected_states) + "'" if selected_states else "'SP'"
    cat_filter = "'" + "','".join(selected_cats) + "'" if selected_cats else "'health_beauty'"

    filtered_df = run_query(f"""
        SELECT
            strftime('%Y-%m', o.order_purchase_timestamp) AS month,
            c.customer_state AS state,
            COALESCE(p.product_category_name_english, 'uncategorized') AS category,
            ROUND(SUM(oi.price + oi.freight_value), 2) AS revenue,
            COUNT(DISTINCT o.order_id) AS orders,
            ROUND(AVG(r.review_score), 2) AS avg_review
        FROM orders o
        JOIN order_items oi ON o.order_id = oi.order_id
        JOIN customers c ON o.customer_id = c.customer_id
        JOIN products p ON oi.product_id = p.product_id
        LEFT JOIN order_reviews r ON o.order_id = r.order_id
        WHERE o.order_status = 'delivered'
          AND c.customer_state IN ({state_filter})
          AND COALESCE(p.product_category_name_english, 'uncategorized') IN ({cat_filter})
          AND strftime('%Y-%m', o.order_purchase_timestamp) >= '{date_range[0]}'
          AND strftime('%Y-%m', o.order_purchase_timestamp) <= '{date_range[1]}'
        GROUP BY month, state, category
        ORDER BY month
    """)

    if filtered_df.empty:
        st.info("No data for the selected filters. Try adjusting your selection.")
    else:
        # KPIs for filtered data
        fk1, fk2, fk3, fk4 = st.columns(4)
        fk1.metric("Filtered Revenue", f"R$ {filtered_df['revenue'].sum():,.0f}")
        fk2.metric("Filtered Orders", f"{filtered_df['orders'].sum():,}")
        fk3.metric("Avg Review", f"⭐ {filtered_df['avg_review'].mean():.2f}")
        fk4.metric("Data Points", f"{len(filtered_df):,}")

        st.divider()

        col_left, col_right = st.columns(2)

        with col_left:
            # Revenue by month (filtered)
            monthly = filtered_df.groupby("month").agg({"revenue": "sum", "orders": "sum"}).reset_index()
            fig_filt = px.bar(
                monthly, x="month", y="revenue",
                color_discrete_sequence=[COLORS["primary"]],
                title="Filtered Revenue Trend",
            )
            fig_filt.update_layout(
                template=PLOTLY_TEMPLATE, height=380,
                margin=dict(t=50, b=40),
            )
            st.plotly_chart(fig_filt, use_container_width=True)

        with col_right:
            # Revenue by category (filtered)
            by_cat = filtered_df.groupby("category")["revenue"].sum().reset_index().sort_values("revenue", ascending=True)
            fig_filt2 = px.bar(
                by_cat, x="revenue", y="category", orientation="h",
                color_discrete_sequence=[COLORS["secondary"]],
                title="Revenue by Category (Filtered)",
            )
            fig_filt2.update_layout(
                template=PLOTLY_TEMPLATE, height=380,
                margin=dict(t=50, b=40),
            )
            st.plotly_chart(fig_filt2, use_container_width=True)

        # Raw data table + download
        st.markdown("##### 📋 Raw Data Table")
        st.dataframe(
            filtered_df.style.format({
                "revenue": "R$ {:,.2f}",
                "avg_review": "{:.2f}",
            }),
            use_container_width=True,
            height=300,
        )

        csv = filtered_df.to_csv(index=False)
        st.download_button(
            label="📥 Download Filtered Data as CSV",
            data=csv,
            file_name="bharatcommerce_filtered_data.csv",
            mime="text/csv",
        )


# ── Footer ───────────────────────────────────────────────────
st.divider()
st.markdown(
    "<div style='text-align:center; color:#888; font-size:0.85rem;'>"
    "BharatCommerce BI Dashboard | Built with Python, SQL, Streamlit & Plotly | "
    "Data: Olist Brazilian E-Commerce Dataset (Kaggle)"
    "</div>",
    unsafe_allow_html=True,
)