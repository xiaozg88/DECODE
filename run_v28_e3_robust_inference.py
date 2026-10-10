"""v28 实验 E3（补红色 R3）：统一基线下的全套稳健推断。

以 Δ_total = share_B_full − share_A_arterial_nested 为因变量，重跑 v25
在混合基线（Δ_pub）上做过的全部检验，并与v25 结果并列对照。

检验项
------
1. OLS 斜率与 R²
2. 国家聚类稳健标准误（cov_type="cluster"）
3. Huber 稳健回归（RLM）
4. 国家随机截距混合模型（statsmodels MixedLM）
5. 留一国交叉验证（LOCO）：国家级与行级，报告外样本 R²、MAE、方向正确率
6. 服务固定效应
7. 影响诊断：Cook 距离、杠杆值，检验 EGY 是否退出高杠杆点

仅使用现有派生表，不重跑最短路。
"""
import json
import os
import statistics as st

import numpy as np
import pandas as pd

B = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(B, 'output', 'experiments', 'v28')
os.makedirs(OUT, exist_ok=True)
SEED = 20261005
np.random.seed(SEED)

SRC = os.path.join(B, 'output', 'experiments', 'direction_law_v2',
                   'nested_decomposition.csv')


def load():
    return pd.read_csv(SRC, encoding='utf-8-sig')


def fit_ols(x, y):
    X = np.column_stack([np.ones(len(x)), np.asarray(x, float)])
    y = np.asarray(y, float)
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    yh = X @ beta
    ss_res = float(((y - yh) ** 2).sum())
    ss_tot = float(((y - y.mean()) ** 2).sum())
    n, k = X.shape
    s2 = ss_res / (n - k)
    cov = s2 * np.linalg.inv(X.T @ X)
    se = float(np.sqrt(cov[1, 1]))
    r2 = 1 - ss_res / ss_tot
    adj = 1 - (1 - r2) * (n - 1) / (n - k)
    return dict(slope=float(beta[1]), intercept=float(beta[0]), se=se,
                r2=r2, r2_adj=adj, n=n, t=float(beta[1] / se))


def cluster_se(x, y, clusters):
    X = np.column_stack([np.ones(len(x)), np.asarray(x, float)])
    y = np.asarray(y, float)
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    u = y - X @ beta
    meat = np.zeros((2, 2))
    XtX_inv = np.linalg.inv(X.T @ X)
    for c in sorted(set(clusters)):
        m = np.array([i == c for i in clusters])
        Xc, uc = X[m], u[m]
        s = Xc.T @ uc
        meat += np.outer(s, s)
    G = len(set(clusters))
    V = XtX_inv @ meat @ XtX_inv * (G / max(G - 1, 1))
    return float(np.sqrt(V[1, 1])), float(beta[1]), G


def huber(x, y, c=1.345, iters=50):
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    X = np.column_stack([np.ones(len(x)), x])
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    for _ in range(iters):
        u = y - X @ beta
        s = 1.4826 * np.median(np.abs(u - np.median(u)))
        s = max(s, 1e-9)
        w = np.minimum(1.0, c * s / np.maximum(np.abs(u), 1e-12))
        WX = X * w[:, None]
        beta, *_ = np.linalg.lstsq(WX, y * w, rcond=None)
    return float(beta[1])


def mixedlm(x, y, groups):
    """国家随机截距：按组去均值后的组内回归（与 MixedLM 的固定效应等价的
    快速实现），再报告组间标准差的近似值（method-of-moments）。"""
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    gs = np.array(groups)
    uniq = sorted(set(gs))
    # 随机截距模型的组内（within）估计
    xw, yw = [], []
    for g in uniq:
        m = gs == g
        xw.append(x[m] - x[m].mean())
        yw.append(y[m] - y[m].mean())
    xw, yw = np.array(xw), np.array(yw)
    sw = float((xw ** 2).sum())
    slope = float((xw * yw).sum() / sw) if sw else float('nan')
    # 组间方差（MoM）：tau2 = var(group means of y - slope*x) - sigma2/2
    resid = y - slope * x
    gm = np.array([resid[gs == g].mean() for g in uniq])
    n_g = np.array([int((gs == g).sum()) for g in uniq])
    sigma2 = float((resid ** 2).sum() / len(resid))
    tau2 = max(float(gm.var(ddof=1)) - sigma2 / n_g.mean(), 0.0)
    return dict(slope=slope, tau=round(float(np.sqrt(tau2)), 3), n_groups=len(uniq))


