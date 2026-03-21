"""
Step 1 — Upload Model
Upload an SBML model or select a pre-built demo model. Optionally apply a media preset.
"""
import sys
import os
import tempfile
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import streamlit as st

from core.utils import list_example_models, load_model, load_media_library, apply_media
from app.components.widgets import page_header, step_progress_sidebar, info_tooltip

st.set_page_config(page_title="Step 1 — Upload", page_icon="📁", layout="wide")

step_progress_sidebar(1)
page_header("Step 1: Upload Model", "Load your metabolic model to begin analysis")

info_tooltip("GEM", "gem")

# --- Source selection ---

source = st.radio(
    "Model source",
    ["Use a demo model", "Upload your own SBML (.xml)"],
    horizontal=True,
)

model_path: str | None = None
model_name: str | None = None

if source == "Use a demo model":
    examples = list_example_models()
    if not examples:
        st.error("No example models found in data/example_models/. Please add SBML files there.")
    else:
        options = {m["display_name"]: m for m in examples}
        chosen_name = st.selectbox("Select a demo organism", list(options.keys()))
        chosen = options[chosen_name]
        model_path = chosen["path"]
        model_name = chosen["display_name"]
        st.success(f"Selected: **{model_name}** (`{os.path.basename(model_path)}`)")

else:
    uploaded = st.file_uploader(
        "Upload an SBML model (.xml)",
        type=["xml"],
        help="Upload a COBRA-compatible SBML model file.",
    )
    if uploaded:
        tmp_dir = tempfile.mkdtemp()
        tmp_path = os.path.join(tmp_dir, uploaded.name)
        with open(tmp_path, "wb") as f:
            f.write(uploaded.read())
        model_path = tmp_path
        model_name = os.path.splitext(uploaded.name)[0]
        st.success(f"Uploaded: **{uploaded.name}**")

# --- Optional: genome upload for CarveMe (advanced) ---

with st.expander("⚙️ Advanced: Generate GEM from genome (requires CarveMe)"):
    st.warning(
        "CarveMe integration is an advanced feature that requires Diamond and Prodigal "
        "to be installed at the system level. For the MVP, use a pre-built SBML model above."
    )
    genome_file = st.file_uploader(
        "Upload an annotated genome (.gbk or .fasta)",
        type=["gbk", "gb", "fasta", "fa", "fna"],
    )
    gram = st.radio("Gram stain", ["negative", "positive"], horizontal=True)

    from core.gem_generator import is_carveme_available
    carveme_ok = is_carveme_available()
    if not carveme_ok:
        st.error(
            "CarveMe CLI (`carve`) is not found on PATH. "
            "Install CarveMe and its dependencies (Diamond, Prodigal) to use this feature, "
            "or upload a pre-built SBML model above."
        )

    if genome_file and carveme_ok and st.button("Generate GEM with CarveMe"):
        from core.gem_generator import generate_gem_from_genome
        import cobra.io

        tmp_genome = os.path.join(tempfile.mkdtemp(), genome_file.name)
        with open(tmp_genome, "wb") as f:
            f.write(genome_file.read())

        # Run CarveMe in a background thread so we can update the elapsed-time display.
        result_box: dict = {}
        error_box: dict = {}

        def _run_carveme():
            try:
                result_box["model"] = generate_gem_from_genome(tmp_genome, gram=gram)
            except Exception as exc:
                error_box["err"] = exc

        thread = threading.Thread(target=_run_carveme, daemon=True)
        thread.start()

        status_ph = st.empty()
        timer_ph = st.empty()
        start_ts = time.time()
        while thread.is_alive():
            elapsed = time.time() - start_ts
            status_ph.info("Running CarveMe — Diamond alignment + Prodigal gene prediction…")
            timer_ph.caption(f"⏱️ Elapsed: {int(elapsed // 60)}m {int(elapsed % 60):02d}s")
            time.sleep(1)
        thread.join()

        elapsed = time.time() - start_ts
        status_ph.empty()
        timer_ph.empty()

        if "err" in error_box:
            st.error(f"CarveMe failed: {error_box['err']}")
        else:
            gem_model = result_box["model"]
            tmp_xml = os.path.join(tempfile.mkdtemp(), "draft_gem.xml")
            cobra.io.write_sbml_model(gem_model, tmp_xml)
            model_path = tmp_xml
            model_name = genome_file.name.rsplit(".", 1)[0] + " (draft GEM)"
            st.success(
                f"GEM generated in {int(elapsed // 60)}m {int(elapsed % 60):02d}s — "
                f"{len(gem_model.reactions)} reactions, {len(gem_model.genes)} genes."
            )

# --- Media preset ---

st.divider()
st.subheader("Medium Configuration")
info_tooltip("exchange reaction", "exchange_reaction")

media_lib = load_media_library()
media_options = {"(Model default — do not change)": None}
media_options.update({v["display_name"]: k for k, v in media_lib.items()})

chosen_medium_label = st.selectbox(
    "Apply a medium preset (optional)",
    list(media_options.keys()),
    help="Sets the exchange reaction bounds to simulate this growth medium. "
         "If unsure, leave as model default.",
)
chosen_medium_key = media_options[chosen_medium_label]

if chosen_medium_key and media_lib.get(chosen_medium_key):
    med = media_lib[chosen_medium_key]
    st.info(f"**{med['display_name']}** — {med['description']}")
    st.caption(
        f"Expected growth rate: {med['expected_growth_rate_range'][0]}–"
        f"{med['expected_growth_rate_range'][1]} h⁻¹  |  "
        f"Nutrient count: {len(med['exchange_bounds'])}"
    )

# --- Load model button ---

st.divider()

if model_path:
    if st.button("✅ Load Model & Continue", type="primary"):
        with st.spinner("Loading model..."):
            try:
                model = load_model(model_path)
                if chosen_medium_key and media_lib.get(chosen_medium_key):
                    apply_media(model, media_lib[chosen_medium_key]["exchange_bounds"])

                st.session_state["model"] = model
                st.session_state["model_path"] = model_path
                st.session_state["model_name"] = model_name or model.id
                st.session_state["chosen_medium_key"] = chosen_medium_key
                st.session_state["chosen_medium_label"] = chosen_medium_label

                # Clear downstream results when a new model is loaded
                for key in ["validation_result", "objective_reaction",
                            "essentiality_df", "shadow_df", "fva_df",
                            "key_nutrients", "nutrient_ranges", "doe_df"]:
                    st.session_state.pop(key, None)

                st.success(
                    f"Model loaded: **{model.id}** — "
                    f"{len(model.reactions)} reactions, "
                    f"{len(model.metabolites)} metabolites, "
                    f"{len(model.genes)} genes."
                )
                st.balloons()

            except Exception as e:
                st.error(f"Failed to load model: {e}")

    if st.session_state.get("model_path") == model_path and st.session_state.get("model"):
        st.page_link("pages/02_Model_Summary.py", label="→ Go to Step 2: Model Summary", icon="📊")
else:
    st.info("Select or upload a model above to proceed.")
