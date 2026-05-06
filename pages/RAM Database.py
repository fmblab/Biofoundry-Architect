import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import ast
import re
import Auth_manage as am

# Note: st.set_page_config is managed in Home.py, so it has been removed here.
pd.set_option('future.no_silent_downcasting', True)

# --- Constants & Config ---
MY_SHEET_URL = st.secrets["connections"]["gsheets"]["spreadsheet"]
MASTER_CODE = st.secrets["MASTER_CODE"]
LABOR_RATE = 37.5

conn = st.connection("gsheets", type=GSheetsConnection)


def safe_eval_list(val):
    """Robust parser for list-like strings (handles JSON and Python literal formats)"""

    if val is None:
        return []

    if isinstance(val, (list, dict)):
        return val

    val_str = str(val).strip()

    if val_str in ["", "[]", "nan", "NaN", "None"]:
        return []

    # --- FIX 1: normalize quotes ---
    # convert single quotes to double quotes for JSON compatibility
    normalized = val_str.replace("'", '"')

    # --- FIX 2: remove problematic newlines ---
    normalized = normalized.replace("\n", " ").replace("\r", " ")

    # --- TRY JSON FIRST ---
    try:
        import json
        return json.loads(normalized)
    except:
        pass

    # --- FALLBACK: python literal ---
    try:
        return ast.literal_eval(val_str)
    except:
        return []


def to_float(val):
    try:
        return float(str(val).strip())
    except:
        return 0.0


# ==========================================
# 1. Custom Sorting Logic
# ==========================================

def ram_natural_sort_key(id_series):
    def split_id(x):
        s = str(x)
        parts = s.split('-')
        prefix = parts[0]
        num = 0
        if len(parts) > 1:
            num_part = re.sub(r'\D', '', parts[1])
            num = int(num_part) if num_part else 0
        return (len(prefix), prefix, num)

    return id_series.apply(split_id)


# ==========================================
# 2. Data Loading & Cleaning
# ==========================================

@st.cache_data(ttl=60, show_spinner="Syncing with RAM Database...")
def _cached_db_fetch():
    # Load raw data from sheets
    m_db = conn.read(spreadsheet=MY_SHEET_URL, worksheet="RAM_MasterDB", ttl=0)
    u_db = conn.read(spreadsheet=MY_SHEET_URL, worksheet="RAM_UserDB", ttl=0)

    # Preprocess Master DB
    if m_db is not None and not m_db.empty:
        m_db.columns = [c.strip() for c in m_db.columns]
        m_db['Source'] = '1. 🏛️ Master'  # Add temporary source for sorting
    else:
        m_db = pd.DataFrame()

    # Preprocess User DB
    if u_db is not None and not u_db.empty:
        u_db.columns = [c.strip() for c in u_db.columns]
        u_db['Source'] = '2. 👤 User'  # Add temporary source for sorting
    else:
        u_db = pd.DataFrame()

    if m_db.empty and u_db.empty:
        return pd.DataFrame()

    # Merge DataFrames
    combined = pd.concat([m_db, u_db], ignore_index=True).fillna("None")

    # [CORE SORTING] Source (1st priority) -> RAM_ID (2nd priority, natural sort)
    if not combined.empty and 'RAM_ID' in combined.columns:
        combined = combined.sort_values(
            by=['Source', 'RAM_ID'],
            ascending=[True, True],
            key=lambda col: ram_natural_sort_key(col) if col.name == 'RAM_ID' else col
        ).reset_index(drop=True)

        # Remove sorting prefix from Source column
        combined['Source'] = combined['Source'].str.replace(r'^\d+\. ', '', regex=True)

    # Clean numeric data
    numeric_cols = ['Total_RAM_Cost(USD)', 'Total_Material_Cost(USD)', 'Labor_cost(USD)', 'Total_Time(h)',
                    'Operation_Time(h)', 'Hands_on_Time(h)', 'Sample_Capacity']
    for col in numeric_cols:
        if col in combined.columns:
            combined[col] = pd.to_numeric(combined[col].replace("None", 0), errors='coerce').fillna(0)

    # Format string lists to improve readability
    cols_to_fix = ['Process_Action', 'Robot', 'Functional_Device']
    for col in cols_to_fix:
        if col in combined.columns:
            combined[col] = combined[col].apply(
                lambda x: ", ".join(ast.literal_eval(x)) if isinstance(x, str) and x.startswith('[') else str(x))

    return combined


