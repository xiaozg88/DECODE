# DECODE code index

This index records the code needed to support the manuscript, distinguishes derived-data verification from a raw-data rerun, and maps the main claims to outputs and scripts. File hashes are in `MANIFEST.csv`.

## 1. Analysis-entry-point groups

### A. Acquisition and provenance

| Script | Purpose | Required for |
|---|---|---|
| `run_experiment_29_global_expansion_design.py` | Define the 30-country sample and required inputs | Methods §4.1 |
| `download_experiment_29_inputs.py` | Download baseline Planet/WorldPop inputs | Full raw rerun |
| `download_experiment_29_facilities.py` | Download HOT/OSM facilities | Full raw rerun |
| `extract_experiment_29_facilities.py` | Extract/normalise facility geometries | Full raw rerun |
| `audit_experiment_29_facility_exports.py` | Audit facility records | Fig. 5c, facility quality |
| `download_experiment_29_full_osm_roads.py` | Download full local-road exports | Full raw rerun |
| `audit_experiment_29_full_osm_roads.py` | Audit local-road exports | Provenance |
| `build_expansion_data_provenance.py` | Country-level URLs, paths and feature counts | Data availability |
| `download_cpas_second_target.py` | Download CPAS 100-m rasters | CPAS rerun |
| `download_experiment_04_hazards.py` | Download core hazard footprints | Hazard rerun |
| `write_download.py`, `write_hazard_download.py` | Generate scripted source downloads | Raw rerun |

Primary outputs: `output/experiments/experiment_29_global_expansion/expansion_data_provenance.csv`, `facility_quality_by_country.csv`, `output/data_source_index.csv`.

### B. Network construction and access model

| Script | Purpose | Required for |
|---|---|---|
| `prototype_multicountry_access.py` | Shared original access-model utilities | Historical/core runners |
| `run_experiment_29_arterial_baseline.py` | Arterial-only baselines | Baseline contrasts |
| `run_experiment_29_corrected_countries.py` | Corrected noded baselines, small/medium countries | Main 30-country model |
| `run_experiment_29_corrected_tiled.py` | 1.5° adaptive tiled noding for large countries | IND/IDN/MEX-class networks |
| `validate_tiled_vs_canonical.py` | Tiled vs one-shot equivalence | Methods §4.2 |
| `run_experiment_29_weight_sensitivity.py` | Population/length/scenario variants | Measurement uncertainty |
| `run_access_cost_model.py`, `run_access_cost_grid.py` | Explicit access-cost sensitivity | Methods §4.2 and SI |
| `run_expansion_urban_rural.py` | Urban/rural aggregation | SI |
| `run_corrected_core_experiments.py` | Core experiment driver | Corrected core chain |
| `run_experiment_15_urban_rural.py` | Core urban/rural experiment | SI |
| `run_experiment_16_socioeconomic.py` | Core socioeconomic experiment | SI |

Primary outputs: corrected main table, urban/rural table, access-cost table and noding-equivalence outputs.

### C. Decomposition, inference and robustness

| Script | Purpose | Required for |
|---|---|---|
| `run_nested_counterfactual.py` | A/B_shared/B_full and speed-multiplier scenarios | Fig. 2, Table 1, Fig. 4 |
| `build_direction_law_v2.py` | Δ_edge/Δ_conv/residual decomposition and direction-law diagnostics | Fig. 2, Fig. 4, Table 1 |
| `run_shapley_decomposition.py` | Order-independent decomposition | SI |
| `verify_residual_identity.py` | Numerical identity checks | Methods and Source Data verification |
| `run_review_stats.py` | Reviewer-directed comparisons | SI |
| `run_v27_analyses.py` | Sign-reversal mechanism | Fig. 3 |
| `run_v28_e1_edge_threshold.py` | Edge increments at 30/60/120 min | Fig. 4/SI |
| `run_v28_e2b_null_models.py` | Three null-model families | Fig. 4/SI |
| `run_v28_e3_robust_inference.py` | OLS/clustered/Huber/mixed/LOCO | Fig. 4/SI |
| `run_hierarchical_mixed_model.py` | Country/service mixed model | SI |
| `build_uncertainty_envelope.py` | Population/length/facility envelope | Fig. 5 |
| `build_effect_distributions.py` | Bootstrap effect distributions and rank sensitivity | SI |
| `run_missing_road_stress.py` | Missing-road stress tests | Limitations |
| `run_nonrandom_missing_road_stress.py` | Non-random deletion | Limitations |
| `run_grip4_completeness.py` | GRIP4 cross-check | Limitations |
| `run_grip4_calibrated_stress.py` | GRIP4-anchored deletion | Limitations |
| `run_jrc_flood_exposure.py` | Unified flood exposure | SI |
| `run_hazard_null_model.py`, `run_spatial_null_model.py` | Hazard placement nulls | SI |

