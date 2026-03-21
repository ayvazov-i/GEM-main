# GEM-Based Media Optimisation Tool — Project Specification

> **Purpose of this document:** This is the complete specification and context brief for building an MVP tool that allows non-GEM specialists and bioprocess engineers to optimise microbial growth media using Genome-Scale Metabolic Models (GEMs). Hand this file to Claude Code as the primary project reference.

---

## 1. Background & Motivation

### 1.1 The Opportunity

Microbial genome sequences are becoming cheap and widely available. Genome-Scale Metabolic Models (GEMs) can translate those genomes into quantitative, predictive models of cellular metabolism — but today, GEMs are almost exclusively used by computational biologists. Bioprocess engineers and bench scientists, the people who actually design fermentation media, rarely touch them.

At the same time, automated pipelines for *generating* GEMs from annotated genomes (e.g., CarveMe, ModelSEED, KBase) have matured enough that a draft model can be produced in minutes. This creates a clear integration opportunity: connect genome → GEM generation → media-aware flux analysis → actionable experimental design in a single, guided workflow that hides the computational complexity.

### 1.2 The Problem with Traditional Media Optimisation

Traditional approaches to media optimisation suffer from several well-known pain points:

- **Combinatorial explosion:** A typical defined medium has 15–40 components. Full factorial or even fractional factorial designs across realistic concentration ranges produce thousands of experimental conditions.
- **Expensive and slow:** Each condition requires actual fermentation runs (plates, shake flasks, or bioreactors), consumables, and labour. A single Design-of-Experiments (DoE) round can take weeks and cost thousands of pounds.
- **Expert intuition bottleneck:** Media design often depends on the tacit knowledge of experienced microbiologists who "just know" which carbon/nitrogen sources and trace metals matter for a given organism. This knowledge doesn't transfer easily.
- **Strain-specific:** Media recipes rarely transfer well between strains, even within the same species. Every new production strain or isolate can require a fresh optimisation cycle.
- **Limited mechanistic insight:** Statistical DoE methods (Plackett-Burman, response surface methodology) identify *what* matters but not *why*. They don't reveal which metabolic pathways are carbon-limited vs nitrogen-limited, or which cofactors are bottlenecked.

### 1.3 How GEMs Can Help

A GEM encodes the full known metabolic network of an organism: every reaction, every metabolite, every gene-protein-reaction (GPR) association. Using constraint-based methods like Flux Balance Analysis (FBA), a GEM can:

- **Predict growth rates** on arbitrary media compositions (defined by setting uptake flux bounds for each nutrient).
- **Identify essential nutrients** — nutrients whose removal zeroes the growth rate.
- **Rank nutrient sensitivity** — which nutrients, when increased or decreased, have the largest effect on growth or product flux.
- **Reveal metabolic bottlenecks** — shadow prices from the LP dual indicate which exchange reactions are growth-limiting.
- **Simulate knockout and overexpression** for strain engineering context.

By using these capabilities *before* going to the bench, you can dramatically shrink the experimental design space from "vary everything" to "vary the 5–8 components that the model says actually matter, within these specific concentration ranges."

---

## 2. Research Questions

1. **Pipeline integration:** What is the most pragmatic pipeline to obtain an easy-to-use, GEM-based media optimisation tool for non-specialists and bioprocess engineers?
2. **Experimental space reduction:** Can GEMs decrease the experimental space, focus on key media variables, and reduce the cost of bioprocess development?

---

## 3. Expected Outcome — MVP Feature Set

The MVP is a **concept pipeline + exploratory model + prototype UI + visualisation layer** that demonstrates the full workflow end-to-end. It is *not* a production-grade platform — it is a convincing proof-of-concept.

### 3.1 Core Workflow (User Journey)

