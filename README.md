# DECODE: measurement-convention decomposition for road-based service accessibility

This repository accompanies the manuscript **“Misaligned arterial baselines produce spurious accessibility laws.”** It contains the custom code, derived result tables, Source Data workbook, numerical audit records, documentation, and final main-text figures needed to inspect and reproduce the paper's claims from the released derived data. It also contains the scripted acquisition and full-analysis entry points required for a raw-data rerun.

## Repository scope

**Included**

- 107 Python analysis/provenance/validation scripts: 86 analysis/provenance entry points, 20 reviewer-driven exploration scripts, and one repository-integrity verifier.
- 3 exploratory notebooks (historical context; not required to reproduce the main claims).
- Derived CSV/JSON outputs in the canonical `output/` and `explorations/output/` paths used by the scripts.
- `source_data/source_data_v32.xlsx`: 18 Nature-format sheets covering Figures 1a–6b and Tables 1–2.
- Final v33 main-text figures (PNG + PDF) under `figures/main/`.
- Data dictionary, data inventory, methods summary, limitations, source/licence records, experiment register, and per-country provenance.
- `MANIFEST.csv` with byte counts and SHA-256 checksums for every distributable file.

**Not redistributed**

The original raw third-party inputs are not included because of size and licence terms. They comprise Planet arterial surface lines, HOT/OSM exports, WorldPop, GHS-SMOD, GDL SHDI, hazard footprints, JRC flood layers, GRIP4, MAP 2020, Weiss & Nelson 2015, CPAS rasters, SDG 9.1.1 RAI, Meta Map With AI, and OSRM. Source URLs/licences are recorded in `docs/DATA_SOURCES.md` and `docs/DATA_AVAILABILITY_STATEMENT.md`. Download and provenance scripts are included.

## Quick start

```bash
python -m venv .venv
# or: conda env create -f environment.yml && conda activate decode
python -m pip install -r requirements.txt

# Verify the released Source Data and headline numbers (39 checks)
python verify_source_data.py

# Verify the residual/decomposition identities (60 country-service rows)
python verify_residual_identity.py
```

Both checks are read-only apart from a small verification output directory. They do not require the raw geospatial inputs.

## Reproduction levels

### Level 1 — verify released results

Run the quick-start commands above and inspect:

- `output/experiments/numerical_audit/numerical_audit.csv`
- `source_data/source_data_v32.xlsx`
- `MANIFEST.csv`

### Level 2 — rebuild derived analyses from included intermediates

Selected examples:

```bash
# Rebuild the 60-row decomposition and direction-law diagnostics
python build_direction_law_v2.py

# Rebuild robust-inference summaries and null models
python run_v28_e3_robust_inference.py
python run_v28_e2b_null_models.py

# Rebuild the external-target regression (requires interstudy comparison table)
python run_v31_e4_external_target.py

# Rebuild bootstrap effect distributions
python build_effect_distributions.py

# Regenerate the 18-sheet Source Data workbook
python make_source_data_v32.py
```

### Level 3 — full raw-data rerun

A full rerun requires the external inputs listed above and a 16 GB-RAM workstation; continental networks use `run_experiment_29_corrected_tiled.py`. The general order is:

1. `run_experiment_29_global_expansion_design.py`
2. download/audit scripts in the *Acquisition and provenance* group of `docs/CODE_INDEX.md`
3. arterial, corrected-country and tiled noding runners
4. access, urban/rural and SHDI runners
5. nested counterfactual and decomposition runners
6. robustness, stress, external-target and validation runners
7. `build_numerical_audit_table.py`, `make_source_data_v32.py`, and figure scripts

Runtime varies from seconds for derived-data checks to several hours for the full 30-country raw-data chain. Seeds and resample counts are fixed in the scripts (for example, decomposition seed 20261002 with 2,000 permutations/bootstraps; external-target seed 20261007 with 2,000 draws; robust-inference seed 20261005).

## Claim-to-code map

The complete map, including every script group and output, is in [`docs/CODE_INDEX.md`](docs/CODE_INDEX.md). The main entries are:

| Manuscript element | Primary released outputs | Key scripts |
|---|---|---|
| Fig. 1 and §2.1 convention magnitude | `output/experiments/interstudy_comparison/` | `build_interstudy_comparison.py` |
| Fig. 2, Table 1, residual identity | `output/experiments/direction_law_v2/`, `output/experiments/nested_counterfactual/` | `run_nested_counterfactual.py`, `build_direction_law_v2.py`, `verify_residual_identity.py` |
| Fig. 3 sign-reversal criterion | `output/experiments/v27/` | `run_v27_analyses.py` |
| Fig. 4 common-baseline inference | `output/experiments/v28/`, `direction_law_variants.csv` | `run_v28_e1_edge_threshold.py`, `run_v28_e2b_null_models.py`, `run_v28_e3_robust_inference.py` |
| Fig. 5 measurement choices | facility, uncertainty, quality and registry outputs | `run_facility_scenarios.py`, `run_facility_registry_bottleneck.py`, `build_uncertainty_envelope.py`, `run_capacity_access.py` |
| Fig. 6 population scale | `explorations/output/d09_access_identity_flip_summary.csv`, `d04_connectivity_all.csv` | `explorations/scripts/d09_arterial_cell_access.py`, `d04_redundancy.py` |
| §2.6 validation | OSRM, Idai, Nepal, MAP and Colombia REPS outputs | corresponding validation scripts in `docs/CODE_INDEX.md` |
| Table 2 external targets | `output/experiments/v31/`, `v33/`, `v34/` | `run_v31_e4_external_target.py`, `run_v32_e4_sensitivity.py`, `run_v33_e5_second_target.py`, `run_v34_e6_rai_external_target.py` |
| Limitations and robustness | stress, GRIP4, Map With AI, MAUP, RAI and SHDI outputs | corresponding scripts in `docs/CODE_INDEX.md` |

## Licence and citation

Analysis code is released under the MIT licence (`LICENSE`). Derived data and Source Data are released under CC BY 4.0 (`DATA_LICENSE.md`). Third-party sources retain their original licences. Please cite the manuscript, the DECODE repository, and the original external datasets when reusing these materials.
