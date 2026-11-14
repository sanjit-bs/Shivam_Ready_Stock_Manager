from datetime import date
import pandas as pd
import requests
import streamlit as st

# ======================================================
# Configuration
# ======================================================
st.set_page_config(page_title="Ready Product Stock Manager", page_icon="📦", layout="wide")
st.title("📦 Ready Product Stock Management")

APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbwZ5UOX93DVnrSuRPNdTs00GE1vGKoxGVSkCNN9g3pU7UNQKQwEe3uYnzx9YHZKKjGafw/exec"

UNIT_OPTIONS = ["pcs", "kg"]

# ======================================================
# Data Loader (Reads Main_Stock & Stock_History_Log)
# ======================================================
@st.cache_data(ttl=5)
def load_stock_and_logs():
    try:
        res = requests.get(f"{APPS_SCRIPT_URL}?action=read_all", timeout=30)
        data = res.json()
        if data.get("status") == "success":
            stock_df = pd.DataFrame(data.get("stock", []))
            logs_df = pd.DataFrame(data.get("logs", []))
            return stock_df, logs_df
    except Exception as e:
        st.error(f"Error connecting to Google Sheets: {e}")
    return pd.DataFrame(), pd.DataFrame()

stock_df, logs_df = load_stock_and_logs()

# Extract Master Companies from Main_Stock
master_companies = []
if not stock_df.empty and "Company Name" in stock_df.columns:
    master_companies = sorted([
        str(c).strip() for c in stock_df["Company Name"].dropna().unique() if str(c).strip() != ""
    ])

# ======================================================
# Session State Management
# ======================================================
if "form_key" not in st.session_state:
    st.session_state.form_key = 0

k = st.session_state.form_key

# ======================================================
# UI Tabs: Stock Entry | Live Main Stock | History Log
# ======================================================
tab_entry, tab_stock, tab_logs = st.tabs([
    "🏭 Production & Delivery Entry",
    "📊 Main Stock (Live Balance)",
    "📜 History Log"
])

