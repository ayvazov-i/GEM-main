"""
FBA, nutrient essentiality, shadow price analysis, and FVA.
"""
import warnings

import cobra
import pandas as pd
from cobra.flux_analysis import flux_variability_analysis

from core.utils import exchange_reaction_display_name


# --- Exchange reaction filter ---

EXCLUDE_EXCHANGE_IDS = {
    "EX_h2o_e", "EX_h_e", "EX_co2_e",  # outputs / always-open
}


def _is_analysable_exchange(rxn: cobra.Reaction) -> bool:
    """Skip proton, water, and CO2 exchanges — not nutritional."""
    return rxn.id not in EXCLUDE_EXCHANGE_IDS


def _configure_solver(model: cobra.Model) -> None:
    """
    Apply GLPK solver settings that prevent the alloc.c:70 assertion error.

    The error fires when GLPK's simplex reaches a degenerate state during
    repeated solves (FVA, essentiality loops).  Forcing presolve=True makes
    GLPK normalise the LP before every solve, which eliminates the degenerate
    bases that trigger the internal xassert(size > 0) failure.
    """
    try:
        cfg = model.solver.configuration
        cfg.presolve = True                    # force presolve on every LP
        cfg.tolerances.feasibility = 1e-6     # slightly looser than default 1e-7
        cfg.verbosity = 0                      # suppress GLPK console output
    except Exception:
        pass  # non-GLPK solver — no action needed


# --- FBA ---

def run_fba(model: cobra.Model) -> cobra.Solution:
    _configure_solver(model)
    sol = model.optimize()
    return sol


def get_baseline_growth(model: cobra.Model) -> float:
    _configure_solver(model)
    sol = model.optimize()
    if sol.status == "optimal":
        return sol.objective_value
    return 0.0


# --- Nutrient Essentiality ---

def nutrient_essentiality(model: cobra.Model) -> pd.DataFrame:
    """
    For each uptake-capable exchange reaction, close it and re-run FBA.
    Classify nutrients as:
        essential   — growth drops to <1% of baseline
        enhancing   — growth drops to 1–90% of baseline
        dispensable — growth stays ≥90% of baseline
    Returns a sorted DataFrame.
    """
    _configure_solver(model)
    baseline = get_baseline_growth(model)
    if baseline < 1e-9:
        baseline = 1e-9  # avoid divide-by-zero

    results = []
    exchanges = [r for r in model.exchanges if _is_analysable_exchange(r)]

    for rxn in exchanges:
        original_lb = rxn.lower_bound
        if original_lb >= 0:
            # Nutrient is not being taken up — skip
            continue
        try:
            with model:
                rxn.lower_bound = 0  # block uptake
                _configure_solver(model)
                sol = model.optimize()
                if sol.status == "optimal" and sol.objective_value > 1e-9:
                    ratio = sol.objective_value / baseline
                else:
                    ratio = 0.0
        except Exception:
            ratio = 0.0

        classification = (
            "essential" if ratio < 0.01 else
            "enhancing" if ratio < 0.90 else
            "dispensable"
        )

        results.append({
            "reaction_id": rxn.id,
            "metabolite_name": exchange_reaction_display_name(rxn),
            "uptake_rate": abs(original_lb),
            "growth_without": round(ratio * baseline, 6),
            "growth_ratio": round(ratio, 4),
            "classification": classification,
        })

    df = pd.DataFrame(results)
    if df.empty:
        return df

    order = {"essential": 0, "enhancing": 1, "dispensable": 2}
    df["_order"] = df["classification"].map(order)
    df = df.sort_values(["_order", "growth_ratio"]).drop(columns=["_order"]).reset_index(drop=True)
    return df


# --- Shadow Price (Sensitivity) Analysis ---

def nutrient_sensitivity(model: cobra.Model) -> pd.DataFrame:
    """
    Run FBA and extract shadow prices for exchange reaction metabolites.
    A large absolute shadow price → growth is highly sensitive to that nutrient.

    Returns DataFrame sorted by |shadow_price| descending.
    """
    sol = model.optimize()
    if sol.status != "optimal":
        return pd.DataFrame()

    results = []
    for rxn in model.exchanges:
        if not _is_analysable_exchange(rxn):
            continue
        for met in rxn.metabolites:
            try:
                sp = sol.shadow_prices.get(met.id, 0.0)
            except Exception:
                sp = 0.0

            results.append({
                "reaction_id": rxn.id,
                "metabolite_id": met.id,
                "metabolite_name": met.name if met.name else exchange_reaction_display_name(rxn),
                "shadow_price": round(float(sp), 6),
                "abs_shadow_price": abs(round(float(sp), 6)),
            })

    df = pd.DataFrame(results)
    if df.empty:
        return df

    df = df.sort_values("abs_shadow_price", ascending=False).reset_index(drop=True)
    return df


# --- Flux Variability Analysis ---

def compute_fva(
    model: cobra.Model,
    fraction: float = 0.95,
    exchange_only: bool = True,
) -> pd.DataFrame:
    """
    Run FVA on exchange reactions.
    Returns DataFrame with columns: reaction_id, metabolite_name, minimum, maximum.

    Uses presolve=True and processes=1 to avoid GLPK alloc.c assertion errors
    that occur when GLPK solves many LPs with degenerate bases in sequence.
    """
    _configure_solver(model)
    rxn_list = [r for r in model.exchanges if _is_analysable_exchange(r)] if exchange_only else None

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        fva = flux_variability_analysis(
            model,
            reaction_list=rxn_list,
            fraction_of_optimum=fraction,
            processes=1,           # must be 1 — multiprocessing re-creates solvers
        )                          # without presolve, triggering the GLPK crash

    fva = fva.reset_index()
    fva.columns = ["reaction_id", "minimum", "maximum"]

    name_map = {rxn.id: exchange_reaction_display_name(rxn) for rxn in model.exchanges}
    fva["metabolite_name"] = fva["reaction_id"].map(name_map).fillna(fva["reaction_id"])
    fva["minimum"] = fva["minimum"].round(4)
    fva["maximum"] = fva["maximum"].round(4)

    return fva


# --- Growth Waterfall (for visualisation) ---

def compute_growth_waterfall(model: cobra.Model) -> pd.DataFrame:
    """
    Compute cumulative growth rate as nutrients are added one-by-one
    (ordered by essentiality: essential first, then enhancing, then dispensable).
    Returns DataFrame: nutrient_name, growth_rate_with_this_nutrient.
    """
    # Run essentiality to get order
    ess_df = nutrient_essentiality(model)
    if ess_df.empty:
        return pd.DataFrame()

    records = []
    # Start with no uptake
    active_medium: dict[str, float] = {}

    for _, row in ess_df.iterrows():
        rxn_id = row["reaction_id"]
        rxn = model.reactions.get_by_id(rxn_id)
        active_medium[rxn_id] = abs(rxn.lower_bound)

        with model:
            # Apply only the active medium
            for r in model.exchanges:
                r.lower_bound = 0
            for rid, rate in active_medium.items():
                if rid in model.reactions:
                    model.reactions.get_by_id(rid).lower_bound = -rate
            sol = model.optimize()
            gr = sol.objective_value if sol.status == "optimal" else 0.0

        records.append({
            "nutrient": row["metabolite_name"],
            "reaction_id": rxn_id,
            "classification": row["classification"],
            "cumulative_growth": round(gr, 4),
        })

    return pd.DataFrame(records)