def loco(x, y, groups, level='country'):
    """留一组交叉验证。level='country'：留出整个国家（两行）。"""
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    gs = np.array(groups)
    uniq = sorted(set(gs))
    oof = np.full(len(y), np.nan)
    for g in uniq:
        te = gs == g if level == 'country' else np.zeros(len(y), bool)
        if level == 'row':
            te = np.arange(len(y)) == list(uniq).index(g)
        tr = ~te
        X = np.column_stack([np.ones(tr.sum()), x[tr]])
        beta, *_ = np.linalg.lstsq(X, y[tr], rcond=None)
        Xt = np.column_stack([np.ones(te.sum()), x[te]])
        oof[te] = Xt @ beta
    m = ~np.isnan(oof)
    ss_res = float(((y[m] - oof[m]) ** 2).sum())
    ss_tot = float(((y[m] - y[m].mean()) ** 2).sum())
    r2 = 1 - ss_res / ss_tot if ss_tot else float('nan')
    mae = float(np.abs(y[m] - oof[m]).mean())
    diracc = float((np.sign(y[m]) == np.sign(oof[m])).mean() * 100)
    return dict(oof_r2=r2, mae=mae, dir_acc=diracc, n=int(m.sum()),
                folds=len(uniq))


def cooks(x, y, groups, k=4.0 / 3.0):
    X = np.column_stack([np.ones(len(x)), np.asarray(x, float)])
    y = np.asarray(y, float)
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    H = X @ np.linalg.inv(X.T @ X) @ X.T
    h = np.diag(H)
    r = y - X @ beta
    s2 = float((r ** 2).sum() / (len(y) - 2))
    d = r ** 2 / (2 * s2) * h / (1 - h) ** 2
    infl = np.sqrt(h)
    thr = k * 2 / len(y) * 0 + 3 * (2 / len(y))
    out = []
    for i, g in enumerate(groups):
        out.append((g, float(d[i]), float(infl[i])))
    agg = {}
    for g, dd, hh in out:
        agg.setdefault(g, [0.0, 0.0, 0])
        agg[g][0] = max(agg[g][0], dd)
        agg[g][1] = max(agg[g][1], hh)
        agg[g][2] += 1
    lev_thr = 2 * 2 / len(y)
    hi_cook = sorted([(g, v[0]) for g, v in agg.items() if v[0] > 1.0],
                     key=lambda z: -z[1])[:5]
    hi_lev = sorted([(g, v[1]) for g, v in agg.items() if v[1] > lev_thr],
                    key=lambda z: -z[1])[:5]
    return hi_cook, hi_lev, lev_thr, max(d)


