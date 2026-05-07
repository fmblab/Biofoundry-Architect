import streamlit as st
import base64
import os

# Page Configuration
st.set_page_config(page_title="Concept: RAM & Logic Matching", layout="wide")

# Function to encode local images to Base64
def get_base64_image(image_path):
    if os.path.exists(image_path):
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    return None

# Title and Introduction
st.title("🧩 What is a Robot Assisted Module (RAM)?")
st.markdown("""
**Robot Assisted Module (RAM)** is the fundamental, standardized unit of a biofoundry workflow. 
Inspired by the modularity of blocks, RAMs are designed as **plug-and-play units** that allow researchers 
to rapidly construct and reconfigure diverse automated workflows for synthetic biology and metabolic engineering.
""")

# --- [Image Card Section] ---
img_path = os.path.join("assets", "RAMconcept.png")
img_base64 = get_base64_image(img_path)

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
            <img src="data:image/png;base64,{img_base64}" style="width: 100%; max-width: 700px; height: auto; border-radius: 10px;">
        </div>
        <p style="text-align: center; color: #6b7280; font-size: 0.9rem; margin-top: -15px;">
            Conceptual illustration of robot assisted module (RAM) architecture
        </p>
    """, unsafe_allow_html=True)
else:
    st.error("Image file not found at the specified path.")

st.divider()

# 1. MIARB Standard
st.markdown("## 1. Minimum Information About a RAM for Biofoundry workflow (MIARB)")
st.markdown("""
Each RAM follows the **MIARB (Minimum Information About a RAM for Biofoundry workflow)** standard<sup>[<a href="#ref1" target="_self">1</a>]</sup><sup>[<a href="#ref2" target="_self">2</a>]</sup>. 
This ensures that every physical laboratory process is transformed into a **standardized digital representation**, 
allowing for precise simulation and techno-economic evaluation before actual execution.
""", unsafe_allow_html=True)

col1, col2, col3 = st.columns(3)
with col1:
    st.subheader("📥 Input")
    st.markdown("- Sample Type\n- Vessel Format\n- Volume\n- Number of Samples")
with col2:
    st.subheader("⚙️ Process")
    st.markdown("- Functional Device/Robot\n- Function/Action\n- Time ($T$)\n- Cost ($C$)")
with col3:
    st.subheader("📤 Output")
    st.markdown("- Resulting Sample\n- Format Change\n- Generated Data")

st.divider()

# --- Section 2: Logic Matching Mechanism ---
st.header("2. Logic Matching: Ensuring Procedural Validity")
st.markdown("""
To prevent design errors in the \"Dry-lab\" stage, the platform validates the connectivity between RAMs 
using a **Three-Layer Matching** mechanism. This ensures the workflow is both biologically sound and physically executable.
""")

c1, c2, c3 = st.columns(3)
with c1:
    st.info("**1. Essentiality**")
    st.markdown("Identifies whether a substance is critical for the module's objective. (e.g., Template DNA in PCR)")
with c2:
    st.info("**2. Classification**")
    st.markdown("Categorizes the biochemical identity. (e.g., DNA, Cells, Buffer, etc.)")
with c3:
    st.info("**3. Vessel Format**")
    st.markdown("Defines physical container specifications. (e.g., 96-well Plate, 1.5mL Tube, etc.)")

st.markdown("### The Logic of Connection Rule")
st.success("""
**Connectivity Requirement:** Two RAMs are compatible only if:
1. The **Classification** of the Essential Output matches the Input requirement of the succeeding RAM.
2. The **Vessel Format** of the Output matches the Input format of the succeeding RAM.

