import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import json
import plotly.express as px
import ast
import math
import time
import re
import io
import Auth_manage as am

# [NOTICE] 2026 Standard Syntax Compliance
pd.set_option('future.no_silent_downcasting', True)

# --- Constants ---
MY_SHEET_URL = st.secrets["connections"]["gsheets"]["spreadsheet"]
MASTER_CODE = st.secrets["MASTER_CODE"]
LABOR_RATE = 37.5

conn = st.connection("gsheets", type=GSheetsConnection)

# --- UI Elements & Top Anchor ---
st.markdown("<div id='top-anchor'></div>", unsafe_allow_html=True)

back_to_top_html = """
<div style="text-align: center; margin-top: 50px; margin-bottom: 30px;">
    <a href="#top-anchor" target="_self" style="display: inline-block; padding: 10px 20px; background-color: #F1F5F9; color: #3B82F6; border-radius: 8px; text-decoration: none; font-weight: 600; font-size: 14px; border: 1px solid #E2E8F0;">
        ⬆️ Back to Top
    </a>
</div>
"""


# ==========================================
# 1. Utilities & Robust Data Loading
# ==========================================

def safe_eval_list(val):
    """Safely parse list-like or JSON strings into python objects"""
    if not val or pd.isna(val) or str(val).strip() in ["", "[]", "nan", "NaN", "None"]:
        return []
    if isinstance(val, (list, dict)):
        return val
    try:
        return json.loads(str(val).replace("'", '"'))
    except:
        try:
            return ast.literal_eval(str(val))
        except:
            return []


def to_float(val):
    """Clean and cast values safely to float to prevent NaN calculation errors"""
    try:
        if val is None or str(val).strip() in ["", "nan", "NaN", "None"]:
            return 0.0
        return float(str(val).replace(',', '').strip())
    except:
        return 0.0


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


def refresh_ram_metadata(ram_dict):
    """Enriches individual RAM dictionary with parsed I/O markup displays"""
    io_list = safe_eval_list(ram_dict.get('io_data', '[]'))

    def get_essentials(io_type):
        return [d for d in io_list if str(d.get('Type', '')).lower() == io_type.lower() and (
                d.get('Essential') is True or str(d.get('Essential')).lower() == 'true')]

    def make_label(essentials):
        labels = [
            f"{d.get('Substance', 'Unknown')}:**({str(d.get('Classification') or d.get('Substance Class') or 'Unknown').replace('Universal', 'Generic')})** in `{d.get('Vessel') or 'None'}`"
            for d in essentials]
        return ", ".join(labels) if labels else "None"

    in_ess, out_ess = get_essentials('input'), get_essentials('output')
    ram_dict.update({'input_display': make_label(in_ess), 'output_display': make_label(out_ess)})
    return ram_dict


