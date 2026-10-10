# Corrected Main Model Specification

Last updated: 2026-10-01

## Purpose
This file fixes the analytical version used as the paper main model. Earlier arterial-only and OSM-only runs are lower-bound sensitivity analyses, not the main result.

## Main model
1. Road network: topology-noded Planet arterial roads + HOT OSM motorable local roads.
2. Speed model: M3 = road class x surface x width.
3. Population: WorldPop 2020 1 km positive pixels.
4. Facilities: best-available official registry union:
   - Ethiopia health: OSM hospital/clinic + 3iS hospital/clinic/health-centre union.
   - Bangladesh education: OSM schools + LGED union.
   - Mozambique health: OSM hospital/clinic + OCHA MFL union.
   - Other country/service pairs: HOT OSM facilities.
5. Facility snapping: nearest noded node within 1 km.
6. Population snapping: nearest noded node, no maximum distance.
7. Main hazard rule: direct surface-aware rule; affected unpaved edges are removed and affected paved/unknown edges have travel time doubled.
8. Main metric: population share within 60 minutes; 30/120/240 minutes are supporting metrics.
9. Interpretation: corrected service access on the available motorable network, not door-to-door travel.

## Correct outputs
- output/experiments/corrected_core/
- output/paper_ready_main_access.csv
- output/paper_ready_model_ablation.csv
- output/paper_ready_hazard_rule_sensitivity.csv
- output/paper_ready_inequality.csv
- output/paper_ready_corrected_shdi_correlations.csv
Corrected experiments already run:
- Experiment 6 road-quality ablation.
- Experiment 8 direct hazard-rule ablation.
- Experiment 15 urban/rural heterogeneity.
- Experiment 17 inequality and density-quintile summaries.

## Robustness, not main model
- arterial-only network;
- OSM-only facilities;
- registry-only facilities;
- no-unpaved stress test;
- all-remove/all-slow/surface-only rules;
- direct OR unpaved rule;
- true 5-km buffer rules in corrected_hazard_rules_v2;
- speed/surface/width/unknown/space/MAUP/Monte Carlo sensitivity;
- South Sofala investment case.

## Claims not allowed
Do not claim global estimates, annual expected loss, future climate risk, causal socioeconomic effects, complete door-to-door access, or exact investment optimisation.

## Reporting conventions

1. Hazard loss is positive: `baseline - surface-aware hazard`.
2. Expanded OSRM output (`553` routes; robust subset `181`) is the current routing benchmark.
3. Corrected Gini values use the sign-corrected weighted implementation.
4. Figures that use arterial-only multi-event outputs must label them as sensitivity diagnostics rather than corrected main-model estimates.
