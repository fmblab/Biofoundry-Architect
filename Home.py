import streamlit as st
import base64
import os

# ==========================================
# 1. Page Configuration
# ==========================================
st.set_page_config(page_title="Biofoundry Architect 1.0", layout="wide")


# Helper function to embed local images into HTML using Base64 encoding
def get_base64_img(path):
    try:
        with open(path, "rb") as f:
            data = f.read()
        return base64.b64encode(data).decode()
    except FileNotFoundError:
        return ""


# ==========================================
# 2. Introduction Page Configuration
# ==========================================
def show_intro():
    # CSS Styles (Handles colors and text effects; layout is managed by the Streamlit engine)
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

        .block-container {
            max-width: 1300px !important;
            padding-top: 2rem !important;
            padding-bottom: 2rem !important;
        }

        .main-content {
            text-align: center;
            font-family: 'Inter', sans-serif !important;
        }

        .h-title { font-size: 52px; font-weight: 800; color: var(--text-color); margin-bottom: 10px; }
        .h-sub { font-size: 20px; color: #6B7280; margin-bottom: 5px; line-height: 1.4; }
        .h-affil { font-size: 17px; color: #6B7280; margin-bottom: 20px; }
        .h-hr { width: 100%; border: 0; border-top: 1px solid #E2E8F0; margin: 1.5rem 0; }

        .h-img-header {
            font-size: 26px;
            font-weight: 700;
            color: #3B82F6; 
            margin-top: 25px;
            margin-bottom: 15px;
        }

        .img-card {
            background-color: white; 
            padding: 15px;
            border-radius: 12px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.08);
            margin-bottom: 50px; 
            width: 100%;
            display: flex;
            justify-content: center;
        }
        .img-card img {
            max-width: 100%;
            height: auto;
        }

        /* Primary Button Style */
        div.stButton > button[kind="primary"] { 
            background-color: #FF4B4B !important; 
            color: white !important; 
            height: 52px !important; 
            font-size: 20px !important; 
            font-weight: bold !important; 
            border-radius: 8px !important; 
            border: none !important;
            box-shadow: 0 4px 10px rgba(255, 75, 75, 0.3);
            transition: all 0.3s ease;
        }

        div.stButton > button[kind="primary"]:hover {
            transform: translateY(-2px);
            background-color: #E63E3E !important;
        }

        /* Secondary Button (Text Link Style) Style */
        div.stButton > button[kind="secondary"] {
            background-color: transparent !important;
            color: #6B7280 !important;
            height: auto !important;
            font-size: 15px !important;
            font-weight: 500 !important;
            text-decoration: underline !important;
            border: none !important;
            box-shadow: none !important;
            padding-top: 10px !important;
            margin-top: -5px !important; 
            white-space: pre-line !important; 
            line-height: 1.4 !important; 
            transition: color 0.2s ease;
        }

        div.stButton > button[kind="secondary"] p {
            white-space: pre-line !important;
            margin: 0 !important;
        }

        div.stButton > button[kind="secondary"]:hover {
            color: #3B82F6 !important; 
            background-color: transparent !important;
            transform: none !important; 
        }
        </style>
    """, unsafe_allow_html=True)

    # Header Section
    st.markdown("""
<div class='main-content'>
    <div class='h-title'>Biofoundry Architect 1.0</div>
    <div class='h-sub'>A robot-assisted module configurator and workflow designer with hub interoperability and techno-economic evaluation</div>
    <div class='h-affil'>SKy Biofoundry, Sungkyunkwan University (SKKU), Rep. of Korea</div>
    <div class='h-hr'></div>
    <div class='h-img-header'>Architect & Optimize your lab automation</div>
</div>
    """, unsafe_allow_html=True)

    # Image Section
    img_data = get_base64_img('assets/Thumbnailsver2.png')
    st.markdown(f"""
<div class='main-content'>
    <div class='img-card'>
        <img src="data:image/png;base64,{img_data}" />
    </div>
</div>
    """, unsafe_allow_html=True)

    # Button Section (Applies the latest 'width=stretch' syntax)
    col1, col2, col3 = st.columns([1, 0.6, 1])
    with col2:
        # 1. Primary Action Button (Get Started)
        if st.button("Get Started", type="primary", width="stretch"):
            st.switch_page(wf_build_page)

        # 2. Secondary Link Button (User Guide)
        if st.button("New to this tool?\nRead the User Guide 📖", type="secondary", width="stretch"):
            st.switch_page(user_guide_page)

    # Footer Section
    st.markdown("""
<div class='main-content' style='margin-top: 20px;'>
    <div style="font-weight: 700; font-size: 22px; color: var(--text-color); margin-bottom: 10px;">
        GETTING HELP
    </div>
    <div style="font-size: 15px; color: var(--text-color); line-height: 1.7; margin-bottom: 25px; max-width: 800px; margin-left: auto; margin-right: auto;">
        If you need help regarding technical issues (e.g. errors or missing results) contact <b>Technical Support</b>.<br>
        Please include the name of the service and version and the images you have captured.<br><br>
        If you have scientific questions, contact <b>Correspondence</b>.
    </div>
    <div style="font-size: 14px; color: #64748B; margin-bottom: 30px;">
        All code is released under license GNU General Public License version 3 (GNU GPLv3) <br>and the datasets are made available under Creative Commons Attribution 4.0 International (CC BY NC SA 4.0) license</b>.
    </div>
    <div class='h-hr'></div>
    <div style="font-size: 14px; color: #64748B; line-height: 1.7;">
        <b>Department of Food Science and Biotechnology & SKy Biofoundry</b><br>
        Sungkyunkwan University (SKKU)<br>
        (Office: 62-212; Lab.: 61-254) 2066 Seobu-ro, Jangan-gu, Suwon 16419, Rep. of Korea<br>
        E-mail: skybiofoundry@gmail.com
    </div>
    <div style="font-size: 13px; color: #94A3B8; margin-top: 25px;">
        © 2026 FMB Lab. All rights reserved.
    </div>
</div>
    """, unsafe_allow_html=True)


# ==========================================
# 3. Page Definitions and Navigation
# ==========================================
home_page = st.Page(show_intro, title="Home", default=True)

# Navigation structure prioritized for active design (Workflows on top)
wf_build_page = st.Page("pages/Workflow Builder.py", title="- Workflow Builder")
wf_db_page = st.Page("pages/Workflow Database.py", title="- Workflow Database")
wf_anal_page = st.Page("pages/Workflow Analytics.py", title="- Workflow Analytics")

ram_reg_page = st.Page("pages/RAM Registration.py", title="- RAM Registration")
ram_db_page = st.Page("pages/RAM Database.py", title="- RAM Database")
ram_edit_page = st.Page("pages/RAM Editor.py", title="- RAM Editor")

resource_page = st.Page("pages/Resources.py", title="- Resource Database")

concept_ram_page = st.Page("pages/Concept_RAM.py", title="- Theoretical Framework")
user_guide_page = st.Page("pages/User Guide.py", title="- User Guide")


pg = st.navigation({
    "": [home_page],
    "Workflow System": [wf_build_page, wf_db_page, wf_anal_page],
    "RAM System": [ram_reg_page, ram_db_page, ram_edit_page],
    "Resources of Lab Automation": [resource_page],
    "Help": [concept_ram_page, user_guide_page]
})

pg.run()