Primary outputs: `nested_decomposition.csv`, `direction_law_variants.csv`, `e2_refined.csv`, `e1/e2b/e3` outputs, `effect_distributions.csv`, stress summaries and null-model tables.

### D. External targets and validation

| Script | Purpose | Required for |
|---|---|---|
| `build_interstudy_comparison.py` | Four-convention comparison | Fig. 1 |
| `run_v31_e4_external_target.py` | MAP/Weiss external-target regressions | Table 2 |
| `run_v32_e4_sensitivity.py` | Outlier/bootstrap sensitivity | Table 2/SI |
| `run_v33_e5_second_target.py` | CPAS same-service target | §2.7 |
| `run_v34_e6_rai_external_target.py` | SDG 9.1.1 RAI target | §2.7 |
| `run_map_benchmark.py` | MAP 2020 benchmark | §2.6 |
| `run_routing_validation_expanded.py` | 553-route OSRM validation | §2.6 |
| `run_experiment_13_cyclone_idai_validation.py` | Observed Idai road status | §2.6 |
| `run_experiment_13_nepal_2026_validation.py` | Observed Nepal 2026 road status | §2.6 |
| `run_experiment_13_nepal_planet_surface_validation.py` | Planet surface validation | SI |
| `run_colombia_reps_validation.py` | Independent REPS registry | §2.6 |

Primary outputs: `interstudy_60min_comparison.csv`, `e4/e5/e6` outputs, OSRM summaries, Idai/Nepal metrics, Colombia REPS table.

### E. Facilities, SHDI, sample and audit

| Script | Purpose | Required for |
|---|---|---|
| `run_facility_scenarios.py` | Facility definition scenarios | Fig. 5 |
| `run_facility_registry_bottleneck.py` | Independent registry gains | Fig. 5 |
| `run_capacity_access.py` | Capacity availability | Limitations/SI |
| `run_shdi_30countries.py` | SHDI-access gradients | SI |
| `build_shdi_year_sensitivity.py` | SHDI year robustness | Limitations/SI |
| `build_osm_snapshot_dates.py` | Exact OSM snapshot dates | Methods §4.1 |
| `build_sample_framework.py` | Sample coverage | Methods §4.1 |
| `analyze_network_completeness.py` | Network completeness | Limitations/SI |
| `build_corrected_main_results.py` | Consolidated main table | Source Data |
| `build_correction_direction_matrix.py` | Direction matrix | Diagnostics |
| `build_numerical_audit_table.py` | Number-to-CSV audit | Reproducibility |
| `build_data_release_v36.py` | Curated derived-data collection | Deposit |

### F. Figures and Source Data

| Script | Purpose |
|---|---|
| `make_v29_figures.py` | Main Figures 1–4, 6 and several SI/review panels used in v33 |
| `make_fig5_v29.py` | Main Figure 5 |
| `gen_fig4_v29.py` | Inference/null supplementary panel |
| `make_si_figures.py` | Additional SI figures |
| `make_source_data_v32.py` | 18-sheet Source Data workbook |
| `verify_source_data.py` | 39 numerical checks |
| `run_analysis.py` | Original road-surface exploratory analysis; retained for provenance, not required for main claims |

## 2. Reviewer-driven exploration scripts

Scripts under `explorations/scripts/` support SI sections and limitations:

- `d01_rai.py`, `d08_sdg_rai_rural.py`, `d12_sdg_reproduction.py`: RAI/SDG recomputation.
- `d04_redundancy.py`: connectivity and redundancy.
- `d05_service_bottleneck.py`: service deserts.
- `d09_arterial_cell_access.py`: 985-million population identity-flip analysis.
- `d10_maup_mechanism.py`: MAUP mechanism.
- `d11_decomposition_orders.py`: order dependence.
- `d13_facility_road_2x2.py`: facility × network interaction.
- `d14_capacity_availability.py`: capacity fields.
- `d17_extra_country_sensitivity.py`, `d19_extra_country_edge_sign.py`: extra-country checks.
- `d20_noding_equivalence_summary.py`: tiled-noding equivalence.
- `d21_*`: Meta Map With AI download, three-way cross-check and dual-anchor stress tests.
- `d22_*`: SHAP attribution for the SI.
- `common.py`: country list and canonical local paths.

