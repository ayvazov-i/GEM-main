"""Quick check that all data is present and models load."""
import cobra
import json
import os

print("=" * 50)
print("GEM MEDIA OPTIMISER — DATA VERIFICATION")
print("=" * 50)

# Check models
print("\n--- SBML Models ---")
models_dir = "data/example_models"
if os.path.exists(models_dir):
    for fname in sorted(os.listdir(models_dir)):
        if fname.endswith(".xml"):
            path = os.path.join(models_dir, fname)
            try:
                model = cobra.io.read_sbml_model(path)
                sol = model.optimize()
                growth = sol.objective_value if sol.status == "optimal" else 0
                print(f"  OK  {fname}: {len(model.reactions)} rxns, "
                      f"{len(model.genes)} genes, growth={growth:.4f} h-1")
            except Exception as e:
                print(f"  FAIL  {fname}: {e}")
else:
    print("  MISSING — data/example_models/ not found")

# Check JSON data files
print("\n--- Data Files ---")
for fpath, label in [
    ("data/media_library.json", "Media Library"),
    ("data/metabolite_map.json", "Metabolite Map"),
    ("data/validation_growth_rates.json", "Validation Data"),
    ("data/concentration_flux_conversion.json", "Flux Conversion"),
]:
    if os.path.exists(fpath):
        with open(fpath) as f:
            data = json.load(f)
        print(f"  OK  {label}: {fpath}")
    else:
        print(f"  SKIP  {label}: {fpath} (not yet created, optional)")

# Check genomes
print("\n--- Genomes ---")
genomes_dir = "data/example_genomes"
if os.path.exists(genomes_dir):
    gbk_files = [f for f in os.listdir(genomes_dir) if f.endswith((".gbk", ".gbff"))]
    if gbk_files:
        for f in gbk_files:
            size_mb = os.path.getsize(os.path.join(genomes_dir, f)) / 1e6
            print(f"  OK  {f} ({size_mb:.1f} MB)")
    else:
        print("  SKIP  No .gbk files (optional — not needed if using SBML directly)")
else:
    print("  SKIP  No genomes directory (optional)")

print("\n" + "=" * 50)
print("Verification complete!")
print("=" * 50)