"""
╔══════════════════════════════════════════════════════════════════════╗
║        FOOD ANALYSIS DASHBOARD  — Streamlit + PostgreSQL            ║
║   Run:  streamlit run food_dashboard.py                              ║
╚══════════════════════════════════════════════════════════════════════╝
 
Requirements (install once):
    pip install streamlit pandas plotly psycopg2-binary sqlalchemy
 
1. Edit DB_CONFIG with your PostgreSQL credentials.
2. Edit CSV_PATHS with the actual paths to your four CSV files.
3. Run:  streamlit run food_dashboard.py
"""
 
import os
import re
import tempfile
from datetime import date
 
import pandas as pd
import plotly.express as px
import streamlit as st
from sqlalchemy import create_engine, text
 
# ─────────────────────────────────────────────────────────────────────────────
# 1. CONFIGURATION  ← Edit these before running
# ─────────────────────────────────────────────────────────────────────────────
DB_CONFIG = dict(
    host="localhost",
    port=5432,
    database="Food_Analysis",
    user="food_user",
    password="food1234",
)
 
CSV_PATHS = dict(
    providers     = r"C:/New folder/New folder/All Excel Practice Files/Food managment dataset/providers_data.csv",
    receivers     = r"C:/New folder/New folder/All Excel Practice Files/Food managment dataset/receivers_data.csv",
    food_listings = r"C:/New folder/New folder/All Excel Practice Files/Food managment dataset/food_listings_data.csv",
    claims        = r"C:/New folder/New folder/All Excel Practice Files/Food managment dataset/claims_data.csv",
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
.stApp { background: #F3E5AB; }
 
section[data-testid="stSidebar"] { background: #1a3c5e; }
section[data-testid="stSidebar"] * { color: #e8f0fe !important; }
 
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
 
.section-header {
    background: linear-gradient(90deg,#1a3c5e,#2196F3);
    color: white;
    padding: 8px 18px;
    border-radius: 8px;
    font-size: 1.1rem;
    font-weight: 600;
    margin: 18px 0 12px 0;
}
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
        return pd.read_sql(text(sql), conn, params=params or {})
 
 
def run_write(sql: str, params: dict | None = None) -> bool:
    """Execute INSERT / UPDATE / DELETE — returns True on success."""
    try:
        engine = get_engine()
        with engine.begin() as conn:
            conn.execute(text(sql), params or {})
        run_query.clear()
        return True
    except Exception as exc:
        st.error(f"Database error: {exc}")
        return False
 
# ─────────────────────────────────────────────────────────────────────────────
# 5. CSV IMPORT HELPER
# ─────────────────────────────────────────────────────────────────────────────
def import_csv(table: str, path: str, engine) -> tuple[bool, str]:
    if not os.path.exists(path):
        return False, f"File not found: {path}"
    try:
        df = pd.read_csv(path)
        df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
        for col in df.columns:
            if "date" in col or "timestamp" in col:
                df[col] = pd.to_datetime(df[col], errors="coerce")
        df.to_sql(table.lower(), engine, if_exists="replace", index=False)
        return True, f"✅ Imported {len(df):,} rows into **{table}**"
    except Exception as exc:
        return False, f"❌ {table}: {exc}"
 
# ─────────────────────────────────────────────────────────────────────────────
# 6. SIDEBAR NAVIGATION & CRUD FILTERS
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
            "✏️ CRUD Operations",
            "⬆️ Import CSVs",
            "🔧 Raw SQL",
        ],
        label_visibility="collapsed",
    )
 
    st.markdown("---")
    st.markdown("### 🔍 CRUD Filters")
 
    try:
        cities_df = run_query(
            "SELECT DISTINCT city FROM providers "
            "UNION SELECT DISTINCT city FROM receivers ORDER BY city"
        )
        all_cities = ["All"] + cities_df["city"].dropna().tolist()
    except Exception:
        all_cities = ["All"]
 
    sel_city   = st.selectbox("City", all_cities)
 
    try:
        ft_df   = run_query("SELECT DISTINCT food_type FROM food_listings ORDER BY food_type")
        all_ft  = ["All"] + ft_df["food_type"].dropna().tolist()
    except Exception:
        all_ft = ["All"]
 
    sel_ft   = st.selectbox("Food Type", all_ft)
 
    try:
        mt_df   = run_query("SELECT DISTINCT meal_type FROM food_listings ORDER BY meal_type")
        all_mt  = ["All"] + mt_df["meal_type"].dropna().tolist()
    except Exception:
        all_mt = ["All"]
 
    sel_mt   = st.selectbox("Meal Type", all_mt)
 
    try:
        cs_df   = run_query("SELECT DISTINCT status FROM claims ORDER BY status")
        all_cs  = ["All"] + cs_df["status"].dropna().tolist()
    except Exception:
        all_cs = ["All"]
 
    sel_cs   = st.selectbox("Claim Status", all_cs)
 
    filters_submitted = st.button("🔎 Apply Filters", use_container_width=True)
 
    city_filter = None if sel_city == "All" else sel_city
    ft_filter   = None if sel_ft   == "All" else sel_ft
    mt_filter   = None if sel_mt   == "All" else sel_mt
    cs_filter   = None if sel_cs   == "All" else sel_cs
 
    st.markdown("---")
    if st.button("🔄 Refresh Data Cache"):
        run_query.clear()
        st.success("Cache cleared!")
 
 
def build_where(*conditions):
    """Return a WHERE clause string from a list of non-empty condition strings."""
    parts = [c for c in conditions if c]
    return ("WHERE " + " AND ".join(parts)) if parts else ""
 
# ─────────────────────────────────────────────────────────────────────────────
# 7. PAGE: OVERVIEW
# ─────────────────────────────────────────────────────────────────────────────
if page == "🏠 Overview":
    st.title("🍱 Food Analysis Dashboard")
    st.caption("Real-time insights from the Food Management database")
 
    # KPIs
    try:
        kpi_prov   = run_query("SELECT COUNT(*) AS n FROM providers")["n"][0]
        kpi_recv   = run_query("SELECT COUNT(*) AS n FROM receivers")["n"][0]
        kpi_food   = run_query("SELECT COUNT(*) AS n FROM food_listings")["n"][0]
        kpi_claims = run_query("SELECT COUNT(*) AS n FROM claims")["n"][0]
        kpi_qty    = run_query("SELECT COALESCE(SUM(quantity),0) AS n FROM food_listings")["n"][0]
        kpi_comp   = run_query("SELECT COUNT(*) AS n FROM claims WHERE LOWER(status)='completed'")["n"][0]
 
        def kpi_card(col, label, value, color="#2196F3", suffix=""):
            col.markdown(
                f'<div class="kpi-card" style="border-left-color:{color}">'
                f'<div class="kpi-value">{value:,}{suffix}</div>'
                f'<div class="kpi-label">{label}</div></div>',
                unsafe_allow_html=True,
            )
 
        c1, c2, c3 = st.columns(3)
        c4, c5, c6 = st.columns(3)
        kpi_card(c1, "Total Providers",     kpi_prov,   "#2196F3")
        kpi_card(c2, "Total Receivers",     kpi_recv,   "#4CAF50")
        kpi_card(c3, "Food Listings",       kpi_food,   "#FF9800")
        kpi_card(c4, "Total Claims",        kpi_claims, "#9C27B0")
        kpi_card(c5, "Total Food Quantity", kpi_qty,    "#F44336", suffix=" units")
        kpi_card(c6, "Completed Claims",    kpi_comp,   "#009688")
 
    except Exception as exc:
        st.error(f"KPI load error: {exc}")
 
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
 
    except Exception as exc:
        st.error(f"Chart error: {exc}")
 
# ─────────────────────────────────────────────────────────────────────────────
# 8. PAGE: PROVIDERS
# ─────────────────────────────────────────────────────────────────────────────
elif page == "📦 Providers":
    st.title("📦 Providers")
    search = st.text_input("🔎 Search provider name or city")
 
    try:
        conditions = []
        if city_filter:
            conditions.append(f"p.city = '{city_filter}'")
        if search:
            safe = search.lower().replace("'", "''")
            conditions.append(f"(LOWER(p.name) LIKE '%{safe}%' OR LOWER(p.city) LIKE '%{safe}%')")
 
        sql = f"""
            SELECT p.provider_id, p.name, p.type, p.city, p.address, p.contact,
                   COUNT(f.food_id)            AS listings,
                   COALESCE(SUM(f.quantity),0) AS total_donated
            FROM providers p
            LEFT JOIN food_listings f ON p.provider_id = f.provider_id
            {build_where(*conditions)}
            GROUP BY p.provider_id, p.name, p.type, p.city, p.address, p.contact
            ORDER BY total_donated DESC
        """
        df = run_query(sql)
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
 
    except Exception as exc:
        st.error(f"Providers page error: {exc}")
 
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
            safe = search.lower().replace("'", "''")
            conditions.append(f"(LOWER(r.name) LIKE '%{safe}%' OR LOWER(r.city) LIKE '%{safe}%')")
 
        sql = f"""
            SELECT r.receiver_id, r.name, r.type, r.city, r.contact,
                   COUNT(c.claim_id)             AS total_claims,
                   COALESCE(SUM(f.quantity), 0)  AS total_claimed_qty,
                   ROUND(AVG(f.quantity), 1)      AS avg_quantity
            FROM receivers r
            LEFT JOIN claims c       ON r.receiver_id = c.receiver_id
            LEFT JOIN food_listings f ON c.food_id    = f.food_id
            {build_where(*conditions)}
            GROUP BY r.receiver_id, r.name, r.type, r.city, r.contact
            ORDER BY total_claimed_qty DESC
        """
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
 
    except Exception as exc:
        st.error(f"Receivers page error: {exc}")
 
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
            safe = search.lower().replace("'", "''")
            conditions.append(f"LOWER(f.food_name) LIKE '%{safe}%'")
 
        sql = f"""
            SELECT f.food_id, f.food_name, f.quantity, f.expiry_date,
                   f.food_type, f.meal_type, f.location, f.provider_type,
                   p.name AS provider_name
            FROM food_listings f
            LEFT JOIN providers p ON f.provider_id = p.provider_id
            {build_where(*conditions)}
            ORDER BY f.quantity DESC
        """
        df = run_query(sql)
 
        today = pd.Timestamp(date.today())
        if "expiry_date" in df.columns:
            df["expiry_date"] = pd.to_datetime(df["expiry_date"], errors="coerce")
            df["expiry_status"] = df["expiry_date"].apply(
                lambda d: "🔴 Expired" if pd.notna(d) and d < today else "🟢 Valid"
            )
 
        st.markdown(f"**{len(df):,} listings | Total Qty: {int(df['quantity'].sum()):,}**")
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
            if "expiry_status" in df.columns:
                g = df["expiry_status"].value_counts().reset_index()
                g.columns = ["status", "count"]
                fig = px.pie(g, names="status", values="count", title="Expiry Status",
                             color_discrete_map={"🟢 Valid": "#4CAF50", "🔴 Expired": "#F44336"})
                st.plotly_chart(fig, use_container_width=True)
 
        st.markdown('<div class="section-header">🔥 Food Type × Meal Type Heatmap</div>', unsafe_allow_html=True)
        pivot = df.pivot_table(index="food_type", columns="meal_type", values="quantity",
                               aggfunc="sum", fill_value=0)
        fig = px.imshow(pivot, text_auto=True, color_continuous_scale="Blues",
                        title="Quantity Heatmap (Food Type × Meal Type)")
        st.plotly_chart(fig, use_container_width=True)
 
    except Exception as exc:
        st.error(f"Food Listings page error: {exc}")
 
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
 
        sql = f"""
            SELECT c.claim_id, c.status, c.claim_timestamp,
                   f.food_name, f.food_type, f.meal_type, f.quantity,
                   p.name AS provider_name, p.city AS provider_city,
                   r.name AS receiver_name, r.city AS receiver_city
            FROM claims c
            JOIN food_listings f ON c.food_id     = f.food_id
            JOIN providers p     ON f.provider_id = p.provider_id
            JOIN receivers r     ON c.receiver_id = r.receiver_id
            {build_where(*conditions)}
            ORDER BY c.claim_timestamp DESC
        """
        df = run_query(sql)
        st.markdown(f"**{len(df):,} claims**")
        st.dataframe(df, use_container_width=True, height=350)
 
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
 
        st.markdown('<div class="section-header">🏆 Provider Claim Success Rate</div>', unsafe_allow_html=True)
        rate_df = run_query("""
            SELECT p.name,
                   ROUND(
                       SUM(CASE WHEN LOWER(c.status) = 'completed' THEN 1 ELSE 0 END) * 100.0
                       / NULLIF(COUNT(c.claim_id), 0), 1
                   ) AS success_rate
            FROM providers p
            JOIN food_listings f ON p.provider_id = f.provider_id
            JOIN claims c        ON f.food_id     = c.food_id
            GROUP BY p.name
            ORDER BY success_rate DESC
        """)
        fig = px.bar(rate_df, x="name", y="success_rate",
                     title="Success Rate % by Provider",
                     labels={"name": "Provider", "success_rate": "Success Rate (%)"},
                     color="success_rate", color_continuous_scale="RdYlGn",
                     range_color=[0, 100])
        fig.update_xaxes(tickangle=-35)
        st.plotly_chart(fig, use_container_width=True)
 
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
 
        st.markdown('<div class="section-header">🌆 Demand by City & Meal Type</div>', unsafe_allow_html=True)
        dem_df = run_query("""
            SELECT r.city, f.meal_type, COUNT(c.claim_id) AS demand_count
            FROM receivers r
            JOIN claims c        ON r.receiver_id = c.receiver_id
            JOIN food_listings f ON c.food_id     = f.food_id
            GROUP BY r.city, f.meal_type
            ORDER BY demand_count DESC
        """)
        fig = px.sunburst(dem_df, path=["city", "meal_type"], values="demand_count",
                          title="Demand: City → Meal Type",
                          color="demand_count", color_continuous_scale="Oranges")
        st.plotly_chart(fig, use_container_width=True)
 
    except Exception as exc:
        st.error(f"Claims page error: {exc}")
 
# ─────────────────────────────────────────────────────────────────────────────
# 12. PAGE: ANALYSIS — All 17 Business Questions
# ─────────────────────────────────────────────────────────────────────────────
elif page == "📊 Analysis":
    st.title("📊 Analysis — All 17 Business Questions")
 
    QUESTIONS: dict[str, str | None] = {
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
            JOIN claims c       ON r.receiver_id = c.receiver_id
            JOIN food_listings f ON c.food_id    = f.food_id
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
            JOIN claims c        ON f.food_id     = c.food_id
            WHERE LOWER(c.status) = 'completed'
            GROUP BY p.name ORDER BY success_count DESC LIMIT 1""",
 
        "Q11 · Claim Status Percentage": """
            SELECT status,
                   ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) AS percentage
            FROM claims GROUP BY status""",
 
        "Q12 · Average Quantity per Receiver": """
            SELECT r.name, ROUND(AVG(f.quantity), 2) AS avg_quantity
            FROM receivers r
            JOIN claims c       ON r.receiver_id = c.receiver_id
            JOIN food_listings f ON c.food_id    = f.food_id
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
                       SUM(CASE WHEN LOWER(c.status) = 'completed' THEN 1 ELSE 0 END) * 100.0
                       / NULLIF(COUNT(c.claim_id), 0), 1
                   ) AS success_rate_percentage
            FROM providers p
            JOIN food_listings f ON p.provider_id = f.provider_id
            JOIN claims c        ON f.food_id     = c.food_id
            GROUP BY p.name ORDER BY success_rate_percentage DESC""",
 
        "Q17 · Demand by City & Meal Type": """
            SELECT r.city, f.meal_type, COUNT(c.claim_id) AS demand_count
            FROM receivers r
            JOIN claims c       ON r.receiver_id = c.receiver_id
            JOIN food_listings f ON c.food_id    = f.food_id
            GROUP BY r.city, f.meal_type ORDER BY demand_count DESC""",
    }
 
    selected_q = st.selectbox("Select a question to analyse", list(QUESTIONS.keys()))
 
    if selected_q == "Q4 · Providers in Selected City":
        city_input = st.text_input("Enter City Name", value=city_filter or "")
        if city_input:
            safe_city = city_input.replace("'", "''")
            try:
                df = run_query(
                    f"SELECT name, contact, address FROM providers WHERE LOWER(city) = LOWER('{safe_city}')"
                )
                st.dataframe(df, use_container_width=True)
            except Exception as exc:
                st.error(str(exc))
    else:
        sql = QUESTIONS[selected_q]
        if sql:
            try:
                df = run_query(sql)
                st.dataframe(df, use_container_width=True)
 
                num_cols = df.select_dtypes(include="number").columns.tolist()
                cat_cols = df.select_dtypes(exclude="number").columns.tolist()
 
                if cat_cols and num_cols:
                    x_col, y_col = cat_cols[0], num_cols[0]
                    if len(df) == 1:
                        val  = df[y_col].iloc[0]
                        name = df[x_col].iloc[0]
                        st.metric(label=f"{y_col} ({name})", value=f"{val:,.2f}")
                    elif len(df) <= 6:
                        fig = px.pie(df, names=x_col, values=y_col, title=selected_q,
                                     color_discrete_sequence=px.colors.qualitative.Set2, hole=0.3)
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        fig = px.bar(df, x=x_col, y=y_col, title=selected_q,
                                     color=y_col, color_continuous_scale="Blues")
                        fig.update_xaxes(tickangle=-35)
                        st.plotly_chart(fig, use_container_width=True)
 
                elif len(num_cols) == 1 and not cat_cols:
                    st.metric(selected_q, f"{df[num_cols[0]].iloc[0]:,.0f}")
 
                csv = df.to_csv(index=False).encode()
                st.download_button(
                    "⬇️ Download Results as CSV", csv,
                    file_name=f"{re.sub(r'[^a-z0-9]', '_', selected_q.lower())}.csv",
                    mime="text/csv",
                )
            except Exception as exc:
                st.error(f"Query error: {exc}")
 
# ─────────────────────────────────────────────────────────────────────────────
# 13. PAGE: CRUD OPERATIONS
# ─────────────────────────────────────────────────────────────────────────────
elif page == "✏️ CRUD Operations":
    st.title("✏️ CRUD Operations")
    st.caption("Create, Read, Update and Delete records across all tables")
 
    crud_table = st.selectbox(
        "Select Table",
        ["providers", "receivers", "food_listings", "claims"],
        key="crud_table_select",
    )
    crud_op = st.radio(
        "Operation",
        ["➕ Create", "📖 Read", "✏️ Update", "🗑️ Delete"],
        horizontal=True,
        key="crud_op_radio",
    )
    st.markdown("---")
 
    # ── Helpers ───────────────────────────────────────────────────────────────
    def load_table_filtered(table: str) -> pd.DataFrame:
        conds = []
        if table == "providers" and city_filter:
            conds.append(f"city = '{city_filter}'")
        elif table == "receivers" and city_filter:
            conds.append(f"city = '{city_filter}'")
        elif table == "food_listings":
            if ft_filter:
                conds.append(f"food_type = '{ft_filter}'")
            if mt_filter:
                conds.append(f"meal_type = '{mt_filter}'")
            if city_filter:
                conds.append(f"location = '{city_filter}'")
        elif table == "claims" and cs_filter:
            conds.append(f"status = '{cs_filter}'")
        return run_query(f"SELECT * FROM {table} {build_where(*conds)} ORDER BY 1")
 
    def dropdown_options(table: str, id_col: str, name_col: str, scope_city: str | None = None) -> dict:
        try:
            city_col = "location" if table == "food_listings" else "city"
            sql = f"SELECT {id_col}, {name_col} FROM {table}"
            if scope_city:
                sql += f" WHERE {city_col} = '{scope_city.replace(chr(39), chr(39)*2)}'"
            sql += f" ORDER BY {name_col}"
            rows = run_query(sql)
            return {f"{r[name_col]} ({r[id_col]})": r[id_col] for _, r in rows.iterrows()}
        except Exception:
            return {}
 
    PROVIDER_TYPES = ["Restaurant", "Grocery Store", "Bakery", "Catering", "Farm", "Other"]
    RECEIVER_TYPES = ["NGO", "Shelter", "School", "Hospital", "Individual", "Other"]
    FOOD_TYPES     = ["Vegetarian", "Non-Vegetarian", "Vegan", "Gluten-Free", "Other"]
    MEAL_TYPES     = ["Breakfast", "Lunch", "Dinner", "Snack", "Any"]
    CLAIM_STATUSES = ["Pending", "Completed", "Cancelled"]
 
    # ══════ CREATE ════════════════════════════════════════════════════════════
    if crud_op == "➕ Create":
        st.markdown('<div class="section-header">➕ Add New Record</div>', unsafe_allow_html=True)
 
        if crud_table == "providers":
            with st.form("form_create_provider", clear_on_submit=True):
                st.subheader("New Provider")
                c1, c2 = st.columns(2)
                prov_id   = c1.text_input("Provider ID *", placeholder="e.g. P999")
                prov_name = c2.text_input("Name *")
                c3, c4 = st.columns(2)
                prov_type = c3.selectbox("Type", PROVIDER_TYPES)
                prov_city = c4.text_input("City *", value=city_filter or "")
                prov_addr = st.text_input("Address")
                prov_cont = st.text_input("Contact")
                st.markdown("---")
                if st.form_submit_button("✅ Add Provider", use_container_width=True, type="primary"):
                    if not prov_id or not prov_name or not prov_city:
                        st.error("Provider ID, Name and City are required.")
                    elif run_write(
                        "INSERT INTO providers (provider_id, name, type, city, address, contact) "
                        "VALUES (:provider_id, :name, :type, :city, :address, :contact)",
                        dict(provider_id=prov_id, name=prov_name, type=prov_type,
                             city=prov_city, address=prov_addr, contact=prov_cont),
                    ):
                        st.success(f"Provider '{prov_name}' added successfully!")
 
        elif crud_table == "receivers":
            with st.form("form_create_receiver", clear_on_submit=True):
                st.subheader("New Receiver")
                c1, c2 = st.columns(2)
                rec_id   = c1.text_input("Receiver ID *", placeholder="e.g. R999")
                rec_name = c2.text_input("Name *")
                c3, c4 = st.columns(2)
                rec_type = c3.selectbox("Type", RECEIVER_TYPES)
                rec_city = c4.text_input("City *", value=city_filter or "")
                rec_cont = st.text_input("Contact")
                st.markdown("---")
                if st.form_submit_button("✅ Add Receiver", use_container_width=True, type="primary"):
                    if not rec_id or not rec_name or not rec_city:
                        st.error("Receiver ID, Name and City are required.")
                    elif run_write(
                        "INSERT INTO receivers (receiver_id, name, type, city, contact) "
                        "VALUES (:receiver_id, :name, :type, :city, :contact)",
                        dict(receiver_id=rec_id, name=rec_name, type=rec_type,
                             city=rec_city, contact=rec_cont),
                    ):
                        st.success(f"Receiver '{rec_name}' added successfully!")
 
        elif crud_table == "food_listings":
            prov_opts = dropdown_options("providers", "provider_id", "name", city_filter)
            with st.form("form_create_food", clear_on_submit=True):
                st.subheader("New Food Listing")
                c1, c2 = st.columns(2)
                food_id   = c1.text_input("Food ID *", placeholder="e.g. F999")
                food_name = c2.text_input("Food Name *")
                c3, c4 = st.columns(2)
                food_qty  = c3.number_input("Quantity *", min_value=1, value=1, step=1)
                food_exp  = c4.date_input("Expiry Date", value=date.today())
                c5, c6 = st.columns(2)
                food_type  = c5.selectbox("Food Type", FOOD_TYPES)
                meal_type  = c6.selectbox("Meal Type", MEAL_TYPES)
                c7, c8 = st.columns(2)
                food_loc   = c7.text_input("Location (City)", value=city_filter or "")
                prov_label = c8.selectbox(
                    "Provider *",
                    list(prov_opts.keys()) if prov_opts else ["— no providers found —"],
                )
                prov_type_val = st.text_input("Provider Type Label", placeholder="e.g. Restaurant")
                st.markdown("---")
                if st.form_submit_button("✅ Add Food Listing", use_container_width=True, type="primary"):
                    if not food_id or not food_name or not prov_opts:
                        st.error("Food ID, Food Name, and a valid Provider are required.")
                    elif run_write(
                        "INSERT INTO food_listings "
                        "(food_id, food_name, quantity, expiry_date, food_type, meal_type, location, provider_type, provider_id) "
                        "VALUES (:food_id, :food_name, :quantity, :expiry_date, :food_type, :meal_type, :location, :provider_type, :provider_id)",
                        dict(food_id=food_id, food_name=food_name, quantity=int(food_qty),
                             expiry_date=str(food_exp), food_type=food_type, meal_type=meal_type,
                             location=food_loc, provider_type=prov_type_val,
                             provider_id=prov_opts[prov_label]),
                    ):
                        st.success(f"Food listing '{food_name}' created!")
 
        elif crud_table == "claims":
            food_opts = dropdown_options("food_listings", "food_id", "food_name", city_filter)
            recv_opts = dropdown_options("receivers", "receiver_id", "name", city_filter)
            with st.form("form_create_claim", clear_on_submit=True):
                st.subheader("New Claim")
                c1, c2 = st.columns(2)
                claim_id = c1.text_input("Claim ID *", placeholder="e.g. C999")
                status   = c2.selectbox("Status", CLAIM_STATUSES)
                c3, c4 = st.columns(2)
                food_label = c3.selectbox(
                    "Food Item *",
                    list(food_opts.keys()) if food_opts else ["— no food items found —"],
                )
                recv_label = c4.selectbox(
                    "Receiver *",
                    list(recv_opts.keys()) if recv_opts else ["— no receivers found —"],
                )
                claim_ts = st.date_input("Claim Date", value=date.today())
                st.markdown("---")
                if st.form_submit_button("✅ Add Claim", use_container_width=True, type="primary"):
                    if not claim_id or not food_opts or not recv_opts:
                        st.error("Claim ID, Food Item and Receiver are required.")
                    elif run_write(
                        "INSERT INTO claims (claim_id, food_id, receiver_id, status, claim_timestamp) "
                        "VALUES (:claim_id, :food_id, :receiver_id, :status, :claim_timestamp)",
                        dict(claim_id=claim_id, food_id=food_opts[food_label],
                             receiver_id=recv_opts[recv_label], status=status,
                             claim_timestamp=str(claim_ts)),
                    ):
                        st.success(f"Claim '{claim_id}' created!")
 
    # ══════ READ ══════════════════════════════════════════════════════════════
    elif crud_op == "📖 Read":
        st.markdown('<div class="section-header">📖 View Records</div>', unsafe_allow_html=True)
        st.info("Global sidebar filters are applied automatically.")
 
        search_read = st.text_input("🔎 Search within results", key="crud_read_search")
        try:
            df = load_table_filtered(crud_table)
            if search_read:
                mask = df.apply(
                    lambda col: col.astype(str).str.lower().str.contains(search_read.lower(), na=False)
                ).any(axis=1)
                df = df[mask]
            st.markdown(f"**{len(df):,} records in `{crud_table}`**")
            st.dataframe(df, use_container_width=True, height=400)
            csv = df.to_csv(index=False).encode()
            st.download_button("⬇️ Download as CSV", csv, f"{crud_table}_export.csv", "text/csv")
        except Exception as exc:
            st.error(f"Read error: {exc}")
 
    # ══════ UPDATE ════════════════════════════════════════════════════════════
    elif crud_op == "✏️ Update":
        st.markdown('<div class="section-header">✏️ Update an Existing Record</div>', unsafe_allow_html=True)
 
        if crud_table == "providers":
            upd_id = st.text_input("Enter Provider ID to edit", placeholder="e.g. P001")
            if upd_id:
                row_df = run_query("SELECT * FROM providers WHERE provider_id = :id", {"id": upd_id})
                if row_df.empty:
                    st.warning(f"No provider found with ID: {upd_id}")
                else:
                    row = row_df.iloc[0]
                    with st.form("form_update_provider"):
                        st.subheader(f"Editing Provider: {upd_id}")
                        c1, c2 = st.columns(2)
                        new_name = c1.text_input("Name", value=str(row.get("name", "")))
                        curr_t   = str(row.get("type", "Other"))
                        new_type = c2.selectbox(
                            "Type", PROVIDER_TYPES,
                            index=PROVIDER_TYPES.index(curr_t) if curr_t in PROVIDER_TYPES else len(PROVIDER_TYPES) - 1,
                        )
                        c3, c4 = st.columns(2)
                        new_city = c3.text_input("City", value=str(row.get("city", "")))
                        new_cont = c4.text_input("Contact", value=str(row.get("contact", "")))
                        new_addr = st.text_input("Address", value=str(row.get("address", "")))
                        st.markdown("---")
                        if st.form_submit_button("✏️ Save Changes", use_container_width=True, type="primary"):
                            if run_write(
                                "UPDATE providers SET name=:name, type=:type, city=:city, "
                                "address=:address, contact=:contact WHERE provider_id=:id",
                                dict(name=new_name, type=new_type, city=new_city,
                                     address=new_addr, contact=new_cont, id=upd_id),
                            ):
                                st.success("Provider updated successfully!")
 
        elif crud_table == "receivers":
            upd_id = st.text_input("Enter Receiver ID to edit", placeholder="e.g. R001")
            if upd_id:
                row_df = run_query("SELECT * FROM receivers WHERE receiver_id = :id", {"id": upd_id})
                if row_df.empty:
                    st.warning(f"No receiver found with ID: {upd_id}")
                else:
                    row = row_df.iloc[0]
                    with st.form("form_update_receiver"):
                        st.subheader(f"Editing Receiver: {upd_id}")
                        c1, c2 = st.columns(2)
                        new_name = c1.text_input("Name", value=str(row.get("name", "")))
                        curr_t   = str(row.get("type", "Other"))
                        new_type = c2.selectbox(
                            "Type", RECEIVER_TYPES,
                            index=RECEIVER_TYPES.index(curr_t) if curr_t in RECEIVER_TYPES else len(RECEIVER_TYPES) - 1,
                        )
                        c3, c4 = st.columns(2)
                        new_city = c3.text_input("City", value=str(row.get("city", "")))
                        new_cont = c4.text_input("Contact", value=str(row.get("contact", "")))
                        st.markdown("---")
                        if st.form_submit_button("✏️ Save Changes", use_container_width=True, type="primary"):
                            if run_write(
                                "UPDATE receivers SET name=:name, type=:type, city=:city, "
                                "contact=:contact WHERE receiver_id=:id",
                                dict(name=new_name, type=new_type, city=new_city,
                                     contact=new_cont, id=upd_id),
                            ):
                                st.success("Receiver updated successfully!")
 
        elif crud_table == "food_listings":
            upd_id = st.text_input("Enter Food ID to edit", placeholder="e.g. F001")
            if upd_id:
                row_df = run_query("SELECT * FROM food_listings WHERE food_id = :id", {"id": upd_id})
                if row_df.empty:
                    st.warning(f"No food listing found with ID: {upd_id}")
                else:
                    row = row_df.iloc[0]
                    with st.form("form_update_food"):
                        st.subheader(f"Editing Food Listing: {upd_id}")
                        c1, c2 = st.columns(2)
                        new_fname = c1.text_input("Food Name", value=str(row.get("food_name", "")))
                        new_qty   = c2.number_input("Quantity", min_value=0, value=int(row.get("quantity", 0)))
 
                        try:
                            exp_val = pd.to_datetime(row.get("expiry_date", date.today())).date()
                        except Exception:
                            exp_val = date.today()
 
                        c3, c4 = st.columns(2)
                        new_exp = c3.date_input("Expiry Date", value=exp_val)
                        new_loc = c4.text_input("Location", value=str(row.get("location", "")))
 
                        curr_ft = str(row.get("food_type", ""))
                        curr_mt = str(row.get("meal_type", ""))
                        c5, c6 = st.columns(2)
                        new_ft = c5.selectbox(
                            "Food Type", FOOD_TYPES,
                            index=FOOD_TYPES.index(curr_ft) if curr_ft in FOOD_TYPES else 0,
                        )
                        new_mt = c6.selectbox(
                            "Meal Type", MEAL_TYPES,
                            index=MEAL_TYPES.index(curr_mt) if curr_mt in MEAL_TYPES else 0,
                        )
                        st.markdown("---")
                        if st.form_submit_button("✏️ Save Changes", use_container_width=True, type="primary"):
                            if run_write(
                                "UPDATE food_listings SET food_name=:food_name, quantity=:quantity, "
                                "expiry_date=:expiry_date, food_type=:food_type, meal_type=:meal_type, "
                                "location=:location WHERE food_id=:id",
                                dict(food_name=new_fname, quantity=int(new_qty),
                                     expiry_date=str(new_exp), food_type=new_ft,
                                     meal_type=new_mt, location=new_loc, id=upd_id),
                            ):
                                st.success("Food listing updated successfully!")
 
        elif crud_table == "claims":
            upd_id = st.text_input("Enter Claim ID to edit", placeholder="e.g. C001")
            if upd_id:
                row_df = run_query("SELECT * FROM claims WHERE claim_id = :id", {"id": upd_id})
                if row_df.empty:
                    st.warning(f"No claim found with ID: {upd_id}")
                else:
                    row = row_df.iloc[0]
                    with st.form("form_update_claim"):
                        st.subheader(f"Editing Claim: {upd_id}")
                        curr_s = str(row.get("status", "Pending"))
                        new_status = st.selectbox(
                            "Status", CLAIM_STATUSES,
                            index=CLAIM_STATUSES.index(curr_s) if curr_s in CLAIM_STATUSES else 0,
                        )
                        try:
                            ts_val = pd.to_datetime(row.get("claim_timestamp", date.today())).date()
                        except Exception:
                            ts_val = date.today()
                        new_ts = st.date_input("Claim Date", value=ts_val)
                        st.markdown("---")
                        if st.form_submit_button("✏️ Save Changes", use_container_width=True, type="primary"):
                            if run_write(
                                "UPDATE claims SET status=:status, claim_timestamp=:ts WHERE claim_id=:id",
                                dict(status=new_status, ts=str(new_ts), id=upd_id),
                            ):
                                st.success("Claim updated successfully!")
 
    # ══════ DELETE ════════════════════════════════════════════════════════════
    elif crud_op == "🗑️ Delete":
        st.markdown('<div class="section-header">🗑️ Delete a Record</div>', unsafe_allow_html=True)
        st.warning("⚠️ Deletion is permanent and may affect related records in other tables.")
 
        ID_COLUMNS = {
            "providers":     "provider_id",
            "receivers":     "receiver_id",
            "food_listings": "food_id",
            "claims":        "claim_id",
        }
        pk_col = ID_COLUMNS[crud_table]
 
        try:
            preview_df = load_table_filtered(crud_table)
            st.markdown(f"**Records currently in `{crud_table}` (filtered view):**")
            st.dataframe(preview_df, use_container_width=True, height=220)
        except Exception as exc:
            st.error(f"Could not load preview: {exc}")
 
        with st.form("form_delete_record"):
            del_id = st.text_input(
                f"Enter `{pk_col}` of the record to delete",
                placeholder="Double-check the ID before deleting",
            )
            confirmed = st.checkbox("I confirm this deletion is intentional and irreversible.")
            st.markdown("---")
            if st.form_submit_button("🗑️ Delete Record", use_container_width=True, type="primary"):
                if not del_id:
                    st.error("Please enter a valid ID.")
                elif not confirmed:
                    st.error("Please tick the confirmation checkbox to proceed.")
                elif run_write(
                    f"DELETE FROM {crud_table} WHERE {pk_col} = :id", {"id": del_id}
                ):
                    st.success(f"Record `{del_id}` deleted from `{crud_table}`.")
 
# ─────────────────────────────────────────────────────────────────────────────
# 14. PAGE: IMPORT CSVs
# ─────────────────────────────────────────────────────────────────────────────
elif page == "⬆️ Import CSVs":
    st.title("⬆️ Import CSV Files")
    st.info("Click **Import All** to load/refresh all four CSV files into the database, or upload individually below.")
 
    st.markdown("### Configured CSV Paths")
    for k, v in CSV_PATHS.items():
        icon = "✅" if os.path.exists(v) else "❌"
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
                box_cls = "success-box" if ok else "error-box"
                st.markdown(f'<div class="{box_cls}">{msg}</div>', unsafe_allow_html=True)
                if not ok:
                    all_ok = False
            if all_ok:
                run_query.clear()
                st.success("All tables imported! Cache refreshed.")
 
    with col_b:
        st.markdown("### Upload a CSV Manually")
        table_choice = st.selectbox("Target Table", ["providers", "receivers", "food_listings", "claims"])
        uploaded = st.file_uploader("Choose CSV", type=["csv"])
        if uploaded and st.button("Import Uploaded CSV"):
            with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
                tmp.write(uploaded.read())
                tmp_path = tmp.name
            engine = get_engine()
            ok, msg = import_csv(table_choice, tmp_path, engine)
            box_cls = "success-box" if ok else "error-box"
            st.markdown(f'<div class="{box_cls}">{msg}</div>', unsafe_allow_html=True)
            if ok:
                run_query.clear()
 
# ─────────────────────────────────────────────────────────────────────────────
# 15. PAGE: RAW SQL
# ─────────────────────────────────────────────────────────────────────────────
elif page == "🔧 Raw SQL":
    st.title("🔧 Raw SQL Query Runner")
    st.warning("⚠️ Only SELECT / WITH queries are permitted.")
 
    sql_input = st.text_area("Enter SQL", value="SELECT * FROM food_listings LIMIT 10;", height=180)
 
    if st.button("▶ Run Query", use_container_width=False):
        stripped = sql_input.strip().lstrip("(").upper()
        if not (stripped.startswith("SELECT") or stripped.startswith("WITH")):
            st.error("Only SELECT / WITH queries are allowed.")
        else:
            try:
                df = run_query(sql_input)
                st.success(f"{len(df):,} rows returned")
                st.dataframe(df, use_container_width=True, height=400)
                csv = df.to_csv(index=False).encode()
                st.download_button("⬇️ Download CSV", csv, "query_result.csv", "text/csv")
            except Exception as exc:
                st.error(f"Query failed: {exc}")
 
# ─────────────────────────────────────────────────────────────────────────────
# 16. FOOTER
# ─────────────────────────────────────────────────────────────────────────────
st.markdown(
    """<hr style="margin-top:40px">
    <p style="text-align:center;color:#9e9e9e;font-size:0.8rem">
    🍱 Food Analysis Dashboard &nbsp;•&nbsp; Built with Streamlit + PostgreSQL + Plotly
    </p>""",
    unsafe_allow_html=True,
)