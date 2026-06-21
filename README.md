# 🍱 Food Analysis Dashboard — Quick Start

## 1. Install dependencies (once)
```bash
pip install streamlit pandas plotly psycopg2-binary sqlalchemy
```

## 2. Edit DB_CONFIG in food_dashboard.py
Open the file and update these lines near the top:
```python
DB_CONFIG = dict(
    host     = "localhost",   # your PostgreSQL host
    port     = 5432,
    database = "Food_Analysis",
    user     = "food_user",
    password = "food1234",
)
```

## 3. Edit CSV_PATHS (only if your paths differ)
```python
CSV_PATHS = dict(
    providers    = r"C:/New folder/.../providers_data.csv",
    receivers    = r"C:/New folder/.../receivers_data.csv",
    food_listings= r"C:/New folder/.../food_listings_data.csv",
    claims       = r"C:/New folder/.../claims_data.csv",
)
```

## 4. Run the dashboard
```bash
streamlit run food_dashboard.py
```

The browser opens automatically at http://localhost:8501

---

## Pages & Features

| Page | What it shows |
|------|--------------|
| 🏠 Overview | 6 KPI cards + 4 quick charts |
| 📦 Providers | Searchable table + city & type charts |
| 🤝 Receivers | Searchable table + claimed qty charts |
| 🥗 Food Listings | Expiry status, heatmap, 3 charts |
| 📋 Claims | Status/timeline/sunburst + success rate |
| 📊 Analysis | All 17 SQL questions with auto-charts |
| ⬆️ Import CSVs | One-click import + manual file upload |
| 🔧 Raw SQL | Ad-hoc SELECT runner with CSV export |

## Sidebar Filters (applied globally)
- City, Food Type, Meal Type, Claim Status
- Refresh cache button

## Notes
- Data cache refreshes every **2 minutes** automatically.
- Click **🔄 Refresh Data Cache** in the sidebar to force a refresh.
- The Import CSVs page uses `to_sql(..., if_exists="replace")` — safe to re-run.
