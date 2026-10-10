"""v26 鍥句欢鐢熸垚锛氫富鍥?1鈥? 涓庢柊澧炶ˉ鍏呭浘銆?
鎵€鏈夋暟鍊兼潵鑷幇鏈夋淳鐢?CSV锛屼笉鏂板璁＄畻瀹為獙銆傜孩鑹叉爣娉ㄩ」涓哄緟琛ュ疄楠屽崰浣嶃€?
"""
import csv, math, os
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

B = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(B, 'figures', 'v29')
os.makedirs(OUT, exist_ok=True)
CM_TO_PT = 72 / 2.54
plt.rcParams.update({'font.size': 8, 'axes.titlesize': 8.5, 'axes.labelsize': 8,
                     'xtick.labelsize': 7, 'ytick.labelsize': 7, 'legend.fontsize': 7,
                     'figure.dpi': 150, 'savefig.bbox': 'tight'})
C = dict(blue='#3B6FB0', orange='#E08A3C', green='#4C9A6A', red='#C0453C',
         grey='#8A8A85', purple='#7F77DD', teal='#2E8B8B')
LBL = {'health': 'health', 'education': 'education'}


def load(fn, sub=''):
    p = os.path.join(B, sub, fn) if sub else os.path.join(B, fn)
    with open(p, encoding='utf-8-sig') as fh:
        return list(csv.DictReader(fh))


def save(fig, name):
    for ext in ('png', 'pdf'):
        fig.savefig(os.path.join(OUT, f'{name}.{ext}'), dpi=300)
    plt.close(fig)
    print('  wrote', name)


# ============ 涓诲浘 1锛氬悓瀹氫箟鍙ｅ緞 vs 璺ㄤ骇鍝佷笉鍙瘮锛堜袱鏍忥級 ============
S11 = [('EGY',98.4,99.5,21.7,97.0,77.8),('PNG',19.0,31.8,86.4,62.0,67.4),('JOR',96.8,98.7,34.7,97.2,64.1),
       ('NGA',87.9,96.7,40.3,77.3,56.4),('ETH',55.0,80.2,27.1,52.9,53.1),('PAK',89.7,92.0,39.4,89.6,52.6),
       ('MLI',41.5,89.1,75.8,65.7,47.6),('TZA',47.2,93.8,88.9,86.9,46.6),('TUR',89.8,98.7,55.5,92.4,43.3),
       ('KHM',49.9,79.5,64.5,86.5,36.7),('SEN',64.9,93.8,58.7,84.7,35.1),('VNM',90.2,96.4,63.9,90.7,32.5),
       ('MEX',86.2,97.6,65.3,92.9,32.3),('KEN',74.9,94.2,62.3,85.6,31.9),('MOZ',54.6,85.9,55.6,76.6,31.3),
       ('HND',57.4,87.5,76.6,84.9,30.1),('ZMB',58.4,85.5,87.2,80.0,28.8),('GEO',69.9,97.1,85.5,97.3,27.4),
       ('BGD',97.4,98.7,72.2,93.1,26.5),('KGZ',64.7,83.5,82.0,88.0,23.3),('PHL',74.1,95.8,88.8,89.7,21.8),
       ('GHA',75.5,97.0,81.3,90.1,21.5),('RWA',79.1,99.8,94.1,98.0,20.7),('IND',94.5,96.9,77.7,98.1,20.3),
       ('GTM',70.8,89.4,74.0,83.0,18.6),('NPL',78.9,95.5,97.1,91.3,18.2),('LKA',86.3,99.6,81.8,99.0,17.8),
       ('IDN',81.7,91.9,76.4,84.4,15.5),('PER',73.4,83.7,83.3,87.1,13.7),('COL',77.0,82.7,81.6,88.0,11.0)]

fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.5), gridspec_kw={'width_ratios': [1, 1]})
fig.set_constrained_layout(True)
# (a) same-definition contrast
ax = axes[0]
d = sorted([(r[0], r[3], r[4]) for r in S11], key=lambda x: -(x[1]-x[2]))
y = np.arange(len(d))
for i, (iso, a, b) in enumerate(d):
    ax.plot([a, b], [i, i], color=C['grey'], lw=0.7, zorder=1)
    ax.plot(a, i, 'o', ms=3.2, color=C['orange'], zorder=3)
    ax.plot(b, i, 'o', ms=3.2, color=C['green'], zorder=3)
ax.set_yticks(y[::3]); ax.set_yticklabels([x[0] for x in d[::3]])
ax.set_xlabel('Population within 60 min (%)')
ax.set_title('a  Same-definition contrast\n(identical model, year, population, facilities)', loc='left')
ax.set_ylim(-1.8, len(d))
ax.legend(handles=[Patch(color=C['orange'], label='arterial only'),
                   Patch(color=C['green'], label='+ local roads')],
          loc='upper center', bbox_to_anchor=(0.5, -0.12), frameon=False, fontsize=6.5, ncol=2)
ax.annotate('median spread 18.8 pp, max 75.3 pp',
            xy=(0, 0), xycoords='axes fraction',
            xytext=(0.2 * CM_TO_PT, 0.5 * CM_TO_PT), textcoords='offset points',
            fontsize=6.5, ha='left', va='bottom',
            bbox=dict(fc='white', ec=C['grey'], lw=0.4, alpha=0.95))
# (b) cross-product
ax = axes[1]
d2 = sorted(S11, key=lambda r: -r[5])
y = np.arange(len(d2))
for i, r in enumerate(d2):
    ax.plot([r[1], r[2], r[3], r[4]], [i]*4, color=C['grey'], lw=0.7, zorder=1)
    for x, c in zip(r[1:5], [C['purple'], C['blue'], C['orange'], C['green']]):
        ax.plot(x, i, 'o', ms=3.0, color=c, zorder=3)
ax.set_yticks(y[::3]); ax.set_yticklabels([r[0] for r in d2[::3]])
ax.set_xlabel('Population within 60 min (%)')
ax.set_title('b  Cross-product non-comparability\n(differs in service target and vintage)', loc='left')
ax.set_ylim(-3.6, len(d2))
ax.legend(handles=[Patch(color=C['purple'], label='town >=50k (2015)'),
                   Patch(color=C['blue'], label='healthcare (2020)'),
                   Patch(color=C['orange'], label='this: arterial'),
                   Patch(color=C['green'], label='this: + local')],
          loc='upper center', bbox_to_anchor=(0.5, -0.12), frameon=False, fontsize=6.0, ncol=2)
ax.annotate('median spread 30.7 pp, max 77.8 pp (EGY)\n24/30 countries > 20 pp',
            xy=(0, 1), xycoords='axes fraction',
            xytext=(0.2 * CM_TO_PT, -0.5 * CM_TO_PT), textcoords='offset points',
            fontsize=6.5, ha='left', va='top',
            bbox=dict(fc='white', ec=C['grey'], lw=0.4, alpha=0.95))
save(fig, 'fig1_protocol_contrasts')

# ============ 涓诲浘 2锛氬悓鍩虹嚎鍒嗚В + 瑕嗙洊鐜囧叧绯昏璇佷吉 ============
R = load(r'output\experiments\direction_law_v2\nested_decomposition.csv')
fl = lambda r, k: float(r[k])
by = {}
for r in R:
    by.setdefault(r['iso3'], []).append(r)
iso = sorted(by)
E = {k: np.mean([fl(r, 'delta_edges') for r in by[k]]) for k in iso}
S = {k: np.mean([fl(r, 'delta_snapping') for r in by[k]]) for k in iso}
LEG = {k: np.mean([fl(r, 'delta_published') for r in by[k]]) for k in iso}
FULL = {k: np.mean([fl(r, 'share_60min_pct_B_full') - fl(r, 'share_60min_pct_A_arterial_nested') for r in by[k]]) for k in iso}
cov = {k: np.mean([fl(r, 'arterial_coverage') for r in by[k]]) for k in iso}
order = sorted(iso, key=lambda k: -FULL[k])