*※ Exception: When the output is **'Data'**, strict physical matching constraints do not apply.
""")

st.divider()

# --- Section 3: Flexibility & Exceptions ---
st.header("3. Flexibility & Exceptions: Bridging the Gaps")
st.markdown("""
Real-world laboratory processes often involve complex scenarios. We support two primary bridge mechanisms to maintain design flexibility without compromising logical integrity.
""")

tab_vcm, tab_data = st.tabs(["🔄 Vessel Conversion (Physical)", "💾 Data Exception (Informational)"])

with tab_vcm:
    st.markdown("#### Vessel Conversion Setting")
    st.markdown("""
    **The Problem:** Direct connection is blocked due to **Vessel Mismatch** (e.g., Output in *Plate* vs. Input in *Tubes*).

    **The Solution:**
    - **Vessel Conversion:** Connectivity can be ensured by adjusting Input/Output definitions to align vessel types between RAMs.
    """)

with tab_data:
    st.markdown("#### Data Exception & Retrospective Selection")
    st.markdown("""
    **The Concept:**
    When a RAM's output classification is *Data*, the standard material-based connectivity constraints (Substance & Vessel) for the next connection are relaxed. Instead of requiring direct physical transfer, subsequent connections are determined based on informational dependency.

    **The GE Workflow Model (Retrospective Selection):**
    - **Informational Continuity:** *Data* acts as an informational bridge, allowing the workflow to progress without requiring direct material linkage between consecutive RAMs.
    - **Decoupled Dependency:** Although RAMs are represented sequentially in the workflow, their logical dependencies are not strictly governed by physical material flow.
    - **Decision-Driven Connectivity:** Data enables downstream RAMs to be selected based on analytical outcomes, allowing them to utilize materials generated from earlier points in the workflow lineage (e.g., via **parent RAM context**), rather than the immediate upstream output.
    """)
    st.info("💡 **Note:** Bypassing constraints assumes the researcher ensures contextual validity. The system allows flexibility to reflect advanced experimental designs where results inform the selection of materials from previous steps.")

st.divider()

# 4. Performance Analysis: Techno-Economic Evaluation
st.header("4. Performance Evaluation: Techno-Economic Analysis")
st.markdown("""
The platform provides a comprehensive **Techno-Economic Assessment (TEA)** for the constructed workflow<sup>[<a href="#ref2" target="_self">2</a>]</sup>. 
By calculating three core metrics, researchers can evaluate whether a workflow is optimized for the objective<sup>[<a href="#ref3" target="_self">3</a>]</sup>.
""", unsafe_allow_html=True)

# Metrics Explanation Layout
pa_col1, pa_col2, pa_col3 = st.columns(3)

with pa_col1:
    st.markdown("#### ⏱️ TAT")
    st.caption("**Turnaround Time**")
    st.markdown("""
    The total time required to complete the entire sequence. 
    It is calculated as the sum of Operation time and Hands-on time.
    """)
    st.latex(r"TAT = \sum (T_{operation} + T_{hands-on})")

with pa_col2:
    st.markdown("#### 💰 Total Cost")
    st.caption("**Economic Investment**")
    st.markdown("""
    The sum of material expenses and labor costs (Hands-on time $\\times$ Labor rate (37.5 USD per hour)).
    """)
    st.latex(r"Cost = \sum (C_{mat} + C_{labor})")

with pa_col3:
    st.markdown("#### ⚖️ EPI")
    st.caption("**Experiment Price Index**")
    st.markdown("""
    A metric of experimental efficiency defined as the geometric mean of processing time and cost per sample.
    """)
    st.latex(r"EPI = \sqrt{\frac{TAT}{N} \times \frac{Cost}{N}}")

# Performance Analysis Methodology Expansion
st.markdown("---")
st.markdown("### 📊 How to Analyze Workflow Performance")

ana_c1, ana_c2 = st.columns(2)

with ana_c1:
    st.info("**1. Bottleneck Identification**")
    st.markdown("""
    * **Time Bottleneck:** The specific RAM that occupies the largest percentage of total TAT. 
      Target this for hardware upgrades (e.g., switching from LiHa to MCA).
    * **Cost Bottleneck:** The step with the highest material or labor cost. 
      Target this for protocol optimization or reagent miniaturization.
    """)

with ana_c2:
    st.success("**2. Comparative Evaluation**")
    st.markdown("""
    * **Design Selection:** Compare different workflow candidates for the same output. The design with the **lower EPI** is objectively more efficient.
    """)

# --- [Go to User Guide Button] ---
st.markdown(
    """
    <div style="display: flex; justify-content: center; padding: 20px 0;">
        <a href="/User_Guide" target="_self" style="text-decoration: none;">
            <div style="
                display: flex;
                align-items: center;
                gap: 8px;
                padding: 6px 14px;
                border-radius: 8px;
                background-color: #f0f2f6;
                color: #31333F;
                border: 1px solid rgba(49, 51, 63, 0.2);
                font-size: 14px;
                font-weight: 500;
                cursor: pointer;
                transition: background-color 0.2s;
            " onmouseover="this.style.backgroundColor='#e0e4eb'" onmouseout="this.style.backgroundColor='#f0f2f6'">
                <span style="color: #2563eb; font-size: 16px;">➡️</span> Go to User Guide
            </div>
        </a>
    </div>
    """,
    unsafe_allow_html=True
)

st.divider()

# Reference Section
# Reordered based on 'Order of Appearance' with specific HTML ID anchors
st.markdown("""
<div style="font-size: 0.85rem; color: #6b7280; line-height: 1.5;">
    <b>Reference</b><br>
    <div id="ref1" style="padding-top: 5px; margin-bottom: 5px;">
        1. Heo, Y. B., Park, J. S., & Woo, H. M. (2025). 
        <b>Architectures of emerging biofoundry platforms for synthetic biology.</b> 
        <i>Current Opinion in Biotechnology</i>, 96, 103379.
        <a href="https://doi.org/10.1016/j.copbio.2025.103379" target="_blank" style="color: #2563eb; text-decoration: none;">https://doi.org/10.1016/j.copbio.2025.103379</a>
    <div id="ref2" style="padding-top: 5px; margin-bottom: 5px;">
        2. Heo, Y. B., Ko, S. C., Keasling, J. D., & Woo, H. M. (2025). 
        <b>Techno-economic assessment-guided biofoundry for microbial strain development.</b> 
        <i>Trends in Biotechnology</i>.
         <a href="https://doi.org/10.1016/j.tibtech.2025.11.002" target="_blank" style="color: #2563eb; text-decoration: none;">https://doi.org/10.1016/j.tibtech.2025.11.002</a>
    <div id="ref3" style="padding-top: 5px; margin-bottom: 5px;">
        3. Woo, H. M., & Keasling, J. D. (2024). 
        <b>Measuring the economic efficiency of laboratory automation in biotechnology.</b> 
        <i>Trends in Biotechnology</i>, 42(9), 1076-1080.
        <a href="https://doi.org/10.1016/j.tibtech.2024.02.001" target="_blank" style="color: #2563eb; text-decoration: none;">https://doi.org/10.1016/j.tibtech.2024.02.001</a>
    </div>
</div>
""", unsafe_allow_html=True)