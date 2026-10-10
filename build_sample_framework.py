# -*- coding: utf-8 -*-
"""Sampling-design coverage for the 30-country stratified purposive sample.

Reads the sample catalogue, the road density table and the GRIP4 reference to
document how the 30 countries span income groups, World Bank regions, hazard
profiles and the road-density gradient.  This turns the paper's "convenience
sample" into a defensible, transparent stratified-purposive sampling design.

Usage:
  python build_sample_framework.py
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
EXP = ROOT / 'output/experiments'
OUT = EXP / 'sample_framework'


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    d = pd.read_csv(EXP / 'experiment_29_global_expansion'
                    / 'country_sample_and_input_availability.csv')
    d['income_group'] = d['income_group'].astype(str).str.strip().replace(
        {'low-middle': 'lower-middle'})

    nc = pd.read_csv(EXP / 'network_completeness/network_completeness_by_country.csv')
    dens = nc.road_density_km_per_km2

    hazard_types = set()
    for h in d.hazard_profile.dropna().astype(str):
        for t in h.split('/'):
            hazard_types.add(t.strip())

    rows = []
    for g in ('low', 'lower-middle', 'upper-middle'):
        rows.append(('收入组', g, int((d.income_group == g).sum()), '世界银行 2020'))
    for r in sorted(d.region.unique()):
        rows.append(('地理区域', r, int((d.region == r).sum()), '世界银行区域'))
    rows.append(('灾害类型', '合计', len(hazard_types), ','.join(sorted(hazard_types))))
    rows.append(('路网密度', '范围 (km/km2)', f'{dens.min():.3f}–{dens.max():.3f}',
                 f'{dens.max() / dens.min():.1f}×'))
    rows.append(('路网密度', '中位数 (km/km2)', f'{dens.median():.3f}', '—'))
    rows.append(('核心 / 扩充', '7 + 23', '7 + 23',
                 '核心国为灾害高暴露且 Planet 主干路面可得'))

    df = pd.DataFrame(rows, columns=['维度', '取值', '国家数 / 数值', '备注'])
    df.to_csv(OUT / 'sample_coverage.csv', index=False, encoding='utf-8-sig')
    pd.set_option('display.width', 200)
    print(df.to_string(index=False))
    print(f'\nwrote {OUT / "sample_coverage.csv"}')


if __name__ == '__main__':
    main()
