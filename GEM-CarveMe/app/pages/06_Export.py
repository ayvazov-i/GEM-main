"""
Step 6 — Export
Download the DoE matrix, model file, and summary report.
"""
import sys
import os
import io
import tempfile
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import streamlit as st
import pandas as pd
import cobra

from core.gem_generator import save_model_to_sbml
from app.components.widgets import page_header, step_progress_sidebar, session_state_guard

st.set_page_config(page_title="Step 6 — Export", page_icon="📥", layout="wide")

step_progress_sidebar(6)
page_header("Step 6: Export", "Download your results and take them to the lab")

if not session_state_guard(["model"], "Export"):
    st.stop()

model: cobra.Model = st.session_state["model"]
model_name: str = st.session_state.get("model_name", model.id)
doe_df: pd.DataFrame | None = st.session_state.get("doe_df")
ess_df: pd.DataFrame | None = st.session_state.get("essentiality_df")
shadow_df: pd.DataFrame | None = st.session_state.get("shadow_df")
fva_df: pd.DataFrame | None = st.session_state.get("fva_df")

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

# --- DoE Matrix ---

st.subheader("📋 Experimental Design Matrix")

if doe_df is not None:
    st.success(f"DoE matrix ready: {len(doe_df)} experiments × {len(doe_df.columns)} factors")
    st.dataframe(doe_df, use_container_width=True)

    # CSV download
    csv_bytes = doe_df.to_csv(index=True).encode("utf-8")
    st.download_button(
        label="⬇️ Download DoE Matrix (CSV)",
        data=csv_bytes,
        file_name=f"doe_matrix_{timestamp}.csv",
        mime="text/csv",
    )

    # Excel download
    try:
        excel_buffer = io.BytesIO()
        with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
            doe_df.to_excel(writer, sheet_name="DoE Matrix", index=True)
            if ess_df is not None and not ess_df.empty:
                ess_df.to_excel(writer, sheet_name="Essentiality", index=False)
            if shadow_df is not None and not shadow_df.empty:
                shadow_df.to_excel(writer, sheet_name="Shadow Prices", index=False)
            if fva_df is not None and not fva_df.empty:
                fva_df.to_excel(writer, sheet_name="FVA Results", index=False)
        excel_buffer.seek(0)
        st.download_button(
            label="⬇️ Download All Results (Excel)",
            data=excel_buffer.getvalue(),
            file_name=f"gem_media_optimiser_{timestamp}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    except Exception as e:
        st.warning(f"Excel export failed: {e}. Use CSV instead.")
else:
    st.info("No DoE matrix available. Complete Step 5 to generate one.")

st.divider()

# --- Individual analysis tables ---

st.subheader("📊 Analysis Results")

col1, col2 = st.columns(2)

with col1:
    if ess_df is not None and not ess_df.empty:
        csv_ess = ess_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "⬇️ Essentiality Table (CSV)",
            data=csv_ess,
            file_name=f"essentiality_{timestamp}.csv",
            mime="text/csv",
        )
    else:
        st.info("No essentiality data. Run Step 4.")

with col2:
    if shadow_df is not None and not shadow_df.empty:
        csv_shadow = shadow_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "⬇️ Shadow Prices (CSV)",
            data=csv_shadow,
            file_name=f"shadow_prices_{timestamp}.csv",
            mime="text/csv",
        )
    else:
        st.info("No shadow price data. Run Step 4.")

st.divider()

# --- Model file ---

st.subheader("🧬 Metabolic Model File")

if st.button("Prepare SBML model for download"):
    try:
        tmp_path = os.path.join(tempfile.mkdtemp(), f"{model.id}.xml")
        save_model_to_sbml(model, tmp_path)
        with open(tmp_path, "rb") as f:
            sbml_bytes = f.read()
        st.download_button(
            "⬇️ Download Model (SBML .xml)",
            data=sbml_bytes,
            file_name=f"{model.id}_{timestamp}.xml",
            mime="application/xml",
        )
    except Exception as e:
        st.error(f"Failed to serialise model: {e}")

st.divider()

# --- Text summary report ---

st.subheader("📄 Summary Report")


def build_report() -> str:
    lines = [
        "# GEM Media Optimiser — Analysis Report",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        f"## Model: {model_name} ({model.id})",
        f"- Reactions: {len(model.reactions)}",
        f"- Metabolites: {len(model.metabolites)}",
        f"- Genes: {len(model.genes)}",
    ]

    val = st.session_state.get("validation_result")
    if val:
        lines.append(f"- Predicted growth rate: {val['growth_rate']:.4f} h⁻¹")
        lines.append(f"- Model feasible: {val['feasible']}")

    obj_rxn = st.session_state.get("objective_reaction")
    if obj_rxn:
        lines += ["", f"## Objective: {obj_rxn}"]

    if ess_df is not None and not ess_df.empty:
        lines += ["", "## Nutrient Essentiality"]
        counts = ess_df["classification"].value_counts()
        lines.append(f"- Essential: {counts.get('essential', 0)}")
        lines.append(f"- Enhancing: {counts.get('enhancing', 0)}")
        lines.append(f"- Dispensable: {counts.get('dispensable', 0)}")
        lines += ["", "### Essential Nutrients"]
        for _, row in ess_df[ess_df["classification"] == "essential"].iterrows():
            lines.append(f"- {row['metabolite_name']} (`{row['reaction_id']}`)")

    key_nutrients = st.session_state.get("key_nutrients", [])
    if key_nutrients:
        lines += ["", "## Selected Key Nutrients for DoE"]
        ess_name_map = {}
        if ess_df is not None and not ess_df.empty:
            ess_name_map = dict(zip(ess_df["reaction_id"], ess_df["metabolite_name"]))
        for rxn_id in key_nutrients:
            lines.append(f"- {ess_name_map.get(rxn_id, rxn_id)} (`{rxn_id}`)")

    if doe_df is not None:
        lines += [
            "",
            "## Experimental Design",
            f"- Design type: {doe_df.attrs.get('design_type', 'N/A')}",
            f"- Number of experiments: {len(doe_df)}",
            f"- Factors: {', '.join(doe_df.columns.tolist())}",
        ]

    lines += [
        "",
        "---",
        "Generated by GEM Media Optimiser (COBRApy + Streamlit)",
    ]
    return "\n".join(lines)


report_text = build_report()
st.text_area("Report preview", value=report_text, height=300)
st.download_button(
    "⬇️ Download Report (Markdown)",
    data=report_text.encode("utf-8"),
    file_name=f"gem_media_report_{timestamp}.md",
    mime="text/markdown",
)

st.divider()

# --- Session summary ---

st.subheader("Session Summary")

completed_steps = []
if st.session_state.get("model"):
    completed_steps.append("✅ Model loaded")
if st.session_state.get("validation_result"):
    completed_steps.append("✅ Model validated")
if st.session_state.get("objective_reaction"):
    completed_steps.append("✅ Objective set")
if st.session_state.get("essentiality_df") is not None:
    completed_steps.append("✅ Essentiality & sensitivity analysis complete")
if st.session_state.get("doe_df") is not None:
    completed_steps.append("✅ DoE matrix generated")

for step in completed_steps:
    st.markdown(step)

st.divider()
st.page_link("pages/05_Design_Space.py", label="← Back to Step 5: Design Space", icon="🧪")
