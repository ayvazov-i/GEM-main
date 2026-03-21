"""
Step 3 — Set Objective
Choose what to optimise: growth rate (biomass) or a specific product reaction.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import streamlit as st
import cobra

from app.components.widgets import (
    page_header, step_progress_sidebar, session_state_guard, info_tooltip,
)

st.set_page_config(page_title="Step 3 — Objective", page_icon="🎯", layout="wide")

step_progress_sidebar(3)
page_header("Step 3: Set Objective", "Choose what the model should optimise")

if not session_state_guard(["model"], "Set Objective"):
    st.stop()

model: cobra.Model = st.session_state["model"]

info_tooltip("biomass_reaction", "biomass_reaction")

# --- Objective type ---

obj_type = st.radio(
    "Optimisation objective",
    ["Maximise Growth Rate (Biomass)", "Maximise Product Flux"],
    help="Growth rate is the default objective. Switch to Product Flux if you have a "
         "specific metabolic product in mind.",
)

objective_reaction: str | None = None

if obj_type == "Maximise Growth Rate (Biomass)":
    # Find biomass reaction candidates
    biomass_candidates = [
        r for r in model.reactions
        if "biomass" in r.id.lower() or "growth" in r.id.lower()
    ]

    if biomass_candidates:
        # Show current objective
        current_obj_rxn = None
        for rxn in model.reactions:
            obj_coeff = model.objective.get_linear_coefficients([rxn.forward_variable])
            if list(obj_coeff.values())[0] > 0:
                current_obj_rxn = rxn.id
                break

        options = {r.id: f"{r.id} — {r.name or 'Biomass reaction'}" for r in biomass_candidates}
        default_idx = 0
        if current_obj_rxn in options:
            default_idx = list(options.keys()).index(current_obj_rxn)

        chosen_rxn = st.selectbox(
            "Biomass / growth reaction",
            list(options.keys()),
            index=default_idx,
            format_func=lambda x: options[x],
        )
        objective_reaction = chosen_rxn

    else:
        st.warning(
            "No reaction with 'biomass' or 'growth' in its ID was found. "
            "You can type a reaction ID below."
        )
        # Safely derive a default text value from the current objective.
        # model.objective.to_json() returns a deeply-nested structure that varies
        # between COBRApy versions — wrap it to avoid crashes on unexpected formats.
        try:
            _obj_default = (
                model.objective.to_json()
                .get("expression", {})
                .get("args", [{}])[0]
                .get("args", [{}])[0]
                .get("name", "")
                if hasattr(model.objective, "to_json") else ""
            )
        except (AttributeError, IndexError, TypeError):
            _obj_default = ""
        typed_rxn = st.text_input(
            "Enter the growth/biomass reaction ID manually",
            value=_obj_default,
        )
        if typed_rxn.strip():
            if typed_rxn.strip() in model.reactions:
                objective_reaction = typed_rxn.strip()
            else:
                st.error(f"Reaction `{typed_rxn.strip()}` not found in the model.")

    # Show current objective
    current_sol = None
    if objective_reaction:
        with model:
            model.objective = model.reactions.get_by_id(objective_reaction)
            sol = model.optimize()
            if sol.status == "optimal":
                current_sol = sol.objective_value

        if current_sol is not None:
            st.metric("Predicted Growth Rate", f"{current_sol:.4f} h⁻¹")

else:
    st.info(
        "Enter the ID of the reaction whose flux you want to maximise "
        "(e.g. `EX_etoh_e` for ethanol, `DM_succ_c` for succinate)."
    )

    # Autocomplete: list all reactions
    rxn_ids = [r.id for r in model.reactions]
    rxn_display = [f"{r.id} — {r.name}" if r.name else r.id for r in model.reactions]

    product_rxn = st.selectbox(
        "Product reaction",
        rxn_ids,
        format_func=lambda x: next(
            (d for i, d in zip(rxn_ids, rxn_display) if i == x), x
        ),
    )
    objective_reaction = product_rxn

    # Preview predicted flux
    if objective_reaction:
        with model:
            model.objective = model.reactions.get_by_id(objective_reaction)
            sol = model.optimize()
            if sol.status == "optimal":
                st.metric(
                    f"Predicted flux through {objective_reaction}",
                    f"{sol.objective_value:.4f} mmol/gDW/h",
                )
            else:
                st.warning("Model is infeasible with this objective.")

st.divider()

# --- Confirm and save ---

if objective_reaction:
    rxn = model.reactions.get_by_id(objective_reaction)
    st.success(
        f"Objective: **{rxn.id}** — {rxn.name or 'unnamed reaction'}"
    )

    if st.button("✅ Confirm Objective & Continue", type="primary"):
        # Apply objective to the stored model
        model.objective = model.reactions.get_by_id(objective_reaction)
        st.session_state["model"] = model
        st.session_state["objective_reaction"] = objective_reaction
        st.session_state["objective_type"] = obj_type
        st.success("Objective saved.")

if st.session_state.get("objective_reaction"):
    col_back, col_fwd = st.columns(2)
    with col_back:
        st.page_link("pages/02_Model_Summary.py", label="← Back to Step 2: Model Summary", icon="📊")
    with col_fwd:
        st.page_link("pages/04_Analysis.py", label="→ Go to Step 4: Analysis", icon="🔬")
else:
    st.page_link("pages/02_Model_Summary.py", label="← Back to Step 2: Model Summary", icon="📊")
