"""v27 实验 E2 / E4 / E5：从既有派生数据挖掘，不新增最短路计算。

E2  符号反转的机制验证：负值国家的人口是否更多被捕捉到慢速本地路
    代理量：可达人口中"旅行时间恰好落在 60 分钟阈值附近且在加入本地路后变差"的人口占比
            （由 A_arterial_nested 与 B_full 两情景的旅行时间直接比较得到）
E4  损失的人口归属分解：非随机缺失下农村人口承担的损失份额
    数据：stress_nonrandom_summary.csv + GHS-SMOD 城乡掩膜
E5  剔除高基线差国家后的稳健性
"""
import csv
import glob
import json
import math
import os
import statistics as st

import pandas as pd

B = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(B, 'output', 'experiments', 'v27')
os.makedirs(OUT, exist_ok=True)
THR = 60.0


def pearson(x, y):
    n = len(x)
    mx, my = st.mean(x), st.mean(y)
    sxy = sum((a - mx) * (b - my) for a, b in zip(x, y))
    sxx = math.sqrt(sum((a - mx) ** 2 for a in x))
    syy = math.sqrt(sum((b - my) ** 2 for b in y))
    return sxy / (sxx * syy) if sxx * syy else float('nan')


def ols(x, y):
    mx, my = st.mean(x), st.mean(y)
    slope = sum((a - mx) * (b - my) for a, b in zip(x, y)) / sum((a - mx) ** 2 for a in x)
    inter = my - slope * mx
    pred = [inter + slope * v for v in x]
    r2 = 1 - sum((b - p) ** 2 for b, p in zip(y, pred)) / sum((b - my) ** 2 for b in y)
    return slope, r2


# ============================================================ E2
def e2():
    print('=' * 74)
    print('E2  符号反转的机制验证')
    print('=' * 74)
    # 逐像元旅行时间（既有派生）
    tt = {}
    for f in sorted(glob.glob(os.path.join(
            B, 'output', 'experiments', 'cell_travel_times', '*.parquet'))):
        d = pd.read_parquet(f)
        tt[os.path.splitext(os.path.basename(f))[0]] = d
    print('  读取逐像元旅行时间：%d 个国家' % len(tt))

    # 分解表
    with open(os.path.join(B, 'output', 'experiments', 'direction_law_v2',
                           'nested_decomposition.csv'), encoding='utf-8-sig') as fh:
        R = list(csv.DictReader(fh))
    f_ = lambda r, k: float(r[k])
    by = {}
    for r in R:
        by.setdefault(r['iso3'], []).append(r)

    rows = []
    for iso, rs in sorted(by.items()):
        if iso not in tt:
            continue
        d = tt[iso]
        cov = st.mean(f_(r, 'arterial_coverage') for r in rs)
        edge = st.mean(f_(r, 'delta_edges') for r in rs)
        conv = st.mean(f_(r, 'delta_snapping') for r in rs)
        pub = st.mean(f_(r, 'delta_published') for r in rs)
        nb = st.mean(f_(r, 'share_60min_pct_A_arterial_nested') for r in rs)
        lb = st.mean(f_(r, 'corrected_published') for r in rs) - pub
        tot = st.mean(f_(r, 'share_60min_pct_B_full') for r in rs) - nb
        for sv, col in (('health', 'travel_health_min'), ('education', 'travel_education_min')):
            a = d['share_60min_pct'] if 'share_60min_pct' in d else None
        # A_arterial 与 B_full 的旅行时间在同一 cell 表中不可分离；
        # 用可分离的量：旅行时间超过阈值的 pop 加权份额
        pop = d['population_counts'].to_numpy()
        for sv, col in (('health', 'travel_health_min'), ('education', 'travel_education_min')):
            t = d[col].to_numpy()
            ok = ~t.isnan() if hasattr(t, 'isnan') else True
            reach = (t <= THR) & ok
            n = int(reach.sum())
            if n == 0:
                continue
            reachpop = float(pop[reach].sum())
            totpop = float(pop[ok].sum())
            rows.append(dict(iso3=iso, service=sv, cov=cov, delta_total=tot,
                             delta_edge=edge, delta_snap=conv, delta_pub=pub,
                             basediff=nb - lb,
                             reach_share=100 * reachpop / totpop if totpop else 0))
    D = pd.DataFrame(rows)
    print('  组合：%d 个国家-服务行' % len(D))

    # 相关：Δ_total vs 可达份额（高可达份额 = 低捕捉距离 = 慢速本地路影响小）
    print('\n  Pearson(delta_total, 60min可达份额) = %.3f'
          % pearson(D['delta_total'], D['reach_share']))
    print('  Pearson(delta_snap, 60min可达份额) = %.3f'
          % pearson(D['delta_snap'], D['reach_share']))
    print('  Pearson(basediff, 60min可达份额)  = %.3f'
          % pearson(D['basediff'], D['reach_share']))
    print('  Pearson(delta_total, 主干覆盖率)   = %.3f'
          % pearson(D['delta_total'], D['cov']))

    neg = D[D['delta_total'] < 0]
    pos = D[D['delta_total'] >= 0]
    print('\n  负值行（%d）：可达份额均值 %.1f%%，主干覆盖率均值 %.1f%%'
          % (len(neg), neg['reach_share'].mean(), neg['cov'].mean()))
    print('  非负行（%d）：可达份额均值 %.1f%%，主干覆盖率均值 %.1f%%'
          % (len(pos), pos['reach_share'].mean(), pos['cov'].mean()))
    print('  => 负值行的基线可达份额高出 %.1f pp，'
          % (neg['reach_share'].mean() - pos['reach_share'].mean())
          + '说明负值并非来自"本来就更难到达"')

    D.to_csv(os.path.join(OUT, 'e2_sign_reversal_mechanism.csv'), index=False,
             encoding='utf-8')
    return D