fig, axes = plt.subplots(1, 3, figsize=(9.8, 3.4), gridspec_kw={'width_ratios': [1.05, 1, 0.95]})
fig.set_constrained_layout(True)
# (a) E_edge and E_snap on common baseline
ax = axes[0]
y = np.arange(len(order))
for i, k in enumerate(order):
    ax.plot([0, E[k]], [i, i], color=C['green'], lw=2.4, solid_capstyle='butt', alpha=0.85)
    ax.plot([S[k], 0], [i, i], color=C['orange'], lw=2.4, solid_capstyle='butt', alpha=0.85)
ax.axvline(0, color=C['grey'], lw=0.6)
ax.set_yticks(y[::3]); ax.set_yticklabels([k for k in order[::3]])
ax.set_xlabel('Component (pp)')
ax.set_title('a  Edge and capture components\nshare one baseline', loc='left')
ax.legend(handles=[Patch(color=C['green'], label='edge (E_edge >= 0, 60/60)'),
                   Patch(color=C['orange'], label='capture (E_snap <= 0, 60/60)')],
          loc='upper center', bbox_to_anchor=(0.5, -0.16), frameon=False, fontsize=6.2, ncol=1)
ax.set_ylim(-1, len(order))
# (b) total contrast, nested vs legacy
ax = axes[1]
w = 0.38
x = np.arange(len(order))
ax.barh(x - w/2, [FULL[k] for k in order], height=w, color=C['blue'], label='same baseline (E_full)')
ax.barh(x + w/2, [LEG[k] for k in order], height=w, color=C['grey'], label='legacy mixed baseline')
ax.axvline(0, color='black', lw=0.6)
ax.set_yticks(x[::3]); ax.set_yticklabels([k for k in order[::3]])
ax.invert_yaxis()
ax.set_ylim(len(order) + 1.2, -0.6)
ax.set_xlabel('60-min share difference (pp)')
ax.set_title('b  Baseline choice determines\nthe apparent effect', loc='left')
ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.16), frameon=False, fontsize=6.2, ncol=1)
# (c) coverage relationship collapses
ax = axes[2]
ax.scatter([cov[k] for k in iso], [LEG[k] for k in iso], s=14, color=C['grey'], label='legacy ($R^2$=0.77)')
ax.scatter([cov[k] for k in iso], [FULL[k] for k in iso], s=14, color=C['blue'], label='same baseline ($R^2$=0.06)')
x0, x1 = 20, 100
ax.plot([x0, x1], [np.polyval(np.polyfit([cov[k] for k in iso], [LEG[k] for k in iso], 1), x0),
                   np.polyval(np.polyfit([cov[k] for k in iso], [LEG[k] for k in iso], 1), x1)],
        color=C['grey'], lw=1.0, ls='--')
ax.set_xlabel('Arterial coverage (%)')
ax.set_ylabel('60-min share difference (pp)')
ax.set_title('c  The apparent coverage "law"\ncollapses on a common baseline', loc='left')
ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.16), frameon=False, fontsize=6.2, ncol=1)
ax.set_ylim(-32, 78)
save(fig, 'fig2_common_baseline')

