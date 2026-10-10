# Experiment Register

Last updated: 2026-10-02

This register links experiments to source IDs, processing workflows, outputs, results, and limits. Source IDs resolve in DATA_SOURCES.md and output/data_source_index.csv.

Records: 37

## Index

| No. | Experiment | Status | Output | Key result |
|---:|---|---|---|---|
| 1 | Baseline accessibility | Complete | output/prototype/multicountry/ | Arterial health 60min ranges 35.91% Ethiopia to 90.69% Philippines; corrected noded networks are higher. |
| 2 | No-unpaved stress test | Complete | output/prototype/multicountry/ | Large losses in Ethiopia, Kenya, Mozambique, and Bangladesh. |
| 3 | Single flood scenario | Complete | output/prototype/multicountry/ | Pakistan and Mozambique show largest losses. |
| 4 | Multiple flood events | Partial | output/experiments/experiment_04_multi_events/ | Pakistan health loss ranges -0.785 to -9.690 pp; Mozambique -0.017 to -15.795 pp; DFO events PHL 102, BGD 70, PAK 50. |
| 5 | Health vs education | Complete | output/prototype/multicountry/ | Health and school access/disruption differ systematically. |
| 6 | Road-quality ablation | Complete | output/experiments/experiment_06_ablation/ | Mozambique M1 health 77.88% vs M3 72.86%; Pakistan M1 46.85% vs M3 43.95%. |
| 7 | OSM vs Planet surface | Complete | output/experiments/experiment_07_osm_vs_planet/ | Pakistan known surface 30.7% OSM to 94.6% Planet; Ethiopia 34.6% to 91.9%. |
| 8 | Hazard-rule ablation | Complete | output/experiments/experiment_08_hazard_rules/ | Mozambique health loss -35.67 all-remove, -9.01 all-slow, -15.80 surface-aware pp. |
| 9 | Speed sensitivity | Complete | output/experiments/experiment_09_speed_sensitivity/ | Mozambique health baseline interval 8.67 pp; Pakistan hazard deceleration 6.43 pp. |
| 10 | Spatial sensitivity | Complete | output/experiments/experiment_10_spatial_sensitivity/ | 0.05-degree aggregation lowers 60min access 24.26 pp on average; last mile lowers 9.20 pp. |
| 11 | External accessibility products | Partial | output/experiments/experiment_11_external_products/ | Mean travel Spearman: health 0.714, school 0.679; threshold correlations weak. |
| 12 | Standard routing engines | Blocked | — | No result. |
| 13 | Hazard-event validation | Partial | output/experiments/experiment_13_hazard_validation/ | Only 1/32 blockage points within 100m of arterial roads; South Sofala noded network matches 24/24 within 25m. Flood5km OR unpaved: precision 82.28%, recall 70.26%, F1 0.758. |
| 14 | Facility validation and corrected facility model | Partial | output/experiments/experiment_14_facility_validation/ | Noded corrected access: Ethiopia health 52.45% to 93.20%; Bangladesh school 93.77% to 97.30%; Mozambique health 75.53% to 84.35%. |
| 15 | Urban-rural heterogeneity | Complete | output/experiments/experiment_15_urban_rural/ | Kenya baseline health gap 20.00 pp; Mozambique school gap 35.30 pp. |
| 16 | Socioeconomic heterogeneity | Partial | output/experiments/experiment_16_socioeconomic/ | Mozambique SHDI-health correlation shifts -0.509 arterial to +0.390 noded; school +0.254 to +0.821. |
| 17 | Accessibility inequality | Complete | output/experiments/experiment_17_inequality/ | School Gini often high; flood-added travel concentrates in lower-density cells. |
| 18 | Critical-road identification | Complete | output/experiments/experiment_18_critical_roads/ | Top 1% medical roads cause 5-7 pp losses; top 10% reaches 24-29 pp. |
| 19 | Restoration priority and noded South Sofala | Complete | output/experiments/experiment_19_restoration_priority/; output/experiments/experiment_19_21_south_sofala_noded/ | South Sofala restoring 10% by population dependency: health +9.28 pp, school +4.60 pp. |
| 20 | Paving upgrades and noded South Sofala | Complete | output/experiments/experiment_20_paving_upgrades/; output/experiments/experiment_19_21_south_sofala_noded/ | South Sofala 10% paving: hazard health +3.68 pp; baseline health +3.28 pp. |
| 21 | Budget optimization and noded South Sofala | Complete | output/experiments/experiment_21_budget_optimization/; output/experiments/experiment_19_21_south_sofala_noded/ | South Sofala 10% budget hazard health +3.10 pp exposure-first vs +0.86 pp random. |
| 22 | Monte Carlo uncertainty | Partial | output/experiments/experiment_22_monte_carlo/ | Pakistan school hazard interval 7.11 pp; Mozambique school 6.27 pp. |
| 23 | Unknown-surface handling | Complete | output/experiments/experiment_23_unknown_surface/ | Unknown-as-unpaved causes up to -3.58 pp Mozambique health hazard. |
| 24 | Network integrity and noded country networks | Partial | output/experiments/experiment_24_network_integrity/ | Baseline health gains: PAK +47.66, ETH +25.31, KEN +23.25, BGD +20.60, MOZ +19.98, COL +6.26, PHL +0.83 pp. |
| 25 | Global expansion | Blocked | — | No result. |
| 26 | Time dynamics | Partial | output/experiments/experiment_26_time_dynamics/ | Mozambique health hazard +6.05 pp; Pakistan health hazard +4.64 pp from 2020 to 2024. |
| 27 | Future climate scenarios | Blocked | — | No result. |
| 28 | Learned cross-event road passability | Partial | output/experiments/experiment_28_learned_passability/ | Passability model ranks road-status labels but is not used as a hazard rule. |
| 29 | Representative 30-country expansion | Partial | output/experiments/experiment_29_global_expansion/ | 23 corrected noded baselines completed; arterial-to-corrected change -24.65 to +73.98 pp. |
| 30 | Empirical probabilistic-risk diagnostic | Partial | output/experiments/experiment_30_probabilistic_risk/ | Mean archived-event annual loss 2.97-3.09 pp with wide bootstrap intervals. |
| 31 | Nested counterfactual of the local-road effect | Complete | output/experiments/nested_counterfactual/ | Single-node-basis A/B_shared/B_full scenarios for 30 countries; reproduces the published corrected shares (max abs gap 0.052 pp). |
| 32 | Decomposition of the local-road effect + permutation null | Complete | output/experiments/direction_law_v2/ | Local-edge term +9.71 pp (0/60 negative); snapping/coverage term -7.25 pp; the published difference-score R2 sits at the 0.8th percentile of its own artefact null. |
| 33 | Hazard placement null model + channel decomposition | Complete | output/experiments/hazard_null_model/ | Observed vs length-matched random placement differ by <=0.34 pp; removal vs slowdown channels quantified for MOZ/PAK. |
| 34 | Cross-product comparability (four conventions) | Complete | output/experiments/interstudy_comparison/ | Within-country 60-min spread median 30.7 pp (max 77.8, Egypt); 21.2 pp when restricted to 2020+ products. |
| 35 | Effect distributions with bootstrap CIs + rank sensitivity | Complete | output/experiments/effect_distributions/ | Hospital-only penalty 4.19 pp (95% CI 2.07-6.83); product-based rank shift median 3, max 12 (Nigeria). |
| 36 | Per-country OSM/HOT snapshot dates | Complete | output/experiments/osm_snapshots/ | 30/30 countries documented; road and facility snapshots 2026-05-05 to 2026-09-10. |
| 37 | SHDI year sensitivity (vintage robustness) | Complete | output/experiments/shdi_year_sensitivity/ | Reproduces the published 2020 gradient exactly; 2020 vs 2023 per country-service r = 0.994, negative rows 8 -> 8. |
| S1 | Original global road-surface analysis | Complete | output/maps; output/plots; output/tables | 2024 length-weighted pavedness: total 93.76%, urban 99.49%, rural 92.97%. |
| S2 | Madagascar prototype | Complete | output/prototype/madagascar/ | Baseline health 73.87%; no-unpaved 63.54%; flood 73.72%. |
| S3 | Corrected noded + official facility model | Complete | output/experiments/experiment_14_facility_validation/noded_facility_sensitivity/ | Ethiopia health 93.20%; Bangladesh school 97.30%; Mozambique health 84.35% baseline with union facilities. |

## Detailed records

### Experiment 1: Baseline accessibility

- Status: Complete
- Purpose: Population-weighted baseline health/school accessibility.
- Input source IDs: PLANET_ROADS_PAK;WORLDPOP_PAK;OSM_HEALTH_FACILITIES_PAK;OSM_EDUCATION_FACILITIES_PAK;HAZARD_CURRENT_PAK;PLANET_ROADS_MOZ;WORLDPOP_MOZ;OSM_HEALTH_FACILITIES_MOZ;OSM_EDUCATION_FACILITIES_MOZ;HAZARD_CURRENT_MOZ;PLANET_ROADS_BGD;WORLDPOP_BGD;OSM_HEALTH_FACILITIES_BGD;OSM_EDUCATION_FACILITIES_BGD;HAZARD_CURRENT_BGD;PLANET_ROADS_ETH;WORLDPOP_ETH;OSM_HEALTH_FACILITIES_ETH;OSM_EDUCATION_FACILITIES_ETH;HAZARD_CURRENT_ETH;PLANET_ROADS_KEN;WORLDPOP_KEN;OSM_HEALTH_FACILITIES_KEN;OSM_EDUCATION_FACILITIES_KEN;HAZARD_CURRENT_KEN;PLANET_ROADS_PHL;WORLDPOP_PHL;OSM_HEALTH_FACILITIES_PHL;OSM_EDUCATION_FACILITIES_PHL;HAZARD_CURRENT_PHL;PLANET_ROADS_COL;WORLDPOP_COL;OSM_HEALTH_FACILITIES_COL;OSM_EDUCATION_FACILITIES_COL;HAZARD_CURRENT_COL
- Processing scripts: prototype_multicountry_access.py
- Processing method: Build arterial graph; class x surface x width speeds; nearest facility/population snapping; multi-source Dijkstra; population weighting.
- Output: output/prototype/multicountry/
- Key results: Arterial health 60min ranges 35.91% Ethiopia to 90.69% Philippines; corrected noded networks are higher.
- Limitations: Arterial-only version is a lower-bound sensitivity.
- Recorded date: 2026-09-30

### Experiment 2: No-unpaved stress test