```
┌─────────────────────────────────────────────────────────────┐
│  1. UPLOAD         User uploads an annotated genome          │
│                    (.gbk, .fasta + .gff, or SBML model)     │
├─────────────────────────────────────────────────────────────┤
│  2. GENERATE GEM   Auto-reconstruct a draft GEM from the    │
│                    genome using CarveMe / ModelSEED          │
│                    → User chooses: use draft or curate       │
├─────────────────────────────────────────────────────────────┤
│  3. VALIDATE       Quick sanity checks on the model:         │
│                    • Can it produce biomass on default       │
│                      minimal medium?                         │
│                    • Gene count vs reaction count summary    │
│                    • Gap-fill report (what was auto-added)   │
├─────────────────────────────────────────────────────────────┤
│  4. DEFINE GOALS   User selects objective:                   │
│                    • Maximise growth rate (default)           │
│                    • Maximise product flux (if known)         │
│                    • Multi-objective (growth + product)       │
├─────────────────────────────────────────────────────────────┤
│  5. ANALYSE        FBA + sensitivity analysis:               │
│                    • Identify essential nutrients             │
│                    • Rank nutrients by shadow price / impact  │
│                    • Compute feasible flux ranges (FVA)       │
├─────────────────────────────────────────────────────────────┤
│  6. REFINE         Narrow the design space:                  │
│                    • Suggest the top-N most impactful         │
│                      media components                        │
│                    • Recommend concentration ranges           │
│                    • Generate a reduced DoE matrix            │
├─────────────────────────────────────────────────────────────┤
│  7. EXPORT         Deliver results:                          │
│                    • Summary dashboard / report               │
│                    • Downloadable DoE table (CSV/Excel)       │
│                    • Model file (SBML) for further use        │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 Feature Breakdown

| Feature | Priority | Description |
|---------|----------|-------------|
| Genome upload & parsing | P0 | Accept `.gbk` (GenBank) files; parse annotations. For MVP, also accept pre-built SBML models directly. |
| GEM reconstruction | P0 | Wrap CarveMe (`carve` CLI) to auto-generate a draft GEM from the genome. Fallback: accept user-uploaded SBML. |
| Draft vs curate toggle | P1 | Let the user choose to proceed with the raw draft model or enter a lightweight curation step (e.g., toggle gap-fill reactions, adjust biomass equation). |
| Model validation summary | P0 | Run basic checks: does FBA produce a non-zero growth rate? How many reactions, metabolites, genes? List gap-filled reactions. |
| Objective selection | P0 | Dropdown to pick optimisation objective. Default: biomass. Allow user to type a reaction ID for product maximisation. |
| FBA & growth prediction | P0 | Run FBA with COBRApy. Display predicted growth rate and key flux distributions. |
| Nutrient essentiality screen | P0 | Systematically knock out each exchange reaction; classify nutrients as essential, enhancing, or dispensable. |
| Sensitivity / shadow price analysis | P0 | Extract shadow prices from the FBA dual. Rank nutrients by growth sensitivity. |
| Flux Variability Analysis (FVA) | P1 | Run FVA on exchange reactions to determine feasible uptake ranges. |
| Reduced design space output | P0 | Based on the analysis, output: (a) the shortlist of key variables, (b) suggested min/max ranges, (c) a compact DoE matrix. |
| Interactive dashboard | P0 | Web-based UI with: upload panel, model summary cards, sensitivity bar chart, essentiality heatmap, DoE table. |
| Export (CSV, SBML, PDF report) | P1 | Let users download the DoE matrix, the model, and a summary report. |
| Robustness analysis | P2 | Phenotype phase planes (vary two nutrients simultaneously), envelope analysis. |
| Multi-strain comparison | P2 | Upload multiple genomes, compare essentiality profiles side-by-side. |

---

## 4. Technical Architecture

### 4.1 Recommended Tech Stack

```
FRONTEND                 BACKEND                     COMPUTATION
─────────────────────    ────────────────────────    ──────────────────────
React / Next.js          Python (FastAPI or Flask)    COBRApy (FBA, FVA)
  or Streamlit (MVP)     Celery (async tasks)         CarveMe (GEM generation)
                         Redis (task queue)            GLPK or Gurobi (LP solver)