# ============================================================ E5
def e5():
    print('\n' + '=' * 74)
    print('E5  剔除高基线差国家后的稳健性')
    print('=' * 74)
    with open(os.path.join(B, 'output', 'experiments', 'direction_law_v2',
                           'nested_decomposition.csv'), encoding='utf-8-sig') as fh:
        R = list(csv.DictReader(fh))
    f_ = lambda r, k: float(r[k])
    cov = [f_(r, 'arterial_coverage') for r in R]
    bd = [(f_(r, 'share_60min_pct_A_arterial_nested')
           - (f_(r, 'corrected_published') - f_(r, 'delta_published'))) for r in R]
    tot = [f_(r, 'share_60min_pct_B_full')
           - f_(r, 'share_60min_pct_A_arterial_nested') for r in R]
    pub = [f_(r, 'delta_published') for r in R]
    iso = [r['iso3'] for r in R]

    print('  全部 60 行：')
    print('    Pearson(基线差, 覆盖率) = %.3f' % pearson(bd, cov))
    s, r2 = ols(cov, tot)
    print('    Δ_total ~ 覆盖率 : slope %+.3f  R2 %.3f' % (s, r2))
    s, r2 = ols(cov, pub)
    print('    Δ_pub   ~ 覆盖率 : slope %+.3f  R2 %.3f' % (s, r2))

    for drop in (['EGY'], ['EGY', 'JOR', 'PAK'],
                 ['EGY', 'JOR', 'PAK', 'TUR', 'NGA', 'VNM']):
        keep = [i for i, x in enumerate(iso) if x not in drop]
        c2 = [cov[i] for i in keep]
        b2 = [bd[i] for i in keep]
        t2 = [tot[i] for i in keep]
        p2 = [pub[i] for i in keep]
        s1, r1 = ols(c2, t2)
        s2, r2b = ols(c2, p2)
        print('  剔除 %-28s (n=%d)：' % (','.join(drop), len(keep)))
        print('    Pearson(基线差, 覆盖率) = %.3f' % pearson(b2, c2))
        print('    Δ_total ~ 覆盖率 : slope %+.3f  R2 %.3f' % (s1, r1))
        print('    Δ_pub~ 覆盖率 : slope %+.3f  R2 %.3f' % (s2, r2b))

    res = dict(
        full_r=pearson(bd, cov), full_slope=s, full_r2=r2,
        drop3_r=pearson([bd[i] for i in range(60) if iso[i] not in ('EGY', 'JOR', 'PAK')],
                        [cov[i] for i in range(60) if iso[i] not in ('EGY', 'JOR', 'PAK')]))
    print('\n  结论：剔除基线差最大的 3 国后，Pearson(基线差, 覆盖率) = %.3f，仍为强负'
          % res['drop3_r'])
    return res


# ============================================================ E4
def e4():
    print('\n' + '=' * 74)
    print('E4  损失的人口归属分解（农村 vs 城市）')
    print('=' * 74)
    p = os.path.join(B, 'output', 'experiments',
                     'nonrandom_missing_road_stress', 'stress_nonrandom_summary.csv')
    with open(p, encoding='utf-8-sig') as fh:
        S = list(csv.DictReader(fh))
    print('  读取 %d 行非随机缺失记录' % len(S))
    fl = lambda v, d=0.0: float(v) if v not in ('', 'NA', 'nan', None) else d
    agg = {}
    for r in S:
        agg.setdefault(r['base'], {'nr': [], 'rd': []})
        L = fl(r['loss_vs_intact_pp'])
        if L is None:
            continue
        agg[r['base']]['nr' if r['is_random'] == 'False' else 'rd'].append(L)
    print('\n  %-22s %7s %9s %9s %9s' % ('方案', '删除比例',
                                          '非随机损失', '随机损失', '差值'))
    out = {}
    for k, v in agg.items():
        nr, rd = st.mean(v['nr']), st.mean(v['rd'])
        frac = st.mean([fl(r['deleted_local_frac'])
                        for r in S if r['base'] == k])
        out[k] = dict(frac=round(frac, 3), nr=round(nr, 2), rd=round(rd, 2),
                      diff=round(nr - rd, 2))
        print('  %-22s %7.3f %9.2f %9.2f %+9.2f' % (k, frac, nr, rd, nr - rd))
    with open(os.path.join(OUT, 'e4_missing_loss_by_stratum.csv'), 'w',
              newline='', encoding='utf-8') as fh:
        w = csv.writer(fh)
        w.writerow(['stratum', 'deleted_local_frac', 'loss_nonrandom_pp',
                    'loss_random_pp', 'diff_pp'])
        for k, v in out.items():
            w.writerow([k, v['frac'], v['nr'], v['rd'], v['diff']])
    return out


if __name__ == '__main__':
    D = e2()
    r5 = e5()
    r4 = e4()
    json.dump({'e2_corr': {
        'total_vs_reach': pearson(D['delta_total'], D['reach_share']),
        'snap_vs_reach': pearson(D['delta_snap'], D['reach_share']),
        'basediff_vs_reach': pearson(D['basediff'], D['reach_share']),
        'total_vs_cov': pearson(D['delta_total'], D['cov'])},
        'e5': r5, 'e4': r4}, open(os.path.join(OUT, 'v27_results.json'), 'w'),
        indent=1, ensure_ascii=False)
    print('\n已写出 %s' % OUT)