@st.cache_data(ttl=300)
def load_workflow_db():
    """Loads and aggregates saved workflows from Master and User tabs securely"""
    try:
        m_db = conn.read(spreadsheet=MY_SHEET_URL, worksheet="Workflow_MasterDB", ttl=0)
        u_db = conn.read(spreadsheet=MY_SHEET_URL, worksheet="Workflow_UserDB", ttl=0)

        if m_db is not None and not m_db.empty:
            m_db['DB_Source'] = 'MasterDB'
        else:
            m_db = pd.DataFrame(columns=['Workflow_Name', 'DB_Source'])

        if u_db is not None and not u_db.empty:
            u_db['DB_Source'] = 'UserDB'
        else:
            u_db = pd.DataFrame(columns=['Workflow_Name', 'DB_Source'])

        combined = pd.concat([m_db, u_db], ignore_index=True).dropna(subset=['Workflow_Name'])
        combined.columns = combined.columns.str.strip()

        num_cols = ['Turnaround_Time(h)', 'Operation_Time(h)', 'Hands_on_Time(h)', 'Material_Cost(USD)',
                    'Labor_Cost(USD)', 'EPI', 'Number_of_Samples(Throughput)']
        for col in num_cols:
            if col in combined.columns:
                combined[col] = combined[col].apply(to_float)

        return combined
    except Exception as e:
        st.error(f"Error loading workflow database: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=300)
def load_ram_reference_full():
    """Loads all Master/User RAM specifications with unified data clearing"""
    try:
        # 1. Load spreadsheet data
        m_ram = conn.read(spreadsheet=MY_SHEET_URL, worksheet="RAM_MasterDB", ttl=0)
        u_ram = conn.read(spreadsheet=MY_SHEET_URL, worksheet="RAM_UserDB", ttl=0)

        # 2. Merge DataFrames
        combined = pd.concat([
            m_ram if m_ram is not None else pd.DataFrame(),
            u_ram if u_ram is not None else pd.DataFrame()
        ], ignore_index=True)

        # 3. Refresh metadata (I/O labels, etc.)
        processed = [refresh_ram_metadata(row.to_dict()) for _, row in combined.iterrows()]
        df = pd.DataFrame(processed)
        df.columns = df.columns.str.strip()

        # 4. Sanitize hardware (Robot, Device) information to prevent standard array displays
        for h_col in ['Robot', 'Functional_Device']:
            if h_col in df.columns:
                df[h_col] = df[h_col].astype(str).str.strip().replace(['[]', 'nan', '', 'None', 'NaN'], 'None')

        # 5. Numeric column conversion using to_float utility
        for col in ['Total_Material_Cost(USD)', 'Hands_on_Time(h)', 'Operation_Time(h)']:
            if col in df.columns:
                df[col] = df[col].apply(to_float)

        df['Total_RAM_Cost(USD)'] = df['Total_Material_Cost(USD)'] + (df['Hands_on_Time(h)'] * LABOR_RATE)
        df['Total_Time(h)'] = df['Operation_Time(h)'] + df['Hands_on_Time(h)']

        # 6. Sort naturally by RAM_ID for consistent sequence alignment
        if 'RAM_ID' in df.columns:
            df = df.sort_values(by='RAM_ID', key=ram_natural_sort_key).reset_index(drop=True)

        return df
    except Exception as e:
        st.error(f"Error loading RAM reference: {e}")
        return pd.DataFrame()


# --- Load Initialized Data ---
df_wf = load_workflow_db()
df_ram_ref = load_ram_reference_full()

# ==========================================
# 2. Main UI: Header & Selection
# ==========================================
st.title("📚 Workflow Database")
st.markdown("Real-time repository of workflows managed by the SKy Biofoundry.")

if df_wf.empty:
    st.info("No workflows found. Please build and save one first.")
    st.stop()

col_list, col_detail = st.columns([1, 2.5])

with col_list:
    st.subheader("🔍 Browse Workflows")
    db_filter = st.radio("Source", ["All", "MasterDB", "UserDB"], horizontal=True)

    # 1. Apply database source filtering
    f_df = df_wf if db_filter == "All" else df_wf[df_wf['DB_Source'] == db_filter]

    # 2. Search filter: dynamically query by workflow name or author
    search_query = st.text_input("Search Workflow", placeholder="Type name or author...")
    if search_query:
        f_df = f_df[
            f_df['Workflow_Name'].str.contains(search_query, case=False, na=False) |
            f_df['Author'].str.contains(search_query, case=False, na=False)
        ]

    # 3. Populate selectbox with filtered workflow options
    selected_wf_name = st.selectbox("Select Workflow", ["-- Select a workflow --"] + f_df['Workflow_Name'].tolist())

    st.divider()

    # 4. Render the filtered workflow list table for preview
    st.markdown("#### 📋 Workflow List")
    if not f_df.empty:
        ov_disp = f_df[['DB_Source', 'Workflow_Name', 'Author']].rename(
            columns={'DB_Source': 'Src', 'Workflow_Name': 'Name'}
        )
        st.dataframe(ov_disp, hide_index=True, width='stretch')
    else:
        st.caption("No matching workflows found.")

# ==========================================
# 3. Main Detail Panel (Header & Tab 1)
# ==========================================
with col_detail:
    if selected_wf_name == "-- Select a workflow --":
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.info("💡 **Please select a workflow from the list on the left to begin analysis.**")
        st.stop()

    row = f_df[f_df['Workflow_Name'] == selected_wf_name].iloc[0]
    target_ws = "Workflow_MasterDB" if row['DB_Source'] == 'MasterDB' else "Workflow_UserDB"

    st.subheader(f"📄 {row['Workflow_Name']}")
    st.caption(f"**Author:** {row.get('Author', 'Unknown')} | **Registry:** {row['DB_Source']}")

    # [CRITICAL FIX] Implement safe type casting using to_float to prevent page crashes on NaN cells
    tat = to_float(row.get('Turnaround_Time(h)', 0))
    mat_cost = to_float(row.get('Material_Cost(USD)', 0))
    labor_cost = to_float(row.get('Labor_Cost(USD)', 0))
    total_cost_calc = mat_cost + labor_cost
    tp = int(to_float(row.get('Number_of_Samples(Throughput)', 96)))
    epi = to_float(row.get('EPI', 0))

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("EPI (-)", f"{epi:.2f}")
    m2.metric("Turnaround Time (h)", f"{tat:.2f}")
    m3.metric("Total Cost (USD)", f"{total_cost_calc:,.2f}")
    m4.metric("Number of Samples", f"{tp}")

    st.divider()

    # [CORRECTED INDENTATION] Unnested tabs layout to ensure perfect parallel alignment (4-space indentation)
    t_analytics, t_steps, t_mats, t_sim, t_manage, t_export = st.tabs([
        "📝 Overview & Analysis", "⚙️ Steps", "📦 Materials", "🔄 Loop Simulation", "🛠️ Manage", "📤 Export"
    ])

    steps_list = safe_eval_list(row.get('Steps_RAMList', '[]'))

    # --- TAB 1: Overview & Analysis ---
    with t_analytics:
        with st.container(border=True):
            c_desc, c_out = st.columns([1, 1])
            with c_desc:
                st.markdown("##### 📝 Description")
                st.write(row.get('Description', 'No description provided.'))
            with c_out:
                st.markdown("##### 🎯 Output Summary")
                st.markdown(f":green[**{row.get('Output_Summary', 'Not specified.')}**]")

        st.markdown("<div style='margin-top: 20px;'></div>", unsafe_allow_html=True)
        st.markdown("#### 💎 Performance Summary")
        c_time_card, c_cost_card = st.columns(2)
        with c_time_card:
            op_t = to_float(row.get('Operation_Time(h)', 0))
            hot_t = to_float(row.get('Hands_on_Time(h)', 0))
            st.info(f"⏱️ **Operation Time (h):** {op_t:.2f} \n\n⏱️ **Hands-on Time (h):** {hot_t:.2f}")
        with c_cost_card:
            st.warning(f"💰 **Labor Cost (USD):** {labor_cost:,.2f}\n\n💰 **Material Cost (USD):** {mat_cost:,.2f}")

        st.divider()
        st.markdown("#### 📊 Resource Consumption Breakdown")

        if steps_list and not df_ram_ref.empty:
            ana_df = pd.DataFrame(steps_list).merge(
                df_ram_ref[['RAM_ID', 'Total_Time(h)', 'Total_RAM_Cost(USD)', 'RAM_Name']],
                left_on='id', right_on='RAM_ID', how='left'
            ).fillna(0.0)

            if 'op_time' in ana_df.columns and 'ho_time' in ana_df.columns:
                ana_df['Total_Time(h)'] = ana_df['op_time'].apply(to_float) + ana_df['ho_time'].apply(to_float)

            if 'mat_cost' in ana_df.columns:
                ho_ref = ana_df['ho_time'] if 'ho_time' in ana_df.columns else ana_df['Hands_on_Time(h)']
                ana_df['Total_RAM_Cost(USD)'] = ana_df['mat_cost'].apply(to_float) + (
                        ho_ref.apply(to_float) * LABOR_RATE)

            if not ana_df.empty:
                t_bn = ana_df.loc[ana_df['Total_Time(h)'].idxmax()]
                c_bn = ana_df.loc[ana_df['Total_RAM_Cost(USD)'].idxmax()]
                st.markdown("##### 🚨 Bottleneck Identification")
                bc1, bc2 = st.columns(2)
                with bc1:
                    st.error(f"**Time Bottleneck**: {t_bn['id']} ({t_bn.get('RAM_Name', 'N/A')})")
                    st.caption(
                        f"Occupies **{t_bn['Total_Time(h)']:.2f} h** ({(t_bn['Total_Time(h)'] / tat * 100 if tat > 0 else 0):.1f}% of TAT.)")
                with bc2:
                    st.warning(f"**Cost Bottleneck**: {c_bn['id']} ({c_bn.get('RAM_Name', 'N/A')})")
                    st.caption(
                        f"Consumes **${c_bn['Total_RAM_Cost(USD)']:,.2f}** ({(c_bn['Total_RAM_Cost(USD)'] / total_cost_calc * 100 if total_cost_calc > 0 else 0):.1f}% of Total Cost.)")

            st_tab1, st_tab2 = st.tabs(["⏱️ Time Analysis", "💰 Cost Analysis"])
            ana_df['Chart_Label'] = [f"Step {i + 1}: {r['id']}" for i, r in ana_df.iterrows()]
            ana_df['Full_Label'] = [f"Step {i + 1}: {r['id']} ({r.get('RAM_Name', 'N/A')})" for i, r in
                                    ana_df.iterrows()]

            with st_tab1:
                tc1, tc2 = st.columns([1.5, 1])
                with tc1:
                    fig_t = px.pie(ana_df[ana_df['Total_Time(h)'] > 0], values='Total_Time(h)', names='Chart_Label',
                                   hole=0.5, color_discrete_sequence=px.colors.qualitative.Pastel)
                    fig_t.update_layout(showlegend=True, margin=dict(t=30, b=30, l=10, r=10), title="Time Distribution")

                    # [SYNCED] Custom Hover Template with "h" unit & Keep Step Sequence
                    fig_t.update_traces(
                        hovertemplate="<b>%{label}</b><br>Total Time = %{value:.2f}h<extra></extra>",
                        sort=False
                    )
                    st.plotly_chart(fig_t, width='stretch')
                with tc2:
                    for _, r in ana_df.iterrows():
                        ratio = (r['Total_Time(h)'] / tat) if tat > 0 else 0
                        st.write(f"**{r['Full_Label']}** ({r['Total_Time(h)']:.2f}h, {ratio * 100:.1f}%)")
                        st.progress(max(0.0, min(float(ratio), 1.0)))
            with st_tab2:
                cc1, cc2 = st.columns([1.5, 1])
                with cc1:
                    fig_c = px.pie(ana_df[ana_df['Total_RAM_Cost(USD)'] > 0], values='Total_RAM_Cost(USD)',
                                   names='Chart_Label', hole=0.5, color_discrete_sequence=px.colors.qualitative.Set3)
                    fig_c.update_layout(showlegend=True, margin=dict(t=30, b=30, l=10, r=10), title="Cost Distribution")

                    # [SYNCED] Custom Hover Template with USD formatting & Keep Step Sequence
                    fig_c.update_traces(
                        hovertemplate="<b>%{label}</b><br>Total Cost = %{value:,.3f} USD<extra></extra>",
                        sort=False
                    )
                    st.plotly_chart(fig_c, width='stretch')
                with cc2:
                    for _, r in ana_df.iterrows():
                        ratio = (r['Total_RAM_Cost(USD)'] / total_cost_calc) if total_cost_calc > 0 else 0
                        st.write(f"**{r['Full_Label']}** (${r['Total_RAM_Cost(USD)']:.2f}, {ratio * 100:.1f}%)")
                        st.progress(max(0.0, min(float(ratio), 1.0)))
        else:
            st.info("Step data required for breakdown visualization.")

    # --- TAB 2: Steps ---
    with t_steps:
        st.subheader("⚙️ Workflow Step Sequence")
        if not steps_list:
            st.info("No detailed step data available.")
        else:
            for i, s in enumerate(steps_list):
                # Merge step-specific configuration with master RAM DB references to retrieve hardware details
                ram_match = df_ram_ref[df_ram_ref['RAM_ID'] == s['id']]
                ref_data = ram_match.iloc[0].to_dict() if not ram_match.empty else {}

                # Unpack step-specific I/O specs or fallback to defaults
                if 'io_data' in s and s['io_data'] != '[]':
                    display_data = refresh_ram_metadata(s)
                else:
                    display_data = ref_data

                with st.container(border=True):
                    st.markdown(f"**Step {i + 1}: {s['id']} - {s.get('name', 'N/A')}**")

                    # Row 1: Render input/output specifications
                    st.caption(
                        f"In: {display_data.get('input_display', 'None')} | Out: {display_data.get('output_display', 'None')}"
                    )

                    # Row 2: Render active hardware configuration metrics (Robot and Functional Devices)
                    robot_info = s.get('Robot') or ref_data.get('Robot', 'None')
                    device_info = s.get('Functional_Device') or ref_data.get('Functional_Device', 'None')

                    # Clean bracket strings and NaN representations for display readability
                    r_disp = robot_info if str(robot_info) not in ["[]", "nan", ""] else "None"
                    d_disp = device_info if str(device_info) not in ["[]", "nan", ""] else "None"

                    st.caption(f"🤖 **Robot:** {r_disp} | 🛠️ **Device:** {d_disp}")

    # --- TAB 3: Materials ---
    with t_mats:
        st.subheader("📦 Bill of Materials (BOM)")

        # Unpack and aggregate materials from individual steps, mapping to their Source RAM
        all_mats_preview = []
        if steps_list:
            for s in steps_list:
                s_id = s.get('id', 'Unknown')
                s_mats = safe_eval_list(s.get('material_data', '[]'))
                for m in s_mats:
                    m_item = m.copy()
                    m_item['Source_RAM'] = s_id  # Inject step mapping dependency
                    all_mats_preview.append(m_item)

        # Fallback mechanism for legacy workflow entries without nested step-material tables
        if not all_mats_preview:
            legacy_mats = safe_eval_list(row.get('Material_Summary', '[]'))
            for m in legacy_mats:
                m_item = m.copy()
                if 'Source_RAM' not in m_item:
                    m_item['Source_RAM'] = "Legacy"
                all_mats_preview.append(m_item)

        if all_mats_preview:
            df_bom_preview = pd.DataFrame(all_mats_preview)

            # Re-order key columns to place Source_RAM first
            if 'Source_RAM' in df_bom_preview.columns:
                cols_order = ['Source_RAM'] + [c for c in df_bom_preview.columns if c != 'Source_RAM']
                df_bom_preview = df_bom_preview[cols_order]

            st.metric("Total Material Cost (USD)", f"{mat_cost:,.2f}")
            st.dataframe(
                df_bom_preview,
                hide_index=True,
                width='stretch',
                column_config={
                    "Quantity": st.column_config.NumberColumn("Qty", format="%.2f"),
                    "Unit Price": st.column_config.NumberColumn("Unit Price (USD)", format="$%,.4f"),
                    "Total Price": st.column_config.NumberColumn("Total Price (USD)", format="$%,.2f"),
                }
            )
        else:
            st.info("No detailed material data available for this workflow.")

    # --- TAB 4: Loop Simulation (Indentation Corrected) ---
    with t_sim:
        st.subheader("🔄 Loop Simulation")
        sim_mode = st.radio("Simulation Mode", ["Manual Scaling", "Resource-limited Auto-calc"],
                            horizontal=True)
        st.divider()

        if sim_mode == "Manual Scaling":
            sim_col1, sim_col2 = st.columns([1, 2])
            with sim_col1:
                loops = st.slider("Target Cycles", 1, 100, 10)
            with sim_col2:
                req_t, req_c, req_s = tat * loops, total_cost_calc * loops, tp * loops
                st.markdown(f"#### Results for {loops} Cycles")
                res_c1, res_c2, res_c3 = st.columns(3)
                res_c1.metric("Required Time (h)", f"{req_t:.2f}")
                res_c2.metric("Required Budget (USD)", f"{req_c:,.2f}")
                res_c3.metric("Number of Samples", f"{req_s:,}")
                st.success(f"✅ **EPI remains stable at {epi:.2f}**. Scaling complete.")
        else:
            sim_col3, sim_col4 = st.columns([1, 2])
            with sim_col3:
                lim_b = st.slider("Budget Limit (USD)", 500, 100000, 5000, 100)
                lim_t = st.slider("Time Limit (h)", 24, 3000, 168, 12)
            with sim_col4:
                max_n_b = math.floor(lim_b / total_cost_calc) if total_cost_calc > 0 else 9999
                max_n_t = math.floor(lim_t / tat) if tat > 0 else 9999
                final_max = min(max_n_b, max_n_t)
                actual_c, actual_t = final_max * total_cost_calc, final_max * tat

                st.markdown(f"#### Maximum Capacity Analysis")
                st.metric("Possible Maximum Cycles", f"{final_max} Loops")

                st.write("**Budget Usage**")
                st.progress(min(actual_c / lim_b if lim_b > 0 else 0, 1.0))
                st.markdown(
                    f'<div style="margin-bottom:15px;"><span style="color:#ff4b4b;font-weight:700;">${actual_c:,.2f}</span> <span style="float:right;color:#10b981;">Remain: ${max(0, lim_b - actual_c):,.2f}</span></div>',
                    unsafe_allow_html=True
                )

                st.write("**Time Usage**")
                st.progress(min(actual_t / lim_t if lim_t > 0 else 0, 1.0))
                st.markdown(
                    f'<div><span style="color:#ff4b4b;font-weight:700;">{actual_t:.2f} h</span> <span style="float:right;color:#10b981;">Remain: {max(0, lim_t - actual_t):,.2f} h</span></div>',
                    unsafe_allow_html=True
                )

                if final_max > 0:
                    bn = "Financial Budget" if max_n_b <= max_n_t else "Time Budget"
                    st.warning(f"⚠️ **Resource Insight:** Scaling is restricted by your **{bn}**.")

    # --- TAB 5: Manage ---
    with t_manage:
        st.markdown("### 🛠️ Administrative Actions")

        if st.button("🏗️ Load to Workflow Builder", type="primary", width='stretch'):
            reconstructed_wf = []
            for s in steps_list:
                match = df_ram_ref[df_ram_ref['RAM_ID'] == s.get('id')]
                if not match.empty:
                    ram_d = match.iloc[0].to_dict()

                    # [Persistence Core Fix] Unify NaN (float) values to empty strings ("")
                    # Replacing with None can cause errors in the Builder's loop, so handling safely here
                    ram_d = {k: ("" if isinstance(v, float) and math.isnan(v) else v) for k, v in ram_d.items()}

                    if 'op_time' in s: ram_d['Operation_Time(h)'] = to_float(s['op_time'])
                    if 'ho_time' in s: ram_d['Hands_on_Time(h)'] = to_float(s['ho_time'])
                    if 'mat_cost' in s: ram_d['Total_Material_Cost(USD)'] = to_float(s['mat_cost'])
                    if 'io_data' in s: ram_d['io_data'] = s['io_data']

                    ram_d = refresh_ram_metadata(ram_d)
                    reconstructed_wf.append(ram_d)

            st.session_state.workflow = reconstructed_wf
            st.session_state.wf_name = row['Workflow_Name']
            st.session_state.wf_author = row.get('Author', "Researcher")
            st.session_state.wf_desc = row.get('Description', "")
            st.session_state.wf_output = row.get('Output_Summary', "")
            st.session_state.wf_throughput = int(row.get('Number_of_Samples(Throughput)', 96))

            st.switch_page("pages/Workflow Builder.py")

        st.divider()

        with st.expander("📝 Edit workflow Metadata"):
            with st.form(key="edit_meta_form"):
                new_desc = st.text_area("Update Description", value=row.get('Description', ''))
                new_output = st.text_input("Update Output Summary", value=row.get('Output_Summary', ''))
                edit_code = st.text_input("Access Code", type="password")

                if st.form_submit_button("Apply Metadata Changes"):
                    try:
                        t_df = conn.read(spreadsheet=MY_SHEET_URL, worksheet=target_ws, ttl=0)
                        idx_list = t_df.index[t_df['Workflow_Name'] == selected_wf_name].tolist()
                        if idx_list:
                            idx = idx_list[0]
                            raw_stored_code = t_df.at[idx, 'access_code']
                            raw_pw_str = str(raw_stored_code).strip() if not pd.isna(raw_stored_code) else "None"
                            stored_code = raw_pw_str[:-2] if raw_pw_str.endswith('.0') else raw_pw_str

                            if am.is_edit_authorized(edit_code, stored_code):
                                t_df.at[idx, 'Description'], t_df.at[idx, 'Output_Summary'] = new_desc, new_output
                                conn.update(spreadsheet=MY_SHEET_URL, worksheet=target_ws, data=t_df)
                                st.success("Metadata updated successfully!")

                                # [API OPTIMIZATION] Target clearing for workflow DB only to prevent heavy reloads
                                load_workflow_db.clear()
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.error("Authorization failed.")
                    except Exception as e:
                        st.error(f"Update failed: {e}")

        with st.expander("🗑️ Delete Workflow"):
            with st.form(key="delete_wf_form"):
                del_code = st.text_input("Access Code to Confirm Deletion", type="password")

                if st.form_submit_button("Delete Permanently"):
                    try:
                        t_df = conn.read(spreadsheet=MY_SHEET_URL, worksheet=target_ws, ttl=0)
                        idx_list = t_df.index[t_df['Workflow_Name'] == selected_wf_name].tolist()
                        if idx_list:
                            idx = idx_list[0]
                            raw_stored_code = t_df.at[idx, 'access_code']
                            raw_pw_str = str(raw_stored_code).strip() if not pd.isna(raw_stored_code) else "None"
                            stored_code = raw_pw_str[:-2] if raw_pw_str.endswith('.0') else raw_pw_str

                            if am.is_edit_authorized(del_code, stored_code):
                                conn.update(spreadsheet=MY_SHEET_URL, worksheet=target_ws, data=t_df.drop(idx))
                                st.success(f"Successfully deleted {selected_wf_name}!")

                                # [API OPTIMIZATION] Target clearing for workflow DB only to prevent heavy reloads
                                load_workflow_db.clear()
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.error("Authorization failed.")
                    except Exception as e:
                        st.error(f"Deletion failed: {e}")

    # --- TAB 6: Export (Indentation, Security and Hardware Aligned) ---
    with t_export:
        st.subheader("📤 Export Workflow Data")
        st.write("Download the complete workflow profile, resource analysis, and BOM.")

        try:
            # 1. Summary Data Sheet Generation
            summary_df = pd.DataFrame([{
                "Workflow Name": row['Workflow_Name'],
                "Author": row.get('Author', 'Unknown'),
                "Turnaround Time (h)": tat,
                "Total Cost (USD)": total_cost_calc,
                "Material Cost (USD)": row.get('Material_Cost(USD)', 0),
                "Labor Cost (USD)": row.get('Labor_Cost(USD)', 0),
                "Throughput": tp,
                "EPI": epi
            }])

            # 2. [FIXED] Robust Resource Breakdown Sheet Generation with Robot & Device Specs
            if steps_list:
                resolved_steps = []
                for s in steps_list:
                    # Pull default metadata from RAM Reference DB to secure a fallback source
                    ram_match = df_ram_ref[df_ram_ref['RAM_ID'] == s.get('id')]
                    ref_data = ram_match.iloc[0].to_dict() if not ram_match.empty else {}

                    # Determine operational parameters dynamically with step overrides
                    op_t = to_float(s.get('op_time', ref_data.get('Operation_Time(h)', 0.0)))
                    ho_t = to_float(s.get('ho_time', ref_data.get('Hands_on_Time(h)', 0.0)))
                    mat_c = to_float(s.get('mat_cost', ref_data.get('Total_Material_Cost(USD)', 0.0)))
                    lab_c = ho_t * LABOR_RATE

                    # Retrieve and clean active hardware configurations matching the step's profile
                    robot_info = s.get('Robot') or ref_data.get('Robot', 'None')
                    device_info = s.get('Functional_Device') or ref_data.get('Functional_Device', 'None')

                    r_disp = robot_info if str(robot_info) not in ["[]", "nan", ""] else "None"
                    d_disp = device_info if str(device_info) not in ["[]", "nan", ""] else "None"

                    resolved_steps.append({
                        "Step No": int(to_float(s.get('step', 1))),
                        "RAM ID": s.get('id', 'Unknown'),
                        "RAM Name": s.get('name') or ref_data.get('RAM_Name', 'N/A'),
                        "Robot": r_disp,
                        "Functional Device": d_disp,
                        "Operation Time (h)": op_t,
                        "Hands On Time (h)": ho_t,
                        "Material Cost (USD)": mat_c,
                        "Labor Cost (USD)": lab_c,
                        "Total Time (h)": op_t + ho_t,
                        "Total Cost (USD)": mat_c + lab_c
                    })
                res_disp = pd.DataFrame(resolved_steps)
            else:
                res_disp = pd.DataFrame()

            # 3. Dynamic BOM Reconstruction (Source_RAM aligned to first column)
            all_mats = []
            if steps_list:
                for s in steps_list:
                    s_id = s.get('id', 'Unknown')
                    s_mats = safe_eval_list(s.get('material_data', '[]'))
                    for m in s_mats:
                        m_item = m.copy()
                        m_item['Source_RAM'] = s_id
                        m_item['Total Price'] = to_float(str(m_item.get('Total Price', '0')).replace(',', ''))
                        all_mats.append(m_item)

            if all_mats:
                bom_df = pd.DataFrame(all_mats)
                cols = ['Source_RAM'] + [c for c in bom_df.columns if c != 'Source_RAM']
                bom_df = bom_df[cols]
                total_val = bom_df['Total Price'].sum()
                total_row = pd.DataFrame([{
                    "Source_RAM": "---",
                    "Material Name": "TOTAL MATERIAL COST (USD)",
                    "Total Price": total_val
                }])
                bom_df = pd.concat([bom_df, total_row], ignore_index=True).fillna("")
            else:
                bom_df = pd.DataFrame()

            # 4. Generate Excel File in memory
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                summary_df.to_excel(writer, sheet_name='Summary', index=False)
                if not res_disp.empty:
                    res_disp.to_excel(writer, sheet_name='Analysis', index=False)
                if not bom_df.empty:
                    bom_df.to_excel(writer, sheet_name='BOM', index=False)
            excel_data = output.getvalue()

            # 5. TXT Report Generation
            report_txt = f"# Workflow Analysis: {row['Workflow_Name']}\n\n"
            report_txt += f"- Turnaround Time (h): {tat:.2f}  | Total Cost (USD): {total_cost_calc:,.2f}\n\n"
            report_txt += "## Step Sequence\n"
            if not res_disp.empty:
                for _, r in res_disp.iterrows():
                    report_txt += f"{int(r['Step No'])}. [{r['RAM ID']}] {r['RAM Name']} | Robot: {r['Robot']} | Device: {r['Functional Device']}: {r['Total Time (h)']:.2f}h / {r['Total Cost (USD)']:,.2f} USD\n"

            # 6. UI Download Layout
            st.divider()
            c1, c2, c3 = st.columns(3)
            with c1:
                st.download_button("📊 Download Excel", data=excel_data,
                                   file_name=f"{row['Workflow_Name']}_Report.xlsx",
                                   mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                   width='stretch')
            with c2:
                # [SECURITY FIXED] Strip out password keys prior to JSON serialization
                json_export_data = row.to_dict()
                for sensitive_key in ['access_code', 'Access_Code']:
                    json_export_data.pop(sensitive_key, None)

                st.download_button("🔗 Download JSON",
                                   data=json.dumps(json_export_data, indent=4, ensure_ascii=False),
                                   file_name=f"{row['Workflow_Name']}.json", mime="application/json",
                                   width='stretch')
            with c3:
                st.download_button("📝 Download TXT", data=report_txt,
                                   file_name=f"{row['Workflow_Name']}_Note.txt", mime="text/plain",
                                   width='stretch')

            st.markdown("##### 🔍 Preview: Resource Analysis")
            st.dataframe(res_disp, hide_index=True)

        except Exception as e:
            st.error(f"Export Tab Error: {e}")

st.markdown(back_to_top_html, unsafe_allow_html=True)