- Status: Complete
- Purpose: Measure simultaneous dependence on unpaved roads.
- Input source IDs: PLANET_ROADS_PAK;WORLDPOP_PAK;OSM_HEALTH_FACILITIES_PAK;OSM_EDUCATION_FACILITIES_PAK;HAZARD_CURRENT_PAK;PLANET_ROADS_MOZ;WORLDPOP_MOZ;OSM_HEALTH_FACILITIES_MOZ;OSM_EDUCATION_FACILITIES_MOZ;HAZARD_CURRENT_MOZ;PLANET_ROADS_BGD;WORLDPOP_BGD;OSM_HEALTH_FACILITIES_BGD;OSM_EDUCATION_FACILITIES_BGD;HAZARD_CURRENT_BGD;PLANET_ROADS_ETH;WORLDPOP_ETH;OSM_HEALTH_FACILITIES_ETH;OSM_EDUCATION_FACILITIES_ETH;HAZARD_CURRENT_ETH;PLANET_ROADS_KEN;WORLDPOP_KEN;OSM_HEALTH_FACILITIES_KEN;OSM_EDUCATION_FACILITIES_KEN;HAZARD_CURRENT_KEN;PLANET_ROADS_PHL;WORLDPOP_PHL;OSM_HEALTH_FACILITIES_PHL;OSM_EDUCATION_FACILITIES_PHL;HAZARD_CURRENT_PHL;PLANET_ROADS_COL;WORLDPOP_COL;OSM_HEALTH_FACILITIES_COL;OSM_EDUCATION_FACILITIES_COL;HAZARD_CURRENT_COL
- Processing scripts: prototype_multicountry_access.py
- Processing method: Remove all unpaved arterial edges and rerun access.
- Output: output/prototype/multicountry/
- Key results: Large losses in Ethiopia, Kenya, Mozambique, and Bangladesh.
- Limitations: Artificial stress test, not realistic simultaneous failure.
- Recorded date: 2026-09-30

### Experiment 3: Single flood scenario

- Status: Complete
- Purpose: Estimate one recent flood footprint per country.
- Input source IDs: PLANET_ROADS_PAK;WORLDPOP_PAK;OSM_HEALTH_FACILITIES_PAK;OSM_EDUCATION_FACILITIES_PAK;HAZARD_CURRENT_PAK;PLANET_ROADS_MOZ;WORLDPOP_MOZ;OSM_HEALTH_FACILITIES_MOZ;OSM_EDUCATION_FACILITIES_MOZ;HAZARD_CURRENT_MOZ;PLANET_ROADS_BGD;WORLDPOP_BGD;OSM_HEALTH_FACILITIES_BGD;OSM_EDUCATION_FACILITIES_BGD;HAZARD_CURRENT_BGD;PLANET_ROADS_ETH;WORLDPOP_ETH;OSM_HEALTH_FACILITIES_ETH;OSM_EDUCATION_FACILITIES_ETH;HAZARD_CURRENT_ETH;PLANET_ROADS_KEN;WORLDPOP_KEN;OSM_HEALTH_FACILITIES_KEN;OSM_EDUCATION_FACILITIES_KEN;HAZARD_CURRENT_KEN;PLANET_ROADS_PHL;WORLDPOP_PHL;OSM_HEALTH_FACILITIES_PHL;OSM_EDUCATION_FACILITIES_PHL;HAZARD_CURRENT_PHL;PLANET_ROADS_COL;WORLDPOP_COL;OSM_HEALTH_FACILITIES_COL;OSM_EDUCATION_FACILITIES_COL;HAZARD_CURRENT_COL
- Processing scripts: prototype_multicountry_access.py
- Processing method: Representative-point road-footprint match; remove affected unpaved and halve affected paved/unknown speed.
- Output: output/prototype/multicountry/
- Key results: Pakistan and Mozambique show largest losses.
- Limitations: Events differ by country and are not probabilistic.
- Recorded date: 2026-09-30

### Experiment 4: Multiple flood events

- Status: Partial
- Purpose: Quantify within-country heterogeneity across real flood/cyclone footprints on both arterial and corrected national graphs.
- Input source IDs: MULTI_EVENT_ARCHIVE;CORRECTED_MULTI_EVENTS
- Processing scripts: run_experiment_04_multi_events.py;run_corrected_multi_events.py
- Processing method: Apply 18 curated event footprints to topology-noded national graphs; mark representative road points; compute direct surface-aware health/education access; merge corrected baseline and positive loss.
- Output: output/experiments/experiment_04_multi_events/;output/experiments/corrected_multi_events/
- Key results: Corrected losses range from near zero to 26.61 pp. Pakistan 2025 health loss is 21.53 pp and Mozambique 2025 health loss is 26.61 pp; several small footprints are near zero.
- Limitations: Convenience sample and equal event weighting are not an annual expected-loss model.
- Recorded date: 2026-10-01

### Experiment 5: Health vs education

- Status: Complete
- Purpose: Compare service-specific sensitivity.
- Input source IDs: PLANET_ROADS_PAK;WORLDPOP_PAK;OSM_HEALTH_FACILITIES_PAK;OSM_EDUCATION_FACILITIES_PAK;HAZARD_CURRENT_PAK;PLANET_ROADS_MOZ;WORLDPOP_MOZ;OSM_HEALTH_FACILITIES_MOZ;OSM_EDUCATION_FACILITIES_MOZ;HAZARD_CURRENT_MOZ;PLANET_ROADS_BGD;WORLDPOP_BGD;OSM_HEALTH_FACILITIES_BGD;OSM_EDUCATION_FACILITIES_BGD;HAZARD_CURRENT_BGD;PLANET_ROADS_ETH;WORLDPOP_ETH;OSM_HEALTH_FACILITIES_ETH;OSM_EDUCATION_FACILITIES_ETH;HAZARD_CURRENT_ETH;PLANET_ROADS_KEN;WORLDPOP_KEN;OSM_HEALTH_FACILITIES_KEN;OSM_EDUCATION_FACILITIES_KEN;HAZARD_CURRENT_KEN;PLANET_ROADS_PHL;WORLDPOP_PHL;OSM_HEALTH_FACILITIES_PHL;OSM_EDUCATION_FACILITIES_PHL;HAZARD_CURRENT_PHL;PLANET_ROADS_COL;WORLDPOP_COL;OSM_HEALTH_FACILITIES_COL;OSM_EDUCATION_FACILITIES_COL;HAZARD_CURRENT_COL
- Processing scripts: prototype_multicountry_access.py;run_experiment_06_ablation.py
- Processing method: Run health and school models on identical inputs.
- Output: output/prototype/multicountry/
- Key results: Health and school access/disruption differ systematically.
- Limitations: Facility completeness differs by service.
- Recorded date: 2026-09-30

### Experiment 6: Road-quality ablation

- Status: Complete
- Purpose: Test value of surface and width.
- Input source IDs: PLANET_ROADS_PAK;WORLDPOP_PAK;OSM_HEALTH_FACILITIES_PAK;OSM_EDUCATION_FACILITIES_PAK;HAZARD_CURRENT_PAK;PLANET_ROADS_MOZ;WORLDPOP_MOZ;OSM_HEALTH_FACILITIES_MOZ;OSM_EDUCATION_FACILITIES_MOZ;HAZARD_CURRENT_MOZ;PLANET_ROADS_BGD;WORLDPOP_BGD;OSM_HEALTH_FACILITIES_BGD;OSM_EDUCATION_FACILITIES_BGD;HAZARD_CURRENT_BGD;PLANET_ROADS_ETH;WORLDPOP_ETH;OSM_HEALTH_FACILITIES_ETH;OSM_EDUCATION_FACILITIES_ETH;HAZARD_CURRENT_ETH;PLANET_ROADS_KEN;WORLDPOP_KEN;OSM_HEALTH_FACILITIES_KEN;OSM_EDUCATION_FACILITIES_KEN;HAZARD_CURRENT_KEN;PLANET_ROADS_PHL;WORLDPOP_PHL;OSM_HEALTH_FACILITIES_PHL;OSM_EDUCATION_FACILITIES_PHL;HAZARD_CURRENT_PHL;PLANET_ROADS_COL;WORLDPOP_COL;OSM_HEALTH_FACILITIES_COL;OSM_EDUCATION_FACILITIES_COL;HAZARD_CURRENT_COL
- Processing scripts: run_experiment_06_ablation.py
- Processing method: Compare M1 class-only, M2 class+surface, M3 class+surface+width.
- Output: output/experiments/experiment_06_ablation/
- Key results: Mozambique M1 health 77.88% vs M3 72.86%; Pakistan M1 46.85% vs M3 43.95%.
- Limitations: Needs noded-network rerun for final paper.
- Recorded date: 2026-09-30

### Experiment 7: OSM vs Planet surface

- Status: Complete
- Purpose: Compare OSM surface tags and Planet predictions on arterial and corrected topology-noded national graphs.
- Input source IDs: PLANET_ROADS_PAK;PLANET_ROADS_MOZ;PLANET_ROADS_BGD;PLANET_ROADS_ETH;PLANET_ROADS_KEN;PLANET_ROADS_PHL;PLANET_ROADS_COL;CORRECTED_OSM_PLANET_SURFACE
- Processing scripts: run_experiment_07_osm_vs_planet.py;run_corrected_osm_planet_surface.py
- Processing method: Compare known surface share and accessibility under Planet priority, OSM tags and OSM-plus-Planet fill; use 2024 surfaces, corrected graphs and registry-union facilities.
- Output: output/experiments/experiment_07_osm_vs_planet/;output/experiments/corrected_osm_planet_surface/
- Key results: Corrected Planet-known share exceeds OSM by 1.5-13.0 length-percentage points. OSM-only lowers baseline access by up to 2.51 pp (Ethiopia education), 2.32 pp (Pakistan education) and 1.16 pp (Kenya health).
- Limitations: OSM local-road surfaces are held at current extraction; source-priority inheritance can assign conflicting labels deterministically.
- Recorded date: 2026-10-01

### Experiment 8: Hazard-rule ablation