# ------------------------------------------------------
# TAB 1: PRODUCTION & DELIVERY ENTRY
# ------------------------------------------------------
with tab_entry:
    col_prod, col_del = st.columns(2)

    # === POINT 1: PRODUCTION ENTRY (+) ===
    with col_prod:
        st.subheader("🏭 Production Entry (+ Stock)")
        with st.container(border=True):
            prod_date = st.date_input("Production Date *", value=date.today(), format="DD/MM/YYYY", key=f"p_date_{k}")

            # Company Dropdown loaded from Main_Stock + option to add new
            p_comp_options = ["Select Company"] + master_companies + ["Others (New Company)"]
            p_comp_sel = st.selectbox("Company Name *", options=p_comp_options, key=f"p_comp_sel_{k}")

            if p_comp_sel == "Others (New Company)":
                p_company = st.text_input("Enter New Company Name *", key=f"p_comp_new_{k}")
            else:
                p_company = p_comp_sel

            # Filter products from Main_Stock for selected company
            comp_products = []
            if p_comp_sel not in ["Select Company", "Others (New Company)"] and not stock_df.empty:
                filtered = stock_df[stock_df["Company Name"].astype(str).str.strip() == p_comp_sel]
                comp_products = sorted([
                    str(p).strip() for p in filtered["Product Name"].dropna().unique() if str(p).strip() != ""
                ])

            p_prod_options = ["Select Product"] + comp_products + ["Others (New Product)"]
            p_prod_sel = st.selectbox("Product Name *", options=p_prod_options, key=f"p_prod_sel_{k}")

            if p_prod_sel == "Others (New Product)":
                p_product = st.text_input("Enter New Product Name *", key=f"p_prod_new_{k}")
            else:
                p_product = p_prod_sel

            # Auto-detect existing unit if product already exists in Main_Stock
            p_default_unit = "per pcs"
            if p_prod_sel not in ["Select Product", "Others (New Product)"] and not stock_df.empty:
                match = stock_df[
                    (stock_df["Company Name"].astype(str).str.strip() == p_company) &
                    (stock_df["Product Name"].astype(str).str.strip() == p_product)
                ]
                if not match.empty:
                    p_default_unit = str(match.iloc[0]["Unit"]).strip()

            p_qty = st.number_input("Produced Quantity *", min_value=0.0, value=0.0, step=1.0, format="%.2f", key=f"p_qty_{k}")
            p_unit = st.selectbox(
                "Unit *",
                options=UNIT_OPTIONS,
                index=UNIT_OPTIONS.index(p_default_unit) if p_default_unit in UNIT_OPTIONS else 0,
                key=f"p_unit_{k}"
            )
            p_batch = st.text_input("Batch / Shift No. (Optional)", placeholder="e.g. Shift-A / B-102", key=f"p_ref_{k}")
            p_remark = st.text_input("Remark (Optional)", key=f"p_rem_{k}")

            if st.button("➕ Add Production Stock", type="primary", use_container_width=True):
                if p_comp_sel == "Select Company" or not p_company.strip():
                    st.warning("Please select or enter a Company Name.")
                elif p_prod_sel == "Select Product" or not p_product.strip():
                    st.warning("Please select or enter a Product Name.")
                elif p_qty <= 0:
                    st.warning("Quantity must be greater than zero.")
                else:
                    params = {
                        "action": "update_stock",
                        "type": "Production",
                        "date": prod_date.strftime("%d/%m/%Y"),
                        "company_name": p_company.strip(),
                        "product_name": p_product.strip(),
                        "quantity": p_qty,
                        "unit": p_unit,
                        "reference": p_batch.strip(),
                        "remark": p_remark.strip()
                    }
                    with st.spinner("Updating Main Stock & History Log..."):
                        res = requests.get(APPS_SCRIPT_URL, params=params, timeout=30).json()
                        if res.get("status") == "success":
                            st.toast(f"✅ {res.get('message')}")
                            st.cache_data.clear()
                            st.session_state.form_key += 1
                            st.rerun()
                        else:
                            st.error(res.get("message", "Failed to add stock."))

    # === POINT 2: DELIVERY ENTRY (- STOCK) ===
    with col_del:
        st.subheader("🚚 Delivery Entry (- Stock)")
        with st.container(border=True):
            del_date = st.date_input("Delivery Date *", value=date.today(), format="DD/MM/YYYY", key=f"d_date_{k}")

            # Company Dropdown loaded from Main_Stock
            d_comp_options = ["Select Company"] + master_companies
            d_comp_sel = st.selectbox("Company Name *", options=d_comp_options, key=f"d_comp_sel_{k}")

            # Filter products belonging to the selected Company
            d_comp_products = []
            if d_comp_sel != "Select Company" and not stock_df.empty:
                filtered_d = stock_df[stock_df["Company Name"].astype(str).str.strip() == d_comp_sel]
                d_comp_products = sorted([
                    str(p).strip() for p in filtered_d["Product Name"].dropna().unique() if str(p).strip() != ""
                ])

            d_prod_sel = st.selectbox("Product Name *", options=["Select Product"] + d_comp_products, key=f"d_prod_sel_{k}")

            # Show live available balance & unit from Main_Stock
            avail_qty = 0.0
            default_unit = "per pcs"
            if d_comp_sel != "Select Company" and d_prod_sel != "Select Product" and not stock_df.empty:
                match = stock_df[
                    (stock_df["Company Name"].astype(str).str.strip() == d_comp_sel) &
                    (stock_df["Product Name"].astype(str).str.strip() == d_prod_sel)
                ]
                if not match.empty:
                    avail_qty = float(pd.to_numeric(match.iloc[0]["Current Stock"], errors="coerce") or 0.0)
                    default_unit = str(match.iloc[0]["Unit"]).strip()
                st.info(f"📦 **Available Stock:** `{avail_qty:,.2f} {default_unit}`")

            d_qty = st.number_input("Delivered Quantity *", min_value=0.0, value=0.0, step=1.0, format="%.2f", key=f"d_qty_{k}")
            d_unit = st.selectbox(
                "Unit *",
                options=UNIT_OPTIONS,
                index=UNIT_OPTIONS.index(default_unit) if default_unit in UNIT_OPTIONS else 0,
                key=f"d_unit_{k}"
            )
            d_inv = st.text_input("Invoice / Challan No. *", placeholder="e.g. SE/040/26-27", key=f"d_ref_{k}")
            d_remark = st.text_input("Remark (Optional)", placeholder="e.g. Vehicle No. or Party Notes", key=f"d_rem_{k}")

            if st.button("➖ Deduct Delivery Stock", type="primary", use_container_width=True):
                if d_comp_sel == "Select Company":
                    st.warning("Please select a Company Name.")
                elif d_prod_sel == "Select Product":
                    st.warning("Please select a Product Name.")
                elif d_qty <= 0:
                    st.warning("Quantity must be greater than zero.")
                elif d_qty > avail_qty:
                    st.error(f"Insufficient stock! Available balance is only {avail_qty:,.2f} {default_unit}.")
                elif not d_inv.strip():
                    st.warning("Please enter an Invoice or Challan Number.")
                else:
                    params = {
                        "action": "update_stock",
                        "type": "Delivery",
                        "date": del_date.strftime("%d/%m/%Y"),
                        "company_name": d_comp_sel,
                        "product_name": d_prod_sel,
                        "quantity": d_qty,
                        "unit": d_unit,
                        "reference": d_inv.strip(),
                        "remark": d_remark.strip()
                    }
                    with st.spinner("Deducting Stock & Updating History Log..."):
                        res = requests.get(APPS_SCRIPT_URL, params=params, timeout=30).json()
                        if res.get("status") == "success":
                            st.toast(f"✅ {res.get('message')}")
                            st.cache_data.clear()
                            st.session_state.form_key += 1
                            st.rerun()
                        else:
                            st.error(res.get("message", "Failed to deduct stock."))

