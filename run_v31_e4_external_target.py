# -*- coding: utf-8 -*-
"""v31 实验E4（方案 B）：外部靶子检验。

问题：本文诊断出"加入本地路前后"这一差分形式会产生虚假的强规律，
但被推翻的规律来自作者自己的前一版实现，缺少可引证的外部靶子。
本脚本用**真实的外部产品**重跑同类差分形式，检验该形式是否在
领域内既有的、已发表的产品之间同样产生高 R² 的表观规律。

数据：output/experiments/interstudy_comparison/interstudy_60min_comparison.csv
      30 国 × 四种口径的 60 分钟份额：
        weiss_2015_cities   —— Weiss & Nelson 2015（外部已发表产品）
        map_2020_health     —— Malaria Atlas Project 2020（外部已发表产品）
        this_arterial_only  —— 本文主干-only 基线
        this_corrected      —— 本文加入本地路

检验 1（外部靶子）：对两个外部产品之间、以及外部与本文口径之间的
        差值 Δ = A − B，用本文的主干覆盖率作自变量重跑全套推断。
        若 Δ 对覆盖率也呈高 R²，则说明该差分形式本身即可产生
        "覆盖率解释差异"的表观规律，与具体实现无关。

检验 2（LOCO 外样本）：与主稿同样的留一国交叉验证，判断该表观规律
        能否迁移到未参与拟合的国家。

检验 3（块自举零模型）：保留国别结构的零分布，各 2000 次。

输出：output/experiments/v31/e4_external_target.json / .csv
"""
import json
import os
import statistics as st

import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.regression.linear_model import OLS
from statsmodels.tools import add_constant

B = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(B, 'output/experiments/interstudy_comparison',
                   'interstudy_60min_comparison.csv')
OUT = os.path.join(B, 'output/experiments/v31')
os.makedirs(OUT, exist_ok=True)

SEED = 20261007
NPERM = 2000

# 差分形式的定义：(标签, 减数, 被减数)
PAIRS = [
    ('Weiss2015 - MAP2020        (外部 vs 外部)',
     'weiss_2015_cities', 'map_2020_health',
     'external_vs_external'),
    ('Weiss2015 - 本文主干基线     (外部 vs 本文)',
     'weiss_2015_cities', 'this_arterial_only',
     'second_external_target'),
    ('MAP2020 - 本文主干基线       (外部 vs 本文)',
     'map_2020_health', 'this_arterial_only',
     'primary_external_target'),
    ('MAP2020 - 本文含本地路       (外部 vs 本文)',
     'map_2020_health', 'this_corrected',
     'external_vs_full'),
    ('本文含本地路 - 本文主干基线   (本文内部同口径)',
     'this_corrected', 'this_arterial_only',
     'internal_same_convention'),
]


def fit_ols(x, y):
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    r = OLS(y, add_constant(x)).fit()
    return dict(slope=float(r.params[1]), intercept=float(r.params[0]),
                se=float(r.bse[1]), t=float(r.tvalues[1]),
                r2=float(r.rsquared), n=len(x))


def loco(x, y, level='row'):
    """留一国交叉验证；level='row' 时每行自成一折（n=30 国，每国 1 行）。"""
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


def block_bootstrap_null(x, y, rng, nboot=NPERM):
    """块自举（块长 1 国）零分布：保留国家级结构。"""
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    r2s = []
    for _ in range(nboot):
        idx = rng.integers(0, len(y), len(y))
        if len(np.unique(x[idx])) < 2:
            continue
        b, a = np.polyfit(x[idx], y[idx], 1)
        pred = a + b * x[idx]
        ss_res = float(((y[idx] - pred) ** 2).sum())
        ss_tot = float(((y[idx] - y[idx].mean()) ** 2).sum())
        if ss_tot > 0:
            r2s.append(1 - ss_res / ss_tot)
    return np.asarray(r2s)


def permute_null(x, y, rng, nperm=NPERM):
    """完全打乱因变量零分布：破坏国家级结构。"""
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    r2s = []
    for _ in range(nperm):
        d = rng.permutation(y)
        b, a = np.polyfit(x, d, 1)
        pred = a + b * x
        ss_res = float(((d - pred) ** 2).sum())
        ss_tot = float(((d - d.mean()) ** 2).sum())
        r2s.append(1 - ss_res / ss_tot)
    return np.asarray(r2s)


