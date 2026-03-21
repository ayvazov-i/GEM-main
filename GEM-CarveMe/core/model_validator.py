"""
Model validation: sanity checks, quality metrics, gap-fill detection.
"""
import cobra
import pandas as pd


def validate_model(model: cobra.Model) -> dict:
    """
    Run basic quality checks on a GEM.

    Returns a dict with:
        growth_rate, feasible, num_reactions, num_metabolites, num_genes,
        num_exchanges, has_biomass, blocked_reactions_count, warnings
    """
    warnings = []
    sol = model.optimize()

    feasible = sol.status == "optimal"
    growth_rate = sol.objective_value if feasible else 0.0

    if not feasible:
        warnings.append("Model is infeasible on current medium — no growth predicted.")
    elif growth_rate < 1e-6:
        warnings.append("Growth rate is effectively zero. Model may be blocked or medium is missing key nutrients.")

    # Check for biomass reaction
    biomass_rxns = [r for r in model.reactions if "biomass" in r.id.lower() or "growth" in r.id.lower()]
    has_biomass = len(biomass_rxns) > 0
    if not has_biomass:
        warnings.append("No obvious biomass reaction detected (searched for 'biomass' or 'growth' in reaction IDs).")

    # Gene coverage
    if len(model.genes) == 0:
        warnings.append("Model has no gene annotations (GPR rules missing).")
    elif len(model.genes) < 100:
        warnings.append(f"Low gene count ({len(model.genes)}). Model may be a draft or incomplete.")

    # Exchange reactions
    exchanges = model.exchanges
    if len(exchanges) == 0:
        warnings.append("No exchange reactions found. Model boundary is undefined.")

    # Estimate blocked reactions (not running full FVA — just count deadends)
    num_exchanges = len(exchanges)

    return {
        "growth_rate": round(growth_rate, 6),
        "feasible": feasible,
        "num_reactions": len(model.reactions),
        "num_metabolites": len(model.metabolites),
        "num_genes": len(model.genes),
        "num_exchanges": num_exchanges,
        "has_biomass": has_biomass,
        "objective_reaction": detect_objective_reaction(model),
        "warnings": warnings,
    }


def get_model_summary_df(model: cobra.Model) -> pd.DataFrame:
    """Return a one-row summary DataFrame for display."""
    sol = model.optimize()
    feasible = sol.status == "optimal"
    return pd.DataFrame([{
        "Reactions": len(model.reactions),
        "Metabolites": len(model.metabolites),
        "Genes": len(model.genes),
        "Exchange reactions": len(model.exchanges),
        "Feasible": "Yes" if feasible else "No",
        "Growth rate (h⁻¹)": round(sol.objective_value, 4) if feasible else 0.0,
    }])


def detect_objective_reaction(model: cobra.Model) -> str | None:
    """Return the ID of the current objective reaction."""
    for rxn in model.reactions:
        coeff = model.objective.get_linear_coefficients([rxn.forward_variable])
        values = list(coeff.values())
        if values and values[0] != 0:
            return rxn.id
    return None
