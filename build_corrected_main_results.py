# -*- coding: utf-8 -*-
"""P0.1: consolidated main results under the corrected measurement conventions.

For all 30 sample countries and both services this table reports

* the arterial-only 60-minute access (the current reference baseline),
* the published corrected/noded 60-minute access (density weights + EPSG:3857 lengths),
* the convention-corrected access (area-weighted population counts + WGS84 geodesic
  lengths), its change, and the corrected absolute population,
* the two scenario stress tests (no unpaved, unknown-as-unpaved),
* the urban/rural gap where available.

Outputs ``output/experiments/corrected_main/corrected_main_access_30countries.csv``
and ``corrected_main_access_summary.txt``.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
EXP = ROOT / 'output/experiments/experiment_29_global_expansion'
OUT_DIR = ROOT / 'output/experiments/corrected_main'
CORE = ['PAK', 'MOZ', 'BGD', 'ETH', 'KEN', 'COL', 'PHL']


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    sample = pd.read_csv(EXP / 'country_sample_and_input_availability.csv')
    core_sens = pd.read_csv(ROOT / 'output/experiments/core_recheck/core_weight_length_sensitivity.csv')
    add_sens = pd.read_csv(EXP / 'weight_length_sensitivity.csv')
    sens = pd.concat([core_sens, add_sens], ignore_index=True)
    core_art = pd.read_csv(ROOT / 'output/experiments/experiment_24_network_integrity'
                           / 'all_countries_noded_vs_arterial_60min.csv')
    core_art = core_art[core_art.scenario == 'baseline'].copy()
    core_art['service'] = core_art.service.replace({'school': 'education'})
    core_art = core_art[['iso3', 'service', 'arterial_60min_pct', 'noded_60min_pct']]
    core_art['group'] = 'core'
    add_art = pd.read_csv(EXP / 'corrected_countries/arterial_vs_corrected_expansion.csv')
    add_art = add_art[['iso3', 'service', 'arterial_60min_pct', 'corrected_60min_pct',
                       'noded_segments']].rename(columns={'corrected_60min_pct': 'noded_60min_pct'})
    add_art['group'] = 'addition'
    art = pd.concat([core_art.assign(noded_segments=np.nan), add_art], ignore_index=True)

    def variant(name, column):
        return (sens[sens.variant == name][['iso3', 'service', column]]
                .rename(columns={column: f'{column}_{name}'}))

    table = art.merge(variant('density_mercator_none', 'share_60min_pct'), on=['iso3', 'service'])
    table = table.merge(variant('counts_geodesic_none', 'share_60min_pct'), on=['iso3', 'service'])
    table = table.merge(variant('density_mercator_none', 'share_30min_pct'), on=['iso3', 'service'])
    table = table.merge(variant('counts_geodesic_none', 'share_30min_pct'), on=['iso3', 'service'])
    table = table.merge(variant('counts_geodesic_none', 'population_total_millions'),
                        on=['iso3', 'service'])
    table = table.merge(variant('density_mercator_none', 'population_total_millions'),
                        on=['iso3', 'service'])
    table = table.merge(variant('counts_geodesic_no_unpaved', 'share_60min_pct'), on=['iso3', 'service'])
    table = table.merge(variant('counts_geodesic_unknown_as_unpaved', 'share_60min_pct'),
                        on=['iso3', 'service'])
    table['convention_delta_60min_pp'] = (table.share_60min_pct_counts_geodesic_none
                                          - table.share_60min_pct_density_mercator_none)
    table['convention_delta_30min_pp'] = (table.share_30min_pct_counts_geodesic_none
                                          - table.share_30min_pct_density_mercator_none)
    table['population_change_pct'] = 100 * (
        table.population_total_millions_counts_geodesic_none
        / table.population_total_millions_density_mercator_none - 1)
    table['no_unpaved_loss_60min_pp'] = (table.share_60min_pct_counts_geodesic_none
                                         - table.share_60min_pct_counts_geodesic_no_unpaved)
    table['unknown_as_unpaved_loss_60min_pp'] = (
        table.share_60min_pct_counts_geodesic_none
        - table.share_60min_pct_counts_geodesic_unknown_as_unpaved)
    table = table.merge(sample[['iso3', 'country', 'region', 'income_group', 'hazard_profile']],
                        on='iso3', how='left')
    ur = pd.read_csv(EXP / 'urban_rural_expansion.csv')
    wide = ur.pivot_table(index=['iso3', 'service'], columns='group',
                          values=['share_60min_pct', 'population_millions'])
    wide.columns = [f'{a}_{b}' for a, b in wide.columns]
    wide = wide.reset_index()
    wide['urban_rural_gap_60min_pp'] = wide.share_60min_pct_urban - wide.share_60min_pct_rural
    table = table.merge(wide[['iso3', 'service', 'urban_rural_gap_60min_pp',
                              'population_millions_urban', 'population_millions_rural']],
                        on=['iso3', 'service'], how='left')
    haz = pd.read_csv(EXP / 'expansion_hazard_pilot.csv')
    if len(haz):
        h = haz[haz.variant == 'baseline'].groupby(['iso3', 'service']).agg(
            hazard_events=('event_id', 'nunique'),
            worst_event_area_km2=('hazard_area_km2', 'max')).reset_index()
        ws = haz.pivot_table(index=['iso3', 'service'], columns='variant',
                             values='share_60min_pct').reset_index()
        if {'baseline', 'hazard'}.issubset(ws.columns):
            ws['worst_event_loss_60min_pp'] = ws['baseline'] - ws['hazard']
            h = h.merge(ws[['iso3', 'service', 'worst_event_loss_60min_pp']], on=['iso3', 'service'])
        # keep the largest event per country-service
        worst = haz.pivot_table(index=['iso3', 'service', 'event_id'], columns='variant',
                                values='share_60min_pct').reset_index()
        if {'baseline', 'hazard'}.issubset(worst.columns):
            worst['loss'] = worst['baseline'] - worst['hazard']
            worst = worst.sort_values('loss', ascending=False).drop_duplicates(['iso3', 'service'])
            h = h.merge(worst[['iso3', 'service', 'event_id', 'loss']]
                        .rename(columns={'event_id': 'worst_event_id', 'loss': 'worst_event_loss_60min_pp'}),
                        on=['iso3', 'service'], how='left')
        table = table.merge(h.drop(columns=['worst_event_loss_60min_pp'], errors='ignore'),
                            on=['iso3', 'service'], how='left')
    table = table.sort_values(['group', 'convention_delta_60min_pp'], ascending=[True, False])
    cols = ['iso3', 'country', 'group', 'region', 'income_group', 'service',
            'arterial_60min_pct', 'noded_60min_pct', 'share_60min_pct_density_mercator_none',
            'share_60min_pct_counts_geodesic_none', 'convention_delta_60min_pp',
            'share_30min_pct_density_mercator_none', 'share_30min_pct_counts_geodesic_none',
            'convention_delta_30min_pp', 'population_total_millions_density_mercator_none',
            'population_total_millions_counts_geodesic_none', 'population_change_pct',
            'no_unpaved_loss_60min_pp', 'unknown_as_unpaved_loss_60min_pp',
            'urban_rural_gap_60min_pp', 'hazard_events', 'worst_event_id',
            'worst_event_loss_60min_pp', 'noded_segments']
    table = table.reindex(columns=cols)
    table.to_csv(OUT_DIR / 'corrected_main_access_30countries.csv', index=False, encoding='utf-8-sig')
    pd.set_option('display.width', 250)
    pd.set_option('display.max_rows', 80)
    print(f'wrote {OUT_DIR / "corrected_main_access_30countries.csv"} ({len(table)} rows)')
    print()
    print(table[['iso3', 'group', 'service', 'arterial_60min_pct', 'noded_60min_pct',
                 'share_60min_pct_counts_geodesic_none', 'convention_delta_60min_pp',
                 'convention_delta_30min_pp', 'population_change_pct',
                 'no_unpaved_loss_60min_pp', 'urban_rural_gap_60min_pp']]
          .round(2).to_string(index=False))
    with (OUT_DIR / 'corrected_main_access_summary.txt').open('w', encoding='utf-8') as f:
        f.write(table.round(4).to_string(index=False))


if __name__ == '__main__':
    main()
