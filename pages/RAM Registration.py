import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import re
import ast
import time
from concurrent.futures import ThreadPoolExecutor
import Auth_manage as am
import json

pd.set_option('future.no_silent_downcasting', True)

# --- Constants & Config ---
MY_SHEET_URL = st.secrets["connections"]["gsheets"]["spreadsheet"]
MASTER_CODE = st.secrets["MASTER_CODE"]
LABOR_RATE = 37.5

ACTION_ROBOT_GUIDE = {
    "Colony Picking": "LiHa is recommended for this action.",
    "Liquid Transfer": "LiHa or MCA are recommended for this action.",
    "Labware Transfer": "RoMa is recommended for this action."
}
MOTION_OPTIONS = ["Colony Picking", "Liquid Transfer", "Labware Transfer"]
VESSEL_CLASS_OPTIONS = ["Microplate", "Digital data", "Tube", "Trough", "Agar plate", "Flexible vessel"]
# [SYNCED] Substance Class List
SUBSTANCE_CLASSES = ["DNA", "Reaction Mix", "Buffer", "Solvent", "Liquid Medium", "Cells", "Solid Medium (Plate)",
                     "Fraction", "Analyte / Sample", "Data"]
UNIT_OPTIONS = ["rxn", "ea", "uL", "mL"]

conn = st.connection("gsheets", type=GSheetsConnection)


# ==========================================
# 1. Utilities & Session State Management
# ==========================================
def reset_registration_state():
    reg_keys = [
        'reg_step', 'reg_id', 'reg_pre', 'reg_name', 'reg_purpose',
        'reg_code', 'reg_acts', 'reg_robots', 'reg_devices',
        'reg_cap', 'reg_opt', 'reg_hot', 'f_m_p_input'
    ]
    for key in reg_keys:
        if key in st.session_state:
            del st.session_state[key]
    # user_db reset
    st.session_state.user_db = pd.DataFrame(columns=DB_COLUMNS)
    st.session_state.reg_complete = False


if 'reg_step' not in st.session_state: st.session_state.reg_step = 1
if 'reg_id' not in st.session_state: st.session_state.reg_id = None
if 'reg_complete' not in st.session_state: st.session_state.reg_complete = False

for key in ['reg_pre', 'reg_name', 'reg_purpose', 'reg_code']:
    if key not in st.session_state: st.session_state[key] = ""
for key in ['reg_acts', 'reg_robots', 'reg_devices']:
    if key not in st.session_state: st.session_state[key] = []

if "reg_cap" not in st.session_state: st.session_state.reg_cap = 96
if "reg_opt" not in st.session_state: st.session_state.reg_opt = "0.0"
if "reg_hot" not in st.session_state: st.session_state.reg_hot = "0.0"
if "f_m_p_input" not in st.session_state: st.session_state.f_m_p_input = 0.0

back_to_top_html = """
<div style="text-align: center; margin-top: 50px; margin-bottom: 30px;">
    <a href="#top-anchor" target="_self" style="display: inline-block; padding: 10px 20px; background-color: #F1F5F9; color: #3B82F6; border-radius: 8px; text-decoration: none; font-weight: 600; font-size: 14px; border: 1px solid #E2E8F0;">
        ⬆️ Back to Top
    </a>
</div>
"""


# ==========================================
# 2. Callbacks & Data Loading
# ==========================================
def apply_calc_to_input_callback(val):
    st.session_state.f_m_p_input = val


def sync_opt(): st.session_state.reg_opt = st.session_state.opt_input_widget


def sync_hot(): st.session_state.reg_hot = st.session_state.hot_input_widget


