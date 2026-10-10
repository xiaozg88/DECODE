# -*- coding: utf-8 -*-
"""P0.4: uncertainty envelope for the 60-minute access shares.

Decomposes the envelope into the three effects that the audit and the P0.3 work
quantified:

* population weighting: density (canonical) vs area-weighted counts,
* segment length: EPSG:3857 (canonical) vs WGS84 geodesic,
* facilities: OSM/HOT only (canonical) vs OSM + independent registry.

Outputs ``output/experiments/uncertainty/uncertainty_envelope_60min.csv``.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
EXP = ROOT / 'output/experiments/experiment_29_global_expansion'
OUT_DIR = ROOT / 'output/experiments/uncertainty'


def variants() -> pd.DataFrame:
    core = pd.read_csv(ROOT / 'output/experiments/core_recheck/core_weight_length_sensitivity.csv')
    add = pd.read_csv(EXP / 'weight_length_sensitivity.csv')
    d = pd.concat([core, add], ignore_index=True)
    wide = d.pivot_table(index=['iso3', 'service'], columns='variant', values='share_60min_pct').reset_index()
    wide['pop_effect_pp'] = wide.counts_mercator_none - wide.density_mercator_none
    wide['length_effect_pp'] = wide.density_geodesic_none - wide.density_mercator_none
    wide['canonical_share_60min_pct'] = wide.density_mercator_none
    return wide


def facility_effect() -> pd.DataFrame:
    rows = []
    reg = ROOT / 'output/experiments/facility_registry/facility_registry_bottleneck.csv'
    if reg.exists():
        d = pd.read_csv(reg)
        for _, r in d.iterrows():
            rows.append({'iso3': r.iso3, 'service': r.service,
                         'facility_effect_pp': r.registry_gain_60min_pp,
                         'facility_case': 'independent_registry'})
    legacy = pd.read_csv(ROOT / 'output/paper_ready_main_access.csv')
    legacy = legacy[legacy.scenario == 'baseline']
    piv = legacy.pivot_table(index=['iso3', 'service'], columns='facility_variant',
                             values='share_60min_pct')
    if {'osm', 'registry_union'}.issubset(piv.columns):
        for (iso, service), r in piv.iterrows():
            rows.append({'iso3': iso, 'service': service,
                         'facility_effect_pp': r.registry_union - r.osm,
                         'facility_case': 'legacy_registry'})
    out = pd.DataFrame(rows)
    if len(out):
        out = out.sort_values('facility_effect_pp', ascending=False).drop_duplicates(
            ['iso3', 'service'], keep='first')
    return out


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    v = variants()
    f = facility_effect()
    table = v.merge(f, on=['iso3', 'service'], how='left')
    table['facility_effect_pp'] = table.facility_effect_pp.fillna(0.0)
    table['low_share_60min_pct'] = (table.canonical_share_60min_pct
                                    + table[['pop_effect_pp', 'length_effect_pp',
                                             'facility_effect_pp']].min(axis=1))
    table['high_share_60min_pct'] = (table.canonical_share_60min_pct
                                     + table[['pop_effect_pp', 'length_effect_pp',
                                              'facility_effect_pp']].max(axis=1))
    table['envelope_width_pp'] = table.high_share_60min_pct - table.low_share_60min_pct
    table = table.sort_values('envelope_width_pp', ascending=False)
    cols = ['iso3', 'service', 'canonical_share_60min_pct', 'pop_effect_pp', 'length_effect_pp',
            'facility_effect_pp', 'facility_case', 'low_share_60min_pct', 'high_share_60min_pct',
            'envelope_width_pp']
    table = table.reindex(columns=cols)
    table.to_csv(OUT_DIR / 'uncertainty_envelope_60min.csv', index=False, encoding='utf-8-sig')
    pd.set_option('display.width', 250)
    pd.set_option('display.max_rows', 80)
    print(f'wrote {OUT_DIR / "uncertainty_envelope_60min.csv"} ({len(table)} rows)')
    print(table.round(2).to_string(index=False))
    print()
    print('mean |pop effect| = %.3f pp; mean |length effect| = %.3f pp; '
          'mean |facility effect| = %.3f pp' % (table.pop_effect_pp.abs().mean(),
                                                table.length_effect_pp.abs().mean(),
                                                table.facility_effect_pp.abs().mean()))
    with (OUT_DIR / 'uncertainty_summary.txt').open('w', encoding='utf-8') as fh:
        fh.write(table.round(4).to_string(index=False))


if __name__ == '__main__':
    main()