# ============ 涓诲浘 3锛氶€熷害 estimand 涓庣鍙风殑鍙ｅ緞渚濊禆 ============
E115 = {k: np.mean([fl(r, 'share_60min_pct_B_full_speed115') - fl(r, 'share_60min_pct_A_arterial_nested') for r in by[k]]) for k in iso}
E130 = {k: np.mean([fl(r, 'share_60min_pct_B_full_speed130') - fl(r, 'share_60min_pct_A_arterial_nested') for r in by[k]]) for k in iso}
fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.0))
fig.set_constrained_layout(True)
ax = axes[0]
srt = sorted(iso, key=lambda k: FULL[k])
x = np.arange(len(srt))
ax.plot(x, [FULL[k] for k in srt], 'o-', ms=3, lw=1.2, color=C['blue'], label='nominal speed')
ax.plot(x, [E115[k] for k in srt], 's-', ms=3, lw=1.0, color=C['orange'], label='speed x1.15')
ax.plot(x, [E130[k] for k in srt], '^-', ms=3, lw=1.0, color=C['green'], label='speed x1.30')
ax.axhline(0, color='black', lw=0.6)
ax.set_xticks(x[::4]); ax.set_xticklabels([k for k in srt[::4]], rotation=60)
ax.set_ylabel('E_full on the stated baseline (pp)')
ax.set_title('a  Even the sign depends on the speed convention', loc='left')
ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.12), frameon=False, fontsize=6.5, ncol=3)
ax.text(0.98, 0.04, 'negative rows: 31 / 26 / 24 of 60', transform=ax.transAxes,
        ha='right', fontsize=6.5, bbox=dict(fc='white', ec=C['grey'], lw=0.4, alpha=0.9))
# (b) edge component under access cost
ax = axes[1]
xs = [0, 0.2, 0.4, 0.6, 0.8, 1.0]
mean_edge = [2.45, 12.0, 15.5, 16.6, 17.4, 17.78]
lo = [-1.0, -4.0, 1.0, 1.4, 3.0, 5.6]
hi = [33.5, 28.0, 21.0, 17.0, 16.0, 30.4]
ax.fill_between(xs, lo, hi, color=C['blue'], alpha=0.15)
ax.plot(xs, mean_edge, 'o-', ms=3.5, lw=1.4, color=C['blue'])
ax.axhline(0, color='black', lw=0.6)
ax.set_xticks(xs)
ax.set_xticklabels(['zero', '1.2/10', '1.2/5', '1.2/3', '1.4/5', '1.4/3'], rotation=30)
ax.set_xlabel('Access-cost scenario (circuity / speed, km h$^{-1}$)')
ax.set_ylabel('Mean edge increment (pp)')
ax.set_title('b  Explicit access cost changes the\nmagnitude of the edge term', loc='left')
ax.text(0.03, 0.06, 'shading: min-max range over 60 country-service rows',
        transform=ax.transAxes, fontsize=6.2,
        bbox=dict(fc='white', ec=C['grey'], lw=0.4, alpha=0.9))
save(fig, 'fig3_speed_and_access')

# ============ 涓诲浘 4锛氭畫宸?= 鍩虹嚎宸?============
LB = {k: np.mean([fl(r, 'corrected_published') - fl(r, 'delta_published') for r in by[k]]) for k in iso}
NB = {k: np.mean([fl(r, 'share_60min_pct_A_arterial_nested') for r in by[k]]) for k in iso}
srt = sorted(iso, key=lambda k: -(NB[k] - LB[k]))
fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.2))
fig.set_constrained_layout(True)
ax = axes[0]
x = np.arange(len(srt))
ax.bar(x, [NB[k] for k in srt], color=C['blue'], label='nested counterfactual baseline', width=0.7)
ax.bar(x, [LB[k] for k in srt], color=C['orange'], label='legacy published baseline', width=0.4)
ax.set_xticks(x[::3]); ax.set_xticklabels([k for k in srt[::3]], rotation=60)
ax.set_ylabel('Arterial-only 60-min share (%)')
ax.set_title('a  Two arterial-only baselines differ by up to 72 pp', loc='left')
ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.12), frameon=False, fontsize=6.5, ncol=2)
ax.text(0.02, 0.72, 'mean gap +12.13 pp, median +4.49 pp\n> 20 pp in 18/60 rows', transform=ax.transAxes,
        fontsize=6.5, bbox=dict(fc='white', ec=C['grey'], lw=0.4, alpha=0.9))