def main():
    print('=' * 78)
    print('E4  外部靶子检验：已发表产品之间是否也产生同样的表观规律')
    print('=' * 78)
    D = pd.read_csv(SRC, encoding='utf-8-sig')
    N = pd.read_csv(os.path.join(B, 'output/experiments/direction_law_v2',
                                 'nested_decomposition.csv'),
                    encoding='utf-8-sig')[['iso3', 'service', 'arterial_coverage']]
    # interstudy 表每国 1 行，nested_decomposition 每国 2 行（health/education）。
    # 主干覆盖率按服务类型不同，必须先按服务展开成 30 国 × 2 服务，
    # 否则 merge 会把每国复制两次。
    # 但外部产品的份额是卫生口径（map_2020_health），故用 health 行的覆盖率。
    N = N[N['service'] == 'health'][['iso3', 'arterial_coverage']]
    D = D.merge(N, on='iso3', how='left')
    assert len(D) == 30, 'merge 后应为 30 行，实际 %d' % len(D)
    cov = D['arterial_coverage'].to_numpy(float)
    print('  n = %d 国，主干覆盖率 %.1f–%.1f%%'
          % (len(D), cov.min(), cov.max()))

    rng = np.random.default_rng(SEED)
    res, rows = {}, []

    for label, a_col, b_col, role in PAIRS:
        delta = D[a_col].to_numpy(float) - D[b_col].to_numpy(float)
        o = fit_ols(cov, delta)
        lc = loco(cov, delta)
        bb = block_bootstrap_null(cov, delta, rng)
        pm = permute_null(cov, delta, rng)
        pct_bb = float((bb < o['r2']).mean() * 100)
        pct_pm = float((pm < o['r2']).mean() * 100)
        pear = float(np.corrcoef(cov, delta)[0, 1])
        spear = float(stats.spearmanr(cov, delta).statistic)
        nneg = int((delta < 0).sum())

        key = label.strip()
        res[key] = dict(role=role, ols=o, loco=lc, pearson=pear, spearman=spear,
                        n_negative=nneg,
                        null_block=dict(mean=float(bb.mean()), sd=float(bb.std()),
                                        pct=pct_bb),
                        null_perm=dict(mean=float(pm.mean()), sd=float(pm.std()),
                                       pct=pct_pm))
        rows.append(dict(pair=key, role=role, slope=o['slope'], r2=o['r2'],
                         r2_adj=o['r2'] - (1 - o['r2']) * (o['n'] - 1) / (o['n'] - 2),
                         t=o['t'], pearson=pear, spearman=spear,
                         loco_r2=lc['oof_r2'], loco_dir=lc['dir_acc'],
                         block_pct=pct_bb, perm_pct=pct_pm, n_neg=nneg))

        print('\n' + '-' * 78)
        print('  %s' % key)
        print('    Δ = %s − %s' % (a_col, b_col))
        print('    Δ 分布: min %+.2f  median %+.2f  mean %+.2f  max %+.2f  负值 %d/30'
              % (delta.min(), np.median(delta), delta.mean(), delta.max(), nneg))
        print('    OLS: slope %+.3f (SE %.3f, t=%.2f)  R2 %.3f  Pearson %.3f  Spearman %.3f'
              % (o['slope'], o['se'], o['t'], o['r2'], pear, spear))
        print('    LOCO 外样本: R2 %.3f  方向正确率 %.1f%%' % (lc['oof_r2'], lc['dir_acc']))
        print('    块自举零分布: 均值 %.3f (SD %.3f)  观测分位 %.1f%%'
              % (bb.mean(), bb.std(), pct_bb))
        print('    完全打乱零分布: 均值 %.3f (SD %.3f)  观测分位 %.1f%%'
              % (pm.mean(), pm.std(), pct_pm))

    # ---- 跨产品对比的可迁移性：把五组回归放在一起比较 ----
    print('\n' + '=' * 78)
    print('  汇总：五组差分形式的拟合优度对比')
    print('=' * 78)
    print('  %-40s %8s %9s %9s %9s' % ('差分形式', 'R2', 'LOCO R2', '块自举%', '打乱%'))
    for r in rows:
        print('  %-40s %8.3f %9.3f %9.1f %9.1f'
              % (r['pair'], r['r2'], r['loco_r2'], r['block_pct'], r['perm_pct']))

    r2s = [r['r2'] for r in rows]
    print('\n  外部产品之间的差分形式最大 R2 = %.3f' % max(r2s))
    print('  n = %d 组中有 %d 组 R2 > 0.5，%d 组 LOCO 外样本 R2 > 0'
          % (len(rows), sum(1 for x in r2s if x > 0.5),
             sum(1 for r in rows if r['loco_r2'] > 0)))
    print('  => 若外部靶子的 R2 与 LOCO 均达到与本文混合基线相当的水平，'
          '则该表观规律是差分形式的普遍产物，而非某一实现特有的错误。')

    pd.DataFrame(rows).to_csv(os.path.join(OUT, 'e4_external_target.csv'),
                              index=False, encoding='utf-8-sig')
    json.dump(res, open(os.path.join(OUT, 'e4_external_target.json'), 'w'),
              indent=1, ensure_ascii=False)
    print('\n  已写出 %s' % OUT)


if __name__ == '__main__':
    main()