- Status: Complete
- Purpose: Assess disruption-rule sensitivity.
- Input source IDs: PLANET_ROADS_PAK;WORLDPOP_PAK;OSM_HEALTH_FACILITIES_PAK;OSM_EDUCATION_FACILITIES_PAK;HAZARD_CURRENT_PAK;PLANET_ROADS_MOZ;WORLDPOP_MOZ;OSM_HEALTH_FACILITIES_MOZ;OSM_EDUCATION_FACILITIES_MOZ;HAZARD_CURRENT_MOZ;PLANET_ROADS_BGD;WORLDPOP_BGD;OSM_HEALTH_FACILITIES_BGD;OSM_EDUCATION_FACILITIES_BGD;HAZARD_CURRENT_BGD;PLANET_ROADS_ETH;WORLDPOP_ETH;OSM_HEALTH_FACILITIES_ETH;OSM_EDUCATION_FACILITIES_ETH;HAZARD_CURRENT_ETH;PLANET_ROADS_KEN;WORLDPOP_KEN;OSM_HEALTH_FACILITIES_KEN;OSM_EDUCATION_FACILITIES_KEN;HAZARD_CURRENT_KEN;PLANET_ROADS_PHL;WORLDPOP_PHL;OSM_HEALTH_FACILITIES_PHL;OSM_EDUCATION_FACILITIES_PHL;HAZARD_CURRENT_PHL;PLANET_ROADS_COL;WORLDPOP_COL;OSM_HEALTH_FACILITIES_COL;OSM_EDUCATION_FACILITIES_COL;HAZARD_CURRENT_COL
- Processing scripts: run_experiment_08_hazard_rules.py
- Processing method: Compare all-remove, all-slow, surface-aware, and surface-only rules.
- Output: output/experiments/experiment_08_hazard_rules/
- Key results: Mozambique health loss -35.67 all-remove, -9.01 all-slow, -15.80 surface-aware pp.
- Limitations: Direct flood rule underestimates observed restrictions.
- Recorded date: 2026-09-30

### Experiment 9: Speed sensitivity

- Status: Complete
- Purpose: Quantify parameter uncertainty.
- Input source IDs: PLANET_ROADS_PAK;WORLDPOP_PAK;OSM_HEALTH_FACILITIES_PAK;OSM_EDUCATION_FACILITIES_PAK;HAZARD_CURRENT_PAK;PLANET_ROADS_MOZ;WORLDPOP_MOZ;OSM_HEALTH_FACILITIES_MOZ;OSM_EDUCATION_FACILITIES_MOZ;HAZARD_CURRENT_MOZ;PLANET_ROADS_BGD;WORLDPOP_BGD;OSM_HEALTH_FACILITIES_BGD;OSM_EDUCATION_FACILITIES_BGD;HAZARD_CURRENT_BGD;PLANET_ROADS_ETH;WORLDPOP_ETH;OSM_HEALTH_FACILITIES_ETH;OSM_EDUCATION_FACILITIES_ETH;HAZARD_CURRENT_ETH;PLANET_ROADS_KEN;WORLDPOP_KEN;OSM_HEALTH_FACILITIES_KEN;OSM_EDUCATION_FACILITIES_KEN;HAZARD_CURRENT_KEN;PLANET_ROADS_PHL;WORLDPOP_PHL;OSM_HEALTH_FACILITIES_PHL;OSM_EDUCATION_FACILITIES_PHL;HAZARD_CURRENT_PHL;PLANET_ROADS_COL;WORLDPOP_COL;OSM_HEALTH_FACILITIES_COL;OSM_EDUCATION_FACILITIES_COL;HAZARD_CURRENT_COL
- Processing scripts: run_experiment_09_speed_sensitivity.py
- Processing method: Vary class speed, surface, width, and hazard deceleration; compute empirical intervals.
- Output: output/experiments/experiment_09_speed_sensitivity/
- Key results: Mozambique health baseline interval 8.67 pp; Pakistan hazard deceleration 6.43 pp.
- Limitations: Assumption intervals, not statistical confidence intervals.
- Recorded date: 2026-09-30

### Experiment 10: Spatial sensitivity

- Status: Complete
- Purpose: Test snapping, MAUP, hazard matching, and last mile.
- Input source IDs: PLANET_ROADS_PAK;WORLDPOP_PAK;OSM_HEALTH_FACILITIES_PAK;OSM_EDUCATION_FACILITIES_PAK;HAZARD_CURRENT_PAK;PLANET_ROADS_MOZ;WORLDPOP_MOZ;OSM_HEALTH_FACILITIES_MOZ;OSM_EDUCATION_FACILITIES_MOZ;HAZARD_CURRENT_MOZ;PLANET_ROADS_BGD;WORLDPOP_BGD;OSM_HEALTH_FACILITIES_BGD;OSM_EDUCATION_FACILITIES_BGD;HAZARD_CURRENT_BGD;PLANET_ROADS_ETH;WORLDPOP_ETH;OSM_HEALTH_FACILITIES_ETH;OSM_EDUCATION_FACILITIES_ETH;HAZARD_CURRENT_ETH;PLANET_ROADS_KEN;WORLDPOP_KEN;OSM_HEALTH_FACILITIES_KEN;OSM_EDUCATION_FACILITIES_KEN;HAZARD_CURRENT_KEN;PLANET_ROADS_PHL;WORLDPOP_PHL;OSM_HEALTH_FACILITIES_PHL;OSM_EDUCATION_FACILITIES_PHL;HAZARD_CURRENT_PHL;PLANET_ROADS_COL;WORLDPOP_COL;OSM_HEALTH_FACILITIES_COL;OSM_EDUCATION_FACILITIES_COL;HAZARD_CURRENT_COL
- Processing scripts: run_experiment_10_spatial_sensitivity.py
- Processing method: Vary facility/population snapping, aggregation resolution, footprint matching, and last-mile speed.
- Output: output/experiments/experiment_10_spatial_sensitivity/
- Key results: 0.05-degree aggregation lowers 60min access 24.26 pp on average; last mile lowers 9.20 pp.
- Limitations: Noded networks reduce but do not eliminate local access uncertainty.
- Recorded date: 2026-09-30

### Experiment 11: External accessibility products

- Status: Partial
- Purpose: Compare with independent city/RAI products.
- Input source IDs: WEISS_TRAVEL;WEISS_METADATA;SDG_RAI
- Processing scripts: download_experiment_11_external_products.py;run_experiment_11_external_products.py
- Processing method: Sample Weiss raster at WorldPop cells; compare national and cell summaries with model and SDG RAI.
- Output: output/experiments/experiment_11_external_products/
- Key results: Mean travel Spearman: health 0.714, school 0.679; threshold correlations weak.
- Limitations: City access differs from health/school access; Sun/CPAS unavailable.
- Recorded date: 2026-09-30

### Experiment 12: Standard routing engines

- Status: Partial
- Purpose: Compare corrected-model road travel times with independent routing engines.
- Input source IDs: OSRM_PUBLIC;EXPANDED_OSRM_VALIDATION
- Processing scripts: run_routing_validation.py;run_routing_validation_expanded.py;build_routing_validation_summary.py;build_routing_validation_expanded_summary.py
- Processing method: Sample population cells across population strata; route from nearest main-facility node to the cell node with public OSRM; benchmark model Dijkstra duration and a snap/next-zero-filtered robust subset.
- Output: output/experiments/routing_validation/;output/experiments/routing_validation_expanded/
- Key results: Expanded validation has 553 successful routes: Pearson 0.814, Spearman 0.938, MAE 37.59 min, median model/OSRM ratio 1.304; robust subset n=181 has Pearson 0.867, Spearman 0.960, MAE 17.43 min, ratio 1.277.
- Limitations: Public OSRM is not ground truth; Google/ORS are unavailable; snapping, endpoint definition and public-network differences affect absolute duration.
- Recorded date: 2026-10-01

### Experiment 13: Hazard-event validation

- Status: Partial
- Purpose: Validate observed blockages and Cyclone Idai rules.
- Input source IDs: PRN_BLOCKAGES_2026;HOT_FLOOD_ROADS_MOZ;WFP_IDAI_CONSTRAINTS;IDAI_FLOOD_RASTER;CURRENT_OSM_IDS_MOZ;HOT_FULL_ROADS_MOZ
- Processing scripts: run_experiment_13_hazard_validation.py;run_experiment_13_cyclone_idai_validation.py;run_experiment_13_idai_rule_variants.py
- Processing method: Match observed points/lines to networks; validate road status against flood raster and surface; test flood-buffer rules.
- Output: output/experiments/experiment_13_hazard_validation/
- Key results: Only 1/32 blockage points within 100m of arterial roads; South Sofala noded network matches 24/24 within 25m. Flood5km OR unpaved: precision 82.28%, recall 70.26%, F1 0.758.
- Limitations: Single-event calibration; WFP live endpoint unavailable; archive snapshot used.
- Recorded date: 2026-09-30

### Experiment 14: Facility validation and corrected facility model

- Status: Partial
- Purpose: Audit OSM facilities and rerun with registries.
- Input source IDs: OSM_HEALTH_FACILITIES_PAK;OSM_EDUCATION_FACILITIES_PAK;OSM_HEALTH_FACILITIES_MOZ;OSM_EDUCATION_FACILITIES_MOZ;OSM_HEALTH_FACILITIES_BGD;OSM_EDUCATION_FACILITIES_BGD;OSM_HEALTH_FACILITIES_ETH;OSM_EDUCATION_FACILITIES_ETH;OSM_HEALTH_FACILITIES_KEN;OSM_EDUCATION_FACILITIES_KEN;OSM_HEALTH_FACILITIES_PHL;OSM_EDUCATION_FACILITIES_PHL;OSM_HEALTH_FACILITIES_COL;OSM_EDUCATION_FACILITIES_COL;ETH_HEALTH_REG;BGD_LGED_EDU;MOZ_MFL;PAK_DHIS;KEN_MFL;COL_REPS;COL_EDU;NODED_CACHE_ETH;NODED_CACHE_BGD;MOZ_NODED_CACHE
- Processing scripts: download_experiment_14_facilities.py;run_experiment_14_facility_validation.py;run_experiment_14_facility_sensitivity.py;run_experiment_14_noded_facility_sensitivity.py;run_experiment_14_mozambique_noded_facility_sensitivity.py
- Processing method: Nearest-match registries to OSM; rerun arterial and noded accessibility using OSM, registry, and union facilities.
- Output: output/experiments/experiment_14_facility_validation/
- Key results: Noded corrected access: Ethiopia health 52.45% to 93.20%; Bangladesh school 93.77% to 97.30%; Mozambique health 75.53% to 84.35%.
- Limitations: Registry scope/year differs; Pakistan/Kenya health and Colombia education remain count-only.
- Recorded date: 2026-09-30

### Experiment 15: Urban-rural heterogeneity

