import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import plotly.express as px
import json
import ast
import math
import re

# [NOTICE] 2026 Standard Syntax Compliance
pd.set_option('future.no_silent_downcasting', True)

# --- Constants ---
MY_SHEET_URL = st.secrets["connections"]["gsheets"]["spreadsheet"]
conn = st.connection("gsheets", type=GSheetsConnection)

LABOR_RATE = 37.5
WORKFLOW_CATEGORY_OPTIONS = [
    "Genetic construct preparation",
    "Host strain engineering",
    "Screening",
    "Analytical measurement",
    "Culture and bioprocessing",
    "Other"
]

# ==========================================
# 1. Utility Functions
# ==========================================

def to_float(val):
    """Clean and cast values safely to float."""
    try:
        if val is None:
            return 0.0
        val_str = str(val).strip()
        if val_str in ["", "nan", "NaN", "None", "N/A"]:
            return 0.0
        return float(val_str.replace(',', ''))
    except Exception:
        return 0.0


def optional_float(val):
    """Return float for optional numeric fields; missing values become NaN, not zero."""
    try:
        if val is None:
            return math.nan
        val_str = str(val).strip()
        if val_str in ["", "nan", "NaN", "None", "N/A"]:
            return math.nan
        return float(val_str.replace(',', ''))
    except Exception:
        return math.nan


def has_value(val):
    """Return True only when an optional spreadsheet cell contains a meaningful value."""
    if val is None:
        return False
    if isinstance(val, float) and math.isnan(val):
        return False
    return str(val).strip() not in ["", "nan", "NaN", "None", "N/A"]


def is_aepi_record_enabled(row):
    """
    Determine whether a workflow has valid empirical success-rate data.
    Legacy rows with aEPI=0.0 and Total_Samples=0 are treated as aEPI-disabled.
    """
    successful = row.get('Successful_Samples', '')
    total = row.get('Total_Samples', '')
    rate = row.get('Empirical_Success_Rate', '')
    aepi = row.get('aEPI', '')

    if not (has_value(successful) and has_value(total) and has_value(rate) and has_value(aepi)):
        return False

    successful_num = to_float(successful)
    total_num = to_float(total)
    rate_num = to_float(rate)

    return (
        total_num > 0
        and 0 < rate_num <= 1
        and 0 <= successful_num <= total_num
    )


def safe_eval_list(val):
    """Safely parse list-like or JSON strings into Python objects."""
    if isinstance(val, list):
        return val
    if isinstance(val, dict):
        return [val]
    if val is None:
        return []
    if isinstance(val, float) and math.isnan(val):
        return []
    try:
        if pd.isna(val):
            return []
    except ValueError:
        pass

    val_str = str(val).strip()
    if val_str in ["", "[]", "nan", "NaN", "None"]:
        return []

    try:
        return json.loads(val_str)
    except Exception:
        try:
            return ast.literal_eval(val_str)
        except Exception:
            return []


def clean_display_text(value, default="None"):
    if value is None:
        return default
    text = str(value).strip()
    if text in ["", "[]", "nan", "NaN", "None"]:
        return default
    return text


def normalize_workflow_category(value):
    category = clean_display_text(value, default="Other")
    return category if category in WORKFLOW_CATEGORY_OPTIONS else "Other"


def normalize_equipment_items(value):
    """Normalize equipment field into a list of readable item names."""
    if isinstance(value, list):
        raw_items = value
    else:
        parsed = safe_eval_list(value)
        if parsed:
            raw_items = parsed
        else:
            raw_items = re.split(r"[,;/]", str(value))

    cleaned = []
    for item in raw_items:
        text = clean_display_text(item, default="")
        if text and text not in ["None", "N/A"]:
            cleaned.append(text)
    return sorted(list(set(cleaned))) if cleaned else ["None"]


def format_optional_number(value, fmt="{:.2f}"):
    if pd.isna(value):
        return "N/A"
    try:
        return fmt.format(float(value))
    except Exception:
        return "N/A"


def workflow_label(row):
    return f"[{row.get('Source', 'DB')}] {row.get('Workflow_Name', 'Unnamed')}"


def has_aepi_data(row):
    return bool(row.get('aEPI_Enabled', is_aepi_record_enabled(row)))


def get_steps_list(row):
    return safe_eval_list(row.get('Steps_RAMList', '[]'))


def final_validation_step_index(row, steps):
    """Return final validation step index if aEPI data exist; otherwise None.
    The revised Builder assigns Final_Validation_RAM from the final workflow RAM.
    """
    final_val = clean_display_text(row.get('Final_Validation_RAM', ''), default="")
    if not final_val or not has_aepi_data(row) or not steps:
        return None
    return len(steps) - 1


def build_stepwise_dataframe(compare_df):
    records = []
    for _, row in compare_df.iterrows():
        steps = get_steps_list(row)
        wf_label = row['Workflow_Label']
        tat = to_float(row.get('Turnaround_Time(h)', 0))
        total_cost = to_float(row.get('Total_Cost(USD)', 0))
        final_idx = final_validation_step_index(row, steps)

        for i, step in enumerate(steps):
            step_no = int(to_float(step.get('step', i + 1))) or i + 1
            ram_id = clean_display_text(step.get('id', 'Unknown'), default="Unknown")
            ram_name = clean_display_text(step.get('name', 'N/A'), default="N/A")
            op_time = to_float(step.get('op_time', 0))
            ho_time = to_float(step.get('ho_time', 0))
            mat_cost = to_float(step.get('mat_cost', 0))
            lab_cost = ho_time * LABOR_RATE
            total_time = op_time + ho_time
            step_cost = mat_cost + lab_cost
            is_final_validation = final_idx == i

            records.append({
                "Workflow": wf_label,
                "Workflow_Name": row.get('Workflow_Name', 'Unnamed'),
                "Category": row.get('Workflow_Category', 'Other'),
                "Step": step_no,
                "RAM ID": ram_id,
                "RAM Name": ram_name,
                "RAM Label": f"{ram_id} - {ram_name}",
                "Display Label": f"{ram_id} - {ram_name}" + (" 🧪 Final Validation RAM" if is_final_validation else ""),
                "Operation Time (h)": op_time,
                "Hands-on Time (h)": ho_time,
                "Total Time (h)": total_time,
                "Material Cost (USD)": mat_cost,
                "Labor Cost (USD)": lab_cost,
                "Total Cost (USD)": step_cost,
                "Time Share (%)": (total_time / tat * 100) if tat > 0 else 0,
                "Cost Share (%)": (step_cost / total_cost * 100) if total_cost > 0 else 0,
                "Robot": clean_display_text(step.get('Robot', 'None')),
                "Functional Device": clean_display_text(step.get('Functional_Device', 'None')),
                "Is Final Validation RAM": is_final_validation,
                "Raw Step": step
            })
    return pd.DataFrame(records)


