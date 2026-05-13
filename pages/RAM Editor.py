import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import re
import ast
import time
from concurrent.futures import ThreadPoolExecutor
import json
import Auth_manage as am
# Compliance with pandas 2026 standards
pd.set_option('future.no_silent_downcasting', True)

# --- Constants & Config ---
MY_SHEET_URL = st.secrets["connections"]["gsheets"]["spreadsheet"]
MASTER_CODE = st.secrets["MASTER_CODE"]
LABOR_RATE = 37.5

MOTION_OPTIONS = ["Colony Picking", "Liquid Transfer", "Labware Transfer"]
ACTION_ROBOT_GUIDE = {
    "Colony Picking": "LiHa is recommended for this action.",
    "Liquid Transfer": "LiHa or MCA are recommended for this action.",
    "Labware Transfer": "RoMa is recommended for this action."
}
VESSEL_CLASS_OPTIONS = ["Microplate", "Digital data", "Tube", "Trough", "Agar plate"]
SUBSTANCE_CLASSES = ["DNA", "Reaction Mix", "Buffer", "Solvent", "Liquid Medium", "Cells", "Solid Medium (Plate)",
                     "Fraction", "Analyte / Sample", "Data"]
UNIT_OPTIONS = ["rxn", "ea", "uL", "mL"]

conn = st.connection("gsheets", type=GSheetsConnection)


# ==========================================
# 1. Utilities & Callbacks
# ==========================================

def safe_eval_list(val):
    if not val or pd.isna(val) or str(val).strip() in ["", "[]", "nan", "NaN", "None"]:
        return []
    try:
        if isinstance(val, (list, dict)):
            return val
        return json.loads(val)
    except:
        try:
            return ast.literal_eval(str(val))  # fallback
        except:
            return []


def to_float(val):
    try:
        return float(str(val).strip())
    except:
        return 0.0

def ram_id_sort_key(ram_id):
    s = str(ram_id).strip().upper()
    m = re.match(r"^([A-Z]+)(?:-(\d+))?$", s)

    if not m:
        return (s, 10**9)

    prefix = m.group(1)
    num = int(m.group(2)) if m.group(2) else 0
    return (prefix, num)


def sort_ram_db(df):
    if df is None or df.empty or "RAM_ID" not in df.columns:
        return df

    df = df.copy()
    df["_ram_sort_key"] = df["RAM_ID"].apply(ram_id_sort_key)
    df = (
        df.sort_values("_ram_sort_key")
        .drop(columns="_ram_sort_key")
        .reset_index(drop=True)
    )
    return df


def apply_calc_to_edit_callback(val):
    st.session_state.f_m_p_input = val


def add_edit_material_callback():
    if st.session_state.f_m_n:
        st.session_state.edit_mat_list.append({
            "Material Name": st.session_state.f_m_n,
            "Quantity": st.session_state.f_m_q,
            "Unit": st.session_state.f_m_u,
            "Unit Price": st.session_state.f_m_p_input,
            "Total Price": round(st.session_state.f_m_q * st.session_state.f_m_p_input, 4)
        })
        st.session_state.f_m_p_input = 0.0
        st.session_state.f_m_n = ""

@st.cache_data(ttl=3600, show_spinner=False)
def get_asset_sheet_data(worksheet_name):
    try:
        df = conn.read(spreadsheet=MY_SHEET_URL, worksheet=worksheet_name, ttl=600)
        if df is None or df.empty:
            return pd.DataFrame()
        df.columns = [c.strip() for c in df.columns]
        return df
    except:
        return pd.DataFrame()


@st.cache_data(ttl=60, show_spinner=False)
def get_db_sheet_data(worksheet_name):
    try:
        df = conn.read(spreadsheet=MY_SHEET_URL, worksheet=worksheet_name, ttl=30)
        if df is None or df.empty:
            return pd.DataFrame(columns=['RAM_ID'])

        df.columns = df.columns.str.strip()
        return df
    except Exception:
        return pd.DataFrame(columns=['RAM_ID'])