ax = axes[1]
gap = [NB[k] - LB[k] for k in iso]
ax.scatter(cov.values(), gap, s=16, color=C['red'])
xs = np.linspace(min(cov.values()) - 3, max(cov.values()) + 3, 50)
p = np.polyfit(list(cov.values()), gap, 1)
ax.plot(xs, np.polyval(p, xs), color='black', lw=1.0, ls='--')
ax.axhline(0, color=C['grey'], lw=0.6)
ax.set_xlabel('Arterial coverage (%)')
ax.set_ylabel('Nested minus legacy baseline (pp)')
ax.set_title('b  Baseline inconsistency is\nanti-correlated with coverage (r = -0.79)', loc='left')
ax.text(0.03, 0.06, 'sparse arterial networks have the\nmost severe baseline mismatch', transform=ax.transAxes,
        fontsize=6.5, bbox=dict(fc='white', ec=C['grey'], lw=0.4, alpha=0.9))
save(fig, 'fig4_residual_diagnosis')

# ============ 涓诲浘 5锛氳韩浠界炕杞?============
I = [r for r in load(r'explorations\output\d09_access_identity_flip_summary.csv')
     if r['threshold_min'] == '60' and r['service'] == 'either']
def ff(v, d=0.0):
    try: return float(v)
    except Exception: return d
fl_rows = sorted([(r['iso3'], ff(r['total_population']), ff(r['flip_population'])) for r in I],
                 key=lambda x: -x[2])
conn = {}
for r in load(r'explorations\output\d04_connectivity_all.csv'):
    b = ff(r['bridge_length_share'], -1)
    if b >= 0: conn[r['iso3']] = ff(r['connectivity_share'])
sub = [(k, 100 * f / p) for k, p, f in fl_rows if p > 0 and k in conn]
fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.0))
fig.set_constrained_layout(True)
ax = axes[0]
top = fl_rows[::-1]
x = np.arange(len(top))
vals = [f / 1e6 for _, _, f in top]
ax.barh(x, [max(v, 0.6) for v in vals], color=[C['red'] if i >= len(top) - 8 else C['grey'] for i in range(len(top))])
ax.set_yticks(x); ax.set_yticklabels([k for k, _, _ in top], fontsize=5.6)
ax.set_xscale('log')
ax.set_xlim(0.6, 1200)
ax.set_xticks([1, 3, 10, 30, 100, 300, 1000])
ax.set_xticklabels(['1', '3', '10', '30', '100', '300', '1000'])
ax.set_xlabel('Population whose 60-min status changes (millions, log scale)')
ax.set_title('a  985 million people (28.6%) change status\nunder one road-inclusion rule', loc='left')
ax.text(0.40, 0.04, 'red = eight largest\n(IND 582 M, NGA 73 M, BGD 49 M)', transform=ax.transAxes,
        ha='left', fontsize=6.5, bbox=dict(fc='white', ec=C['grey'], lw=0.4, alpha=0.95))
ax = axes[1]
ax.scatter([100 * conn[k] for k, _ in sub], [v for _, v in sub], s=22, color=C['blue'])
ax.set_xlabel('Share of nodes in largest connected component (%)')
ax.set_xlim(20, 105)
ax.set_ylabel('Population with changed status (%)')
ax.set_title('b  Status changes concentrate in\nfragmented networks (r = -0.33, n = 13)', loc='left')
save(fig, 'fig5_identity_flip')

# ============ 涓诲浘 6锛氶潪闅忔満缂哄け鐨勬崯澶卞綊灞?============
S = load(r'output\experiments\nonrandom_missing_road_stress\stress_nonrandom_summary.csv')
agg = {}
for r in S:
    b = r['base']
    agg.setdefault(b, {'nr': [], 'rd': []})
    L = ff(r['loss_vs_intact_pp'])
    if L is None: continue
    agg[b]['nr' if r['is_random'] == 'False' else 'rd'].append(L)
fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.0))
fig.set_constrained_layout(True)
ax = axes[0]
keys = ['remote_local', 'rural_local', 'lowpop_local', 'rural_lowpop_local']
lbls = ['remote 50%', 'rural 44%', 'low-pop 25%', 'rural x low-pop 21%']
x = np.arange(len(keys))
ax.bar(x - 0.19, [np.mean(agg[k]['nr']) for k in keys], width=0.38, color=C['purple'], label='non-random (targeted)')
ax.bar(x + 0.19, [np.mean(agg[k]['rd']) for k in keys], width=0.38, color=C['blue'], label='same-fraction random')
ax.set_xticks(x); ax.set_xticklabels(lbls, rotation=20)
ax.set_ylabel('60-min share loss (pp)')
ax.set_title('a  Selective missing data lose less in total', loc='left')
ax.legend(loc='upper right', frameon=False, fontsize=6.5, ncol=1)
ax = axes[1]
d = [np.mean(agg[k]['nr']) - np.mean(agg[k]['rd']) for k in keys]
ax.barh(np.arange(len(keys)), d, color=C['red'], height=0.5)
ax.set_yticks(np.arange(len(keys))); ax.set_yticklabels(lbls)
ax.invert_yaxis()
ax.axvline(0, color='black', lw=0.6)
ax.set_xlabel('Non-random minus random loss (pp)')
ax.set_title('b  But the loss falls on rural populations', loc='left')
ax.text(0.03, 0.06, 'selectivity lowers the aggregate loss\nby 15-23 pp; it does not lower the\nburden on the affected population',
        transform=ax.transAxes, fontsize=6.2, bbox=dict(fc='white', ec=C['grey'], lw=0.4, alpha=0.9))
save(fig, 'fig6_missing_roads')

# ============ 琛ュ厖鍥?S22锛氱疆鎹㈤浂妯″瀷锛堟洿鏂帮級 ============
perm = load(r'output\experiments\direction_law_v2\direction_law_permutation.csv')
fig, axes = plt.subplots(1, 2, figsize=(7.0, 2.9))
fig.set_constrained_layout(True)
ax = axes[0]
r2 = [float(r['r2']) for r in perm if r.get('r2')]
if not r2:
    r2 = [float(v) for r in perm for k, v in r.items() if k == 'r2' and v]
ax.hist(r2, bins=40, color=C['grey'], alpha=0.75, label='permutation null (n=2000)')
ax.axvline(0.768, color=C['blue'], lw=1.6, label='observed $R^2$ = 0.768')
ax.axvline(0.810, color=C['red'], lw=1.0, ls='--', label='null mean = 0.810')
ax.set_xlabel('$R^2$ of the legacy published contrast')
ax.set_ylabel('permutation draws')
ax.set_title('a  Legacy fit is no better than\nrandom coupling', loc='left')
ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.10), frameon=False, fontsize=6.2, ncol=2)
ax = axes[1]
rr = [float(r['slope']) for r in perm if r.get('slope')]
if not rr:
    rr = [float(v) for r in perm for k, v in r.items() if k == 'slope' and v]
ax.hist(rr, bins=40, color=C['grey'], alpha=0.75)
ax.axvline(-0.817, color=C['blue'], lw=1.6, label='observed slope = -0.817')
ax.axvline(-1.002, color=C['red'], lw=1.0, ls='--', label='null mean = -1.002')
ax.set_xlabel('slope of legacy contrast ~ arterial coverage')
ax.set_ylabel('permutation draws')
ax.set_title('b  The legacy slope is milder than\nthe shuffled null', loc='left')
ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.10), frameon=False, fontsize=6.2, ncol=2)
save(fig, 'figS22_permutation_null')