Plotly / D3.js           SQLite or PostgreSQL          
(visualisations)         (session storage)            
```

**For the fastest MVP, use Streamlit or a single-page React app with a FastAPI backend.** Streamlit is recommended for the initial prototype because it collapses the frontend/backend boundary and lets you iterate rapidly.

### 4.2 Key Python Dependencies

```
# Core
cobrapay          >= 0.29     # Constraint-based modelling (FBA, FVA, etc.)
carveme           >= 1.6      # Automated GEM reconstruction from genomes
                                # (requires Diamond BLAST, Prodigal)

# Data & Viz
pandas            >= 2.0
numpy             >= 1.24
plotly            >= 5.18     # Interactive charts
seaborn / matplotlib          # Static fallback charts

# Web
streamlit         >= 1.30     # Rapid prototyping UI
  OR
fastapi           >= 0.109    # Production-grade API
uvicorn                       # ASGI server

# Utilities
biopython         >= 1.83     # Genome file parsing (.gbk, .fasta, .gff)
pyDOE2            >= 1.3      # Design of Experiments matrix generation
openpyxl                      # Excel export
```

### 4.3 System Dependencies (for GEM reconstruction)

CarveMe requires several bioinformatics tools to be installed at the system level:

- **Prodigal** — gene prediction from genome sequences
- **Diamond** — fast protein sequence alignment (used instead of BLAST)
- **CPLEX or GLPK** — LP solver (GLPK is free; CPLEX is faster but requires a licence)

For the MVP, if CarveMe installation is too heavy, the tool can accept pre-built SBML models and skip the reconstruction step entirely.

### 4.4 Pipeline Pseudocode

```python
# === STEP 1: Genome → GEM ===
def generate_gem(genome_path: str, gram: str = "negative") -> cobra.Model:
    """Wrap CarveMe to produce a draft GEM from an annotated genome."""
    import subprocess
    output = f"/tmp/{uuid4()}.xml"
    subprocess.run([
        "carve", genome_path,
        "--output", output,
        "--gram", gram       # "positive" or "negative"
    ], check=True)
    return cobra.io.read_sbml_model(output)

# === STEP 2: Validate ===
def validate_model(model: cobra.Model) -> dict:
    """Quick sanity checks on the draft GEM."""
    sol = model.optimize()
    return {
        "growth_rate": sol.objective_value,
        "num_reactions": len(model.reactions),
        "num_metabolites": len(model.metabolites),
        "num_genes": len(model.genes),
        "feasible": sol.status == "optimal",
    }

# === STEP 3: Essentiality Screen ===
def nutrient_essentiality(model: cobra.Model) -> pd.DataFrame:
    """
    For each exchange reaction (nutrient), close it and re-run FBA.
    Classify as essential / enhancing / dispensable.
    """
    baseline = model.optimize().objective_value
    results = []
    for rxn in model.exchanges:
        with model:
            rxn.lower_bound = 0  # block uptake
            sol = model.optimize()
            ratio = sol.objective_value / baseline if sol.status == "optimal" else 0
            classification = (
                "essential"   if ratio < 0.01 else
                "enhancing"   if ratio < 0.90 else
                "dispensable"
            )
            results.append({
                "reaction": rxn.id,
                "metabolite": rxn.name,
                "growth_ratio": round(ratio, 4),
                "classification": classification
            })
    return pd.DataFrame(results).sort_values("growth_ratio")

# === STEP 4: Sensitivity (Shadow Prices) ===
def nutrient_sensitivity(model: cobra.Model) -> pd.DataFrame:
    """
    Run FBA and extract shadow prices for exchange metabolites.
    A large negative shadow price = growth is highly sensitive to that nutrient.
    """
    sol = model.optimize()
    shadow = []
    for rxn in model.exchanges:
        for met in rxn.metabolites:
            sp = sol.shadow_prices[met.id]
            shadow.append({
                "metabolite": met.id,
                "name": met.name,
                "shadow_price": round(sp, 6),
                "abs_shadow_price": abs(round(sp, 6)),
            })
    return pd.DataFrame(shadow).sort_values("abs_shadow_price", ascending=False)

