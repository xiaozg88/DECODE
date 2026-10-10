# Experiment Status

Last updated: 2026-10-02

## Main experiments

| No. | Experiment | Status |
|---:|---|---|
| 1 | Baseline accessibility | Complete |
| 2 | No-unpaved stress test | Complete |
| 3 | Single flood scenario | Complete |
| 4 | Multiple flood events | Partial |
| 5 | Health vs education | Complete |
| 6 | Road-quality ablation | Complete |
| 7 | OSM vs Planet surface | Complete |
| 8 | Hazard-rule ablation | Complete |
| 9 | Speed sensitivity | Complete |
| 10 | Spatial sensitivity | Complete |
| 11 | External accessibility products | Partial |
| 12 | Standard routing engines | Partial |
| 13 | Hazard-event validation | Partial |
| 14 | Facility validation and corrected facility model | Partial |
| 15 | Urban-rural heterogeneity | Complete |
| 16 | Socioeconomic heterogeneity | Partial |
| 17 | Accessibility inequality | Complete |
| 18 | Critical-road identification | Complete |
| 19 | Restoration priority and noded South Sofala | Complete |
| 20 | Paving upgrades and noded South Sofala | Complete |
| 21 | Budget optimization and noded South Sofala | Complete |
| 22 | Monte Carlo uncertainty | Partial |
| 23 | Unknown-surface handling | Complete |
| 24 | Network integrity and noded country networks | Partial |
| 25 | Global expansion | Blocked |
| 26 | Time dynamics | Complete |
| 27 | Future climate scenarios | Blocked |
| 28 | Learned cross-event road passability | Partial |
| 29 | Representative 30-country expansion | Partial (23 corrected baselines + audit/provenance; correction-direction law fitted on 30 countries; hazard pilot covers 14/23; urban-rural covers 30) |
| 30 | Empirical probabilistic-risk diagnostic | Partial |
| 31 | Nested counterfactual of the local-road effect | Complete (30/30 countries) |
| 32 | Decomposition of the local-road effect + permutation null | Complete (60 rows) |
| 33 | Hazard placement null model + channel decomposition | Complete (MOZ/PAK) |
| 34 | Cross-product comparability (four conventions) | Complete (30 countries) |
| 35 | Effect distributions with bootstrap CIs + rank sensitivity | Complete |
| 36 | Per-country OSM/HOT snapshot dates | Complete (30/30) |
| 37 | SHDI year sensitivity (vintage robustness) | Complete (52 rows) |

## Supporting / corrected-model records

| No. | Record | Status |
|---:|---|---|
| S1 | Original global road-surface analysis | Complete |
| S2 | Madagascar prototype | Complete |
| S3 | Corrected noded + official facility model | Complete |
| S4 | Corrected core experiments | Complete |
| S5 | True 5-km buffer hazard-rule sensitivity | Complete |
| S6 | OSRM routing validation | Complete |
| S7 | Nepal 2026 second road-status validation | Complete |
| S8 | Corrected all-country SHDI heterogeneity | Complete |
| S9 | Corrected main-model maps | Complete |
| S10 | Corrected unknown-surface sensitivity (Philippines pilot) | Complete |
| S11 | Ethiopia facility-level and strong-event sensitivity | Complete |
| S12 | Paper-ready reconciliation and positive-loss convention | Complete |
| S13 | Nepal Planet surface validation | Complete |
| S14 | Corrected time dynamics | Complete |
| S15 | Corrected OSM versus Planet surface sensitivity | Complete |
| S16 | Corrected unknown-surface sensitivity | Complete |
| S17 | Corrected multi-event accessibility | Complete |

## Current paper-ready chain
1. Planet surface/width information changes access estimates and greatly reduces unknown surface share.
2. Topology-noded local roads and official facility registries remove two major lower-bound biases.
3. The direct surface-aware rule is the main hazard model; true 5 km buffers and OR-unpaved variants are robustness rules.
4. Expanded public-OSRM validation uses 553 routes (robust n=181) and remains rank-consistent but conservative.
5. Cyclone Idai and Nepal 2026 provide two observed road-status validations with different optimal rule semantics.
6. Corrected SHDI, urban/rural, critical-road, restoration, paving and budget analyses support heterogeneity and intervention prioritisation.
7. Corrected 2020-2024 dynamics, OSM/Planet source sensitivity, unknown-surface stress tests and 18-event heterogeneity are complete.
8. Current flood footprints remain scenario inputs, not annual expected loss.
9. The 23 non-core additions of the 30-country expansion sample now have corrected noded Planet+OSM baselines (arterial-only versus corrected reported side by side; large countries produced with the tiled memory-bounded runner).

## Post-convergence audits completed
1. Corrected weighted-Gini sign error fixed; paper-ready Gini is now non-negative.
2. Hazard loss is consistently positive: baseline minus surface-aware hazard.
3. Expanded OSRM replaced the 169-route result as the canonical benchmark.
4. Corrected unknown-surface sensitivity was rerun for all seven countries after fixing nested edge-attribute contamination.
5. Ethiopia facility-level and three strong-event sensitivities completed.
6. Main maps use valid GDL geometries and non-negative absolute loss; Figures 4-5 use corrected events and expanded OSRM.

## Remaining priority gaps
1. Probabilistic event weighting and a representative multi-event archive for annual expected loss.
2. Additional independent facility registries (notably Pakistan/Kenya health and Colombia education).
3. National poverty maps and broader socioeconomic validation.
4. Broader observed road-status events beyond Idai and Nepal.
5. Future-climate scenarios and global expansion beyond seven countries.
6. Very large noding workflows are now tiled and memory-bounded (`run_experiment_29_corrected_tiled.py`); moving the remaining step to native OSM node/way graphs would still speed up reproducibility.
7. Expansion audit (2026-10-02) found two shared conventions that should be corrected or reported as sensitivity in the core model as well: WorldPop `*_pd_2020_1km.tif` is a density raster (absolute populations inflated 1.16-1.82x) and segment lengths are Web-Mercator (up to +35% travel-time inflation at high latitude). Corrected expansion variants and stress tests are in `output/experiments/experiment_29_global_expansion/weight_length_sensitivity_summary.csv`.
8. Experiments 31-37 (2026-10-02, reviewer-driven) closed the "non-nested comparison / difference-score artefact / exposure-relation endogeneity" challenges and added vintage checks: the local-edge term is positive in 60/60 rows (+0.22 to +44.23 pp) while the snapping/coverage rule supplies -7.25 pp on average; the published difference-score R2 lies at the 0.8th percentile of its own permutation null; observed hazard loss cannot be distinguished from a length-matched random placement (<=0.34 pp); and the SHDI gradient is unchanged when the year is swapped from 2020 to 2023 (r = 0.994). Remaining vintage gap: population and urban/rural layers were not re-run with a newer WorldPop release.
