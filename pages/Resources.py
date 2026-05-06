import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import re
import ast
import time
from concurrent.futures import ThreadPoolExecutor
import Auth_manage as am

# Pandas warning prevention and type conversion settings
pd.set_option('future.no_silent_downcasting', True)

# --- Constants & Config ---
MY_SHEET_URL = st.secrets["connections"]["gsheets"]["spreadsheet"]
MASTER_CODE = st.secrets["MASTER_CODE"]

# [SYNCED] Vessel classification options
VESSEL_CLASS_OPTIONS = ["Microplate", "Digital data", "Tube", "Trough", "Agar plate", "Flexible vessel"]

conn = st.connection("gsheets", type=GSheetsConnection)


# ==========================================
# 1. Utilities & Custom Sorting
# ==========================================

def ram_natural_sort_key(id_series):
    """Natural sort key for ID/Abbreviation sorting (A...Z -> AA...ZZ)"""

    def split_id(x):
        s = str(x)
        # Handle IDs with hyphens, underscores, or spaces
        parts = re.split(r'[-_ ]', s)
        prefix = parts[0]
        num_part = re.sub(r'\D', '', parts[-1]) if len(parts) > 1 else re.sub(r'\D', '', s)
        num = int(num_part) if num_part else 0
        return (len(prefix), prefix, num)

    return id_series.apply(split_id)


def format_list_strings(val):
    """Converts list-like strings to a clean comma-separated format for display"""
    val_str = str(val).strip()
    if val_str.startswith('[') and val_str.endswith(']'):
        try:
            actual_list = ast.literal_eval(val_str)
            if isinstance(actual_list, list): return ", ".join(actual_list)
        except:
            return val_str
    return val