def load_all_assets_optimized():
    worksheets = ['Master_Robotic_Units', 'User_Robotic_Units', 'Master_Functional_Devices', 'User_Functional_Devices',
                  'Master_Vessels', 'User_Vessels']
    with ThreadPoolExecutor(max_workers=3) as executor:
        results = list(executor.map(get_asset_sheet_data, worksheets))
    m_robots, u_robots, m_devices, u_devices, m_vessels, u_vessels = results

    def process_hw(m_df, u_df, name_col, id_col, info_col):
        mapping, displays, info_dict = {}, [], {}
        for df in [m_df, u_df]:
            if not df.empty and name_col in df.columns:
                prefix = "[User] " if df is u_df else ""
                for _, row in df.iterrows():
                    n_disp = f"{prefix}{str(row[name_col]).strip()}"
                    mapping[n_disp] = str(row[id_col]).strip()
                    displays.append(n_disp)
                    info_dict[n_disp] = str(row.get(info_col, "No description available."))
        return mapping, sorted(list(set(displays))), info_dict

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


# [CALLBACKS]
def sync_edit_opt(): st.session_state.edit_opt = st.session_state.opt_widget


def sync_edit_hot(): st.session_state.edit_hot = st.session_state.hot_widget


def update_edit_capacity():
    val = st.session_state.cap_widget
    if val % 96 != 0:
        val = max(96, (val // 96) * 96)
        st.toast(f"⚠️ Adjusted to {val}.")
    st.session_state.edit_cap = val


# ==========================================
# 2. Initialization & Target Validation
# ==========================================
if not st.session_state.get('edit_target'):
    st.warning("⚠️ No RAM selected. Please select from RAM DB.")
    if st.button("📊 Back to RAM Database", width="stretch"): st.switch_page("pages/RAM Database.py")
    st.stop()

if "f_m_p_input" not in st.session_state: st.session_state.f_m_p_input = 0.0

target_id = str(st.session_state.edit_target).strip().upper()
st.session_state.edit_target = target_id

assets = load_all_assets_optimized()

with st.spinner("Syncing latest data from Cloud..."):
    get_db_sheet_data.clear()

    m_db = get_db_sheet_data("RAM_MasterDB")
    u_db = get_db_sheet_data("RAM_UserDB")

    for df in [m_db, u_db]:
        if not df.empty and "RAM_ID" in df.columns:
            df["RAM_ID"] = df["RAM_ID"].astype(str).str.strip().str.upper()

    if "RAM_ID" in m_db.columns:
        is_master = target_id in m_db["RAM_ID"].values
    else:
        is_master = False

    full_db = pd.concat([m_db, u_db], ignore_index=True)
    source_worksheet = "RAM_MasterDB" if is_master else "RAM_UserDB"

    if not full_db.empty and "RAM_ID" in full_db.columns:
        target_row_df = full_db[full_db["RAM_ID"] == target_id]
    else:
        target_row_df = pd.DataFrame()

if target_row_df.empty:
    st.error(f"❌ Data not found for ID: {target_id}. (Data load failed or ID mismatch)")
    st.stop()

r_data = target_row_df.iloc[0].to_dict()

if st.session_state.get('current_loaded_id') != target_id:
    st.session_state.edit_io_list = safe_eval_list(r_data.get('io_data', '[]'))
    st.session_state.edit_mat_list = safe_eval_list(r_data.get('material_data', '[]'))
    st.session_state.edit_cap = int(to_float(r_data.get('Sample_Capacity', 96)))
    st.session_state.edit_opt = str(r_data.get('Operation_Time(h)', "0.0"))
    st.session_state.edit_hot = str(r_data.get('Hands_on_Time(h)', "0.0"))
    st.session_state.edit_acts = smart_parse(r_data.get('Process_Action', ''), {})
    st.session_state.current_loaded_id = target_id

# ==========================================
# 3. UI Construction
# ==========================================
c_head1, c_head2 = st.columns([0.8, 0.2])
c_head1.title(f"🛠️ RAM Editor: {target_id}")
c_head1.caption(f"Editing Source: {source_worksheet}")

with c_head2:
    with st.popover("🗑️ Delete Module", width="stretch"):
        st.error(f"Deleting from {source_worksheet}. This is permanent.")
        del_pw = st.text_input("Access Code", type="password", key="del_auth")
        if st.button("🔥 Confirm Deletion", width="stretch", type="primary"):
            raw_saved_pw = r_data.get('access_code', r_data.get('Access_Code', ''))

            # Robust parsing of passwords to prevent truncating on periods
            raw_pw_str = str(raw_saved_pw).strip() if not pd.isna(raw_saved_pw) else "None"
            saved_pw = raw_pw_str[:-2] if raw_pw_str.endswith('.0') else raw_pw_str

            if am.is_edit_authorized(del_pw, saved_pw):
                try:
                    latest_db = get_db_sheet_data(source_worksheet)
                    updated_db = latest_db[latest_db['RAM_ID'] != target_id]
                    conn.update(spreadsheet=MY_SHEET_URL, worksheet=source_worksheet, data=updated_db)
                    get_db_sheet_data.clear()
                    st.session_state.db_needs_refresh = True
                    st.success("Deleted successfully.")
                    time.sleep(0.5)
                    st.session_state.edit_target = None
                    st.switch_page("pages/RAM Database.py")
                except Exception as e:
                    st.error(f"Deletion failed: {e}")
            else:
                st.error("❌ Invalid Code")

with st.expander("⚡ Quick Import Input/Output Data"):
    c_imp1, c_imp2 = st.columns([0.8, 0.2])
    imp_options = [f"[{r['RAM_ID']}] {r['RAM_Name']}" for _, r in full_db.iterrows()]
    sel_imp = c_imp1.selectbox("Select Source RAM", ["-- Select RAM --"] + imp_options, key="edit_import_sel")
    with c_imp2:
        st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
        if st.button("Import I/O", width="stretch", key="btn_editor_import_io"):
            if sel_imp != "-- Select RAM --":
                try:
                    source_id = sel_imp.split(']')[0][1:].strip().lower()
                    df_temp = full_db.copy()
                    df_temp.columns = [str(col).strip().lower().replace(" ", "_") for col in df_temp.columns]

                    id_col_key = 'ram_id' if 'ram_id' in df_temp.columns else df_temp.columns[0]
                    target_mask = df_temp[id_col_key].astype(str).str.strip().str.lower() == source_id
                    match_res = df_temp[target_mask]

                    if not match_res.empty:
                        # Scan all potential I/O columns to find valid data
                        io_search_list = [c for c in df_temp.columns if 'io_data' in c]
                        final_io_val = "[]"
                        max_len = 0
                        for c_name in io_search_list:
                            candidate = match_res[c_name].iloc[0]
                            str_cand = str(candidate).strip() if pd.notna(candidate) else ""
                            if str_cand and str_cand not in ["nan", "[]", "None"] and len(str_cand) > max_len:
                                final_io_val = str_cand
                                max_len = len(str_cand)

                        st.session_state.edit_io_list = safe_eval_list(final_io_val)
                        st.toast("✅ Imported Successfully!")
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.error(f"Failed to locate RAM ID '{source_id.upper()}'")
                except Exception as e:
                    st.error(f"Import failed: {e}")

st.divider()

with st.form("metadata_form"):
    c_b1, c_b2 = st.columns(2)
    new_name = c_b1.text_input("RAM Name", value=r_data.get('RAM_Name', ''))
    old_pre = str(r_data.get('Base_Root', target_id.split('-')[0]))
    new_pre = c_b2.text_input("RAM ID Prefix", value=old_pre).upper().strip()
    new_purp = st.text_area("Purpose", value=r_data.get('Purpose', ''), height=100)
    submitted = st.form_submit_button("Update Metadata Above")
    if submitted:
        st.toast("✅ Metadata updated in session! (Click 'Save to DB' below to finalize)")

final_id = target_id
if new_pre != old_pre:
    all_ids = full_db['RAM_ID'].dropna().unique()
    nums = [int(rid.split("-")[-1]) for rid in all_ids if
            str(rid).startswith(f"{new_pre}-") and rid.split("-")[-1].isdigit()]
    final_id = f"{new_pre}-{str(max(nums) + 1).zfill(3)}" if nums else f"{new_pre}-001"
    st.warning(f"⚠️ ID will be updated to {final_id}")

st.markdown("### Hardware Setup")
st.pills(
    "Required Action Type",
    MOTION_OPTIONS,
    selection_mode="multi",
    key="edit_acts"
)

if not st.session_state.edit_acts:
    st.info("Select all Action Types required for that RAM.", icon="ℹ️")
else:
    for act in st.session_state.edit_acts:
        guide_msg = ACTION_ROBOT_GUIDE.get(act)
        if guide_msg:
            st.info(guide_msg, icon="ℹ️")
    ch1, ch2 = st.columns(2)
    new_rbts = ch1.multiselect(
        "Robots",
        options=assets["robot"][1],
        default=[n for n in assets["robot"][1] if n in smart_parse(r_data.get('Robot', ''), assets["robot"][0])]
    )
    new_dvcs = ch2.multiselect(
        "Devices",
        options=assets["device"][1],
        default=[n for n in assets["device"][1] if
                 n in smart_parse(r_data.get('Functional_Device', ''), assets["device"][0])]
    )

st.markdown("### 🧪 Input/Output")
with st.container(border=True):
    with st.form("add_substance_form"):
        st.markdown("#### Add New Substance")
        cio1, cio2, cio3, cio4, cio5, cio6 = st.columns([0.6, 1.1, 1.0, 0.9, 0.9, 0.5])
        f_io_t, f_io_s = cio1.selectbox("Type", ["Input", "Output"]), cio2.text_input("Substance Name")
        f_io_c = cio3.selectbox("Substance Class", SUBSTANCE_CLASSES)
        f_io_v, f_io_vc = cio4.selectbox("Vessel", options=assets["vessel"][1]), cio5.selectbox("Vessel Class",
                                                                                                VESSEL_CLASS_OPTIONS)
        cio6.markdown("<div style='margin-top: 25px;'></div>", unsafe_allow_html=True)
        f_io_e = cio6.checkbox("Ess.", value=True)
        if st.form_submit_button("➕ Add", width='stretch'):
            if f_io_s:
                st.session_state.edit_io_list.append(
                    {"Type": f_io_t, "Substance": f_io_s, "Classification": f_io_c, "Vessel": f_io_v,
                     "Vessel Class": f_io_vc, "Essential": f_io_e})
                st.rerun()

    updated_io_df = st.data_editor(pd.DataFrame(st.session_state.edit_io_list), num_rows="dynamic", width='stretch',
                                   column_config={"Classification": st.column_config.SelectboxColumn("Substance Class",
                                                                                                     options=SUBSTANCE_CLASSES),
                                                  "Type": st.column_config.SelectboxColumn("Type",
                                                                                           options=["Input", "Output"]),
                                                  "Vessel": st.column_config.SelectboxColumn("Vessel",
                                                                                             options=assets["vessel"][
                                                                                                 1]),
                                                  "Vessel Class": st.column_config.SelectboxColumn("Vessel Class",
                                                                                                   options=VESSEL_CLASS_OPTIONS),
                                                  "Essential": st.column_config.CheckboxColumn("Ess. ✅")},
                                   key="io_editor")
    st.session_state.edit_io_list = updated_io_df.to_dict('records')

st.markdown("### 💰 Economics & Productivity")
m_df = pd.DataFrame(st.session_state.edit_mat_list)

with st.container(border=True):
    def calc_mat_total(df):
        if df.empty: return 0.0
        q_col = "Quantity"
        p_col = "Unit Price" if "Unit Price" in df.columns else "Unit price"
        if q_col not in df.columns or p_col not in df.columns: return 0.0
        return (pd.to_numeric(df[q_col], errors='coerce').fillna(0) * pd.to_numeric(df[p_col], errors='coerce').fillna(
            0)).sum()


    mat_sum_val = calc_mat_total(m_df)
    m1, m2 = st.columns(2)
    m1.metric("Total Time (h)", f"{(to_float(st.session_state.edit_opt) + to_float(st.session_state.edit_hot)):.2f} ")
    m2.metric("Total Cost (USD)", f"{((to_float(st.session_state.edit_hot) * LABOR_RATE) + mat_sum_val):,.2f}")
    st.divider()
    i1, i2, i3, i4 = st.columns(4)
    i1.number_input("Capacity", min_value=96, step=96, value=st.session_state.edit_cap, key="cap_widget",
                    on_change=update_edit_capacity)
    i2.text_input("Operation Time (h)", value=st.session_state.edit_opt, key="opt_widget", on_change=sync_edit_opt)
    i3.text_input("Hands on Time (h)", value=st.session_state.edit_hot, key="hot_widget", on_change=sync_edit_hot)
    i4.metric("Labor Cost (USD)", f"{(to_float(st.session_state.edit_hot) * LABOR_RATE):,.2f}")

st.markdown("#### 📦 Bill of Materials")
with st.container(border=True):
    mc1, mc2, mc3, mc4, mc5, mc6 = st.columns([0.26, 0.1, 0.1, 0.18, 0.21, 0.15], vertical_alignment="bottom")
    f_m_n = mc1.text_input("Material Name", key="f_m_n")
    f_m_q = mc2.number_input("Qty", min_value=0.0, value=1.0, key="f_m_q")
    f_m_u = mc3.selectbox("Unit", options=UNIT_OPTIONS, key="f_m_u")
    f_m_p = mc4.number_input("Unit Price (USD)", format="%.4f", key="f_m_p_input")
    with mc5:
        with st.popover("🔢 Price Calc", width='stretch'):
            p_total, p_pk, p_qp = st.number_input("Total ($)", min_value=0.0), st.number_input("Packs", min_value=1,
                                                                                               value=1), st.number_input(
                "Qty/Pk", min_value=1, value=1)
            if p_pk > 0 and p_qp > 0:
                calc_v = p_total / (p_pk * p_qp)
                st.info(f"Calc: ${calc_v:.4f}")
                st.button("Apply", on_click=apply_calc_to_edit_callback, args=(calc_v,))
    mc6.button("Add Item", width='stretch', on_click=add_edit_material_callback)

updated_mat_df = st.data_editor(m_df.reindex(
    columns=["Material Name", "Quantity", "Unit", "Unit Price", "Total Price"]) if not m_df.empty else pd.DataFrame(
    columns=["Material Name", "Quantity", "Unit", "Unit Price", "Total Price"]), num_rows="dynamic", width='stretch',
                                key="mat_edit", column_config={
        "Unit Price": st.column_config.NumberColumn("Price (USD/Unit)", format="%.4f"),
        "Total Price": st.column_config.NumberColumn("Total Price (USD)", disabled=True, format="%.2f")})
st.session_state.edit_mat_list = updated_mat_df.to_dict('records')

st.divider()
with st.container(border=True):
    st.markdown("#### 🔐 Authorize & Save")
    c_save1, c_save2 = st.columns([0.8, 0.2], vertical_alignment="bottom")
    final_auth = c_save1.text_input("Enter Access Code to Save Changes", type="password", key="final_save_auth")
    if c_save2.button("💾 Save to DB", type="primary", width='stretch'):
        raw_saved_pw = r_data.get('access_code', r_data.get('Access_Code', ''))

        # Robust parsing of passwords to prevent truncating on periods
        raw_pw_str = str(raw_saved_pw).strip() if not pd.isna(raw_saved_pw) else "None"
        saved_pw = raw_pw_str[:-2] if raw_pw_str.endswith('.0') else raw_pw_str

        if am.is_edit_authorized(final_auth, saved_pw):
            with st.spinner("Syncing..."):
                try:
                    latest_db = get_db_sheet_data(source_worksheet)
                    h, o = to_float(st.session_state.edit_hot), to_float(st.session_state.edit_opt)
                    m_cost = calc_mat_total(pd.DataFrame(st.session_state.edit_mat_list))

                    updated_dict = r_data.copy()
                    # Unified standard column names
                    updated_dict.update({
                        'RAM_ID': final_id, 'Base_Root': new_pre, 'RAM_Name': new_name,
                        'Process_Action': str(list(st.session_state.edit_acts)),
                        'Robot': str([assets["robot"][0][n] for n in new_rbts]),
                        'Functional_Device': str([assets["device"][0][n] for n in new_dvcs]),
                        'Purpose': new_purp, 'Sample_Capacity': st.session_state.edit_cap,
                        'Operation_Time(h)': o, 'Hands_on_Time(h)': h, 'Total_Time(h)': o + h,
                        'Labor_cost(USD)': h * LABOR_RATE, 'Total_Material_Cost(USD)': m_cost,
                        'Total_RAM_Cost(USD)': (h * LABOR_RATE) + m_cost,
                        'io_data': json.dumps(st.session_state.edit_io_list),
                        'material_data': json.dumps(st.session_state.edit_mat_list)
                    })

                    latest_db = latest_db[latest_db['RAM_ID'] != target_id]
                    # Avoid pd.concat FutureWarning
                    final_save_df = pd.concat([latest_db, pd.DataFrame([updated_dict])],
                                              ignore_index=True) if not latest_db.empty else pd.DataFrame(
                        [updated_dict])
                    final_save_df = sort_ram_db(final_save_df)

                    conn.update(spreadsheet=MY_SHEET_URL, worksheet=source_worksheet, data=final_save_df)
                    get_db_sheet_data.clear()
                    st.session_state.db_needs_refresh = True
                    st.success("Successfully updated!")
                    time.sleep(0.5)
                    st.session_state.edit_target = None
                    st.switch_page("pages/RAM Database.py")
                except Exception as e:
                    st.error(f"Save failed: {e}")
        else:
            st.error("❌ Access Code Denied.")
