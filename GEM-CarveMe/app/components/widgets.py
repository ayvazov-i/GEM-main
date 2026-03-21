"""
Reusable Streamlit UI components.
"""
import streamlit as st


STEPS = [
    ("1", "Upload Model"),
    ("2", "Model Summary"),
    ("3", "Set Objective"),
    ("4", "Analysis"),
    ("5", "Design Space"),
    ("6", "Export"),
]

STEP_PAGES = {
    1: "pages/01_Upload.py",
    2: "pages/02_Model_Summary.py",
    3: "pages/03_Objective.py",
    4: "pages/04_Analysis.py",
    5: "pages/05_Design_Space.py",
    6: "pages/06_Export.py",
}

# Plain-language tooltips for GEM jargon
TOOLTIPS = {
    "shadow_price": (
        "Shadow Price measures how much the growth rate would change if slightly more "
        "of a given nutrient were available. A high shadow price means the nutrient is "
        "currently limiting growth."
    ),
    "fva": (
        "Flux Variability Analysis (FVA) finds the range of possible uptake/secretion "
        "rates for each nutrient that still allows the cell to grow at (or near) "
        "its maximum rate."
    ),
    "fba": (
        "Flux Balance Analysis (FBA) predicts the optimal distribution of metabolic "
        "fluxes that maximises a chosen objective (e.g. growth rate), subject to the "
        "stoichiometric constraints of the metabolic network."
    ),
    "exchange_reaction": (
        "An exchange reaction represents a nutrient entering or leaving the cell. "
        "Setting its lower bound controls the maximum uptake rate of that nutrient "
        "in units of mmol per gram dry weight per hour (mmol/gDW/h)."
    ),
    "essentiality": (
        "Essential nutrients are those whose removal causes growth to drop below 1% "
        "of baseline. Enhancing nutrients reduce growth by 10–99% when removed. "
        "Dispensable nutrients have little effect on growth when removed."
    ),
    "doe": (
        "Design of Experiments (DoE) is a statistical approach to planning experiments "
        "efficiently. Instead of testing every combination, DoE selects a structured "
        "subset that maps the design space with the fewest runs."
    ),
    "biomass_reaction": (
        "The biomass reaction represents cell growth. It consumes all the building "
        "blocks (amino acids, lipids, nucleotides, etc.) in proportions needed to "
        "make new cells. Maximising its flux predicts maximum growth rate."
    ),
    "gem": (
        "A Genome-Scale Metabolic Model (GEM) encodes all known metabolic reactions "
        "of an organism derived from its genome. It can predict growth rates and "
        "metabolic fluxes for arbitrary nutrient conditions."
    ),
}


def info_tooltip(label: str, key: str) -> None:
    """Render a label with an info expander containing a plain-language tooltip."""
    tooltip = TOOLTIPS.get(key, "")
    if tooltip:
        with st.expander(f"ℹ️ What is {label}?", expanded=False):
            st.caption(tooltip)


def step_progress_sidebar(current_step: int) -> None:
    """Render a step progress indicator in the sidebar."""
    st.sidebar.markdown("### Workflow Progress")
    for num, name in STEPS:
        step_num = int(num)
        if step_num < current_step:
            icon = "✅"
        elif step_num == current_step:
            icon = "▶️"
        else:
            icon = "⬜"
        st.sidebar.markdown(f"{icon} **Step {num}:** {name}")
    st.sidebar.divider()


def session_state_guard(required_keys: list[str], step_name: str) -> bool:
    """
    Check that required session_state keys are set.
    If not, show a warning and return False.
    """
    missing = [k for k in required_keys if not st.session_state.get(k)]
    if missing:
        st.warning(
            f"⚠️ Please complete earlier steps before accessing **{step_name}**. "
            f"Missing: {', '.join(missing)}."
        )
        st.info("Use the sidebar to navigate to **Step 1: Upload Model** and work through the wizard.")
        return False
    return True


def metric_card(label: str, value: str, delta: str | None = None, help_text: str | None = None) -> None:
    """Render a single metric card."""
    st.metric(label=label, value=value, delta=delta, help=help_text)


def classification_badge(classification: str) -> str:
    """Return a coloured HTML badge for an essentiality classification."""
    colours = {
        "essential": ("#e74c3c", "white"),
        "enhancing": ("#f39c12", "white"),
        "dispensable": ("#2ecc71", "white"),
    }
    bg, fg = colours.get(classification, ("#95a5a6", "white"))
    return (
        f'<span style="background-color:{bg}; color:{fg}; '
        f'padding:2px 8px; border-radius:4px; font-size:0.85em;">'
        f'{classification.capitalize()}</span>'
    )


def page_header(title: str, subtitle: str = "") -> None:
    st.title(title)
    if subtitle:
        st.markdown(f"_{subtitle}_")
    st.divider()
