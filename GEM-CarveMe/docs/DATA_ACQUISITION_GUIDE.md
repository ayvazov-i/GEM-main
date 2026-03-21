# GEM Media Optimiser — Data Acquisition & Integration Guide

> **Purpose:** This companion document tells you exactly what data you need, where to download it, what format it comes in, and how it plugs into each step of the pipeline defined in `GEM_MEDIA_OPTIMISER_SPEC.md`.

---

## 1. Data Overview — What You Need and Why

The tool has three pipeline entry points, each requiring different input data:

```
ENTRY POINT A (full pipeline):  Annotated Genome (.gbk)
                                     ↓
                                 CarveMe reconstructs GEM
                                     ↓
ENTRY POINT B (skip reconstruction): Pre-built SBML Model (.xml)
                                     ↓
                                 FBA / Essentiality / Sensitivity
                                     ↓
ENTRY POINT C (validation only):  Known Media + Growth Data
                                     ↓
                                 Compare predictions vs reality
```

Here is every data type the tool needs, categorised by role:

| # | Data Type | Format | Role in Tool | Required? |
|---|-----------|--------|--------------|-----------|
| 1 | Annotated genome | `.gbk` (GenBank) | Input to CarveMe for GEM reconstruction | Optional (if user uploads SBML directly) |
| 2 | Pre-built SBML model | `.xml` (SBML L3) | Direct input to FBA engine; also used as benchmark | Yes (at least for demo/testing) |
| 3 | Known media compositions | JSON / CSV | Set exchange reaction bounds to simulate real media | Yes (for meaningful defaults) |
| 4 | Experimental growth rate data | CSV | Validate model predictions against real measurements | Nice-to-have |
| 5 | Metabolite name mapping | CSV / JSON | Map human-readable nutrient names (e.g., "glucose") to model exchange reaction IDs (e.g., `EX_glc__D_e`) | Yes (built once, reused) |
| 6 | Universal reaction database | Built into CarveMe | Provides the reaction pool for GEM reconstruction | Bundled with CarveMe |

---

## 2. Data Source #1 — Annotated Genomes (.gbk)

### What They Are

GenBank flat files containing the full genome sequence plus gene annotations (CDS features with protein translations, EC numbers, gene names). This is the raw input for automated GEM reconstruction.

### Where to Get Them

**NCBI GenBank / RefSeq** — the primary source for annotated microbial genomes.