- Status: Complete
- Purpose: Compare urban/rural access.
- Input source IDs: PLANET_ROADS_PAK;WORLDPOP_PAK;OSM_HEALTH_FACILITIES_PAK;OSM_EDUCATION_FACILITIES_PAK;HAZARD_CURRENT_PAK;GHS_SMOD;PLANET_ROADS_MOZ;WORLDPOP_MOZ;OSM_HEALTH_FACILITIES_MOZ;OSM_EDUCATION_FACILITIES_MOZ;HAZARD_CURRENT_MOZ;GHS_SMOD;PLANET_ROADS_BGD;WORLDPOP_BGD;OSM_HEALTH_FACILITIES_BGD;OSM_EDUCATION_FACILITIES_BGD;HAZARD_CURRENT_BGD;GHS_SMOD;PLANET_ROADS_ETH;WORLDPOP_ETH;OSM_HEALTH_FACILITIES_ETH;OSM_EDUCATION_FACILITIES_ETH;HAZARD_CURRENT_ETH;GHS_SMOD;PLANET_ROADS_KEN;WORLDPOP_KEN;OSM_HEALTH_FACILITIES_KEN;OSM_EDUCATION_FACILITIES_KEN;HAZARD_CURRENT_KEN;GHS_SMOD;PLANET_ROADS_PHL;WORLDPOP_PHL;OSM_HEALTH_FACILITIES_PHL;OSM_EDUCATION_FACILITIES_PHL;HAZARD_CURRENT_PHL;GHS_SMOD;PLANET_ROADS_COL;WORLDPOP_COL;OSM_HEALTH_FACILITIES_COL;OSM_EDUCATION_FACILITIES_COL;HAZARD_CURRENT_COL;GHS_SMOD
- Processing scripts: run_experiment_15_urban_rural.py
- Processing method: Classify 1km WorldPop cells using GHS-SMOD and calculate access by urban/rural group.
- Output: output/experiments/experiment_15_urban_rural/
- Key results: Kenya baseline health gap 20.00 pp; Mozambique school gap 35.30 pp.
- Limitations: Needs noded rerun.
- Recorded date: 2026-09-30

### Experiment 16: Socioeconomic heterogeneity

- Status: Partial
- Purpose: Relate access to SHDI/poverty and diagnose graph artifacts.
- Input source IDs: GDL_SHDI;GDL_REGIONS;WB_METADATA;WB_POVERTY;MOZ_NODED_CACHE
- Processing scripts: download_experiment_16_socioeconomic.py;run_experiment_16_socioeconomic.py;run_experiment_16_mozambique_noded_shdi.py
- Processing method: Assign cells to GDL regions; calculate SHDI correlations; compare arterial and noded Mozambique.
- Output: output/experiments/experiment_16_socioeconomic/
- Key results: Mozambique SHDI-health correlation shifts -0.509 arterial to +0.390 noded; school +0.254 to +0.821.
- Limitations: Only Mozambique corrected; national poverty is not spatial.
- Recorded date: 2026-09-30

### Experiment 17: Accessibility inequality

- Status: Complete
- Purpose: Quantify travel-time inequality.
- Input source IDs: PLANET_ROADS_PAK;WORLDPOP_PAK;GHS_SMOD;PLANET_ROADS_MOZ;WORLDPOP_MOZ;GHS_SMOD;PLANET_ROADS_BGD;WORLDPOP_BGD;GHS_SMOD;PLANET_ROADS_ETH;WORLDPOP_ETH;GHS_SMOD;PLANET_ROADS_KEN;WORLDPOP_KEN;GHS_SMOD;PLANET_ROADS_PHL;WORLDPOP_PHL;GHS_SMOD;PLANET_ROADS_COL;WORLDPOP_COL;GHS_SMOD
- Processing scripts: run_experiment_17_inequality.py
- Processing method: Calculate Gini/concentration indices and density-quintile access.
- Output: output/experiments/experiment_17_inequality/
- Key results: School Gini often high; flood-added travel concentrates in lower-density cells.
- Limitations: Density is an imperfect socioeconomic proxy.
- Recorded date: 2026-09-30

### Experiment 18: Critical-road identification

- Status: Complete
- Purpose: Identify high-impact roads.
- Input source IDs: PLANET_ROADS_PAK;WORLDPOP_PAK;OSM_HEALTH_FACILITIES_PAK;OSM_EDUCATION_FACILITIES_PAK;HAZARD_CURRENT_PAK;PLANET_ROADS_MOZ;WORLDPOP_MOZ;OSM_HEALTH_FACILITIES_MOZ;OSM_EDUCATION_FACILITIES_MOZ;HAZARD_CURRENT_MOZ;PLANET_ROADS_BGD;WORLDPOP_BGD;OSM_HEALTH_FACILITIES_BGD;OSM_EDUCATION_FACILITIES_BGD;HAZARD_CURRENT_BGD;PLANET_ROADS_ETH;WORLDPOP_ETH;OSM_HEALTH_FACILITIES_ETH;OSM_EDUCATION_FACILITIES_ETH;HAZARD_CURRENT_ETH;PLANET_ROADS_KEN;WORLDPOP_KEN;OSM_HEALTH_FACILITIES_KEN;OSM_EDUCATION_FACILITIES_KEN;HAZARD_CURRENT_KEN;PLANET_ROADS_PHL;WORLDPOP_PHL;OSM_HEALTH_FACILITIES_PHL;OSM_EDUCATION_FACILITIES_PHL;HAZARD_CURRENT_PHL;PLANET_ROADS_COL;WORLDPOP_COL;OSM_HEALTH_FACILITIES_COL;OSM_EDUCATION_FACILITIES_COL;HAZARD_CURRENT_COL
- Processing scripts: run_experiment_18_critical_roads.py
- Processing method: Population-weight path usage; remove top 1/5/10% edges and compare random removal.
- Output: output/experiments/experiment_18_critical_roads/
- Key results: Top 1% medical roads cause 5-7 pp losses; top 10% reaches 24-29 pp.
- Limitations: Arterial-only; noded rankings may differ.
- Recorded date: 2026-09-30

### Experiment 19: Restoration priority and noded South Sofala

- Status: Complete
- Purpose: Rank post-flood restoration.
- Input source IDs: PLANET_ROADS_PAK;WORLDPOP_PAK;OSM_HEALTH_FACILITIES_PAK;OSM_EDUCATION_FACILITIES_PAK;HAZARD_CURRENT_PAK;PLANET_ROADS_MOZ;WORLDPOP_MOZ;OSM_HEALTH_FACILITIES_MOZ;OSM_EDUCATION_FACILITIES_MOZ;HAZARD_CURRENT_MOZ;PLANET_ROADS_BGD;WORLDPOP_BGD;OSM_HEALTH_FACILITIES_BGD;OSM_EDUCATION_FACILITIES_BGD;HAZARD_CURRENT_BGD;PLANET_ROADS_ETH;WORLDPOP_ETH;OSM_HEALTH_FACILITIES_ETH;OSM_EDUCATION_FACILITIES_ETH;HAZARD_CURRENT_ETH;PLANET_ROADS_KEN;WORLDPOP_KEN;OSM_HEALTH_FACILITIES_KEN;OSM_EDUCATION_FACILITIES_KEN;HAZARD_CURRENT_KEN;PLANET_ROADS_PHL;WORLDPOP_PHL;OSM_HEALTH_FACILITIES_PHL;OSM_EDUCATION_FACILITIES_PHL;HAZARD_CURRENT_PHL;PLANET_ROADS_COL;WORLDPOP_COL;OSM_HEALTH_FACILITIES_COL;OSM_EDUCATION_FACILITIES_COL;HAZARD_CURRENT_COL;MOZ_NODED_CACHE;MOZ_MFL;GDL_REGIONS
- Processing scripts: run_experiment_19_restoration_priority.py;run_south_sofala_noded_investment_experiments.py
- Processing method: Restore ranked affected edges; compare population dependency, hazard exposure, random, shortest length.
- Output: output/experiments/experiment_19_restoration_priority/; output/experiments/experiment_19_21_south_sofala_noded/
- Key results: South Sofala restoring 10% by population dependency: health +9.28 pp, school +4.60 pp.
- Limitations: Static rankings; length proxy cost.
- Recorded date: 2026-09-30

### Experiment 20: Paving upgrades and noded South Sofala

- Status: Complete
- Purpose: Simulate paving investments.
- Input source IDs: PLANET_ROADS_PAK;WORLDPOP_PAK;OSM_HEALTH_FACILITIES_PAK;OSM_EDUCATION_FACILITIES_PAK;HAZARD_CURRENT_PAK;PLANET_ROADS_MOZ;WORLDPOP_MOZ;OSM_HEALTH_FACILITIES_MOZ;OSM_EDUCATION_FACILITIES_MOZ;HAZARD_CURRENT_MOZ;PLANET_ROADS_BGD;WORLDPOP_BGD;OSM_HEALTH_FACILITIES_BGD;OSM_EDUCATION_FACILITIES_BGD;HAZARD_CURRENT_BGD;PLANET_ROADS_ETH;WORLDPOP_ETH;OSM_HEALTH_FACILITIES_ETH;OSM_EDUCATION_FACILITIES_ETH;HAZARD_CURRENT_ETH;PLANET_ROADS_KEN;WORLDPOP_KEN;OSM_HEALTH_FACILITIES_KEN;OSM_EDUCATION_FACILITIES_KEN;HAZARD_CURRENT_KEN;PLANET_ROADS_PHL;WORLDPOP_PHL;OSM_HEALTH_FACILITIES_PHL;OSM_EDUCATION_FACILITIES_PHL;HAZARD_CURRENT_PHL;PLANET_ROADS_COL;WORLDPOP_COL;OSM_HEALTH_FACILITIES_COL;OSM_EDUCATION_FACILITIES_COL;HAZARD_CURRENT_COL;MOZ_NODED_CACHE;MOZ_MFL;GDL_REGIONS
- Processing scripts: run_experiment_20_paving_upgrades.py;run_south_sofala_noded_investment_experiments.py
- Processing method: Upgrade selected unpaved edges to paved speed; flooded upgraded roads slow instead of closing.
- Output: output/experiments/experiment_20_paving_upgrades/; output/experiments/experiment_19_21_south_sofala_noded/
- Key results: South Sofala 10% paving: hazard health +3.68 pp; baseline health +3.28 pp.
- Limitations: Length-only cost; no construction feasibility.
- Recorded date: 2026-09-30

### Experiment 21: Budget optimization and noded South Sofala

