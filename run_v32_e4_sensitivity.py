# -*- coding: utf-8 -*-
"""v32 实验 E4 敏感性：外部靶子的离群国/杠杆稳健性。

回答：外部靶子的核心读数（MAP 2020 - 本文主干基线的高 R²、可迁移 LOCO、
3 国符号反转）是否由单一极端国家（尤其 PNG）驱动。

数据与 run_v31_e4_external_target.py 相同：
  output/experiments/interstudy_comparison/interstudy_60min_comparison.csv
  output/experiments/direction_law_v2/nested_decomposition.csv

输出：
  output/experiments/v31/e4_external_target_sensitivity.json
  output/experiments/v31/e4_external_target_sensitivity.csv
"""
import json
import os

import numpy as np
import pandas as pd
from statsmodels.regression.linear_model import OLS
from statsmodels.tools import add_constant

B = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(B, 'output/experiments/interstudy_comparison',
                   'interstudy_60min_comparison.csv')
DECOMP = os.path.join(B, 'output/experiments/direction_law_v2',
                      'nested_decomposition.csv')
OUT = os.path.join(B, 'output/experiments/v31')
os.makedirs(OUT, exist_ok=True)

SEED = 20261007
NB = 2000
PAIR = ('MAP2020 - 本文主干基线', 'map_2020_health', 'this_arterial_only')


def fit(x, y):
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    r = OLS(y, add_constant(x)).fit()
    influence = r.get_influence()
    cooks = influence.cooks_distance[0]
    lev = influence.hat_matrix_diag
    return dict(slope=float(r.params[1]), t=float(r.tvalues[1]),
                r2=float(r.rsquared), n=len(x),
                cooks=float(cooks.max()), cooks_idx=int(cooks.argmax()),
                lev=float(lev.max()), lev_idx=int(lev.argmax()))


def loco(x, y):
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    oof = np.full(len(y), np.nan)
    for i in range(len(y)):
        te = np.zeros(len(y), bool)
        te[i] = True
        tr = ~te
        beta = np.linalg.lstsq(
            np.column_stack([np.ones(tr.sum()), x[tr]]), y[tr], rcond=None)[0]
        oof[te] = np.column_stack([np.ones(te.sum()), x[te]]) @ beta
    m = ~np.isnan(oof)
    ss_res = float(((y[m] - oof[m]) ** 2).sum())
    ss_tot = float(((y[m] - y[m].mean()) ** 2).sum())
    return dict(oof_r2=1 - ss_res / ss_tot,
                mae=float(np.abs(y[m] - oof[m]).mean()),
                dir_acc=float((np.sign(y[m]) == np.sign(oof[m])).mean() * 100))


def bootstrap_r2(x, y, rng, nboot=NB):
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    vals = []
    for _ in range(nboot):
        idx = rng.integers(0, len(y), len(y))
        if len(np.unique(x[idx])) < 2:
            continue
        beta = np.linalg.lstsq(
            np.column_stack([np.ones(len(idx)), x[idx]]), y[idx], rcond=None)[0]
        pred = np.column_stack([np.ones(len(idx)), x[idx]]) @ beta
        ss_res = float(((y[idx] - pred) ** 2).sum())
        ss_tot = float(((y[idx] - y[idx].mean()) ** 2).sum())
        if ss_tot > 0:
            vals.append(1 - ss_res / ss_tot)
    vals = np.asarray(vals)
    return dict(mean=float(vals.mean()), lo=float(np.percentile(vals, 2.5)),
                hi=float(np.percentile(vals, 97.5)))


def load():
    D = pd.read_csv(SRC, encoding='utf-8-sig')
    N = pd.read_csv(DECOMP, encoding='utf-8-sig')[
        ['iso3', 'service', 'arterial_coverage']]
    N = N[N['service'] == 'health'][['iso3', 'arterial_coverage']]
    D = D.merge(N, on='iso3', how='left')
    assert len(D) == 30
    return D


def main():
    D = load()
    label, a_col, b_col = PAIR
    x = D['arterial_coverage'].to_numpy(float)
    delta = D[a_col].to_numpy(float) - D[b_col].to_numpy(float)
    iso = D['iso3'].to_numpy()

    full_fit = fit(x, delta)
    full_loco = loco(x, delta)
    full_nneg = int((delta < 0).sum())
    rng = np.random.default_rng(SEED)
    full_boot = bootstrap_r2(x, delta, rng)

    rows = []
    for exclude in ['NONE'] + list(iso):
        if exclude == 'NONE':
            mask = np.ones(len(x), bool)
        else:
            mask = iso != exclude
        f = fit(x[mask], delta[mask])
        l = loco(x[mask], delta[mask])
        nneg = int((delta[mask] < 0).sum())
        rows.append(dict(exclude_iso3=exclude, n=len(delta[mask]),
                         r2=round(f['r2'], 4), loco_r2=round(l['oof_r2'], 4),
                         dir_acc=round(l['dir_acc'], 2), n_negative=nneg,
                         slope=round(f['slope'], 4), t=round(f['t'], 3)))

    loo = pd.DataFrame(rows)
    png_row = loo[loo['exclude_iso3'] == 'PNG'].iloc[0]
    nneg_excl_png = int(png_row['n_negative'])
    neg_countries = sorted(iso[delta < 0].tolist())

    res = {
        'pair': label,
        'full': {
            'n': int(full_fit['n']), 'r2': round(full_fit['r2'], 4),
            'loco_r2': round(full_loco['oof_r2'], 4),
            'dir_acc': round(full_loco['dir_acc'], 2),
            'n_negative': full_nneg,
            'negative_countries': neg_countries,
            'max_cooks_distance': round(full_fit['cooks'], 4),
            'max_cooks_country': str(iso[full_fit['cooks_idx']]),
            'max_leverage': round(full_fit['lev'], 4),
            'max_leverage_country': str(iso[full_fit['lev_idx']]),
            'bootstrap_r2_95ci': full_boot,
        },
        'exclude_png': {
            'r2': round(png_row['r2'], 4),
            'loco_r2': round(png_row['loco_r2'], 4),
            'dir_acc': round(png_row['dir_acc'], 2),
            'n_negative': nneg_excl_png,
        },
        'leave_one_out': loo.to_dict(orient='records'),
    }

    loo.to_csv(os.path.join(OUT, 'e4_external_target_sensitivity.csv'),
               index=False, encoding='utf-8-sig')
    json.dump(res, open(os.path.join(OUT, 'e4_external_target_sensitivity.json'),
                        'w'), indent=2, ensure_ascii=False)

    print('MAP2020 - 本文主干基线（外部靶子）敏感性')
    print('  full: R2=%.3f LOCO=%.3f dir_acc=%.1f%% n_neg=%d/30'
          % (full_fit['r2'], full_loco['oof_r2'], full_loco['dir_acc'],
             full_nneg))
    print('  negative countries:', neg_countries)
    print('  max cooks: %.3f (%s)  max leverage: %.3f (%s)'
          % (full_fit['cooks'], iso[full_fit['cooks_idx']],
             full_fit['lev'], iso[full_fit['lev_idx']]))
    print('  bootstrap R2 95%% CI: %.3f - %.3f'
          % (full_boot['lo'], full_boot['hi']))
    print('  exclude PNG: R2=%.3f LOCO=%.3f dir_acc=%.1f%% n_neg=%d/29'
          % (png_row['r2'], png_row['loco_r2'], png_row['dir_acc'],
             nneg_excl_png))
    print('  已写出 e4_external_target_sensitivity.csv/json')


if __name__ == '__main__':
    main()
