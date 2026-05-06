import streamlit as st
import base64
import os

# 1. Page Configuration
st.set_page_config(
    page_title="User Guide - Biofoundry Architect",
    page_icon="📖",
    layout="wide"
)

# Helper function to encode local images to Base64
def get_base64_image(image_path):
    if os.path.exists(image_path):
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    return None

# Helper function to render a stylized card containing the centered Base64 image
def render_image_card(image_path, caption, max_width=800):
    img_base64 = get_base64_image(image_path)
    if img_base64:
        st.markdown(f"""
            <div style="
                background-color: white; 
                padding: 20px; 
                border-radius: 25px; 
                box-shadow: 0 10px 25px rgba(0,0,0,0.1);
                margin: 25px auto;
                width: fit-content;
                display: flex;
                justify-content: center;
                align-items: center;
            ">
                <img src="data:image/png;base64,{img_base64}" style="width: 100%; max-width: {max_width}px; height: auto; border-radius: 10px;">
            </div>
            <p style="text-align: center; color: #6b7280; font-size: 0.9rem; margin-top: -15px; margin-bottom: 25px;">
                {caption}
            </p>
        """, unsafe_allow_html=True)
    else:
        st.error(f"Image file not found at path: {image_path}")

st.title("📖 User Guide")
st.markdown("This guide provides step-by-step instructions on how to use the core features of Biofoundry Architect.")

# ==========================================
# 💡 Prerequisites & Recommendations
# ==========================================
st.info("""
**Before you begin:** Biofoundry Architect is built upon the concept of Robot-Assisted Modules (RAM). 
If you are new to this system, we highly recommend reading about the core architecture first.
""")

# Quick link to the RAM concepts page
st.page_link("pages/Concept_RAM.py", label="Read 'Concept: What is RAM?'", icon="🧩")

st.markdown("""
> 💡 **Note:** The main workspace of Biofoundry Architect is the `Workflow Builder` located at the top of the left sidebar. However, for first-time users, we recommend following this tutorial starting with the `RAM System` to learn how to configure basic modules first.
""")

st.divider()

# ==========================================
# 📌 Anchor to return to the tabs area
# ==========================================
st.markdown("<div id='tabs-top'></div>", unsafe_allow_html=True)

# 2. Section Separation using Tabs
tab1, tab2, tab3 = st.tabs(["1. Access Code & RAM Setup", "2. Workflow Builder", "3. Workflow Analytics"])

# HTML/CSS style for the 'Back to Tabs' button
back_to_top_html = """
<div style="text-align: center; margin-top: 40px; margin-bottom: 20px;">
    <a href="#tabs-top" target="_self" style="display: inline-block; padding: 8px 16px; background-color: #F1F5F9; color: #3B82F6; border-radius: 8px; text-decoration: none; font-weight: 600; font-size: 14px; transition: background-color 0.2s ease;">
        ⬆️ Back to Tabs
    </a>
</div>
"""