- Status: Complete
- Purpose: Select roads under length budgets.
- Input source IDs: PLANET_ROADS_PAK;WORLDPOP_PAK;OSM_HEALTH_FACILITIES_PAK;OSM_EDUCATION_FACILITIES_PAK;HAZARD_CURRENT_PAK;PLANET_ROADS_MOZ;WORLDPOP_MOZ;OSM_HEALTH_FACILITIES_MOZ;OSM_EDUCATION_FACILITIES_MOZ;HAZARD_CURRENT_MOZ;PLANET_ROADS_BGD;WORLDPOP_BGD;OSM_HEALTH_FACILITIES_BGD;OSM_EDUCATION_FACILITIES_BGD;HAZARD_CURRENT_BGD;PLANET_ROADS_ETH;WORLDPOP_ETH;OSM_HEALTH_FACILITIES_ETH;OSM_EDUCATION_FACILITIES_ETH;HAZARD_CURRENT_ETH;PLANET_ROADS_KEN;WORLDPOP_KEN;OSM_HEALTH_FACILITIES_KEN;OSM_EDUCATION_FACILITIES_KEN;HAZARD_CURRENT_KEN;PLANET_ROADS_PHL;WORLDPOP_PHL;OSM_HEALTH_FACILITIES_PHL;OSM_EDUCATION_FACILITIES_PHL;HAZARD_CURRENT_PHL;PLANET_ROADS_COL;WORLDPOP_COL;OSM_HEALTH_FACILITIES_COL;OSM_EDUCATION_FACILITIES_COL;HAZARD_CURRENT_COL;MOZ_NODED_CACHE;MOZ_MFL;GDL_REGIONS
- Processing scripts: run_experiment_21_budget_optimization.py;run_south_sofala_noded_investment_experiments.py
- Processing method: Greedy selection under 1/5/10% length budgets; compare population, exposure, random, length.
- Output: output/experiments/experiment_21_budget_optimization/; output/experiments/experiment_19_21_south_sofala_noded/
- Key results: South Sofala 10% budget hazard health +3.10 pp exposure-first vs +0.86 pp random.
- Limitations: Greedy heuristic, not exact optimisation.
- Recorded date: 2026-09-30

### Experiment 22: Monte Carlo uncertainty

- Status: Partial
- Purpose: Jointly sample model parameters.
- Input source IDs: PLANET_ROADS_PAK;WORLDPOP_PAK;OSM_HEALTH_FACILITIES_PAK;OSM_EDUCATION_FACILITIES_PAK;HAZARD_CURRENT_PAK;PLANET_ROADS_MOZ;WORLDPOP_MOZ;OSM_HEALTH_FACILITIES_MOZ;OSM_EDUCATION_FACILITIES_MOZ;HAZARD_CURRENT_MOZ;PLANET_ROADS_BGD;WORLDPOP_BGD;OSM_HEALTH_FACILITIES_BGD;OSM_EDUCATION_FACILITIES_BGD;HAZARD_CURRENT_BGD;PLANET_ROADS_ETH;WORLDPOP_ETH;OSM_HEALTH_FACILITIES_ETH;OSM_EDUCATION_FACILITIES_ETH;HAZARD_CURRENT_ETH;PLANET_ROADS_KEN;WORLDPOP_KEN;OSM_HEALTH_FACILITIES_KEN;OSM_EDUCATION_FACILITIES_KEN;HAZARD_CURRENT_KEN;PLANET_ROADS_PHL;WORLDPOP_PHL;OSM_HEALTH_FACILITIES_PHL;OSM_EDUCATION_FACILITIES_PHL;HAZARD_CURRENT_PHL;PLANET_ROADS_COL;WORLDPOP_COL;OSM_HEALTH_FACILITIES_COL;OSM_EDUCATION_FACILITIES_COL;HAZARD_CURRENT_COL
- Processing scripts: run_experiment_22_monte_carlo.py
- Processing method: Sample speed, surface, unknown assignment, width, hazard deceleration; 20 draws per country.
- Output: output/experiments/experiment_22_monte_carlo/
- Key results: Pakistan school hazard interval 7.11 pp; Mozambique school 6.27 pp.
- Limitations: No population/facility/event/topology uncertainty.
- Recorded date: 2026-09-30

### Experiment 23: Unknown-surface handling

- Status: Complete
- Purpose: Test alternative assumptions for roads whose surface remains unknown, including on corrected national graphs.
- Input source IDs: CORRECTED_UNKNOWN_SURFACE
- Processing scripts: run_experiment_23_unknown_surface.py;run_corrected_unknown_surface_sensitivity.py
- Processing method: Compare current slow, as-paved, as-unpaved, no-penalty, class mean and random allocations with independent edge attributes for each rule.
- Output: output/experiments/experiment_23_unknown_surface/;output/experiments/corrected_unknown_surface/
- Key results: Across 17 corrected country-service cases, hazard access changes on average +1.81 pp as-paved, -9.55 pp as-unpaved and about -6.6 pp under random allocation; Pakistan hazard health can fall 41.55 pp if all unknowns are unpaved.
- Limitations: Extreme as-unpaved is a stress test, not an equally likely scenario; random rules condition only on road class.
- Recorded date: 2026-10-01

### Experiment 24: Network integrity and noded country networks

- Status: Partial
- Purpose: Assess network completeness and build corrected graphs.
- Input source IDs: PLANET_ROADS_PAK;WORLDPOP_PAK;OSM_HEALTH_FACILITIES_PAK;OSM_EDUCATION_FACILITIES_PAK;HOT_FULL_ROADS_PAK;NODED_CACHE_PAK;PLANET_ROADS_MOZ;WORLDPOP_MOZ;OSM_HEALTH_FACILITIES_MOZ;OSM_EDUCATION_FACILITIES_MOZ;HOT_FULL_ROADS_MOZ;MOZ_NODED_CACHE;PLANET_ROADS_BGD;WORLDPOP_BGD;OSM_HEALTH_FACILITIES_BGD;OSM_EDUCATION_FACILITIES_BGD;HOT_FULL_ROADS_BGD;NODED_CACHE_BGD;PLANET_ROADS_ETH;WORLDPOP_ETH;OSM_HEALTH_FACILITIES_ETH;OSM_EDUCATION_FACILITIES_ETH;HOT_FULL_ROADS_ETH;NODED_CACHE_ETH;PLANET_ROADS_KEN;WORLDPOP_KEN;OSM_HEALTH_FACILITIES_KEN;OSM_EDUCATION_FACILITIES_KEN;HOT_FULL_ROADS_KEN;NODED_CACHE_KEN;PLANET_ROADS_PHL;WORLDPOP_PHL;OSM_HEALTH_FACILITIES_PHL;OSM_EDUCATION_FACILITIES_PHL;HOT_FULL_ROADS_PHL;NODED_CACHE_PHL;PLANET_ROADS_COL;WORLDPOP_COL;OSM_HEALTH_FACILITIES_COL;OSM_EDUCATION_FACILITIES_COL;HOT_FULL_ROADS_COL;NODED_CACHE_COL
- Processing scripts: run_experiment_24_network_integrity.py;download_remaining_local_osm_roads_parallel.py;run_experiment_24_country_noded_network.py;run_experiment_24_mozambique_noded_network.py;run_experiment_24_south_sofala_noded_osm_pilot.py;build_all_countries_noded_summary.py
- Processing method: Download HOT roads; filter motorable classes; shapely union_all Planet+OSM lines; inherit nearest-source attributes; build baseline/hazard graphs.
- Output: output/experiments/experiment_24_network_integrity/
- Key results: Baseline health gains: PAK +47.66, ETH +25.31, KEN +23.25, BGD +20.60, MOZ +19.98, COL +6.26, PHL +0.83 pp.
- Limitations: Derived caches are large; native OSM node/way graphs preferable.
- Recorded date: 2026-09-30

### Experiment 25: Global expansion

- Status: Blocked
- Purpose: Extend beyond seven countries.
- Input source IDs: 
- Processing scripts: 
- Processing method: Not executed.
- Output: 
- Key results: No result.
- Limitations: Requires comparable multi-country inputs and compute.
- Recorded date: 2026-09-30

### Experiment 26: Time dynamics

- Status: Complete
- Purpose: Compare 2020 and 2024 Planet surface labels on corrected topology-noded national graphs.
- Input source IDs: CORRECTED_TIME_DYNAMICS
- Processing scripts: run_experiment_26_time_dynamics.py;run_corrected_time_dynamics.py
- Processing method: Update Planet-assigned noded segments from DL_road_class_2020 to DL_road_class_2024; hold OSM local surfaces, width, facilities, population and hazard footprint constant; compute baseline and surface-aware access.
- Output: output/experiments/experiment_26_time_dynamics/;output/experiments/corrected_time_dynamics/
- Key results: Pakistan health hazard access improves +4.68 pp and education +4.04 pp; Mozambique health hazard +3.07 pp; Kenya health hazard +1.29 pp. Baseline changes are smaller.
- Limitations: No 2016 class on corrected cache; OSM local-road surface dynamics are unavailable.
- Recorded date: 2026-10-01

### Experiment 27: Future climate scenarios

- Status: Blocked
- Purpose: Project future hazards.
- Input source IDs: 
- Processing scripts: 
- Processing method: Not executed.
- Output: 
- Key results: No result.
- Limitations: Requires probabilistic future flood/cyclone projections.
- Recorded date: 2026-09-30

### Experiment S1: Original global road-surface analysis

- Status: Complete
- Purpose: Reproduce original global pavedness analysis.
- Input source IDs: CORE_GRID;NE110M;PAPER_PDF
- Processing scripts: run_analysis.py
- Processing method: Read aggregate grid; calculate pavedness and unknown share; merge boundaries; make maps/tables.
- Output: output/maps; output/plots; output/tables
- Key results: 2024 length-weighted pavedness: total 93.76%, urban 99.49%, rural 92.97%.
- Limitations: Uses aggregate grid, not raw per-road data.
- Recorded date: 2026-09-30

### Experiment S2: Madagascar prototype

- Status: Complete
- Purpose: Test service-access idea.
- Input source IDs: MADAGASCAR_INPUTS
- Processing scripts: prototype_madagascar_access.py
- Processing method: Build road graph and baseline/no-unpaved/flood scenarios.
- Output: output/prototype/madagascar/
- Key results: Baseline health 73.87%; no-unpaved 63.54%; flood 73.72%.
- Limitations: Proof of concept with small flood impact.
- Recorded date: 2026-09-30

### Experiment S3: Corrected noded + official facility model

- Status: Complete
- Purpose: Combine corrected topology and registry facilities.
- Input source IDs: NODED_CACHE_ETH;NODED_CACHE_BGD;MOZ_NODED_CACHE;WORLDPOP_ETH;WORLDPOP_BGD;WORLDPOP_MOZ;ETH_HEALTH_REG;BGD_LGED_EDU;MOZ_MFL
- Processing scripts: run_experiment_14_noded_facility_sensitivity.py;run_experiment_14_mozambique_noded_facility_sensitivity.py
- Processing method: Use national noded graphs and alternate OSM/registry/union facility sources.
- Output: output/experiments/experiment_14_facility_validation/noded_facility_sensitivity/
- Key results: Ethiopia health 93.20%; Bangladesh school 97.30%; Mozambique health 84.35% baseline with union facilities.
- Limitations: Completed only for ETH, BGD, MOZ.
- Recorded date: 2026-09-30

## Cross-experiment interpretation rules