# ------------------------------------------------------
# TAB 2: MAIN STOCK (LIVE BALANCE)
# ------------------------------------------------------
with tab_stock:
    col_s1, col_s2 = st.columns([4, 1])
    with col_s1:
        st.subheader("📊 Current Ready Product Inventory")
    with col_s2:
        if st.button("🔄 Refresh Stock", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    if stock_df.empty:
        st.info("No stock records found yet. Add products to 'Main_Stock' or record a Production entry.")
    else:
        filter_comp = st.selectbox("Filter by Company:", ["All Companies"] + master_companies, key="filter_stock_comp")
        display_stock = stock_df.copy()
        if filter_comp != "All Companies" and "Company Name" in display_stock.columns:
            display_stock = display_stock[display_stock["Company Name"].astype(str).str.strip() == filter_comp]

        st.dataframe(display_stock, use_container_width=True, hide_index=True)

# ------------------------------------------------------
# TAB 3: HISTORY LOG
# ------------------------------------------------------
with tab_logs:
    col_l1, col_l2 = st.columns([4, 1])
    with col_l1:
        st.subheader("📜 Complete Production & Delivery History Log")
    with col_l2:
        if st.button("🔄 Refresh Logs", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    if logs_df.empty:
        st.info("No stock transactions logged yet.")
    else:
        filter_type = st.radio("Filter Transactions:", ["All", "Production", "Delivery"], horizontal=True)
        display_logs = logs_df.copy()
        if filter_type != "All" and "Transaction Type" in display_logs.columns:
            display_logs = display_logs[display_logs["Transaction Type"] == filter_type]

        st.dataframe(display_logs.iloc[::-1], use_container_width=True, hide_index=True)
