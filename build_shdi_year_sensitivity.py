# -*- coding: utf-8 -*-
"""Vintage robustness: does the subnational development gradient depend on the
SHDI year?  The local GDL panel covers 1990-2023, so the 2020 choice used in the
manuscript can be tested against 2021-2023.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
REG = ROOT / 'output/experiments/shdi_30countries/shdi_access_regions_30countries.csv'
PANEL = ROOT / 'data/external/socioeconomic/gdl/shdi_30countries_long.csv'
OUT = ROOT / 'output/experiments/shdi_year_sensitivity'


def weighted_pearson(x, y, w):
    ok = np.isfinite(x) & np.isfinite(y) & np.isfinite(w) & (w > 0)
    if ok.sum() < 4:
        return np.nan
    x, y, w = x[ok], y[ok], w[ok]
    mx = np.average(x, weights=w)
    my = np.average(y, weights=w)
    cov = np.average((x - mx) * (y - my), weights=w)
    vx = np.average((x - mx) ** 2, weights=w)
    vy = np.average((y - my) ** 2, weights=w)
    if vx <= 0 or vy <= 0:
        return np.nan
    return float(cov / np.sqrt(vx * vy))


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    reg = pd.read_csv(REG)
    panel = pd.read_csv(PANEL)
    rows = []
    for year in sorted(panel.year.unique()):
        if year < 2018:
            continue
        s = panel[panel.year == year][['gdlcode', 'shdi']]
        m = reg.merge(s, on='gdlcode', how='inner')
        if m.empty:
            continue
        for iso3, g in m.groupby('iso3'):
            for svc, col in (('health', 'pop60_health'), ('education', 'pop60_education')):
                # match run_shdi_30countries.py: correlate the within-region SHARE
                share = (100 * g[col] / g.population.replace(0, np.nan)).to_numpy(float)
                r = weighted_pearson(g.shdi.to_numpy(float), share,
                                     g.population.to_numpy(float))
                rows.append({'year': year, 'iso3': iso3, 'service': svc, 'rho': r,
                             'regions': int(g.shape[0])})
    df = pd.DataFrame(rows)
    df.to_csv(OUT / 'shdi_year_correlations.csv', index=False, encoding='utf-8-sig')
    piv = df.pivot_table(index=['iso3', 'service'], columns='year', values='rho')
    lines = []
    lines.append('weighted SHDI-access correlation by year:')
    lines.append(piv.describe().round(3).to_string())
    lines.append('')
    base, last = 2020, int(piv.columns.max())
    pair = piv[[base, last]].dropna()
    lines.append(f'per country-service: n={len(pair)}, correlation between the '
                 f'{base} and {last} values = {pair[base].corr(pair[last]):.3f}')
    lines.append(f'mean absolute change {base}->{last} = '
                 f'{(pair[last] - pair[base]).abs().mean():.3f}; '
                 f'max = {(pair[last] - pair[base]).abs().max():.3f}')
    for y in piv.columns:
        neg = int((piv[y] < 0).sum())
        lines.append(f'  {y}: mean {piv[y].mean():+.3f}, '
                     f'min {piv[y].min():+.3f}, max {piv[y].max():+.3f}, negative rows {neg}/'
                     f'{int(piv[y].notna().sum())}')
    (OUT / 'summary.txt').write_text('\n'.join(lines), encoding='utf-8')
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