def build_material_dataframe(compare_df):
    records = []
    for _, row in compare_df.iterrows():
        wf_label = row['Workflow_Label']
        steps = get_steps_list(row)

        if steps:
            for step in steps:
                ram_id = clean_display_text(step.get('id', 'Unknown'), default="Unknown")
                mats = safe_eval_list(step.get('material_data', '[]'))
                for mat in mats:
                    if not isinstance(mat, dict):
                        continue
                    material_name = clean_display_text(mat.get('Material Name', mat.get('Material_Name', 'Unknown')), default="Unknown")
                    quantity = to_float(mat.get('Quantity', 0))
                    unit = clean_display_text(mat.get('Unit', ''), default="")
                    unit_price = to_float(mat.get('Unit Price', mat.get('Unit_Price', 0)))
                    total_price = to_float(mat.get('Total Price', mat.get('Total_Price', 0)))
                    records.append({
                        "Workflow": wf_label,
                        "Source RAM": ram_id,
                        "Material Name": material_name,
                        "Quantity": quantity,
                        "Unit": unit,
                        "Unit Price (USD)": unit_price,
                        "Total Price (USD)": total_price
                    })

        # Fallback for legacy workflows where material data only exists in Material_Summary.
        if not any(r["Workflow"] == wf_label for r in records):
            legacy_mats = safe_eval_list(row.get('Material_Summary', '[]'))
            for mat in legacy_mats:
                if not isinstance(mat, dict):
                    continue
                material_name = clean_display_text(mat.get('Material Name', mat.get('Material_Name', 'Unknown')), default="Unknown")
                total_price = to_float(mat.get('Total Price', mat.get('Total_Price', 0)))
                records.append({
                    "Workflow": wf_label,
                    "Source RAM": clean_display_text(mat.get('Source_RAM', 'Legacy'), default="Legacy"),
                    "Material Name": material_name,
                    "Quantity": to_float(mat.get('Quantity', 0)),
                    "Unit": clean_display_text(mat.get('Unit', ''), default=""),
                    "Unit Price (USD)": to_float(mat.get('Unit Price', mat.get('Unit_Price', 0))),
                    "Total Price (USD)": total_price
                })
    return pd.DataFrame(records)


def build_equipment_dataframe(step_df):
    records = []
    if step_df.empty:
        return pd.DataFrame(records)

    for _, row in step_df.iterrows():
        for robot in normalize_equipment_items(row.get('Robot', 'None')):
            if robot != "None":
                records.append({
                    "Workflow": row['Workflow'],
                    "Step": row['Step'],
                    "RAM ID": row['RAM ID'],
                    "Equipment Type": "Robot",
                    "Equipment": robot
                })
        for device in normalize_equipment_items(row.get('Functional Device', 'None')):
            if device != "None":
                records.append({
                    "Workflow": row['Workflow'],
                    "Step": row['Step'],
                    "RAM ID": row['RAM ID'],
                    "Equipment Type": "Functional Device",
                    "Equipment": device
                })
    return pd.DataFrame(records)



def build_ram_delta_dataframe(step_df):
    """Summarize how shared RAMs differ across selected workflows."""
    records = []
    if step_df.empty:
        return pd.DataFrame(records)

    for ram_id, group in step_df.groupby('RAM ID'):
        workflows = group['Workflow'].nunique()
        if workflows < 2:
            continue

        time_min_idx = group['Total Time (h)'].idxmin()
        time_max_idx = group['Total Time (h)'].idxmax()
        cost_min_idx = group['Total Cost (USD)'].idxmin()
        cost_max_idx = group['Total Cost (USD)'].idxmax()

        time_min = group.loc[time_min_idx]
        time_max = group.loc[time_max_idx]
        cost_min = group.loc[cost_min_idx]
        cost_max = group.loc[cost_max_idx]

        records.append({
            "RAM ID": ram_id,
            "RAM Name": clean_display_text(group['RAM Name'].iloc[0], default="N/A"),
            "Compared Workflows": int(workflows),
            "Min Time Workflow": time_min['Workflow'],
            "Min Time (h)": time_min['Total Time (h)'],
            "Max Time Workflow": time_max['Workflow'],
            "Max Time (h)": time_max['Total Time (h)'],
            "Δ Time (h)": time_max['Total Time (h)'] - time_min['Total Time (h)'],
            "Min Cost Workflow": cost_min['Workflow'],
            "Min Cost (USD)": cost_min['Total Cost (USD)'],
            "Max Cost Workflow": cost_max['Workflow'],
            "Max Cost (USD)": cost_max['Total Cost (USD)'],
            "Δ Cost (USD)": cost_max['Total Cost (USD)'] - cost_min['Total Cost (USD)']
        })

    if not records:
        return pd.DataFrame(records)
    return pd.DataFrame(records).sort_values(["Δ Time (h)", "Δ Cost (USD)"], ascending=False).reset_index(drop=True)


def build_material_delta_dataframe(material_df):
    """Summarize how shared consumable costs differ across selected workflows."""
    records = []
    if material_df.empty:
        return pd.DataFrame(records)

    summary = material_df.groupby(['Workflow', 'Material Name'], as_index=False)['Total Price (USD)'].sum()
    for material, group in summary.groupby('Material Name'):
        workflows = group['Workflow'].nunique()
        if workflows < 2:
            continue

        min_idx = group['Total Price (USD)'].idxmin()
        max_idx = group['Total Price (USD)'].idxmax()
        min_row = group.loc[min_idx]
        max_row = group.loc[max_idx]
        records.append({
            "Material Name": material,
            "Compared Workflows": int(workflows),
            "Min Cost Workflow": min_row['Workflow'],
            "Min Cost (USD)": min_row['Total Price (USD)'],
            "Max Cost Workflow": max_row['Workflow'],
            "Max Cost (USD)": max_row['Total Price (USD)'],
            "Δ Cost (USD)": max_row['Total Price (USD)'] - min_row['Total Price (USD)']
        })

    if not records:
        return pd.DataFrame(records)
    return pd.DataFrame(records).sort_values("Δ Cost (USD)", ascending=False).reset_index(drop=True)


