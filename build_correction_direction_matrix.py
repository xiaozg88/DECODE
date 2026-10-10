# -*- coding: utf-8 -*-
"""Correction-direction matrix: arterial-only versus topology-noded accessibility.

Combines the seven core countries (Experiment 24, OSM facilities, 60-minute access)
with the 23 expansion additions (`arterial_vs_corrected_expansion.csv`) into one
table, adds regional/income context, the Planet known-surface share of the arterial
network and the audit-corrected variants, and reports where the correction flips sign.

Outputs
-------
* ``output/experiments/correction_direction/correction_direction_matrix.csv``
* ``output/experiments/correction_direction/planet_surface_availability.csv``
"""
from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
EXP = ROOT / 'output/experiments/experiment_29_global_expansion'
OUT_DIR = ROOT / 'output/experiments/correction_direction'
SURFACE_CSV = OUT_DIR / 'planet_surface_availability.csv'
MATRIX_CSV = OUT_DIR / 'correction_direction_matrix.csv'
ROADS = ROOT / 'data/external/hdx/roads'


def planet_known_share(force: bool = False) -> pd.DataFrame:
    """Length-weighted known-surface share of the Planet arterial layer per country."""
    if SURFACE_CSV.exists() and not force:
        return pd.read_csv(SURFACE_CSV)
    sample = pd.read_csv(EXP / 'country_sample_and_input_availability.csv')
    rows = []
    for _, r in sample.iterrows():
        path = ROADS / f'heigit_{r.iso2}_planet_roadsurface_lines.gpkg'
        if not path.exists():
            rows.append({'iso3': r.iso3, 'planet_known_share_pct': np.nan,
                         'planet_arterial_km': np.nan})
            continue
        g = gpd.read_file(path, columns=['DL_road_class_2024', 'geometry'])
        if g.crs is None:
            g = g.set_crs(4326)
        length = g.to_crs(3857).geometry.length.to_numpy() / 1000.0
        cls = g.DL_road_class_2024.astype(str).str.lower()
        known = cls.isin(['paved', 'unpaved'])
        rows.append({'iso3': r.iso3, 'planet_segments': len(g),
                     'planet_arterial_km': float(length.sum()),
                     'planet_known_share_pct': float(100 * length[known].sum() / max(length.sum(), 1e-9))})
        print(f'{r.iso3}: known {rows[-1]["planet_known_share_pct"]:.1f}% '
              f'({length.sum():,.0f} km)', flush=True)
    out = pd.DataFrame(rows)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out.to_csv(SURFACE_CSV, index=False, encoding='utf-8-sig')
    return out


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    sample = pd.read_csv(EXP / 'country_sample_and_input_availability.csv')
    core = pd.read_csv(ROOT / 'output/experiments/experiment_24_network_integrity'
                       / 'all_countries_noded_vs_arterial_60min.csv')
    core = core[(core.scenario == 'baseline')].copy()
    core['service'] = core.service.replace({'school': 'education'})
    core = core.rename(columns={'noded_60min_pct': 'corrected_60min_pct',
                                'noded_minus_arterial_pct_points': 'corrected_minus_arterial_pp'})
    core['group'] = 'core'
    core = core[['iso3', 'service', 'arterial_60min_pct', 'corrected_60min_pct',
                 'corrected_minus_arterial_pp', 'group']]
    add = pd.read_csv(EXP / 'corrected_countries/arterial_vs_corrected_expansion.csv')
    add['group'] = 'addition'
    add = add[['iso3', 'service', 'arterial_60min_pct', 'corrected_60min_pct',
               'corrected_minus_arterial_pp', 'noded_segments', 'group']]
    matrix = pd.concat([core.assign(noded_segments=np.nan), add], ignore_index=True)
    matrix = matrix.merge(sample[['iso3', 'country', 'region', 'income_group', 'hazard_profile']],
                          on='iso3', how='left')
    matrix = matrix.merge(planet_known_share(), on='iso3', how='left')
    sens = pd.read_csv(EXP / 'weight_length_sensitivity_summary.csv')
    sens = sens[['iso3', 'service', 'share_60min_corrected_pct',
                 'share_30min_geodesic_minus_canonical_pp']].rename(
        columns={'share_60min_corrected_pct': 'corrected_counts_geodesic_60min_pct',
                 'share_30min_geodesic_minus_canonical_pp': 'geodesic_30min_delta_pp'})
    matrix = matrix.merge(sens, on=['iso3', 'service'], how='left')
    matrix['sign'] = np.where(matrix.corrected_minus_arterial_pp > 0.5, 'improves',
                              np.where(matrix.corrected_minus_arterial_pp < -0.5, 'worsens', 'flat'))
    matrix = matrix.sort_values(['group', 'corrected_minus_arterial_pp'], ascending=[True, False])
    matrix.to_csv(MATRIX_CSV, index=False, encoding='utf-8-sig')
    pd.set_option('display.width', 250)
    pd.set_option('display.max_rows', 100)
    print(f'wrote {MATRIX_CSV} ({len(matrix)} rows)')
    print()
    print(matrix[['iso3', 'group', 'service', 'arterial_60min_pct', 'corrected_60min_pct',
                  'corrected_minus_arterial_pp', 'sign', 'region', 'income_group',
                  'planet_known_share_pct']].round(2).to_string(index=False))
    print()
    print('=== sign summary ===')
    print(matrix.groupby(['group', 'sign']).size().to_string())
    print()
    print('=== by region (mean delta pp) ===')
    print(matrix.groupby('region').corrected_minus_arterial_pp.agg(['count', 'mean', 'min', 'max'])
          .round(2).to_string())
    print()
    print('=== by income group (mean delta pp) ===')
    print(matrix.groupby('income_group').corrected_minus_arterial_pp.agg(['count', 'mean', 'min', 'max'])
          .round(2).to_string())
    print()
    print('=== correlation with Planet known-surface share ===')
    sub = matrix.dropna(subset=['planet_known_share_pct'])
    print(sub[['planet_known_share_pct', 'corrected_minus_arterial_pp']].corr().round(3).to_string())
    print()
    print('=== correction magnitude vs arterial-only baseline ===')
    ok = matrix.dropna(subset=['arterial_60min_pct', 'corrected_minus_arterial_pp'])
    slope, intercept = np.polyfit(ok.arterial_60min_pct, ok.corrected_minus_arterial_pp, 1)
    pred = slope * ok.arterial_60min_pct + intercept
    ss_res = float(((ok.corrected_minus_arterial_pp - pred) ** 2).sum())
    ss_tot = float(((ok.corrected_minus_arterial_pp - ok.corrected_minus_arterial_pp.mean()) ** 2).sum())
    print(f'delta = {intercept:.1f} + {slope:.3f} x arterial_60min   '
          f'(r={ok.arterial_60min_pct.corr(ok.corrected_minus_arterial_pp):.3f}, '
          f'R2={1 - ss_res / ss_tot:.3f}, n={len(ok)})')
    print(f'break-even arterial coverage where the correction stops helping: '
          f'{-intercept / slope:.1f}%')


if __name__ == '__main__':
    main()
