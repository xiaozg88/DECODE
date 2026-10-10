# -*- coding: utf-8 -*-
"""Review items R1/R2/R4/R5: rebuild the correction "direction law" on a defensible
footing.

Inputs
------
* output/experiments/nested_counterfactual/{iso}_nested_counterfactual.csv
  (scenarios A_arterial_nested, B_shared, B_full, B_full_speed115/130)
* output/experiments/corrected_main/corrected_main_access_30countries.csv
* output/experiments/grip4_completeness/grip4_vs_network_density.csv

Outputs
-------
* nested_decomposition.csv         per country/service decomposition of delta_pp
* direction_law_variants.csv       the law under each predictor/outcome definition
* direction_law_permutation.csv    permutation null for the published form
* summary.txt                      human-readable digest
"""
from __future__ import annotations

import glob
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.regression.linear_model import OLS
from statsmodels.regression.mixed_linear_model import MixedLM
from statsmodels.tools import add_constant

ROOT = Path(__file__).resolve().parent
NEST = ROOT / 'output/experiments/nested_counterfactual'
OUT = ROOT / 'output/experiments/direction_law_v2'
SEED = 20261002
NPERM = 2000
NBOOT = 2000


def load_nested():
    frames = [pd.read_csv(f) for f in sorted(glob.glob(str(NEST / '*_nested_counterfactual.csv')))]
    d = pd.concat(frames, ignore_index=True)
    wide = d.pivot_table(index=['iso3', 'service'], columns='scenario',
                         values=['share_30min_pct', 'share_60min_pct',
                                 'share_120min_pct', 'source_nodes']).reset_index()
    wide.columns = [f'{a}_{b}' for a, b in wide.columns]
    wide = wide.rename(columns={'iso3_': 'iso3', 'service_': 'service'})
    # the nested runner labels the education service 'school'; the canonical
    # tables use 'education'
    wide['service'] = wide['service'].replace({'school': 'education'})
    return wide