@st.cache_data(ttl=3600)
def load_and_merge_resources(master_tab, user_tab, id_col_name, refresh_token=0):
    """Merges Master and User resource tabs with cleaning and sorting"""
    try:
        m_ttl = "1h" if refresh_token == 0 else 0
        m_df = conn.read(spreadsheet=MY_SHEET_URL, worksheet=master_tab, ttl=m_ttl)
        m_df['Source'] = 'Master'
        u_df = conn.read(spreadsheet=MY_SHEET_URL, worksheet=user_tab, ttl=m_ttl)
        u_df['Source'] = 'User'

        combined = pd.concat([m_df, u_df], ignore_index=True).dropna(how='all')
        combined = combined.fillna("")

        # Apply natural sorting based on the ID column
        raw_id_col = id_col_name.replace(' ', '_')
        if raw_id_col in combined.columns:
            combined = combined.sort_values(by=raw_id_col, key=ram_natural_sort_key, ascending=True)
        elif id_col_name in combined.columns:
            combined = combined.sort_values(by=id_col_name, key=ram_natural_sort_key, ascending=True)

        # Force string type to prevent Arrow engine serialization conflicts
        for col in combined.columns:
            combined[col] = combined[col].astype(str)

        display_df = combined.copy()
        # Securely hide access codes from the public table
        if 'access_code' in display_df.columns:
            display_df = display_df.drop(columns=['access_code'])

        # Clean list strings for display readability
        for col in display_df.columns:
            display_df[col] = display_df[col].apply(format_list_strings)

        # Standardize column headers
        display_df.columns = [c.strip().replace('_', ' ') for c in display_df.columns]
        cols = ['Source'] + [c for c in display_df.columns if c != 'Source']

        return display_df[cols]
    except Exception as e:
        st.error(f"Error loading resources: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=60)
def get_raw_data_safe(worksheet_name):
    """Fetches raw data for editing/deleting without schema changes"""
    df = conn.read(spreadsheet=MY_SHEET_URL, worksheet=worksheet_name, ttl=0)
    return df.fillna("").astype(object)


# ==========================================
# 2. UI: Header & Metrics
# ==========================================
c_head1, c_head2 = st.columns([0.8, 0.2], vertical_alignment="bottom")
with c_head1:
    st.title("📚 Resource Database")
    st.caption("Central library for robotic units, functional devices, and labware specifications.")
with c_head2:
    if st.button("🔄 Refresh DB", width='stretch', type="primary"):
        st.cache_data.clear()
        for key in list(st.session_state.keys()):
            if key.startswith("raw_data_"): del st.session_state[key]
        st.rerun()

# Load all resource categories
df_robots_all = load_and_merge_resources("Master_Robotic_Units", "User_Robotic_Units", "Robotic unit")
df_devices_all = load_and_merge_resources("Master_Functional_Devices", "User_Functional_Devices",
                                          "Device Functional Unit")
df_vessels_all = load_and_merge_resources("Master_Vessels", "User_Vessels", "Abbreviation")

with st.container(border=True):
    m1, m2, m3 = st.columns(3)
    m1.metric("🤖 Robotic Units", len(df_robots_all))
    m2.metric("🔬 Functional Devices", len(df_devices_all))
    m3.metric("🧪 Vessels", len(df_vessels_all))

st.write("")

# ==========================================
# 3. Navigation & Filtering
# ==========================================
c_nav, c_filter = st.columns([0.65, 0.35], vertical_alignment="center")
with c_nav:
    category_choice = st.segmented_control(
        "Select Category",
        options=["🤖 Robotic Units", "🔬 Functional Devices", "🧪 Vessels"],
        default="🤖 Robotic Units",
        label_visibility="collapsed"
    )
with c_filter:
    source_choice = st.multiselect(
        "Source Filter",
        ["Master", "User"],
        default=["Master", "User"],
        label_visibility="collapsed"
    )


def apply_filter(df):
    if not df.empty and 'Source' in df.columns:
        return df[df['Source'].isin(source_choice)]
    return df


f_robots = apply_filter(df_robots_all)
f_devices = apply_filter(df_devices_all)
f_vessels = apply_filter(df_vessels_all)

# ==========================================
# 4. Content Area & Management Logic
# ==========================================

def asset_management_ui(category, master_ws, user_ws, id_col, name_col, display_df):
    """Reusable UI component for searching, viewing, and managing assets"""
    c_sub1, c_sub2 = st.columns([0.6, 0.4], vertical_alignment="bottom")
    with c_sub1:
        st.subheader(f"{category} Inventory")
    with c_sub2:
        search_query = st.text_input(f"🔍 Search", key=f"search_{category}", label_visibility="collapsed",
                                     placeholder=f"Search {category}...")

    if search_query:
        display_df = display_df[
            display_df.apply(lambda row: row.astype(str).str.contains(search_query, case=False).any(), axis=1)]

    st.dataframe(display_df, hide_index=True, width='stretch')

    with st.expander(f"🛠️ Edit or Delete {category}"):
        with st.form(key=f"auth_form_{category}"):
            col_auth, col_sel = st.columns([0.4, 0.6])

            # [ADDED] Integrated helper tooltip and placeholder in English
            with col_auth:
                input_code = st.text_input(
                    "🔑 Access Code",
                    type="password",
                    key=f"f_pw_{category}",
                    placeholder="Enter access code...",
                    help=f"Please enter the access code corresponding to the selected {category.lower()} to authorize editing or deleting its data."
                )

            with col_sel:
                target_name = st.selectbox(
                    f"Select {category}",
                    ["-- Select --"] + display_df[name_col].tolist(),
                    key=f"f_sel_{category}"
                )
            submit_auth = st.form_submit_button("🔓 Access & Load Data", width='stretch')

        if submit_auth:
            if target_name != "-- Select --":
                st.session_state[f"auth_active_{category}"] = True
                st.session_state[f"auth_code_{category}"] = input_code
                st.session_state[f"auth_target_{category}"] = target_name
            else:
                st.session_state[f"auth_active_{category}"] = False

        if st.session_state.get(f"auth_active_{category}"):
            input_code = st.session_state[f"auth_code_{category}"]
            target_name = st.session_state[f"auth_target_{category}"]

            # Identify the source worksheet for the selected asset
            source_type = display_df[display_df[name_col] == target_name]['Source'].values[0]
            target_ws = master_ws if source_type == 'Master' else user_ws
            state_key = f"raw_data_{target_ws}"

            if state_key not in st.session_state:
                try:
                    with st.spinner("Fetching original data..."):
                        st.session_state[state_key] = get_raw_data_safe(target_ws)
                except Exception as e:
                    st.error(f"Error fetching raw data: {e}")
                    return

            raw_df = st.session_state[state_key]
            id_col_raw = id_col.replace(' ', '_')
            target_id = display_df[display_df[name_col] == target_name][id_col].values[0]

            try:
                # Robust matching for ID column names with or without underscores
                actual_cols = raw_df.columns.tolist()
                matched_col = next((c for c in actual_cols if c.strip() in [id_col, id_col_raw]), id_col_raw)
                target_row = raw_df[raw_df[matched_col].astype(str).str.strip() == str(target_id).strip()].iloc[0]
            except Exception:
                st.error("Data integrity mismatch. Please refresh.")
                return

            # Access authentication with support for numeric code parsing
            stored_code = str(target_row.get('access_code', '')).strip()
            if stored_code.endswith('.0'): stored_code = stored_code[:-2]

            if not am.is_edit_authorized(input_code, stored_code):
                st.error("❌ Invalid Access Code. Permission denied.")
                return

            st.success(f"🔓 Access Granted for {target_name}")

            # Dynamic form generation based on the sheet schema
            new_data = {}
            edit_cols = [c for c in raw_df.columns if c != 'access_code']
            form_cols = st.columns(2)

            for i, col in enumerate(edit_cols):
                with form_cols[i % 2]:
                    current_val = str(target_row[col])
                    widget_key = f"ed_{category}_{target_id}_{col}"

                    if "Motion" in col:
                        try:
                            default_vals = ast.literal_eval(current_val) if current_val.startswith('[') else [x.strip()
                                                                                                              for x in
                                                                                                              current_val.split(
                                                                                                                  ',')
                                                                                                              if
                                                                                                              x.strip()]
                        except:
                            default_vals = []
                        new_data[col] = str(st.multiselect(f"Edit {col}", options=["Colony Picking", "Liquid Transfer",
                                                                                   "Labware Transfer"],
                                                           default=default_vals, key=widget_key))
                    elif "class" in col.lower() and category == "Vessel":
                        d_idx = VESSEL_CLASS_OPTIONS.index(current_val) if current_val in VESSEL_CLASS_OPTIONS else 0
                        new_data[col] = st.selectbox(f"Edit {col}", options=VESSEL_CLASS_OPTIONS, index=d_idx,
                                                     key=widget_key)
                    else:
                        new_data[col] = st.text_input(f"Edit {col}", value=current_val, key=widget_key)

            st.write("")
            b_col1, b_col2 = st.columns(2)

            if b_col1.button("Update Changes", key=f"up_{category}", type="primary", width='stretch'):
                try:
                    idx = raw_df.index[raw_df[matched_col].astype(str).str.strip() == str(target_id).strip()][0]
                    for k, v in new_data.items(): raw_df.at[idx, k] = v
                    conn.update(spreadsheet=MY_SHEET_URL, worksheet=target_ws, data=raw_df)

                    # Keep cache intact to save API quota, but guide the user clearly
                    if state_key in st.session_state:
                        del st.session_state[state_key]
                    st.session_state[f"auth_active_{category}"] = False

                    # Dynamic info alert with a clear action item
                    st.success("Successfully saved to cloud database!")
                    st.info(
                        "💡 Please click the **🔄 Refresh DB** button at the top to apply changes to your current view.")
                    time.sleep(2)
                    st.rerun()
                except Exception as e:
                    st.error(f"Update failed: {e}")

            if b_col2.button("Delete Asset", key=f"del_{category}", width='stretch'):
                try:
                    new_raw_df = raw_df[raw_df[matched_col].astype(str).str.strip() != str(target_id).strip()]
                    conn.update(spreadsheet=MY_SHEET_URL, worksheet=target_ws, data=new_raw_df)
                    if state_key in st.session_state: del st.session_state[state_key]
                    st.session_state[f"auth_active_{category}"] = False
                    st.success("Successfully deleted!")
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"Delete failed: {e}")


# Main Execution Logic
if category_choice == "🤖 Robotic Units":
    asset_management_ui("Robot", "Master_Robotic_Units", "User_Robotic_Units", "Robotic unit", "Robot Name", f_robots)
elif category_choice == "🔬 Functional Devices":
    asset_management_ui("Device", "Master_Functional_Devices", "User_Functional_Devices", "Device Functional Unit",
                        "Device Name", f_devices)
elif category_choice == "🧪 Vessels":
    asset_management_ui("Vessel", "Master_Vessels", "User_Vessels", "Abbreviation", "Vessel Name", f_vessels)