## 3. Claim map

| Manuscript claim / display item | Released data | Generating or checking scripts |
|---|---|---|
| Same-definition median 18.8 pp; cross-product median 30.7 pp, max 77.8 pp (Fig. 1) | `output/experiments/interstudy_comparison/interstudy_60min_comparison.csv` | `build_interstudy_comparison.py`; `make_source_data_v32.py`; `verify_source_data.py` |
| Δ_edge mean +9.71 pp, 0/60 negative; Δ_conv mean −7.25 pp, 60/60 negative; Δ_total 31/60 negative (Fig. 2, Table 1) | `direction_law_v2/nested_decomposition.csv` and per-country nested outputs | `run_nested_counterfactual.py`; `build_direction_law_v2.py`; `verify_residual_identity.py` |
| Baseline mismatch mean 12.1 pp, max 72.2 pp, r=−0.786 | `nested_decomposition.csv` | `build_direction_law_v2.py`; `verify_source_data.py` |
| Sign-reversal criterion and capture-loss collinearity (Fig. 3) | `v27/e2_refined.csv`, `e2_sign_reversal_mechanism.csv` | `run_v27_analyses.py` |
| R² 0.768→0.062; LOCO 0.714→−0.022 (Fig. 4) | `direction_law_variants.csv`, `v28/e3_results.json`, `e2b_null_models.json` | `build_direction_law_v2.py`; `run_v28_e3_robust_inference.py`; `run_v28_e2b_null_models.py` |
| Facility, MAUP, registry and capacity effects (Fig. 5) | facility scenarios/registry/quality, uncertainty envelope, capacity tables | corresponding group E/B scripts |
| 985 million people / 28.6% identity flips (Fig. 6) | `d09_access_identity_flip_summary.csv`, `d04_connectivity_all.csv` | `d09_arterial_cell_access.py`; `d04_redundancy.py` |
| OSRM Pearson 0.814/Spearman 0.938; Idai F1 0.758; Nepal F1 0.887 | routing, Idai and Nepal validation outputs | corresponding validation scripts |
| MAP external-target R²=0.754, LOCO=0.717; full-network R²=0.141 (Table 2) | `v31/e4_external_target.csv/.json` | `run_v31_e4_external_target.py`; `run_v32_e4_sensitivity.py` |
| CPAS cell-level second target | `v33/e5_*` | `run_v33_e5_second_target.py` |
| SDG RAI mean gap 32.4 pp and local-road correction R²=0.746 | `v34/e6_*` | `run_v34_e6_rai_external_target.py` |
| 985 million and other headline numbers across manuscript/SI | `numerical_audit.csv`, Source Data workbook | `build_numerical_audit_table.py`; `verify_source_data.py` |
| Non-synchronised years and snapshot range | `osm_snapshot_dates.csv`, provenance tables | `build_osm_snapshot_dates.py`; `build_expansion_data_provenance.py` |
| Road completeness limitations | GRIP4, Map With AI and stress summaries | `run_grip4_*`; `run_*missing*`; `explorations/scripts/d21_*` |
| Speed-convention dependence 31/60→26/60→24/60 | nested decomposition and speed columns | `run_nested_counterfactual.py`; `build_direction_law_v2.py` |

## 4. Reproducibility conventions

- Python 3.11.11; pinned packages are in `requirements.txt` and `environment.yml`.
- Random seeds: decomposition/effect distributions use 20261002; v28 inference uses 20261005; external-target sensitivity uses 20261007.
- Permutation/bootstrap counts: 2,000 unless stated otherwise; `build_effect_distributions.py` uses 5,000 country bootstraps.
- Raw inputs are not redistributed. `docs/DATA_SOURCES.md` and provenance tables give source families, URLs/licences where applicable, and local path conventions.
- Every distributable file is listed with SHA-256 in `MANIFEST.csv`.
- `source_data/source_data_v32.xlsx` contains one sheet per main-figure panel and one sheet per main-text table.

## 5. Known scope boundary

The GitHub deposit supports (i) numerical verification from derived data, (ii) regeneration of statistical diagnostics from included intermediates, and (iii) scripted full reruns when users obtain the external raw inputs. It does not claim to redistribute the raw third-party datasets, nor does it turn the hazard archive into annual expected-loss estimates.