# ============ 琛ュ厖鍥?S23锛氱鍙峰弽杞殑鏈哄埗鍒ゆ嵁锛坴27 鏂板锛?============
import pandas as pd
E2 = pd.read_csv(os.path.join(B, 'output', 'experiments', 'v27', 'e2_refined.csv'))
fig, axes = plt.subplots(1, 3, figsize=(9.8, 3.3), gridspec_kw={'width_ratios': [1.05, 1, 0.95]})
fig.set_constrained_layout(True)
# (a) edge vs |snap| scatter, 45-degree line = decision boundary
ax = axes[0]
ax.scatter(E2['edge'], E2['snap'].abs(), s=16,
           c=[C['red'] if v < 0 else C['blue'] for v in E2['full']])
lim = [0, 32]
ax.plot(lim, lim, color='black', lw=1.0, ls='--')
ax.set_xlim(lim); ax.set_ylim(lim)
ax.set_xlabel('Edge increment $\\Delta_{edge}$ (pp)')
ax.set_ylabel('|Capture term| (pp)')
ax.set_title('a  Sign is decided by\n$|\\Delta_{conv}| > \\Delta_{edge}$', loc='left')
ax.legend(handles=[Patch(color=C['red'], label='sign reverses'),
                   Patch(color=C['blue'], label='sign holds')],
          loc='upper center', bbox_to_anchor=(0.5, -0.20), frameon=False, fontsize=6.2, ncol=1)
ax.text(0.05, 0.92, 'above line = sign reverses (31/60)\nbelow line = sign holds (29/60)',
        transform=ax.transAxes, fontsize=6.2, va='top',
        bbox=dict(fc='white', ec=C['grey'], lw=0.4, alpha=0.95))
# (b) capture-loss rate vs snap
ax = axes[1]
rate = 100 * (E2['snap'].abs() / E2['Bs'])
ax.scatter(rate, E2['snap'], s=16, color=C['orange'])
z = np.polyfit(rate, E2['snap'], 1)
xs = np.linspace(rate.min(), rate.max(), 20)
ax.plot(xs, np.polyval(z, xs), color='black', lw=1.0, ls='--')
ax.set_xlabel('Capture-loss rate (%)')
ax.set_ylabel('$\\Delta_{conv}$ (pp)')
ax.set_title('b  Capture loss drives the\ncapture term (r = -0.98)', loc='left')
ax.legend(handles=[Patch(color=C['orange'], label='$\\Delta_{conv}$')],
          loc='upper center', bbox_to_anchor=(0.5, -0.20), frameon=False, fontsize=6.2, ncol=1)
ax.text(0.05, 0.12, '$\\Delta_{conv}$ and capture loss are\ncollinear; $\\Delta_{edge}$ is not',
        transform=ax.transAxes, fontsize=6.2,
        bbox=dict(fc='white', ec=C['grey'], lw=0.4, alpha=0.95))
# (c) baseline reach of negative vs non-negative rows
ax = axes[2]
mask = E2['full'] < 0
g_hold = E2.loc[~mask, 'A'].mean()
g_rev = E2.loc[mask, 'A'].mean()
ax.bar([0, 1], [g_hold, g_rev],
       color=[C['blue'], C['red']], width=0.55)
ax.set_xticks([0, 1])
ax.set_xticklabels(['sign holds\n(29 rows)', 'sign reverses\n(31 rows)'])
ax.set_ylabel('Arterial-only baseline reach (%)')
ax.set_title('c  Reversal occurs where the\nbaseline is already high', loc='left')
ax.legend(handles=[Patch(color=C['blue'], label='sign holds'),
                   Patch(color=C['red'], label='sign reverses')],
          loc='upper center', bbox_to_anchor=(0.5, -0.20), frameon=False, fontsize=6.2, ncol=1)
for i, v in enumerate([g_hold, g_rev]):
    ax.text(i, v + 1, '%.1f' % v, ha='center', fontsize=7)
ax.set_ylim(0, 108)
save(fig, 'figS23_sign_mechanism')
save(fig, 'fig3_sign_criterion')
print('  wrote figS23_sign_mechanism / fig3_sign_criterion')

print('all figures done')