# === STEP 5: FVA for Feasible Ranges ===
def compute_fva(model: cobra.Model, fraction: float = 0.95) -> pd.DataFrame:
    """
    Flux Variability Analysis on exchange reactions.
    Returns min/max uptake rates that maintain >= fraction of optimal growth.
    """
    from cobra.flux_analysis import flux_variability_analysis
    fva = flux_variability_analysis(
        model,
        reaction_list=model.exchanges,
        fraction_of_optimum=fraction
    )
    return fva

# === STEP 6: Generate Reduced DoE ===
def generate_doe(key_nutrients: list, ranges: dict, design: str = "ccf") -> pd.DataFrame:
    """
    Given the shortlisted nutrients and their ranges,
    produce a compact experimental design matrix.
    """
    from pyDOE2 import ccdesign, bbdesign
    n = len(key_nutrients)
    if design == "ccf":
        matrix = ccdesign(n, face="ccf")  # Central Composite Face-centred
    elif design == "bb":
        matrix = bbdesign(n)               # Box-Behnken
    else:
        raise ValueError(f"Unknown design: {design}")

    # Scale coded values (-1, 0, +1) to real concentration ranges
    df = pd.DataFrame(matrix, columns=key_nutrients)
    for nutrient in key_nutrients:
        lo, hi = ranges[nutrient]
        mid = (lo + hi) / 2
        half = (hi - lo) / 2
        df[nutrient] = mid + df[nutrient] * half
    return df.round(4)