def io_display_from_step(step):
    """Create compact input/output display strings from step-level io_data."""
    io_list = safe_eval_list(step.get('io_data', '[]'))

    def essentials(io_type):
        return [
            item for item in io_list
            if isinstance(item, dict)
            and str(item.get('Type', '')).lower() == io_type.lower()
            and (item.get('Essential') is True or str(item.get('Essential')).lower() == 'true')
        ]

    def label(items):
        labels = []
        for item in items:
            substance = clean_display_text(item.get('Substance', 'Unknown'), default='Unknown')
            classification = clean_display_text(
                item.get('Classification', item.get('Substance Class', 'Generic')),
                default='Generic'
            ).replace('Universal', 'Generic')
            vessel = clean_display_text(item.get('Vessel', 'None'), default='None')
            labels.append(f"{substance}:({classification}) in {vessel}")
        return ", ".join(labels) if labels else "None"

    return label(essentials('Input')), label(essentials('Output'))


def short_workflow_name(label, max_chars=42):
    text = str(label)
    return text if len(text) <= max_chars else text[:max_chars - 1] + "…"


def safe_key(value):
    """Create a stable Streamlit key fragment from arbitrary workflow/material labels."""
    text = str(value)
    text = re.sub(r"[^0-9A-Za-z_]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text[:80] if text else "item"


def make_chart_label(step, ram_id, ram_name, max_chars=62):
    """Compact legend label for time/cost pie charts."""
    label = f"Step {int(to_float(step))}: {ram_id} - {ram_name}"
    return label if len(label) <= max_chars else label[:max_chars - 1] + "…"


def make_top_with_other(df, name_col, value_col, top_n=6):
    """Return top-N rows plus an Other row for pie chart readability."""
    if df.empty:
        return df
    work = df.groupby(name_col, as_index=False)[value_col].sum()
    work = work.sort_values(value_col, ascending=False)
    if len(work) <= top_n:
        return work
    top = work.head(top_n).copy()
    other_sum = work.iloc[top_n:][value_col].sum()
    if other_sum > 0:
        top = pd.concat([top, pd.DataFrame([{name_col: 'Other', value_col: other_sum}])], ignore_index=True)
    return top


# ==========================================
# 2. Data Loading
# ==========================================

@st.cache_data(ttl=60)
def load_all_workflows():
    try:
        m_db = conn.read(spreadsheet=MY_SHEET_URL, worksheet="Workflow_MasterDB", ttl=0)
        u_db = conn.read(spreadsheet=MY_SHEET_URL, worksheet="Workflow_UserDB", ttl=0)

        if m_db is None or m_db.empty:
            m_db = pd.DataFrame(columns=['Workflow_Name'])
        else:
            m_db['Source'] = 'Master'

        if u_db is None or u_db.empty:
            u_db = pd.DataFrame(columns=['Workflow_Name'])
        else:
            u_db['Source'] = 'User'

        combined = pd.concat([m_db, u_db], ignore_index=True).dropna(subset=['Workflow_Name'])
        combined.columns = [c.strip() for c in combined.columns]

        if 'Source' not in combined.columns:
            combined['Source'] = 'Unknown'

        if 'Author' not in combined.columns:
            combined['Author'] = ""

        if 'Workflow_Category' not in combined.columns:
            combined['Workflow_Category'] = "Other"
        combined['Workflow_Category'] = combined['Workflow_Category'].apply(normalize_workflow_category)

        if 'access_code' in combined.columns:
            combined['access_code'] = combined['access_code'].astype(str)

        standard_num_cols = [
            'Turnaround_Time(h)', 'Operation_Time(h)', 'Hands_on_Time(h)',
            'Material_Cost(USD)', 'Labor_Cost(USD)', 'Total_Cost(USD)',
            'EPI', 'Number_of_Samples(Throughput)'
        ]
        for col in standard_num_cols:
            if col not in combined.columns:
                combined[col] = 0.0
            combined[col] = combined[col].apply(to_float)

        optional_num_cols = ['Successful_Samples', 'Total_Samples', 'Empirical_Success_Rate', 'aEPI']
        for col in optional_num_cols:
            if col not in combined.columns:
                combined[col] = math.nan
            combined[f'{col}_num'] = combined[col].apply(optional_float)

        combined['aEPI_Enabled'] = combined.apply(is_aepi_record_enabled, axis=1)
        disabled_aepi_mask = ~combined['aEPI_Enabled']
        for col in optional_num_cols:
            combined.loc[disabled_aepi_mask, f'{col}_num'] = math.nan

        if 'Final_Validation_RAM' not in combined.columns:
            combined['Final_Validation_RAM'] = ""

        if 'Steps_RAMList' not in combined.columns:
            combined['Steps_RAMList'] = "[]"
        if 'Material_Summary' not in combined.columns:
            combined['Material_Summary'] = "[]"

        combined['Workflow_Label'] = combined.apply(workflow_label, axis=1)

        return combined.reset_index(drop=True)
    except Exception as e:
        st.error(f"Data Load Error: {e}")
        return pd.DataFrame()


df_all = load_all_workflows()

# ==========================================
# 3. UI: Header & Filtering
# ==========================================
st.title("📊 Workflow Comparative Analytics")
st.markdown(
    "Compare workflows within the same experimental category and decompose performance differences "
    "into RAM composition, time/cost contributions, bottlenecks, equipment, and consumables."
)

if df_all.empty:
    st.warning("No workflow data found. Please create and save a workflow in the Builder first.")
    st.stop()

with st.sidebar:
    st.header("🔍 Comparison Scope")
    source_filter = st.multiselect("Database Source", ["Master", "User"], default=["Master", "User"])

    source_pool = df_all[df_all['Source'].isin(source_filter)].copy()
    if source_pool.empty:
        st.warning("No workflows found for the selected database source.")
        st.stop()

    present_categories = [c for c in WORKFLOW_CATEGORY_OPTIONS if c in source_pool['Workflow_Category'].unique().tolist()]
    if not present_categories:
        present_categories = ["Other"]

    selected_category = st.selectbox(
        "Workflow Category",
        present_categories,
        help="Select a workflow category to compare workflows with similar experimental purposes."
    )

    filtered_pool = source_pool[source_pool['Workflow_Category'] == selected_category].reset_index(drop=True)

    st.info(
        "Workflow comparisons are restricted to the selected category to avoid comparing workflows "
        "with fundamentally different purposes, inputs, outputs, or evaluation criteria."
    )

    st.divider()
    if st.button("🔄 Refresh Data", width='stretch'):
        load_all_workflows.clear()
        st.rerun()

if filtered_pool.empty:
    st.warning(f"No workflows found in category: {selected_category}")
    st.stop()

# ==========================================
# 4. Main View: Category-Restricted Selection
# ==========================================
st.subheader(f"📋 Workflow List: {selected_category}")
st.caption("Select one or more workflows from the same category for metric comparison. Detailed RAM-level tabs require exactly two selected workflows.")

search_query = st.text_input("🔍 Search Workflow", placeholder="Search by name or author...")
if search_query:
    filtered_pool = filtered_pool[
        filtered_pool['Workflow_Name'].astype(str).str.contains(search_query, case=False, na=False) |
        filtered_pool['Author'].astype(str).str.contains(search_query, case=False, na=False)
    ].reset_index(drop=True)

column_order = [
    "Source", "Workflow_Category", "Workflow_Name", "Author",
    "Number_of_Samples(Throughput)", "Turnaround_Time(h)", "Total_Cost(USD)", "EPI", "aEPI_num"
]
column_order = [c for c in column_order if c in filtered_pool.columns]

config = {
    "Source": st.column_config.TextColumn("Source"),
    "Workflow_Category": st.column_config.TextColumn("Category"),
    "Workflow_Name": st.column_config.TextColumn("Workflow Name"),
    "Author": st.column_config.TextColumn("Author"),
    "Number_of_Samples(Throughput)": st.column_config.NumberColumn("Throughput", format="%d"),
    "Turnaround_Time(h)": st.column_config.NumberColumn("TAT (h)", format="%.2f"),
    "Total_Cost(USD)": st.column_config.NumberColumn("Cost (USD)", format="%.2f"),
    "EPI": st.column_config.NumberColumn("EPI", format="%.2f"),
    "aEPI_num": st.column_config.NumberColumn("aEPI", format="%.2f"),
}

selection_event = st.dataframe(
    filtered_pool,
    column_order=column_order,
    column_config=config,
    width='stretch',
    hide_index=True,
    on_select="rerun",
    selection_mode="multi-row"
)

selected_indices = selection_event.selection.rows

# ==========================================
# 5. Analytics Visualization
# ==========================================
if not selected_indices:
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.info("💡 **Please select one or more workflows from the table above to view metric comparisons.**")
    st.stop()

# Summary comparison can include any number of workflows.
# Detailed RAM-level, breakdown, equipment, and consumable analyses remain pairwise.
compare_df = filtered_pool.iloc[selected_indices].copy().reset_index(drop=True)
pairwise_ready = len(compare_df) == 2

if pairwise_ready:
    step_df = build_stepwise_dataframe(compare_df)
    material_df = build_material_dataframe(compare_df)
    equipment_df = build_equipment_dataframe(step_df)
else:
    step_df = pd.DataFrame()
    material_df = pd.DataFrame()
    equipment_df = pd.DataFrame()

st.divider()
st.subheader("📈 Category-based Comparison")
st.caption(f"Selected category: **{selected_category}**")

summary_records = []
for _, row in compare_df.iterrows():
    summary_records.append({
        "Workflow": row['Workflow_Label'],
        "Throughput": int(to_float(row.get('Number_of_Samples(Throughput)', 0))),
        "TAT (h)": to_float(row.get('Turnaround_Time(h)', 0)),
        "Operation Time (h)": to_float(row.get('Operation_Time(h)', 0)),
        "Hands-on Time (h)": to_float(row.get('Hands_on_Time(h)', 0)),
        "Total Cost (USD)": to_float(row.get('Total_Cost(USD)', 0)),
        "Material Cost (USD)": to_float(row.get('Material_Cost(USD)', 0)),
        "Labor Cost (USD)": to_float(row.get('Labor_Cost(USD)', 0)),
        "EPI": to_float(row.get('EPI', 0)),
        "aEPI": row.get('aEPI_num', math.nan),
        "Empirical Success Rate": row.get('Empirical_Success_Rate_num', math.nan),
    })
summary_df = pd.DataFrame(summary_records)

show_aepi = summary_df['aEPI'].notna().any()
if not show_aepi:
    st.caption("aEPI is optional and is shown as N/A when empirical success-rate data were not saved.")

if pairwise_ready:
    st.caption("Detailed RAM-level tabs use the two selected workflows as the pairwise comparison set.")
else:
    st.info(
        "Summary Comparison supports multiple selected workflows. "
        "Select exactly two workflows to enable RAM Composition, Time & Cost Breakdown, and Equipment & Consumables tabs."
    )

st.dataframe(
    summary_df,
    hide_index=True,
    width='stretch',
    column_config={
        "TAT (h)": st.column_config.NumberColumn(format="%.2f"),
        "Operation Time (h)": st.column_config.NumberColumn(format="%.2f"),
        "Hands-on Time (h)": st.column_config.NumberColumn(format="%.2f"),
        "Total Cost (USD)": st.column_config.NumberColumn(format="$%,.2f"),
        "Material Cost (USD)": st.column_config.NumberColumn(format="$%,.2f"),
        "Labor Cost (USD)": st.column_config.NumberColumn(format="$%,.2f"),
        "EPI": st.column_config.NumberColumn(format="%.2f"),
        "aEPI": st.column_config.NumberColumn(format="%.2f"),
        "Empirical Success Rate": st.column_config.NumberColumn(format="%.4f"),
    }
)

summary_tab, comp_tab, breakdown_tab, resource_tab = st.tabs([
    "🏁 Summary Comparison",
    "🧬 RAM Composition",
    "⏱️ Time & Cost Breakdown",
    "🤖 Equipment & Consumables"
])

# ==========================================
# Tab 1. Summary Comparison
# ==========================================
with summary_tab:
    chart_cols = st.columns(4 if show_aepi else 3)

    with chart_cols[0]:
        st.markdown("#### ⏱️ TAT")
        fig_tat = px.bar(compare_df, x='Workflow_Label', y='Turnaround_Time(h)', color='Workflow_Label', text_auto='.2f', template="plotly_white")
        fig_tat.update_layout(showlegend=False, xaxis_title=None, yaxis_title="h", margin=dict(t=30, b=10, l=10, r=10), height=320)
        st.plotly_chart(fig_tat, width='stretch', key='summary_tat_chart')

    with chart_cols[1]:
        st.markdown("#### 💰 Total Cost")
        fig_cost = px.bar(compare_df, x='Workflow_Label', y='Total_Cost(USD)', color='Workflow_Label', text_auto='.2f', template="plotly_white")
        fig_cost.update_layout(showlegend=False, xaxis_title=None, yaxis_title="USD", margin=dict(t=30, b=10, l=10, r=10), height=320)
        st.plotly_chart(fig_cost, width='stretch', key='summary_cost_chart')

    with chart_cols[2]:
        st.markdown("#### 💎 EPI")
        fig_epi = px.bar(compare_df, x='Workflow_Label', y='EPI', color='Workflow_Label', text_auto='.2f', template="plotly_white")
        fig_epi.update_layout(showlegend=False, xaxis_title=None, yaxis_title="EPI", margin=dict(t=30, b=10, l=10, r=10), height=320)
        st.plotly_chart(fig_epi, width='stretch', key='summary_epi_chart')

    if show_aepi:
        with chart_cols[3]:
            st.markdown("#### 🧪 aEPI")
            fig_aepi = px.bar(compare_df.dropna(subset=['aEPI_num']), x='Workflow_Label', y='aEPI_num', color='Workflow_Label', text_auto='.2f', template="plotly_white")
            fig_aepi.update_layout(showlegend=False, xaxis_title=None, yaxis_title="aEPI", margin=dict(t=30, b=10, l=10, r=10), height=320)
            st.plotly_chart(fig_aepi, width='stretch', key='summary_aepi_chart')

    st.divider()
    st.markdown("#### 💡 Key Comparison Insights")
    try:
        best_epi = compare_df.loc[compare_df['EPI'].idxmin()]
        fastest = compare_df.loc[compare_df['Turnaround_Time(h)'].idxmin()]
        cheapest = compare_df.loc[compare_df['Total_Cost(USD)'].idxmin()]

        insight_cols = st.columns(4 if show_aepi else 3)
        with insight_cols[0]:
            st.success(f"**🏆 Lowest EPI**\n\n**{best_epi['Workflow_Name']}**\n\nEPI = **{best_epi['EPI']:.2f}**")
        with insight_cols[1]:
            st.info(f"**⚡ Fastest**\n\n**{fastest['Workflow_Name']}**\n\nTAT = **{fastest['Turnaround_Time(h)']:.2f} h**")
        with insight_cols[2]:
            st.warning(f"**💸 Lowest Cost**\n\n**{cheapest['Workflow_Name']}**\n\nCost = **{cheapest['Total_Cost(USD)']:,.2f} USD**")

        if show_aepi:
            aepi_df = compare_df.dropna(subset=['aEPI_num'])
            if not aepi_df.empty:
                best_aepi = aepi_df.loc[aepi_df['aEPI_num'].idxmin()]
                with insight_cols[3]:
                    st.success(f"**🧪 Lowest aEPI**\n\n**{best_aepi['Workflow_Name']}**\n\naEPI = **{best_aepi['aEPI_num']:.2f}**")
    except Exception:
        st.info("Insufficient data for automated insights.")

# ==========================================
# Tab 2. RAM Composition
# ==========================================
with comp_tab:
    st.markdown("### 🧬 Changed RAM Comparison")
    if not pairwise_ready:
        st.info(
            "RAM Composition is a pairwise analysis. Select exactly two workflows to identify changed RAMs."
        )
    elif step_df.empty:
        st.info("No step-level RAM data are available for the selected workflows.")
    else:
        st.caption(
            "Only shared RAMs with changed time or cost are shown below, so differences are visible at a glance. "
            "The full step alignment matrix is available in the expander."
        )

        ram_delta_df_for_cards = build_ram_delta_dataframe(step_df)
        changed_ram_ids = set()
        ram_min_time = {}
        ram_min_cost = {}
        if not ram_delta_df_for_cards.empty:
            changed_rows = ram_delta_df_for_cards[
                (ram_delta_df_for_cards['Δ Time (h)'].abs() > 1e-9)
                | (ram_delta_df_for_cards['Δ Cost (USD)'].abs() > 1e-9)
            ]
            changed_ram_ids = set(changed_rows['RAM ID'].astype(str).tolist())
            for _, r in ram_delta_df_for_cards.iterrows():
                ram_min_time[str(r['RAM ID'])] = to_float(r.get('Min Time (h)', 0))
                ram_min_cost[str(r['RAM ID'])] = to_float(r.get('Min Cost (USD)', 0))

        total_shared = len(ram_delta_df_for_cards) if not ram_delta_df_for_cards.empty else 0
        st.info(
            f"Changed shared RAMs detected: **{len(changed_ram_ids)} / {total_shared}**"
            if total_shared else
            "No shared RAMs were detected among the selected workflows."
        )

        if not changed_ram_ids:
            st.success(
                "No changed shared RAMs were detected. The selected workflows have identical step-level time and cost values for shared RAMs."
            )
        else:
            wf_groups = list(step_df.sort_values(['Workflow', 'Step']).groupby('Workflow', sort=False))
            seq_cols = st.columns(2)
            for col, (wf, group) in zip(seq_cols, wf_groups[:2]):
                changed_group = group[group['RAM ID'].astype(str).isin(changed_ram_ids)].sort_values('Step')
                with col:
                    st.markdown(f"#### 🧬 {short_workflow_name(wf, 60)}")
                    if changed_group.empty:
                        st.caption("No changed shared RAMs in this workflow.")
                        continue

                    for _, step_row in changed_group.iterrows():
                        ram_id = str(step_row['RAM ID'])
                        raw_step = step_row.get('Raw Step', {}) if isinstance(step_row.get('Raw Step', {}), dict) else {}
                        in_disp, out_disp = io_display_from_step(raw_step)

                        time_delta = step_row['Total Time (h)'] - ram_min_time.get(ram_id, step_row['Total Time (h)'])
                        cost_delta = step_row['Total Cost (USD)'] - ram_min_cost.get(ram_id, step_row['Total Cost (USD)'])

                        badges = []
                        if step_row.get('Is Final Validation RAM', False):
                            badges.append(
                                "<span style='background-color:#DBEAFE; color:#1D4ED8; padding:2px 7px; "
                                "border-radius:999px; font-size:11px; font-weight:600;'>🧪 Final Validation RAM</span>"
                            )
                        badges.append(
                            "<span style='background-color:#FEF3C7; color:#92400E; padding:2px 7px; "
                            "border-radius:999px; font-size:11px; font-weight:600;'>Changed</span>"
                        )
                        badge_html = " ".join(badges)

                        with st.container(border=True):
                            st.markdown(
                                f"**Step {int(step_row['Step'])}: {ram_id} - {step_row['RAM Name']}** {badge_html}",
                                unsafe_allow_html=True
                            )
                            c1, c2 = st.columns(2)
                            c1.markdown(f"**Time:** {step_row['Total Time (h)']:.2f} h")
                            c2.markdown(f"**Cost:** ${step_row['Total Cost (USD)']:,.2f}")
                            st.caption(
                                f"🤖 Robot: {short_workflow_name(step_row.get('Robot', 'None'), 34)} | "
                                f"🛠️ Device: {short_workflow_name(step_row.get('Functional Device', 'None'), 34)}"
                            )

                            delta_parts = []
                            ram_delta_row = ram_delta_df_for_cards[ram_delta_df_for_cards['RAM ID'].astype(str) == ram_id]
                            if not ram_delta_row.empty:
                                delta_info = ram_delta_row.iloc[0]
                                if abs(delta_info['Δ Time (h)']) > 1e-9:
                                    delta_parts.append(
                                        f"Time: {delta_info['Min Time (h)']:.2f} h → {delta_info['Max Time (h)']:.2f} h "
                                        f"(Δ +{delta_info['Δ Time (h)']:.2f} h)"
                                    )
                                if abs(delta_info['Δ Cost (USD)']) > 1e-9:
                                    delta_parts.append(
                                        f"Cost: ${delta_info['Min Cost (USD)']:,.2f} → ${delta_info['Max Cost (USD)']:,.2f} "
                                        f"(Δ +${delta_info['Δ Cost (USD)']:,.2f})"
                                    )

                            if delta_parts:
                                st.warning("Pairwise difference: " + " | ".join(delta_parts), icon="🔎")

                            st.caption(f"In: {in_disp} | Out: {out_disp}")

        with st.expander("View full step alignment matrix"):
            composition_matrix = step_df.pivot_table(
                index="Step",
                columns="Workflow",
                values="Display Label",
                aggfunc="first"
            ).sort_index().fillna("—")
            st.dataframe(composition_matrix, width='stretch')

        with st.expander("View shared and workflow-specific RAM summary"):
            workflow_ram_sets = {
                wf: set(group['RAM ID'].dropna().astype(str).tolist())
                for wf, group in step_df.groupby('Workflow')
            }
            if workflow_ram_sets:
                shared_rams = set.intersection(*workflow_ram_sets.values()) if len(workflow_ram_sets) > 1 else list(workflow_ram_sets.values())[0]
                st.info(f"**Shared RAM IDs:** {', '.join(sorted(shared_rams)) if shared_rams else 'None'}")

                step_count_df = step_df.groupby('Workflow').agg(
                    Steps=('Step', 'max'),
                    Unique_RAMs=('RAM ID', 'nunique')
                ).reset_index()
                st.dataframe(step_count_df, hide_index=True, width='stretch')

                unique_records = []
                for wf, ram_set in workflow_ram_sets.items():
                    other_rams = set.union(*(s for k, s in workflow_ram_sets.items() if k != wf)) if len(workflow_ram_sets) > 1 else set()
                    unique = sorted(ram_set - other_rams)
                    unique_records.append({"Workflow": wf, "Workflow-specific RAM IDs": ", ".join(unique) if unique else "None"})
                st.dataframe(pd.DataFrame(unique_records), hide_index=True, width='stretch')

# ==========================================
# Tab 3. Time & Cost Breakdown
# ==========================================
with breakdown_tab:
    if not pairwise_ready:
        st.info("Time & Cost Breakdown is a pairwise analysis. Select exactly two workflows to use this tab.")
    else:
        st.markdown("### ⏱️ Time and Cost Breakdown")
        if step_df.empty:
            st.info("No step-level timing or cost data are available for the selected workflows.")
        else:
            st.markdown("#### 🚨 Bottleneck RAMs")
            bottleneck_records = []
            for wf, group in step_df.groupby('Workflow'):
                t_bn = group.loc[group['Total Time (h)'].idxmax()]
                c_bn = group.loc[group['Total Cost (USD)'].idxmax()]
                bottleneck_records.append({
                    "Workflow": wf,
                    "Time Bottleneck RAM": f"{t_bn['RAM ID']} - {t_bn['RAM Name']}",
                    "Time Share (%)": t_bn['Time Share (%)'],
                    "Cost Bottleneck RAM": f"{c_bn['RAM ID']} - {c_bn['RAM Name']}",
                    "Cost Share (%)": c_bn['Cost Share (%)']
                })

            bottleneck_df = pd.DataFrame(bottleneck_records)
            for row_start in range(0, len(bottleneck_df), 2):
                cols = st.columns(min(2, len(bottleneck_df.iloc[row_start:row_start + 2])))
                for col, (_, r) in zip(cols, bottleneck_df.iloc[row_start:row_start + 2].iterrows()):
                    with col:
                        with st.container(border=True):
                            st.markdown(f"##### {short_workflow_name(r['Workflow'], 55)}")
                            b1, b2 = st.columns(2)
                            b1.markdown(f"**Time bottleneck**  \n{short_workflow_name(r['Time Bottleneck RAM'], 36)}  \n<span style='color:#047857; font-size:12px;'>↑ {r['Time Share (%)']:.1f}% of TAT</span>", unsafe_allow_html=True)
                            b2.markdown(f"**Cost bottleneck**  \n{short_workflow_name(r['Cost Bottleneck RAM'], 36)}  \n<span style='color:#047857; font-size:12px;'>↑ {r['Cost Share (%)']:.1f}% of cost</span>", unsafe_allow_html=True)

            st.divider()
            st.markdown("#### 🔎 Comparable RAM-level Changes")
            st.caption(
                "Only shared RAMs with changed time or cost are highlighted here. This is useful when workflows keep the same RAM identity but change implementation mode, such as automated versus manual execution."
            )

            ram_delta_df = build_ram_delta_dataframe(step_df)
            if ram_delta_df.empty:
                st.info("No shared RAMs were available for RAM-level change comparison.")
            else:
                changed_delta = ram_delta_df[
                    (ram_delta_df['Δ Time (h)'].abs() > 1e-9)
                    | (ram_delta_df['Δ Cost (USD)'].abs() > 1e-9)
                ].copy()

                if changed_delta.empty:
                    st.info("No changed shared RAMs were detected. The selected workflows use shared RAMs with identical step-level time and cost values.")
                else:
                    st.success(f"Changed shared RAMs detected: **{len(changed_delta)} / {len(ram_delta_df)}**")

                    card_df = changed_delta.copy()
                    card_df['Change Score'] = card_df['Δ Time (h)'].abs() + (card_df['Δ Cost (USD)'].abs() / 1000.0)
                    card_df = card_df.sort_values('Change Score', ascending=False).head(6)

                    for _, r in card_df.iterrows():
                        with st.container(border=True):
                            st.markdown(f"##### 🔁 {r['RAM ID']} - {r['RAM Name']}")
                            c_time, c_cost = st.columns(2)
                            with c_time:
                                st.markdown("**Time change**")
                                st.markdown(f"<div style='font-size:28px; font-weight:650; line-height:1.15;'>+{r['Δ Time (h)']:.2f} h</div>", unsafe_allow_html=True)
                                st.markdown(f"<span style='font-size:12px; color:#047857; background:#D1FAE5; padding:3px 7px; border-radius:999px;'>{r['Min Time (h)']:.2f} h → {r['Max Time (h)']:.2f} h</span>", unsafe_allow_html=True)
                                st.caption(f"{short_workflow_name(r['Min Time Workflow'], 40)} → {short_workflow_name(r['Max Time Workflow'], 40)}")
                            with c_cost:
                                st.markdown("**Cost change**")
                                st.markdown(f"<div style='font-size:28px; font-weight:650; line-height:1.15;'>+${r['Δ Cost (USD)']:,.2f}</div>", unsafe_allow_html=True)
                                st.markdown(f"<span style='font-size:12px; color:#047857; background:#D1FAE5; padding:3px 7px; border-radius:999px;'>${r['Min Cost (USD)']:,.2f} → ${r['Max Cost (USD)']:,.2f}</span>", unsafe_allow_html=True)
                                st.caption(f"{short_workflow_name(r['Min Cost Workflow'], 40)} → {short_workflow_name(r['Max Cost Workflow'], 40)}")

            st.divider()
            time_tab, cost_tab = st.tabs(["⏱️ Time composition", "💰 Cost composition"])

            with time_tab:
                st.caption("Pie charts show the within-workflow contribution of each RAM to total turnaround time.")
                wf_groups = list(step_df.groupby('Workflow', sort=False))
                for row_start in range(0, len(wf_groups), 2):
                    cols = st.columns(min(2, len(wf_groups[row_start:row_start + 2])))
                    for col, (wf, group) in zip(cols, wf_groups[row_start:row_start + 2]):
                        with col:
                            st.markdown(f"##### {short_workflow_name(wf, 55)}")
                            chart_df = group[group['Total Time (h)'] > 0].copy()
                            if chart_df.empty:
                                st.info("No positive time values available.")
                            else:
                                chart_df['Chart Label'] = chart_df.apply(lambda r: make_chart_label(r['Step'], r['RAM ID'], r['RAM Name']), axis=1)
                                chart_df['Full Label'] = chart_df.apply(lambda r: f"Step {int(r['Step'])}: {r['RAM ID']} - {r['RAM Name']}", axis=1)
                                fig_time = px.pie(
                                    chart_df,
                                    values='Total Time (h)',
                                    names='Chart Label',
                                    hole=0.5,
                                    title="Time Distribution",
                                    custom_data=['Full Label', 'Time Share (%)']
                                )
                                fig_time.update_layout(showlegend=True, margin=dict(t=45, b=10, l=10, r=10), height=340)
                                fig_time.update_traces(
                                    hovertemplate="<b>%{label}</b><br>Total Time: %{value:.2f} h<br>Share: %{percent:.1%}<extra></extra>",
                                    sort=False
                                )
                                st.plotly_chart(fig_time, width='stretch', key=f'time_breakdown_{safe_key(wf)}')

            with cost_tab:
                st.caption("Pie charts show the within-workflow contribution of each RAM to total cost.")
                wf_groups = list(step_df.groupby('Workflow', sort=False))
                for row_start in range(0, len(wf_groups), 2):
                    cols = st.columns(min(2, len(wf_groups[row_start:row_start + 2])))
                    for col, (wf, group) in zip(cols, wf_groups[row_start:row_start + 2]):
                        with col:
                            st.markdown(f"##### {short_workflow_name(wf, 55)}")
                            chart_df = group[group['Total Cost (USD)'] > 0].copy()
                            if chart_df.empty:
                                st.info("No positive cost values available.")
                            else:
                                chart_df['Chart Label'] = chart_df.apply(lambda r: make_chart_label(r['Step'], r['RAM ID'], r['RAM Name']), axis=1)
                                chart_df['Full Label'] = chart_df.apply(lambda r: f"Step {int(r['Step'])}: {r['RAM ID']} - {r['RAM Name']}", axis=1)
                                fig_cost_breakdown = px.pie(
                                    chart_df,
                                    values='Total Cost (USD)',
                                    names='Chart Label',
                                    hole=0.5,
                                    title="Cost Distribution",
                                    custom_data=['Full Label', 'Cost Share (%)']
                                )
                                fig_cost_breakdown.update_layout(showlegend=True, margin=dict(t=45, b=10, l=10, r=10), height=340)
                                fig_cost_breakdown.update_traces(
                                    hovertemplate="<b>%{label}</b><br>Total Cost: $%{value:,.2f}<br>Share: %{percent:.1%}<extra></extra>",
                                    sort=False
                                )
                                st.plotly_chart(fig_cost_breakdown, width='stretch', key=f'cost_breakdown_{safe_key(wf)}')


# ==========================================
# Tab 4. Equipment & Consumables
# ==========================================
with resource_tab:
    if not pairwise_ready:
        st.info("Equipment & Consumables comparison is pairwise. Select exactly two workflows to use this tab.")
    else:
        eq_tab, mat_tab = st.tabs(["🤖 Required Equipment", "📦 Consumables"])

        with eq_tab:
            st.markdown("### 🤖 Required Robots and Functional Devices")
            if equipment_df.empty:
                st.info("No equipment metadata are available in the selected workflow steps.")
            else:
                equipment_summary = equipment_df.groupby(['Workflow', 'Equipment Type'])['Equipment'].apply(
                    lambda x: ", ".join(sorted(set(x)))
                ).reset_index()
                equipment_matrix = equipment_summary.pivot(index='Workflow', columns='Equipment Type', values='Equipment').fillna("None")
                st.dataframe(equipment_matrix, width='stretch')

                all_sets = {
                    wf: set(group['Equipment'].dropna().astype(str).tolist())
                    for wf, group in equipment_df.groupby('Workflow')
                }
                if all_sets:
                    common_equipment = set.intersection(*all_sets.values()) if len(all_sets) > 1 else list(all_sets.values())[0]
                    st.info(f"**Common equipment:** {', '.join(sorted(common_equipment)) if common_equipment else 'None'}")

                    specific_equipment = []
                    for wf, eq_set in all_sets.items():
                        other_eq = set.union(*(s for k, s in all_sets.items() if k != wf)) if len(all_sets) > 1 else set()
                        unique_eq = sorted(eq_set - other_eq)
                        specific_equipment.append({"Workflow": wf, "Workflow-specific equipment": ", ".join(unique_eq) if unique_eq else "None"})
                    st.dataframe(pd.DataFrame(specific_equipment), hide_index=True, width='stretch')

        with mat_tab:
            st.markdown("### 📦 Consumable Cost Drivers")
            if material_df.empty:
                st.info("No consumable metadata are available for the selected workflows.")
            else:
                material_summary = material_df.groupby(['Workflow', 'Material Name'], as_index=False)['Total Price (USD)'].sum()
                material_matrix = material_summary.pivot(index='Material Name', columns='Workflow', values='Total Price (USD)').fillna(0.0)

                st.markdown("#### Workflow-level consumable cost distribution")
                st.caption("Pie charts show the major consumables driving material cost within each workflow. Low-cost items are grouped as Other when needed.")
                wf_material_groups = list(material_summary.groupby('Workflow', sort=False))
                for row_start in range(0, len(wf_material_groups), 2):
                    cols = st.columns(min(2, len(wf_material_groups[row_start:row_start + 2])))
                    for col, (wf, group) in zip(cols, wf_material_groups[row_start:row_start + 2]):
                        with col:
                            st.markdown(f"##### {short_workflow_name(wf, 55)}")
                            chart_df = make_top_with_other(group, 'Material Name', 'Total Price (USD)', top_n=6)
                            chart_df = chart_df[chart_df['Total Price (USD)'] > 0]
                            if chart_df.empty:
                                st.info("No positive consumable costs available.")
                            else:
                                fig_consumable = px.pie(
                                    chart_df,
                                    values='Total Price (USD)',
                                    names='Material Name',
                                    hole=0.5,
                                    title='Consumable Cost Drivers'
                                )
                                fig_consumable.update_layout(showlegend=True, margin=dict(t=45, b=10, l=10, r=10), height=340)
                                fig_consumable.update_traces(
                                    hovertemplate="<b>%{label}</b><br>Cost: $%{value:,.2f}<br>Share: %{percent:.1%}<extra></extra>",
                                    sort=False
                                )
                                st.plotly_chart(fig_consumable, width='stretch', key=f'consumable_pie_{safe_key(wf)}')

                                top_row = chart_df.sort_values('Total Price (USD)', ascending=False).iloc[0]
                                total = chart_df['Total Price (USD)'].sum()
                                share = (top_row['Total Price (USD)'] / total * 100) if total > 0 else 0
                                st.info(
                                    f"Top driver: **{top_row['Material Name']}** "
                                    f"(${top_row['Total Price (USD)']:,.2f}, {share:.1f}%)"
                                )

                st.divider()
                st.markdown("#### 🔎 Consumable Cost Change Highlights")
                st.caption("Only shared consumables whose costs differ across workflows are highlighted here.")
                material_delta_df = build_material_delta_dataframe(material_df)
                if material_delta_df.empty:
                    st.info("No consumable cost changes detected. This means the selected workflows do not share comparable consumables, or no consumable costs differ between them.")
                else:
                    changed_material_delta = material_delta_df[material_delta_df['Δ Cost (USD)'].abs() > 1e-9].copy()
                    if changed_material_delta.empty:
                        st.info("No consumable cost changes detected. Shared consumables exist, but their costs are identical across the selected workflows.")
                    else:
                        top_changed_materials = changed_material_delta.sort_values('Δ Cost (USD)', ascending=False).head(6)
                        st.success(f"Changed shared consumables detected: **{len(changed_material_delta)} / {len(material_delta_df)}**")

                        for _, r in top_changed_materials.iterrows():
                            with st.container(border=True):
                                st.markdown(f"##### 📦 {r['Material Name']}")
                                st.markdown("**Cost change**")
                                st.markdown(f"<div style='font-size:28px; font-weight:650; line-height:1.15;'>+${r['Δ Cost (USD)']:,.2f}</div>", unsafe_allow_html=True)
                                st.markdown(f"<span style='font-size:12px; color:#047857; background:#D1FAE5; padding:3px 7px; border-radius:999px;'>${r['Min Cost (USD)']:,.2f} → ${r['Max Cost (USD)']:,.2f}</span>", unsafe_allow_html=True)
                                st.caption(
                                    f"{short_workflow_name(r['Min Cost Workflow'], 45)} → {short_workflow_name(r['Max Cost Workflow'], 45)}"
                                )

                with st.expander("View consumable cost matrix"):
                    st.dataframe(
                        material_matrix,
                        width='stretch',
                        column_config={col: st.column_config.NumberColumn(format="$%,.2f") for col in material_matrix.columns}
                    )

                with st.expander("View all consumable records"):
                    st.dataframe(
                        material_summary.sort_values(['Workflow', 'Total Price (USD)'], ascending=[True, False]),
                        hide_index=True,
                        width='stretch',
                        column_config={"Total Price (USD)": st.column_config.NumberColumn(format="$%,.2f")}
                    )