with tab1:
    st.header("🔑 0. Access Code & Quota System")
    st.markdown("""
    This platform employs an **Access Code–based permission system** to manage data accessibility, editing rights, and cloud-level security without requiring personal user accounts or forced registration.
    """)

    col_auth1, col_auth2 = st.columns(2)

    with col_auth1:
        with st.container(border=True):
            st.markdown("### 👑 Master Code")
            st.markdown("""
            The administrator holds a universal **Master Code**, which grants full permissions across the entire platform.
            * **Absolute Authority**: It acts as a master key with all permissions.
            * **Administrative Oversight**: Grants management and curation authority over data stored by other sessions.
            """)

    with col_auth2:
        with st.container(border=True):
            st.markdown("### 👤 Personal Access Codes")
            st.markdown("""
            Users may request a personal **Access Code** from the administrator via email.
            * **Ownership Lock**: Restricts editing and deletion rights exclusively to the creator of the configuration.
            * **Security**: Protects your configured datasets and configurations from being accidentally modified or corrupted by other concurrent sessions.
            """)

    st.markdown("#### 📈 Dynamic Storage Quotas")
    st.markdown("""
    The administrator can dynamically define storage quotas (the maximum number of allowed stored items) per Access Code. 
    Premium or privileged codes may be configured to allow unlimited data storage for large-scale operations.
    """)

    st.warning("""
    **⚠️ Default Session Quota (Code-Free Sessions)** Users operating without an Access Code are subject to strict default storage limits:
    * **Strict limit**: Capped at a maximum of **5 entries** each for RAMs, Workflows, Robots, Devices, and Vessels.
    * **Data Vulnerability**: Code-free saved entries are unprotected and can be modified or deleted by *any* user, raising the risk of data corruption or loss. 

    Obtaining a dedicated Access Code is **strongly recommended** for any non-testing or production use to guarantee dataset isolation.
    """)

    st.divider()

    st.header("🧪 1. RAM Configuration & Setup")
    st.markdown("""
    The RAM configuration interface is structured into **three sequential steps** to ensure data completeness, reproducibility, and cost traceability.
    """)

    # Sub-tabs for Steps 1, 2, 3, and 4 inside the RAM Setup guide
    step1, step2, step3, step4 = st.tabs([
        "Step 1: Setup & Hardware",
        "Step 2: Substance I/O",
        "Step 3: Economics & Materials",
        "Curation: Database & Editor"
    ])

    # --- STEP 1 ---
    with step1:
        st.subheader("Step 1: Configuration & Hardware Setup")

        with st.expander("📂 Template Import (Optional)", expanded=False):
            st.markdown("""
            Existing RAM entries from the MasterDB or UserDB can be used as templates to accelerate setup. 
            When a template is selected and loaded via the "Load Selected Template" button, **all Step 1 fields are automatically populated** except for the Access Code.
            """)

        # [Image 1] - Centered Base64 card for Step 1 Overview
        render_image_card(
            "assets/step1_setup.png",
            caption="Step 1 Interface: Template Import, Core Fields, and Hardware Setup",
            max_width=750
        )

        st.markdown("#### 🏷️ RAM ID & Naming Convention")
        st.markdown("""
        The **RAM ID** consists of an alphabetical prefix (e.g., A, B, Z). Beyond Z, the system extends sequentially (AA, AB, and so on).
        """)

        col_rule1, col_rule2 = st.columns(2)
        with col_rule1:
            st.info("""
            **🧬 Identity Rule** RAMs sharing an **identical experimental architecture**—defined strictly by using the same robot, the same functional devices, and sharing an identical or highly similar process action configuration—are assigned the **same RAM ID prefix**.
            """)
        with col_rule2:
            st.success("""
            **🌿 Derivative RAMs** If the hardware configuration is identical but variables such as input/output composition, experimental purpose, or sample capacity differ, the entry is classified as a **derivative RAM**. 
            * A three-digit suffix is appended to the parent prefix (e.g., `A-002`, `A-003`).
            * The original parent RAM conceptually corresponds to the first instance (`-001`) but is displayed as a clean, single-letter identifier (e.g., `A`).
            """)

        st.markdown("""
        * **Auto-numbering**: When a prefix is entered in the *RAM ID* field, the system automatically query-scans the database and suggests the next available identifier (e.g., `B-004`), minimizing manual tracking errors. You only need to type the prefix itself.
        * **Name**: State the name of the process step (ideally matching or highly similar to your experimental procedure).
        * **Purpose**: Provide a concise description of the objective of using this module.
        """)

        # [Image 2] - Centered Base64 card for ID Suggestion close-up
        render_image_card(
            "assets/step1_id_suggestion.png",
            caption="RAM ID Entry Auto-Numbering Suggestion System",
            max_width=900
        )

        st.markdown("#### 🤖 Hardware Configuration & Execution Logic")
        st.markdown("""
        Users define process execution logic through selected **Process Actions**:
        * **Colony Picking**: Automated selection and harvesting of colonies from agar plates.
        * **Liquid Transfer**: Liquid handling operations including transferring, mixing, separating, and aliquotting.
        * **Labware Transfer**: Physical movement of vessels (e.g., microplates) using robotic gripping systems.

        Compatible robots and functional devices can be selected from the registry. If a required device or robot is missing, it can be defined dynamically via the **\"+ New\"** popover next to the dropdowns.
        """)

    # --- STEP 2 ---
    with step2:
        st.subheader("Step 2: Substance I/O")
        st.markdown("""
        This step defines the physical substances and laboratory vessels passing through the RAM. You can import existing I/O templates to reduce setup time.

        * **Minimum Requirement**: At least **one Input** and **one Output** substance must be defined in the editor table to proceed to the next step.
        """)

        # [Image 3] - Centered Base64 card for Empty I/O Table Setup
        render_image_card(
            "assets/step2_io_empty.png",
            caption="Step 2 Interface: Substance Input & Output Entry Rows",
            max_width=750
        )

        st.info("""
        **🏷️ The Essential Flag (Ess.)** The **Essential** checkbox identifies substances that define the core transformation of the process.

        * *Example (DNA Purification)*: 
            * **\"Amplified DNA\"** (Input) and **\"Purified DNA\"** (Output) are marked as **Essential** because they represent the core transformation outcome.
            * Auxiliary reagents (e.g., wash buffers, ethanol, magnetic beads) are necessary to run the process but are not marked as Essential since they do not define the identity of the product transformation.
        """)

        # [Image 4] - Centered Base64 card for Filled I/O Table Example
        render_image_card(
            "assets/step2_io_filled.png",
            caption="Substance Configuration Table with Essential Flags Applied",
            max_width=750
        )

        st.markdown("""
        * **Vessel Definition**: If a required labware vessel format is not available in the dropdown options, new entries can be added on-the-fly via the **\"+\"** popover next to the Vessel Class option.
        * **Back Navigation**: Use the **\"Back to Step 1\"** button to safely return and make corrections without losing your entered data.
        """)

    # --- STEP 3 ---
    with step3:
        st.subheader("Step 3: Economics & Materials")
        st.markdown("""
        This step defines the temporal, capacity, and material profiles required for the economic modeling of the RAM.
        """)

        # [Image 5] - Centered Base64 card for Economics step 3 overview
        render_image_card(
            "assets/step3_economics.png",
            caption="Step 3 Interface: Runtime Parameter, Cost KPI Dashboard, and BOM Editor",
            max_width=750
        )

        col_econ1, col_econ2 = st.columns(2)
        with col_econ1:
            st.markdown("#### 📊 Capacity & Time Components")
            st.markdown("""
            * **Sample Capacity**: Standardized in multiples of **96 samples** to align with high-throughput automation standards. Calculations assume a standard minimum batch size of 96.
            * **Operation Time**: Total automated run execution time from system start to completion.
            * **Hands-on Time**: Manual labor time required prior to execution (e.g., reagent preparation, system setup, labware loading).
            """)
        with col_econ2:
            st.markdown("#### 💸 Labor Cost")
            st.markdown("""
            Labor cost is calculated automatically based on your entered Hands-on Time.
            * **Rate**: Calculated using a fixed rate of **37.5 USD/hour**.
            * **Formula Base**: Modeled on a standard 40-hour workweek with a weekly wage of $1,500 USD.
            """)

        st.markdown("---")
        st.markdown("#### 📦 Bill of Materials (BOM)")
        st.markdown("""
        List the reagents, consumables, and disposable kits required for a single batch run.

        * **Strict Exclusion**: Capital equipment (such as robots, grippers, or functional thermocyclers) must be excluded from the BOM; list **only consumables**.
        * **Supported Units**: `rxn` (reaction), `ea` (each/item), `uL`, and `mL`.
        """)

        with st.expander("🔢 Price Calculator (Price Calc) Guide", expanded=True):
            st.markdown("""
            For bulk-purchased consumables, the unit price can be easily derived using the **Price Calc** popover:

            1. Enter the **Total Purchase Price (USD)** of the bulk package.
            2. Enter the **Number of Packs** and **Qty per Pack** (total units provided in the purchase).
            3. Click **\"Apply\"** to automatically calculate the unit cost and insert it into the *Unit Price* field.

            *Example*: If a PCR Kit costs **$100.00 USD** and contains **100 reactions**, the calculator outputs **$1.00 USD/rxn**, which is automatically mapped as your Unit Price.
            """)

        # [Image 6] - Centered Base64 card for Price Calc popover details
        render_image_card(
            "assets/step3_price_calc.png",
            caption="Using the Popover Price Calculator to derive Unit Price",
            max_width=1000
        )

        st.markdown("""
        #### 💾 Finalization & Cloud Commit
        Once all fields are filled, review the real-time **Metrics Dashboard** displaying:
        * **Total Time** (Operation Time + Hands-on Time)
        * **Total Cost** (Labor Cost + Material Cost)

        Click **\"Save & Commit RAM\"** to run the security validation, check your storage quota, and commit the configured RAM safely to the cloud database.
        """)

    # --- STEP 4 ---
    with step4:
        st.subheader("Curation: Database & Editor")
        st.markdown("""
        The **RAM Database** and **RAM Editor** act as the central repository and curation engine of the platform, enabling researchers to search, inspect, and update stored modules as laboratory specifications evolve.
        """)

        st.markdown("#### 🔍 Searching & Filtering Configurations")
        st.markdown("""
        * **Targeted Search**: Locate specific configurations instantly by typing part of the RAM ID or RAM Name into the search bar.
        * **Data Source Toggles**: Filter configurations based on whether they belong to the curated **MasterDB** or the user-defined **UserDB**.
        * **Action Filters**: Isolate modules by specific process actions (e.g., *Liquid Transfer*, *Colony Picking*, or *Labware Transfer*).
        * **Cache Sync (Force Refresh)**: If a newly configured RAM does not immediately appear in the list, click the blue **Sync/Refresh button** next to the Action Filter to clear the cache and force a live pull from the cloud database.
        """)

        # [Image 7] - Centered Base64 card for Database Filters (Docx Image 2)
        render_image_card(
            "assets/ram_db_filters.png",
            caption="RAM Database: Multi-parameter filtering and refresh system",
            max_width=800
        )

        st.markdown("#### 🔬 Detailed View & Metadata Inspection")
        st.markdown("""
        Clicking on any row within the RAM List expands a comprehensive, interactive **RAM Details** panel below:
        * **Unified Metrics**: Review the standard sample capacity, total operation/hands-on time, and overall calculated RAM cost.
        * **Physical Profiles**: Inspect the configured hardware actions, compatible robots, auxiliary functional devices, and complete Substance I/O and BOM tables.
        """)

        # [Image 8] - Centered Base64 card for Database Details (Docx Image 3)
        render_image_card(
            "assets/ram_db_details.png",
            caption="Expanded RAM Details dashboard showing consolidated metrics and substances",
            max_width=800
        )

        st.markdown("#### 🔐 Administrative Access & Security")
        st.markdown("""
        To prevent accidental modification or unauthorized data loss, the editing workspace is protected by a security gate:
        1. Scroll to the bottom of the **RAM Details** panel and expand the **Administrative Access** fold-out block.
        2. Enter the **Access Code** that was originally defined when configuring this RAM.
        3. Click **Verify & Open Editor** to authenticate and unlock the edit options. 
        """)

        # [Image 9] - Centered Base64 card for Admin Gate Prompt (Docx Image 4)
        render_image_card(
            "assets/ram_admin_access.png",
            caption="Administrative Access verification gate protecting the configuration",
            max_width=500
        )

        st.markdown("#### ⚠️ Editor Pre-selection Requirement")
        st.warning("""
        **Context-Dependent Workspace Access:**
        Please note that the RAM Editor cannot be accessed directly without an active module selection. 
        If a user attempts to navigate straight to the RAM Editor page without selecting a target RAM from the database first, the system will display a warning banner stating **'No RAM selected. Please select from RAM DB.'** and block editing until a valid module is loaded.
        """)

        # [Image 10] - Centered Base64 card for Editor No-Selection Warning (Standalone Image)
        render_image_card(
            "assets/ram_editor_no_selection.png",
            caption="Warning banner displayed when attempting to access the Editor directly without selecting a RAM",
            max_width=800
        )

        st.markdown("#### 🛠️ Curation & Editing in the RAM Editor")
        st.markdown("""
        Once authorized, you will be redirected to the dedicated **RAM Editor** workspace, which mirrors the Step 1, 2, and 3 configurations:
        * **Metadata Update**: Edit basic parameters (e.g., RAM Name or Purpose) and click **Update Metadata Above** to apply them to the metadata layer.
        """)

        # [Image 11] - Centered Base64 card for Editor Metadata (Docx Image 1 / Image 5)
        render_image_card(
            "assets/ram_editor_header.png",
            caption="Curation Workspace: Basic metadata and purpose editing card",
            max_width=800
        )

        st.markdown("""
        * **Hardware & Substance Modification**: Adjust compatible robotic units, functional devices, and edit Substance I/O rows in real-time.
        * **Dynamic Re-modeling**: Update the Bill of Materials (BOM) or adjust operation/preparation times to re-evaluate economic metrics.
        * **Destructive Deletion**: If a module is no longer valid or physically available in your laboratory architecture, expand the **Delete Module** dropdown in the top-right corner to permanently purge it from the cloud database.
        """)

        # [Image 12] - Centered Base64 card for Editor Full Layout (Docx Image 6)
        render_image_card(
            "assets/ram_editor_full.png",
            caption="The complete RAM Editor curation and lifecycle management workspace",
            max_width=800
        )

    # Scroll up button
    st.markdown(back_to_top_html, unsafe_allow_html=True)

with tab2:
    st.header("Step 2. Building a Workflow")
    st.markdown("""
    In this step, you assemble the actual experimental process (Workflow) by connecting the configured RAMs in a logical sequence.
    """)

    st.info(
        "💡 **Workflow Builder Tutorial is coming soon.** This section will outline how to add, reorder, edit, and validate process sequences.")

    # Scroll up button
    st.markdown(back_to_top_html, unsafe_allow_html=True)

with tab3:
    st.header("Step 3. Analyzing a Workflow")
    st.markdown("""
    Quantitatively evaluate the techno-economic efficiency and identify potential bottlenecks of your designed workflow using EPI indicators.
    """)

    st.info(
        "💡 **Workflow Analytics Tutorial is coming soon.** This section will guide you through interpretative metrics, cost distributions, and EPI metrics.")

    # Scroll up button
    st.markdown(back_to_top_html, unsafe_allow_html=True)