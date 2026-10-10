# -*- coding: utf-8 -*-
"""Reviewer-requested statistics for paper v7 (operates on the already-deposited
60-row nested_decomposition table; no segment reload needed).

Produces, for the direction regression  delta_published ~ arterial_coverage:
  1. leave-one-country-out (LOCO) cross-validation  -> out-of-sample R2/MAE/sign
  2. country-clustered robust standard errors
  3. mixed model with a country random intercept
  4. Huber robust regression
  5. influence diagnostics (Cook's distance / leverage), high-leverage countries
  6. beta-response feasibility note (delta is unbounded, so no beta regression)

Usage:
  python run_review_stats_v7.py
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

import statsmodels.api as sm
from statsmodels.formula.api import mixedlm

ROOT = Path(__file__).resolve().parent
EXP = ROOT / 'output/experiments'
DEC = EXP / 'direction_law_v2/nested_decomposition.csv'
OUT = EXP / 'review_stats_v7'


def _fit_ols(y, X, cluster=None):
    Xc = sm.add_constant(X)
    m = sm.OLS(y, Xc).fit()
    out = {'slope': m.params[1], 'slope_se': m.bse[1],
           'intercept': m.params[0], 'r2': m.rsquared,
           'pearson': np.corrcoef(X, y)[0, 1], 'n': len(y)}
    if cluster is not None:
        cov = m.get_robustcov_results(cov_type='cluster', groups=cluster)
        out['slope_se_cluster'] = cov.bse[1]
        out['p_cluster'] = cov.pvalues[1]
    return m, out


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    d = pd.read_csv(DEC)
    y = d['delta_published'].to_numpy(float)
    X = d['arterial_coverage'].to_numpy(float)
    cid = d['iso3'].to_numpy()

    report = []

    # ---- 1. LOCO (leave-one-country-out) ----------------------------------
    uniq = np.unique(cid)
    preds, oos = np.empty_like(y, dtype=float), np.zeros_like(y, dtype=float)
    for c in uniq:
        te = cid == c
        tr = ~te
        b = np.polyfit(X[tr], y[tr], 1)
        preds[te] = np.polyval(b, X[te])
        oos[te] = 1
    ss_res = np.sum((y - preds) ** 2)
    ss_tot = np.sum((y - y.mean()) ** 2)
    r2_oos = 1 - ss_res / ss_tot
    mae = np.mean(np.abs(y - preds))
    sign_acc = float(np.mean(np.sign(preds) == np.sign(y)) * 100)
    report.append('=== 1. leave-one-country-out (LOCO) cross-validation ===')
    report.append(f'n={len(y)} countries={len(uniq)} '
                  f'out-of-sample R2={r2_oos:.3f} MAE={mae:.2f} pp '
                  f'sign-accuracy={sign_acc:.1f}%')
    # country-level LOCO as secondary check
    g = d.groupby('iso3')[['delta_published', 'arterial_coverage']].mean()
    yc, xc = g['delta_published'].to_numpy(), g['arterial_coverage'].to_numpy()
    pc = np.empty_like(yc)
    for i in range(len(g)):
        m = (np.arange(len(g)) != i)
        pc[i] = np.polyval(np.polyfit(xc[m], yc[m], 1), xc[i])
    ss_res_c, ss_tot_c = np.sum((yc - pc) ** 2), np.sum((yc - yc.mean()) ** 2)
    report.append(f'country-level LOCO: n={len(g)} R2_oos={1 - ss_res_c / ss_tot_c:.3f} '
                  f'MAE={np.mean(np.abs(yc - pc)):.2f} pp '
                  f'sign-accuracy={np.mean(np.sign(pc) == np.sign(yc)) * 100:.1f}%')

    # ---- 2. country-clustered robust SE -----------------------------------
    _, ols = _fit_ols(y, X, cluster=cid)
    report.append('=== 2. country-clustered robust standard errors ===')
    report.append(f'slope={ols["slope"]:.3f} naive SE={ols["slope_se"]:.3f} '
                  f'clustered SE={ols["slope_se_cluster"]:.3f} '
                  f'p(clustered)={ols["p_cluster"]:.2e}')

    # ---- 3. mixed model (country random intercept) ------------------------
    df = d[['delta_published', 'arterial_coverage', 'iso3']].copy()
    mm = mixedlm('delta_published ~ arterial_coverage', df, groups=df['iso3']).fit(
        reml=True, method='lbfgs')
    report.append('=== 3. mixed model (country random intercept) ===')
    report.append(f'slope={mm.params["arterial_coverage"]:.3f} '
                  f'SE={mm.bse["arterial_coverage"]:.3f} '
                  f'p={mm.pvalues["arterial_coverage"]:.2e} '
                  f'group SD={float(np.sqrt(mm.cov_re.iloc[0, 0])):.3f}')

    # ---- 4. Huber robust regression ---------------------------------------
    hu = sm.RLM(y, sm.add_constant(X), M=sm.robust.norms.HuberT()).fit()
    report.append('=== 4. Huber robust regression ===')
    report.append(f'slope={hu.params[1]:.3f} SE={hu.bse[1]:.3f} '
                  f'p={hu.pvalues[1]:.2e}')

    # ---- 5. influence diagnostics -----------------------------------------
    m, _ = _fit_ols(y, X)
    infl = m.get_influence()
    cooks = infl.cooks_distance[0]
    lev = infl.hat_matrix_diag
    d = d.copy()
    d['cooks'], d['leverage'] = cooks, lev
    top = d.sort_values('cooks', ascending=False).head(6)
    report.append('=== 5. influence diagnostics (Cook / leverage) ===')
    report.append('top Cook-D rows:')
    for r in top.itertuples():
        report.append(f'  {r.iso3} {r.service} cov={r.arterial_coverage:.1f} '
                      f'delta={r.delta_published:+.1f} cooks={r.cooks:.3f} '
                      f'lev={r.leverage:.3f}')
    hi = d[d.leverage > 2 * lev.mean()]
    report.append(f'high-leverage rows (lev > 2*mean): {len(hi)}/60, '
                  f'countries={sorted(hi.iso3.unique().tolist())}')
    # re-fit without the single most influential country
    drop = top.iso3.iloc[0]
    sub = d[d.iso3 != drop]
    ys, xs = sub['delta_published'].to_numpy(), sub['arterial_coverage'].to_numpy()
    b = np.polyfit(xs, ys, 1)
    rr = np.corrcoef(xs, ys)[0, 1]
    report.append(f'after dropping {drop}: n={len(sub)} slope={b[0]:.3f} '
                  f'r={rr:.3f} R2={rr ** 2:.3f}')

    report.append('=== 6. beta/fractional regression feasibility ===')
    report.append(f'delta_published range = [{y.min():+.1f}, {y.max():+.1f}] pp '
                  f'(unbounded, so a beta/fractional response is inapplicable; '
                  f'we report Huber + clustered inference + influence diagnostics instead)')

    text = '\n'.join(report)
    (OUT / 'summary.txt').write_text(text + '\n', encoding='utf-8')
    d[['iso3', 'service', 'arterial_coverage', 'delta_published',
       'delta_edges', 'delta_snapping', 'delta_residual',
       'cooks', 'leverage']].to_csv(OUT / 'influence_diagnostics.csv',
                                    index=False, encoding='utf-8-sig')
    print(text, flush=True)


if __name__ == '__main__':
    main()
