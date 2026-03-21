"""
Step 5 — Design Space
Run FVA to get feasible ranges, let the user adjust ranges, generate DoE matrix.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import threading
import time

import streamlit as st
import pandas as pd
import cobra

from core.fba_analysis import compute_fva
from core.doe_generator import (
    generate_doe, suggest_ranges_from_fva, experiment_count, DESIGN_TYPES,
)
from app.components.charts import fva_range_chart, doe_parallel_coordinates
from app.components.widgets import (
    page_header, step_progress_sidebar, session_state_guard, info_tooltip,
)

st.set_page_config(page_title="Step 5 — Design Space", page_icon="🧪", layout="wide")

step_progress_sidebar(5)
page_header("Step 5: Design Space", "Define concentration ranges and generate your experimental design")

if not session_state_guard(["model", "key_nutrients"], "Design Space"):
    st.stop()

model: cobra.Model = st.session_state["model"]
key_nutrients: list[str] = st.session_state["key_nutrients"]

# --- FVA ---

st.subheader("Feasible Flux Ranges (FVA)")
info_tooltip("FVA", "fva")

# Fraction slider is always visible so the user can adjust it before OR after running FVA
fraction = st.slider(
    "Fraction of optimal growth to maintain",
    min_value=0.70, max_value=0.99,
    value=st.session_state.get("fva_fraction", 0.95),
    step=0.01,
    help="FVA finds flux ranges that allow the organism to grow at at least this "
         "fraction of its maximum predicted rate.",
)
# Persist the slider value immediately so it survives page re-renders
st.session_state["fva_fraction"] = fraction

run_fva_btn = st.button("▶️ Run FVA", help="Compute feasible uptake ranges for the selected nutrients")

if run_fva_btn:
    _fva_box: dict = {}
    _fva_err: dict = {}

    def _run_fva():
        try:
            _fva_box["df"] = compute_fva(model, fraction=fraction)
        except Exception as _e:
            _fva_err["err"] = _e

    _fva_thread = threading.Thread(target=_run_fva, daemon=True)
    _fva_thread.start()
    _fva_status = st.empty()
    _fva_timer = st.empty()
    _fva_t0 = time.time()
    while _fva_thread.is_alive():
        _fva_elapsed = time.time() - _fva_t0
        _fva_status.info("Running Flux Variability Analysis…")
        _fva_timer.caption(f"⏱️ Elapsed: {int(_fva_elapsed // 60)}m {int(_fva_elapsed % 60):02d}s")
        time.sleep(1)
    _fva_thread.join()
    _fva_elapsed = time.time() - _fva_t0
    _fva_status.empty()
    _fva_timer.empty()

    if "err" in _fva_err:
        st.error(f"FVA failed: {_fva_err['err']}")
    else:
        st.session_state["fva_df"] = _fva_box["df"]
        st.success(f"FVA completed in {int(_fva_elapsed // 60)}m {int(_fva_elapsed % 60):02d}s")

if st.session_state.get("fva_df") is not None:
    fva_df: pd.DataFrame = st.session_state["fva_df"]

    if fva_df.empty:
        st.warning("FVA returned no results.")
    else:
        st.plotly_chart(fva_range_chart(fva_df, key_reaction_ids=key_nutrients), use_container_width=True)

        with st.expander("📋 FVA Results Table", expanded=False):
            display = fva_df[fva_df["reaction_id"].isin(key_nutrients)][
                ["reaction_id", "metabolite_name", "minimum", "maximum"]
            ].rename(columns={
                "reaction_id": "Reaction ID",
                "metabolite_name": "Nutrient",
                "minimum": "Min Flux",
                "maximum": "Max Flux",
            })
            st.dataframe(display, use_container_width=True)

else:
    st.info("Click **Run FVA** to compute feasible uptake ranges for the selected nutrients.")

st.divider()

# --- Concentration ranges ---

st.subheader("Nutrient Concentration Ranges")
st.markdown(
    "Define the minimum and maximum uptake rates (mmol/gDW/h) for each selected nutrient. "
    "FVA-derived suggestions are pre-filled where available."
)

fva_df = st.session_state.get("fva_df", pd.DataFrame())
suggested_ranges = suggest_ranges_from_fva(fva_df, key_nutrients) if not fva_df.empty else {}

# Get display names from essentiality DF
ess_df: pd.DataFrame = st.session_state.get("essentiality_df", pd.DataFrame())
name_map = {}
if not ess_df.empty:
    name_map = dict(zip(ess_df["reaction_id"], ess_df["metabolite_name"]))

nutrient_ranges: dict[str, tuple[float, float]] = {}
prev_ranges = st.session_state.get("nutrient_ranges", {})

for rxn_id in key_nutrients:
    display_name = name_map.get(rxn_id, rxn_id)
    lo_default, hi_default = prev_ranges.get(rxn_id, suggested_ranges.get(rxn_id, (0.0, 10.0)))

    with st.expander(f"📌 {display_name} (`{rxn_id}`)", expanded=True):
        c1, c2 = st.columns(2)
        with c1:
            lo = st.number_input(
                f"Min (mmol/gDW/h)",
                min_value=0.0,
                value=float(lo_default),
                step=0.5,
                key=f"lo_{rxn_id}",
            )
        with c2:
            hi = st.number_input(
                f"Max (mmol/gDW/h)",
                min_value=0.0,
                value=float(hi_default),
                step=0.5,
                key=f"hi_{rxn_id}",
            )
        if hi <= lo:
            st.warning("Max must be greater than Min.")
        else:
            nutrient_ranges[rxn_id] = (lo, hi)

st.divider()

# --- DoE design type ---

st.subheader("Experimental Design")
info_tooltip("DoE", "doe")

col_design, col_preview = st.columns([1, 2])

with col_design:
    n = len(key_nutrients)
    available_designs = {k: v for k, v in DESIGN_TYPES.items()}
    if n < 3:
        available_designs.pop("Box-Behnken", None)
        available_designs.pop("Plackett-Burman", None)

    design_label = st.selectbox("DoE design type", list(available_designs.keys()))
    design_type = available_designs[design_label]

    n_runs = experiment_count(n, design_type)
    st.metric("Estimated number of experiments", n_runs)

    if n_runs > 100:
        st.warning(f"This design produces {n_runs} experiments. Consider reducing factors or using Plackett-Burman.")

with col_preview:
    st.markdown("**Design type guide:**")
    st.markdown(
        """
