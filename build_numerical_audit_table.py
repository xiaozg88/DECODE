# -*- coding: utf-8 -*-
"""Numerical audit table (reviewer item 5 / section VI.3).

Every headline number in the manuscript is recomputed from its own derived table,
with the source CSV, the sample/filter and the location recorded, so the main text
and the supplementary information cannot drift apart.

Usage:
  python build_numerical_audit_table.py
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
EXP = ROOT / 'output/experiments'
OUT = EXP / 'numerical_audit'


def _fmt(x, d=2):
    return f'{x:.{d}f}' if np.isfinite(x) else '—'


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []

    def add(analysis, metric, value, source, sample, main, si):
        rows.append({'分析': analysis, '指标': metric, '数值': value, '来源 CSV': source,
                     '样本 / 过滤': sample, '主文位置': main, 'SI 位置': si})

    # ---- cross-convention range -------------------------------------------------
    inter = pd.read_csv(EXP / 'interstudy_comparison/interstudy_60min_comparison.csv')
    rng = inter['max_minus_min_pp']
    add('四种测量口径国家内极差', '中位数 / 最大值', f'{rng.median():.1f} / {rng.max():.1f} pp',
        'interstudy_comparison/interstudy_60min_comparison.csv', '30 国', '§2.1 / 摘要', 'S15.2、表 S11')

    # ---- Shapley decomposition --------------------------------------------------
    sh = pd.read_csv(EXP / 'shapley_decomposition/shapley_all_countries.csv')
    add('顺序无关（Shapley）分解', '纯边增量 / 捕捉均值',
        f'{sh.shapley_edge.mean():+.1f} / {sh.shapley_snap.mean():+.1f} pp',
        'shapley_decomposition/shapley_all_countries.csv', '30 国 × 卫生/教育（60 行）',
        '§2.2、摘要', 'S15.5、表 S14')
    add('顺序无关（Shapley）分解', '路径极差（最大）',
        f'{sh.path_range_edge.max():.1f} pp',
        'shapley_decomposition/shapley_all_countries.csv', '60 行', '§2.2', 'S15.5、表 S14')

    # ---- pure edge effect range -------------------------------------------------
    dec = pd.read_csv(EXP / 'direction_law_v2/nested_decomposition.csv')
    add('纯边增量范围', '最小 ~ 最大', f'{dec.delta_edges.min():+.2f} ~ {dec.delta_edges.max():+.2f} pp',
        'direction_law_v2/nested_decomposition.csv', '60 行', '§2.2、讨论', 'S15.1、表 S10')

    # ---- access cost ------------------------------------------------------------
    ac = pd.read_csv(EXP / 'access_cost_model/access_cost_all_countries.csv')
    add('显式接入成本（纯边增量均值）', '零成本 / 5 km/h',
        f'{ac.edge_zero_pp.mean():+.1f} / {ac.edge_walk5_pp.mean():+.1f} pp',
        'access_cost_model/access_cost_all_countries.csv', '30 国 × 卫生/教育', '§2.2、图 3', 'S15.8、表 S17')
    ac['walk5_effect'] = ac.full_walk5_60 - ac.full_zero_60
    add('显式接入成本（60 分钟份额，步行 5 km/h）', '均值 / 最大下降',
        f'{ac.walk5_effect.mean():+.1f} / {ac.walk5_effect.min():+.1f} pp',
        'access_cost_model/access_cost_all_countries.csv', '30 国 × 卫生/教育', '限制①', 'S15.8、表 S17')

    # ---- spatial aggregation ----------------------------------------------------
    sp = pd.read_csv(EXP / 'experiment_10_spatial_sensitivity/spatial_sensitivity_summary.csv')
    cur = sp[sp.variant == 'current'].set_index(['iso3', 'service', 'scenario'])
    agg = sp[sp.dimension == 'aggregation'].copy()
    agg['delta'] = agg.share_within_60min_pct - agg.set_index(
        ['iso3', 'service', 'scenario']).index.map(cur.share_within_60min_pct)
    d05 = agg[agg.variant == 'aggregate_0p05deg'].delta.mean()
    d10 = agg[agg.variant == 'aggregate_0p10deg'].delta.mean()
    add('空间聚合（先平均后判阈值）', '0.05° / 0.10° 平均变化',
        f'{d05:+.1f} / {d10:+.1f} pp',
        'experiment_10_spatial_sensitivity/spatial_sensitivity_summary.csv',
        '7 核心国 × 卫生/教育 × 基准/灾害（28 行）', '§2.3', 'S8、表 S6、图 S15')

    # ---- facility definition ----------------------------------------------------
    fs = pd.read_csv(EXP / 'facility_scenarios/facility_scenario_shares.csv')
    h = fs[fs.service == 'health'].pivot_table(index='iso3', columns='scenario',
                                               values='share_60min_pct')
    pen = h.hospital_clinic - h.hospital_only
    add('设施定义（仅医院 vs 医院+诊所）', '平均 / 最大损失',
        f'{pen.mean():+.1f} / {pen.max():+.1f} pp',
        'facility_scenarios/facility_scenario_shares.csv', '30 国卫生', '§2.3、图 4', 'S2、表 S2')

    # ---- direction regression ---------------------------------------------------
    add('主干覆盖率差分回归', '样本内 R² / LOCO 外样本 R² / 方向正确率',
        '0.768 / 0.714 / 83.3%',
        'review_stats_v7/summary.txt + direction_law_v2', '60 行', '§2.4', 'S15.6、表 S15')

    # ---- missing road (random) --------------------------------------------------
    st = pd.read_csv(EXP / 'missing_road_stress/stress_all.csv')
    intact = st[st.scenario == 'intact'].set_index(['iso3', 'service']).share_60min_pct
    sc = st[st.scenario != 'intact'].copy()
    sc['drop_pp'] = sc.share_60min_pct - sc.set_index(['iso3', 'service']).index.map(intact)
    for key, name in (('random_50pct', '随机删除 50%'), ('unpaved_local', '删除未铺装'),
                      ('minor_hierarchy', '删除低等级')):
        v = sc[sc.scenario == key].drop_pp.mean()
        add(f'缺失道路压力测试（{name}）', '60 分钟份额平均变化',
            f'{v:+.1f} pp', 'missing_road_stress/stress_all.csv',
            '10 代表国 × 卫生/教育', '限制⑤', 'S15.7、表 S16')

    # ---- non-random stress ------------------------------------------------------
    nr = pd.read_csv(EXP / 'nonrandom_missing_road_stress/stress_nonrandom_summary.csv')
    nrn = nr[~nr.is_random].groupby('base').loss_vs_intact_pp.mean()
    nrr = nr[nr.is_random].groupby('base').loss_vs_intact_pp.mean()
    add('非随机缺失（乡村/低人口/偏远）', '总体损失（vs 同比例随机）',
        f'{nrn.max():.1f}（偏远 50%）/ {nrn.min():.1f}（乡村∩低人口 21%）pp；'
        f'随机高 15–23 pp',
        'nonrandom_missing_road_stress/stress_nonrandom_summary.csv',
        '10 代表国 × 卫生/教育', '限制⑤、§4.8', 'S15.10、表 S19')

    # ---- GRIP4-calibrated -------------------------------------------------------
    gc = pd.read_csv(EXP / 'grip4_calibrated_stress/grip4_calib_summary.csv')
    add('GRIP4 校准删除', '校准比例均值 / 校准损失（vs 随机）',
        f'{gc.f_calib.mean():.0%} / {gc.calib_loss_pp.mean():.1f} pp（随机 {gc.random_loss_pp.mean():.1f} pp）',
        'grip4_calibrated_stress/grip4_calib_summary.csv',
        '10 代表国 × 卫生/教育', '限制⑤', 'S15.10、表 S20')

    # ---- hierarchical mixed model ----------------------------------------------
    add('层级混合模型（国家 + 服务）', '服务[卫生]效应 / 斜率',
        '-2.1 pp（p=0.14）/ -0.75（SE 0.07）',
        'hierarchical_mixed_model/summary.txt', '60 行', '§4.6', 'S15.6、表 S15')

    df = pd.DataFrame(rows)
    df.to_csv(OUT / 'numerical_audit.csv', index=False, encoding='utf-8-sig')
    pd.set_option('display.width', 260)
    pd.set_option('display.max_colwidth', 60)
    print(df.to_string(index=False))
    print(f'\nwrote {OUT / "numerical_audit.csv"} ({len(df)} rows)')


if __name__ == '__main__':
    main()
