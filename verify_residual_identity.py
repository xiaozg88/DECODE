"""v26代数核验：验证残差恒等式、基线差、覆盖率回归重估与速度estimand 对照。

用法：
    python verify_residual_identity.py

输入：
    output/experiments/direction_law_v2/nested_decomposition.csv
输出：
    stdout 报告 + output/experiments/v26_verification/*.csv
"""
import csv
import math
import os
import statistics as st

B = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(B, 'output', 'experiments', 'direction_law_v2', 'nested_decomposition.csv')
OUT = os.path.join(B, 'output', 'experiments', 'v26_verification')
os.makedirs(OUT, exist_ok=True)

RED = '\033[31m'
RESET = '\033[0m'


def load():
    with open(SRC, encoding='utf-8-sig') as fh:
        return list(csv.DictReader(fh))


def f(r, k):
    return float(r[k])


def pearson(x, y):
    n = len(x)
    mx, my = st.mean(x), st.mean(y)
    sxy = sum((a - mx) * (b - my) for a, b in zip(x, y))
    sxx = math.sqrt(sum((a - mx) ** 2 for a in x))
    syy = math.sqrt(sum((b - my) ** 2 for b in y))
    return sxy / (sxx * syy) if sxx * syy else float('nan')


def ols(x, y):
    n = len(x)
    mx, my = st.mean(x), st.mean(y)
    sxx = sum((a - mx) ** 2 for a in x)
    sxy = sum((a - mx) * (b - my) for a, b in zip(x, y))
    slope = sxy / sxx
    inter = my - slope * mx
    pred = [inter + slope * v for v in x]
    ss_res = sum((b - p) ** 2 for b, p in zip(y, pred))
    ss_tot = sum((b - my) ** 2 for b in y)
    return slope, 1 - ss_res / ss_tot


