import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import random
 
# ─── Page Config ────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="🍽️ Food Dashboard",
    page_icon="🍽️",
    layout="wide",
    initial_sidebar_state="expanded",
)
 
# ─── Custom CSS ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .main { background-color: #f9f5f0; }
    .block-container { padding-top: 1.5rem; }
    .metric-card {
        background: white;
        border-radius: 12px;
        padding: 1.2rem 1.5rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.07);
        border-left: 4px solid #e07b39;
    }
    .metric-card h3 { margin: 0; font-size: 0.85rem; color: #888; text-transform: uppercase; letter-spacing: 0.05em; }
    .metric-card p  { margin: 0.3rem 0 0; font-size: 2rem; font-weight: 700; color: #1a1a1a; }
    .section-title  { font-size: 1.1rem; font-weight: 600; color: #333; margin-bottom: 0.5rem; }
    div[data-testid="stMetricValue"] { font-size: 2rem; }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px 8px 0 0;
        padding: 0.5rem 1.2rem;
        font-weight: 500;
    }
</style>
""", unsafe_allow_html=True)
 
# ─── Sample Data Generation ──────────────────────────────────────────────────
@st.cache_data
def generate_data():
    random.seed(42)
    np.random.seed(42)
 
    categories = ["Burgers", "Pizza", "Salads", "Pasta", "Desserts", "Beverages", "Sushi", "Tacos"]
    items = {
        "Burgers":   ["Classic Burger", "BBQ Burger", "Veggie Burger", "Double Patty"],
        "Pizza":     ["Margherita", "Pepperoni", "BBQ Chicken", "Veggie Supreme"],
        "Salads":    ["Caesar Salad", "Greek Salad", "Garden Fresh", "Quinoa Bowl"],
        "Pasta":     ["Carbonara", "Bolognese", "Pesto Pasta", "Alfredo"],
        "Desserts":  ["Cheesecake", "Brownie", "Ice Cream", "Tiramisu"],
        "Beverages": ["Fresh Juice", "Smoothie", "Cold Brew", "Lemonade"],
        "Sushi":     ["California Roll", "Salmon Nigiri", "Dragon Roll", "Spicy Tuna"],
        "Tacos":     ["Beef Taco", "Chicken Taco", "Fish Taco", "Veggie Taco"],
    }
 
    # Orders for last 90 days
    dates = [datetime.today() - timedelta(days=i) for i in range(89, -1, -1)]
    orders = []
    for date in dates:
        n = random.randint(30, 120)
        for _ in range(n):
            cat = random.choice(categories)
            item = random.choice(items[cat])
            price = round(random.uniform(5, 30), 2)
            qty = random.randint(1, 5)
            orders.append({
                "date": date.date(),
                "category": cat,
                "item": item,
                "price": price,
                "quantity": qty,
                "revenue": round(price * qty, 2),
                "rating": round(random.uniform(3.0, 5.0), 1),
                "table": random.randint(1, 20),
            })
 
    df = pd.DataFrame(orders)
 
    # Inventory
    inventory = []
    ingredients = ["Tomatoes", "Lettuce", "Chicken", "Beef", "Cheese", "Pasta", "Rice",
                   "Bread", "Salmon", "Avocado", "Eggs", "Milk", "Flour", "Olive Oil"]
    for ing in ingredients:
        stock = random.randint(10, 200)
        threshold = random.randint(20, 50)
        inventory.append({
            "ingredient": ing,
            "stock_kg": stock,
            "threshold_kg": threshold,
            "status": "⚠️ Low" if stock < threshold else "✅ OK",
            "cost_per_kg": round(random.uniform(1.5, 15.0), 2),
        })
 
    inv_df = pd.DataFrame(inventory)
    return df, inv_df, categories, items
 
df, inv_df, categories, items = generate_data()
 
# ─── Sidebar ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/restaurant.png", width=60)
    st.markdown("## 🍽️ Food Dashboard")
    st.markdown("---")
 
    st.markdown("### 📅 Date Range")
    date_min = df["date"].min()
    date_max = df["date"].max()
    start_date = st.date_input("From", value=date_min, min_value=date_min, max_value=date_max)
    end_date   = st.date_input("To",   value=date_max, min_value=date_min, max_value=date_max)
 
    st.markdown("### 🏷️ Category Filter")
    selected_cats = st.multiselect("Select categories", categories, default=categories)
 
    st.markdown("### ⭐ Min Rating")
    min_rating = st.slider("", 1.0, 5.0, 3.0, 0.1)
 
    st.markdown("---")
    st.caption("Data refreshes daily. Showing sample data.")
 
# ─── Filter Data ─────────────────────────────────────────────────────────────
mask = (
    (df["date"] >= start_date) &
    (df["date"] <= end_date) &
    (df["category"].isin(selected_cats)) &
    (df["rating"] >= min_rating)
)
filtered = df[mask].copy()
 
# ─── Header ──────────────────────────────────────────────────────────────────
st.markdown("# 🍽️ Food Analytics Dashboard")
st.caption(f"Showing data from **{start_date}** to **{end_date}** · {len(filtered):,} orders")
st.markdown("---")
 
# ─── KPI Row ─────────────────────────────────────────────────────────────────
k1, k2, k3, k4, k5 = st.columns(5)
 
total_revenue = filtered["revenue"].sum()
total_orders  = len(filtered)
avg_order_val = filtered["revenue"].mean() if total_orders else 0
avg_rating    = filtered["rating"].mean()   if total_orders else 0
top_category  = filtered.groupby("category")["revenue"].sum().idxmax() if total_orders else "—"
 
k1.metric("💰 Total Revenue",    f"₹{total_revenue:,.0f}")
k2.metric("📦 Total Orders",     f"{total_orders:,}")
k3.metric("🧾 Avg Order Value",  f"₹{avg_order_val:.2f}")
k4.metric("⭐ Avg Rating",       f"{avg_rating:.2f}")
k5.metric("🏆 Top Category",     top_category)
 
st.markdown("---")
 
# ─── Tabs ─────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs(["📈 Sales Trends", "🍕 Menu Insights", "📦 Inventory", "➕ Add Order"])
 
# ── Tab 1 : Sales Trends ──────────────────────────────────────────────────────
with tab1:
    col1, col2 = st.columns([2, 1])
 
    with col1:
        st.markdown("#### Daily Revenue")
        daily = filtered.groupby("date")["revenue"].sum().reset_index()
        fig_line = px.line(
            daily, x="date", y="revenue",
            labels={"revenue": "Revenue (₹)", "date": "Date"},
            color_discrete_sequence=["#e07b39"],
        )
        fig_line.update_traces(line_width=2.5, mode="lines+markers", marker_size=4)
        fig_line.update_layout(
            plot_bgcolor="white", paper_bgcolor="white",
            margin=dict(t=10, b=10), height=320,
        )
        st.plotly_chart(fig_line, use_container_width=True)
 
    with col2:
        st.markdown("#### Revenue by Category")
        cat_rev = filtered.groupby("category")["revenue"].sum().reset_index()
        fig_pie = px.pie(
            cat_rev, names="category", values="revenue",
            color_discrete_sequence=px.colors.qualitative.Pastel,
            hole=0.4,
        )
        fig_pie.update_layout(margin=dict(t=10, b=10), height=320, showlegend=True)
        st.plotly_chart(fig_pie, use_container_width=True)
 
    col3, col4 = st.columns(2)
 
    with col3:
        st.markdown("#### Orders by Day of Week")
        filtered["weekday"] = pd.to_datetime(filtered["date"]).dt.day_name()
        order_days = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
        dow = filtered.groupby("weekday")["revenue"].sum().reindex(order_days).reset_index()
        fig_bar = px.bar(
            dow, x="weekday", y="revenue",
            color="revenue", color_continuous_scale="Oranges",
            labels={"revenue": "Revenue (₹)", "weekday": ""},
        )
        fig_bar.update_layout(plot_bgcolor="white", paper_bgcolor="white",
                              margin=dict(t=10, b=10), height=280, coloraxis_showscale=False)
        st.plotly_chart(fig_bar, use_container_width=True)
 
    with col4:
        st.markdown("#### Hourly Order Heatmap (Simulated)")
        hours = list(range(8, 24))
        days  = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        heat  = np.random.randint(5, 80, size=(len(days), len(hours)))
        fig_heat = go.Figure(go.Heatmap(
            z=heat, x=[f"{h}:00" for h in hours], y=days,
            colorscale="YlOrRd", showscale=True,
        ))
        fig_heat.update_layout(margin=dict(t=10, b=10), height=280,
                               paper_bgcolor="white", plot_bgcolor="white")
        st.plotly_chart(fig_heat, use_container_width=True)
 
# ── Tab 2 : Menu Insights ──────────────────────────────────────────────────────
with tab2:
    col1, col2 = st.columns(2)
 
    with col1:
        st.markdown("#### Top 10 Items by Revenue")
        top_items = (
            filtered.groupby("item")["revenue"].sum()
            .sort_values(ascending=True).tail(10).reset_index()
        )
        fig_h = px.bar(
            top_items, x="revenue", y="item", orientation="h",
            color="revenue", color_continuous_scale="Oranges",
            labels={"revenue": "Revenue (₹)", "item": ""},
        )
        fig_h.update_layout(plot_bgcolor="white", paper_bgcolor="white",
                            margin=dict(t=10, b=10), height=360, coloraxis_showscale=False)
        st.plotly_chart(fig_h, use_container_width=True)
 
    with col2:
        st.markdown("#### Avg Rating by Category")
        rat = filtered.groupby("category")["rating"].mean().sort_values(ascending=False).reset_index()
        fig_rat = px.bar(
            rat, x="category", y="rating",
            color="rating", color_continuous_scale="RdYlGn", range_color=[3, 5],
            labels={"rating": "Avg Rating ⭐", "category": ""},
        )
        fig_rat.update_layout(plot_bgcolor="white", paper_bgcolor="white",
                              margin=dict(t=10, b=10), height=360, coloraxis_showscale=False)
        st.plotly_chart(fig_rat, use_container_width=True)
 
    st.markdown("#### Menu Performance Table")
    perf = filtered.groupby(["category", "item"]).agg(
        Orders=("quantity", "sum"),
        Revenue=("revenue", "sum"),
        Avg_Rating=("rating", "mean"),
    ).reset_index()
    perf["Revenue"] = perf["Revenue"].map("₹{:,.2f}".format)
    perf["Avg_Rating"] = perf["Avg_Rating"].map("{:.2f}".format)
    st.dataframe(perf, use_container_width=True, hide_index=True)
 
# ── Tab 3 : Inventory ──────────────────────────────────────────────────────────
with tab3:
    st.markdown("#### Inventory Status")
 
    low_stock = inv_df[inv_df["stock_kg"] < inv_df["threshold_kg"]]
    if not low_stock.empty:
        st.warning(f"⚠️ **{len(low_stock)} ingredient(s)** are below the reorder threshold!")
 
    col1, col2 = st.columns([1.5, 1])
 
    with col1:
        fig_inv = px.bar(
            inv_df.sort_values("stock_kg"),
            x="stock_kg", y="ingredient", orientation="h",
            color="status",
            color_discrete_map={"✅ OK": "#4CAF50", "⚠️ Low": "#FF6B35"},
            labels={"stock_kg": "Stock (kg)", "ingredient": ""},
        )
        fig_inv.update_layout(plot_bgcolor="white", paper_bgcolor="white",
                              margin=dict(t=10, b=10), height=420, showlegend=True)
        st.plotly_chart(fig_inv, use_container_width=True)
 
    with col2:
        st.markdown("#### Stock Table")
        display_inv = inv_df[["ingredient", "stock_kg", "threshold_kg", "status"]].copy()
        display_inv.columns = ["Ingredient", "Stock (kg)", "Min Threshold", "Status"]
        st.dataframe(display_inv, use_container_width=True, hide_index=True, height=420)
 
# ── Tab 4 : Add Order (fixed — uses st.form_submit_button) ────────────────────
with tab4:
    st.markdown("#### ➕ Log a New Order")
    st.info("This form is for demo purposes. Orders are not persisted in this sample build.")
 
    with st.form("add_order_form"):
        col1, col2, col3 = st.columns(3)
 
        with col1:
            form_category = st.selectbox("Category", categories)
        with col2:
            form_item = st.selectbox("Menu Item", items[form_category])
        with col3:
            form_table = st.number_input("Table Number", min_value=1, max_value=50, value=1)
 
        col4, col5, col6 = st.columns(3)
        with col4:
            form_qty = st.number_input("Quantity", min_value=1, max_value=20, value=1)
        with col5:
            form_price = st.number_input("Price (₹)", min_value=0.0, value=9.99, step=0.5)
        with col6:
            form_rating = st.slider("Customer Rating", 1.0, 5.0, 4.5, 0.5)
 
        form_notes = st.text_area("Special Instructions (optional)", placeholder="e.g. No onions, extra sauce…")
 
        # ✅ REQUIRED: st.form_submit_button() fixes the 'Missing Submit Button' error
        submitted = st.form_submit_button("✅ Submit Order", use_container_width=True, type="primary")
 
        if submitted:
            st.success(
                f"✅ Order logged! **{form_qty}× {form_item}** at Table {form_table} "
                f"for ₹{form_price * form_qty:.2f} — Rating: {form_rating}⭐"
            )
            if form_notes:
                st.info(f"📝 Notes: {form_notes}")
 
# ─── Footer ───────────────────────────────────────────────────────────────────
st.markdown("---")
st.caption("🍽️ Food Dashboard · Built with Streamlit & Plotly · Sample data only")
