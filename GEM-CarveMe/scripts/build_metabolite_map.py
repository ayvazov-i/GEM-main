"""Generate metabolite name mapping from a reference SBML model."""
import cobra
import json

model = cobra.io.read_sbml_model("data/example_models/iML1515.xml")

metabolite_map = {}
for rxn in model.exchanges:
    for met in rxn.metabolites:
        metabolite_map[rxn.id] = {
            "model_reaction_id": rxn.id,
            "metabolite_id": met.id,
            "name": met.name,
            "formula": met.formula,
            "compartment": met.compartment,
            "common_names": []
        }

# Enrich key nutrients with human-readable names
enrichments = {
    "EX_glc__D_e": ["glucose", "dextrose"],
    "EX_nh4_e": ["ammonium", "NH4+"],
    "EX_pi_e": ["phosphate", "Pi"],
    "EX_so4_e": ["sulfate", "SO4"],
    "EX_o2_e": ["oxygen", "O2"],
    "EX_fe2_e": ["iron", "Fe2+"],
    "EX_mg2_e": ["magnesium", "Mg2+"],
    "EX_ca2_e": ["calcium", "Ca2+"],
    "EX_k_e": ["potassium", "K+"],
    "EX_na1_e": ["sodium", "Na+"],
    "EX_mn2_e": ["manganese", "Mn2+"],
    "EX_zn2_e": ["zinc", "Zn2+"],
    "EX_cu2_e": ["copper", "Cu2+"],
    "EX_cobalt2_e": ["cobalt", "Co2+"],
    "EX_glyc_e": ["glycerol"],
    "EX_ac_e": ["acetate"],
    "EX_succ_e": ["succinate"],
    "EX_fru_e": ["fructose"],
    "EX_xyl__D_e": ["xylose"],
}
for rxn_id, names in enrichments.items():
    if rxn_id in metabolite_map:
        metabolite_map[rxn_id]["common_names"] = names

with open("data/metabolite_map.json", "w") as f:
    json.dump(metabolite_map, f, indent=2)

print(f"Done — mapped {len(metabolite_map)} exchange reactions to data/metabolite_map.json")