# -*- coding: utf-8 -*-
"""Review item R4/S1: report measurement-convention effects as distributions with
country-level bootstrap confidence intervals instead of single maxima."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
EXP = ROOT / 'output/experiments'
OUT = EXP / 'effect_distributions'
SEED = 20261002
NBOOT = 5000


def boot_ci(values, rng):
    v = np.asarray(values, float)
    v = v[np.isfinite(v)]
    if len(v) < 3:
        return np.nan, np.nan
    draws = [v[rng.integers(0, len(v), len(v))].mean() for _ in range(NBOOT)]
    return float(np.percentile(draws, 2.5)), float(np.percentile(draws, 97.5))


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(SEED)

    fac = pd.read_csv(EXP / 'facility_scenarios/facility_scenario_shares.csv')
    hh = fac[fac.service == 'health'].pivot_table(index='iso3', columns='scenario',
                                                  values='share_60min_pct')
    reg = pd.read_csv(EXP / 'facility_registry/facility_registry_bottleneck.csv')
    reg['gain'] = reg.share_60min_union_counts - reg.share_60min_osm_counts
    env = pd.read_csv(EXP / 'uncertainty/uncertainty_envelope_60min.csv')
    core = pd.read_csv(EXP / 'core_recheck/core_weight_length_sensitivity.csv')
    add = pd.read_csv(EXP / 'experiment_29_global_expansion/weight_length_sensitivity.csv')
    wl = pd.concat([core, add], ignore_index=True).pivot_table(
        index=['iso3', 'service'], columns='variant',
        values=['share_30min_pct', 'share_60min_pct']).reset_index()
    wl.columns = [f'{a}_{b}' for a, b in wl.columns]
    wl = wl.rename(columns={'iso3_': 'iso3', 'service_': 'service'})
    no_unp = (wl['share_60min_pct_counts_geodesic_no_unpaved']
              - wl['share_60min_pct_counts_geodesic_none'])
    len60 = (wl['share_60min_pct_density_geodesic_none']
             - wl['share_60min_pct_density_mercator_none'])
    len30 = (wl['share_30min_pct_density_geodesic_none']
             - wl['share_30min_pct_density_mercator_none'])

    series = {
        '仅医院相对医院+诊所（pp，损失为正）': hh.hospital_clinic - hh.hospital_only,
        '全部已测绘卫生点相对医院+诊所（pp）': hh.all_health_points - hh.hospital_clinic,
        '独立登记册增益（pp）': reg.gain,
        '未铺装全部失效的损失（pp，损失为正）': -no_unp,
        '长度度量效应（60 min，pp）': len60,
        '长度度量效应（30 min，pp）': len30,
        '人口单位效应（pp）': env.pop_effect_pp,
        '设施来源效应（pp）': env.facility_effect_pp,
        '合成不确定性包络宽度（pp）': env.envelope_width_pp,
    }
    rows = []
    for label, s in series.items():
        s = s.dropna()
        lo, hi = boot_ci(s, rng)
        rows.append({'effect': label, 'n': int(len(s)), 'mean': float(s.mean()),
                     'ci_lo': lo, 'ci_hi': hi, 'median': float(s.median()),
                     'min': float(s.min()), 'max': float(s.max()),
                     'n_negative': int((s < 0).sum())})
    df = pd.DataFrame(rows)
    df.to_csv(OUT / 'effect_distributions.csv', index=False, encoding='utf-8-sig')
    print(df.round(2).to_string(index=False))

    # rank-comparison: does a country's position depend on which product is used?
    inter = pd.read_csv(EXP / 'interstudy_comparison/interstudy_60min_comparison.csv')
    cols = ['weiss_2015_cities', 'map_2020_health', 'this_corrected']
    inter['multi_product_mean'] = inter[cols].mean(axis=1)
    for c in cols + ['this_arterial_only']:
        inter[f'rank_{c}'] = inter[c].rank(ascending=False)
    inter['rank_this'] = inter['this_corrected'].rank(ascending=False)
    inter['rank_mean3'] = inter['multi_product_mean'].rank(ascending=False)
    inter['rank_shift'] = (inter.rank_this - inter.rank_mean3).abs()
    out = inter[['iso3', 'this_corrected', 'multi_product_mean', 'rank_this',
                 'rank_mean3', 'rank_shift']].sort_values('rank_shift', ascending=False)
    out.to_csv(OUT / 'rank_comparison.csv', index=False, encoding='utf-8-sig')
    rho = inter.this_corrected.corr(inter.multi_product_mean, method='spearman')
    print(f'\nrank comparison: Spearman(this model, 3-product mean) = {rho:.3f}; '
          f'median |rank shift| = {out.rank_shift.median():.1f}; '
          f'max = {out.rank_shift.max():.0f} (n={len(out)})')
    print(out.head(8).round(2).to_string(index=False))


if __name__ == '__main__':
    main()