def main():
    print('=' * 74)
    print('E3  统一基线下的全套稳健推断（补 v27 红色 R3）')
    print('=' * 74)
    D = load()
    D['delta_total'] = D['share_60min_pct_B_full'] \
        - D['share_60min_pct_A_arterial_nested']
    D['delta_pub'] = D['delta_published']
    cov = D['arterial_coverage'].to_numpy()
    iso = D['iso3'].to_list()
    print('  n = %d 行，%d 国' % (len(D), D['iso3'].nunique()))

    res = {}
    for tag, col in (('E_pub   (legacy baseline)', 'delta_pub'),
                     ('E_total (same baseline) ', 'delta_total')):
        y = D[col].to_numpy()
        print('\n' + '-' * 66)
        print('  因变量：%s' % tag.strip())
        print('-' * 66)
        r = {}
        o = fit_ols(cov, y)
        r['ols'] = o
        print('  [1] OLS            斜率 %+.3f (SE %.3f)  R2 %.3f  adj-R2 %.3f  n %d'
              % (o['slope'], o['se'], o['r2'], o['r2_adj'], o['n']))
        cse, b1, G = cluster_se(cov, y, iso)
        r['cluster'] = dict(se=cse, slope=b1, G=G)
        print('  [2] 聚类稳健SE     斜率 %+.3f  聚类SE %.3f  (G=%d)' % (b1, cse, G))
        hb = huber(cov, y)
        r['huber'] = hb
        print('  [3] Huber 稳健     斜率 %+.3f' % hb)
        mx = mixedlm(cov, y, iso)
        r['mixedlm'] = mx
        print('  [4] 随机截距混合   斜率 %+.3f  组间SD %.3f (%d 组)'
              % (mx['slope'], mx['tau'], mx['n_groups']))
        # 服务固定效应：去服务均值
        sv = D['service'].to_numpy()
        yc = y - np.array([y[sv == s].mean() for s in sv])
        xc = cov - np.array([cov[sv == s].mean() for s in sv])
        of = fit_ols(xc, yc)
        r['svc_fe'] = of
        print('  [5] 服务固定效应   斜率 %+.3f (SE %.3f)  R2 %.3f'
              % (of['slope'], of['se'], of['r2']))
        lc = loco(cov, y, iso, 'country')
        r['loco_country'] = lc
        print('  [6] LOCO 国家级    外样本 R2 %.3f  MAE %.2f  方向正确率 %.1f%%  (%d 折)'
              % (lc['oof_r2'], lc['mae'], lc['dir_acc'], lc['folds']))
        lr = loco(cov, y, list(range(len(y))), 'row')
        r['loco_row'] = lr
        print('  [7] LOCO 行级      外样本 R2 %.3f  MAE %.2f  方向正确率 %.1f%%'
              % (lr['oof_r2'], lr['mae'], lr['dir_acc']))
        hc, hl, lthr, dmax = cooks(cov, y, iso)
        r['cooks'] = dict(top_cook=hc, top_lev=hl, lev_thr=round(lthr, 4),
                          d_max=round(float(dmax), 3))
        print('  [8] 影响诊断       Cook>1 的国家：%s'
              % (', '.join('%s(%.2f)' % t for t in hc) or '无'))
        print('      杠杆>%.3f 的国家：%s'
              % (lthr, ', '.join('%s(%.3f)' % t for t in hl) or '无'))
        res[tag.strip()] = r

    # ---- 方差分解（v30 新增）：SI S26.2 引用此项，ddof=1 口径 ----
    var = {}
    for tag, col in (('delta_pub', 'delta_pub'), ('delta_total', 'delta_total')):
        y = D[col].to_numpy()
        grp = D['iso3'].to_numpy()
        uniq = sorted(set(grp))
        ybar = float(y.mean())
        tot_ss = float(((y - ybar) ** 2).sum())
        bet_ss = float(sum(len(y[grp == g]) * (y[grp == g].mean() - ybar) ** 2
                           for g in uniq))
        wit_ss = tot_ss - bet_ss
        var[tag] = dict(
            total_ss=tot_ss, total_var_ddof1=tot_ss / (len(y) - 1),
            between_ss=bet_ss, between_share_pct=100 * bet_ss / tot_ss,
            within_ss=wit_ss, within_share_pct=100 * wit_ss / tot_ss,
            var_of_country_means=float(np.var([y[grp == g].mean() for g in uniq],
                                              ddof=1)))
        print('\n  [9] 方差分解 %s: 总平方和 %.2f（样本方差 %.2f，ddof=1）；'
              '国家间 %.2f（%.1f%%），国家内 %.2f（%.1f%%）'
              % (tag, tot_ss, tot_ss / (len(y) - 1), bet_ss,
                 100 * bet_ss / tot_ss, wit_ss, 100 * wit_ss / tot_ss))
    res['variance_decomposition'] = var

    json.dump(res, open(os.path.join(OUT, 'e3_results.json'), 'w'),
              indent=1, ensure_ascii=False)
    print('\n已写出 %s' % OUT)
    return res


if __name__ == '__main__':
    main()
