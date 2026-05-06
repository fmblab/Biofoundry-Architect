import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import ast
import json
import math
import plotly.express as px
from datetime import datetime
import time
import re
import io
import Auth_manage as am

# [Standard Compliance] 2026 Syntax
pd.set_option('future.no_silent_downcasting', True)

# --- Constants ---
MY_SHEET_URL = st.secrets["connections"]["gsheets"]["spreadsheet"]
MASTER_CODE = st.secrets["MASTER_CODE"]
LABOR_RATE = 37.5
UNIT_OPTIONS = ["rxn", "ea", "uL", "mL"]
VESSEL_CLASS_OPTIONS = ["Microplate", "Tube", "Trough", "Agar plate", "Digital data"]
SUBSTANCE_CLASSES = ["DNA", "Reaction Mix", "Buffer", "Solvent", "Liquid Medium", "Cells", "Analyte / Sample",
                     "Generic", "Data"]

conn = st.connection("gsheets", type=GSheetsConnection)

# --- UI Styling ---
st.markdown("""
<style>
    div[data-testid="column"] button p { font-size: 12px !important; font-weight: 600 !important; }
    @media (min-width: 992px) {
        div[data-testid="stColumn"]:nth-of-type(1) > div:nth-child(1) {
            position: sticky;
            top: 2.5rem;
            z-index: 99;
        }
    }
    [data-testid="stHorizontalBlock"] { align-items: flex-start !important; }
</style>
""", unsafe_allow_html=True)

st.markdown("<div id='top-anchor'></div>", unsafe_allow_html=True)

back_to_top_html = """
<div style="text-align: center; margin-top: 50px; margin-bottom: 30px;">
    <a href="#top-anchor" target="_self" style="display: inline-block; padding: 10px 20px; background-color: #F1F5F9; color: #3B82F6; border-radius: 8px; text-decoration: none; font-weight: 600; font-size: 14px; border: 1px solid #E2E8F0;">
        ⬆️ Back to Top
    </a>
</div>
"""


# ==========================================
# 1. Utilities & [CORE] DB Loaders
# ==========================================

def to_float(val):
    """[CRITICAL FIX] Clean formatting to prevent NaN"""
    try:
        if val is None or str(val).strip() in ["", "nan", "NaN", "None"]:
            return 0.0
        return float(str(val).replace(',', '').strip())
    except:
        return 0.0


def safe_eval_list(val):
    """Safely parse list-like or JSON strings into python objects"""
    # [CORE FIX]: If val is already a list or dict, bypass pd.isna() to prevent ValueError
    if isinstance(val, (list, dict)):
        return val

    if val is None:
        return []

    # Safely handle float NaN values
    if isinstance(val, float) and math.isnan(val):
        return []

    # Perform pandas null check only on single scalar values to prevent ambiguous truth value errors
    try:
        if pd.isna(val):
            return []
    except ValueError:
        return []

    val_str = str(val).strip()
    if val_str in ["", "[]", "nan", "NaN", "None"]:
        return []

    try:
        # Standardize single quotes to double quotes for valid JSON parsing
        return json.loads(val_str.replace("'", '"'))
    except:
        try:
            return ast.literal_eval(val_str)
        except:
            return []

def normalize_io_keys(io_list):
    normalized = []
    for item in io_list:
        if not isinstance(item, dict):
            continue

        if "Substance Class" in item and "Classification" not in item:
            item["Classification"] = item.pop("Substance Class")

        normalized.append(item)

    return normalized

def ram_natural_sort_key(id_series):
    """Generates a natural sorting key for RAM IDs (e.g., A-002 before A-010)"""
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


def generate_next_derivative_id(base_id):
    """
    [Rule] Increments the main ID number (e.g., B-004 -> B-005).
    Searches the entire database for the highest number in the same prefix group.
    """
    try:
        # Extract prefix (e.g., 'B' from 'B-004')
        prefix = str(base_id).split('-')[0]
        existing_ids = full_db['RAM_ID'].astype(str).tolist()

        nums = []
        pattern = re.compile(rf"^{re.escape(prefix)}-(\d+)")

        for rid in existing_ids:
            match = pattern.match(rid)
            if match:
                nums.append(int(match.group(1)))

        if not nums:
            return f"{prefix}-001"
        else:
            next_num = max(nums) + 1
            return f"{prefix}-{next_num:03d}"
    except:
        return f"{base_id}-NEW"


def refresh_ram_metadata(ram_dict):
    """Restores io_data from string to objects and generates UI labels/meta"""

    # 1. Restore io_data
    io_list = safe_eval_list(ram_dict.get('io_data', '[]'))

    # [FIX 1] Normalize key names: "Substance Class" -> "Classification"
    normalized_io = []
    for item in io_list:
        if not isinstance(item, dict):
            continue

        if "Substance Class" in item and "Classification" not in item:
            item["Classification"] = item.pop("Substance Class")

        normalized_io.append(item)

    io_list = normalized_io
    ram_dict['io_data'] = io_list

    # 2. Restore material_data (no issue here)
    mat_list = safe_eval_list(ram_dict.get('material_data', '[]'))
    ram_dict['material_data'] = mat_list

    # --- Internal Helpers ---
    def get_essentials(io_type):
        if not isinstance(io_list, list):
            return []
        return [
            d for d in io_list
            if isinstance(d, dict)
            and str(d.get('Type', '')).lower() == io_type.lower()
            and (d.get('Essential') is True or str(d.get('Essential')).lower() == 'true')
        ]

    def make_label(essentials):
        labels = []
        for d in essentials:
            substance = d.get('Substance', 'Unknown')
            classification = d.get('Classification', 'Generic')
            vessel = d.get('Vessel', 'None')

            labels.append(
                f"{substance}:**({str(classification).replace('Universal', 'Generic')})** in `{vessel}`"
            )

        return ", ".join(labels) if labels else "None"

    def make_match_meta(essentials):
        return [
            {
                "class": str(d.get('Classification', '')).strip().replace('Universal', 'Generic'),
                "vessel": str(d.get('Vessel') or "").strip(),
                "vessel_class": str(d.get('Vessel Class') or "").strip()
            }
            for d in essentials
        ]

    # 3. Extract essentials
    input_essentials = get_essentials('input')
    output_essentials = get_essentials('output')

    # 4. Bind metadata
    ram_dict.update({
        'input_display': make_label(input_essentials),
        'output_display': make_label(output_essentials),
        'input_meta': make_match_meta(input_essentials),
        'output_meta': make_match_meta(output_essentials)
    })

    return ram_dict


