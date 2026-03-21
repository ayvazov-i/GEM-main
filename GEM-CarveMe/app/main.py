"""
GEM Media Optimiser — Streamlit App Entry Point.

Run from the project root:
    streamlit run app/main.py
"""
import sys
import os

# Ensure project root is on the Python path so `core` and `app` are importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st

st.set_page_config(
    page_title="GEM Media Optimiser",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Home Page ---

st.title("🧬 GEM Media Optimiser")
st.markdown(
    """
**Genome-Scale Metabolic Model–based Media Optimisation for Bioprocess Engineers**

This tool lets you go from a metabolic model to a reduced experimental design in minutes —
without any coding or GEM expertise required.
"""
)

st.divider()

col1, col2 = st.columns([3, 2])

with col1:
    st.subheader("What does this tool do?")
    st.markdown(
        """
Designing growth media for a new microbial strain typically requires testing hundreds of
nutrient combinations. This tool uses a **Genome-Scale Metabolic Model (GEM)** to predict
which nutrients actually matter for growth, reducing your experimental design from 30+ variables
down to 5–8 key factors.

**Workflow:**
1. **Upload** a pre-built SBML metabolic model (or select a demo)
2. **Validate** the model — check it predicts growth on standard media
3. **Set objective** — maximise growth or a specific product
4. **Analyse** — identify essential nutrients and rank by growth sensitivity
5. **Refine** — generate a compact Design of Experiments (DoE) matrix
6. **Export** — download your DoE as a spreadsheet and take it to the lab
"""
    )

with col2:
    st.subheader("Quick Start")
    st.info(
        """
**No model? No problem.**

Select one of the pre-loaded example models in **Step 1**:
- *E. coli* K-12 MG1655 (iML1515)
- *B. subtilis* 168 (iYO844)
- *S. cerevisiae* S288C (iMM904)
- *P. putida* KT2440 (iJN1463)

Then click through the sidebar steps.
"""
    )

    if st.button("🚀 Get Started →", type="primary", use_container_width=True):
        st.switch_page("pages/01_Upload.py")

st.divider()

# --- Workflow overview cards ---

st.subheader("Workflow Overview")

steps = [
    ("1️⃣", "Upload Model", "Load an SBML model or select a demo organism"),
    ("2️⃣", "Model Summary", "Validate the model and review key statistics"),
    ("3️⃣", "Set Objective", "Choose what to optimise: growth or product flux"),
    ("4️⃣", "Analysis", "Screen nutrient essentiality and rank by sensitivity"),
    ("5️⃣", "Design Space", "Generate a reduced DoE matrix with concentration ranges"),
    ("6️⃣", "Export", "Download the DoE table, model file, and summary report"),
]

cols = st.columns(3)
for i, (icon, title, desc) in enumerate(steps):
    with cols[i % 3]:
        # Check if step is complete
        completed = False
        if title == "Upload Model" and st.session_state.get("model_path"):
            completed = True
        elif title == "Model Summary" and st.session_state.get("validation_result"):
            completed = True
        elif title == "Set Objective" and st.session_state.get("objective_reaction"):
            completed = True
        elif title == "Analysis" and st.session_state.get("essentiality_df") is not None:
            completed = True
        elif title == "Design Space" and st.session_state.get("doe_df") is not None:
            completed = True

        status = "✅" if completed else ""
        st.markdown(
            f"""
<div style="border:1px solid #ddd; border-radius:8px; padding:12px; margin:6px 0;
            background-color:{'#f0fff4' if completed else '#fafafa'};">
<b>{icon} {title}</b> {status}<br>
<small style="color:#666;">{desc}</small>
</div>
""",
            unsafe_allow_html=True,
        )

st.divider()

# --- Sidebar navigation hint ---

with st.sidebar:
    st.markdown("### Navigation")
    st.info("Use the page links above to navigate through the workflow steps.")
    st.divider()
    st.markdown("### About")
    st.caption(
        "Built with [COBRApy](https://cobrapy.readthedocs.io/), "
        "[Streamlit](https://streamlit.io/), and [Plotly](https://plotly.com/). "
        "Data from [BiGG Models](http://bigg.ucsd.edu/)."
    )
