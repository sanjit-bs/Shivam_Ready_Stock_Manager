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
# Session State Management for Multi-Row Entries
# ======================================================
if "form_key" not in st.session_state:
    st.session_state.form_key = 0
if "prod_rows" not in st.session_state:
    st.session_state.prod_rows = 1
if "del_rows" not in st.session_state:
    st.session_state.del_rows = 1

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
# TAB 1: HORIZONTAL MULTI-COMPANY / MULTI-PRODUCT ENTRY
# ------------------------------------------------------
with tab_entry:
    entry_mode = st.radio(
        "Select Entry Mode:",
        ["🏭 Production Entry (+ Stock)", "🚚 Delivery Entry (- Stock)"],
        horizontal=True,
        key="entry_mode_selector"
    )
    st.markdown("---")

    # ==================================================
    # MODE 1: PRODUCTION ENTRY (+ STOCK) - HORIZONTAL
    # ==================================================
    if entry_mode == "🏭 Production Entry (+ Stock)":
        top_c1, top_c2, top_c3 = st.columns([1.5, 1, 1])
        with top_c1:
            prod_date = st.date_input("Production Date *", value=date.today(), format="DD/MM/YYYY", key=f"p_date_{k}")
        with top_c2:
            st.write("")
            st.write("")
            if st.button("➕ Add Row", key="add_prod_row", use_container_width=True):
                st.session_state.prod_rows += 1
                st.rerun()
        with top_c3:
            st.write("")
            st.write("")
            if st.session_state.prod_rows > 1 and st.button("➖ Remove Last Row", key="rem_prod_row", use_container_width=True):
                st.session_state.prod_rows -= 1
                st.rerun()

        # Horizontal Table Headers
        h1, h2, h3, h4, h5, h6 = st.columns([2.2, 2.2, 1.2, 1.0, 1.5, 1.9])
        h1.markdown("**Company Name ***")
        h2.markdown("**Product Name ***")
        h3.markdown("**Quantity ***")
        h4.markdown("**Unit ***")
        h5.markdown("**Batch / Shift**")
        h6.markdown("**Remark**")

        prod_entries = []
        for idx in range(st.session_state.prod_rows):
            with st.container(border=True):
                c1, c2, c3, c4, c5, c6 = st.columns([2.2, 2.2, 1.2, 1.0, 1.5, 1.9])

                with c1:
                    p_comp_options = ["Select Company"] + master_companies + ["Others (New)"]
                    p_comp_sel = st.selectbox("Company", options=p_comp_options, label_visibility="collapsed", key=f"p_comp_{k}_{idx}")
                    if p_comp_sel == "Others (New)":
                        p_company = st.text_input("New Company", placeholder="Enter Company Name...", label_visibility="collapsed", key=f"p_new_comp_{k}_{idx}")
                    else:
                        p_company = p_comp_sel

                with c2:
                    comp_products = []
                    if p_comp_sel not in ["Select Company", "Others (New)"] and not stock_df.empty:
                        filtered = stock_df[stock_df["Company Name"].astype(str).str.strip() == p_comp_sel]
                        comp_products = sorted([
                            str(p).strip() for p in filtered["Product Name"].dropna().unique() if str(p).strip() != ""
                        ])
                    p_prod_options = ["Select Product"] + comp_products + ["Others (New)"]
                    p_prod_sel = st.selectbox("Product", options=p_prod_options, label_visibility="collapsed", key=f"p_prod_{k}_{idx}")
                    if p_prod_sel == "Others (New)":
                        p_product = st.text_input("New Product", placeholder="Enter Product Name...", label_visibility="collapsed", key=f"p_new_prod_{k}_{idx}")
                    else:
                        p_product = p_prod_sel

                # Auto-detect default unit from Main_Stock
                p_default_unit = "pcs"
                if p_comp_sel not in ["Select Company", "Others (New)"] and p_prod_sel not in ["Select Product", "Others (New)"] and not stock_df.empty:
                    match = stock_df[
                        (stock_df["Company Name"].astype(str).str.strip() == p_company) &
                        (stock_df["Product Name"].astype(str).str.strip() == p_product)
                    ]
                    if not match.empty:
                        raw_unit = str(match.iloc[0]["Unit"]).strip()
                        if raw_unit in UNIT_OPTIONS:
                            p_default_unit = raw_unit

                with c3:
                    p_qty = st.number_input("Qty", min_value=0.0, value=0.0, step=1.0, format="%.2f", label_visibility="collapsed", key=f"p_qty_{k}_{idx}")

                with c4:
                    p_unit = st.selectbox(
                        "Unit",
                        options=UNIT_OPTIONS,
                        index=UNIT_OPTIONS.index(p_default_unit),
                        label_visibility="collapsed",
                        key=f"p_unit_{k}_{idx}"
                    )

                with c5:
                    p_batch = st.text_input("Batch", placeholder="Shift / Batch", label_visibility="collapsed", key=f"p_batch_{k}_{idx}")

                with c6:
                    p_remark = st.text_input("Remark", placeholder="Optional note", label_visibility="collapsed", key=f"p_rem_{k}_{idx}")

                prod_entries.append({
                    "row": idx + 1,
                    "comp_sel": p_comp_sel,
                    "company": p_company.strip(),
                    "prod_sel": p_prod_sel,
                    "product": p_product.strip(),
                    "qty": p_qty,
                    "unit": p_unit,
                    "reference": p_batch.strip(),
                    "remark": p_remark.strip()
                })

        if st.button("➕ Submit All Production Entries", type="primary", use_container_width=True):
            errors = []
            valid_items = []

            for item in prod_entries:
                # Skip completely blank rows if user added extra rows
                if item["comp_sel"] == "Select Company" and item["prod_sel"] == "Select Product" and item["qty"] == 0:
                    continue
                if item["comp_sel"] == "Select Company" or not item["company"]:
                    errors.append(f"Row {item['row']}: Please select or enter a Company Name.")
                elif item["prod_sel"] == "Select Product" or not item["product"]:
                    errors.append(f"Row {item['row']}: Please select or enter a Product Name.")
                elif item["qty"] <= 0:
                    errors.append(f"Row {item['row']}: Quantity must be greater than 0.")
                else:
                    valid_items.append(item)

            if errors:
                for err in errors:
                    st.warning(err)
            elif not valid_items:
                st.warning("Please fill in at least one valid Production row.")
            else:
                success_count = 0
                with st.spinner(f"Saving {len(valid_items)} production entry(ies)..."):
                    for item in valid_items:
                        params = {
                            "action": "update_stock",
                            "type": "Production",
                            "date": prod_date.strftime("%d/%m/%Y"),
                            "company_name": item["company"],
                            "product_name": item["product"],
                            "quantity": item["qty"],
                            "unit": item["unit"],
                            "reference": item["reference"],
                            "remark": item["remark"]
                        }
                        res = requests.get(APPS_SCRIPT_URL, params=params, timeout=30).json()
                        if res.get("status") == "success":
                            success_count += 1
                        else:
                            st.error(f"Row {item['row']} ({item['product']}): {res.get('message', 'Failed')}")

                if success_count == len(valid_items):
                    st.toast(f"✅ Successfully recorded {success_count} Production entry(ies)!")
                    st.cache_data.clear()
                    st.session_state.prod_rows = 1
                    st.session_state.form_key += 1
                    st.rerun()

    # ==================================================
    # MODE 2: DELIVERY ENTRY (- STOCK) - HORIZONTAL
    # ==================================================
    else:
        top_c1, top_c2, top_c3 = st.columns([1.5, 1, 1])
        with top_c1:
            del_date = st.date_input("Delivery Date *", value=date.today(), format="DD/MM/YYYY", key=f"d_date_{k}")
        with top_c2:
            st.write("")
            st.write("")
            if st.button("➕ Add Row", key="add_del_row", use_container_width=True):
                st.session_state.del_rows += 1
                st.rerun()
        with top_c3:
            st.write("")
            st.write("")
            if st.session_state.del_rows > 1 and st.button("➖ Remove Last Row", key="rem_del_row", use_container_width=True):
                st.session_state.del_rows -= 1
                st.rerun()

        # Horizontal Table Headers
        h1, h2, h3, h4, h5, h6, h7 = st.columns([2.0, 2.0, 1.1, 1.1, 0.9, 1.4, 1.5])
        h1.markdown("**Company Name ***")
        h2.markdown("**Product Name ***")
        h3.markdown("**Available**")
        h4.markdown("**Quantity ***")
        h5.markdown("**Unit ***")
        h6.markdown("**Invoice / Challan ***")
        h7.markdown("**Remark**")

        del_entries = []
        for idx in range(st.session_state.del_rows):
            with st.container(border=True):
                c1, c2, c3, c4, c5, c6, c7 = st.columns([2.0, 2.0, 1.1, 1.1, 0.9, 1.4, 1.5])

                with c1:
                    d_comp_options = ["Select Company"] + master_companies
                    d_comp_sel = st.selectbox("Company", options=d_comp_options, label_visibility="collapsed", key=f"d_comp_{k}_{idx}")

                with c2:
                    d_comp_products = []
                    if d_comp_sel != "Select Company" and not stock_df.empty:
                        filtered_d = stock_df[stock_df["Company Name"].astype(str).str.strip() == d_comp_sel]
                        d_comp_products = sorted([
                            str(p).strip() for p in filtered_d["Product Name"].dropna().unique() if str(p).strip() != ""
                        ])
                    d_prod_sel = st.selectbox("Product", options=["Select Product"] + d_comp_products, label_visibility="collapsed", key=f"d_prod_{k}_{idx}")

                avail_qty = 0.0
                default_unit = "pcs"
                if d_comp_sel != "Select Company" and d_prod_sel != "Select Product" and not stock_df.empty:
                    match = stock_df[
                        (stock_df["Company Name"].astype(str).str.strip() == d_comp_sel) &
                        (stock_df["Product Name"].astype(str).str.strip() == d_prod_sel)
                    ]
                    if not match.empty:
                        avail_qty = float(pd.to_numeric(match.iloc[0]["Current Stock"], errors="coerce") or 0.0)
                        raw_unit = str(match.iloc[0]["Unit"]).strip()
                        if raw_unit in UNIT_OPTIONS:
                            default_unit = raw_unit

                with c3:
                    if d_comp_sel != "Select Company" and d_prod_sel != "Select Product":
                        st.markdown(f"**`{avail_qty:,.2f} {default_unit}`**")
                    else:
                        st.caption("-")

                with c4:
                    d_qty = st.number_input("Qty", min_value=0.0, value=0.0, step=1.0, format="%.2f", label_visibility="collapsed", key=f"d_qty_{k}_{idx}")

                with c5:
                    d_unit = st.selectbox(
                        "Unit",
                        options=UNIT_OPTIONS,
                        index=UNIT_OPTIONS.index(default_unit),
                        label_visibility="collapsed",
                        key=f"d_unit_{k}_{idx}"
                    )

                with c6:
                    d_inv = st.text_input("Invoice", placeholder="e.g. SE/040", label_visibility="collapsed", key=f"d_inv_{k}_{idx}")

                with c7:
                    d_remark = st.text_input("Remark", placeholder="Vehicle / Party", label_visibility="collapsed", key=f"d_rem_{k}_{idx}")

                del_entries.append({
                    "row": idx + 1,
                    "company": d_comp_sel,
                    "product": d_prod_sel,
                    "avail_qty": avail_qty,
                    "qty": d_qty,
                    "unit": d_unit,
                    "reference": d_inv.strip(),
                    "remark": d_remark.strip()
                })

        if st.button("➖ Submit All Delivery Entries", type="primary", use_container_width=True):
            errors = []
            valid_items = []
            cumulative_deductions = {}

            for item in del_entries:
                # Skip completely blank rows
                if item["company"] == "Select Company" and item["product"] == "Select Product" and item["qty"] == 0 and not item["reference"]:
                    continue
                if item["company"] == "Select Company":
                    errors.append(f"Row {item['row']}: Please select a Company Name.")
                elif item["product"] == "Select Product":
                    errors.append(f"Row {item['row']}: Please select a Product Name.")
                elif item["qty"] <= 0:
                    errors.append(f"Row {item['row']}: Quantity must be greater than 0.")
                elif not item["reference"]:
                    errors.append(f"Row {item['row']}: Please enter an Invoice / Challan Number.")
                else:
                    key_pair = (item["company"], item["product"])
                    cumulative_deductions[key_pair] = cumulative_deductions.get(key_pair, 0.0) + item["qty"]
                    if cumulative_deductions[key_pair] > item["avail_qty"]:
                        errors.append(
                            f"Row {item['row']}: Total requested quantity ({cumulative_deductions[key_pair]:,.2f}) for "
                            f"{item['product']} ({item['company']}) exceeds available stock ({item['avail_qty']:,.2f} {item['unit']})."
                        )
                    else:
                        valid_items.append(item)

            if errors:
                for err in errors:
                    st.warning(err)
            elif not valid_items:
                st.warning("Please fill in at least one valid Delivery row.")
            else:
                success_count = 0
                with st.spinner(f"Processing {len(valid_items)} delivery entry(ies)..."):
                    for item in valid_items:
                        params = {
                            "action": "update_stock",
                            "type": "Delivery",
                            "date": del_date.strftime("%d/%m/%Y"),
                            "company_name": item["company"],
                            "product_name": item["product"],
                            "quantity": item["qty"],
                            "unit": item["unit"],
                            "reference": item["reference"],
                            "remark": item["remark"]
                        }
                        res = requests.get(APPS_SCRIPT_URL, params=params, timeout=30).json()
                        if res.status_code == "success" or res.get("status") == "success":
                            success_count += 1
                        else:
                            st.error(f"Row {item['row']} ({item['product']}): {res.get('message', 'Failed')}")

                if success_count == len(valid_items):
                    st.toast(f"✅ Successfully deducted {success_count} Delivery entry(ies)!")
                    st.cache_data.clear()
                    st.session_state.del_rows = 1
                    st.session_state.form_key += 1
                    st.rerun()

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