@st.cache_data(ttl=600)
def load_vessel_options():
    """Fetches unique vessel names across Master and User vessel sheets"""
    v_pool = []
    for ws in ["Master_Vessels", "User_Vessels"]:
        try:
            df = conn.read(spreadsheet=MY_SHEET_URL, worksheet=ws, ttl=0)
            if df is not None and not df.empty:
                df.columns = df.columns.str.strip()
                col = next((c for c in df.columns if c.lower().replace("_", " ") == "vessel name"), None)
                if col:
                    v_pool.extend([str(v).strip() for v in df[col].dropna().unique().tolist() if v])
        except:
            continue
    return sorted(list(set(v_pool))) + ["None"] if v_pool else ["96 PCR plate", "96 Deep-well plate", "1.5mL Tube", "Trough", "None"]


@st.cache_data(ttl=3600)
def load_combined_db():
    """Loads RAM databases and ensures io_data is strictly treated as a parseable JSON string"""
    try:
        m_db = conn.read(spreadsheet=MY_SHEET_URL, worksheet="RAM_MasterDB", ttl="1h")
        u_db = conn.read(spreadsheet=MY_SHEET_URL, worksheet="RAM_UserDB", ttl="1h")

        combined = pd.concat(
            [m_db if m_db is not None else pd.DataFrame(), u_db if u_db is not None else pd.DataFrame()],
            ignore_index=True)

        # [CRITICAL FIX] Force io_data and material_data to be identical in handling
        # Replace NaN or empty strings with "[]" to ensure safe_eval_list works perfectly
        for col in ['io_data', 'material_data']:
            if col in combined.columns:
                combined[col] = combined[col].apply(
                    lambda x: '[]' if pd.isna(x) or str(x).strip() == "" else x
                )
            else:
                # If column is missing in sheet, create it as empty list string
                combined[col] = '[]'

        # Standard cleaning for other columns
        other_cols = [c for c in combined.columns if c not in ['io_data', 'material_data']]
        combined[other_cols] = combined[other_cols].fillna("")

        # Numeric conversion for existing cost/time columns
        num_cols = ['Total_RAM_Cost(USD)', 'Total_Time(h)', 'Operation_Time(h)',
                    'Hands_on_Time(h)', 'Labor_cost(USD)', 'Total_Material_Cost(USD)', 'Sample_Capacity']
        for col in num_cols:
            if col in combined.columns:
                combined[col] = combined[col].apply(to_float)

        # Reconstruct RAM objects with metadata enrichment
        updated = [refresh_ram_metadata(row.to_dict()) for _, row in combined.iterrows()]
        df = pd.DataFrame(updated)

        df['RAM_ID'] = df['RAM_ID'].astype(str)
        df['display'] = df['RAM_ID'] + " - " + df.get('RAM_Name', 'Unnamed')

        return df.sort_values(by='RAM_ID', key=ram_natural_sort_key).reset_index(drop=True)
    except Exception as e:
        st.error(f"DB Load Failure: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def load_workflow_db():
    """Loads and merges Master and User workflows"""
    try:
        m_db = conn.read(spreadsheet=MY_SHEET_URL, worksheet="Workflow_MasterDB", ttl="1h")
        u_db = conn.read(spreadsheet=MY_SHEET_URL, worksheet="Workflow_UserDB", ttl="1h")
        if m_db is not None: m_db['DB_Source'] = 'MasterDB'
        if u_db is not None: u_db['DB_Source'] = 'UserDB'
        return pd.concat([m_db, u_db], ignore_index=True).dropna(subset=['Workflow_Name'])
    except:
        return pd.DataFrame()


@st.cache_data(ttl=300)
def load_auth_df():
    """Loads the registered access codes and quotas from Google Sheet"""
    try:
        df = conn.read(spreadsheet=MY_SHEET_URL, worksheet="Access_codelist", ttl=0)
        return df
    except:
        return pd.DataFrame(columns=['access_code', 'Max_Workflows', 'Max_RAMs'])


def force_refresh():
    """Clears all cached functions and resets data synchronization flags"""
    load_combined_db.clear()
    load_workflow_db.clear()
    load_vessel_options.clear()
    load_auth_df.clear()  # [ADDED] Clear auth list cache during force refresh
    st.session_state.db_needs_refresh = False
    st.toast("🔄 Database caches cleared. Re-syncing...")


# --- Execute Proactive Cache Sync ---
if st.session_state.get('db_needs_refresh', False):
    force_refresh()

# --- Initialize Global Databases ---
full_db = load_combined_db()
df_wf = load_workflow_db()
VESSEL_NAME_OPTIONS = load_vessel_options()
auth_df = load_auth_df()

# --- Session State Management ---
if 'workflow' not in st.session_state: st.session_state.workflow = []
if 'wf_name' not in st.session_state: st.session_state.wf_name = f"WF_{datetime.now().strftime('%m%d_%H%M')}"
if 'wf_author' not in st.session_state: st.session_state.wf_author = "Researcher"
if 'wf_desc' not in st.session_state: st.session_state.wf_desc = ""
if 'wf_output' not in st.session_state: st.session_state.wf_output = ""
if 'wf_throughput' not in st.session_state: st.session_state.wf_throughput = 96
if 'edit_index' not in st.session_state: st.session_state.edit_index = None
if 'f_m_p_input' not in st.session_state: st.session_state.f_m_p_input = 0.0
if 'save_success_flag' not in st.session_state: st.session_state.save_success_flag = False

# [FIX] Reconstructing session state from Database Load (Important for Source_RAM logic)
if 'edit_workflow_target' in st.session_state:
    target = st.session_state['edit_workflow_target']
    st.session_state.wf_name = target.get('Workflow_Name', st.session_state.wf_name)
    st.session_state.wf_author = target.get('Author', st.session_state.wf_author)
    st.session_state.wf_desc = target.get('Description', "")
    st.session_state.wf_output = target.get('Output_Summary', "")
    st.session_state.wf_throughput = int(target.get('Number_of_Samples(Throughput)', 96))
    try:
        reconstructed, steps = [], safe_eval_list(target.get('Steps_RAMList', '[]'))
        for s in steps:
            match = full_db[full_db['RAM_ID'] == s.get('id')]
            if not match.empty:
                ram_dict = match.iloc[0].to_dict()
                # Override information (individual step configurations stored in DB)
                if 'op_time' in s: ram_dict['Operation_Time(h)'] = s['op_time']
                if 'ho_time' in s: ram_dict['Hands_on_Time(h)'] = s['ho_time']
                if 'mat_cost' in s: ram_dict['Total_Material_Cost(USD)'] = s['mat_cost']
                if 'io_data' in s: ram_dict['io_data'] = safe_eval_list(s['io_data'])  # Parse back as native list!
                if 'material_data' in s: ram_dict['material_data'] = safe_eval_list(
                    s['material_data'])  # Parse back as native list!

                reconstructed.append(refresh_ram_metadata(ram_dict))
        st.session_state.workflow = reconstructed
    except:
        pass
    del st.session_state['edit_workflow_target']


# ==========================================
# 2. Dialog: Inline RAM Editor
# ==========================================

def apply_calc_to_wf_edit(val):
    """Callback to apply calculated unit price directly to material price input"""
    st.session_state.f_m_p_input = val


def add_wf_material_item_callback(index):
    """Callback to append a newly defined material item to the temporary list"""
    n_key, q_key, u_key = f"f_m_n_{index}", f"f_m_q_{index}", f"f_m_u_{index}"
    mat_key = f"temp_mat_{index}"
    if st.session_state.get(n_key):
        st.session_state[mat_key].append({
            "Material Name": st.session_state[n_key],
            "Quantity": st.session_state[q_key],
            "Unit": st.session_state[u_key],
            "Unit Price": st.session_state.f_m_p_input,
            "Total Price": round(st.session_state[q_key] * st.session_state.f_m_p_input, 4)
        })
        st.session_state.f_m_p_input = 0.0
        st.session_state[n_key] = ""


@st.dialog("🛠️ Edit RAM Information", width="large")
def edit_ram_dialog(index):
    # [HACK] Hide default dialog close button to control save/close behavior
    st.markdown("""
        <style>
            button[aria-label="Close"] { display: none !important; }
        </style>
    """, unsafe_allow_html=True)

    ram = st.session_state.workflow[index]
    ram_id = ram.get('RAM_ID', 'Unknown')
    st.markdown(f"### Editing Step {index + 1}: {ram_id}")

    io_key, mat_key, tracking_key = f"temp_io_{index}", f"temp_mat_{index}", f"loaded_id_{index}"

    # Initialize or sync temporary state when RAM changes
    if (io_key not in st.session_state or st.session_state.get(tracking_key) != ram_id):
        st.session_state[io_key] = safe_eval_list(ram.get('io_data', '[]'))
        st.session_state[mat_key] = safe_eval_list(ram.get('material_data', '[]'))
        st.session_state[tracking_key] = ram_id

    col1, col2 = st.columns(2)
    e_name = col1.text_input("RAM Name", value=ram.get('RAM_Name', ''), key=f"nm_{index}")
    e_purpose = col2.text_input("Purpose", value=ram.get('Purpose', ''), key=f"pp_{index}")

    st.divider()
    st.markdown("#### 🧪 Substance I/O Management")
    aio1, aio2, aio3, aio4, aio5, aio6, aio7 = st.columns([0.6, 1.1, 1.1, 1.2, 1.1, 0.4, 0.3])
    f_t = aio1.selectbox("Type", ["Input", "Output"], key=f"et_{index}")
    f_s = aio2.text_input("Substance", key=f"es_{index}")
    f_c = aio3.selectbox("Substance Class", SUBSTANCE_CLASSES, key=f"ec_{index}")
    f_v = aio4.selectbox("Vessel", VESSEL_NAME_OPTIONS, key=f"ev_{index}")
    f_vc = aio5.selectbox("Vessel Class", VESSEL_CLASS_OPTIONS, key=f"evc_{index}")
    aio6.markdown("<div style='margin-top: 25px;'></div>", unsafe_allow_html=True)
    f_e = aio6.checkbox("Ess.", value=True, key=f"ee_{index}")

    if aio7.button("➕", key=f"add_io_{index}"):
        if f_s:
            st.session_state[io_key].append(
                {"Type": f_t, "Substance": f_s, "Classification": f_c, "Vessel": f_v, "Vessel Class": f_vc,
                 "Essential": f_e})
            st.rerun()

    # [FIX 1] Normalize before DataFrame conversion
    normalized_io = []
    for item in st.session_state[io_key]:
        if not isinstance(item, dict):
            continue

        if "Substance Class" in item and "Classification" not in item:
            item["Classification"] = item.pop("Substance Class")

        normalized_io.append(item)

    io_df = pd.DataFrame(normalized_io)

    # [FIX 2] Enforce schema
    column_order = ["Type", "Substance", "Classification", "Vessel", "Vessel Class", "Essential"]

    for col in column_order:
        if col not in io_df.columns:
            io_df[col] = None

    io_df = io_df[column_order]

    # [FIX 3] Data editor
    e_io_df = st.data_editor(
        io_df,
        width='stretch',
        num_rows="dynamic",
        key=f"io_table_{index}",
        column_config={
            "Essential": st.column_config.CheckboxColumn("Ess. ✅"),
            "Vessel": st.column_config.SelectboxColumn("Vessel", options=VESSEL_NAME_OPTIONS)
        }
    )

    # [FIX 4] Normalize again after editing (very important)
    updated_io = e_io_df.to_dict('records')

    final_io = []
    for item in updated_io:
        if not isinstance(item, dict):
            continue

        if "Substance Class" in item and "Classification" not in item:
            item["Classification"] = item.pop("Substance Class")

        final_io.append(item)

    st.session_state[io_key] = final_io
    st.divider()
    st.markdown("#### 📦 Bill of Materials (BOM)")
    with st.container(border=True):
        mc1, mc2, mc3, mc4, mc5, mc6 = st.columns([0.26, 0.1, 0.1, 0.18, 0.21, 0.15], vertical_alignment="bottom")
        f_m_n = mc1.text_input("Material Name", placeholder="PCR Kit", key=f"f_m_n_{index}")
        f_m_q = mc2.number_input("Qty", min_value=0.0, value=1.0, key=f"f_m_q_{index}")
        f_m_u = mc3.selectbox("Unit", options=UNIT_OPTIONS, key=f"f_m_u_{index}")
        f_m_p = mc4.number_input("Unit Price (USD)", format="%.4f", key="f_m_p_input")
        with mc5:
            with st.popover("🔢 Price Calc", width='stretch'):
                p_tot = st.number_input("Total Price (USD)", min_value=0.0, step=0.01, key=f"p_tot_{index}")
                p_pk = st.number_input("Packs", min_value=1, value=1, key=f"p_pk_{index}")
                p_qp = st.number_input("Qty/Pack", min_value=1, value=1, key=f"p_qp_{index}")
                calc_val = p_tot / (p_pk * p_qp) if (p_pk * p_qp) > 0 else 0.0
                st.info(f"Calc: **{calc_val:,.4f} USD**")
                st.button("Apply", on_click=apply_calc_to_wf_edit, args=(calc_val,), key=f"app_btn_{index}",
                          width='stretch')
        if mc6.button("Add Item", key=f"add_m_btn_{index}", on_click=add_wf_material_item_callback,
                      args=(index,)): st.rerun()

    e_mat_df = st.data_editor(pd.DataFrame(st.session_state[mat_key]), width='stretch', num_rows="dynamic",
                              key=f"mat_table_{index}")
    st.session_state[mat_key] = e_mat_df.to_dict('records')

    st.divider()
    ec1, ec2, ec3 = st.columns(3)
    e_cap = ec1.number_input("Capacity", value=int(ram.get('Sample_Capacity', 96)), step=96, key=f"cap_edit_{index}")
    # [RESTORED] Retained text_input design pattern as requested
    e_opt = ec2.text_input("Operation Time (h)", value=str(ram.get('Operation_Time(h)', 0.0)), key=f"opt_edit_{index}")
    e_hot = ec3.text_input("Hands-on Time (h)", value=str(ram.get('Hands_on_Time(h)', 0.0)), key=f"hot_edit_{index}")

    st.markdown("#### 💾 Save Options")
    is_vcm_target = ram_id.upper().replace("-", "").startswith(('Z', 'AA'))

    # Save Option A: Session state ONLY (No write commands to cloud DB)
    if st.button("✨ Apply to Session Only", width='stretch', type="secondary"):
        mat_sum = sum(to_float(m.get('Total Price', 0)) for m in st.session_state[mat_key])
        updated = ram.copy()
        updated.update({
            'RAM_Name': e_name,
            'Purpose': e_purpose,
            'io_data': st.session_state[io_key],  # Keep as native list in state!
            'material_data': st.session_state[mat_key],  # Keep as native list in state!
            'Sample_Capacity': e_cap,
            'Operation_Time(h)': to_float(e_opt),
            'Hands_on_Time(h)': to_float(e_hot),
            'Total_Material_Cost(USD)': mat_sum,
            'Total_RAM_Cost(USD)': mat_sum + (to_float(e_hot) * LABOR_RATE)
        })
        st.session_state.workflow[index] = refresh_ram_metadata(updated)
        st.session_state.edit_index = None
        st.toast("✅ Applied to session!")
        time.sleep(0.3)
        st.rerun()

    # Save Option B: Cloud Database Overwrite or Derivative Insertion (Only for physical RAMs)
    if not is_vcm_target:
        e_code = st.text_input("Access Code (Database Update)", type="password", key=f"auth_edit_{index}")
        cs1, cs2, cs3 = st.columns(3)

        # Define strict database schema to strip away temporary metadata columns
        official_columns = [
            'RAM_ID', 'RAM_Name', 'Process_Action', 'Robot', 'Functional_Device', 'Purpose',
            'Operation_Time(h)', 'Hands_on_Time(h)', 'Sample_Capacity', 'Total_RAM_Cost(USD)',
            'access_code', 'io_data', 'material_data', 'Base_Root', 'Labor_cost(USD)',
            'Total_Time(h)', 'Total_Material_Cost(USD)'
        ]

        if cs1.button("💾 Overwrite Original", width='stretch', type="primary"):
            # Normalize and securely read stored password to avoid dot-truncation bugs (e.g. 'test.1234')
            raw_saved_pw = ram.get('access_code', ram.get('Access_Code', ''))
            raw_pw_str = str(raw_saved_pw).strip() if not pd.isna(raw_saved_pw) else "None"
            saved_pw = raw_pw_str[:-2] if raw_pw_str.endswith('.0') else raw_pw_str

            if am.is_edit_authorized(e_code, saved_pw):
                mat_sum = sum(to_float(m.get('Total Price', 0)) for m in st.session_state[mat_key])
                updated = ram.copy()

                # Standardize access code columns
                if 'Access_Code' in updated:
                    updated['access_code'] = updated.pop('Access_Code')
                if 'access_code' not in updated:
                    updated['access_code'] = e_code

                # Keep state variables as clean native lists inside memory to prevent double-stringification
                updated.update({
                    'RAM_Name': e_name,
                    'Purpose': e_purpose,
                    'io_data': st.session_state[io_key],
                    'material_data': st.session_state[mat_key],
                    'Sample_Capacity': e_cap,
                    'Operation_Time(h)': to_float(e_opt),
                    'Hands_on_Time(h)': to_float(e_hot),
                    'Total_Material_Cost(USD)': mat_sum,
                    'Total_RAM_Cost(USD)': mat_sum + (to_float(e_hot) * LABOR_RATE)
                })

                # Filter and serialize strictly for GSheet connection to block double-escaping
                clean_row = {k: v for k, v in updated.items() if k in official_columns}
                clean_io = normalize_io_keys(st.session_state[io_key])
                clean_row['io_data'] = json.dumps(clean_io)
                clean_row['material_data'] = json.dumps(st.session_state[mat_key])

                db_ws = "RAM_MasterDB" if e_code == MASTER_CODE else "RAM_UserDB"
                db = conn.read(spreadsheet=MY_SHEET_URL, worksheet=db_ws, ttl=0)

                # Exclude target row and append clean row safely
                db = db[db['RAM_ID'] != ram['RAM_ID']]
                db = pd.concat([db, pd.DataFrame([clean_row])], ignore_index=True)

                # Enforce natural sorting sequence natively
                db = db.sort_values(by='RAM_ID', key=ram_natural_sort_key).reset_index(drop=True)

                conn.update(spreadsheet=MY_SHEET_URL, worksheet=db_ws, data=db)

                # [API OPTIMIZATION] Invalidate RAM DB cache on save to keep data perfectly in sync
                load_combined_db.clear()

                st.session_state.workflow[index] = refresh_ram_metadata(updated)
                st.session_state.edit_index = None
                st.success("Successfully updated original RAM!")
                time.sleep(0.5)
                st.rerun()
            else:
                st.error("❌ Access Code Denied.")

        if cs2.button("🌿 Save as New", width='stretch'):
            if e_code is not None:
                # [SECURITY & QUOTA CHECK] Validate access code and quota via am module
                # full_db: existing registered RAMs, e_code: input password, auth_df: authorization ledger
                can_save, auth_msg = am.check_registration_quota(full_db, e_code, auth_df)

                if not can_save:
                    st.error(f"❌ {auth_msg}")
                else:
                    new_id = generate_next_derivative_id(ram['RAM_ID'])
                    mat_sum = sum(to_float(m.get('Total Price', 0)) for m in st.session_state[mat_key])
                    new_ram = ram.copy()

                    # Keep state variables as clean native lists inside memory to prevent double-stringification
                    new_ram.update({
                        'RAM_ID': new_id,
                        'RAM_Name': e_name,
                        'io_data': st.session_state[io_key],
                        'material_data': st.session_state[mat_key],
                        'Sample_Capacity': e_cap,
                        'Operation_Time(h)': to_float(e_opt),
                        'Hands_on_Time(h)': to_float(e_hot),
                        'access_code': e_code,
                        'Total_Material_Cost(USD)': mat_sum,
                        'Total_RAM_Cost(USD)': mat_sum + (to_float(e_hot) * LABOR_RATE)
                    })

                    # Filter and serialize strictly for GSheet connection to block double-escaping
                    clean_row = {k: v for k, v in new_ram.items() if k in official_columns}
                    clean_io = normalize_io_keys(st.session_state[io_key])
                    clean_row['io_data'] = json.dumps(clean_io)
                    clean_row['material_data'] = json.dumps(st.session_state[mat_key])

                    db_ws = "RAM_MasterDB" if e_code == MASTER_CODE else "RAM_UserDB"
                    db = conn.read(spreadsheet=MY_SHEET_URL, worksheet=db_ws, ttl=0)

                    # Concatenate and sort naturally
                    db = pd.concat([db, pd.DataFrame([clean_row])], ignore_index=True)
                    db = db.sort_values(by='RAM_ID', key=ram_natural_sort_key).reset_index(drop=True)

                    conn.update(spreadsheet=MY_SHEET_URL, worksheet=db_ws, data=db)

                    # [API OPTIMIZATION] Invalidate RAM DB cache on save to keep data perfectly in sync
                    load_combined_db.clear()

                    st.session_state.workflow[index] = refresh_ram_metadata(new_ram)
                    st.session_state.edit_index = None
                    st.success(f"Successfully saved as derivative: {new_id}! ({auth_msg})")
                    time.sleep(0.5)
                    st.rerun()
            else:
                st.error("❌ Access Code is required to create a new derivative.")

        if cs3.button("✖️ Close", width='stretch'):
            st.session_state.edit_index = None
            st.rerun()
    else:
        if st.button("✖️ Close", width='stretch'):
            st.session_state.edit_index = None
            st.rerun()


if st.session_state.get('edit_index') is not None:
    edit_ram_dialog(st.session_state.edit_index)

# ==========================================
# 3. Connectivity Engine
# ==========================================

def check_match_info(row, last_step_data):
    """
    Evaluates compatibility between consecutive RAM steps.
    Validates based on Substance Class, Vessel Format, and Data Exceptions.
    """
    if not last_step_data:
        return "🆕 Start", True, ""

    # Refresh metadata on shallow copies to prevent modifying session state references
    if 'output_meta' not in last_step_data or isinstance(last_step_data.get('output_meta'), str):
        last_step_data = refresh_ram_metadata(last_step_data.copy())
    if 'input_meta' not in row or isinstance(row.get('input_meta'), str):
        row = refresh_ram_metadata(row.copy())

    # Extract parsed metadata with robust safety fallbacks
    src_outputs = last_step_data.get('output_meta')
    if not isinstance(src_outputs, list):
        src_outputs = safe_eval_list(src_outputs)

    nxt_inputs = row.get('input_meta')
    if not isinstance(nxt_inputs, list):
        nxt_inputs = safe_eval_list(nxt_inputs)

    # Ensure elements are dictionaries to protect against schema discrepancies
    src_outputs = [o for o in src_outputs if isinstance(o, dict)]
    nxt_inputs = [i for i in nxt_inputs if isinstance(i, dict)]

    # 1. Data Exception
    # Informational continuity bypasses physical vessel checks.
    if any(o.get('class') == 'Data' for o in src_outputs):
        return "✅ Match (Data)", True, "Data Exception: Informational continuity granted."

    # 2. Direct class and vessel matching
    for o in src_outputs:
        o_class = str(o.get('class', 'Unknown')).replace('Universal', 'Generic')
        o_vessel = o.get('vessel')

        for i in nxt_inputs:
            i_class = str(i.get('class', 'Unknown')).replace('Universal', 'Generic')
            i_vessel = i.get('vessel')

            # Match substance class directly or through Generic wildcard.
            class_match = (
                o_class == i_class
                or o_class == 'Generic'
                or i_class == 'Generic'
            )

            # Vessel must match directly.
            vessel_match = (o_vessel == i_vessel)

            if class_match and vessel_match:
                return "✅ Match", True, ""

    # Generate a descriptive error message on mismatch using safe dictionary retrieval
    expected_class = src_outputs[0].get('class', 'Unknown') if src_outputs else "Unknown"
    expected_vessel = src_outputs[0].get('vessel', 'Unknown') if src_outputs else "Unknown"
    return "❌ Mismatch", False, f"Expected '{expected_class}' in '{expected_vessel}'."


# ==========================================
# 4. Sidebar: Management (API Optimized Version)
# ==========================================

# Initialize sidebar authentication states if not present
if 'sb_auth_code' not in st.session_state:
    st.session_state.sb_auth_code = ""
if 'sb_auth_verified' not in st.session_state:
    st.session_state.sb_auth_verified = False

# [IMPORTANT] Determine sequence validity beforehand to control the save button's enabled state
all_valid = True
if st.session_state.workflow:
    for i in range(len(st.session_state.workflow)):
        prev_step = st.session_state.workflow[i - 1] if i > 0 else None
        _, step_valid, _ = check_match_info(st.session_state.workflow[i], prev_step)
        if not step_valid:
            all_valid = False
            break

with st.sidebar:
    # --- [1] Import Workflow ---
    st.header("📂 Import Workflow")
    if not df_wf.empty:
        # Combine database source and workflow name for selection display label
        df_wf['Import_Label'] = "📁 [" + df_wf['DB_Source'] + "] " + df_wf['Workflow_Name']
        import_label = st.selectbox("Select to Load", ["-- Select --"] + df_wf['Import_Label'].tolist())

        if st.button("📥 Load Selected Workflow", width='stretch'):
            if import_label != "-- Select --":
                target = df_wf[df_wf['Import_Label'] == import_label].iloc[0].to_dict()
                st.session_state.wf_name = target.get('Workflow_Name', "")
                st.session_state.wf_author = target.get('Author', "")
                st.session_state.wf_desc = target.get('Description', "")
                st.session_state.wf_output = target.get('Output_Summary', "")
                st.session_state.wf_throughput = int(target.get('Number_of_Samples(Throughput)', 96))

                reconstructed = []
                steps = safe_eval_list(target.get('Steps_RAMList', '[]'))
                for s in steps:
                    match = full_db[full_db['RAM_ID'] == s.get('id')]
                    if not match.empty:
                        ram_dict = match.iloc[0].to_dict()

                        if s.get('io_data') and str(s.get('io_data')) != '[]':
                            ram_dict['io_data'] = safe_eval_list(s['io_data'])

                        if s.get('material_data') and str(s.get('material_data')) != '[]':
                            ram_dict['material_data'] = safe_eval_list(s['material_data'])

                        ram_dict = refresh_ram_metadata(ram_dict)
                        reconstructed.append(ram_dict)
                st.session_state.workflow = reconstructed
                st.rerun()

    st.divider()

    # --- [2] Workflow Settings ---
    st.header("⚙️ Workflow Settings")
    st.session_state.wf_name = st.text_input("Workflow Name", value=st.session_state.wf_name)
    st.session_state.wf_author = st.text_input("Researcher Name", value=st.session_state.wf_author)
    st.session_state.wf_desc = st.text_area("Description", value=st.session_state.wf_desc)
    st.session_state.wf_output = st.text_input("Output Summary", value=st.session_state.wf_output)

    # Throughput configuration (Enforces multiples of 96-well format)
    st.number_input("Throughput", min_value=96, step=96, value=st.session_state.wf_throughput, key="wf_tp_input")
    st.session_state.wf_throughput = (st.session_state.wf_tp_input // 96) * 96

    st.divider()

    # --- [3] Save to Database ---
    st.header("💾 Save to Database")

    if st.session_state.save_success_flag:
        st.success("🎉 Workflow Saved!")
        c_nav1, c_nav2 = st.columns(2)
        if c_nav1.button("📂 Go to DB", width='stretch'):
            st.session_state.save_success_flag = False
            st.switch_page("pages/Workflow Database.py")
        if c_nav2.button("🔄 Reset", width='stretch'):
            st.session_state.workflow = []
            st.session_state.save_success_flag = False
            st.rerun()
    else:
        with st.popover("📥 Save to WorkflowDB", width='stretch'):
            with st.form("save_auth_form"):
                code = st.text_input("Access Code", type="password")
                check_btn = st.form_submit_button("🔍 Check Name & Authority", width='stretch')

            # Stage 1: Auth check and cache entered verification credentials
            if check_btn:
                st.session_state.sb_auth_code = code
                st.session_state.sb_auth_verified = True

            # Stage 2: Render confirmation actions conditionally using persistent state
            if st.session_state.get('sb_auth_verified'):
                current_code = st.session_state.sb_auth_code
                target_ws = "Workflow_MasterDB" if current_code == MASTER_CODE else "Workflow_UserDB"
                try:
                    # [SECURITY & QUOTA CHECK] Validate access code and quota against Access_codelist sheet via am module
                    # df_wf: used to calculate current active workflow registrations under the user's code
                    # auth_df: global cache holding registered access codes and user-specific limits
                    can_save, auth_msg = am.check_registration_quota(df_wf, current_code, auth_df)

                    if not can_save:
                        st.error(f"❌ {auth_msg}")
                    else:
                        st.info(f"🔑 {auth_msg}")

                        # [API OPTIMIZATION] Read duplicates from local df_wf memory cache.
                        # This completely halts real-time connection query leaks while the popover remains open.
                        name_match = df_wf[
                            df_wf['Workflow_Name'] == st.session_state.wf_name] if not df_wf.empty else pd.DataFrame()

                        # Prepare computational data and aggregate parameters for saving
                        wf_df_tmp = pd.DataFrame(st.session_state.workflow)
                        for c in ['Operation_Time(h)', 'Hands_on_Time(h)', 'Total_Material_Cost(USD)']:
                            if c in wf_df_tmp.columns:
                                wf_df_tmp[c] = wf_df_tmp[c].apply(to_float)
                            else:
                                wf_df_tmp[c] = 0.0

                        tat = wf_df_tmp['Operation_Time(h)'].sum() + wf_df_tmp['Hands_on_Time(h)'].sum()
                        mat_c = wf_df_tmp['Total_Material_Cost(USD)'].sum()
                        lab_c = wf_df_tmp['Hands_on_Time(h)'].sum() * LABOR_RATE
                        tp = st.session_state.wf_throughput

                        new_row = {
                            "Workflow_Name": st.session_state.wf_name,
                            "Author": st.session_state.wf_author,
                            "Description": st.session_state.wf_desc,
                            "Output_Summary": st.session_state.wf_output,
                            "Number_of_Samples(Throughput)": tp,
                            "Steps_RAMList": json.dumps([{
                                "step": i + 1,
                                "id": s['RAM_ID'],
                                "name": s['RAM_Name'],
                                "op_time": to_float(s.get('Operation_Time(h)', 0)),
                                "ho_time": to_float(s.get('Hands_on_Time(h)', 0)),
                                "mat_cost": to_float(s.get('Total_Material_Cost(USD)', 0)),
                                "io_data": json.dumps(s.get('io_data', [])),
                                "material_data": json.dumps(s.get('material_data', [])),
                                "Robot": s.get('Robot', 'None'),
                                "Functional_Device": s.get('Functional_Device', 'None')
                            } for i, s in enumerate(st.session_state.workflow)]),
                            "Turnaround_Time(h)": tat,
                            "Operation_Time(h)": wf_df_tmp['Operation_Time(h)'].sum(),
                            "Hands_on_Time(h)": wf_df_tmp['Hands_on_Time(h)'].sum(),
                            "Material_Summary": json.dumps(
                                [{**m, "Source_RAM": s['RAM_ID']} for s in st.session_state.workflow for m in
                                 safe_eval_list(s.get('material_data', '[]'))]
                            ),
                            "Material_Cost(USD)": mat_c,
                            "Labor_Cost(USD)": lab_c,
                            "Total_Cost(USD)": mat_c + lab_c,
                            "EPI": round(math.sqrt(max(0.0, (tat / tp) * ((mat_c + lab_c) / tp))), 2) if tp > 0 else 0,
                            "access_code": current_code
                        }

                        # 3. Perform duplicate name checks and branch save procedures accordingly
                        if not name_match.empty:
                            raw_stored_code = name_match.iloc[0].get('access_code', '')
                            raw_pw_str = str(raw_stored_code).strip() if not pd.isna(raw_stored_code) else "None"
                            stored_code = raw_pw_str[:-2] if raw_pw_str.endswith('.0') else raw_pw_str

                            if current_code == stored_code or current_code == MASTER_CODE:
                                st.warning(f"⚠️ A workflow named '{st.session_state.wf_name}' already exists.")
                                if st.button("💾 Yes, Overwrite it", width='stretch', type="primary",
                                             disabled=not all_valid,
                                             key="btn_overwrite_wf"):
                                    # [API OPTIMIZATION] Execute live sheet query ONLY at the single instant the user commits saving
                                    db_snap = conn.read(spreadsheet=MY_SHEET_URL, worksheet=target_ws, ttl=0)
                                    final_db = pd.concat([db_snap[db_snap['Workflow_Name'] != st.session_state.wf_name],
                                                          pd.DataFrame([new_row])], ignore_index=True)
                                    conn.update(spreadsheet=MY_SHEET_URL, worksheet=target_ws, data=final_db)

                                    # Clear temporary authentication keys and trigger sync
                                    st.session_state.save_success_flag = True
                                    st.session_state.sb_auth_code = ""
                                    st.session_state.sb_auth_verified = False

                                    # [API OPTIMIZATION] Targeted Cache Clearing to prevent reloading whole databases
                                    load_workflow_db.clear()
                                    st.rerun()
                            else:
                                st.error("❌ Name conflict: Unauthorized to overwrite.")
                        else:
                            if st.button("🚀 Save as New Workflow", width='stretch', type="primary",
                                         disabled=not all_valid,
                                         key="btn_save_new_wf"):
                                # [API OPTIMIZATION] Execute live sheet query ONLY at the single instant the user commits saving
                                db_snap = conn.read(spreadsheet=MY_SHEET_URL, worksheet=target_ws, ttl=0)
                                final_db = pd.concat([db_snap, pd.DataFrame([new_row])], ignore_index=True)
                                conn.update(spreadsheet=MY_SHEET_URL, worksheet=target_ws, data=final_db)

                                # Clear temporary authentication keys and trigger sync
                                st.session_state.save_success_flag = True
                                st.session_state.sb_auth_code = ""
                                st.session_state.sb_auth_verified = False

                                # [API OPTIMIZATION] Targeted Cache Clearing to prevent reloading whole databases
                                load_workflow_db.clear()
                                st.rerun()

                except Exception as e:
                    st.error(f"Connection Error: {e}")

            # Render warnings when workflow compatibility checks fail (applies disabled=not all_valid)
            if not all_valid:
                st.caption(":red[⚠️ Resolve sequence mismatches to enable saving.]")

# ==========================================
# 5. Main UI: Tabs & Dashboard
# ==========================================

st.title("🔗 Workflow Builder")

# Connection rules explanation block
with st.expander("ℹ️ Connection Rules & Logical Bridges", expanded=False):
    st.markdown("""
    To ensure procedural validity, the builder validates connections using the following logic:
    * **Standard Rule**: Essential **Substance Class** and **Vessel Format** must match between RAMs.
    * **Vessel Change**: Resolve the mismatch by adjusting either the input vessel of the final RAM or the output vessel of the preceding RAM.
    * **Data Exception**: If a RAM outputs **'Data'**, physical matching is bypassed to support informational continuity.
    """)

# [CORE] Re-validate entire sequence validity (to control adding and saving buttons)
all_valid = True
if st.session_state.workflow:
    for i in range(len(st.session_state.workflow)):
        prev_step = st.session_state.workflow[i - 1] if i > 0 else None
        _, step_valid, _ = check_match_info(st.session_state.workflow[i], prev_step)
        if not step_valid:
            all_valid = False
            break

    # Calculate real-time indicators (TAT, Cost, EPI) securely
    live_tat = sum(to_float(r.get('Operation_Time(h)', 0)) + to_float(r.get('Hands_on_Time(h)', 0)) for r in
                   st.session_state.workflow)
    live_cost = sum(
        to_float(r.get('Total_Material_Cost(USD)', 0)) + (to_float(r.get('Hands_on_Time(h)', 0)) * LABOR_RATE) for r in
        st.session_state.workflow)
    live_tp = st.session_state.wf_throughput
    live_epi = math.sqrt(max(0.0, (live_tat / live_tp) * (live_cost / live_tp))) if live_tp > 0 else 0.0

    # Display real-time KPI metrics dashboard
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Steps", len(st.session_state.workflow))
    m2.metric("Turnaround Time (h)", f"{live_tat:.2f}")
    m3.metric("Total Cost (USD)", f"{live_cost:,.2f}")
    m4.metric("EPI (Experimental Price Index) (-)", f"{live_epi:.2f}")

st.divider()
t1, t2, t3 = st.tabs(["🛠️ Builder", "📊 Breakdown", "📦 Materials"])

with t1:
    c1, c2 = st.columns([1.1, 2.0])
    with c1:
        st.subheader("Current Process Status")
        if st.session_state.workflow:
            # 1. Extract data and map exact keys to match column_config formats
            sum_list = []
            for i, s in enumerate(st.session_state.workflow):
                op_t = to_float(s.get('Operation_Time(h)', 0))
                ho_t = to_float(s.get('Hands_on_Time(h)', 0))
                mat_c = to_float(s.get('Total_Material_Cost(USD)', 0))
                lab_c = ho_t * LABOR_RATE

                sum_list.append({
                    "Step": i + 1,
                    "RAM ID": str(s['RAM_ID']),
                    "RAM Name": str(s.get('RAM_Name', '')).replace('nan', ''),
                    "Op. Time(h)": op_t,
                    "HO. Time(h)": ho_t,
                    "Total Time(h)": op_t + ho_t,
                    "Mat. Cost(USD)": mat_c,
                    "Lab. Cost(USD)": lab_c,
                    "Total Cost(USD)": mat_c + lab_c
                })

            # 2. Create structured summary DataFrame
            status_df = pd.DataFrame(sum_list)

            # 3. Render dataframe with standard formats mapped to the correct columns
            st.dataframe(
                status_df,
                width='stretch',
                hide_index=True,
                height=350,
                column_config={
                    "Op. Time(h)": st.column_config.NumberColumn(format="%.2f"),
                    "HO. Time(h)": st.column_config.NumberColumn(format="%.2f"),
                    "Total Time(h)": st.column_config.NumberColumn(format="%.2f"),
                    "Mat. Cost(USD)": st.column_config.NumberColumn(format="%,.2f"),
                    "Lab. Cost(USD)": st.column_config.NumberColumn(format="%,.2f"),
                    "Total Cost(USD)": st.column_config.NumberColumn(format="%,.2f")
                }
            )

        # Select and add process steps dynamically (Bypassed if mismatches exist)
        st.subheader("Add Process Step")
        sc1, sc2, sc3 = st.columns([0.6, 0.2, 0.2], vertical_alignment="bottom")
        selected = sc1.selectbox("Select RAM", full_db['display'].tolist() if not full_db.empty else [])

        if sc2.button("➕ Add", width='stretch', key="add_btn_main", disabled=not all_valid):
            if selected:
                st.session_state.workflow.append(full_db[full_db['display'] == selected].iloc[0].to_dict())
                st.rerun()

        if sc3.button("🗑️ Reset", width='stretch', key="reset_btn_main"):
            st.session_state.workflow = []
            st.rerun()

        # Display sequence validation errors prominently
        if not all_valid:
            st.error("🚨 **Sequence Mismatch Detected:** Please resolve the mismatch before adding more steps.")

        # Recommendations engine (Suggests compatible successor RAM modules)
        if st.session_state.workflow:
            last_ram = st.session_state.workflow[-1]
            st.markdown(f"#### 💡 Recommendations (Matching with `{last_ram['RAM_ID']}`)")

            # [CRITICAL FIX] Add safety check for empty database and enforce string type casting
            if not full_db.empty:
                rec_db = full_db.copy()
                rec_db['Status'] = rec_db.apply(lambda r: check_match_info(r, last_ram)[0], axis=1).astype(str)

                # Filter safely using na=False parameter to handle any potential missing elements
                matched_rec = rec_db[rec_db['Status'].str.contains("✅", na=False)]
                st.dataframe(matched_rec[['Status', 'RAM_ID', 'RAM_Name']], width='stretch', hide_index=True)
            else:
                st.caption("No RAM modules available in the database for recommendation matching.")

    with c2:
        st.subheader("Current Sequence")
        for i, step in enumerate(st.session_state.workflow):
            st_txt, valid, err = check_match_info(step, st.session_state.workflow[i - 1]) if i > 0 else (
                "🆕 Start", True, "")
            with st.container(border=True):
                ca, cb = st.columns([0.8, 0.2], vertical_alignment="center")
                with ca:
                    # Color compatibility icons dynamically based on verification status
                    valid_icon = "✅" if valid else "🚨"
                    error_msg = f"| <span style='color:#ff4b4b;'>{err}</span>" if not valid else ""
                    st.markdown(f"**Step {i + 1}: {valid_icon} {step['RAM_ID']} - {step['RAM_Name']}** {error_msg}",
                                unsafe_allow_html=True)
                    st.caption(f"In: {step.get('input_display', 'None')} | Out: {step.get('output_display', 'None')}")
                    st.caption(
                        f"🤖 **Robot:** {step.get('Robot', 'None')} | 🛠️ **Device:** {step.get('Functional_Device', 'None')}")
                with cb:
                    bc = st.columns(4)
                    if bc[0].button("↑", key=f"u_{i}", width='stretch'):
                        if i > 0:
                            st.session_state.workflow[i], st.session_state.workflow[i - 1] = st.session_state.workflow[
                                i - 1], st.session_state.workflow[i]
                            st.rerun()
                    if bc[1].button("↓", key=f"d_{i}", width='stretch'):
                        if i < len(st.session_state.workflow) - 1:
                            st.session_state.workflow[i], st.session_state.workflow[i + 1] = st.session_state.workflow[
                                i + 1], st.session_state.workflow[i]
                            st.rerun()
                    if bc[2].button("📝", key=f"e_{i}", width='stretch'):
                        st.session_state.edit_index = i
                        st.rerun()
                    if bc[3].button("❌", key=f"x_{i}", width='stretch'):
                        st.session_state.workflow.pop(i)
                        st.rerun()

with t2:
    if st.session_state.workflow:
        st.subheader("📊 Breakdown Analysis")
        b_df = pd.DataFrame(st.session_state.workflow)
        b_df['Total_Time'] = b_df.apply(
            lambda r: to_float(r.get('Operation_Time(h)', 0)) + to_float(r.get('Hands_on_Time(h)', 0)), axis=1)
        b_df['Total_Cost'] = b_df.apply(lambda r: to_float(r.get('Total_Material_Cost(USD)', 0)) + (
                to_float(r.get('Hands_on_Time(h)', 0)) * LABOR_RATE), axis=1)
        tat_b, cost_b = b_df['Total_Time'].sum(), b_df['Total_Cost'].sum()

        st.markdown("#### 🚨 Bottleneck Identification")
        bc1, bc2 = st.columns(2)
        with bc1:
            t_bn = b_df.loc[b_df['Total_Time'].idxmax()]
            st.error(f"**Time Bottleneck**: {t_bn['RAM_ID']} ({t_bn['RAM_Name']})")
            st.caption(
                f"Occupies **{t_bn['Total_Time']:.2f} h** ({(t_bn['Total_Time'] / tat_b * 100 if tat_b > 0 else 0):.1f}% of TAT)")
        with bc2:
            c_bn = b_df.loc[b_df['Total_Cost'].idxmax()]
            st.warning(f"**Cost Bottleneck**: {c_bn['RAM_ID']} ({c_bn['RAM_Name']})")
            st.caption(
                f"Consumes **${c_bn['Total_Cost']:,.2f}** ({(c_bn['Total_Cost'] / cost_b * 100 if cost_b > 0 else 0):.1f}% of Total Cost)")

        at1, at2 = st.tabs(["⏱️ Time Distribution", "💰 Cost Distribution"])
        b_df['Chart_Label'] = [f"Step {i + 1}: {r['RAM_ID']}" for i, r in b_df.iterrows()]
        b_df['Full_Label'] = [f"Step {i + 1}: {r['RAM_ID']} ({r.get('RAM_Name', 'N/A')})" for i, r in b_df.iterrows()]

        with at1:
            col1, col2 = st.columns([1.5, 1])
            with col1:
                fig_t = px.pie(b_df[b_df['Total_Time'] > 0], values='Total_Time', names='Chart_Label', hole=0.5,
                               color_discrete_sequence=px.colors.qualitative.Pastel)
                fig_t.update_layout(showlegend=True, margin=dict(t=60, b=10, l=10, r=10), title="Time Distribution")

                # [UPDATE] Custom Hover Template with "h" unit & Keep Step Sequence
                fig_t.update_traces(
                    hovertemplate="<b>%{label}</b><br>Total Time = %{value:.2f} h<extra></extra>",
                    sort=False
                )

                st.plotly_chart(fig_t, width='stretch')
            with col2:
                for _, r in b_df.iterrows():
                    ratio = (r['Total_Time'] / tat_b) if tat_b > 0 else 0
                    st.write(f"**{r['Full_Label']}** ({r['Total_Time']:.2f}h, {ratio * 100:.1f}%)")
                    st.progress(max(0.0, min(float(ratio), 1.0)))
        with at2:
            col3, col4 = st.columns([1.5, 1])
            with col3:
                fig_c = px.pie(b_df[b_df['Total_Cost'] > 0], values='Total_Cost', names='Chart_Label', hole=0.5,
                               color_discrete_sequence=px.colors.qualitative.Set3)
                fig_c.update_layout(showlegend=True, margin=dict(t=60, b=10, l=10, r=10), title="Cost Distribution")

                # [UPDATE] Custom Hover Template with USD formatting & Keep Step Sequence
                fig_c.update_traces(
                    hovertemplate="<b>%{label}</b><br>Total Cost = %{value:,.3f} USD<extra></extra>",
                    sort=False
                )

                st.plotly_chart(fig_c, width='stretch')
            with col4:
                for _, r in b_df.iterrows():
                    ratio = (r['Total_Cost'] / cost_b) if cost_b > 0 else 0
                    st.write(f"**{r['Full_Label']}** (${r['Total_Cost']:.2f}, {ratio * 100:.1f}%)")
                    st.progress(max(0.0, min(float(ratio), 1.0)))

with t3:
    st.subheader("📦 Bill of Materials")
    if st.session_state.workflow:
        all_m = []
        for s in st.session_state.workflow:
            mats = safe_eval_list(s.get('material_data', '[]'))
            for m in mats:
                # Standardize material data labels
                nm = {
                    (nk := "Unit Price" if (
                                               kl := k.lower().strip()) == "unit price" else "Material Name" if kl == "material name" else "Total Price" if kl == "total price" else k):
                        (0.0 if (str(v).strip().lower() in ["none", "nan", ""] and "price" in nk.lower()) else v)
                    for k, v in m.items()
                }
                nm['Source_RAM'] = s['RAM_ID']
                all_m.append(nm)

        if all_m:
            df_b = pd.DataFrame(all_m)
            total_m_val = pd.to_numeric(df_b['Total Price'].astype(str).str.replace(',', ''), errors='coerce').sum()
            st.metric("Total Material Cost (USD)", f"{total_m_val:,.2f}")
            st.dataframe(df_b[['Source_RAM', 'Material Name', 'Quantity', 'Unit', 'Unit Price', 'Total Price']],
                         hide_index=True, width='stretch', height=1000)

st.markdown(back_to_top_html, unsafe_allow_html=True)