def load_cloud_database():
    """Wrapper for cached fetch with error handling"""
    try:
        return _cached_db_fetch()
    except Exception as e:
        st.error(f"❌ Database Sync Error: {e}")
        return pd.DataFrame()


def force_refresh():
    """Clear cache and trigger re-sync"""
    _cached_db_fetch.clear()
    st.session_state.db_needs_refresh = False
    st.toast("Database cache cleared. Re-syncing...")


if st.session_state.get('db_needs_refresh', False):
    force_refresh()

full_db = load_cloud_database()

st.title("📚 RAM Database")
st.markdown("Real-time repository of **Robot Assisted Modules (RAM)** managed by the SKy Biofoundry")

# ==========================================
# 3. Filtering & Interactive Table UI
# ==========================================
if not full_db.empty:
    with st.container(border=True):
        c1, c2, c3, c4 = st.columns([2, 1, 1, 0.4], vertical_alignment="bottom")
        search_q = c1.text_input("🔍 Search (RAM ID or RAM Name)", placeholder="Search RAM...")
        source_f = c2.multiselect("Data Source", ["🏛️ Master", "👤 User"], default=["🏛️ Master", "👤 User"])
        all_actions = []
        if 'Process_Action' in full_db.columns:
            for x in full_db['Process_Action'].unique():
                if x != "None": all_actions.extend([a.strip() for a in str(x).split(',')])
        action_f = c3.multiselect("Action Filter", sorted(list(set(all_actions))))
        with c4:
            if st.button("🔄", help="Force database re-sync", width='stretch'):
                force_refresh()
                st.rerun()

    mask = full_db['Source'].isin(source_f)
    if search_q:
        mask &= (full_db['RAM_Name'].str.contains(search_q, case=False, na=False) | full_db['RAM_ID'].str.contains(
            search_q, case=False, na=False))
    if action_f:
        mask &= full_db['Process_Action'].apply(lambda x: any(act in str(x) for act in action_f))

    filtered_df = full_db[mask]
    st.markdown("#### 📋 RAM List (Click a row to view details)")
    selection_event = st.dataframe(
        filtered_df[['Source', 'RAM_ID', 'RAM_Name', 'Process_Action', 'Robot', 'Functional_Device', 'Purpose']],
        width="stretch", hide_index=True, on_select="rerun", selection_mode="single-row")

    st.divider()

    # ==========================================
    # 4. RAM Details
    # ==========================================
    st.subheader("🔍 RAM Details")
    selected_rows = selection_event.selection.rows

    if selected_rows:
        sel_idx = selected_rows[0]
        sel_id = filtered_df.iloc[sel_idx]['RAM_ID']
        row_data = full_db[full_db['RAM_ID'] == sel_id].iloc[0].to_dict()

        opt_time = to_float(row_data.get('Operation_Time(h)'))
        hot_time = to_float(row_data.get('Hands_on_Time(h)'))
        sample_cap = int(to_float(row_data.get('Sample_Capacity', 96)))
        total_time = to_float(row_data.get('Total_Time(h)')) or (opt_time + hot_time)

        labor_cost = to_float(row_data.get('Labor_cost(USD)')) or (hot_time * LABOR_RATE)
        mat_list = safe_eval_list(row_data.get('material_data', '[]'))
        mat_total = to_float(row_data.get('Total_Material_Cost(USD)'))
        if mat_total <= 0 and mat_list:
            mat_total = sum(
                to_float(m.get('Quantity', 0)) * to_float(m.get('Unit Price', m.get('Unit price', 0))) for m in
                mat_list)

        total_ram_cost = to_float(row_data.get('Total_RAM_Cost(USD)')) or (labor_cost + mat_total)

        c_det1, c_det2, c_det3 = st.columns([1, 1, 1.2])
        with c_det1:
            st.markdown("#### Basic Information")
            st.write(f"**Source:** `{row_data['Source']}`")
            st.write(f"**ID:** `{row_data['RAM_ID']}`")
            # [ADDED] Display RAM Name
            st.write(f"**Name:** `{row_data['RAM_Name']}`")
            st.info(row_data['Purpose'] if str(row_data['Purpose']) != "None" else "No description.")

        with c_det2:
            st.markdown("#### Hardware & Process")
            st.markdown(f"> **Actions:** {row_data['Process_Action']}")
            st.markdown(f"> **Robots:** {row_data['Robot']}")
            st.markdown(f"> **Devices:** {row_data['Functional_Device']}")

        with c_det3:
            st.markdown("#### Economics & Productivity")
            m1, m2, m3 = st.columns(3)
            m1.metric("Sample Capacity", f"{sample_cap} ")
            m2.metric("Total Time (h)", f"{total_time:.2f} ")
            m3.metric("Total RAM Cost (USD)", f"{total_ram_cost:,.2f}")

            st.divider()
            st.write(f"⏱️ **Operation Time:** {opt_time:.2f} h")
            st.write(f"👤 **Hands-on Time:** {hot_time:.2f} h")
            st.write(f"💸 **Labor Cost:** {labor_cost:,.2f} USD")
            st.write(f"📦 **Material Cost:** {mat_total:,.2f} USD")

        st.write("---")
        st.markdown("#### Input/Output & Materials")
        tab_io, tab_mat = st.tabs(["🧪 Substance I/O Information", "📦 Bill of Materials"])

        with tab_io:
            io_list = safe_eval_list(row_data.get('io_data', '[]'))

            if io_list:
                df_io = pd.DataFrame(io_list)

                # Normalize column names
                if 'Classification' in df_io.columns and 'Substance Class' not in df_io.columns:
                    df_io['Substance Class'] = df_io['Classification']

                display_cols = ['Type', 'Substance', 'Substance Class', 'Vessel', 'Vessel Class', 'Essential']

                st.dataframe(
                    df_io[[c for c in display_cols if c in df_io.columns]],
                    width="stretch",
                    hide_index=True
                )
            else:
                st.info("No Substance I/O data.")

        with tab_mat:
            if mat_list:
                df_mat = pd.DataFrame(mat_list)
                if "Unit price" in df_mat.columns: df_mat.rename(columns={"Unit price": "Unit Price"}, inplace=True)
                st.dataframe(df_mat, width="stretch", hide_index=True)
            else:
                st.info("No material information.")

        with st.popover(f"🔐 Administrative Access: {row_data['RAM_Name']}", width='stretch'):
            input_pw = st.text_input("Access Code", type="password", key=f"pw_{row_data['RAM_ID']}")
            if st.button("Verify & Open Editor", width='stretch', type="primary"):
                # Normalize column access_code lookup (lowercase prioritized)
                raw_saved_pw = row_data.get('access_code', row_data.get('Access_Code', ''))

                # Robust parsing of passwords to prevent truncating on periods
                raw_pw_str = str(raw_saved_pw).strip() if not pd.isna(raw_saved_pw) else "None"
                if raw_pw_str.endswith('.0'):
                    saved_pw = raw_pw_str[:-2]
                else:
                    saved_pw = raw_pw_str

                if am.is_edit_authorized(input_pw, saved_pw):
                    st.success("Verification successful.")
                    st.session_state.edit_target = row_data['RAM_ID']
                    st.switch_page("pages/RAM Editor.py")
                else:
                    st.error("Access Denied.")
    else:
        st.info("👆 Please click a row in the RAM List above to view details.")
else:
    st.warning("⚠️ Database is empty or sync failed.")