```

---

## 5. UI / UX Design Guidance

### 5.1 Design Principles

1. **Wizard-style flow.** The user should be guided step-by-step through the pipeline. Each step should be completable before advancing. A sidebar or stepper bar shows progress.
2. **Sensible defaults everywhere.** A bioprocess engineer should be able to click "Next" through the whole workflow using defaults and still get useful output.
3. **No jargon without tooltips.** Terms like "shadow price," "FVA," "exchange reaction" should have hover-tooltips or info icons explaining them in plain language.
4. **Visual-first results.** Every analysis step should produce a chart or heatmap *before* a table. Tables are secondary/expandable.
5. **Export at every step.** The user should be able to download intermediate results (model file, essentiality table, DoE matrix) at any point — not just at the end.

### 5.2 Key UI Components

**Step 1 — Upload Panel**
- Drag-and-drop zone for `.gbk`, `.fasta`, `.gff`, or `.xml` (SBML) files.
- Organism name auto-detected from the file; editable text field.
- Radio button: Gram-positive / Gram-negative (needed for CarveMe).
- "Generate Model" button.

**Step 2 — Model Summary Card**
- Grid of key stats: gene count, reaction count, metabolite count.
- Traffic light indicator: green if baseline FBA is feasible, red if not.
- Growth rate displayed prominently.
- Collapsible section: list of gap-filled reactions with brief explanations.

**Step 3 — Objective Selector**
- Dropdown: "Maximise Growth Rate" (default), "Maximise Product Flux."
- If product flux is selected, a secondary input for the reaction ID / metabolite name with autocomplete from the model.

**Step 4 — Essentiality & Sensitivity Dashboard**
- **Essentiality heatmap:** Rows = nutrients, single column coloured green/amber/red (dispensable/enhancing/essential).
- **Sensitivity bar chart:** Horizontal bars showing |shadow price| for each nutrient, sorted descending. The top-N are highlighted and auto-selected as "key variables."
- Interactive: user can override the auto-selection by toggling nutrients on/off.

**Step 5 — Design Space Refinement**
- For each selected key variable, a range slider showing FVA-derived min and max, with the user able to adjust.
- Dropdown for DoE type: Central Composite, Box-Behnken, Plackett-Burman.
- Preview of the DoE matrix (scrollable table).
- "Number of experiments" counter updating in real time as variables and design type change.

**Step 6 — Export & Report**
- "Download DoE Matrix" button (CSV + Excel).
- "Download Model" button (SBML .xml).
- "Generate Report" button — produces a PDF or markdown summary of all steps.

### 5.3 Key Visualisations

| Visualisation | Library | Purpose |
|---------------|---------|---------|
| Nutrient essentiality heatmap | Plotly heatmap or Seaborn | Classify nutrients at a glance |
| Shadow price bar chart | Plotly bar | Rank nutrient impact on growth |
| Growth rate waterfall chart | Plotly waterfall | Show cumulative effect of adding nutrients |
| Phenotype phase plane (P2) | Plotly contour / surface | 2-nutrient interaction landscape |
| DoE matrix preview table | AG Grid or Streamlit dataframe | Inspect and edit the experimental plan |
| Flux map (P2) | Escher or D3 | Visualise flux distribution on the metabolic network |

---

## 6. Challenges & Risks

| Challenge | Mitigation |
|-----------|------------|
| **CarveMe installation is heavy** (Diamond, Prodigal, CPLEX). | For MVP, default to accepting pre-built SBML models. Offer CarveMe path as an optional advanced feature. Provide Docker image with all deps pre-installed. |
| **Draft GEMs are inaccurate.** Auto-generated models have gaps, incorrect GPR rules, and missing or wrong biomass equations. | Show a clear "model quality" warning. Provide a lightweight curation UI (toggle reactions, edit biomass). Long-term: integrate MEMOTE quality scores. |
| **Shadow prices can be degenerate.** The LP dual is not unique when the model is degenerate (multiple optimal solutions). | Use FVA as a complementary measure. Average shadow prices across multiple optima if needed. |
| **Concentration → flux mapping is non-trivial.** GEMs use flux units (mmol/gDW/h), not concentration units (g/L). Converting between them requires Michaelis-Menten or similar kinetics. | For MVP, work in relative terms (fold-change from baseline). Provide a lookup/conversion helper for common nutrients. Document the limitation clearly. |
| **Solver availability.** GLPK is free but slower. CPLEX/Gurobi are fast but require licences. | Default to GLPK. Detect and use CPLEX/Gurobi if available. |
| **User trust.** Non-specialists may not trust model predictions. | Show validation metrics, allow comparison with known growth data, and emphasise that the tool *prioritises* experiments rather than *replaces* them. |
| **Genome quality variation.** Poorly annotated genomes produce poor GEMs. | Provide genome annotation quality checks (e.g., number of hypothetical proteins, CDS count). Warn if annotation quality is low. |

---

## 7. Provided Resources

The following resources are available or assumed available for development:

1. **Exemplary genomes** — Annotated genomes of well-studied strains (e.g., *E. coli* K-12 MG1655, *B. subtilis* 168, *S. cerevisiae* S288C, *P. putida* KT2440) in GenBank (`.gbk`) format.
2. **Pre-built reference GEMs** — Published, curated SBML models for the above strains from BiGG Models or other repositories, to serve as validation benchmarks.
3. **Known experimental media compositions** — Published defined media recipes (e.g., M9 minimal, LB equivalent, CGXII) with known growth rates, to validate model predictions.
4. **This specification document** — The document you are reading now.

---

## 8. Glossary for Non-Specialists

| Term | Plain English |
|------|---------------|
| **GEM** (Genome-Scale Metabolic Model) | A mathematical model of all the chemical reactions an organism can perform, built from its genome. |
| **FBA** (Flux Balance Analysis) | A method that predicts how fast an organism can grow (or produce a product) given certain nutrients, by solving a linear programming problem. |
| **FVA** (Flux Variability Analysis) | An extension of FBA that finds the range of possible reaction rates (not just one optimal point). |
| **Exchange reaction** | A model boundary that represents a nutrient entering or leaving the cell. Setting its bounds controls how much of that nutrient the model can use. |
| **Shadow price** | A number from the FBA solution that tells you how much the growth rate would change if you allowed slightly more of a given nutrient. Large shadow price = high sensitivity. |
| **Gap-filling** | The process of adding reactions to a draft model so that it can produce biomass. Needed when the genome annotation is incomplete. |
| **Biomass reaction** | A special reaction in the model that represents cell growth. It consumes all the building blocks (amino acids, lipids, nucleotides, etc.) in the proportions needed to make new cells. |
| **DoE** (Design of Experiments) | A statistical method for planning experiments efficiently. Instead of testing every possible combination, DoE selects a smart subset that covers the design space. |
| **SBML** | A standard file format for encoding metabolic models. |
| **CarveMe** | An automated tool that builds a draft GEM from a genome sequence. |
| **COBRApy** | A Python library for working with GEMs — running FBA, FVA, gene knockouts, etc. |
| **Gram-positive / Gram-negative** | A classification of bacteria based on their cell wall structure. Affects the biomass composition in the model. |

---

## 9. Getting Started — Quick Commands for Claude Code

### 9.1 Environment Setup

```bash
# Create project structure
mkdir -p gem-media-optimiser/{app,core,data,tests,docs}
cd gem-media-optimiser

