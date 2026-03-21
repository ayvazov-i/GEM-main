"""
Step 2 — Model Summary
Display model statistics, FBA baseline result, and validation warnings.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import streamlit as st
import pandas as pd

from core.model_validator import validate_model
from core.utils import load_validation_data, format_growth_rate
from app.components.widgets import (
    page_header, step_progress_sidebar, session_state_guard,
    info_tooltip, metric_card,
)

st.set_page_config(page_title="Step 2 — Model Summary", page_icon="📊", layout="wide")

step_progress_sidebar(2)
page_header("Step 2: Model Summary", "Review model quality and baseline growth prediction")

if not session_state_guard(["model", "model_name"], "Model Summary"):
    st.stop()

model = st.session_state["model"]
model_name = st.session_state["model_name"]

st.markdown(f"**Model:** {model_name} (`{model.id}`)")

# --- Run / cache validation ---

if st.session_state.get("validation_result") is None or st.button("🔄 Re-run Validation"):
    with st.spinner("Running FBA and model checks..."):
        result = validate_model(model)
        st.session_state["validation_result"] = result

result = st.session_state["validation_result"]

# --- Traffic-light status ---

col_status, col_rate = st.columns([1, 2])
with col_status:
    if result["feasible"] and result["growth_rate"] > 1e-6:
        st.success("🟢 Model is feasible — growth predicted")
    elif result["feasible"]:
        st.warning("🟡 Model is feasible but growth rate is near-zero")
    else:
        st.error("🔴 Model is infeasible — no growth on current medium")

with col_rate:
    st.metric(
        label="Predicted Growth Rate",
        value=format_growth_rate(result["growth_rate"]),
        help="Optimal growth rate predicted by FBA (Flux Balance Analysis).",
    )

info_tooltip("FBA", "fba")

# --- Warnings ---

if result["warnings"]:
    with st.expander(f"⚠️ {len(result['warnings'])} validation warning(s)", expanded=True):
        for w in result["warnings"]:
            st.warning(w)

st.divider()

# --- Key metrics ---

st.subheader("Model Statistics")

cols = st.columns(4)
with cols[0]:
    metric_card("Reactions", str(result["num_reactions"]))
with cols[1]:
    metric_card("Metabolites", str(result["num_metabolites"]))
with cols[2]:
    metric_card("Genes", str(result["num_genes"]))
with cols[3]:
    metric_card("Exchange Reactions", str(result["num_exchanges"]))

st.divider()

# --- Validation against known growth rates ---

st.subheader("Comparison with Experimental Data")

medium_key = st.session_state.get("chosen_medium_key")
val_data = load_validation_data()

if medium_key and medium_key in val_data:
    ref = val_data[medium_key]
    lo, hi = ref["expected_growth_rate_range"]
    predicted = result["growth_rate"]
    in_range = lo <= predicted <= hi

    st.markdown(f"**Medium:** {ref.get('display_name', medium_key)}")
    st.markdown(f"**Expected experimental range:** {lo:.2f} – {hi:.2f} h⁻¹")
    st.markdown(f"**Model prediction:** {format_growth_rate(predicted)}")

    if predicted < 1e-6:
        st.error("Model predicts no growth. Check that the medium is applied correctly.")
    elif in_range:
        st.success(f"✅ Prediction is within the experimental range ({lo:.2f}–{hi:.2f} h⁻¹).")
    elif predicted < lo:
        pct = (lo - predicted) / lo * 100
        st.warning(f"⚠️ Prediction is {pct:.0f}% below the expected lower bound. "
                   f"The model may be over-constrained or missing transport reactions.")
    else:
        pct = (predicted - hi) / hi * 100
        st.warning(f"⚠️ Prediction is {pct:.0f}% above the expected upper bound. "
                   f"The model may be under-constrained (too many nutrients open).")
else:
    st.info("No validation data available for the current medium. "
            "Apply a named medium preset in Step 1 to enable comparison.")

st.divider()

# --- Exchange reactions table ---

with st.expander("📋 Active Medium (Exchange Reaction Bounds)", expanded=False):
    medium_rows = []
    for rxn in model.exchanges:
        lb = rxn.lower_bound
        ub = rxn.upper_bound
        if lb < 0:
            medium_rows.append({
                "Reaction ID": rxn.id,
                "Metabolite": rxn.name or rxn.id,
                "Max Uptake (mmol/gDW/h)": abs(lb),
                "Max Secretion (mmol/gDW/h)": ub,
            })

    if medium_rows:
        st.dataframe(
            pd.DataFrame(medium_rows).sort_values("Max Uptake (mmol/gDW/h)", ascending=False),
            use_container_width=True,
            height=300,
        )
    else:
        st.info("No nutrients are currently set for uptake. Apply a medium preset in Step 1.")

# --- Navigation ---

st.divider()
col_back, col_fwd = st.columns(2)
with col_back:
    st.page_link("pages/01_Upload.py", label="← Back to Step 1: Upload", icon="📁")
with col_fwd:
    if result["feasible"] and result["growth_rate"] > 1e-6:
        st.page_link("pages/03_Objective.py", label="→ Go to Step 3: Set Objective", icon="🎯")
    else:
        st.warning("Fix model feasibility before proceeding.")