def law(x, y, label, rng=None, boot=True):
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    ok = np.isfinite(x) & np.isfinite(y)
    x, y = x[ok], y[ok]
    fit = OLS(y, add_constant(x)).fit()
    slope = float(fit.params[1])
    intercept = float(fit.params[0])
    res = {
        'variant': label, 'n': int(len(x)), 'slope': slope, 'intercept': intercept,
        'pearson': float(np.corrcoef(x, y)[0, 1]),
        'spearman': float(stats.spearmanr(x, y).statistic),
        'r2': float(fit.rsquared), 'p_slope': float(fit.pvalues[1]),
        'break_even_x': float(-intercept / slope) if slope != 0 else float('nan'),
    }
    if boot and rng is not None and len(x) > 5:
        slopes, breaks = [], []
        for _ in range(NBOOT):
            idx = rng.integers(0, len(x), len(x))
            if len(np.unique(x[idx])) < 2:
                continue
            b, a = np.polyfit(x[idx], y[idx], 1)
            slopes.append(b)
            if b != 0:
                breaks.append(-a / b)
        slopes = np.asarray(slopes)
        res['slope_ci_lo'] = float(np.percentile(slopes, 2.5))
        res['slope_ci_hi'] = float(np.percentile(slopes, 97.5))
        if breaks:
            res['break_even_ci_lo'] = float(np.percentile(breaks, 2.5))
            res['break_even_ci_hi'] = float(np.percentile(breaks, 97.5))
    return res


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(SEED)
    n = load_nested()
    main_tbl = pd.read_csv(ROOT / 'output/experiments/corrected_main/'
                                 'corrected_main_access_30countries.csv')
    grip = pd.read_csv(ROOT / 'output/experiments/grip4_completeness/'
                              'grip4_vs_network_density.csv')
    grip = grip[['iso3', 'planet_km', 'local_km', 'local_share_pct',
                 'road_density_km_per_km2']].copy()
    grip['arterial_length_share_pct'] = 100 - grip.local_share_pct
    df = (main_tbl.merge(n, on=['iso3', 'service'], how='inner')
          .merge(grip, on='iso3', how='left'))
    df['arterial_coverage'] = df.arterial_60min_pct
    df['corrected_published'] = df.share_60min_pct_counts_geodesic_none
    df['delta_published'] = df.corrected_published - df.arterial_coverage
    df['delta_edges'] = df.share_60min_pct_B_shared - df.share_60min_pct_A_arterial_nested
    df['delta_snapping'] = df.share_60min_pct_B_full - df.share_60min_pct_B_shared
    df['delta_residual'] = df.delta_published - df.delta_edges - df.delta_snapping
    df['reproduction_gap'] = df.share_60min_pct_B_full - df.noded_60min_pct
    # --- R 的构成项（v30 新增）：让残差分解在派生表中即可逐行核验 ---
    # legacy_baseline: 已发布实现所用的主干-only 基线（= corrected_published - delta_published）
    df['legacy_baseline'] = df.corrected_published - df.delta_published
    # baseline_diff: 两个"仅主干路"基线之差（嵌套反事实 − 已发布实现）
    df['baseline_diff'] = (df.share_60min_pct_A_arterial_nested
                           - df.legacy_baseline)
    # protocol_gap: 进入 R 恒等式的口径项（已发布全路值 − 重实现全路值）。
    # 它非零是因为两套口径的人口单位与长度度量不同，正是本文主题在自身管线内的体现。
    df['protocol_gap'] = df.corrected_published - df.share_60min_pct_B_full
    keep = ['iso3', 'country', 'service', 'arterial_coverage', 'corrected_published',
            'noded_60min_pct', 'share_60min_pct_A_arterial_nested',
            'share_60min_pct_B_shared', 'share_60min_pct_B_full',
            'share_60min_pct_B_full_speed115', 'share_60min_pct_B_full_speed130',
            'delta_published', 'delta_edges', 'delta_snapping', 'delta_residual',
            'legacy_baseline', 'baseline_diff', 'protocol_gap', 'reproduction_gap',
            'arterial_length_share_pct', 'road_density_km_per_km2']
    df[keep].to_csv(OUT / 'nested_decomposition.csv', index=False, encoding='utf-8-sig')

    lines = []
    lines.append('=== 1. reproduction check (nested B_full vs published corrected) ===')
    lines.append(f'n={len(df)}  mean gap={df.reproduction_gap.mean():+.3f} pp  '
                 f'max |gap|={df.reproduction_gap.abs().max():.3f} pp')
    lines.append('')
    lines.append('=== 2. decomposition of the published delta (pp) ===')
    lines.append(df[['delta_published', 'delta_edges', 'delta_snapping',
                     'delta_residual']].describe().round(2).to_string())
    lines.append(f'delta_edges < 0 in {int((df.delta_edges < 0).sum())} of {len(df)} rows')
    lines.append('')

    # --- R 的构成项（v30）---
    lines.append('=== 2b. residual decomposition: R = baseline_diff + protocol_gap ===')
    lines.append(f'legacy_baseline  (published arterial-only) : min {df.legacy_baseline.min():.2f} '
                 f'median {df.legacy_baseline.median():.2f} mean {df.legacy_baseline.mean():.2f} '
                 f'max {df.legacy_baseline.max():.2f}')
    lines.append(f'nested_baseline  (A_arterial_nested)   : min {df.share_60min_pct_A_arterial_nested.min():.2f} '
                 f'median {df.share_60min_pct_A_arterial_nested.median():.2f} '
                 f'mean {df.share_60min_pct_A_arterial_nested.mean():.2f} '
                 f'max {df.share_60min_pct_A_arterial_nested.max():.2f}')
    lines.append(f'baseline_diff    (nested - legacy)    : min {df.baseline_diff.min():+.2f} '
                 f'median {df.baseline_diff.median():+.2f} mean {df.baseline_diff.mean():+.2f} '
                 f'max {df.baseline_diff.max():+.2f}')
    lines.append(f'  |baseline_diff| > 10 pp : {int((df.baseline_diff.abs() > 10).sum())}/{len(df)} rows')
    lines.append(f'  |baseline_diff| > 20 pp : {int((df.baseline_diff.abs() > 20).sum())}/{len(df)} rows')
    lines.append(f'  baseline_diff > 0        : {int((df.baseline_diff > 0).sum())}/{len(df)} rows')
    lines.append(f'Pearson(baseline_diff, arterial_coverage) = '
                 f'{df.baseline_diff.corr(df.arterial_coverage):+.4f}')
    lines.append(f'protocol_gap     (published - B_full)  : min {df.protocol_gap.min():+.3f} '
                 f'median {df.protocol_gap.median():+.3f} mean {df.protocol_gap.mean():+.3f} '
                 f'max {df.protocol_gap.max():+.3f}')
    lines.append(f'  |protocol_gap| > 0.052 pp: '
                 f'{int((df.protocol_gap.abs() > 0.052).sum())}/{len(df)} rows')
    lines.append(f'reproduction_gap (B_full - noded)     : min {df.reproduction_gap.min():+.4f} '
                 f'median {df.reproduction_gap.median():+.4f} max {df.reproduction_gap.abs().max():.4f}')
    _dev = (df.delta_residual - df.baseline_diff - df.protocol_gap).abs().max()
    lines.append(f'identity check  max|R - baseline_diff - protocol_gap| = {_dev:.10f}')
    lines.append('')

    variants = [
        law(df.arterial_coverage, df.delta_published,
            'published: delta_published ~ arterial coverage', rng=rng),
        law(df.arterial_coverage, df.delta_edges,
            'nested: delta_edges ~ arterial coverage', rng=rng),
        law(df.arterial_coverage, df.delta_snapping,
            'convention: delta_snapping ~ arterial coverage', rng=rng),
        law(df.arterial_length_share_pct, df.delta_published,
            'published delta ~ geometric arterial length share', rng=rng),
        law(df.arterial_length_share_pct, df.delta_edges,
            'nested delta_edges ~ geometric arterial length share', rng=rng),
        law(df.road_density_km_per_km2, df.delta_published,
            'published delta ~ road density', rng=rng),
        law(df.arterial_coverage, df.share_60min_pct_B_full,
            'corrected ~ arterial coverage (slope<>1 test)', rng=rng),
        law(df.arterial_coverage, df.share_60min_pct_B_shared,
            'nested corrected (B_shared) ~ arterial coverage', rng=rng),
    ]
    v = pd.DataFrame(variants)
    v.to_csv(OUT / 'direction_law_variants.csv', index=False, encoding='utf-8-sig')
    lines.append('=== 3. law variants ===')
    lines.append(v.round(3).to_string(index=False))
    lines.append('')

    fit = OLS(df.share_60min_pct_B_full.to_numpy(),
              add_constant(df.arterial_coverage.to_numpy())).fit()
    t_slope1 = (fit.params[1] - 1.0) / fit.bse[1]
    p_slope1 = 2 * (1 - stats.t.cdf(abs(t_slope1), df=fit.df_resid))
    lines.append('=== 4. slope != 1 test for corrected ~ arterial coverage ===')
    lines.append(f'slope={fit.params[1]:.3f} (se {fit.bse[1]:.3f}), t={t_slope1:.2f}, '
                 f'p={p_slope1:.2e}')
    lines.append('')

    obs = law(df.arterial_coverage, df.delta_published, 'observed', boot=False)
    corr = df.share_60min_pct_B_full.to_numpy()
    art = df.arterial_coverage.to_numpy()
    perm_slope, perm_r, perm_r2 = [], [], []
    for _ in range(NPERM):
        dlt = rng.permutation(corr) - art
        perm_slope.append(np.polyfit(art, dlt, 1)[0])
        pr = float(np.corrcoef(art, dlt)[0, 1])
        perm_r.append(pr)
        perm_r2.append(pr ** 2)
    perm = pd.DataFrame({'slope': perm_slope, 'pearson': perm_r, 'r2': perm_r2})
    perm.to_csv(OUT / 'direction_law_permutation.csv', index=False, encoding='utf-8-sig')
    lines.append('=== 5. permutation null for the published difference-score form ===')
    lines.append(f"observed: slope={obs['slope']:.3f} r={obs['pearson']:.3f} r2={obs['r2']:.3f}")
    lines.append(f'null (shuffled corrected outcome): slope mean={perm.slope.mean():.3f} '
                 f'[{perm.slope.quantile(.025):.3f}, {perm.slope.quantile(.975):.3f}], '
                 f'|r| mean={perm.pearson.abs().mean():.3f}, r2 mean={perm.r2.mean():.3f} '
                 f'[{perm.r2.quantile(.025):.3f}, {perm.r2.quantile(.975):.3f}]')
    lines.append(f'observed r2 percentile inside the null = '
                 f'{(perm.r2 < obs["r2"]).mean() * 100:.1f}%')
    lines.append('')

    agg = df.groupby('iso3').agg(arterial=('arterial_coverage', 'mean'),
                                 delta_pub=('delta_published', 'mean'),
                                 delta_edges=('delta_edges', 'mean'),
                                 delta_snap=('delta_snapping', 'mean')).reset_index()
    lines.append('=== 6. country-level (n=30) re-estimation ===')
    lines.append(str(law(agg.arterial, agg.delta_pub, 'published, country means', rng=rng)))
    lines.append(str(law(agg.arterial, agg.delta_edges, 'nested delta_edges, country means',
                         rng=rng)))
    d = df.copy()
    d['grp'] = d.iso3
    try:
        mdf = d[['delta_published', 'arterial_coverage', 'grp']].dropna()
        mres = MixedLM.from_formula('delta_published ~ arterial_coverage', groups='grp',
                                    data=mdf).fit()
        lines.append('mixed model (country random intercept): '
                     f'slope={mres.params["arterial_coverage"]:.3f} '
                     f'(se {mres.bse["arterial_coverage"]:.3f}, '
                     f'p={mres.pvalues["arterial_coverage"]:.2e})')
    except Exception as exc:
        lines.append(f'mixed model failed: {type(exc).__name__} {exc}')
    lines.append('')

    lines.append('=== 7. global speed calibration (item R5) ===')
    for tag in ('B_full', 'B_full_speed115', 'B_full_speed130'):
        s = df[f'share_60min_pct_{tag}']
        lines.append(f'{tag}: mean 60-min share {s.mean():.2f}%, range {s.min():.2f}-{s.max():.2f}')
    for mult, tag in ((1.15, 'B_full_speed115'), (1.30, 'B_full_speed130')):
        delta = df[f'share_60min_pct_{tag}'] - df.share_60min_pct_A_arterial_nested
        r = law(df.arterial_coverage, delta, f'delta (speed x{mult}) ~ arterial coverage')
        lines.append(str(r))
    lines.append('')
    lines.append('=== 8. decomposition by country (largest |delta_edges|) ===')
    lines.append(df.reindex(df.delta_edges.abs().sort_values(ascending=False).index)[
        ['iso3', 'service', 'arterial_coverage', 'delta_published', 'delta_edges',
         'delta_snapping', 'delta_residual']].head(12).round(2).to_string(index=False))
    (OUT / 'summary.txt').write_text('\n'.join(lines), encoding='utf-8')
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