# Python environment
python -m venv .venv
source .venv/bin/activate

# Core dependencies
pip install cobra pandas numpy plotly streamlit biopython pyDOE2 openpyxl

# Optional: CarveMe (requires Diamond and Prodigal installed separately)
# pip install carveme
```

### 9.2 Project Structure

```
gem-media-optimiser/
├── app/
│   ├── main.py                # Streamlit app entry point
│   ├── pages/
│   │   ├── 01_upload.py       # Genome / model upload
│   │   ├── 02_model_summary.py
│   │   ├── 03_objective.py
│   │   ├── 04_analysis.py     # Essentiality + sensitivity
│   │   ├── 05_design_space.py # Refinement + DoE
│   │   └── 06_export.py
│   └── components/
│       ├── charts.py          # Plotly chart builders
│       └── widgets.py         # Reusable UI elements
├── core/
│   ├── gem_generator.py       # CarveMe wrapper
│   ├── model_validator.py     # Sanity checks
│   ├── fba_analysis.py        # FBA, essentiality, shadow prices
│   ├── fva_analysis.py        # Flux variability
│   ├── doe_generator.py       # Experimental design matrices
│   └── utils.py               # File parsing, conversions
├── data/
│   ├── example_genomes/       # .gbk files for demo
│   └── example_models/        # Pre-built SBML for demo
├── tests/
│   ├── test_fba.py
│   ├── test_essentiality.py
│   └── test_doe.py
├── docs/
│   └── GEM_MEDIA_OPTIMISER_SPEC.md  # This file
├── Dockerfile                 # Full environment with CarveMe deps
├── requirements.txt
└── README.md
```

### 9.3 Suggested Build Order

1. **Start with `core/fba_analysis.py`** — Load a known SBML model (e.g., *E. coli* iML1515 from BiGG), run FBA, extract essentiality and shadow prices. This is the analytical heart.
2. **Build `core/doe_generator.py`** — Take the essentiality/sensitivity output and generate a reduced DoE matrix.
3. **Wire up `app/main.py`** — Streamlit wizard that calls the core functions. Start with a single page, then split into multi-page.
4. **Add `core/model_validator.py`** — Sanity checks and quality metrics.
5. **Add `core/gem_generator.py`** — CarveMe wrapper (optional for MVP; can stub with direct SBML upload).
6. **Polish visualisations** — Essentiality heatmap, shadow price chart, DoE preview.
7. **Add export** — CSV, Excel, SBML download, and summary report.

---

## 10. Success Criteria

The MVP is successful if a bioprocess engineer who has never used COBRApy or any GEM tool can:

1. Upload an annotated genome or pre-built SBML model.
2. See a clear summary of the model and its predicted growth.
3. Identify the top 5–10 most impactful media components from a list of 30+.
4. Receive a reduced experimental design with concentration ranges.
5. Download that design as a spreadsheet and take it to the lab.
6. Complete the entire workflow in under 15 minutes without reading documentation.

---

## 11. Future Directions (Beyond MVP)

- **Experimental feedback loop:** Upload actual growth data from the DoE experiments; re-calibrate the model; iterate.
- **Multi-strain comparison:** Side-by-side essentiality profiles for strain selection.
- **Product-specific optimisation:** Shift objective from growth to product titre; identify trade-offs.
- **Kinetic constraints:** Integrate Michaelis-Menten kinetics for more accurate concentration-to-flux mapping.
- **Cloud deployment:** Containerised service with user accounts and persistent projects.
- **MEMOTE integration:** Automated model quality scoring to guide curation decisions.
- **Community model database:** Allow users to share curated models for common industrial strains.
