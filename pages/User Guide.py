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
tab0, tab1, tab2, tab3 = st.tabs([
    "🔑 0. Access Code & Quota System",
    "🧪 1. RAM Configuration & Setup",
    "🧱 2. Workflow Builder & Database",
    "📊 3. Workflow Analytics"
])

# HTML/CSS style for the 'Back to Tabs' button
back_to_top_html = """
<div style="text-align: center; margin-top: 40px; margin-bottom: 20px;">
    <a href="#tabs-top" target="_self" style="display: inline-block; padding: 8px 16px; background-color: #F1F5F9; color: #3B82F6; border-radius: 8px; text-decoration: none; font-weight: 600; font-size: 14px; transition: background-color 0.2s ease;">
        ⬆️ Back to Tabs
    </a>
</div>
"""

with tab0:
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
            Users may request a personal **Access Code** from the administrator via email. (skybiofoundry@gmail.com)
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

    # Scroll up button
    st.markdown(back_to_top_html, unsafe_allow_html=True)

with tab1:
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
    st.header("🧱 2. Workflow Builder & Database")
    st.markdown("""
    The **Workflow Builder** and **Workflow Database** provide an integrated workflow design environment where you can construct automated experimental sequences by logically connecting configured RAMs, evaluate their economics, archive results, and model loop-scaling behaviors.
    """)

    st.markdown("### 🧬 Educational Example: DNA Amplification Workflow")
    st.markdown("""
    To demonstrate how to build and validate automated operations, this tutorial utilizes a simplified, pre-configured **DNA Amplification Workflow**.
    * **Objective**: Amplify 96 distinct DNA sequences arrayed in a standard 96-well microplate.
    * **Prerequisite**: The workflow assumes a base throughput of **96 samples** per run to align with standard microplate geometries.
    * **Overview**: The pipeline automates the standard polymerase chain reaction (PCR) sequence from primer preparation to final DNA quantification using **four key steps**:
      1. **Step 1 (Oligo Dilution)**: Rehydrating and diluting synthesized primer stocks.
      2. **Step 2 (Thermal Cycling)**: Mixing primers with templates and reagents, followed by thermocycler-based PCR.
      3. **Step 3 (DNA Clean-up)**: Magnetic-bead or vacuum-filtration-based purification of amplified DNA.
      4. **Step 4 (DNA Measurement)**: UV/Vis absorbance reading to measure final product concentration.
    """)

    st.divider()

    # Sub-tabs inside Tab 2 to group massive builder content logically
    wf_step1, wf_step2, wf_step3, wf_step4 = st.tabs([
        "1. Sequence Design",
        "2. Live Analytics",
        "3. Mismatch & Validation",
        "4. Database & Loop Simulation"
    ])

    # --- SUB-TAB 1: SEQUENCE DESIGN ---
    with wf_step1:
        st.subheader("1. Workflow Design & Construction")
        st.markdown("### 🛠️ Step-by-Step Construction Guide")

        st.markdown("#### Step 1: Adding the Initial Step")
        st.markdown("""
        1. Navigate to the **Workflow Builder** workspace in the left sidebar.
        2. Under the **Add Process Step** card, click the dropdown menu to browse all active modules.
        3. Select **A - DNA dilution** and click the **\"+ Add\"** button.
        """)

        # [Image 13] - Centered Base64 card for adding step 1
        render_image_card(
            "assets/wf_add_step.png",
            caption="Workflow Builder: Selecting the initial RAM step to construct the sequence",
            max_width=400
        )

        st.markdown("#### Step 2: Utilizing Dynamic Recommendations")
        st.markdown("""
        Once the initial step is registered, the builder automatically updates:
        * **Current Process Status**: Displays real-time calculations (turnaround times, material costs, and labor metrics) for the registered RAMs.
        * **Dynamic Recommendations**: Beneath the step entry card, the system scans the database and populates a matching list of compatible succeeding RAMs.
        * **How it works**: These recommendations are governed by the *Three-Layer Matching Mechanism* (Classification, Vessel Format, and Essentiality).
        * **Adding Recommended Steps**: Simply select the next recommended RAM from the recommendations list and click **\"+ Add\"**.
        """)

        # [Image 14] - Centered Base64 card for dynamic recommendations
        render_image_card(
            "assets/wf_recommendations.png",
            caption="Sequence Overview: The active sequence state and dynamically populated recommended steps",
            max_width=700
        )

        st.markdown("#### Step 3: Completing the Sequence")
        st.markdown("""
        Sequentially add the remaining recommended steps:
        1. Add **B - Thermal cycling** (matches Oligo dilution output).
        2. Add **C - DNA Clean-up** (matches thermal cycling output).
        3. Add **D - DNA measurement** (matches clean-up output) to complete the workflow.
        """)

        # [Image 15] - Centered Base64 card for completed sequence
        render_image_card(
            "assets/wf_full_sequence.png",
            caption="DNA Amplification Workflow: Successfully built 4-step automated sequence",
            max_width=700
        )

    # --- SUB-TAB 2: LIVE ANALYTICS ---
    with wf_step2:
        st.subheader("2. Real-time Economic and Bottleneck Analysis")
        st.markdown("### 📊 In-Session Performance Breakdown & Materials")
        st.markdown("""
        Directly below your workflow workspace, click the **Breakdown** and **Materials** tabs to review the real-time resource distribution of your designed sequence:
        """)

        col_visual1, col_visual2 = st.columns(2)

        with col_visual1:
            st.markdown("#### 1. Turnaround Time & Cost Breakdown")
            st.markdown("""
            Clicking the **Breakdown** tab triggers an automated bottleneck analysis:
            * **Time Bottleneck**: Identifies the exact RAM occupying the largest percentage of total Turnaround Time (e.g., *B - Thermal cycling*).
            * **Cost Bottleneck**: Pinpoints the step responsible for the highest budget consumption.
            * **Interactive Visuals**: Generates structured, interactive pie charts tracking time and cost allocations across each step.
            """)

        with col_visual2:
            st.markdown("#### 2. Consolidated Bill of Materials")
            st.markdown("""
            Clicking the **Materials** tab compiles a complete **Bill of Materials (BOM)**:
            * **Aggregated Manifest**: Consolidates all chemicals, reagents, disposable tips, and microplates across the entire workflow sequence.
            * **Procurement Details**: Displays precise quantities, unit rates, and cumulative cost margins to help streamline purchasing.
            """)

        # Restoring Image 7 (Time Breakdown), Image 8 (Cost Breakdown), and Image 9 (Consolidated Materials BOM)
        render_image_card(
            "assets/wf_time_breakdown.png",
            caption="Time Distribution Chart: Highlighting automated runtimes vs manual prep bottlenecks",
            max_width=700
        )
        render_image_card(
            "assets/wf_cost_breakdown.png",
            caption="Cost Distribution Chart: Pinpointing dominant financial drivers",
            max_width=700
        )
        render_image_card(
            "assets/wf_bom.png",
            caption="Consolidated Bill of Materials (BOM) summary table for bulk procurement tracking",
            max_width=700
        )

    # --- SUB-TAB 3: VALIDATION & MISMATCH ---
    with wf_step3:
        st.subheader("3. Logical Verification & Session Adjustments")
        st.markdown("### ⚠️ Detecting and Resolving Sequence Mismatches")
        st.markdown("""
        The builder allows researchers to bypass recommendations and select any RAM from the dropdown. 
        However, if the material and vessel compatibility constraints (e.g., vessel formats or chemical classifications) do not match, the system alerts you immediately.
        """)

        st.markdown("#### 1. Mismatch Warning Alert")
        st.markdown("""
        If you add an incompatible RAM (e.g., adding *O - Sequencing* instead of *D - DNA measurement* after *C - DNA Clean-up*), the system raises a **Sequence Mismatch Detected** alert and disables further additions.
        * The mismatched step will clearly display the missing requirement (e.g., **Expected 'DNA' in 'UV-STAR MICROPLATE'**).
        * To proceed, you must either remove the mismatched step using the **\"X\"** button or resolve the incompatibility.
        """)

        # [Image 16] - Centered Base64 card for mismatch warning
        render_image_card(
            "assets/wf_mismatch_warning.png",
            caption="Sequence Mismatch: Visual validation alert showing expected vessel and classification mismatches",
            max_width=700
        )

        st.markdown("#### 2. Resolving Mismatches via Inline Editing")
        st.markdown("""
        Instead of re-configuring a new RAM from scratch, you can directly within the builder session directly inside the builder session:
        1. Click the **Edit button** (the pencil icon located to the left of the \"X\" delete button) on the mismatched sequence card.
        2. An **Edit RAM Information** popup modal will appear.
        3. Modify the mismatched I/O definitions or vessel formatting within the modal (e.g., updating the input vessel type to *UV-STAR MICROPLATE* to match the preceding step's output).
        """)

        # [Image 17] - Centered Base64 card for inline edit modal
        render_image_card(
            "assets/wf_edit_session_modal.png",
            caption="Inline RAM Editor: Editing substance input/output requirements in the builder session",
            max_width=700
        )

        st.markdown("#### 3. Understanding Session Save Options")
        st.markdown("""
        The modal offers **three distinct saving methods** to apply your changes to the sequence:
        * **Apply to Session Only**: Temporarily applies the modified RAM configurations strictly to the active builder session. 
          * *Use case*: Perfect for one-off experimental modifications where you do not want to alter the global cloud database. 
          * *Security*: **Does not require** an Access Code.
        * **Overwrite Original**: Permanently overwrites the existing master RAM in the cloud database.
          * *Security*: **Requires the Access Code** matching the original configuration.
        * **Save as New**: Saves the edited configuration as a brand-new, standalone RAM.
          * *Security*: Does not require the original code; a new entry is automatically assigned a new unique identifier.
        * Once done, click the **Close** button to dismiss the modal.
        """)

        # [Image 18] - Centered Base64 card for resolved mismatch sequence
        render_image_card(
            "assets/wf_mismatch_resolved.png",
            caption="Mismatched sequence resolved: The sequence chain is valid after applying session modifications",
            max_width=700
        )

        st.warning("""
        **⚠️ Important Usage Note**
        Bypassing validation blocks or editing properties requires a thorough understanding of the underlying biochemical process. 
        Artificially modifying and forcing a material connection to clear the mismatch warning—without ensuring actual physical or logical compatibility in the laboratory—is strongly discouraged. 
        The researcher is solely responsible for verifying the physical execution of any session-modified steps.
        """)

    # --- SUB-TAB 4: DATABASE & SIMULATION ---
    with wf_step4:
        st.subheader("4. Database Archival, Querying, & Scaled Simulation")
        st.markdown("### 💾 Metadata and Cloud Database Archival")
        st.markdown("""
        When your sequence is complete and validated, you can configure its metadata in the left sidebar and save the workflow to the database:
        * **Workflow Settings**: Input a distinct *Workflow Name*, *Researcher Name* (can be flagged as *Anonymous* if desired), and an *Output Summary*.
        * **Throughput Multipliers**: The throughput defaults to 96 samples and can be scaled upwards in multiples of 96.
        * **Commit Actions**: Click the **Save to WorkflowDB** button. Enter your **Access Code** to initiate validation.
        * **Overwrite Policy**: If a workflow with the same name exists, the system verifies your Access Code. If authenticated, it overwrites the existing entry; if unauthorized, it is archived as a new unique copy.
        """)

        # [Image 19] - Centered Base64 card for sidebar configuration
        render_image_card(
            "assets/wf_sidebar_settings.png",
            caption="Sidebar Configuration Panel: Setting metadata and scaling throughput parameters",
            max_width=300
        )

        # [Image 20] - Centered Base64 card for access code save block
        render_image_card(
            "assets/wf_save_access_code.png",
            caption="Authentication Gate: Checking permissions and duplication states prior to saving",
            max_width=350
        )

        st.markdown("---")
        st.markdown("### 📂 Workflow Database Curation & Management")
        st.markdown("""
        The **Workflow Database** serves as the public directory and registry for all finalized sequences.
        """)

        st.markdown("#### 1. Browsing and Inspecting Protocols")
        st.markdown("""
        * **Repository Filters**: Isolate workflows based on curated **MasterDB** reference architectures or custom **UserDB** records.
        * **Interactive Dropdown**: Select any archived workflow to expand its full operational record and details dashboard.
        """)

        # [Image 21] - Centered Base64 card for database browser
        render_image_card(
            "assets/wf_db_browse.png",
            caption="Workflow Database: Exploring reference protocols and user repositories",
            max_width=600
        )

        # [Image 22] - Centered Base64 card for database dashboard details
        render_image_card(
            "assets/wf_db_details.png",
            caption="Consolidated analytical profile loaded from the Workflow Database",
            max_width=600
        )

        st.markdown("#### 2. Multi-Format Data Export")
        st.markdown("""
        Under the **Export** tab, researchers can extract complete simulation data, timing breakdowns, and material manifests.
        * Supported export formats include **Excel (.xlsx)**, **JSON (.json)**, and **Plain Text (.txt)**.
        """)

        # [Image 23] - Centered Base64 card for DB export tab
        render_image_card(
            "assets/wf_db_export.png",
            caption="Export utility: Extracting structured laboratory and economic datasets",
            max_width=700
        )

        st.markdown("#### 3. Administrative Actions: Manage Tab")
        st.markdown("""
        Under the **Manage** tab, authenticated users can execute workflow management tasks:
        * **Metadata Curation**: Modify the name, description, or outcome summaries. Duplication check policies match the main builder.
        * **Permanent Deletion**: Purge obsolete or inaccurate workflows from the repository. 
        * *Security*: Editing and deletion tasks **require Access Code authentication** to prevent unauthorized data loss.
        """)

        # [Image 24] - Centered Base64 card for DB manage tab
        render_image_card(
            "assets/wf_db_manage.png",
            caption="Administrative Actions Panel: Modifying metadata or deleting database entries",
            max_width=700
        )

        st.markdown("#### 4. Loading to Builder (Iterative Optimization)")
        st.markdown("""
        * Click **\"Load to Workflow Builder\"** to import an archived database workflow back into the live builder session.
        * This allows you to immediately test modifications, swap equipment, or recalculate costs.
        * Saves back to the database are securely authorized via Access Code to prevent accidental overwrites.
        """)

        # [Image 25] - Centered Base64 card showing loaded workflow in builder
        render_image_card(
            "assets/wf_builder_loaded.png",
            caption="Iterative workflow development: Live sequence loaded from database for optimization",
            max_width=700
        )

        st.markdown("---")
        st.markdown("### 🔄 Predictive Loop Simulation")
        st.markdown("""
        Located under the **Loop Simulation** tab of a workflow's details, this advanced tool allows researchers to model scaled, high-frequency execution profiles before experimental execution.
        """)

        tab_sim1, tab_sim2 = st.tabs(["Manual Scaling Mode", "Resource-Limited Auto-Calc"])

        with tab_sim1:
            st.markdown("#### Manual Scaling Mode")
            st.markdown("""
            * **How it works**: Adjust the **Target Cycles** slider to set the number of repeated runs you wish to model.
            * **Output**: The system scales calculations and outputs the projected total execution hours, budget consumption, and processed sample yield.
            """)
            # [Image 26] - Centered Base64 card for manual simulation
            render_image_card(
                "assets/wf_loop_manual.png",
                caption="Manual Scaling Simulation: Modeling requirements for a fixed loop volume",
                max_width=800
            )

        with tab_sim2:
            st.markdown("#### Resource-Limited Auto-Calc")
            st.markdown("""
            * **How it works**: Set your constraints (e.g., maximum available **Budget** and **Time Limit**).
            * **Output**: The solver automatically calculates the maximum possible loops you can run within those limits. 
            * **Resource Insight**: Identifies whether your scale-up is restricted by financial constraints (reagents) or temporal constraints (run durations).
            """)
            # [Image 27] - Centered Base64 card for resource simulation
            render_image_card(
                "assets/wf_loop_resource.png",
                caption="Resource-constrained Auto-Calc modeling the maximum capacity threshold",
                max_width=800
            )

    # Scroll up button
    st.markdown(back_to_top_html, unsafe_allow_html=True)

