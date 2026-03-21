"""
Step 4 — Analysis
Run nutrient essentiality screen and shadow price (sensitivity) analysis.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import threading
import time

import streamlit as st
import pandas as pd
import cobra

from core.fba_analysis import (
    nutrient_essentiality, nutrient_sensitivity, get_baseline_growth,
)
from app.components.charts import essentiality_chart, shadow_price_chart
from app.components.widgets import (
    page_header, step_progress_sidebar, session_state_guard,
    info_tooltip, classification_badge,
)

st.set_page_config(page_title="Step 4 — Analysis", page_icon="🔬", layout="wide")

step_progress_sidebar(4)
page_header("Step 4: Analysis", "Identify essential nutrients and rank by growth impact")

if not session_state_guard(["model", "objective_reaction"], "Analysis"):
    st.stop()

model: cobra.Model = st.session_state["model"]

# --- Run analysis ---

col_run, col_info = st.columns([1, 3])
with col_run:
    run_btn = st.button("▶️ Run Analysis", type="primary")
with col_info:
    st.caption(
        "This screen tests each nutrient by removing it from the medium and re-running FBA. "
        "It may take 10–60 seconds depending on model size."
    )

if run_btn or (
    st.session_state.get("essentiality_df") is not None
    and not st.session_state["essentiality_df"].empty
):
    if run_btn:
        # --- Essentiality screen with live timer ---
        _ess_box: dict = {}
        _ess_err: dict = {}

        def _run_essentiality():
            try:
                _ess_box["df"] = nutrient_essentiality(model)
            except Exception as _e:
                _ess_err["err"] = _e

        _t = threading.Thread(target=_run_essentiality, daemon=True)
        _t.start()
        _ess_status = st.empty()
        _ess_timer = st.empty()
        _t0 = time.time()
        while _t.is_alive():
            _elapsed = time.time() - _t0
            _ess_status.info("Running essentiality screen…")
            _ess_timer.caption(f"⏱️ Elapsed: {int(_elapsed // 60)}m {int(_elapsed % 60):02d}s")
            time.sleep(1)
        _t.join()
        _elapsed = time.time() - _t0
        _ess_status.empty()
        _ess_timer.empty()

        if "err" in _ess_err:
            st.error(f"Essentiality analysis failed: {_ess_err['err']}")
            st.stop()

        ess_df = _ess_box["df"]
        st.session_state["essentiality_df"] = ess_df
        st.success(f"Essentiality screen completed in {int(_elapsed // 60)}m {int(_elapsed % 60):02d}s")

        # --- Shadow prices with live timer ---
        _sp_box: dict = {}
        _sp_err: dict = {}

        def _run_shadow():
            try:
                _sp_box["df"] = nutrient_sensitivity(model)
            except Exception as _e:
                _sp_err["err"] = _e

        _t2 = threading.Thread(target=_run_shadow, daemon=True)
        _t2.start()
        _sp_status = st.empty()
        _sp_timer = st.empty()
        _t1 = time.time()
        while _t2.is_alive():
            _elapsed2 = time.time() - _t1
            _sp_status.info("Computing shadow prices…")
            _sp_timer.caption(f"⏱️ Elapsed: {int(_elapsed2 // 60)}m {int(_elapsed2 % 60):02d}s")
            time.sleep(1)
        _t2.join()
        _elapsed2 = time.time() - _t1
        _sp_status.empty()
        _sp_timer.empty()

        if "err" in _sp_err:
            st.warning(f"Shadow price computation failed: {_sp_err['err']}")
            shadow_df = pd.DataFrame()
        else:
            shadow_df = _sp_box["df"]
            st.success(f"Shadow prices computed in {int(_elapsed2 // 60)}m {int(_elapsed2 % 60):02d}s")
        st.session_state["shadow_df"] = shadow_df

        baseline = get_baseline_growth(model)
        st.session_state["baseline_growth"] = baseline

    ess_df: pd.DataFrame = st.session_state.get("essentiality_df", pd.DataFrame())
    shadow_df: pd.DataFrame = st.session_state.get("shadow_df", pd.DataFrame())
    baseline: float = st.session_state.get("baseline_growth", 0.0)

    if ess_df.empty:
        st.warning(
            "No nutrients were found with active uptake bounds. "
            "Apply a medium preset in Step 1 before running analysis."
        )
        st.stop()

    st.metric("Baseline Growth Rate", f"{baseline:.4f} h⁻¹")

    # --- Summary counts ---

    st.divider()
    st.subheader("Essentiality Summary")
    info_tooltip("essentiality", "essentiality")

    counts = ess_df["classification"].value_counts()
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("🔴 Essential", counts.get("essential", 0),
                  help="Removal causes growth < 1% of baseline")
    with c2:
        st.metric("🟡 Enhancing", counts.get("enhancing", 0),
                  help="Removal reduces growth by 10–99%")
    with c3:
        st.metric("🟢 Dispensable", counts.get("dispensable", 0),
                  help="Removal has little effect on growth")

    # --- Essentiality chart ---

    st.plotly_chart(essentiality_chart(ess_df), use_container_width=True)

    # Essentiality table (expandable)
    with st.expander("📋 Essentiality Table", expanded=False):
        display_df = ess_df.copy()
        display_df["Classification"] = display_df["classification"].apply(
            lambda c: classification_badge(c)
        )
        st.dataframe(
            ess_df[["metabolite_name", "reaction_id", "growth_ratio", "classification"]].rename(columns={
                "metabolite_name": "Nutrient",
                "reaction_id": "Reaction ID",
                "growth_ratio": "Growth Ratio",
                "classification": "Classification",
            }),
            use_container_width=True,
        )

    st.divider()

    # --- Shadow price analysis ---

    st.subheader("Nutrient Sensitivity (Shadow Prices)")
    info_tooltip("shadow price", "shadow_price")

    if shadow_df.empty:
        st.info("Shadow price analysis returned no results. The model LP may be degenerate.")
    else:
        _max_n = min(30, len(shadow_df))
        top_n = st.slider("Show top N nutrients", min_value=min(5, _max_n), max_value=_max_n, value=min(15, _max_n))
        st.plotly_chart(shadow_price_chart(shadow_df, top_n=top_n), use_container_width=True)

        with st.expander("📋 Shadow Price Table", expanded=False):
            st.dataframe(
                shadow_df[["metabolite_name", "reaction_id", "shadow_price", "abs_shadow_price"]].head(top_n).rename(columns={
                    "metabolite_name": "Metabolite",
                    "reaction_id": "Reaction ID",
                    "shadow_price": "Shadow Price",
                    "abs_shadow_price": "|Shadow Price|",
                }),
                use_container_width=True,
            )

    st.divider()

    # --- Key nutrient selection ---

    st.subheader("Select Key Nutrients for DoE")
    st.markdown(
        "Choose the nutrients to include in the experimental design. "
        "The analysis pre-selects essential and high-sensitivity nutrients."
    )

    # Auto-select: all essential + top-5 by shadow price
    auto_essential = set(ess_df[ess_df["classification"] == "essential"]["reaction_id"].tolist())
    auto_shadow = set(shadow_df.head(5)["reaction_id"].tolist()) if not shadow_df.empty else set()
    auto_selected = auto_essential | auto_shadow

    all_nutrients = ess_df[["reaction_id", "metabolite_name", "classification"]].copy()

    options = {
        row["reaction_id"]: f"{row['metabolite_name']} ({row['classification']})"
        for _, row in all_nutrients.iterrows()
    }

    # Filter out trivial metabolites
    exclude = {"EX_h2o_e", "EX_h_e", "EX_co2_e"}
    options = {k: v for k, v in options.items() if k not in exclude}
    default_selected = [k for k in auto_selected if k in options]

    key_nutrients = st.multiselect(
        "Key nutrients for DoE (select 2–8 for best results)",
        list(options.keys()),
        default=default_selected,
        format_func=lambda x: options.get(x, x),
    )

    if len(key_nutrients) < 2:
        st.warning("Select at least 2 nutrients to generate a DoE matrix.")
    elif len(key_nutrients) > 10:
        st.warning("Selecting > 10 nutrients will produce a very large DoE. Consider narrowing to the top 8.")

    if key_nutrients and st.button("✅ Save Selection & Continue", type="primary"):
        st.session_state["key_nutrients"] = key_nutrients
        st.success(f"Saved {len(key_nutrients)} key nutrients.")

    if st.session_state.get("key_nutrients"):
        col_back, col_fwd = st.columns(2)
        with col_back:
            st.page_link("pages/03_Objective.py", label="← Back to Step 3: Objective", icon="🎯")
        with col_fwd:
            st.page_link("pages/05_Design_Space.py", label="→ Go to Step 5: Design Space", icon="🧪")
    else:
        st.page_link("pages/03_Objective.py", label="← Back to Step 3: Objective", icon="🎯")

else:
    st.info("Click **Run Analysis** to begin the nutrient essentiality and sensitivity screen.")
    st.page_link("pages/03_Objective.py", label="← Back to Step 3: Objective", icon="🎯")