def update_capacity():
    val = st.session_state.edit_cap_input
    if val % 96 != 0:
        val = max(96, (val // 96) * 96)
        st.toast(f"Adjusted to {val}.")
    st.session_state.reg_cap = val


def add_material_item_callback(row_idx):
    if st.session_state.f_m_n:
        curr_m = safe_eval_list(st.session_state.user_db.at[row_idx, 'material_data'])
        curr_m.append({
            "Material Name": st.session_state.f_m_n,
            "Quantity": st.session_state.f_m_q,
            "Unit": st.session_state.f_m_u,
            "Unit Price": st.session_state.f_m_p_input,
            "Total Price": round(st.session_state.f_m_q * st.session_state.f_m_p_input, 4)
        })
        st.session_state.user_db.at[row_idx, 'material_data'] = str(curr_m)
        st.session_state.f_m_p_input = 0.0
        st.session_state.f_m_n = ""

def safe_eval_list(val):
    if not val or pd.isna(val) or str(val).strip() in ["", "[]", "nan", "NaN", "None"]:
        return []
    try:
        if isinstance(val, (list, dict)):
            return val
        return json.loads(val)
    except:
        try:
            return ast.literal_eval(str(val))
        except:
            return []


def to_float(val):
    try:
        return float(str(val).strip())
    except:
        return 0.0


@st.cache_data(ttl=3600, show_spinner=False)
def get_asset_sheet_data(worksheet_name):
    try:
        df = conn.read(spreadsheet=MY_SHEET_URL, worksheet=worksheet_name, ttl="1h")
        if df is None or df.empty: return pd.DataFrame()
        df.columns = [c.strip() for c in df.columns]
        return df
    except:
        return pd.DataFrame()


@st.cache_data(ttl=3600, show_spinner=False)
def get_db_sheet_data(worksheet_name):
    try:
        df = conn.read(spreadsheet=MY_SHEET_URL, worksheet=worksheet_name, ttl="1h")
        if df is None or df.empty: return pd.DataFrame()
        df.columns = [c.strip() for c in df.columns]
        return df
    except:
        return pd.DataFrame()


def load_all_assets_optimized():
    worksheets = ['Master_Robotic_Units', 'User_Robotic_Units', 'Master_Functional_Devices', 'User_Functional_Devices',
                  'Master_Vessels', 'User_Vessels']
    with ThreadPoolExecutor(max_workers=3) as executor:
        results = list(executor.map(get_asset_sheet_data, worksheets))
    m_robots, u_robots, m_devices, u_devices, m_vessels, u_vessels = results

    def process_hw(m_df, u_df, name_col, id_col, func_col):
        mapping, info, master_displays, user_displays = {}, {}, [], []
        if not m_df.empty and name_col in m_df.columns:
            for _, row in m_df.iterrows():
                n_disp = str(row[name_col]).strip()
                mapping[n_disp] = str(row[id_col]).strip()
                master_displays.append(n_disp)
                info[n_disp] = str(row.get(func_col, "No description available."))
        if not u_df.empty and name_col in u_df.columns:
            for _, row in u_df.iterrows():
                n_disp = f"[User] {str(row[name_col]).strip()}"
                mapping[n_disp] = str(row[id_col]).strip()
                user_displays.append(n_disp)
                info[n_disp] = str(row.get(func_col, "No description available."))
        return mapping, sorted(list(set(master_displays))) + sorted(list(set(user_displays))), info

    r_map, r_list, r_info = process_hw(m_robots, u_robots, 'Robot_Name', 'Robotic_unit', 'Function')
    d_map, d_list, d_info = process_hw(m_devices, u_devices, 'Device_Name', 'Device_Functional_Unit', 'Function')
    v_map, v_list, v_info = process_hw(m_vessels, u_vessels, 'Vessel_Name', 'Abbreviation', 'Description')
    return {"robot": (r_map, r_list, r_info), "device": (d_map, d_list, d_info), "vessel": (v_map, v_list, v_info)}


def smart_parse(raw_data, asset_mapping):
    if pd.isna(raw_data) or str(raw_data).lower() in ["nan", "", "[]", "none"]: return []
    raw_str = str(raw_data).replace("[", "").replace("]", "").replace("'", "").replace('"', "")
    items = [i.strip().lower() for i in re.split(r'[,;/]', raw_str) if i.strip()]
    matched, motion_map = [], {k.lower(): k for k in MOTION_OPTIONS}
    for item in items:
        if item in motion_map: matched.append(motion_map[item]); continue
        for full_n, abbr_id in asset_mapping.items():
            if item == abbr_id.lower() or item == full_n.lower(): matched.append(full_n); break
    return list(set(matched))


def load_template_to_state(template_row, assets, include_econ=False):
    st.session_state.reg_pre = str(template_row.get('Base_Root', str(template_row.get('RAM_ID', '')).split('-')[0]))
    st.session_state.reg_name = str(template_row.get('RAM_Name', ''))
    st.session_state.reg_purpose = str(template_row.get('Purpose', ''))
    st.session_state.reg_acts = smart_parse(template_row.get('Process_Action', ''), {})
    st.session_state.reg_robots = [n for n in assets["robot"][1] if
                                   n in smart_parse(template_row.get('Robot', ''), assets["robot"][0])]
    st.session_state.reg_devices = [n for n in assets["device"][1] if
                                    n in smart_parse(template_row.get('Functional_Device', ''), assets["device"][0])]
    if include_econ:
        st.session_state.reg_cap = int(template_row.get('Sample_Capacity', 96))
        st.session_state.reg_opt = str(template_row.get('Operation_Time(h)', "0.0"))
        st.session_state.reg_hot = str(template_row.get('Hands_on_Time(h)', "0.0"))


def register_cloud_asset(hw_type, data_dict, access_code, auth_df):
    """
    Registers hardware assets (Robot, Device, Vessel) to the cloud with quota validation.
    """
    # 1. Determine the target worksheet
    prefix = "Master" if str(access_code).strip() == MASTER_CODE else "User"
    sheet_name = f"{prefix}_Robotic_Units" if hw_type == "Robot" else (
        f"{prefix}_Functional_Devices" if hw_type == "Device" else f"{prefix}_Vessels")

    try:
        # 2. Load cloud data
        existing_df = conn.read(spreadsheet=MY_SHEET_URL, worksheet=sheet_name, ttl=0)

        # 3. [Normalize Case] Check and create access_code header
        if not existing_df.empty and 'access_code' not in existing_df.columns:
            existing_df['access_code'] = ""

        # 4. Quota validation via Auth_manage module
        can_reg, msg = am.check_registration_quota(existing_df, access_code, auth_df)

        if not can_reg:
            return False, msg  # Return rejection message if quota is exceeded

        # 5. Data preparation and merging
        data_dict['access_code'] = access_code
        new_row = pd.DataFrame([data_dict])
        updated_df = pd.concat([existing_df, new_row], ignore_index=True)

        # 6. Update cloud
        conn.update(spreadsheet=MY_SHEET_URL, worksheet=sheet_name, data=updated_df)

        # Clear cache to reflect the latest data on the next load
        get_asset_sheet_data.clear()
        if 'assets_cache' in st.session_state:
            del st.session_state.assets_cache

        return True, msg

    except Exception as e:
        return False, f"Sync failed: {e}"


# ==========================================
# 3. Data Synchronization & Loading
# ==========================================

# Clear cache and session state if a DB refresh is required
if st.session_state.get('db_needs_refresh', False):
    get_db_sheet_data.clear()
    if 'full_db' in st.session_state: del st.session_state.full_db
    if 'auth_df' in st.session_state: del st.session_state.auth_df
    st.session_state.db_needs_refresh = False

# Load data only if it is not in session state (API call optimization)
if 'assets_cache' not in st.session_state or 'full_db' not in st.session_state or 'auth_df' not in st.session_state:
    with st.spinner("⚡ Loading Latest Data..."):
        # 1. Load hardware assets
        st.session_state.assets_cache = load_all_assets_optimized()

        # 2. Load Master/User DB
        st.session_state.m_db = get_db_sheet_data('RAM_MasterDB')
        st.session_state.u_db_cloud = get_db_sheet_data('RAM_UserDB')

        # 3. [New] Load authorization and quota information
        st.session_state.auth_df = get_db_sheet_data('Access_codelist')

        # 4. Merge and preprocess the entire DB
        combined_db = pd.concat([st.session_state.m_db, st.session_state.u_db_cloud], ignore_index=True)

        # Prevent Arrow TypeError: Handle NaNs and force string type
        target_cols = ['RAM_ID', 'RAM_Name', 'Process_Action', 'Robot', 'Functional_Device']
        for col in target_cols:
            if col in combined_db.columns:
                combined_db[col] = combined_db[col].fillna("").astype(str)

        st.session_state.full_db = combined_db

# Assign cached data to local variables
assets = st.session_state.assets_cache
m_db = st.session_state.m_db
u_db_cloud = st.session_state.u_db_cloud
full_db = st.session_state.full_db

# [Solution] Assign empty DataFrame if auth_df is missing to prevent errors
auth_df = st.session_state.get('auth_df', pd.DataFrame(columns=['Code', 'Quota']))

DB_COLUMNS = ['RAM_ID', 'RAM_Name', 'Process_Action', 'Robot', 'Functional_Device', 'Purpose',
              'Operation_Time(h)', 'Hands_on_Time(h)', 'Sample_Capacity', 'Total_RAM_Cost(USD)',
              'access_code', 'io_data', 'material_data', 'Base_Root', 'Labor_cost(USD)',
              'Total_Time(h)', 'Total_Material_Cost(USD)']

# Initialize user_db (temporary storage) if it doesn't exist
if 'user_db' not in st.session_state or not isinstance(st.session_state.user_db, pd.DataFrame):
    st.session_state.user_db = pd.DataFrame(columns=DB_COLUMNS)


def on_master_change():
    if st.session_state.sm_1 != "-- Select Master --": st.session_state.su_1 = "-- Select User --"


def on_user_change():
    if st.session_state.su_1 != "-- Select User --": st.session_state.sm_1 = "-- Select Master --"


# ==========================================
# 4. UI Rendering
# ==========================================
st.markdown("<div id='top-anchor'></div>", unsafe_allow_html=True)
st.title("RAM Registration")

# Registration Completion Screen
if st.session_state.get('reg_complete'):
    st.success(f"### 🎉 RAM '{st.session_state.last_id}' Saved Successfully!")
    c_nav1, c_nav2 = st.columns(2)
    if c_nav1.button("📊 Go to RAM Database", width='stretch', type="primary"):
        reset_registration_state()
        st.switch_page("pages/RAM Database.py")
    if c_nav2.button("🏗️ Register Another RAM", width='stretch'):
        reset_registration_state()
        st.rerun()
    st.stop()

# --- STEP 1: Registration & Hardware Setup ---
if st.session_state.reg_step == 1:
    st.subheader("Step 1: Registration & Hardware Setup")

    with st.container(border=True):
        st.markdown("### Import Template (Optional)")
        # Guidance for Step 1 exclusive import
        st.caption(
            "※ This feature imports only the **Step 1: Registration & Hardware** configuration from the template.")

        c_t1, c_t2 = st.columns(2)
        m_list = [f"[{r.get('RAM_ID', '?')}] {r.get('RAM_Name', '?')}" for _, r in m_db.iterrows()]
        u_list = [f"[{r.get('RAM_ID', '?')}] {r.get('RAM_Name', '?')}" for _, r in u_db_cloud.iterrows()]

        sel_m = c_t1.selectbox("From MasterDB", ["-- Select Master --"] + m_list, key="sm_1",
                               on_change=on_master_change)
        sel_u = c_t2.selectbox("From UserDB", ["-- Select User --"] + u_list, key="su_1", on_change=on_user_change)

        if st.button("Load Selected Template", width='stretch'):
            target_df = m_db if sel_m != "-- Select Master --" else (
                u_db_cloud if sel_u != "-- Select User --" else None)
            if target_df is not None:
                selected_id = (sel_m if sel_m != "-- Select Master --" else sel_u).split(']')[0][1:]
                # Load Step 1 data only (include_econ=False)
                load_template_to_state(target_df[target_df['RAM_ID'] == selected_id].iloc[0], assets,
                                       include_econ=False)
                st.success(f"Template '{selected_id}' (Step 1 only) loaded successfully.")
                st.rerun()

        st.divider()

        # Input RAM ID and Name
        c1, c2 = st.columns(2)
        r_pre = c1.text_input("RAM ID :red[*]", value=st.session_state.reg_pre, placeholder="e.g., A, Z...").upper()
        r_nm = c2.text_input("RAM Name :red[*]", value=st.session_state.reg_name,
                             placeholder="e.g., Protein Purification")
        st.session_state.reg_pre, st.session_state.reg_name = r_pre, r_nm

        # Information on the next ID
        p = r_pre.strip()
        all_ids = [str(x).upper() for x in full_db['RAM_ID'].dropna().tolist()] if not full_db.empty else []
        nums = [int(rid.split("-")[-1]) for rid in all_ids if rid.startswith(f"{p}-") and rid.split("-")[-1].isdigit()]
        next_id = f"{p}-{str(max(nums) + 1).zfill(3)}" if nums else (f"{p}-002" if p in all_ids else p)
        if r_pre: st.info(f"ℹ️ Next ID for this RAM: **{next_id}**")

        st.session_state.reg_purpose = st.text_input("Purpose", value=st.session_state.reg_purpose)

        # Access Code and guidance text
        st.session_state.reg_code = st.text_input("🔐 RAM Access Code", type="password", value=st.session_state.reg_code)
        st.caption(
            "※ Without an access code, permissions for registration, editing, and deletion of this data will be restricted.")

        st.divider()

        # Hardware Configuration Section
        st.markdown("### Hardware Configuration")
        st.session_state.reg_acts = st.pills("Process Action", MOTION_OPTIONS, selection_mode="multi",
                                             default=st.session_state.reg_acts)

        # [Restore] Robot selection and new registration
        col_r1, col_r2 = st.columns([0.85, 0.15], vertical_alignment="bottom")
        sel_r = col_r1.multiselect("Compatible Robots", options=assets["robot"][1], default=st.session_state.reg_robots)
        st.session_state.reg_robots = sel_r
        if sel_r:
            for rbt in sel_r: col_r1.caption(f"🔧 **{rbt}**: {assets['robot'][2].get(rbt, 'No description available.')}")

        with col_r2:
            with st.popover("➕ New", width='stretch'):
                st.markdown("#### Register New Robot")
                nr_n = st.text_input("Robot Name", key="nr_name_input")
                nr_id = st.text_input("Abbreviation", key="nr_id_input")
                nr_m = st.pills("Available Motion", MOTION_OPTIONS, selection_mode="multi", key="nr_motion_pills")
                nr_f = st.text_area("Function/Description", key="nr_func_input")
                nr_c = st.text_input("Access Code", type="password", key="nr_code_input")
                if st.button("Register Robot", width='stretch', key="nr_reg_btn"):
                    if nr_n and nr_id:
                        # Passing auth_df at the end is the key
                        success, msg = register_cloud_asset("Robot", {
                            "Robot_Name": nr_n,
                            "Robotic_unit": nr_id,
                            "Available_Motion": str(nr_m),
                            "Function": nr_f
                        }, nr_c, auth_df)

                        if success:
                            st.success(f"Success: {msg}")  # Display success message from auth_manage
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error(msg)  # Display failure reason (e.g., quota exceeded)
                    else:
                        st.error("Please fill required fields.")

        # [Restore] Device selection and new registration
        col_d1, col_d2 = st.columns([0.85, 0.15], vertical_alignment="bottom")
        sel_d = col_d1.multiselect("Functional Devices", options=assets["device"][1],
                                   default=st.session_state.reg_devices)
        st.session_state.reg_devices = sel_d
        if sel_d:
            for dvc in sel_d: col_d1.caption(
                f"⚙️ **{dvc}**: {assets['device'][2].get(dvc, 'No description available.')}")

        with col_d2:
            with st.popover("➕ New", width='stretch'):
                st.markdown("#### Register New Device")
                nd_n = st.text_input("Device Name", key="nd_name_input")
                nd_id = st.text_input("Abbreviation", key="nd_id_input")
                nd_f = st.text_area("Function/Description", key="nd_func_input")
                nd_c = st.text_input("Access Code", type="password", key="nd_code_input")
                if st.button("Register Device", width='stretch', key="nd_reg_btn"):
                    if nd_n and nd_id:
                        # Add auth_df and receive two return values
                        success, msg = register_cloud_asset("Device", {
                            "Device_Name": nd_n,
                            "Device_Functional_Unit": nd_id,
                            "Function": nd_f
                        }, nd_c, auth_df)

                        if success:
                            st.success(f"Success: {msg}")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error(msg)
                    else:
                        st.error("Please fill required fields.")

        st.divider()

        # Proceed Button: update user_db and move to Step 2
        if st.button("Proceed to Substance I/O 🧪", type="primary", width='stretch', disabled=not (r_pre and r_nm)):
            st.session_state.reg_id = next_id
            can_proceed, msg = am.check_registration_quota(full_db, st.session_state.reg_code, auth_df)
            if not can_proceed:
                st.error(msg)
                st.stop()
            else:
                st.toast(msg)

            existing_io, existing_mat = "[]", "[]"
            if not st.session_state.user_db.empty and next_id in st.session_state.user_db['RAM_ID'].values:
                idx_f = st.session_state.user_db.index[st.session_state.user_db['RAM_ID'] == next_id][0]
                existing_io = st.session_state.user_db.at[idx_f, 'io_data']
                existing_mat = st.session_state.user_db.at[idx_f, 'material_data']

            row_dict = {col: (0.0 if "USD" in col or "(h)" in col else ("[]" if "data" in col else "")) for col in
                        DB_COLUMNS}
            row_dict.update({
                'RAM_ID': next_id, 'RAM_Name': r_nm, 'Process_Action': str(st.session_state.reg_acts),
                'Robot': str([assets["robot"][0][n] for n in sel_r]),
                'Functional_Device': str([assets["device"][0][n] for n in sel_d]),
                'Purpose': st.session_state.reg_purpose, 'access_code': st.session_state.reg_code,
                'Base_Root': r_pre, 'Sample_Capacity': st.session_state.reg_cap,
                'Operation_Time(h)': to_float(st.session_state.reg_opt),
                'Hands_on_Time(h)': to_float(st.session_state.reg_hot),
                'io_data': existing_io, 'material_data': existing_mat
            })

            if st.session_state.user_db.empty:
                st.session_state.user_db = pd.DataFrame([row_dict])
            elif next_id in st.session_state.user_db['RAM_ID'].values:
                idx_old = st.session_state.user_db.index[st.session_state.user_db['RAM_ID'] == next_id][0]
                for k, v in row_dict.items(): st.session_state.user_db.at[idx_old, k] = v
            else:
                st.session_state.user_db = pd.concat([st.session_state.user_db, pd.DataFrame([row_dict])],
                                                     ignore_index=True)

            st.session_state.reg_step = 2;
            st.rerun()

# --- STEP 2: Substance I/O Setup ---
elif st.session_state.reg_step == 2:
    # 0. Setup and Indexing
    idx = st.session_state.user_db.index[st.session_state.user_db['RAM_ID'] == st.session_state.reg_id][0]
    IO_COLUMNS = ["Type", "Substance", "Classification", "Vessel", "Vessel Class", "Essential"]

    st.subheader(f"Step 2: Substance I/O - {st.session_state.reg_id}")

    # 1. [Modular Import] Unified & Robust Import Section
    with st.container(border=True):
        st.markdown("### Import I/O Template (Optional)")
        st.caption(
            "※ This logic scans all columns to find valid I/O data, fixing issues from 'Workflow Builder' overwrites.")

        c_imp1, c_imp2 = st.columns([0.8, 0.2], vertical_alignment="bottom")
        imp_options = [f"[{r['RAM_ID']}] {r['RAM_Name']}" for _, r in full_db.iterrows()]

        # Unique key added to prevent DuplicateElementId error
        sel_imp = c_imp1.selectbox(
            "Select Source RAM for I/O",
            ["-- Select RAM --"] + imp_options,
            key="selectbox_import_io_v3"
        )

        if c_imp2.button("Import I/O", width='stretch', key="btn_import_io_v3"):
            if sel_imp != "-- Select RAM --":
                try:
                    # Robust ID extraction: [A-002] -> A-002 (lowercase and stripped for perfect matching)
                    target_id_str = sel_imp.split(']')[0][1:].strip().lower()

                    # Create a normalized temporary DB for searching
                    df_temp = full_db.copy()
                    df_temp.columns = [str(col).strip().lower().replace(" ", "_") for col in df_temp.columns]

                    # Search for matching row
                    id_col_key = 'ram_id' if 'ram_id' in df_temp.columns else df_temp.columns[0]
                    target_mask = df_temp[id_col_key].astype(str).str.strip().str.lower() == target_id_str
                    match_res = df_temp[target_mask]

                    if not match_res.empty:
                        # Scan all potential I/O columns (io_data, io_data.1, etc.)
                        io_search_list = [c for c in df_temp.columns if 'io_data' in c]
                        final_io_val = "[]"
                        max_len = 0

                        # Find the column with the most substantial content (longest string)
                        for c_name in io_search_list:
                            candidate = match_res[c_name].iloc[0]
                            str_cand = str(candidate).strip() if pd.notna(candidate) else ""
                            if str_cand and str_cand not in ["nan", "[]", "None"] and len(str_cand) > max_len:
                                final_io_val = str_cand
                                max_len = len(str_cand)

                        # Update session state and reset editor widget state
                        st.session_state.user_db.at[idx, 'io_data'] = final_io_val
                        if 'io_edit_widget_v3' in st.session_state:
                            del st.session_state.io_edit_widget_v3

                        st.success(f"Successfully loaded I/O for {target_id_str.upper()}")
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.error(f"Mapping failed: ID '{target_id_str.upper()}' not found.")
                except Exception as e:
                    st.error(f"Import process error: {e}")

    st.divider()

    # 2. Add New Substance Section
    with st.container(border=True):
        st.markdown("#### ➕ Add New Substance")
        cio1, cio2, cio3, cio4, cio5, cio6, cio7 = st.columns([0.5, 1.0, 0.8, 0.8, 0.8, 0.2, 0.4],
                                                              vertical_alignment="bottom")

        f_io_t = cio1.selectbox("Type", ["Input", "Output"], key="f_io_type_v3")
        f_io_s = cio2.text_input("Substance Name", key="f_io_name_v3", placeholder="e.g., DNA Stock")
        f_io_c = cio3.selectbox("Substance Class", SUBSTANCE_CLASSES, key="f_io_class_v3")
        f_io_v = cio4.selectbox("Vessel", options=assets["vessel"][1], key="f_io_vessel_v3")
        f_io_vc = cio5.selectbox("Vessel Class", VESSEL_CLASS_OPTIONS, key="f_io_vclass_v3")

        with cio6:  # Vessel Registration Popover
            with st.popover("➕", key="popover_vessel_v3"):
                st.markdown("#### Register New Vessel")
                nv_n = st.text_input("Full Name", key="nv_name_v3")
                nv_a = st.text_input("Abbreviation", key="nv_abbr_v3")
                nv_vc = st.selectbox("Vessel Class", VESSEL_CLASS_OPTIONS, key="nv_class_v3")
                nv_d = st.text_area("Description", key="nv_desc_v3")
                nv_c = st.text_input("Access Code", type="password", key="nv_code_v3")
                if st.button("Register Vessel", width='stretch', key="btn_reg_vessel_v3"):
                    if nv_n and nv_a:
                        success, msg = register_cloud_asset("Vessel", {
                            "Vessel_Name": nv_n, "Abbreviation": nv_a,
                            "Vessel_classification": nv_vc, "Description": nv_d
                        }, nv_c, auth_df)
                        if success:
                            st.success(f"Success: {msg}");
                            time.sleep(1);
                            st.rerun()
                        else:
                            st.error(msg)
                    else:
                        st.error("Please fill required fields.")

        f_io_e = cio7.checkbox("Ess.", value=True, key="f_io_ess_v3")

        if st.button("Add to I/O List", width='stretch', key="btn_add_sub_v3") and f_io_s:
            temp_io_list = safe_eval_list(st.session_state.user_db.at[idx, 'io_data'])
            temp_io_list.append({
                "Type": f_io_t, "Substance": f_io_s, "Classification": f_io_c,
                "Vessel": f_io_v, "Vessel Class": f_io_vc, "Essential": f_io_e
            })
            st.session_state.user_db.at[idx, 'io_data'] = str(temp_io_list)
            if 'io_edit_widget_v3' in st.session_state:
                del st.session_state.io_edit_widget_v3
            st.rerun()

    # 3. I/O Data Editor
    raw_list = safe_eval_list(st.session_state.user_db.at[idx, 'io_data'])
    io_df_display = pd.DataFrame(raw_list)
    if io_df_display.empty:
        io_df_display = pd.DataFrame(columns=IO_COLUMNS)

    edited_io_res = st.data_editor(
        io_df_display,
        width='stretch',
        num_rows="dynamic",
        key="io_edit_widget_v3",
        column_config={
            "Essential": st.column_config.CheckboxColumn("Ess. ✅"),
            "Classification": st.column_config.SelectboxColumn("Substance Class", options=SUBSTANCE_CLASSES),
            "Vessel": st.column_config.SelectboxColumn("Vessel", options=assets["vessel"][1]),
            "Vessel Class": st.column_config.SelectboxColumn("Vessel Class", options=VESSEL_CLASS_OPTIONS)
        }
    )
    st.session_state.user_db.at[idx, 'io_data'] = json.dumps(edited_io_res.to_dict('records'))

    st.divider()

    # 4. Navigation & Validation (Strict Rule: Both Input and Output required)
    c_nav1, c_nav2 = st.columns(2)
    if c_nav1.button("⬅️ Back to Step 1", width='stretch', key="btn_back_v3"):
        st.session_state.reg_step = 1;
        st.rerun()

    # Logic to check for both Input and Output
    final_verify_list = safe_eval_list(st.session_state.user_db.at[idx, 'io_data'])
    has_input_sub = any(str(item.get('Type')).lower() == 'input' for item in final_verify_list)
    has_output_sub = any(str(item.get('Type')).lower() == 'output' for item in final_verify_list)

    # Step 3 access condition
    can_go_step3 = has_input_sub and has_output_sub
    proceed_btn_label = "Proceed to Economics 💰" if can_go_step3 else "⚠️ Need both Input & Output"

    if c_nav2.button(proceed_btn_label, type="primary", width='stretch',
                     disabled=not can_go_step3, key="btn_next_v3"):
        st.session_state.reg_step = 3;
        st.rerun()

# --- STEP 3: Economics & Materials ---
elif st.session_state.reg_step == 3:
    idx = st.session_state.user_db.index[st.session_state.user_db['RAM_ID'] == st.session_state.reg_id][0]
    st.subheader(f"Step 3: Economics & Materials - {st.session_state.reg_id}")

    # [Update] Unified Economics Import Logic
    with st.container(border=True):
        st.markdown("### Import Economics Template (Optional)")
        c_mi1, c_mi2 = st.columns([0.8, 0.2], vertical_alignment="bottom")
        imp_options = [f"[{r['RAM_ID']}] {r['RAM_Name']}" for _, r in full_db.iterrows()]
        sel_imp_m = c_mi1.selectbox("Select Source RAM for Economics", ["-- Select RAM --"] + imp_options)

        if c_mi2.button("Import Data", width='stretch'):
            if sel_imp_m != "-- Select RAM --":
                sid = sel_imp_m.split(']')[0][1:]
                source_row = full_db[full_db['RAM_ID'] == sid].iloc[0]

                # 1. Extract original data values
                opt_val = str(source_row.get('Operation_Time(h)', "0.0"))
                hot_val = str(source_row.get('Hands_on_Time(h)', "0.0"))
                cap_val = int(source_row.get('Sample_Capacity', 96))
                mat_data = source_row.get('material_data', '[]')

                # 2. Update widget session states directly
                st.session_state.opt_input_widget = opt_val
                st.session_state.hot_input_widget = hot_val
                st.session_state.edit_cap_input = cap_val

                # 3. Synchronize variables for internal calculation
                st.session_state.reg_opt = opt_val
                st.session_state.reg_hot = hot_val
                st.session_state.reg_cap = cap_val

                # 4. Update user_db row data
                st.session_state.user_db.at[idx, 'material_data'] = mat_data
                st.session_state.user_db.at[idx, 'Operation_Time(h)'] = to_float(opt_val)
                st.session_state.user_db.at[idx, 'Hands_on_Time(h)'] = to_float(hot_val)
                st.session_state.user_db.at[idx, 'Sample_Capacity'] = cap_val

                st.success(f"Economics data imported from {sid}!")
                time.sleep(0.5)
                st.rerun()

    st.divider()

    # Summary information at the top
    with st.expander("🔍 Review RAM Setup Summary", expanded=True):
        sum_c1, sum_c2 = st.columns(2)
        with sum_c1:
            st.markdown("**🛠️ Hardware & Action**")
            st.write(f"- **Name:** {st.session_state.reg_name}")
            st.write(f"- **Actions:** {', '.join(st.session_state.reg_acts)}")
        with sum_c2:
            st.markdown("**🧪 Substance I/O**")
            io_df_sum = pd.DataFrame(safe_eval_list(st.session_state.user_db.at[idx, 'io_data']))
            if not io_df_sum.empty:
                st.dataframe(io_df_sum[['Type', 'Substance', 'Vessel', 'Essential']], width='stretch', hide_index=True)

    st.divider()

    # Load Data
    m_list = safe_eval_list(st.session_state.user_db.at[idx, 'material_data'])
    m_df = pd.DataFrame(m_list)


    def calc_mat_sum(df):
        if df.empty: return 0.0
        q = pd.to_numeric(df['Quantity'].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
        p = pd.to_numeric(df['Unit Price'].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
        return (q * p).sum()


    mat_sum_val = calc_mat_sum(m_df)
    cur_hot, cur_opt = to_float(st.session_state.reg_hot), to_float(st.session_state.reg_opt)

    # Real-time metric dashboard
    m1, m2 = st.columns(2)
    m1.metric("Total Time (h)", f"{(cur_hot + cur_opt):.2f} h")
    m2.metric("Total Cost (USD)", f"{((cur_hot * LABOR_RATE) + mat_sum_val):,.2f}")

    st.divider()

    # Time and Throughput configuration widgets (Directly reflects session state updated during Import)
    i1, i2, i3, i4 = st.columns(4)
    i1.number_input("Capacity", min_value=96, step=96, key="edit_cap_input", on_change=update_capacity)
    i2.text_input("Operation Time (h)", key="opt_input_widget", on_change=sync_opt)
    i3.text_input("Hands on Time (h)", key="hot_input_widget", on_change=sync_hot)
    i4.metric("Labor Cost (USD)", f"{(to_float(st.session_state.get('reg_hot', 0)) * LABOR_RATE):,.2f}")

    st.markdown("#### 📦 Material Items (Bill of Materials)")

    # Material addition section
    with st.container(border=True):
        st.markdown("##### ➕ Add New Material")
        mc = st.columns([0.26, 0.1, 0.1, 0.18, 0.21, 0.15], vertical_alignment="bottom")
        f_m_n = mc[0].text_input("Material Name", placeholder="e.g., PCR Kit", key="f_m_n")
        f_m_q = mc[1].number_input("Qty", min_value=0.0, value=1.0, format="%.2f", key="f_m_q")
        f_m_u = mc[2].selectbox("Unit", options=UNIT_OPTIONS, key="f_m_u")
        f_m_p = mc[3].number_input("Unit Price (USD)", format="%.4f", key="f_m_p_input")

        with mc[4]:
            with st.popover("🔢 Price Calc", width='stretch'):
                p_tot = st.number_input("Total Purchase Price (USD)", min_value=0.0, step=0.01)
                p_pk = st.number_input("Number of Packs", min_value=1, value=1)
                p_qp = st.number_input("Qty per Pack", min_value=1, value=1)
                calc_val = p_tot / (p_pk * p_qp) if (p_pk * p_qp) > 0 else 0.0
                st.info(f"Calculated: **{calc_val:,.4f} USD**")
                st.button("Apply", on_click=apply_calc_to_input_callback, args=(calc_val,), width='stretch')

        if mc[5].button("Add Item", width='stretch'):
            if f_m_n:
                m_list.append({"Material Name": f_m_n, "Quantity": f_m_q, "Unit": f_m_u, "Unit Price": f_m_p,
                               "Total Price": round(f_m_q * f_m_p, 2)})
                st.session_state.user_db.at[idx, 'material_data'] = json.dumps(m_list)
                st.rerun()

    # BOM Editor
    edited_mat = st.data_editor(
        pd.DataFrame(m_list), num_rows="dynamic", width='stretch', key="mat_edit",
        column_config={
            "Unit Price": st.column_config.NumberColumn("Price (USD/Unit)", format="%.4f"),
            "Total Price": st.column_config.NumberColumn("Total Price (USD)", disabled=True, format="%.2f")
        }
    )
    st.session_state.user_db.at[idx, 'material_data'] = json.dumps(edited_mat.to_dict('records'))

    st.divider()

    # Bottom navigation and final save
    c_f1, c_f2 = st.columns(2)
    if c_f1.button("⬅️ Back to I/O Setup", width='stretch'):
        st.session_state.reg_step = 2
        st.rerun()

    if c_f2.button("✅ Save & Finish Registration", type="primary", width='stretch'):
        with st.spinner("Saving to Cloud Database..."):
            try:
                # 1. [Security & Quota Check] Final approval check before saving
                # full_db: total data loaded so far, reg_code: user input code, auth_df: authorization ledger
                can_save, auth_msg = am.check_registration_quota(full_db, st.session_state.reg_code, auth_df)

                if not can_save:
                    # Stop if quota exceeded or invalid code
                    st.error(auth_msg)
                    st.stop()

                # 2. [Data Preparation] Construct final row data for saving
                final_row = st.session_state.user_db.iloc[idx].copy()
                # Calculate total amount by parsing material data (JSON/List string)
                mat_final_sum = calc_mat_sum(pd.DataFrame(safe_eval_list(final_row['material_data'])))

                # Final update of economic and time metrics
                final_row.update({
                    'Sample_Capacity': st.session_state.reg_cap,
                    'Operation_Time(h)': to_float(st.session_state.reg_opt),
                    'Hands_on_Time(h)': to_float(st.session_state.reg_hot),
                    'Labor_cost(USD)': (to_float(st.session_state.reg_hot) * LABOR_RATE),
                    'Total_Time(h)': (to_float(st.session_state.reg_opt) + to_float(st.session_state.reg_hot)),
                    'Total_Material_Cost(USD)': mat_final_sum,
                    'Total_RAM_Cost(USD)': (to_float(st.session_state.reg_hot) * LABOR_RATE) + mat_final_sum
                })

                # 3. [Target Worksheet Determination] Branch storage location based on Master Code input
                # Transfer to MasterDB if 'fmb2016' is entered, otherwise to UserDB
                target_ws = "RAM_MasterDB" if str(st.session_state.reg_code).strip() == MASTER_CODE else "RAM_UserDB"

                # Read latest sheet status (Real-time comparison without cache)
                db_now = conn.read(spreadsheet=MY_SHEET_URL, worksheet=target_ws, ttl=0)

                if db_now is None or db_now.empty:
                    db_now = pd.DataFrame([final_row])
                else:
                    # Merge after excluding existing RAM_ID row to overwrite if it exists
                    db_now = pd.concat([db_now[db_now['RAM_ID'] != st.session_state.reg_id], pd.DataFrame([final_row])],
                                       ignore_index=True)

                # 4. [Cloud Update and State Reflection]
                conn.update(spreadsheet=MY_SHEET_URL, worksheet=target_ws, data=db_now)

                # Set success flag and lead to completion page
                st.session_state.db_needs_refresh = True
                st.session_state.reg_complete = True
                st.session_state.last_id = st.session_state.reg_id

                st.success(f"Success! {auth_msg}")  # Success notification with authorization message
                time.sleep(1)
                st.rerun()

            except Exception as e:
                st.error(f"Save failed: {e}")

st.markdown(back_to_top_html, unsafe_allow_html=True)
