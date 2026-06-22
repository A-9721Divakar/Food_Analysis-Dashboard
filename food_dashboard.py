"""
╔══════════════════════════════════════════════════════════════════════╗
║        FOOD ANALYSIS DASHBOARD  — Streamlit + PostgreSQL            ║
║    Run:  streamlit run food_dashboard.py                             ║
╚══════════════════════════════════════════════════════════════════════╝

Requirements (install once):
    pip install streamlit pandas plotly psycopg2-binary sqlalchemy

Cloud Configuration:
    Add your credentials in App Settings → Secrets on your Streamlit Dashboard:
    [postgres]
    host     = "your-cloud-db-host.tech"
    port     = 5432
    database = "Food_Analysis"
    user     = "food_user"
    password = "food1234"
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
# 1. DATABASE CONNECTION MANAGEMENT (Secrets Overrides Localhost)
# ─────────────────────────────────────────────────────────────────────────────
def _get_db_url() -> str:
    """Dynamically build connection string favoring Cloud Secrets over local fallback."""
    # 1. Try Structured [postgres] secret block (Recommended for Cloud Deployment)
    try:
        pg = st.secrets["postgres"]
        return (
            f"postgresql+psycopg2://{pg['user']}:{pg['password']}"
            f"@{pg['host']}:{pg.get('port', 5432)}/{pg['database']}"
        )
    except (KeyError, FileNotFoundError):
        pass

    # 2. Try Single DATABASE_URL secret
    url = st.secrets.get("DATABASE_URL")
    if url:
        return url.replace("postgres://", "postgresql+psycopg2://", 1)

    # 3. Fallback to Local Settings
    local_host = "localhost"
    local_user = "food_user"
    local_pass = "food1234"
    local_port = 5432
    local_db   = "Food_Analysis"
    return f"postgresql+psycopg2://{local_user}:{local_pass}@{local_host}:{local_port}/{local_db}"


@st.cache_resource(show_spinner="Connecting to database…")
def get_engine():
    db_url = _get_db_url()
    return create_engine(db_url, pool_pre_ping=True)


def run_query(sql: str, params: dict | None = None) -> pd.DataFrame:
    try:
        engine = get_engine()
        with engine.connect() as conn:
            return pd.read_sql(text(sql), conn, params=params or {})
    except Exception as e:
        # Graceful handling for uninitialized tables/databases
        st.warning(f"Database table notice: {e}")
        return pd.DataFrame()

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
.stApp { background: #f0f4f8; }
section[data-testid="stSidebar"] { background: #1a3c5e; }
section[data-testid="stSidebar"] * { color: #e8f0fe !important; }
section[data-testid="stSidebar"] .stSelectbox label { color: #a8c8f8 !important; }

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
.success-box { background:#e8f5e9; border-left:4px solid #4caf50; padding:10px 16px; border-radius:6px; margin:6px 0; }
.error-box { background:#ffebee; border-left:4px solid #f44336; padding:10px 16px; border-radius:6px; margin:6px 0; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# 4. CSV IMPORT ENGINE
# ─────────────────────────────────────────────────────────────────────────────
def import_csv(table: str, file_obj) -> tuple[bool, str]:
    try:
        engine = get_engine()
        df = pd.read_csv(file_obj)
        df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
        for col in df.columns:
            if "date" in col or "timestamp" in col:
                df[col] = pd.to_datetime(df[col], errors="coerce")
        df.to_sql(table.lower(), engine, if_exists="replace", index=False)
        return True, f"✅ Imported {len(df):,} rows into **{table}**"
    except Exception as e:
        return False, f"❌ {table}: {e}"

# ─────────────────────────────────────────────────────────────────────────────
# 5. SIDEBAR NAVIGATION & DYNAMIC GLOBAL FILTERS
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🍱 Food Analysis")
    st.markdown("---")

    page = st.radio(
        "Navigate",
        ["🏠 Overview", "📦 Providers", "🤝 Receivers", "🥗 Food Listings", "📋 Claims", "📊 Analysis", "⬆️ Import CSVs", "🔧 Raw SQL"],
        label_visibility="collapsed"
    )

    st.markdown("---")
    st.markdown("### 🔍 Global Filters")

    # Fetch filter elements safely via run_query
    cities_df = run_query("SELECT DISTINCT city FROM providers UNION SELECT DISTINCT city FROM receivers ORDER BY city")
    all_cities = ["All"] + cities_df["city"].dropna().tolist() if not cities_df.empty else ["All"]
    sel_city = st.selectbox("City", all_cities)

    ft_df = run_query("SELECT DISTINCT food_type FROM food_listings ORDER BY food_type")
    all_ft = ["All"] + ft_df["food_type"].dropna().tolist() if not ft_df.empty else ["All"]
    sel_ft = st.selectbox("Food Type", all_ft)

    mt_df = run_query("SELECT DISTINCT meal_type FROM food_listings ORDER BY meal_type")
    all_mt = ["All"] + mt_df["meal_type"].dropna().tolist() if not mt_df.empty else ["All"]
    sel_mt = st.selectbox("Meal Type", all_mt)

    cs_df = run_query("SELECT DISTINCT status FROM claims ORDER BY status")
    all_cs = ["All"] + cs_df["status"].dropna().tolist() if not cs_df.empty else ["All"]
    sel_cs = st.selectbox("Claim Status", all_cs)

    # Clean filtering hooks to feed directly into parametrized raw queries
    query_params = {}
    where_clauses = []

    if sel_city != "All":
        query_params["city"] = sel_city
    if sel_ft != "All":
        query_params["food_type"] = sel_ft
    if sel_mt != "All":
        query_params["meal_type"] = sel_mt
    if sel_cs != "All":
        query_params["status"] = sel_cs

    st.markdown("---")
    if st.button("🔄 Refresh Data Cache"):
        run_query.clear()
        st.success("Cache cleared!")

# Helper to construct WHERE filters dynamically safely
def build_where_clause(conditions_list):
    return " WHERE " + " AND ".join(conditions_list) if conditions_list else ""

# ─────────────────────────────────────────────────────────────────────────────
# 6. PAGE CONTENT GENERATOR
# ─────────────────────────────────────────────────────────────────────────────

# 🏠 OVERVIEW PAGE
if page == "🏠 Overview":
    st.title("🍱 Food Analysis Dashboard")
    st.caption("Real-time insights connected to your PostgreSQL database instance")

    # KPI Parameter logic safely tracking variations across tables
    f_cond = []
    c_cond = []
    p_cond = []
    r_cond = []
    
    if "city" in query_params:
        p_cond.append("city = :city")
        r_cond.append("city = :city")
        f_cond.append("location = :city")
    if "food_type" in query_params:
        f_cond.append("food_type = :food_type")
    if "meal_type" in query_params:
        f_cond.append("meal_type = :meal_type")
    if "status" in query_params:
        c_cond.append("status = :status")

    # Fetch rows
    prov_df = run_query(f"SELECT COUNT(*) as n FROM providers{build_where_clause(p_cond)}", query_params)
    recv_df = run_query(f"SELECT COUNT(*) as n FROM receivers{build_where_clause(r_cond)}", query_params)
    food_df = run_query(f"SELECT COUNT(*) as n, COALESCE(SUM(quantity),0) as qty FROM food_listings{build_where_clause(f_cond)}", query_params)
    
    # Claims metrics combined with food listing attributes for dynamic cross-filtering
    claim_join_clause = ""
    if "food_type" in query_params or "meal_type" in query_params:
        claim_join_clause = " JOIN food_listings f ON c.food_id = f.food_id"
        if "food_type" in query_params: c_cond.append("f.food_type = :food_type")
        if "meal_type" in query_params: c_cond.append("f.meal_type = :meal_type")
    
    claims_df = run_query(f"SELECT COUNT(*) as n FROM claims c{claim_join_clause}{build_where_clause(c_cond)}", query_params)
    c_cond.append("LOWER(status)='completed'")
    comp_df = run_query(f"SELECT COUNT(*) as n FROM claims c{claim_join_clause}{build_where_clause(c_cond)}", query_params)

    # Render metrics cleanly
    if not prov_df.empty and not recv_df.empty and not food_df.empty:
        col1, col2, col3 = st.columns(3)
        col4, col5, col6 = st.columns(3)

        def render_kpi(col, label, value, color, suffix=""):
            col.markdown(f'<div class="kpi-card" style="border-left-color:{color}"><div class="kpi-value">{value:,}{suffix}</div><div class="kpi-label">{label}</div></div>', unsafe_allow_html=True)

        render_kpi(col1, "Total Providers", prov_df["n"].iloc[0], "#2196F3")
        render_kpi(col2, "Total Receivers", recv_df["n"].iloc[0], "#4CAF50")
        render_kpi(col3, "Food Listings", food_df["n"].iloc[0], "#FF9800")
        render_kpi(col4, "Total Claims", claims_df["n"].iloc[0] if not claims_df.empty else 0, "#9C27B0")
        render_kpi(col5, "Total Food Quantity", food_df["qty"].iloc[0], "#F44336", suffix=" units")
        render_kpi(col6, "Completed Claims", comp_df["n"].iloc[0] if not comp_df.empty else 0, "#009688")

        st.markdown('<div class="section-header">📈 Quick Charts</div>', unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            df = run_query(f"SELECT type, COUNT(*) AS total FROM providers {build_where_clause(p_cond)} GROUP BY type", query_params)
            if not df.empty:
                st.plotly_chart(px.pie(df, names="type", values="total", title="Providers by Type", color_discrete_sequence=px.colors.qualitative.Set2), use_container_width=True)
        with c2:
            df = run_query(f"SELECT food_type, SUM(quantity) AS total FROM food_listings {build_where_clause(f_cond)} GROUP BY food_type", query_params)
            if not df.empty:
                st.plotly_chart(px.bar(df, x="food_type", y="total", title="Food Quantity by Type", color="food_type", color_discrete_sequence=px.colors.qualitative.Pastel), use_container_width=True)
    else:
        st.info("👋 Database connected successfully! Go to 'Import CSVs' page to load your data records.")

# 📦 PROVIDERS PAGE
elif page == "📦 Providers":
    st.title("📦 Providers Management")
    search = st.text_input("🔎 Search provider name")
    
    p_cond = []
    if "city" in query_params: p_cond.append("p.city = :city")
    if search: p_cond.append("LOWER(p.name) LIKE :search") ; query_params["search"] = f"%{search.lower()}%"
    
    sql = f"""SELECT p.provider_id, p.name, p.type, p.city, p.contact, COUNT(f.food_id) AS listings, COALESCE(SUM(f.quantity),0) AS total_donated 
              FROM providers p LEFT JOIN food_listings f ON p.provider_id = f.provider_id 
              {build_where_clause(p_cond)} GROUP BY p.provider_id, p.name, p.type, p.city, p.contact ORDER BY total_donated DESC"""
    df = run_query(sql, query_params)
    st.markdown(f"**{len(df)} records found**")
    st.dataframe(df, use_container_width=True)

# 🤝 RECEIVERS PAGE
elif page == "🤝 Receivers":
    st.title("🤝 Receivers Tracker")
    r_cond = []
    if "city" in query_params: r_cond.append("r.city = :city")
    sql = f"""SELECT r.receiver_id, r.name, r.type, r.city, COUNT(c.claim_id) as claims_made FROM receivers r 
              LEFT JOIN claims c ON r.receiver_id = c.receiver_id {build_where_clause(r_cond)} GROUP BY r.receiver_id, r.name, r.type, r.city"""
    df = run_query(sql, query_params)
    st.dataframe(df, use_container_width=True)

# 🥗 FOOD LISTINGS PAGE
elif page == "🥗 Food Listings":
    st.title("🥗 Active Food Listings")
    f_cond = []
    if "city" in query_params: f_cond.append("location = :city")
    if "food_type" in query_params: f_cond.append("food_type = :food_type")
    if "meal_type" in query_params: f_cond.append("meal_type = :meal_type")
    
    df = run_query(f"SELECT * FROM food_listings {build_where_clause(f_cond)}", query_params)
    st.dataframe(df, use_container_width=True)

# 📋 CLAIMS PAGE
elif page == "📋 Claims":
    st.title("📋 Claims Management")
    c_cond = []
    if "status" in query_params: c_cond.append("c.status = :status")
    df = run_query(f"SELECT * FROM claims c {build_where_clause(c_cond)}", query_params)
    st.dataframe(df, use_container_width=True)

# 📊 ANALYSIS PAGE (All 17 Business Questions)
elif page == "📊 Analysis":
    st.title("📊 Structural Analytical Processing — 17 Core KPI Questions")
    
    QUESTIONS = {
        "Q1 · Providers per City": "SELECT city, COUNT(*) AS provider_count FROM providers GROUP BY city ORDER BY provider_count DESC",
        "Q2 · Receivers per City": "SELECT city, COUNT(*) AS receiver_count FROM receivers GROUP BY city ORDER BY receiver_count DESC",
        "Q3 · Provider Type with Highest Quantity": "SELECT provider_type, SUM(quantity) AS total_quantity FROM food_listings GROUP BY provider_type ORDER BY total_quantity DESC LIMIT 1",
        "Q4 · Providers in Selected City": "SELECT name, contact, address FROM providers WHERE LOWER(city) = LOWER(:city)",
        "Q5 · Receivers by Total Claimed Quantity": "SELECT r.name, SUM(f.quantity) AS total_claimed FROM receivers r JOIN claims c ON r.receiver_id = c.receiver_id JOIN food_listings f ON c.food_id = f.food_id GROUP BY r.name ORDER BY total_claimed DESC",
        "Q6 · Total Available Food Quantity": "SELECT SUM(quantity) AS total_available FROM food_listings",
        "Q7 · Location with Most Listings": "SELECT location, COUNT(*) AS listing_count FROM food_listings GROUP BY location ORDER BY listing_count DESC LIMIT 1",
        "Q8 · Food Availability by Food Type": "SELECT food_type, COUNT(*) AS availability_count FROM food_listings GROUP BY food_type ORDER BY availability_count DESC",
        "Q9 · Claims Count per Food Item": "SELECT food_id, COUNT(*) AS claim_count FROM claims GROUP BY food_id ORDER BY claim_count DESC",
        "Q10 · Provider with Most Completed Claims": "SELECT p.name, COUNT(c.claim_id) AS success_count FROM providers p JOIN food_listings f ON p.provider_id = f.provider_id JOIN claims c ON f.food_id = c.food_id WHERE LOWER(c.status) = 'completed' GROUP BY p.name ORDER BY success_count DESC LIMIT 1",
        "Q11 · Claim Status Percentage": "SELECT status, ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) AS percentage FROM claims GROUP BY status",
        "Q12 · Average Quantity per Receiver": "SELECT r.name, ROUND(AVG(f.quantity),2) AS avg_quantity FROM receivers r JOIN claims c ON r.receiver_id = c.receiver_id JOIN food_listings f ON c.food_id = f.food_id GROUP BY r.name ORDER BY avg_quantity DESC",
        "Q13 · Most Claimed Meal Type": "SELECT f.meal_type, COUNT(c.claim_id) AS claim_count FROM food_listings f JOIN claims c ON f.food_id = c.food_id GROUP BY f.meal_type ORDER BY claim_count DESC LIMIT 1",
        "Q14 · Total Donated per Provider": "SELECT p.name, SUM(f.quantity) AS total_donated FROM providers p JOIN food_listings f ON p.provider_id = f.provider_id GROUP BY p.name ORDER BY total_donated DESC",
        "Q15 · Food Wasted (Expired, Unclaimed)": "SELECT f.food_type, SUM(f.quantity) AS total_wasted_quantity FROM food_listings f LEFT JOIN claims c ON f.food_id = c.food_id WHERE c.claim_id IS NULL AND f.expiry_date < CURRENT_DATE GROUP BY f.food_type ORDER BY total_wasted_quantity DESC",
        "Q16 · Provider Success Rate (%)": "SELECT p.name, ROUND(SUM(CASE WHEN LOWER(c.status)='completed' THEN 1 ELSE 0 END)*100.0 / NULLIF(COUNT(c.claim_id),0), 1) AS success_rate_percentage FROM providers p JOIN food_listings f ON p.provider_id = f.provider_id JOIN claims c ON f.food_id = c.food_id GROUP BY p.name ORDER BY success_rate_percentage DESC",
        "Q17 · Demand by City & Meal Type": "SELECT r.city, f.meal_type, COUNT(c.claim_id) AS demand_count FROM receivers r JOIN claims c ON r.receiver_id = c.receiver_id JOIN food_listings f ON c.food_id = f.food_id GROUP BY r.city, f.meal_type ORDER BY demand_count DESC"
    }

    selected_q = st.selectbox("Select a question to analyze", list(QUESTIONS.keys()))
    sql = QUESTIONS[selected_q]
    
    # Inject active filter fallback parameters dynamically into analysis questions
    bind_params = {}
    if ":city" in sql:
        bind_params["city"] = sel_city if sel_city != "All" else "London" # Sensible fallback string

    df = run_query(sql, bind_params)
    st.dataframe(df, use_container_width=True)

    if not df.empty:
        num_cols = df.select_dtypes(include="number").columns.tolist()
        cat_cols = df.select_dtypes(exclude="number").columns.tolist()
        if cat_cols and num_cols:
            st.plotly_chart(px.bar(df, x=cat_cols[0], y=num_cols[0], title=selected_q, color=num_cols[0], color_continuous_scale="Blues"), use_container_width=True)

# ⬆️ IMPORT CSV PORTAL
elif page == "⬆️ Import CSVs":
    st.title("⬆️ Live Cloud Migration Portal")
    st.info("Upload your local datasets using the UI components below to initialize your cloud PostgreSQL database tables securely.")

    tables = ["providers", "receivers", "food_listings", "claims"]
    for t in tables:
        uploaded_file = st.file_uploader(f"Choose CSV file for table **{t}**", type=["csv"], key=f"file_{t}")
        if uploaded_file:
            if st.button(f"🚀 Initialize and Import {t.upper()}", key=f"btn_{t}"):
                ok, msg = import_csv(t, uploaded_file)
                if ok:
                    st.markdown(f'<div class="success-box">{msg}</div>', unsafe_allow_html=True)
                    run_query.clear()
                else:
                    st.markdown(f'<div class="error-box">{msg}</div>', unsafe_allow_html=True)

# 🔧 RAW SQL PANEL
elif page == "🔧 Raw SQL":
    st.title("🔧 Raw SQL Console")
    sql_input = st.text_area("SQL Engine Sandbox Console", value="SELECT * FROM food_listings LIMIT 5;")
    if st.button("Execute Command"):
        if "SELECT" in sql_input.upper() or "WITH" in sql_input.upper():
            df = run_query(sql_input)
            st.dataframe(df, use_container_width=True)
        else:
            st.error("Write/Mutation operations restricted to protect data state safety.")

# ─────────────────────────────────────────────────────────────────────────────
# 16. FOOTER
# ─────────────────────────────────────────────────────────────────────────────
st.markdown('<hr style="margin-top:40px"><p style="text-align:center;color:#9e9e9e;font-size:0.8rem">🍱 Food Analysis Dashboard • Powered by Streamlit Cloud Engine</p>', unsafe_allow_html=True)