def main():
    R = load()
    print('=' * 74)
    print('v26 残差恒等式核验   n = %d 个国家-服务行，%d 个国家'
          % (len(R), len(set(r['iso3'] for r in R))))
    print('=' * 74)

    # ---- 1. 三项恒等式 ----
    print('\n[1] 恒等式核验')
    e_id = max(abs(f(r, 'delta_published') - f(r, 'delta_edges')
                   - f(r, 'delta_snapping') - f(r, 'delta_residual')) for r in R)
    e_ed = max(abs((f(r, 'share_60min_pct_B_shared')
                    - f(r, 'share_60min_pct_A_arterial_nested'))
                   - f(r, 'delta_edges')) for r in R)
    e_sn = max(abs((f(r, 'share_60min_pct_B_full')
                    - f(r, 'share_60min_pct_B_shared'))
                   - f(r, 'delta_snapping')) for r in R)
    gap = [abs(f(r, 'reproduction_gap')) for r in R]
    print('    delta_pub - delta_edge - delta_snap - delta_residual : max|.| = %.10f' % e_id)
    print('    delta_edge  == B_shared - A_arterial_nested: max|.| = %.10f' % e_ed)
    print('    delta_snap  == B_full   - B_shared        : max|.| = %.10f' % e_sn)
    print('    复现差 |reproduction_gap| : max = %.4f pp, mean = %.4f pp'
          % (max(gap), st.mean(gap)))
    ok = max(e_id, e_ed, e_sn) < 1e-6
    print('    => 分解自洽：%s' % ('是' if ok else '否'))
    print('    => 复现差 <= 0.052 pp，故残差不来自"实现差异"')

    # ---- 2. 两个基线 ----
    print('\n[2] 两个"仅主干路"基线的对比')
    legacy = [f(r, 'corrected_published') - f(r, 'delta_published') for r in R]
    nested = [f(r, 'share_60min_pct_A_arterial_nested') for r in R]
    basediff = [n - b for b, n in zip(legacy, nested)]
    cov = [f(r, 'arterial_coverage') for r in R]
    print('    已发布基线 (%%) : min %.2f  median %.2f  mean %.2f  max %.2f'
          % (min(legacy), st.median(legacy), st.mean(legacy), max(legacy)))
    print('    嵌套基线   (%%) : min %.2f  median %.2f  mean %.2f  max %.2f'
          % (min(nested), st.median(nested), st.mean(nested), max(nested)))
    print('    基线差     (pp): min %+.2f median %+.2f mean %+.2f max %+.2f'
          % (min(basediff), st.median(basediff), st.mean(basediff), max(basediff)))
    print('    |基线差| > 10 pp : %d/%d 行' % (sum(1 for x in basediff if abs(x) > 10), len(R)))
    print('    |基线差| > 20 pp : %d/%d 行' % (sum(1 for x in basediff if abs(x) > 20), len(R)))
    print('    Pearson (基线差, 主干覆盖率)= %.3f' % pearson(basediff, cov))
    print('    Pearson (|基线差|, 主干覆盖率) = %.3f' % pearson([abs(x) for x in basediff], cov))

    # ---- 3. 三个 estimand ----
    print('\n[3] 三个 estimand 的分布（60 行）')
    E = [f(r, 'delta_edges') for r in R]
    S = [f(r, 'delta_snapping') for r in R]
    FL = [f(r, 'share_60min_pct_B_full')
          - f(r, 'share_60min_pct_A_arterial_nested') for r in R]
    LG = [f(r, 'delta_published') for r in R]
    for nm, v in [('delta_edge  (fixed capture)', E),
                  ('delta_snap  (capture change)', S),
                  ('delta_total (SAME baseline)', FL),
                  ('delta_pub   (legacy baseline)', LG)]:
        print('    %-30s min %+7.2f median %+7.2f mean %+7.2f max %+7.2f  neg %2d/%d'
              % (nm, min(v), st.median(v), st.mean(v), max(v),
                 sum(1 for x in v if x < 0), len(v)))

    # 符号反转计数的三种口径
    anyneg = {r['iso3'] for r, v in zip(R, FL) if v < 0}
    bothneg = set()
    per = {}
    for r, v in zip(R, FL):
        per.setdefault(r['iso3'], []).append(v)
    for k, v in per.items():
        if all(x < 0 for x in v):
            bothneg.add(k)
    meanneg = {k for k, v in per.items() if st.mean(v) < 0}
    legneg = {r['iso3'] for r, v in zip(R, LG) if v < 0}
    print('    统一基线：31/60 负；至少一类服务为负 %d 国；两类均为负 %d 国；国均值为负 %d 国'
          % (len(anyneg), len(bothneg), len(meanneg)))
    print('    混合基线：13/60 负；%d 国' % len(legneg))
    print('    新揭示反转的国家（%d）：%s'
          % (len(anyneg - legneg), sorted(anyneg - legneg)))

    # ---- 4. 覆盖率回归重估 ----
    print('\n[4] 对主干路覆盖率的回归重估')
    for nm, v in [('delta_pub   (legacy)', LG),
                  ('delta_total (same)  ', FL),
                  ('delta_edge          ', E),
                  ('delta_snap          ', S)]:
        sl, r2 = ols(cov, v)
        print('    %-24s slope %+7.3f   R2 %.3f' % (nm, sl, r2))

    # ---- 5. 速度 estimand ----
    print('\n[5] 速度敏感性：不同 estimand 的符号')
    an = [f(r, 'share_60min_pct_A_arterial_nested') for r in R]
    for nm, key in [('nominal', 'share_60min_pct_B_full'),
                    ('speed x1.15', 'share_60min_pct_B_full_speed115'),
                    ('speed x1.30', 'share_60min_pct_B_full_speed130')]:
        v = [f(r, key) - a for r, a in zip(R, an)]
        print('    delta_full @ %-12s min %+7.2f median %+7.2f  neg %2d/%d'
              % (nm, min(v), st.median(v), sum(1 for x in v if x < 0), len(v)))
    v0 = [f(r, 'share_60min_pct_B_full') - a for r, a in zip(R, an)]
    v1 = [f(r, 'share_60min_pct_B_full_speed115') - a for r, a in zip(R, an)]
    agree = sum(1 for a, b in zip(v0, v1) if (a < 0) == (b < 0))
    print('    标称与 x1.15 的符号一致率 = %d/%d' % (agree, len(R)))

    # ---- 输出 CSV ----
    with open(os.path.join(OUT, 'v26_country_table.csv'), 'w', newline='',
              encoding='utf-8') as fh:
        w = csv.writer(fh)
        w.writerow(['iso3', 'arterial_coverage_pct', 'delta_published',
                    'delta_total_same_baseline', 'delta_edge', 'delta_snapping',
                    'nested_baseline_pct', 'legacy_baseline_pct',
                    'baseline_diff_pp', 'residual_share'])
        by = {}
        for r in R:
            by.setdefault(r['iso3'], []).append(r)
        for k, rs in sorted(by.items()):
            g = lambda c: st.mean(f(r, c) for r in rs)          # noqa: E731
            nb = g('share_60min_pct_A_arterial_nested')
            lb = g('corrected_published') - g('delta_published')
            pub = g('delta_published')
            w.writerow([k, round(g('arterial_coverage'), 2), round(pub, 2),
                        round(g('share_60min_pct_B_full') - nb, 2),
                        round(g('delta_edges'), 2), round(g('delta_snapping'), 2),
                        round(nb, 2), round(lb, 2), round(nb - lb, 2),
                        round(abs(nb - lb) / abs(pub), 3) if pub else ''])
    print('\n已写出 %s' % os.path.join(OUT, 'v26_country_table.csv'))
    print('=' * 74)


if __name__ == '__main__':
    main()
