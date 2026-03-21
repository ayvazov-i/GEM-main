"""
Utility functions: model loading, media application, data file helpers.
"""
import json
import os
import pathlib

import cobra
import cobra.io

DATA_DIR = pathlib.Path(__file__).parent.parent / "data"
MEDIA_LIBRARY_PATH = DATA_DIR / "media_library.json"
VALIDATION_DATA_PATH = DATA_DIR / "validation_growth_rates.json"
METABOLITE_MAP_PATH = DATA_DIR / "metabolite_map.json"
EXAMPLE_MODELS_DIR = DATA_DIR / "example_models"

# Metabolite map cache
_metabolite_map: dict | None = None


def load_metabolite_map() -> dict:
    global _metabolite_map
    if _metabolite_map is None:
        with open(METABOLITE_MAP_PATH) as f:
            _metabolite_map = json.load(f)
    return _metabolite_map


def get_metabolite_display_name(met_id: str) -> str:
    """Return a human-readable name for a metabolite ID."""
    met_map = load_metabolite_map()
    # The map may be nested; try flat lookup first
    if isinstance(met_map, dict):
        for key, val in met_map.items():
            if isinstance(val, dict):
                if met_id in val:
                    entry = val[met_id]
                    if isinstance(entry, dict):
                        return entry.get("name", met_id)
                    return str(entry)
            elif key == met_id:
                return str(val)
    return met_id


def load_media_library() -> dict:
    with open(MEDIA_LIBRARY_PATH) as f:
        data = json.load(f)
    return data.get("media", {})


def load_validation_data() -> dict:
    with open(VALIDATION_DATA_PATH) as f:
        data = json.load(f)
    return data.get("media", {})


def list_example_models() -> list[dict]:
    """Return list of available example SBML models with metadata."""
    models = []
    name_map = {
        "iML1515": "E. coli K-12 MG1655 (iML1515)",
        "iYO844": "B. subtilis 168 (iYO844)",
        "iMM904": "S. cerevisiae S288C (iMM904)",
        "iJN1463": "P. putida KT2440 (iJN1463)",
    }
    for xml_file in sorted(EXAMPLE_MODELS_DIR.glob("*.xml")):
        stem = xml_file.stem
        models.append({
            "id": stem,
            "display_name": name_map.get(stem, stem),
            "path": str(xml_file),
        })
    return models


def load_model(path: str) -> cobra.Model:
    """Load a COBRA model from an SBML file path."""
    return cobra.io.read_sbml_model(path)


def apply_media(model: cobra.Model, exchange_bounds: dict) -> None:
    """
    Apply a medium to a model in-place.

    This sets the lower bounds of the specified exchange reactions to restrict
    (or open) nutrient uptake.  Only reactions present in the model are
    modified; others are left at their current bounds.

    exchange_bounds: {reaction_id: max_uptake_rate (positive float)}
        A positive value means "allow uptake up to this rate".
        A value of 0 means "block uptake entirely".

    Note: This does NOT close exchanges not listed in exchange_bounds.
    This is intentional: trace elements and cofactors not included in a
    named medium preset should remain at the model's defaults, because GEMs
    often include implicit trace-element transport that is not part of the
    nutritional question being asked.
    """
    for rxn_id, bound in exchange_bounds.items():
        if rxn_id in model.reactions:
            rxn = model.reactions.get_by_id(rxn_id)
            rxn.lower_bound = -float(bound)  # uptake: negative lower bound


def exchange_reaction_display_name(rxn: cobra.Reaction) -> str:
    """Get a clean display name for an exchange reaction."""
    if rxn.name:
        return rxn.name
    # Try to get name from metabolites
    for met in rxn.metabolites:
        if met.name:
            return met.name
    return rxn.id


def format_growth_rate(rate: float | None) -> str:
    if rate is None or rate <= 0:
        return "0.000 h⁻¹"
    return f"{rate:.4f} h⁻¹"