1. Arterial-only outputs are lower-bound sensitivities; corrected main results should use topology-noded Planet+OSM networks where available.
2. OSM facility-only results are lower-bound sensitivities where registries show major missing facilities.
3. Flood scenarios are not annual expected losses.
4. Direct flood-footprint intersection underestimates observed access constraints.
5. Registry and OSM facility scopes differ by year, level, and inclusion rules.
6. WorldPop 2020 population is held constant across scenario dates.
7. Derived noded caches are not independent source data.
8. External accessibility products use different destinations and are not service-access ground truth.

### Experiment S4: Corrected core experiments

- Status: Complete
- Purpose: Rerun core experiments 6, 8, 15, and 17 on the final topology-noded, registry-corrected model.
- Input source IDs: NODED_CACHE_PAK;MOZ_NODED_CACHE;NODED_CACHE_BGD;NODED_CACHE_ETH;NODED_CACHE_KEN;NODED_CACHE_PHL;NODED_CACHE_COL;ETH_HEALTH_REG;BGD_LGED_EDU;MOZ_MFL;GHS_SMOD;WORLDPOP_PAK;WORLDPOP_MOZ;WORLDPOP_BGD;WORLDPOP_ETH;WORLDPOP_KEN;WORLDPOP_PHL;WORLDPOP_COL
- Processing scripts: run_corrected_core_experiments.py;build_corrected_core_summary.py
- Processing method: Build M1/M2/M3 graphs on noded caches; use registry-union facilities where available; run direct hazard-rule ablation; classify urban/rural with GHS-SMOD; compute corrected Gini and density-quintile summaries.
- Output: output/experiments/corrected_core/
- Key results: Ignoring surface/width still overstates access; Ethiopia health M1 61.85% versus M3 50.08% under OSM facilities, while registry union gives M1 95.56% versus M3 92.41%.
- Limitations: Registry unions exist only for ETH health, BGD education, and MOZ health; other services remain OSM-only.
- Recorded date: 2026-10-01

### Experiment S5: True 5-km buffer hazard-rule sensitivity

- Status: Complete
- Purpose: Test direct versus true spatial-buffer disruption rules on the corrected model.
- Input source IDs: CORRECTED_HAZARD_V2;HAZARD_CURRENT_PAK;HAZARD_CURRENT_MOZ;HAZARD_CURRENT_BGD;HAZARD_CURRENT_ETH;HAZARD_CURRENT_KEN;HAZARD_CURRENT_PHL;HAZARD_CURRENT_COL
- Processing scripts: run_corrected_hazard_rule_variants.py;build_corrected_hazard_v2_summary.py
- Processing method: Rasterize each flood footprint at 250 m in EPSG:3857; apply Euclidean distance transform; mark road representative points within 5 km; compare direct, buffer-remove, buffer-OR-unpaved, and buffer-surface-aware rules.
- Output: output/experiments/corrected_hazard_rules_v2/
- Key results: Buffer5 surface-aware differs modestly from direct surface-aware (for example, Mozambique registry health 55.10% direct versus 54.60% buffer), while buffer5-remove-all and buffer5-OR-unpaved are much more conservative.
- Limitations: Buffer proximity is not evidence of road inundation; 250 m raster approximation; rules are robustness checks rather than the main model.
- Recorded date: 2026-10-01

### Experiment S6: OSRM routing validation

- Status: Complete
- Purpose: Benchmark corrected-model road travel times against independent public OSRM driving durations, including the expanded 553-route sample.
- Input source IDs: OSRM_PUBLIC;EXPANDED_OSRM_VALIDATION
- Processing scripts: run_routing_validation.py;run_routing_validation_expanded.py;build_routing_validation_summary.py;build_routing_validation_expanded_summary.py
- Processing method: Stratify population-cell samples; route nearest main-facility node to cell node; compare OSRM duration with corrected Dijkstra time; report all-route and snap-filtered robust metrics.
- Output: output/experiments/routing_validation/;output/experiments/routing_validation_expanded/
- Key results: Expanded all-route Pearson 0.814, Spearman 0.938, MAE 37.59 min, median ratio 1.304. Robust subset Pearson 0.867, Spearman 0.960, MAE 17.43 min, median ratio 1.277.
- Limitations: Public OSRM is a benchmark, not ground truth; route sample remains modest and destination snapping is often large.
- Recorded date: 2026-10-01

### Experiment S7: Nepal 2026 second road-status validation

- Status: Complete
- Purpose: Provide a second independent event test of hazard/rule spatial overlap using Copernicus road damage status.
- Input source IDs: NEPAL_PRN_BLOCKAGES_2026;NEPAL_COPERNICUS_EMSR927;NEPAL_PLANET_ROADS;NEPAL_PLANET_SURFACE_VALIDATION
- Processing scripts: run_experiment_13_nepal_2026_validation.py;run_experiment_13_nepal_planet_surface_validation.py
- Processing method: Label Copernicus restricted/damaged roads as positives; test direct and buffer-distance event rules; separately match Copernicus lines to Nepal Planet surface within 500 m.
- Output: output/experiments/experiment_13_hazard_validation/nepal_2026/
- Key results: Direct observed-event intersection precision 91.01%, recall 86.43%, F1 0.887. Planet surface subset n=987: direct F1 0.887; direct OR unpaved F1 0.850; Planet unpaved-only F1 0.157.
- Limitations: Assessment subset is not population-representative; event polygons denote mass movement; Planet-unpaved independent gain is limited in this event.
- Recorded date: 2026-10-01

### Experiment S8: Corrected all-country SHDI heterogeneity

- Status: Complete
- Purpose: Rerun within-country SHDI/access associations on the corrected model for all seven countries.
- Input source IDs: CORRECTED_SHDI;GDL_SHDI;GDL_REGIONS
- Processing scripts: run_experiment_16_corrected_shdi_all_countries.py
- Processing method: Chunk corrected 1 km cell travel-time files; assign each cell to nearest GDL region; aggregate population-weighted baseline/hazard access; merge SHDI 2020; calculate country-service correlations.
- Output: output/experiments/experiment_16_socioeconomic/corrected_all_countries/
- Key results: Corrected SHDI-access correlations are mostly positive. Examples: Mozambique education baseline weighted Pearson 0.832; Kenya health 0.770; Mozambique health 0.699; Pakistan education 0.675.
- Limitations: Regional ecological associations are not causal; poverty maps remain unavailable; Philippines education remains negative at -0.279.
- Recorded date: 2026-10-01

### Experiment S9: Corrected main-model maps

- Status: Complete
- Purpose: Produce paper-ready corrected health/school baseline and hazard-loss maps.
- Input source IDs: CORRECTED_SHDI;CORRECTED_MAIN_MAPS
- Processing scripts: make_corrected_main_maps.py
- Processing method: Merge corrected GDL-region access summaries with GDL boundaries; plot seven-country facets for health/school baseline and hazard loss; export GPKG layers.
- Output: output/maps/corrected/
- Key results: Four publication-style PNG maps and two GPKG layers for corrected health and school access.
- Limitations: GDL-region choropleths are coarser than 1 km cell results and should be interpreted with MAUP caution.
- Recorded date: 2026-10-01


### Experiment S10: Corrected unknown-surface sensitivity (Philippines pilot)

- Status: Complete
- Purpose: Test unknown-road surface assumptions on a full topology-noded national network after repairing edge-attribute contamination.
- Input source IDs: NODED_CACHE_PHL;HAZARD_CURRENT_PHL;WORLDPOP_PHL;OSM_HEALTH_FACILITIES_PHL;OSM_EDUCATION_FACILITIES_PHL;CORRECTED_UNKNOWN_SURFACE_PHL
- Processing scripts: run_corrected_unknown_surface_sensitivity.py
- Processing method: Compare current slow, as-paved, as-unpaved, no-penalty, class-mean and three random assignments using independent edge dictionaries for each rule.
- Output: output/experiments/corrected_unknown_surface/phl/
- Key results: Relative to current slow, hazard health access changes +0.51 pp as-paved, -1.71 pp as-unpaved, and -0.28 to -0.33 pp across random seeds; hazard education changes +0.01, -0.55, and -0.18 to -0.19 pp.
- Limitations: Historical pilot; superseded by the all-country S16 rerun.
- Recorded date: 2026-10-01

### Experiment S11: Ethiopia facility-level and strong-event sensitivity

- Status: Complete
- Purpose: Decompose Ethiopia health facility types and test three large 2023 flood-event footprints on the corrected national graph.
- Input source IDs: NODED_CACHE_ETH;WORLDPOP_ETH;ETH_HEALTH_REG;ETH_STRONG_FLOOD_EVENTS_2023;ETH_FACILITY_LEVEL_SENSITIVITY
- Processing scripts: run_corrected_ethiopia_a_level.py
- Processing method: Evaluate OSM and registry facility type subsets under baseline/direct hazard; mark three WFP strong-event footprints and compare surface-aware, all-remove and all-slow rules.
- Output: output/experiments/corrected_ethiopia_a_level/
- Key results: Registry primary care reaches 92.26% baseline versus 50.08% with OSM hospital/clinic. Strong-event health losses reach -24.45 pp (2023-11-14 surface-aware) and -48.85 pp (2023-11-21 surface-aware) from the 92.26% baseline.
- Limitations: Facility scopes differ by type/year; three events are selected strong footprints rather than a probability sample.
- Recorded date: 2026-10-01

### Experiment S12: Paper-ready reconciliation and positive-loss convention

- Status: Complete
- Purpose: Repair corrected Gini sign, enforce positive hazard-loss convention, integrate expanded OSRM, and regenerate canonical maps and paper-ready tables.
- Input source IDs: CORRECTED_CORE;CORRECTED_HAZARD_V2;EXPANDED_OSRM_VALIDATION;CORRECTED_SHDI;PAPER_READY_RESULTS_V2
- Processing scripts: build_corrected_core_summary.py;build_corrected_hazard_v2_summary.py;build_paper_ready_results.py;make_corrected_main_maps.py;make_nature_main_figures.py
- Processing method: Correct weighted-Gini sign, define hazard loss as baseline minus hazard, use expanded OSRM summary, clip map losses at zero, make GDL geometries valid, and regenerate outputs/figures.
- Output: output/paper_ready_*.csv;output/maps/corrected/;figures/main/
- Key results: Corrected baseline Gini values are now non-negative (reachable mean 0.606); all main hazard losses are non-negative; expanded OSRM is the canonical routing benchmark.
- Limitations: Derived reconciliation does not add new independent validation data.
- Recorded date: 2026-10-01

### Experiment S13: Nepal Planet surface validation

