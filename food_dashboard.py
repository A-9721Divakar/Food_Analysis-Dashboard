"""
╔══════════════════════════════════════════════════════════════════════╗
║          FOOD ANALYSIS DASHBOARD  — Streamlit + PostgreSQL          ║
║  Run:  streamlit run food_dashboard.py                              ║
╚══════════════════════════════════════════════════════════════════════╝

Requirements (install once):
    pip install streamlit pandas plotly psycopg2-binary sqlalchemy

Fill in DB_CONFIG below with your PostgreSQL credentials.
The four CSV files must exist at the paths in CSV_PATHS.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sqlalchemy import create_engine, text
import os, re
from datetime import date

# ─────────────────────────────────────────────────────────────────────────────
# 1. CONFIGURATION  ← Edit these before running
# ─────────────────────────────────────────────────────────────────────────────
DB_CONFIG = dict(
    host     = "localhost",
    port     = 5432,
    database = "Food_Analysis",
    user     = "food_user",
    password = "food1234",
)

CSV_PATHS = dict(
    providers    = r"C:/New folder/New folder/All Excel Practice Files/Food managment dataset/providers_data.csv",
    receivers    = r"C:/New folder/New folder/All Excel Practice Files/Food managment dataset/receivers_data.csv",
    food_listings= r"C:/New folder/New folder/All Excel Practice Files/Food managment dataset/food_listings_data.csv",
    claims       = r"C:/New folder/New folder/All Excel Practice Files/Food managment dataset/claims_data.csv",
)

# ─────────────────────────────────────────────────────────────────────────────
# 2. PAGE CONFIG
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="🍱 Food Analysis Dashboard",
    page_icon="🍱",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────────────────
# 3. CUSTOM CSS
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* Main background */
.stApp { background: #f0f4f8; }

/* Sidebar */
section[data-testid="stSidebar"] { background: #1a3c5e; }
section[data-testid="stSidebar"] * { color: #e8f0fe !important; }
section[data-testid="stSidebar"] .stSelectbox label,
section[data-testid="stSidebar"] .stMultiSelect label { color: #a8c8f8 !important; }

/* KPI cards */
.kpi-card {
    background: white;
    border-radius: 12px;
    padding: 20px 24px;
    box-shadow: 0 2px 8px rgba(0,0,0,.10);
    border-left: 5px solid #2196F3;
    margin-bottom: 10px;
}
.kpi-value { font-size: 2.1rem; font-weight: 700; color: #1a3c5e; }
.kpi-label { font-size: 0.85rem; color: #607d8b; margin-top: 2px; }
.kpi-delta { font-size: 0.8rem; }

/* Section headers */
.section-header {
    background: linear-gradient(90deg,#1a3c5e,#2196F3);
    color: white;
    padding: 8px 18px;
    border-radius: 8px;
    font-size: 1.1rem;
    font-weight: 600;
    margin: 18px 0 12px 0;
}

/* Alert boxes */
.success-box {
    background:#e8f5e9; border-left:4px solid #4caf50;
    padding:10px 16px; border-radius:6px; margin:6px 0;
}
.error-box {
    background:#ffebee; border-left:4px solid #f44336;
    padding:10px 16px; border-radius:6px; margin:6px 0;
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# 4. DATABASE CONNECTION
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_resource(show_spinner="Connecting to database…")
def get_engine():
    url = (
        f"postgresql+psycopg2://{DB_CONFIG['user']}:{DB_CONFIG['password']}"
        f"@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
    )
    return create_engine(url, pool_pre_ping=True)

@st.cache_data(ttl=120, show_spinner=False)
def run_query(sql: str, params: dict | None = None) -> pd.DataFrame:
    engine = get_engine()
    with engine.connect() as conn:
        return pd.read_sql(text(sql), conn, params=params)

# ─────────────────────────────────────────────────────────────────────────────
# 5. CSV IMPORT HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def import_csv(table: str, path: str, engine) -> tuple[bool, str]:
    """Read CSV and upsert into PostgreSQL using pandas + to_sql (replace)."""
    if not os.path.exists(path):
        return False, f"File not found: {path}"
    try:
        df = pd.read_csv(path)
        # Normalise column names → lower-case, strip spaces
        df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
        # Parse date columns
        for col in df.columns:
            if "date" in col or "timestamp" in col:
                df[col] = pd.to_datetime(df[col], errors="coerce")
        df.to_sql(table.lower(), engine, if_exists="replace", index=False)
        return True, f"✅ Imported {len(df):,} rows into **{table}**"
    except Exception as e:
        return False, f"❌ {table}: {e}"

# ─────────────────────────────────────────────────────────────────────────────
# 6. SIDEBAR NAVIGATION & FILTERS
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🍱 Food Analysis")
    st.markdown("---")

    page = st.radio(
        "Navigate",
        [
            "🏠 Overview",
            "📦 Providers",
            "🤝 Receivers",
            "🥗 Food Listings",
            "📋 Claims",
            "📊 Analysis",
            "⬆️ Import CSVs",
            "🔧 Raw SQL",
        ],
        label_visibility="collapsed",
    )

    st.markdown("---")
    st.markdown("### 🔍 Global Filters")

    # City filter (populated from DB)
    try:
        cities_df = run_query("SELECT DISTINCT city FROM providers UNION SELECT DISTINCT city FROM receivers ORDER BY city")
        all_cities = ["All"] + cities_df["city"].dropna().tolist()
    except Exception:
        all_cities = ["All"]

    sel_city = st.selectbox("City", all_cities)
    city_filter = None if sel_city == "All" else sel_city

    # Food type filter
    try:
        ft_df = run_query("SELECT DISTINCT food_type FROM food_listings ORDER BY food_type")
        all_ft = ["All"] + ft_df["food_type"].dropna().tolist()
    except Exception:
        all_ft = ["All"]

    sel_ft = st.selectbox("Food Type", all_ft)
    ft_filter = None if sel_ft == "All" else sel_ft

    # Meal type filter
    try:
        mt_df = run_query("SELECT DISTINCT meal_type FROM food_listings ORDER BY meal_type")
        all_mt = ["All"] + mt_df["meal_type"].dropna().tolist()
    except Exception:
        all_mt = ["All"]

    sel_mt = st.selectbox("Meal Type", all_mt)
    mt_filter = None if sel_mt == "All" else sel_mt

    # Claim status filter
    try:
        cs_df = run_query("SELECT DISTINCT status FROM claims ORDER BY status")
        all_cs = ["All"] + cs_df["status"].dropna().tolist()
    except Exception:
        all_cs = ["All"]

    sel_cs = st.selectbox("Claim Status", all_cs)
    cs_filter = None if sel_cs == "All" else sel_cs

    st.markdown("---")
    if st.button("🔄 Refresh Data Cache"):
        run_query.clear()
        st.success("Cache cleared!")

# helper: build WHERE clauses
def where(*conditions):
    parts = [c for c in conditions if c]
    return ("WHERE " + " AND ".join(parts)) if parts else ""

# ─────────────────────────────────────────────────────────────────────────────
# 7. PAGE: OVERVIEW
# ─────────────────────────────────────────────────────────────────────────────
if page == "🏠 Overview":
    st.title("🍱 Food Analysis Dashboard")
    st.caption("Real-time insights from the Food Management database")

    # ── KPIs ──────────────────────────────────────────────────────────────────
    try:
        kpi_prov   = run_query("SELECT COUNT(*) AS n FROM providers")["n"][0]
        kpi_recv   = run_query("SELECT COUNT(*) AS n FROM receivers")["n"][0]
        kpi_food   = run_query("SELECT COUNT(*) AS n FROM food_listings")["n"][0]
        kpi_claims = run_query("SELECT COUNT(*) AS n FROM claims")["n"][0]
        kpi_qty    = run_query("SELECT COALESCE(SUM(quantity),0) AS n FROM food_listings")["n"][0]
        kpi_comp   = run_query("SELECT COUNT(*) AS n FROM claims WHERE LOWER(status)='completed'")["n"][0]

        col1, col2, col3 = st.columns(3)
        col4, col5, col6 = st.columns(3)

        def kpi(col, label, value, color="#2196F3", prefix="", suffix=""):
            col.markdown(
                f"""<div class="kpi-card" style="border-left-color:{color}">
                    <div class="kpi-value">{prefix}{value:,}{suffix}</div>
                    <div class="kpi-label">{label}</div>
                </div>""",
                unsafe_allow_html=True,
            )

        kpi(col1, "Total Providers",        kpi_prov,   "#2196F3")
        kpi(col2, "Total Receivers",        kpi_recv,   "#4CAF50")
        kpi(col3, "Food Listings",          kpi_food,   "#FF9800")
        kpi(col4, "Total Claims",           kpi_claims, "#9C27B0")
        kpi(col5, "Total Food Quantity",    kpi_qty,    "#F44336", suffix=" units")
        kpi(col6, "Completed Claims",       kpi_comp,   "#009688")

    except Exception as e:
        st.error(f"KPI load error: {e}")

    st.markdown('<div class="section-header">📈 Quick Charts</div>', unsafe_allow_html=True)

    try:
        c1, c2 = st.columns(2)
        with c1:
            df = run_query("SELECT type, COUNT(*) AS total FROM providers GROUP BY type ORDER BY total DESC")
            fig = px.pie(df, names="type", values="total", title="Providers by Type",
                         color_discrete_sequence=px.colors.qualitative.Set2)
            st.plotly_chart(fig, use_container_width=True)

        with c2:
            df = run_query("SELECT food_type, SUM(quantity) AS total FROM food_listings GROUP BY food_type ORDER BY total DESC")
            fig = px.bar(df, x="food_type", y="total", title="Food Quantity by Type",
                         color="food_type", color_discrete_sequence=px.colors.qualitative.Pastel)
            fig.update_layout(showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

        c3, c4 = st.columns(2)
        with c3:
            df = run_query("SELECT status, COUNT(*) AS n FROM claims GROUP BY status")
            fig = px.pie(df, names="status", values="n", title="Claims by Status",
                         color_discrete_sequence=px.colors.qualitative.Safe, hole=0.4)
            st.plotly_chart(fig, use_container_width=True)

        with c4:
            df = run_query("SELECT meal_type, SUM(quantity) AS total FROM food_listings GROUP BY meal_type ORDER BY total DESC")
            fig = px.bar(df, x="meal_type", y="total", title="Quantity by Meal Type",
                         color="meal_type", color_discrete_sequence=px.colors.qualitative.Bold)
            fig.update_layout(showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"Chart error: {e}")

# ─────────────────────────────────────────────────────────────────────────────
# 8. PAGE: PROVIDERS
# ─────────────────────────────────────────────────────────────────────────────
elif page == "📦 Providers":
    st.title("📦 Providers")

    # City search
    search = st.text_input("🔎 Search provider name or city")

    try:
        sql = """
            SELECT p.provider_id, p.name, p.type, p.city, p.address, p.contact,
                   COUNT(f.food_id) AS listings,
                   COALESCE(SUM(f.quantity),0) AS total_donated
            FROM providers p
            LEFT JOIN food_listings f ON p.provider_id = f.provider_id
            {where_clause}
            GROUP BY p.provider_id, p.name, p.type, p.city, p.address, p.contact
            ORDER BY total_donated DESC
        """
        conditions = []
        if city_filter:
            conditions.append(f"p.city = '{city_filter}'")
        if search:
            conditions.append(f"(LOWER(p.name) LIKE '%{search.lower()}%' OR LOWER(p.city) LIKE '%{search.lower()}%')")
        df = run_query(sql.format(where_clause=where(*conditions)))
        st.markdown(f"**{len(df):,} providers found**")
        st.dataframe(df, use_container_width=True, height=350)

        c1, c2 = st.columns(2)
        with c1:
            g = df.groupby("city")["total_donated"].sum().reset_index().sort_values("total_donated", ascending=False)
            fig = px.bar(g, x="city", y="total_donated", title="Total Donated by City",
                         color="total_donated", color_continuous_scale="Blues")
            st.plotly_chart(fig, use_container_width=True)

        with c2:
            g = df.groupby("type")["provider_id"].count().reset_index()
            g.columns = ["type", "count"]
            fig = px.pie(g, names="type", values="count", title="Provider Types",
                         color_discrete_sequence=px.colors.qualitative.Set3)
            st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"Providers page error: {e}")

# ─────────────────────────────────────────────────────────────────────────────
# 9. PAGE: RECEIVERS
# ─────────────────────────────────────────────────────────────────────────────
elif page == "🤝 Receivers":
    st.title("🤝 Receivers")

    search = st.text_input("🔎 Search receiver name or city")

    try:
        conditions = []
        if city_filter:
            conditions.append(f"r.city = '{city_filter}'")
        if search:
            conditions.append(f"(LOWER(r.name) LIKE '%{search.lower()}%' OR LOWER(r.city) LIKE '%{search.lower()}%')")

        sql = """
            SELECT r.receiver_id, r.name, r.type, r.city, r.contact,
                   COUNT(c.claim_id)          AS total_claims,
                   COALESCE(SUM(f.quantity),0) AS total_claimed_qty,
                   ROUND(AVG(f.quantity),1)    AS avg_quantity
            FROM receivers r
            LEFT JOIN claims c      ON r.receiver_id = c.receiver_id
            LEFT JOIN food_listings f ON c.food_id = f.food_id
            {where_clause}
            GROUP BY r.receiver_id, r.name, r.type, r.city, r.contact
            ORDER BY total_claimed_qty DESC
        """.format(where_clause=where(*conditions))

        df = run_query(sql)
        st.markdown(f"**{len(df):,} receivers found**")
        st.dataframe(df, use_container_width=True, height=350)

        c1, c2 = st.columns(2)
        with c1:
            g = df.groupby("city")["total_claimed_qty"].sum().reset_index().sort_values("total_claimed_qty", ascending=False)
            fig = px.bar(g, x="city", y="total_claimed_qty", title="Total Claimed Qty by City",
                         color="total_claimed_qty", color_continuous_scale="Greens")
            st.plotly_chart(fig, use_container_width=True)

        with c2:
            g = df.groupby("type")["receiver_id"].count().reset_index()
            g.columns = ["type", "count"]
            fig = px.pie(g, names="type", values="count", title="Receiver Types",
                         color_discrete_sequence=px.colors.qualitative.Pastel)
            st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"Receivers page error: {e}")

# ─────────────────────────────────────────────────────────────────────────────
# 10. PAGE: FOOD LISTINGS
# ─────────────────────────────────────────────────────────────────────────────
elif page == "🥗 Food Listings":
    st.title("🥗 Food Listings")

    search = st.text_input("🔎 Search food name")

    try:
        conditions = []
        if ft_filter:
            conditions.append(f"f.food_type = '{ft_filter}'")
        if mt_filter:
            conditions.append(f"f.meal_type = '{mt_filter}'")
        if city_filter:
            conditions.append(f"f.location = '{city_filter}'")
        if search:
            conditions.append(f"LOWER(f.food_name) LIKE '%{search.lower()}%'")

        sql = """
            SELECT f.food_id, f.food_name, f.quantity, f.expiry_date,
                   f.food_type, f.meal_type, f.location, f.provider_type,
                   p.name AS provider_name
            FROM food_listings f
            LEFT JOIN providers p ON f.provider_id = p.provider_id
            {w}
            ORDER BY f.quantity DESC
        """.format(w=where(*conditions))

        df = run_query(sql)

        # Expiry status
        today = pd.Timestamp(date.today())
        if "expiry_date" in df.columns:
            df["expiry_date"] = pd.to_datetime(df["expiry_date"], errors="coerce")
            df["status"] = df["expiry_date"].apply(
                lambda d: "🔴 Expired" if pd.notna(d) and d < today else "🟢 Valid"
            )

        st.markdown(f"**{len(df):,} listings | Total Qty: {df['quantity'].sum():,}**")
        st.dataframe(df, use_container_width=True, height=350)

        c1, c2, c3 = st.columns(3)
        with c1:
            g = df.groupby("food_type")["quantity"].sum().reset_index()
            fig = px.bar(g, x="food_type", y="quantity", title="Qty by Food Type",
                         color="food_type", color_discrete_sequence=px.colors.qualitative.Set1)
            fig.update_layout(showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

        with c2:
            g = df.groupby("meal_type")["quantity"].sum().reset_index()
            fig = px.pie(g, names="meal_type", values="quantity", title="Qty by Meal Type",
                         color_discrete_sequence=px.colors.qualitative.Pastel, hole=0.35)
            st.plotly_chart(fig, use_container_width=True)

        with c3:
            if "status" in df.columns:
                g = df["status"].value_counts().reset_index()
                g.columns = ["status", "count"]
                fig = px.pie(g, names="status", values="count", title="Expiry Status",
                             color_discrete_map={"🟢 Valid": "#4CAF50", "🔴 Expired": "#F44336"})
                st.plotly_chart(fig, use_container_width=True)

        # Food type × Meal type heatmap
        st.markdown('<div class="section-header">🔥 Food Type × Meal Type Heatmap</div>', unsafe_allow_html=True)
        pivot = df.pivot_table(index="food_type", columns="meal_type", values="quantity", aggfunc="sum", fill_value=0)
        fig = px.imshow(pivot, text_auto=True, color_continuous_scale="Blues",
                        title="Quantity Heatmap (Food Type × Meal Type)")
        st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"Food Listings page error: {e}")

# ─────────────────────────────────────────────────────────────────────────────
# 11. PAGE: CLAIMS
# ─────────────────────────────────────────────────────────────────────────────
elif page == "📋 Claims":
    st.title("📋 Claims")

    try:
        conditions = []
        if cs_filter:
            conditions.append(f"c.status = '{cs_filter}'")
        if ft_filter:
            conditions.append(f"f.food_type = '{ft_filter}'")
        if mt_filter:
            conditions.append(f"f.meal_type = '{mt_filter}'")
        if city_filter:
            conditions.append(f"r.city = '{city_filter}'")

        sql = """
            SELECT c.claim_id, c.status, c.claim_timestamp,
                   f.food_name, f.food_type, f.meal_type, f.quantity,
                   p.name AS provider_name, p.city AS provider_city,
                   r.name AS receiver_name, r.city AS receiver_city
            FROM claims c
            JOIN food_listings f ON c.food_id    = f.food_id
            JOIN providers p     ON f.provider_id = p.provider_id
            JOIN receivers r     ON c.receiver_id = r.receiver_id
            {w}
            ORDER BY c.claim_timestamp DESC
        """.format(w=where(*conditions))

        df = run_query(sql)
        st.markdown(f"**{len(df):,} claims**")
        st.dataframe(df, use_container_width=True, height=350)

        # Status breakdown
        c1, c2 = st.columns(2)
        with c1:
            g = df.groupby("status")["claim_id"].count().reset_index()
            g.columns = ["status", "count"]
            fig = px.bar(g, x="status", y="count", title="Claims by Status",
                         color="status", color_discrete_sequence=px.colors.qualitative.Safe)
            st.plotly_chart(fig, use_container_width=True)

        with c2:
            g = df.groupby("meal_type")["claim_id"].count().reset_index()
            g.columns = ["meal_type", "count"]
            fig = px.pie(g, names="meal_type", values="count", title="Claims by Meal Type",
                         color_discrete_sequence=px.colors.qualitative.Pastel, hole=0.35)
            st.plotly_chart(fig, use_container_width=True)

        # Claim success rate per provider
        st.markdown('<div class="section-header">🏆 Provider Claim Success Rate</div>', unsafe_allow_html=True)
        rate_sql = """
            SELECT p.name,
                   SUM(CASE WHEN LOWER(c.status) = 'completed' THEN 1 ELSE 0 END) * 100.0
                   / NULLIF(COUNT(c.claim_id),0) AS success_rate
            FROM providers p
            JOIN food_listings f ON p.provider_id = f.provider_id
            JOIN claims c        ON f.food_id = c.food_id
            GROUP BY p.name
            ORDER BY success_rate DESC
        """
        rate_df = run_query(rate_sql)
        rate_df["success_rate"] = rate_df["success_rate"].round(1)
        fig = px.bar(rate_df, x="name", y="success_rate",
                     title="Success Rate % by Provider",
                     labels={"name": "Provider", "success_rate": "Success Rate (%)"},
                     color="success_rate", color_continuous_scale="RdYlGn",
                     range_color=[0, 100])
        fig.update_xaxes(tickangle=-35)
        st.plotly_chart(fig, use_container_width=True)

        # Timeline
        if "claim_timestamp" in df.columns:
            st.markdown('<div class="section-header">📅 Claim Timeline</div>', unsafe_allow_html=True)
            timeline = df.copy()
            timeline["claim_timestamp"] = pd.to_datetime(timeline["claim_timestamp"], errors="coerce")
            timeline = timeline.dropna(subset=["claim_timestamp"])
            if not timeline.empty:
                timeline["month"] = timeline["claim_timestamp"].dt.to_period("M").astype(str)
                g = timeline.groupby(["month", "status"])["claim_id"].count().reset_index()
                fig = px.bar(g, x="month", y="claim_id", color="status",
                             barmode="stack", title="Monthly Claims by Status",
                             labels={"claim_id": "Claims", "month": "Month"})
                st.plotly_chart(fig, use_container_width=True)

        # Demand by city × meal type
        st.markdown('<div class="section-header">🌆 Demand by City & Meal Type</div>', unsafe_allow_html=True)
        dem_sql = """
            SELECT r.city, f.meal_type, COUNT(c.claim_id) AS demand_count
            FROM receivers r
            JOIN claims c       ON r.receiver_id = c.receiver_id
            JOIN food_listings f ON c.food_id = f.food_id
            GROUP BY r.city, f.meal_type
            ORDER BY demand_count DESC
        """
        dem_df = run_query(dem_sql)
        fig = px.sunburst(dem_df, path=["city", "meal_type"], values="demand_count",
                          title="Demand: City → Meal Type",
                          color="demand_count", color_continuous_scale="Oranges")
        st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"Claims page error: {e}")

# ─────────────────────────────────────────────────────────────────────────────
# 12. PAGE: ANALYSIS (all 17 questions)
# ─────────────────────────────────────────────────────────────────────────────
elif page == "📊 Analysis":
    st.title("📊 Analysis — All 17 Business Questions")

    QUESTIONS = {
        "Q1 · Providers per City": """
            SELECT city, COUNT(*) AS provider_count
            FROM providers GROUP BY city ORDER BY provider_count DESC""",

        "Q2 · Receivers per City": """
            SELECT city, COUNT(*) AS receiver_count
            FROM receivers GROUP BY city ORDER BY receiver_count DESC""",

        "Q3 · Provider Type with Highest Quantity": """
            SELECT provider_type, SUM(quantity) AS total_quantity
            FROM food_listings GROUP BY provider_type ORDER BY total_quantity DESC LIMIT 1""",

        "Q4 · Providers in Selected City": None,   # handled separately

        "Q5 · Receivers by Total Claimed Quantity": """
            SELECT r.name, SUM(f.quantity) AS total_claimed
            FROM receivers r
            JOIN claims c ON r.receiver_id = c.receiver_id
            JOIN food_listings f ON c.food_id = f.food_id
            GROUP BY r.name ORDER BY total_claimed DESC""",

        "Q6 · Total Available Food Quantity": """
            SELECT SUM(quantity) AS total_available FROM food_listings""",

        "Q7 · Location with Most Listings": """
            SELECT location, COUNT(*) AS listing_count
            FROM food_listings GROUP BY location ORDER BY listing_count DESC LIMIT 1""",

        "Q8 · Food Availability by Food Type": """
            SELECT food_type, COUNT(*) AS availability_count
            FROM food_listings GROUP BY food_type ORDER BY availability_count DESC""",

        "Q9 · Claims Count per Food Item": """
            SELECT food_id, COUNT(*) AS claim_count
            FROM claims GROUP BY food_id ORDER BY claim_count DESC""",

        "Q10 · Provider with Most Completed Claims": """
            SELECT p.name, COUNT(c.claim_id) AS success_count
            FROM providers p
            JOIN food_listings f ON p.provider_id = f.provider_id
            JOIN claims c ON f.food_id = c.food_id
            WHERE LOWER(c.status) = 'completed'
            GROUP BY p.name ORDER BY success_count DESC LIMIT 1""",

        "Q11 · Claim Status Percentage": """
            SELECT status,
                   COUNT(*) * 100.0 / SUM(COUNT(*)) OVER() AS percentage
            FROM claims GROUP BY status""",

        "Q12 · Average Quantity per Receiver": """
            SELECT r.name, ROUND(AVG(f.quantity),2) AS avg_quantity
            FROM receivers r
            JOIN claims c ON r.receiver_id = c.receiver_id
            JOIN food_listings f ON c.food_id = f.food_id
            GROUP BY r.name ORDER BY avg_quantity DESC""",

        "Q13 · Most Claimed Meal Type": """
            SELECT f.meal_type, COUNT(c.claim_id) AS claim_count
            FROM food_listings f
            JOIN claims c ON f.food_id = c.food_id
            GROUP BY f.meal_type ORDER BY claim_count DESC LIMIT 1""",

        "Q14 · Total Donated per Provider": """
            SELECT p.name, SUM(f.quantity) AS total_donated
            FROM providers p
            JOIN food_listings f ON p.provider_id = f.provider_id
            GROUP BY p.name ORDER BY total_donated DESC""",

        "Q15 · Food Wasted (Expired, Unclaimed)": """
            SELECT f.food_type, SUM(f.quantity) AS total_wasted_quantity
            FROM food_listings f
            LEFT JOIN claims c ON f.food_id = c.food_id
            WHERE c.claim_id IS NULL AND f.expiry_date < CURRENT_DATE
            GROUP BY f.food_type ORDER BY total_wasted_quantity DESC""",

        "Q16 · Provider Success Rate (%)": """
            SELECT p.name,
                   ROUND(
                       SUM(CASE WHEN LOWER(c.status)='completed' THEN 1 ELSE 0 END)*100.0
                       / NULLIF(COUNT(c.claim_id),0), 1
                   ) AS success_rate_percentage
            FROM providers p
            JOIN food_listings f ON p.provider_id = f.provider_id
            JOIN claims c ON f.food_id = c.food_id
            GROUP BY p.name ORDER BY success_rate_percentage DESC""",

        "Q17 · Demand by City & Meal Type": """
            SELECT r.city, f.meal_type, COUNT(c.claim_id) AS demand_count
            FROM receivers r
            JOIN claims c ON r.receiver_id = c.receiver_id
            JOIN food_listings f ON c.food_id = f.food_id
            GROUP BY r.city, f.meal_type ORDER BY demand_count DESC""",
    }

    selected_q = st.selectbox("Select a question to analyse", list(QUESTIONS.keys()))

    # Q4 needs a city input
    if selected_q == "Q4 · Providers in Selected City":
        city_input = st.text_input("Enter City Name", value=city_filter or "")
        if city_input:
            sql = f"""
                SELECT name, contact, address FROM providers
                WHERE LOWER(city) = LOWER('{city_input}')
            """
            try:
                df = run_query(sql)
                st.dataframe(df, use_container_width=True)
            except Exception as e:
                st.error(str(e))
    else:
        sql = QUESTIONS[selected_q]
        if sql:
            try:
                df = run_query(sql)
                st.dataframe(df, use_container_width=True)

                # Auto-visualise
                num_cols = df.select_dtypes(include="number").columns.tolist()
                cat_cols = df.select_dtypes(exclude="number").columns.tolist()

                if len(cat_cols) >= 1 and len(num_cols) >= 1:
                    x_col = cat_cols[0]
                    y_col = num_cols[0]

                    if len(df) == 1:
                        # Single-value result → metric
                        val = df[y_col].iloc[0]
                        name = df[x_col].iloc[0] if cat_cols else ""
                        st.metric(label=f"{y_col} ({name})", value=f"{val:,.2f}")
                    elif len(df) <= 6:
                        fig = px.pie(df, names=x_col, values=y_col,
                                     title=selected_q,
                                     color_discrete_sequence=px.colors.qualitative.Set2,
                                     hole=0.3)
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        fig = px.bar(df, x=x_col, y=y_col, title=selected_q,
                                     color=y_col, color_continuous_scale="Blues")
                        fig.update_xaxes(tickangle=-35)
                        st.plotly_chart(fig, use_container_width=True)

                elif len(num_cols) == 1 and len(cat_cols) == 0:
                    st.metric(selected_q, f"{df[num_cols[0]].iloc[0]:,.0f}")

                # Allow CSV download
                csv = df.to_csv(index=False).encode()
                st.download_button("⬇️ Download Results as CSV", csv,
                                   file_name=f"{re.sub(r'[^a-z0-9]','_', selected_q.lower())}.csv",
                                   mime="text/csv")

            except Exception as e:
                st.error(f"Query error: {e}")

# ─────────────────────────────────────────────────────────────────────────────
# 13. PAGE: IMPORT CSVs
# ─────────────────────────────────────────────────────────────────────────────
elif page == "⬆️ Import CSVs":
    st.title("⬆️ Import CSV Files")
    st.info(
        "Click **Import All** to load/refresh all four CSV files into the database. "
        "You can also upload files manually below."
    )

    st.markdown("### Current CSV Paths")
    for k, v in CSV_PATHS.items():
        exists = os.path.exists(v)
        icon = "✅" if exists else "❌"
        st.markdown(f"- **{k}**: `{v}` {icon}")

    st.markdown("---")

    col_a, col_b = st.columns(2)

    with col_a:
        if st.button("🚀 Import All CSVs", use_container_width=True):
            engine = get_engine()
            TABLE_MAP = {
                "providers":     CSV_PATHS["providers"],
                "receivers":     CSV_PATHS["receivers"],
                "food_listings": CSV_PATHS["food_listings"],
                "claims":        CSV_PATHS["claims"],
            }
            all_ok = True
            for table, path in TABLE_MAP.items():
                ok, msg = import_csv(table, path, engine)
                if ok:
                    st.markdown(f'<div class="success-box">{msg}</div>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<div class="error-box">{msg}</div>', unsafe_allow_html=True)
                    all_ok = False
            if all_ok:
                run_query.clear()
                st.success("All tables imported! Cache refreshed.")

    with col_b:
        st.markdown("### Upload a CSV Manually")
        table_choice = st.selectbox("Target Table", ["providers", "receivers", "food_listings", "claims"])
        uploaded = st.file_uploader("Choose CSV", type=["csv"])
        if uploaded and st.button("Import Uploaded CSV"):
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
                tmp.write(uploaded.read())
                tmp_path = tmp.name
            engine = get_engine()
            ok, msg = import_csv(table_choice, tmp_path, engine)
            if ok:
                st.markdown(f'<div class="success-box">{msg}</div>', unsafe_allow_html=True)
                run_query.clear()
            else:
                st.markdown(f'<div class="error-box">{msg}</div>', unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# 14. PAGE: RAW SQL
# ─────────────────────────────────────────────────────────────────────────────
elif page == "🔧 Raw SQL":
    st.title("🔧 Raw SQL Query Runner")
    st.warning("⚠️ Only SELECT statements are permitted.")

    default_sql = "SELECT * FROM food_listings LIMIT 10;"
    sql_input = st.text_area("Enter SQL", value=default_sql, height=180)

    col1, col2 = st.columns([1, 4])
    run_btn = col1.button("▶ Run Query", use_container_width=True)
    col2.markdown("")

    if run_btn:
        stripped = sql_input.strip().upper().lstrip("(").lstrip()
        if not stripped.startswith("SELECT") and not stripped.startswith("WITH"):
            st.error("Only SELECT / WITH queries are allowed.")
        else:
            try:
                df = run_query(sql_input)
                st.success(f"{len(df):,} rows returned")
                st.dataframe(df, use_container_width=True, height=400)
                csv = df.to_csv(index=False).encode()
                st.download_button("⬇️ Download CSV", csv, "query_result.csv", "text/csv")
            except Exception as e:
                st.error(f"Query failed: {e}")

# ─────────────────────────────────────────────────────────────────────────────
# 15. FOOTER
# ─────────────────────────────────────────────────────────────────────────────
st.markdown(
    """<hr style="margin-top:40px">
    <p style="text-align:center;color:#9e9e9e;font-size:0.8rem">
    🍱 Food Analysis Dashboard • Built with Streamlit + PostgreSQL + Plotly
    </p>""",
    unsafe_allow_html=True,
)