- **Central Composite (Face-Centred):** Best for response surface models. Each factor has 3 levels (lo, mid, hi).
- **Box-Behnken:** Fewer experiments than CCC; no corner points. Requires ≥3 factors.
- **Plackett-Burman:** Screening design — identifies important factors with minimal runs.
- **Full Factorial (2-level):** Tests all combinations of lo/hi; grows exponentially.
"""
    )

# --- Generate DoE ---

st.divider()

valid_ranges = {k: v for k, v in nutrient_ranges.items() if v[1] > v[0]}

if len(valid_ranges) < 2:
    st.warning("Define valid (min < max) ranges for at least 2 nutrients before generating the DoE.")
else:
    if st.button("🧪 Generate DoE Matrix", type="primary"):
        try:
            doe_df = generate_doe(list(valid_ranges.keys()), valid_ranges, design_type)
            # Replace reaction IDs with display names in column headers
            doe_df.columns = [name_map.get(c, c) for c in doe_df.columns]
            st.session_state["doe_df"] = doe_df
            st.session_state["nutrient_ranges"] = nutrient_ranges
        except Exception as e:
            st.error(f"Failed to generate DoE: {e}")

    doe_df: pd.DataFrame | None = st.session_state.get("doe_df")

    if doe_df is not None:
        st.success(f"DoE matrix generated: **{len(doe_df)} experiments × {len(doe_df.columns)} factors**")

        st.dataframe(doe_df, use_container_width=True, height=300)

        if len(doe_df.columns) >= 2:
            st.plotly_chart(doe_parallel_coordinates(doe_df), use_container_width=True)

# --- Navigation ---

st.divider()
col_back, col_fwd = st.columns(2)
with col_back:
    st.page_link("pages/04_Analysis.py", label="← Back to Step 4: Analysis", icon="🔬")
with col_fwd:
    if st.session_state.get("doe_df") is not None:
        st.page_link("pages/06_Export.py", label="→ Go to Step 6: Export", icon="📥")
    else:
        st.info("Generate a DoE matrix to proceed.")