- Status: Complete
- Purpose: Test whether Planet unpaved surface independently predicts Copernicus road damage in the Nepal 2026 event.
- Input source IDs: NEPAL_COPERNICUS_EMSR927;NEPAL_PLANET_ROADS;NEPAL_PLANET_SURFACE_VALIDATION
- Processing scripts: run_experiment_13_nepal_planet_surface_validation.py
- Processing method: Match Copernicus transportation lines to Nepal Planet roads within 500 m and calculate precision/recall/F1 for direct event intersection, direct OR Planet-unpaved, and Planet-unpaved-only rules.
- Output: output/experiments/experiment_13_hazard_validation/nepal_2026/planet_surface/
- Key results: n=987 matched lines. Direct event intersection F1 0.887; direct OR Planet-unpaved F1 0.850; Planet-unpaved-only precision 45.54%, recall 9.47%, F1 0.157.
- Limitations: Matched subset may favour well-mapped roads; event process is flash flood/mass movement rather than pure inundation.
- Recorded date: 2026-10-01

### Experiment S14: Corrected time dynamics

- Status: Complete
- Purpose: Run 2020/2024 surface transitions on all seven topology-noded national graphs.
- Input source IDs: CORRECTED_TIME_DYNAMICS
- Processing scripts: run_corrected_time_dynamics.py
- Processing method: Build a graph with both year-specific surface labels and travel times; run baseline and surface-aware scenarios with corrected facilities.
- Output: output/experiments/corrected_time_dynamics/
- Key results: Hazard improvements exceed baseline improvements in Pakistan, Mozambique and Kenya; Pakistan health hazard +4.68 pp and Mozambique health hazard +3.07 pp.
- Limitations: OSM local surfaces and non-surface inputs are held constant; 2016 remains unavailable.
- Recorded date: 2026-10-01

### Experiment S15: Corrected OSM versus Planet surface sensitivity

- Status: Complete
- Purpose: Compare Planet priority, OSM tags and OSM-plus-Planet fill on corrected national graphs.
- Input source IDs: CORRECTED_OSM_PLANET_SURFACE
- Processing scripts: run_corrected_osm_planet_surface.py
- Processing method: Map OSM tags and Planet predictions to noded segments; rebuild source-specific graphs; compare known share, agreement and accessibility.
- Output: output/experiments/corrected_osm_planet_surface/
- Key results: Planet-known share exceeds OSM in all seven countries; OSM-only reduces access most in Ethiopia education, Pakistan and Kenya. OSM-plus-Planet fill is not uniformly better than Planet priority because conflicts override Planet labels.
- Limitations: Current OSM local surfaces and deterministic source-priority attribution limit causal interpretation.
- Recorded date: 2026-10-01

### Experiment S16: Corrected unknown-surface sensitivity

- Status: Complete
- Purpose: Rerun unknown-surface sensitivity for all seven corrected national graphs after fixing nested edge contamination.
- Input source IDs: CORRECTED_UNKNOWN_SURFACE
- Processing scripts: run_corrected_unknown_surface_sensitivity.py
- Processing method: Apply eight unknown-handling rules with independent edge attribute updates; report baseline/hazard access and removed-edge counts.
- Output: output/experiments/corrected_unknown_surface/
- Key results: Hazard mean changes are +1.81 pp as-paved, -9.55 pp as-unpaved and about -6.6 pp random. Largest stress-test loss is Pakistan health -41.55 pp.
- Limitations: As-unpaved is a deliberately severe stress test; class/random assumptions do not use imagery or contextual covariates.
- Recorded date: 2026-10-01

### Experiment S17: Corrected multi-event accessibility

- Status: Complete
- Purpose: Run the curated 18-event archive on corrected national graphs with official-union facilities.
- Input source IDs: MULTI_EVENT_ARCHIVE;CORRECTED_MULTI_EVENTS
- Processing scripts: run_corrected_multi_events.py
- Processing method: Load each country graph once; spatially join event footprints to road representative points; apply direct surface-aware disruption and merge corrected baseline loss.
- Output: output/experiments/corrected_multi_events/
- Key results: Corrected health losses range from 0 to 26.61 pp; Pakistan 2025 is 21.53 pp and Mozambique 2025 is 26.61 pp, while many small footprints are near zero.
- Limitations: Convenience event sample; no annual probabilities, protection assumptions or climate projections.
- Recorded date: 2026-10-01


### Experiment 28: Learned cross-event road passability

- Status: Partial
- Purpose: Test whether a learned model transfers between observed road-status events and improves over hand-designed hazard rules.
- Input source IDs: WFP_IDAI_CONSTRAINTS;IDAI_FLOOD_RASTER;NEPAL_COPERNICUS_EMSR927;NEPAL_PLANET_ROADS;LEARNED_PASSABILITY
- Processing scripts: run_experiment_28_learned_passability.py
- Processing method: Combine Idai and Nepal labelled roads; use hazard distance, Planet surface, match distance and interactions; test logistic, balanced logistic and random forest with leave-one-event-out and pooled stratified CV.
- Output: output/experiments/experiment_28_learned_passability/
- Key results: Pooled 5-fold random-forest AUC is 0.931, but leave-one-event-out transfer is poor (for example AUC 0.44 Nepal-to-Idai and 0.48-0.81 Idai-to-Nepal depending model). Simple best rules remain event-specific.
- Limitations: Only two events; hazard semantics differ; no terrain, hydrology, bridge or rainfall covariates; pooled CV is not spatial transfer evidence.
- Recorded date: 2026-10-01

### Experiment 29: Representative 30-country expansion

- Status: Partial
- Purpose: Create a pre-specified stratified expansion sample, validate input availability, and progressively build corrected national accessibility models beyond the original seven countries.
- Input source IDs: EXPANSION_SAMPLE;EXPANSION_PLANET_ROADS_23;EXPANSION_WORLDPOP_23;EXPANSION_OSM_FACILITIES_23;EXPANSION_ARTERIAL_BASELINE;EXPANSION_FULL_ROADS_23;EXPANSION_CORRECTED_23
- Processing scripts: run_experiment_29_global_expansion_design.py;download_experiment_29_inputs.py;audit_experiment_29_facility_exports.py;download_experiment_29_facilities.py;extract_experiment_29_facilities.py;audit_experiment_29_full_osm_roads.py;download_experiment_29_full_osm_roads.py;run_experiment_29_arterial_baseline.py;run_experiment_29_corrected_countries.py;run_experiment_29_corrected_tiled.py;validate_tiled_vs_canonical.py;build_corrected_expansion_summary.py;audit_experiment_29_data.py;check_worldpop_units.py;build_expansion_data_provenance.py;run_experiment_29_weight_sensitivity.py;build_weight_sensitivity_summary.py;probe_hdx_hazards.py;run_experiment_29_hazard_pilot.py
- Processing method: Pre-specify 30 countries; audit/download Planet roads, WorldPop, OSM facilities and full-road archives; run the 23-country arterial baseline; topology-node Planet+OSM roads for all 23 additions (union/nodal noding, nearest-source attribute inheritance, multi-source Dijkstra) and compute corrected baseline access. Large additions use the tiled memory-bounded runner (1.5-degree tiles with adaptive sub-tiling, tile-local nearest joins, DuckDB node/edge collapse). The tiled runner was validated against the canonical runner on Sri Lanka (access shares within 0.014 pp; noded length within 0.0007%) and Nepal (within 0.049 pp; length within 0.005%). A full data audit then checked input inventory, baseline consistency, population units, the length metric and hazard coverage, and produced corrected variants (count weights, geodesic lengths, no-unpaved and unknown-as-unpaved scenarios) plus an observed-event hazard pilot.
- Output: output/experiments/experiment_29_global_expansion/; EXPANSION_DATA_AUDIT.md; EXPANSION_DATA_PROVENANCE.md
- Key results: 30/30 Planet and WorldPop URLs available; 46/46 facility exports available; 23-country arterial baseline complete; all 23 additions have corrected noded baselines (46 country-service rows, up to 31.4M noded segments for India). Local-road correction ranges from -24.65 pp (PNG health) to +73.98 pp (Egypt health); India health rises 77.74% -> 97.48% and India education 55.31% -> 90.36%. Audit: the WorldPop `*_pd_2020_1km.tif` layer is a density raster, so canonical absolute populations are inflated 1.16-1.82x (population-weighted shares move only -0.08 to +0.11 pp); EPSG:3857 segment lengths overstate distance by up to +35% at high latitude, which raises 30-min access by up to +6.90 pp (Kyrgyzstan health) once corrected. Uniform stress tests: removing unpaved roads costs up to 61.60 pp of 60-min access (Tanzania health); unknown-as-unpaved costs up to 4.88 pp (Cambodia health). Observed-event hazard pilot: Viet Nam 2020 cyclone (2 962 km2, 2.56M people, 229 869 affected segments) costs -0.71 pp health 30-min access, Indonesia 2025 Aceh -0.21 pp, India 2015 Chennai/coastal Tamil Nadu (16 087 km2, 4.36M people) -0.04 pp, Nigeria 2022 Yobe 0.00 pp (21 km2 footprint touches no mapped road).
- Limitations: Expansion baselines use OSM-only facilities and no official registries; hazard footprints exist only for the four pilot additions (the other 19 need UNOSAT/HDX sourcing, see probe_hdx_hazards.py); corrected expansion networks are single Planet+OSM snapshots; corrected access can fall below the arterial-only baseline (PNG health -24.65 pp), so both must always be reported; the density-as-counts and Web-Mercator conventions are inherited from the core pipeline and should be re-run there as well.
- Recorded date: 2026-10-02

### Experiment 30: Empirical probabilistic-risk diagnostic
- Status: Partial
- Purpose: Convert corrected multi-event losses into an explicit empirical annual-frequency and exceedance diagnostic while avoiding an unsupported annual expected-loss claim.
- Input source IDs: MULTI_EVENT_ARCHIVE;CORRECTED_MULTI_EVENTS;EMPIRICAL_ARCHIVE_RISK
- Processing scripts: run_experiment_30_empirical_risk.py
- Processing method: Use 2018-2026 annual maxima from the corrected event archive, zero-loss years without archived events, Weibull exceedance positions, and 10,000 bootstrap resamples.
- Output: output/experiments/experiment_30_probabilistic_risk/
- Key results: Mean archived-event annual loss is 3.04 pp for Pakistan health, 3.09 pp for Pakistan education and 2.97 pp for Mozambique health, but bootstrap intervals are wide (Pakistan health 0.24-7.84 pp; Mozambique health 0-8.88 pp).
- Limitations: Convenience event sample; no representative event probabilities or return-period hazard layers; values must not be called annual expected loss or climate risk.
- Recorded date: 2026-10-01

### Experiment 31: Nested counterfactual of the local-road effect

