# -*- coding: utf-8 -*-
"""Experiment B (part 3): aggregate the three-way inventory cross-check.

Combines the Map-With-AI density/cell results with the existing model and GRIP4
tables, and compares the two independent completeness anchors (GRIP4 total
density vs Meta satellite-detected missing roads) country by country.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

OUT = ROOT / 'output/experiments/mapwithai_crosscheck'
CELLS = OUT / 'ai_cells'
SUBSET = ['KHM', 'GTM', 'BGD', 'SEN', 'NGA', 'ETH', 'MOZ', 'PNG', 'EGY', 'TUR']


def main() -> None:
    nc = pd.read_csv(ROOT / 'output/experiments/network_completeness'
                     / 'network_completeness_by_country.csv').set_index('iso3')
    gr = pd.read_csv(ROOT / 'output/experiments/grip4_completeness'
                     / 'grip4_vs_network_density.csv').set_index('iso3')
    ai = pd.read_csv(OUT / 'ai_country.csv').set_index('iso3')

    tab = pd.DataFrame(index=SUBSET)
    tab['model_density_km_km2'] = nc['road_density_km_per_km2']
    tab['grip4_density_km_km2'] = gr['grip_all_mean_density'] / 1000.0
    tab['ai_density_km_km2'] = ai['ai_density_country_km_km2']
    tab['local_km'] = nc['local_km']
    tab['ai_km'] = ai['ai_km_mercator']
    tab['ai_km_per_local_km'] = tab['ai_km'] / tab['local_km']
    tab['f_ai'] = tab['ai_km'] / (tab['local_km'] + tab['ai_km'])
    tab['f_grip4'] = ((tab['model_density_km_km2'] - tab['grip4_density_km_km2'])
                      / (nc['local_km'] / nc['area_km2']))
    tab['f_grip4'] = tab['f_grip4'].clip(0, 1)

    # rural share of AI-detected missing road length
    rural_share = {}
    for iso in SUBSET:
        c = pd.read_csv(CELLS / f'{iso}_cells.csv')
        rural = c[c.urban_rural == 'rural']['ai_len_m'].sum()
        tot = c['ai_len_m'].sum()
        rural_share[iso] = rural / max(tot, 1e-9)
    tab['ai_rural_share'] = pd.Series(rural_share)

    # dual-anchor comparison
    gc = pd.read_csv(ROOT / 'output/experiments/grip4_calibrated_stress'
                     / 'grip4_calib_summary.csv').set_index('iso3')
    ac = pd.read_csv(ROOT / 'output/experiments/mapwithai_calibrated_stress'
                     / 'mapwithai_calib_summary.csv').set_index('iso3')
    tab = tab.join(gc[['f_calib', 'calib_loss_pp', 'random_loss_pp', 'excess_pp']]
                   .rename(columns={'f_calib': 'grip_f', 'calib_loss_pp': 'grip_loss_pp',
                                    'random_loss_pp': 'grip_random_pp',
                                    'excess_pp': 'grip_excess_pp'}))
    tab = tab.join(ac[['f_ai', 'ai_loss_pp', 'random_loss_pp', 'excess_pp']]
                   .rename(columns={'f_ai': 'ai_f', 'ai_loss_pp': 'ai_loss_pp',
                                    'random_loss_pp': 'ai_random_pp',
                                    'excess_pp': 'ai_excess_pp'}))

    tab = tab.round(4)
    tab.to_csv(OUT / 'three_way_crosscheck_summary.csv', index_label='iso3',
               encoding='utf-8-sig')

    lines: list[str] = []
    def say(t=''):
        print(t)
        lines.append(t)

    say('=== Three-way road-inventory cross-check (10 countries) ===')
    cols = ['model_density_km_km2', 'grip4_density_km_km2', 'ai_density_km_km2',
            'ai_km_per_local_km', 'f_grip4', 'f_ai', 'ai_rural_share',
            'grip_loss_pp', 'ai_loss_pp', 'grip_excess_pp', 'ai_excess_pp']
    say(tab[cols].to_string())
    say()
    say('Spearman (n=%d):' % len(tab.dropna(subset=['f_grip4', 'f_ai'])))
    for a, b in [('f_grip4', 'f_ai'), ('grip_loss_pp', 'ai_loss_pp'),
                 ('grip_excess_pp', 'ai_excess_pp'),
                 ('grip4_density_km_km2', 'ai_density_km_km2'),
                 ('ai_km_per_local_km', 'grip4_density_km_km2')]:
        sub = tab.dropna(subset=[a, b])
        if len(sub) >= 3:
            say(f'  corr({a}, {b}) = {sub[a].corr(sub[b], method="spearman"):+.3f}')
    say()
    say(f'mean f_grip4 = {tab.f_grip4.mean():.2f}; mean f_ai = {tab.f_ai.mean():.2f}')
    say(f'mean grip_loss = {tab.grip_loss_pp.mean():.1f} pp; mean ai_loss = {tab.ai_loss_pp.mean():.1f} pp')
    say(f'mean grip_excess = {tab.grip_excess_pp.mean():+.1f} pp; mean ai_excess = {tab.ai_excess_pp.mean():+.1f} pp')
    say(f'mean AI rural share = {tab.ai_rural_share.mean():.3f}')
    (OUT / 'three_way_crosscheck_report.txt').write_text('\n'.join(lines), encoding='utf-8')
    print(f'\nwrote {OUT}')


if __name__ == '__main__':
    main()