with tab3:
    st.header("📊 3. Workflow Analytics")
    st.markdown("""
    The **Workflow Analytics** workspace enables researchers to compare performance metrics between multiple finalized workflows stored in the database. 
    By evaluating **Turnaround Time (TAT)**, **Total Cost (USD)**, and the **Experimental Price Index (EPI)** side-by-side, you can quantitatively evaluate and optimize workflow configurations.
    """)

    st.markdown("---")
    st.markdown("### 🛠️ Step-by-Step Comparative Analytics Guide")

    st.markdown("#### Step 1: Accessing and Synchronizing the Workspace")
    st.markdown("""
    1. Navigate to the **Workflow Analytics** page via the left sidebar menu.
    2. If your newly registered workflows do not immediately appear in the comparison list, click the **Refresh Data** button located in the left sidebar filter registry to refresh and synchronize records from the cloud database.
    """)

    # [Image 1] - Centered Base64 card for Analytics Landing Page
    render_image_card(
        "assets/wf_anal_landing.png",
        caption="Workflow Analytics Workspace: Live database directory and registry synchronization",
        max_width=800
    )

    st.markdown("#### Step 2: Selecting Workflows for Multi-Comparison")
    st.markdown("""
    * **Browse & Search**: Scroll through the registry or utilize the **Search Workflow** input field to locate protocols by name or author.
    * **Select Targets**: Check the checkboxes on the left of the table rows to select protocols for comparison. You can select and compare **up to five workflows** simultaneously.
    """)

    # [Image 2] - Centered Base64 card for Comparison Selection and Bar Charts
    render_image_card(
        "assets/wf_anal_comparison.png",
        caption="Selecting target protocols to plot comparative performance profiles",
        max_width=800
    )

    st.markdown("#### Step 3: Interpreting Key Metrics Comparison")
    st.markdown("""
    Upon selection, the system automatically compiles and plots interactive bar charts comparing three core variables side-by-side:
    * **Turnaround Time (h)**: Total sequence duration spanning operation and hands-on preparation hours.
    * **Total Cost (USD)**: The cumulative total workflow cost combining labor and materials.
    * **EPI**: The normalized Experimental Price Index assessing overall efficiency per sample.
    """)

    st.markdown("#### Step 4: Extracting Strategic Insights")
    st.markdown("""
    Directly beneath the comparison charts, the system automatically evaluates the selected pool and instantly flags distinct operational leaders:
    * **🏆 Optimal Choice**: Identifies the workflow achieving the **lowest EPI**, representing the best balance between time and cost per sample.
    * **⚡ Speed Leader**: Highlights the sequence with the **minimum Turnaround Time (TAT)**, best suited for time-sensitive production runs.
    * **💸 Budget Leader**: Highlights the protocol requiring the **lowest overall budget**, ideal for resource-constrained research environments.
    """)

    # [Image 3] - Centered Base64 card for Strategic Insights Cards
    render_image_card(
        "assets/wf_anal_insights.png",
        caption="Strategic Insights Solver: Real-time identification of optimal choices and leaders",
        max_width=800
    )

    st.markdown("---")
    st.markdown("### 🧪 Advanced Curation: Simulating Manual vs. Automated Runs")
    st.markdown("""
    To demonstrate the quantitative benefits of automated laboratory workflows (e.g., for comparative workflow evaluation), you can model and compare your automated protocol against a simulated **manual (human-executed) version**.

    Follow this standard curation sequence to compile and analyze manual benchmarks:
    """)

    st.markdown("""
    1. **Import the Baseline**: Open the **Workflow Database** page, select your automated reference protocol, and click **Load to Workflow Builder**.
    2. **Edit Target RAMs**: Inside the builder sequence, locate the specific RAM steps you want to simulate as manual and click their **Edit (pencil icon)** button.
    3. **Adjust Performance Metrics**: Modify the preparation times, automated operation times, and labor costs to represent manual execution.
    4. **Apply Locally**: Click **Apply to Session Only** within the edit modal. This temporarily modifies the values inside your active builder sequence without altering the public database.
    5. **Save as a Manual Copy**: Go to the sidebar settings, rename the workflow (e.g., add `(Manual)` as a suffix), and click **Save to WorkflowDB** ➡️ Select **Save as new copy**.
    6. **Execute Comparison**: Go back to the **Workflow Analytics** page, check both your original automated workflow and the newly registered manual variant, and evaluate their cost and time differences side-by-side.
    """)

    st.warning("""
    **⚠️ Manual Workflow Estimation Notice**
    Because manual execution metrics are highly dependent on individual laboratory experience, values can vary significantly. 
    To minimize analytical errors, researchers must input realistic, reasonable manual parameters based on historical laboratory records or published reference values.
    """)

    # Scroll up button
    st.markdown(back_to_top_html, unsafe_allow_html=True)