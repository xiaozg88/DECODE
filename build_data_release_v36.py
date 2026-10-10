# -*- coding: utf-8 -*-
"""v36：把正文/SI 引用的所有派生表统一并入 release/data，并更新 MANIFEST.csv。"""
from __future__ import annotations

import hashlib
import os
import shutil

ROOT = os.path.dirname(os.path.abspath(__file__))
DST = os.path.join(ROOT, 'release/data')
MANIFEST = os.path.join(ROOT, 'release/MANIFEST.csv')
os.makedirs(DST, exist_ok=True)

# (source_relative, dest_name, description)
FILES = [
    ('output/experiments/direction_law_v2/nested_decomposition.csv',
     'nested_decomposition.csv',
     'Core 60-row (30 countries x health/education) decomposition: arterial coverage, nested counterfactual shares, delta edge/conv/total, baseline and protocol gaps.'),
    ('output/experiments/interstudy_comparison/interstudy_60min_comparison.csv',
     'interstudy_60min_comparison.csv',
     'Four-product 60-min access comparison (Weiss 2015, MAP 2020, arterial-only, full-network) for 30 countries.'),
    ('output/experiments/v31/e4_external_target.csv',
     'e4_external_target.csv',
     'External-target test (E4): five difference forms x OLS/LOCO/direction/negative-count/null percentiles, 30 countries.'),
    ('output/experiments/v31/e4_external_target.json',
     'e4_external_target.json',
     'External-target test (E4) combined records (JSON).'),
    ('output/experiments/v31/e4_external_target_sensitivity.csv',
     'e4_external_target_sensitivity.csv',
     'External-target sensitivity: MAP-minus-arterial after removing Papua New Guinea.'),
    ('explorations/output/d09_access_identity_flip_summary.csv',
     'd09_access_identity_flip_summary.csv',
     'Per-cell 60-min access-identity flip between arterial-only and full-network conventions (the 985-million figure).'),
    ('explorations/output/d08_sdg_rai_rural_corrected.csv',
     'd08_sdg_rai_rural_corrected.csv',
     'SDG 9.1.1 Rural Access Index recomputation with the corrected GHS-SMOD rural mask (classes 11-13): paved/all-road 2-km rural shares and misclassified population.'),
    ('explorations/output/d12_sdg_reproduction_table.csv',
     'd12_sdg_reproduction_table.csv',
     'SDG 9.1.1 reproduction table (corrected rural mask), Chinese column labels.'),
    ('output/experiments/effect_distributions/effect_distributions.csv',
     'effect_distributions.csv',
     'Country-level bootstrap 95% CIs and rank sensitivity for convention effects.'),
    ('output/experiments/osm_snapshots/osm_snapshot_dates.csv',
     'osm_snapshot_dates.csv',
     'Per-country OSM/HOT road and facility snapshot dates (2026-05-05 to 2026-09-10).'),
    ('output/experiments/sample_framework/sample_coverage.csv',
     'sample_coverage.csv',
     'Stratified purposive sample coverage: income groups, regions, hazard types, road-density range.'),
    ('output/experiments/numerical_audit/numerical_audit.csv',
     'numerical_audit.csv',
     'Numerical audit table: every key number traced back to its source CSV.'),
    ('output/experiments/shapley_decomposition/shapley_all_countries.csv',
     'shapley_all_countries.csv',
     'Shapley decomposition of the two-switch order across all countries.'),
    ('output/experiments/spatial_null_model/spatial_null_model.csv',
     'spatial_null_model.csv',
     'Spatial null-model fits for the exposure-loss relationship.'),
    ('output/experiments/hazard_null_model/hazard_null_model.csv',
     'hazard_null_model.csv',
     'Equal-length random-placement null model for hazard exposure-loss.'),
    ('output/experiments/nonrandom_missing_road_stress/stress_nonrandom_summary.csv',
     'stress_nonrandom_summary.csv',
     'Non-random (rural/low-population/remote) road-deletion stress test summary.'),
    ('output/experiments/grip4_calibrated_stress/grip4_calib_summary.csv',
     'grip4_calib_summary.csv',
     'GRIP4-anchored calibrated road-deletion stress test.'),
    ('output/experiments/access_cost_model/access_cost_all_countries.csv',
     'access_cost_all_countries.csv',
     'Explicit last-mile access-cost sensitivity (walking 5 km/h, detour 1.4) across countries.'),
    ('output/experiments/v28/e1_edge_by_threshold.csv',
     'e1_edge_by_threshold.csv',
     'Edge increment at 30/60/120-minute thresholds (constructive-constraint verification).'),
    ('output/experiments/v28/e2b_null_models.json',
     'e2b_null_models.json',
     'Three permutation null models (complete/stratified/block bootstrap) for the difference-form fits.'),
    ('output/experiments/v28/e3_results.json',
     'e3_results.json',
     'Robust inference results (OLS, clustered, Huber, mixed model, LOCO).'),
    ('output/experiments/mapwithai_crosscheck/three_way_crosscheck_summary.csv',
     'three_way_crosscheck_summary.csv',
     'Three-way cross-check (OSM/GRIP4/Map With AI) of road-network completeness.'),
    ('output/experiments/mapwithai_calibrated_stress/mapwithai_calib_summary.csv',
     'mapwithai_calib_summary.csv',
     'Map With AI-anchored calibrated road-deletion stress test.'),
    ('output/experiments/missing_road_stress/stress_all.csv',
     'stress_all.csv',
     'Random road-deletion stress test (10/25/50% and all-unpaved/all-low-class).'),
    ('explorations/output/d01_rai.csv',
     'd01_rai.csv',
     'Total-population 2-km paved/all-road shares (RAI exploration, d01).'),
    ('explorations/output/d04_connectivity_all.csv',
     'd04_connectivity_all.csv',
     'Network connectivity and redundancy indicators per country.'),
    ('explorations/output/d05_top_education_deserts.csv',
     'd05_top_education_deserts.csv',
     'Top education service-desert regions.'),
    ('explorations/output/d05_top_health_deserts.csv',
     'd05_top_health_deserts.csv',
     'Top health service-desert regions.'),
    ('explorations/output/d10_maup_mechanism.csv',
     'd10_maup_mechanism.csv',
     'MAUP mechanism: aggregation-order sensitivity and within-cell heterogeneity.'),
    ('explorations/output/d11_decomposition_orders.csv',
     'd11_decomposition_orders.csv',
     'Decomposition-order robustness (two Shapley orders).'),
    ('explorations/output/d13_facility_road_2x2.csv',
     'd13_facility_road_2x2.csv',
     'Facility-definition x road-network 2x2 interaction.'),
    ('explorations/output/d14_capacity_availability.csv',
     'd14_capacity_availability.csv',
     'Facility capacity attribute availability across open data.'),
    ('explorations/output/d17_extra_country_sensitivity.csv',
     'd17_extra_country_sensitivity.csv',
     'Out-of-sample five-country convention sensitivity.'),
    ('explorations/output/d19_extra_country_edge_sign.csv',
     'd19_extra_country_edge_sign.csv',
     'Out-of-sample five-country pure edge-increment sign.'),
    ('explorations/output/d20_noding_equivalence.csv',
     'd20_noding_equivalence.csv',
     'Tiled vs global-union noding equivalence (5 countries).'),
]


def sha256(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest().upper()


def main():
    existing = set()
    if os.path.exists(MANIFEST):
        for line in open(MANIFEST, encoding='utf-8-sig'):
            parts = line.rstrip('\n').split(',')
            if len(parts) >= 2:
                existing.add(parts[1])

    new_rows = []
    copied = 0
    for src_rel, dest, desc in FILES:
        src = os.path.join(ROOT, src_rel)
        if not os.path.exists(src):
            print('MISS', src_rel)
            continue
        dst = os.path.join(DST, dest)
        shutil.copyfile(src, dst)
        copied += 1
        size = os.path.getsize(dst)
        h = sha256(dst)
        key = 'data/' + dest
        if key not in existing:
            new_rows.append(f'data,{key},{size},{h},"{desc}"\n')
        else:
            print('SKIP (already in manifest)', key)

    with open(MANIFEST, 'a', encoding='utf-8') as f:
        f.writelines(new_rows)
    print(f'copied {copied} files, appended {len(new_rows)} manifest rows')


if __name__ == '__main__':
    main()