- Status: Complete (30/30 countries)
- Purpose: Re-measure the "adding local roads" effect on a single node basis so that the local-edge effect, the snapping/coverage rule and the attribute-inheritance residual can be separated; the published arterial-only versus corrected comparison mixes two different pipelines.
- Input source IDs: EXPANSION_FULL_ROADS_23; CORE_GRID; EXPANSION_WORLDPOP_23; OSM_HEALTH_FACILITIES_*; OSM_EDUCATION_FACILITIES_*
- Processing scripts: run_nested_counterfactual.py
- Processing method: Stream each cached `{iso}_noded_segments.gpkg` in 750k-feature chunks, rebuild canonical node keys (lon/lat rounded to 7 decimals), collapse each node pair to its minimum travel time, and build a symmetric sparse graph. Five scenarios share the same population cells and facility set: (A) arterial edges only with origins/facilities snapped to the arterial node set; (B_shared) all edges with the same snapping basis; (B_full) all edges with snapping to all nodes (= the canonical published pipeline); (B_full_speed115 / B_full_speed130) as B_full with all travel times divided by 1.15 / 1.30.
- Output: output/experiments/nested_counterfactual/{iso}_nested_counterfactual.csv (30 countries), run_log.txt, run_log_2.txt
- Key results: the reconstruction reproduces the published corrected 60-min shares (30 countries, 60 country-service rows: mean gap +0.001 pp, maximum absolute gap 0.052 pp), so the decomposition and the main results are on the same basis. Largest rebuilt network is India (31.4M segments, 26.2M nodes, 930 s for graph construction); the full batch covers 30/30 countries.
- Limitations: origins are still snapped with zero explicit access cost (that convention is the object of study, not an error); facility tiers are the canonical hospital+clinic / school sets; the arterial subgraph keeps the union network's node coordinates, which is what makes the comparison nested.
- Recorded date: 2026-10-02

### Experiment 32: Decomposition of the local-road effect and permutation null

- Status: Complete (60 country-service rows)
- Purpose: Quantify how much of the published local-road effect comes from local edges, from the snapping/coverage rule, and from attribute/pipeline differences; test whether the published "direction law" (delta_pp regressed on arterial coverage) can be distinguished from a difference-score artefact.
- Input source IDs: NESTED_COUNTERFACTUAL; CORRECTED_MAIN; GRIP4_DENSITY
- Processing scripts: build_direction_law_v2.py
- Processing method: Decompose delta_published = delta_edges + delta_snapping + delta_residual; fit each variant with OLS and 2 000 country-bootstrap resamples; run a 2 000-draw permutation null that shuffles the corrected outcome while holding arterial coverage fixed; repeat with an independent geometric predictor (arterial length share = 100 - local share from the GRIP4 cross-check table); test slope != 1 for corrected ~ arterial coverage; refit with country means (n = 30) and a country random-intercept mixed model; recompute under the two speed-calibration scenarios.
- Output: output/experiments/direction_law_v2/{nested_decomposition.csv, direction_law_variants.csv, direction_law_permutation.csv, summary.txt, run_log.txt}
- Key results: local-edge effect mean +9.71 pp and never negative (0/60 rows; range +0.22 to +44.23); snapping/coverage term mean -7.25 pp (min -28.66); residual mean +12.74 pp. The published relationship reproduces (r = -0.876, R2 = 0.768, break-even 91.8%, slope CI [-0.964, -0.647]) but its R2 sits at the 0.8th percentile of the permutation null (null mean 0.810, 95% range 0.774-0.848); corrected shares regress on arterial coverage with slope 0.195 (test of slope = 1: p < 1e-9); the geometric predictor gives r = +0.309 (p = 0.016, sign reversed); the nested local-edge effect correlates only weakly with arterial coverage (r = -0.261, p = 0.044, R2 = 0.068; -0.309 / -0.350 under speed x1.15 / x1.30).
- Limitations: the permutation null targets the published difference-score form, not the nested effect; the geometric predictor is a length share, not a population-weighted coverage measure; all relationships remain predictive, not causal.
- Recorded date: 2026-10-02

### Experiment 33: Hazard placement null model and channel decomposition

- Status: Complete (2 dominant events x 2 services, 20 draws each)
- Purpose: Test whether the exposure-loss relation depends on where the affected roads are, or only on how much of the network is affected, and split the surface-aware rule into its two channels.
- Input source IDs: NODED_SEGMENTS_30; HAZARD_EVENT_TABLE; WORLDPOP_2020
- Processing scripts: run_hazard_null_model.py
- Processing method: For MOZ 2025-03 and PAK 2025-09, rebuild the country graph, reproduce the observed surface-aware loss, then draw 20 random road sets that match the observed affected length of unpaved and paved roads and recompute the loss (placement null). Report loss with only the unpaved-removal channel and with only the paved-doubling channel.
- Output: output/experiments/hazard_null_model/{hazard_null_model.csv, run_log.txt}
- Key results: observed loss MOZ health 25.25 pp vs length-matched random 26.26 pp (2.5-97.5: 25.93-26.57); PAK health 20.73 vs 20.58 (20.52-20.66); the largest observed-vs-null gap across the four cases is 0.34 pp, i.e. the spatial pattern of the footprint adds no measurable information beyond the affected length. Channel decomposition: MOZ is removal-dominated (18.82 vs 9.13 pp) while PAK is doubling-dominated (3.26 vs 17.75 pp), consistent with its 87.7% affected share.
- Limitations: only the two current-footprint events can be reproduced from the cached layers; affected length (not return period) is held constant; both events affect very large shares, so the test is near saturation and does not cover moderate events.
- Recorded date: 2026-10-02

### Experiment 34: Cross-product comparability (four measurement conventions)

- Status: Complete (30 countries)
- Purpose: Turn the intro's motivating claim ("the same country's estimates differ by tens of percentage points") into a verifiable quantity.
- Input source IDs: WEISS_TRAVEL; MAP_BENCHMARK; CORRECTED_MAIN; WORLDPOP_2020
- Processing scripts: build_interstudy_comparison.py
- Processing method: Convert each product to the same population-weighted 60-min share on the WorldPop 2020 cell grid: Weiss/Nelson 2015 travel time to the nearest urban area >=50k (raster sampled per country window), MAP 2020 motorised travel time to healthcare, this model arterial-only, and this model with local roads. Report the within-country spread, and the restricted variants (2020+ products only; same model/same year/same population only).
- Output: output/experiments/interstudy_comparison/{weiss_60min_by_country.csv, interstudy_60min_comparison.csv, interstudy_summary.csv}
- Key results: within-country spread across the four conventions has median 30.7 pp and maximum 77.8 pp (Egypt), with 24/30 countries above 20 pp; restricting to 2020+ products gives median 21.2 pp and 16/30 above 20 pp; fixing model, year and population (arterial-only vs with local roads) still gives median 18.8 pp and maximum 75.3 pp (15/30 above 20 pp). The Weiss/Nelson layer is a 2015 product and is used only for this comparability display.
- Limitations: the four products differ in target definition (towns vs health facilities vs schools) as well as in vintage; the comparison therefore demonstrates non-comparability and cannot adjudicate which product is more accurate.
- Recorded date: 2026-10-02

### Experiment 35: Effect distributions with bootstrap CIs and rank sensitivity

- Status: Complete
- Purpose: Report every measurement-convention effect as a distribution with uncertainty instead of a single maximum, and check whether country rankings depend on the product chosen.
- Input source IDs: FACILITY_SCENARIOS; FACILITY_REGISTRY; UNCERTAINTY_ENVELOPE; WEIGHT_LENGTH_SENSITIVITY; INTERSTUDY_COMPARISON
- Processing scripts: build_effect_distributions.py
- Processing method: 5 000 country-level bootstrap resamples for the mean of each effect family; rank comparison between this model's corrected convention and the mean of three independent products (Spearman plus per-country rank shifts).
- Output: output/experiments/effect_distributions/{effect_distributions.csv, rank_comparison.csv}
- Key results: hospital-only penalty 4.19 pp (95% CI 2.07-6.83, max 30.37); all mapped health points +1.26 pp (0.82-1.76); independent-registry gain +3.14 pp (1.33-5.19, n = 12); no-unpaved stress loss 18.16 pp (14.33-22.18); length effect 0.66 pp at 60 min (0.47-0.88) and 1.32 pp at 30 min (0.93-1.76); population units -0.01 pp (-0.02 to 0.01); facility-source effect 0.63 pp (0.19-1.17); envelope width 1.21 pp (0.76-1.74). Rank sensitivity: Spearman 0.874 with median rank shift 3 and maximum 12 (Nigeria).
- Limitations: bootstrap CIs describe the sampled 30 countries only; rank shifts mix product definition, vintage and model error.
- Recorded date: 2026-10-02

### Experiment 36: Per-country OSM/HOT snapshot dates

- Status: Complete (30/30)
- Purpose: Remove the vague "2024-2026 snapshot" wording by documenting the exact extraction date of every local-road and facility layer.
- Input source IDs: OSM_HEALTH_FACILITIES_*; OSM_EDUCATION_FACILITIES_*; EXPANSION_FULL_ROADS_23
- Processing scripts: build_osm_snapshot_dates.py
- Processing method: Parse the `Snapshot:` / `Generated:` fields of the Readme.txt shipped with each HDX/oex export.
- Output: output/experiments/osm_snapshots/osm_snapshot_dates.csv
- Key results: all 30 countries have a documented road and facility snapshot; dates span 2026-05-05 (Indonesia, Peru, Philippines, Egypt...) to 2026-09-10 (Tanzania).
- Limitations: the exact extract timestamp is a property of the HDX export, not of the underlying OSM data at query time; population (2020), Planet surface (2024) and OSM (2026) remain different vintages by design.
- Recorded date: 2026-10-02

### Experiment 37: SHDI year sensitivity

- Status: Complete (52 country-service rows)
- Purpose: Test whether the subnational development gradient depends on the SHDI year, given that the manuscript pairs SHDI 2020 with WorldPop 2020.
- Input source IDs: GDL_SHDI; SHDI_ACCESS_REGIONS
- Processing scripts: build_shdi_year_sensitivity.py
- Processing method: Recompute population-weighted within-region SHDI-access correlations for 2018-2023 using the same region table and the same within-region share definition as run_shdi_30countries.py.
- Output: output/experiments/shdi_year_sensitivity/{shdi_year_correlations.csv, summary.txt}
- Key results: the 2020 recomputation matches the published correlation table exactly (mean absolute difference 0.000), confirming the deposit reproduces; per country-service values for 2020 and 2023 correlate at r = 0.994 with mean absolute change 0.023 and maximum 0.172; the number of negative rows stays at 8/52.
- Limitations: population and urban/rural vintages were not swapped (only the 2020 WorldPop raster is stored locally); the test therefore covers the socioeconomic layer only.
- Recorded date: 2026-10-02