| Organism | Strain | NCBI Accession | Use Case |
|----------|--------|----------------|----------|
| *Escherichia coli* | K-12 MG1655 | [U00096](https://www.ncbi.nlm.nih.gov/nuccore/U00096) | Best-studied model organism; gold standard |
| *Bacillus subtilis* | 168 | [AL009126](https://www.ncbi.nlm.nih.gov/nuccore/AL009126) | Gram-positive benchmark |
| *Saccharomyces cerevisiae* | S288C | [GCF_000146045.2](https://www.ncbi.nlm.nih.gov/datasets/genome/GCF_000146045.2/) | Eukaryotic/yeast benchmark |
| *Pseudomonas putida* | KT2440 | [AE015451](https://www.ncbi.nlm.nih.gov/nuccore/AE015451) | Industrial biotech workhorse |
| *Corynebacterium glutamicum* | ATCC 13032 | [BA000036](https://www.ncbi.nlm.nih.gov/nuccore/BA000036) | Amino acid production |
| *Streptomyces coelicolor* | A3(2) | [AL645882](https://www.ncbi.nlm.nih.gov/nuccore/AL645882) | Secondary metabolite producer |

### How to Download

**Option A — NCBI Datasets CLI (recommended for automation)**

```bash
# Install NCBI datasets CLI
curl -o datasets https://ftp.ncbi.nlm.nih.gov/pub/datasets/command-line/v2/linux-amd64/datasets
chmod +x datasets

# Download E. coli K-12 MG1655 genome in GenBank format
./datasets download genome accession GCF_000005845.2 --include gbff
unzip ncbi_dataset.zip -d data/example_genomes/ecoli/

# Download B. subtilis 168
./datasets download genome accession GCF_000009045.1 --include gbff
unzip ncbi_dataset.zip -d data/example_genomes/bsubtilis/
```

**Option B — Direct FTP download**

```bash
# E. coli K-12 MG1655
wget -P data/example_genomes/ \
  "https://ftp.ncbi.nlm.nih.gov/genomes/all/GCF/000/005/845/GCF_000005845.2_ASM584v2/GCF_000005845.2_ASM584v2_genomic.gbff.gz"
gunzip data/example_genomes/GCF_000005845.2_ASM584v2_genomic.gbff.gz
```

**Option C — Manual (browser)**

1. Go to https://www.ncbi.nlm.nih.gov/nuccore/U00096
2. Click "Send to" → "File" → Format: "GenBank (full)" → "Create File"
3. Save to `data/example_genomes/ecoli_k12.gbk`

### How It Integrates

```python
# In core/gem_generator.py
# The .gbk file is passed directly to CarveMe
import subprocess

def generate_gem(genome_path: str, gram: str = "negative") -> str:
    output_path = genome_path.replace(".gbk", "_model.xml")
    subprocess.run([
        "carve", genome_path,
        "--output", output_path,
        "--gram", gram
    ], check=True)
    return output_path  # Returns path to generated SBML
```

```python
# In app/pages/01_upload.py (Streamlit)
uploaded = st.file_uploader("Upload annotated genome", type=["gbk", "gbff"])
gram = st.radio("Gram stain", ["negative", "positive"])

if uploaded:
    genome_path = save_uploaded_file(uploaded, "data/uploads/")
    model_path = generate_gem(genome_path, gram)
    model = cobra.io.read_sbml_model(model_path)
    st.session_state["model"] = model
```

### File Structure After Download

```
data/
└── example_genomes/
    ├── ecoli_k12_MG1655.gbk          # 4.6 Mb genome, ~4,300 genes
    ├── bsubtilis_168.gbk              # 4.2 Mb genome, ~4,200 genes
    ├── pputida_KT2440.gbk            # 6.2 Mb genome, ~5,300 genes
    ├── cglutamicum_ATCC13032.gbk     # 3.3 Mb genome, ~3,000 genes
    └── README.md                      # Source URLs and accessions
```

---

## 3. Data Source #2 — Pre-built SBML Models

### What They Are

Curated, published GEMs in SBML format. These are the most important data for the MVP because they let you skip CarveMe entirely and go straight to analysis. They also serve as ground truth to validate any auto-generated models.

### Where to Get Them

**BiGG Models** (http://bigg.ucsd.edu) — the gold standard repository of curated GEMs.

| Organism | Model ID | Reactions | Metabolites | Genes | BiGG URL |
|----------|----------|-----------|-------------|-------|----------|
| *E. coli* K-12 | iML1515 | 2,712 | 1,877 | 1,515 | http://bigg.ucsd.edu/models/iML1515 |
| *E. coli* K-12 | iJO1366 | 2,583 | 1,805 | 1,366 | http://bigg.ucsd.edu/models/iJO1366 |
| *B. subtilis* | iYO844 | 1,250 | 990 | 844 | http://bigg.ucsd.edu/models/iYO844 |
| *S. cerevisiae* | iMM904 | 1,577 | 1,226 | 904 | http://bigg.ucsd.edu/models/iMM904 |
| *P. putida* | iJN1463 | 2,927 | 2,033 | 1,463 | http://bigg.ucsd.edu/models/iJN1463 |

**BioModels** (https://www.ebi.ac.uk/biomodels/) — alternative source, especially for organisms not in BiGG.

**AGORA2** (https://www.vmh.life/) — large collection of human gut microbe GEMs.

### How to Download

```bash
mkdir -p data/example_models

# E. coli iML1515 (most comprehensive E. coli model)
wget -O data/example_models/iML1515.xml \
  "http://bigg.ucsd.edu/static/models/iML1515.xml"

# E. coli iJO1366 (widely used, slightly older)
wget -O data/example_models/iJO1366.xml \
  "http://bigg.ucsd.edu/static/models/iJO1366.xml"

# B. subtilis iYO844
wget -O data/example_models/iYO844.xml \
  "http://bigg.ucsd.edu/static/models/iYO844.xml"

# S. cerevisiae iMM904
wget -O data/example_models/iMM904.xml \
  "http://bigg.ucsd.edu/static/models/iMM904.xml"

# P. putida iJN1463
wget -O data/example_models/iJN1463.xml \
  "http://bigg.ucsd.edu/static/models/iJN1463.xml"
```

### How It Integrates

```python
# In core/fba_analysis.py — this is the primary entry point for analysis
import cobra

def load_model(model_path: str) -> cobra.Model:
    """Load an SBML model. This is where all analysis begins."""
    model = cobra.io.read_sbml_model(model_path)
    return model

# Usage
model = load_model("data/example_models/iML1515.xml")
solution = model.optimize()
print(f"Predicted growth rate: {solution.objective_value:.4f} h⁻¹")
```

```python
# In app/pages/01_upload.py — user can upload or pick a demo model
uploaded = st.file_uploader("Upload SBML model", type=["xml", "sbml"])

# OR pick a demo model
demo_models = {
    "E. coli iML1515": "data/example_models/iML1515.xml",
    "B. subtilis iYO844": "data/example_models/iYO844.xml",
    "S. cerevisiae iMM904": "data/example_models/iMM904.xml",
    "P. putida iJN1463": "data/example_models/iJN1463.xml",
}
selected = st.selectbox("Or choose a demo model:", list(demo_models.keys()))
```

### Important: What's Inside an SBML Model

When you load a BiGG model in COBRApy, it comes pre-configured with:

- **A default medium** — exchange reactions already have lower bounds set (typically simulating M9 minimal glucose medium for *E. coli*).
- **A biomass objective** — the model's objective function is already set to the biomass reaction.
- **Gene-Protein-Reaction (GPR) rules** — linking genes to reactions.

You can inspect the default medium like this:

```python
model = cobra.io.read_sbml_model("data/example_models/iML1515.xml")

# See the current medium (exchange reactions with non-zero lower bounds)
medium = model.medium
for rxn_id, bound in medium.items():
    rxn = model.reactions.get_by_id(rxn_id)
    print(f"{rxn_id:30s}  {rxn.name:40s}  bound={bound}")
```

This will output something like:

```
EX_ca2_e                       Calcium exchange                          bound=1000.0
EX_cl_e                        Chloride exchange                         bound=1000.0
EX_co2_e                       CO2 exchange                              bound=1000.0
EX_glc__D_e                    D-Glucose exchange                        bound=10.0
EX_fe2_e                       Fe2+ exchange                             bound=1000.0
EX_h2o_e                       H2O exchange                              bound=1000.0
EX_h_e                         H+ exchange                               bound=1000.0
EX_k_e                         Potassium exchange                        bound=1000.0
EX_mg2_e                       Magnesium exchange                        bound=1000.0
EX_mn2_e                       Manganese exchange                        bound=1000.0
EX_nh4_e                       Ammonium exchange                         bound=1000.0
EX_o2_e                        O2 exchange                               bound=1000.0
EX_pi_e                        Phosphate exchange                        bound=1000.0
EX_so4_e                       Sulfate exchange                          bound=1000.0
...
```

---

## 4. Data Source #3 — Known Media Compositions

### What They Are

Real-world defined media recipes mapped to model exchange reaction IDs and flux bounds. This is critical for:

1. Setting realistic starting conditions (instead of arbitrary bounds).
2. Validating that the model predicts reasonable growth on known media.
3. Giving users recognisable starting points ("start from M9 minimal").

### Standard Media Recipes

You need to create a media library — a JSON or CSV file that maps each medium to exchange reaction bounds. Here are the key media to include:

**M9 Minimal Medium (E. coli)**

| Component | Concentration | Exchange Reaction | Suggested Bound (mmol/gDW/h) |
|-----------|--------------|-------------------|------------------------------|
| Glucose | 4 g/L (22.2 mM) | `EX_glc__D_e` | 10.0 |
| NH₄Cl | 1 g/L (18.7 mM) | `EX_nh4_e` | 1000.0 |
| Na₂HPO₄ | 6 g/L | `EX_pi_e` | 1000.0 |
| KH₂PO₄ | 3 g/L | `EX_k_e` | 1000.0 |
| NaCl | 0.5 g/L | `EX_na1_e` | 1000.0 |
| MgSO₄ | 1 mM | `EX_mg2_e` | 1000.0 |
| CaCl₂ | 0.1 mM | `EX_ca2_e` | 1000.0 |
| O₂ | aerobic | `EX_o2_e` | 20.0 |
| FeSO₄ | trace | `EX_fe2_e` | 1000.0 |
| SO₄²⁻ | (from MgSO₄) | `EX_so4_e` | 1000.0 |

**LB Rich Medium (approximate, E. coli)**

LB is undefined (contains tryptone + yeast extract), but for modelling purposes you simulate it by opening all amino acid, vitamin, and nucleotide exchange reactions.

**CGXII Medium (C. glutamicum)**

| Component | Exchange Reaction | Suggested Bound |
|-----------|-------------------|-----------------|
| Glucose | `EX_glc__D_e` | 10.0 |
| (NH₄)₂SO₄ | `EX_nh4_e` | 1000.0 |
| Urea | `EX_urea_e` | 1000.0 |
| KH₂PO₄ | `EX_pi_e` | 1000.0 |
| Biotin | `EX_btn_e` | 1000.0 |
| Protocatechuic acid | `EX_34dhbz_e` | 1000.0 |
| FeSO₄ | `EX_fe2_e` | 1000.0 |
| MnSO₄ | `EX_mn2_e` | 1000.0 |
| ZnSO₄ | `EX_zn2_e` | 1000.0 |
| CuSO₄ | `EX_cu2_e` | 1000.0 |

### How to Create the Media Library

Create a structured JSON file that the tool loads as its media database:

```json
// data/media_library.json
{
  "media": {
    "M9_minimal_glucose": {
      "display_name": "M9 Minimal + Glucose",
      "organism_context": ["E. coli", "general"],
      "description": "Standard minimal medium with glucose as sole carbon source",
      "expected_growth_rate_range": [0.6, 1.0],
      "exchange_bounds": {
        "EX_glc__D_e": 10.0,
        "EX_nh4_e": 1000.0,
        "EX_pi_e": 1000.0,
        "EX_k_e": 1000.0,
        "EX_na1_e": 1000.0,
        "EX_mg2_e": 1000.0,
        "EX_ca2_e": 1000.0,
        "EX_fe2_e": 1000.0,
        "EX_so4_e": 1000.0,
        "EX_cl_e": 1000.0,
        "EX_o2_e": 20.0,
        "EX_h2o_e": 1000.0,
        "EX_h_e": 1000.0,
        "EX_co2_e": 1000.0,
        "EX_mn2_e": 1000.0,
        "EX_zn2_e": 1000.0,
        "EX_cobalt2_e": 1000.0,
        "EX_cu2_e": 1000.0,
        "EX_mobd_e": 1000.0
      }
    },
    "M9_minimal_glycerol": {
      "display_name": "M9 Minimal + Glycerol",
      "organism_context": ["E. coli"],
      "description": "M9 with glycerol instead of glucose",
      "expected_growth_rate_range": [0.4, 0.7],
      "exchange_bounds": {
        "EX_glyc_e": 10.0,
        "EX_nh4_e": 1000.0,
        "EX_pi_e": 1000.0,
        "EX_k_e": 1000.0,
        "EX_na1_e": 1000.0,
        "EX_mg2_e": 1000.0,
        "EX_ca2_e": 1000.0,
        "EX_fe2_e": 1000.0,
        "EX_so4_e": 1000.0,
        "EX_cl_e": 1000.0,
        "EX_o2_e": 20.0,
        "EX_h2o_e": 1000.0,
        "EX_h_e": 1000.0,
        "EX_co2_e": 1000.0
      }
    },
    "LB_rich_approximate": {
      "display_name": "LB Rich (Approximate)",
      "organism_context": ["E. coli", "general"],
      "description": "Approximation of LB: all amino acids, vitamins, nucleotides available",
      "expected_growth_rate_range": [0.8, 1.2],
      "exchange_bounds": {
        "EX_glc__D_e": 10.0,
        "EX_nh4_e": 1000.0,
        "EX_pi_e": 1000.0,
        "EX_o2_e": 20.0,
        "EX_h2o_e": 1000.0,
        "EX_h_e": 1000.0,
        "EX_co2_e": 1000.0,
        "EX_ala__L_e": 1000.0,
        "EX_arg__L_e": 1000.0,
        "EX_asn__L_e": 1000.0,
        "EX_asp__L_e": 1000.0,
        "EX_cys__L_e": 1000.0,
        "EX_glu__L_e": 1000.0,
        "EX_gln__L_e": 1000.0,
        "EX_gly_e": 1000.0,
        "EX_his__L_e": 1000.0,
        "EX_ile__L_e": 1000.0,
        "EX_leu__L_e": 1000.0,
        "EX_lys__L_e": 1000.0,
        "EX_met__L_e": 1000.0,
        "EX_phe__L_e": 1000.0,
        "EX_pro__L_e": 1000.0,
        "EX_ser__L_e": 1000.0,
        "EX_thr__L_e": 1000.0,
        "EX_trp__L_e": 1000.0,
        "EX_tyr__L_e": 1000.0,
        "EX_val__L_e": 1000.0,
        "EX_btn_e": 1000.0,
        "EX_fol_e": 1000.0,
        "EX_nac_e": 1000.0,
        "EX_pnto__R_e": 1000.0,
        "EX_pydam_e": 1000.0,
        "EX_ribflv_e": 1000.0,
        "EX_thm_e": 1000.0,
        "EX_k_e": 1000.0,
        "EX_na1_e": 1000.0,
        "EX_mg2_e": 1000.0,
        "EX_ca2_e": 1000.0,
        "EX_fe2_e": 1000.0,
        "EX_so4_e": 1000.0,
        "EX_cl_e": 1000.0,
        "EX_mn2_e": 1000.0,
        "EX_zn2_e": 1000.0,
        "EX_cobalt2_e": 1000.0,
        "EX_cu2_e": 1000.0
      }
    },
    "M9_anaerobic_glucose": {
      "display_name": "M9 Minimal + Glucose (Anaerobic)",
      "organism_context": ["E. coli"],
      "description": "M9 minimal without oxygen — fermentative growth",
      "expected_growth_rate_range": [0.2, 0.4],
      "exchange_bounds": {
        "EX_glc__D_e": 10.0,
        "EX_nh4_e": 1000.0,
        "EX_pi_e": 1000.0,
        "EX_k_e": 1000.0,
        "EX_na1_e": 1000.0,
        "EX_mg2_e": 1000.0,
        "EX_ca2_e": 1000.0,
        "EX_fe2_e": 1000.0,
        "EX_so4_e": 1000.0,
        "EX_cl_e": 1000.0,
        "EX_o2_e": 0.0,
        "EX_h2o_e": 1000.0,
        "EX_h_e": 1000.0,
        "EX_co2_e": 1000.0
      }
    }
  }
}
```

### How It Integrates

```python
# In core/utils.py
import json

def load_media_library(path: str = "data/media_library.json") -> dict:
    with open(path) as f:
        return json.load(f)["media"]

def apply_medium(model: cobra.Model, medium_id: str, media_library: dict):
    """Set model exchange bounds to simulate a specific medium."""
    medium_def = media_library[medium_id]

    # First, close all exchanges (block all uptake)
    for rxn in model.exchanges:
        rxn.lower_bound = 0.0

    # Then open only the ones defined in the medium
    for rxn_id, bound in medium_def["exchange_bounds"].items():
        if rxn_id in model.reactions:
            model.reactions.get_by_id(rxn_id).lower_bound = -bound
            # Note: negative = uptake in COBRA convention

    return model
```

```python
# In app/pages/03_objective.py (Streamlit)
media_lib = load_media_library()
selected_medium = st.selectbox(
    "Starting medium:",
    options=list(media_lib.keys()),
    format_func=lambda k: media_lib[k]["display_name"]
)

model = apply_medium(st.session_state["model"], selected_medium, media_lib)
st.write(f"Expected growth range: {media_lib[selected_medium]['expected_growth_rate_range']} h⁻¹")
```

---

## 5. Data Source #4 — Metabolite Name Mapping

### What It Is

Users think in terms of "glucose", "ammonium", "phosphate". The model uses IDs like `EX_glc__D_e`, `EX_nh4_e`, `EX_pi_e`. You need a mapping table so the UI can show human-readable names and the backend can translate to model IDs.

### How to Build It

The good news: BiGG models already contain metabolite names. You can extract the mapping automatically:

```python
# scripts/build_metabolite_map.py
import cobra
import json

model = cobra.io.read_sbml_model("data/example_models/iML1515.xml")

metabolite_map = {}
for rxn in model.exchanges:
    # Exchange reactions have exactly one metabolite
    for met in rxn.metabolites:
        metabolite_map[rxn.id] = {
            "model_reaction_id": rxn.id,
            "metabolite_id": met.id,
            "name": met.name,
            "formula": met.formula,
            "compartment": met.compartment,
            # Common synonyms (add manually for key nutrients)
            "common_names": []
        }

# Manually enrich common names for key nutrients
enrichments = {
    "EX_glc__D_e": ["glucose", "dextrose", "D-glucose"],
    "EX_nh4_e": ["ammonium", "ammonium chloride", "NH4+"],
    "EX_pi_e": ["phosphate", "inorganic phosphate", "Pi", "KH2PO4"],
    "EX_so4_e": ["sulfate", "sulphate", "SO4"],
    "EX_o2_e": ["oxygen", "dissolved oxygen", "O2"],
    "EX_fe2_e": ["iron", "ferrous iron", "Fe2+", "FeSO4"],
    "EX_mg2_e": ["magnesium", "Mg2+", "MgSO4"],
    "EX_ca2_e": ["calcium", "Ca2+", "CaCl2"],
    "EX_k_e": ["potassium", "K+", "KCl"],
    "EX_na1_e": ["sodium", "Na+", "NaCl"],
    "EX_mn2_e": ["manganese", "Mn2+"],
    "EX_zn2_e": ["zinc", "Zn2+"],
    "EX_cu2_e": ["copper", "Cu2+"],
    "EX_cobalt2_e": ["cobalt", "Co2+", "vitamin B12 precursor"],
    "EX_glyc_e": ["glycerol"],
    "EX_lac__D_e": ["lactate", "lactic acid"],
    "EX_ac_e": ["acetate", "acetic acid"],
    "EX_succ_e": ["succinate", "succinic acid"],
    "EX_fru_e": ["fructose"],
    "EX_xyl__D_e": ["xylose", "D-xylose"],
    "EX_arab__L_e": ["arabinose", "L-arabinose"],
}

for rxn_id, names in enrichments.items():
    if rxn_id in metabolite_map:
        metabolite_map[rxn_id]["common_names"] = names

with open("data/metabolite_map.json", "w") as f:
    json.dump(metabolite_map, f, indent=2)

print(f"Mapped {len(metabolite_map)} exchange reactions")
```

### Where It Integrates

```python
# In app/components/widgets.py
def nutrient_display_name(rxn_id: str, met_map: dict) -> str:
    """Convert model ID to a human-readable name for the UI."""
    if rxn_id in met_map:
        entry = met_map[rxn_id]
        common = entry.get("common_names", [])
        if common:
            return f"{common[0].capitalize()} ({entry['formula']})"
        return entry["name"]
    return rxn_id
```

---

## 6. Data Source #5 — Experimental Growth Data (Validation)

### What It Is

Published growth rate measurements for known organisms on known media. Used to check whether model predictions are in the right ballpark.

### Where to Get It

| Source | URL | Content |
|--------|-----|---------|
| BioNumbers | https://bionumbers.hms.harvard.edu | Curated biological constants including growth rates |
| Primary literature | PubMed | Strain-specific growth characterisations |
| DBTL datasets | Various | Published datasets from Design-Build-Test-Learn cycles |

### Key Reference Growth Rates

```json
// data/validation_growth_rates.json
{
  "validation_data": [
    {
      "organism": "E. coli K-12 MG1655",
      "model": "iML1515",
      "medium": "M9_minimal_glucose",
      "carbon_source": "glucose",
      "measured_growth_rate": 0.73,
      "unit": "h⁻¹",
      "reference": "Monk et al., 2017, Nat Biotechnol",
      "conditions": "37°C, aerobic, batch"
    },
    {
      "organism": "E. coli K-12 MG1655",
      "model": "iML1515",
      "medium": "M9_minimal_glycerol",
      "carbon_source": "glycerol",
      "measured_growth_rate": 0.55,
      "unit": "h⁻¹",
      "reference": "Monk et al., 2017, Nat Biotechnol",
      "conditions": "37°C, aerobic, batch"
    },
    {
      "organism": "E. coli K-12 MG1655",
      "model": "iML1515",
      "medium": "M9_anaerobic_glucose",
      "carbon_source": "glucose",
      "measured_growth_rate": 0.31,
      "unit": "h⁻¹",
      "reference": "Monk et al., 2017, Nat Biotechnol",
      "conditions": "37°C, anaerobic, batch"
    },
    {
      "organism": "B. subtilis 168",
      "model": "iYO844",
      "medium": "M9_minimal_glucose",
      "carbon_source": "glucose",
      "measured_growth_rate": 0.69,
      "unit": "h⁻¹",
      "reference": "Oh et al., 2007, J Biol Chem",
      "conditions": "37°C, aerobic, batch"
    }
  ]
}
```

### How It Integrates

```python
# In core/model_validator.py
def validate_against_known(model, medium_id, validation_data):
    """Compare FBA prediction to published growth rate."""
    predicted = model.optimize().objective_value

    matches = [
        v for v in validation_data["validation_data"]
        if v["medium"] == medium_id and v["model"] == model.id
    ]

    if not matches:
        return {"status": "no_reference", "predicted": predicted}

    measured = matches[0]["measured_growth_rate"]
    error_pct = abs(predicted - measured) / measured * 100

    return {
        "status": "validated",
        "predicted": round(predicted, 4),
        "measured": measured,
        "error_percent": round(error_pct, 1),
        "reference": matches[0]["reference"],
        "acceptable": error_pct < 20  # within 20% is reasonable for GEMs
    }
```

---

## 7. Data Source #6 — Concentration-to-Flux Conversion Table

### The Problem

GEMs work in flux units (mmol/gDW/h), but engineers think in concentration units (g/L, mM). The conversion is non-trivial because it depends on the specific growth rate, cell density, and uptake kinetics.

### Pragmatic MVP Approach

For the MVP, provide a simple lookup table with approximate conversion factors for common nutrients, derived from published Monod/Michaelis-Menten parameters:

```json
// data/concentration_flux_conversion.json
{
  "conversion_notes": "Approximate conversions assuming OD600=1 ≈ 0.36 gDW/L, exponential phase. These are order-of-magnitude guides, not precise.",
  "nutrients": {
    "EX_glc__D_e": {
      "name": "Glucose",
      "molecular_weight": 180.16,
      "unit_in_medium": "g/L",
      "typical_concentration_range": [1.0, 40.0],
      "approx_flux_per_gL": 1.5,
      "flux_unit": "mmol/gDW/h per g/L",
      "Km_mM": 0.015,
      "Vmax_mmol_gDW_h": 15.0,
      "notes": "Km from Kremling et al. 2015; Vmax strain-dependent"
    },
    "EX_nh4_e": {
      "name": "Ammonium",
      "molecular_weight": 18.04,
      "unit_in_medium": "g/L",
      "typical_concentration_range": [0.5, 5.0],
      "approx_flux_per_gL": 5.0,
      "flux_unit": "mmol/gDW/h per g/L",
      "notes": "Rarely limiting unless very low concentration"
    },
    "EX_pi_e": {
      "name": "Phosphate",
      "molecular_weight": 94.97,
      "unit_in_medium": "g/L",
      "typical_concentration_range": [0.5, 10.0],
      "approx_flux_per_gL": 1.0,
      "flux_unit": "mmol/gDW/h per g/L",
      "notes": "Often provided in excess"
    }
  }
}
```

### How It Integrates

```python
# In core/utils.py
def flux_to_concentration(flux_bound: float, nutrient_id: str, conversion_table: dict) -> float:
    """Approximate conversion from flux bound to medium concentration."""
    if nutrient_id in conversion_table["nutrients"]:
        factor = conversion_table["nutrients"][nutrient_id]["approx_flux_per_gL"]
        return abs(flux_bound) / factor  # g/L
    return None  # Unknown nutrient

def concentration_to_flux(conc_gL: float, nutrient_id: str, conversion_table: dict) -> float:
    """Approximate conversion from medium concentration to flux bound."""
    if nutrient_id in conversion_table["nutrients"]:
        factor = conversion_table["nutrients"][nutrient_id]["approx_flux_per_gL"]
        return conc_gL * factor  # mmol/gDW/h
    return None
```

---

## 8. Complete File Structure After Data Acquisition

```
gem-media-optimiser/
├── app/                                # Streamlit UI (see main spec)
├── core/                               # Analysis engine (see main spec)
├── scripts/
│   ├── download_data.sh                # Automates all downloads below
│   └── build_metabolite_map.py         # Generates metabolite_map.json
├── data/
│   ├── example_genomes/
│   │   ├── ecoli_k12_MG1655.gbk       # ~9 MB
│   │   ├── bsubtilis_168.gbk          # ~8 MB
│   │   ├── pputida_KT2440.gbk         # ~12 MB
│   │   └── cglutamicum_ATCC13032.gbk  # ~6 MB
│   ├── example_models/
│   │   ├── iML1515.xml                 # ~15 MB (E. coli)
│   │   ├── iYO844.xml                  # ~6 MB  (B. subtilis)
│   │   ├── iMM904.xml                  # ~8 MB  (S. cerevisiae)
│   │   └── iJN1463.xml                 # ~12 MB (P. putida)
│   ├── media_library.json              # ~5 KB  (you create this)
│   ├── metabolite_map.json             # ~50 KB (auto-generated)
│   ├── validation_growth_rates.json    # ~2 KB  (you create this)
│   ├── concentration_flux_conversion.json  # ~3 KB (you create this)
│   └── uploads/                        # User uploads land here at runtime
├── tests/
├── docs/
│   ├── GEM_MEDIA_OPTIMISER_SPEC.md
│   └── DATA_ACQUISITION_GUIDE.md       # This file
├── Dockerfile
├── requirements.txt
└── README.md
```

---

## 9. Master Download Script

```bash
#!/bin/bash
# scripts/download_data.sh
# Downloads all required data for the GEM Media Optimiser MVP

set -e
echo "=== GEM Media Optimiser — Data Download ==="

# --- Example SBML Models (from BiGG) ---
echo "[1/2] Downloading pre-built SBML models from BiGG..."
mkdir -p data/example_models

wget -q -O data/example_models/iML1515.xml \
  "http://bigg.ucsd.edu/static/models/iML1515.xml"
echo "  ✓ iML1515 (E. coli)"

wget -q -O data/example_models/iJO1366.xml \
  "http://bigg.ucsd.edu/static/models/iJO1366.xml"
echo "  ✓ iJO1366 (E. coli, older)"

wget -q -O data/example_models/iYO844.xml \
  "http://bigg.ucsd.edu/static/models/iYO844.xml"
echo "  ✓ iYO844 (B. subtilis)"

wget -q -O data/example_models/iMM904.xml \
  "http://bigg.ucsd.edu/static/models/iMM904.xml"
echo "  ✓ iMM904 (S. cerevisiae)"

wget -q -O data/example_models/iJN1463.xml \
  "http://bigg.ucsd.edu/static/models/iJN1463.xml"
echo "  ✓ iJN1463 (P. putida)"

# --- Example Genomes (from NCBI) ---
echo "[2/2] Downloading annotated genomes from NCBI..."
mkdir -p data/example_genomes

wget -q -O data/example_genomes/ecoli_k12_MG1655.gbk.gz \
  "https://ftp.ncbi.nlm.nih.gov/genomes/all/GCF/000/005/845/GCF_000005845.2_ASM584v2/GCF_000005845.2_ASM584v2_genomic.gbff.gz"
gunzip -f data/example_genomes/ecoli_k12_MG1655.gbk.gz
echo "  ✓ E. coli K-12 MG1655"

wget -q -O data/example_genomes/bsubtilis_168.gbk.gz \
  "https://ftp.ncbi.nlm.nih.gov/genomes/all/GCF/000/009/045/GCF_000009045.1_ASM904v1/GCF_000009045.1_ASM904v1_genomic.gbff.gz"
gunzip -f data/example_genomes/bsubtilis_168.gbk.gz
echo "  ✓ B. subtilis 168"

echo ""
echo "=== Download complete ==="
echo "Models: $(ls data/example_models/*.xml | wc -l) SBML files"
echo "Genomes: $(ls data/example_genomes/*.gbk 2>/dev/null | wc -l) GenBank files"
echo ""
echo "Next steps:"
echo "  1. pip install cobra biopython"
echo "  2. python scripts/build_metabolite_map.py"
echo "  3. Create data/media_library.json (see DATA_ACQUISITION_GUIDE.md)"
```

---

## 10. Quick Verification — Test That Everything Works

```python
# scripts/verify_data.py
"""Run after downloading to verify all data loads correctly."""
import cobra
import json
import os

print("=== Data Verification ===\n")

# Check SBML models
models_dir = "data/example_models"
for fname in sorted(os.listdir(models_dir)):
    if fname.endswith(".xml"):
        path = os.path.join(models_dir, fname)
        model = cobra.io.read_sbml_model(path)
        sol = model.optimize()
        status = "✓" if sol.status == "optimal" else "✗"
        print(f"{status} {fname}: {len(model.reactions)} rxns, "
              f"{len(model.genes)} genes, "
              f"growth={sol.objective_value:.4f} h⁻¹")

# Check media library
print()
media_path = "data/media_library.json"
if os.path.exists(media_path):
    with open(media_path) as f:
        media = json.load(f)["media"]
    print(f"✓ Media library: {len(media)} media definitions")
    for mid, mdef in media.items():
        print(f"  - {mdef['display_name']}: {len(mdef['exchange_bounds'])} components")
else:
    print(f"✗ Media library not found at {media_path}")

# Check metabolite map
met_path = "data/metabolite_map.json"
if os.path.exists(met_path):
    with open(met_path) as f:
        met_map = json.load(f)
    print(f"✓ Metabolite map: {len(met_map)} exchange reactions mapped")
else:
    print(f"✗ Metabolite map not found — run: python scripts/build_metabolite_map.py")

print("\n=== Verification complete ===")
```

---

## 11. Summary — Data Checklist

| # | Data | Source | How to Get | Status |
|---|------|--------|------------|--------|
| 1 | SBML models (5 organisms) | BiGG Models | `scripts/download_data.sh` | ☐ |
| 2 | Annotated genomes (2+ organisms) | NCBI GenBank | `scripts/download_data.sh` | ☐ |
| 3 | Media library JSON | You create it | Copy template from Section 4 above | ☐ |
| 4 | Metabolite name mapping | Auto-generated | `python scripts/build_metabolite_map.py` | ☐ |
| 5 | Validation growth rates | Literature | Copy template from Section 6 above | ☐ |
| 6 | Concentration-flux conversion | Literature | Copy template from Section 7 above | ☐ |
| 7 | Run verification | — | `python scripts/verify_data.py` | ☐ |
