import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import plotly.express as px
import math

# [NOTICE] 2026 Standard Syntax Compliance
pd.set_option('future.no_silent_downcasting', True)

# --- Constants ---
MY_SHEET_URL = st.secrets["connections"]["gsheets"]["spreadsheet"]
conn = st.connection("gsheets", type=GSheetsConnection)


# ==========================================
# 1. Data Loading
# ==========================================

@st.cache_data(ttl=60)
def load_all_workflows():
    try:
        m_db = conn.read(spreadsheet=MY_SHEET_URL, worksheet="Workflow_MasterDB", ttl=0)
        u_db = conn.read(spreadsheet=MY_SHEET_URL, worksheet="Workflow_UserDB", ttl=0)

        if m_db is not None and not m_db.empty: m_db['Source'] = 'Master'
        if u_db is not None and not u_db.empty: u_db['Source'] = 'User'

        combined = pd.concat([m_db, u_db], ignore_index=True).dropna(subset=['Workflow_Name'])
        combined.columns = [c.strip() for c in combined.columns]

        if 'access_code' in combined.columns:
            combined['access_code'] = combined['access_code'].astype(str)

        num_cols = ['Turnaround_Time(h)', 'Total_Cost(USD)', 'EPI', 'Number_of_Samples(Throughput)']
        for col in num_cols:
            if col in combined.columns:
                combined[col] = pd.to_numeric(combined[col].astype(str).str.replace(',', ''), errors='coerce').fillna(0)

        return combined
    except Exception as e:
        st.error(f"Data Load Error: {e}")
        return pd.DataFrame()


df_all = load_all_workflows()

# ==========================================
# 2. UI: Header & Filtering
# ==========================================
st.title("📊 Workflow Comparative Analytics")
st.markdown("Analyze and compare protocol performance metrics to optimize Biofoundry operations.")

if df_all.empty:
    st.warning("No workflow data found. Please create and save a protocol in the Builder first.")
    st.stop()

with st.sidebar:
    st.header("🔍 Filter Registry")
    source_filter = st.multiselect("Database Source", ["Master", "User"], default=["Master", "User"])
    st.divider()
    if st.button("🔄 Refresh Data", width='stretch'):
        st.cache_data.clear()
        st.rerun()

filtered_pool = df_all[df_all['Source'].isin(source_filter)].reset_index(drop=True)

# ==========================================
# 3. Main View: Table-based Selection
# ==========================================
st.subheader("📋 Workflow List")
st.caption("Click rows to select workflows for comparison (Max 5).")

search_query = st.text_input("🔍 Search Workflow", placeholder="Search by name or author...")
if search_query:
    filtered_pool = filtered_pool[
        filtered_pool['Workflow_Name'].str.contains(search_query, case=False, na=False) |
        filtered_pool['Author'].str.contains(search_query, case=False, na=False)
    ]

column_mapping = {
    "Source": "Source",
    "Workflow_Name": "Workflow Name",
    "Number_of_Samples(Throughput)": "Throughput",
    "Turnaround_Time(h)": "TAT (h)",
    "Total_Cost(USD)": "Cost ($)",
    "EPI": "EPI",
    "Author": "Author"
}

config = {
    "Source": st.column_config.TextColumn("Source"),
    "Workflow_Name": st.column_config.TextColumn("Workflow Name"),
    "Number_of_Samples(Throughput)": st.column_config.NumberColumn("Throughput", format="%d"),
    "Turnaround_Time(h)": st.column_config.NumberColumn("TAT (h)", format="%.2f"),
    "Total_Cost(USD)": st.column_config.NumberColumn("Cost ($)", format="%.2f"),
    "EPI": st.column_config.NumberColumn("EPI", format="%.2f"),
}

selection_event = st.dataframe(
    filtered_pool,
    column_order=list(column_mapping.keys()),
    column_config=config,
    width='stretch',
    hide_index=True,
    on_select="rerun",
    selection_mode="multi-row"
)

selected_indices = selection_event.selection.rows

# ==========================================
# 4. Analytics Visualization
# ==========================================
if not selected_indices:
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.info("💡 **Please select multiple protocols from the table above to visualize comparison.**")

elif len(selected_indices) > 5:
    st.error("⚠️ **Selection Limit Reached.** Please select up to **5** workflows for optimal visualization.")

else:
    compare_df = filtered_pool.iloc[selected_indices].copy()

    st.divider()
    st.subheader("📈 Key Metrics Comparison")

    # --- Part A: Bar Charts ---
    c1, c2, c3 = st.columns(3)

    with c1:
        st.markdown("#### ⏱️ Turnaround Time (h)")
        fig_tat = px.bar(compare_df, x='Workflow_Name', y='Turnaround_Time(h)',
                         color='Workflow_Name', text_auto='.2f', template="plotly_white")
        fig_tat.update_layout(showlegend=False, xaxis_title=None, margin=dict(t=30, b=10, l=10, r=10))
        st.plotly_chart(fig_tat, width='stretch')

    with c2:
        st.markdown("#### 💰 Total Cost (USD)")
        fig_cost = px.bar(compare_df, x='Workflow_Name', y='Total_Cost(USD)',
                          color='Workflow_Name', text_auto='.2f', template="plotly_white")
        fig_cost.update_layout(showlegend=False, xaxis_title=None, margin=dict(t=30, b=10, l=10, r=10))
        st.plotly_chart(fig_cost, width='stretch')

    with c3:
        st.markdown("#### 💎 EPI")
        fig_epi = px.bar(compare_df, x='Workflow_Name', y='EPI',
                         color='Workflow_Name', text_auto='.2f', template="plotly_white")
        fig_epi.update_layout(showlegend=False, xaxis_title=None, margin=dict(t=30, b=10, l=10, r=10))
        st.plotly_chart(fig_epi, width='stretch')

    # --- Part B: Strategic Insights ---
    st.divider()
    st.subheader("💡 Strategic Insights")
    try:
        best_epi = compare_df.loc[compare_df['EPI'].idxmin()]
        fastest = compare_df.loc[compare_df['Turnaround_Time(h)'].idxmin()]
        cheapest = compare_df.loc[compare_df['Total_Cost(USD)'].idxmin()]

        i1, i2, i3 = st.columns(3)
        with i1:
            st.success(
                f"**🏆 Optimal Choice**\n\n**{best_epi['Workflow_Name']}**\n\nLowest Experiment Price Index **({best_epi['EPI']:.2f})**. Ideal balance of speed and budget per unit.")
        with i2:
            st.info(
                f"**⚡ Speed Leader**\n\n**{fastest['Workflow_Name']}**\n\nMinimum Turnaround Time at **{fastest['Turnaround_Time(h)']:.2f} h**. Best for time-sensitive production.")
        with i3:
            st.warning(
                f"**💸 Budget Leader**\n\n**{cheapest['Workflow_Name']}**\n\nMinimum expenditure at **{cheapest['Total_Cost(USD)']:,.2f} USD**. Most cost-effective protocol for limited funding.")
    except Exception as e:
        st.info("Insufficient data for automated insights.")