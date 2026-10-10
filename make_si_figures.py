# -*- coding: utf-8 -*-
"""Generate Supplementary Figures S1-S10 for paper-v3-SI.docx.

All panels are built from the project's own derived tables, so every SI figure is
reproducible from the deposited data.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
EXP = ROOT / 'output/experiments/experiment_29_global_expansion'
OUT = ROOT / 'figures/si'

plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 7.5, 'axes.titlesize': 8.5,
                     'axes.titleweight': 'bold', 'axes.labelsize': 7.5, 'axes.spines.top': False,
                     'axes.spines.right': False, 'figure.dpi': 160, 'savefig.dpi': 300})


def save(fig, name):
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / f'{name}.png', bbox_inches='tight')
    fig.savefig(OUT / f'{name}.pdf', bbox_inches='tight')
    plt.close(fig)
    print('saved', name)


def sensitivity_table() -> pd.DataFrame:
    core = pd.read_csv(ROOT / 'output/experiments/core_recheck/core_weight_length_sensitivity.csv')
    add = pd.read_csv(EXP / 'weight_length_sensitivity.csv')
    d = pd.concat([core, add], ignore_index=True)
    wide = d.pivot_table(index=['iso3', 'service'], columns='variant',
                         values=['share_30min_pct', 'share_60min_pct']).reset_index()
    wide.columns = [f'{a}_{b}' for a, b in wide.columns]
    wide = wide.rename(columns={'iso3_': 'iso3', 'service_': 'service'})
    wide['pop_effect_60'] = wide.share_60min_pct_counts_mercator_none - wide.share_60min_pct_density_mercator_none
    wide['length_effect_60'] = wide.share_60min_pct_density_geodesic_none - wide.share_60min_pct_density_mercator_none
    wide['length_effect_30'] = wide.share_30min_pct_density_geodesic_none - wide.share_30min_pct_density_mercator_none
    return wide


def fig_s1():
    d = sensitivity_table()
    fig, axs = plt.subplots(1, 2, figsize=(7.6, 3.4))
    ax = axs[0]
    d2 = d.reindex(d.length_effect_60.abs().sort_values().index).tail(18)
    y = np.arange(len(d2))
    ax.barh(y - .18, d2.length_effect_60, height=.34, color='#fdae6b', label='60 min')
    ax.barh(y + .18, d2.length_effect_30, height=.34, color='#8c6bb1', label='30 min')
    ax.set_yticks(y)
    ax.set_yticklabels(d2.iso3 + ' ' + d2.service.str[:4], fontsize=5)
    ax.axvline(0, color='black', lw=.6)
    ax.set_xlabel('Effect on access (pp)')
    ax.set_title('a  Length metric (Mercator vs geodesic)')
    ax.legend(frameon=False, fontsize=6)
    ax = axs[1]
    d3 = d.reindex(d.pop_effect_60.abs().sort_values().index).tail(18)
    ax.barh(np.arange(len(d3)), d3.pop_effect_60, color='#3182bd')
    ax.set_yticks(np.arange(len(d3)))
    ax.set_yticklabels(d3.iso3 + ' ' + d3.service.str[:4], fontsize=5)
    ax.axvline(0, color='black', lw=.6)
    ax.set_xlabel('Effect on 60-min access (pp)')
    ax.set_title('b  Population units (density vs counts)')
    save(fig, 'figS1_measurement_sensitivity')


def fig_s2():
    f = pd.read_csv(ROOT / 'output/experiments/facility_scenarios'
                    / 'facility_scenario_shares.csv')
    h = f[f.service == 'health'].pivot_table(index='iso3', columns='scenario',
                                             values='share_60min_pct')
    h['level_penalty'] = h.hospital_clinic - h.hospital_only
    h['points_gain'] = h.all_health_points - h.hospital_clinic
    h = h.sort_values('level_penalty')
    fig, ax = plt.subplots(figsize=(7.6, 3.6))
    y = np.arange(len(h))
    ax.barh(y - .18, h.level_penalty, height=.34, color='#6a51a3',
            label='Hospital only vs hospital+clinic')
    ax.barh(y + .18, h.points_gain, height=.34, color='#41ab5d',
            label='All mapped health points vs hospital+clinic')
    ax.set_yticks(y)
    ax.set_yticklabels(h.index, fontsize=5)
    ax.axvline(0, color='black', lw=.6)
    ax.set_xlabel('Difference in 60-min access (pp)')
    ax.set_title('Facility-definition sensitivity (30 countries)')
    ax.legend(frameon=False, fontsize=6, loc='lower right')
    save(fig, 'figS2_facility_definitions')


def fig_s3():
    r = pd.read_csv(ROOT / 'output/experiments/facility_registry'
                    / 'facility_registry_bottleneck.csv')
    fig, ax = plt.subplots(figsize=(4.2, 3.6))
    colors = ['#08519c' if s == 'health' else '#238b45' for s in r.service]
    ax.scatter(r.share_60min_osm_counts, r.share_60min_union_counts, s=28, c=colors,
               linewidths=0)
    lim = [55, 102]
    ax.plot(lim, lim, '--', color='black', lw=.8)
    ax.set_xlim(lim); ax.set_ylim(lim)
    for _, row in r.iterrows():
        ax.annotate(row.iso3, (row.share_60min_osm_counts, row.share_60min_union_counts),
                    textcoords='offset points', xytext=(3, 3), fontsize=5)
    ax.set_xlabel('OSM/HOT facilities only (%)')
    ax.set_ylabel('With independent registry (%)')
    ax.set_title('Facility-registry correction (12 cases)')
    ax.text(.03, .95, 'blue = health, green = education', transform=ax.transAxes,
            va='top', fontsize=6)
    save(fig, 'figS3_registry_cases')


def fig_s4():
    d = pd.read_csv(ROOT / 'output/experiments/grip4_completeness'
                    / 'grip4_vs_network_density.csv')
    # grip_over_model_density = GRIP4 density (m/km2) / model density (km/km2),
    # i.e. 1000x the dimensionless GRIP4/model ratio. Report model/GRIP4 instead.
    d['model_over_grip4'] = 1000.0 / d.grip_over_model_density
    fig, ax = plt.subplots(figsize=(4.4, 3.4))
    ax.scatter(d.model_over_grip4, d.benchmark_gap_pp, s=20, color='#8c6bb1',
               linewidths=0)
    for _, row in d.iterrows():
        if abs(row.benchmark_gap_pp) > 12 or row.model_over_grip4 > 8:
            ax.annotate(row.iso3, (row.model_over_grip4, row.benchmark_gap_pp),
                        textcoords='offset points', xytext=(3, 3), fontsize=5)
    ax.axhline(0, color='grey', lw=.7)
    rho = d.model_over_grip4.corr(d.benchmark_gap_pp, method='spearman')
    ax.set_xlabel('Model network density / GRIP4 density')
    ax.set_ylabel('MAP benchmark gap (pp)')
    ax.set_title('Independent road inventory cross-check')
    ax.text(.48, .06, f'Spearman rho = {rho:+.2f} (n={len(d)})', transform=ax.transAxes,
            fontsize=6.5)
    save(fig, 'figS4_grip4_crosscheck')


def fig_s5():
    d = pd.read_csv(ROOT / 'output/experiments/jrc_flood_exposure'
                    / 'jrc_100y_exposure_30countries.csv')
    fig, axs = plt.subplots(1, 2, figsize=(7.6, 3.4))
    ax = axs[0]
    ax.scatter(d.population_exposed_pct, d.network_exposed_pct, s=20, color='#08519c',
               linewidths=0)
    for _, row in d.iterrows():
        if row.network_exposed_pct > 10 or row.population_exposed_pct > 30:
            ax.annotate(row.iso3, (row.population_exposed_pct, row.network_exposed_pct),
                        textcoords='offset points', xytext=(3, 3), fontsize=5)
    ax.set_xlabel('Population exposed to 100-yr flood (%)')
    ax.set_ylabel('Network exposed (%)')
    ax.set_title('a  JRC 100-year exposure')
    ax = axs[1]
    top = d.sort_values('unpaved_exposed_pct_of_network').tail(12)
    ax.barh(np.arange(len(top)), top.unpaved_exposed_pct_of_network, color='#d94801')
    ax.set_yticks(np.arange(len(top)))
    ax.set_yticklabels(top.iso3, fontsize=5.5)
    ax.set_xlabel('Exposed unpaved roads (% of network)')
    ax.set_title('b  Unpaved exposure')
    save(fig, 'figS5_jrc_exposure')


def fig_s6():
    d = pd.read_csv(ROOT / 'output/experiments/shdi_30countries'
                    / 'shdi_access_correlations_26countries.csv').dropna(
        subset=['population_weighted_pearson'])
    fig, axs = plt.subplots(1, 2, figsize=(7.6, 4.4), sharex=True)
    for ax, (svc, slab, color) in zip(axs, (('health', 'Health', '#08519c'),
                                            ('education', 'Education', '#238b45'))):
        s = d[d.service == svc].sort_values('population_weighted_pearson')
        ax.barh(np.arange(len(s)), s.population_weighted_pearson, color=color)
        ax.set_yticks(np.arange(len(s)))
        ax.set_yticklabels(s.iso3, fontsize=6)
        ax.axvline(0, color='black', lw=.7)
        ax.set_xlim(-1.0, 1.02)
        ax.set_xlabel('SHDI-access correlation (2020)')
        ax.set_title(f'{"ab"[svc == "education"]}  {slab} (n={len(s)})')
    fig.suptitle('Population-weighted subnational development gradient, 26 countries',
                 fontsize=8.5, fontweight='bold')
    save(fig, 'figS6_shdi_gradients')


def fig_s7():
    d = pd.read_csv(ROOT / 'output/experiments/capacity_access'
                    / 'capacity_attribute_coverage.csv')
    fig, ax = plt.subplots(figsize=(4.4, 3.2))
    x = np.arange(len(d))
    ax.bar(x - .2, d.beds_recorded_pct, width=.4, color='#08519c', label='Beds recorded')
    ax.bar(x + .2, d.staff_recorded_pct, width=.4, color='#238b45', label='Staff recorded')
    ax.set_xticks(x)
    ax.set_xticklabels(d.iso3, fontsize=6)
    ax.set_ylabel('Share of facility records (%)')
    ax.set_title('Capacity attributes in open data')
    ax.legend(frameon=False, fontsize=6)
    save(fig, 'figS7_capacity_coverage')


def fig_s8():
    d = pd.read_csv(ROOT / 'output/experiments/experiment_22_monte_carlo'
                    / 'monte_carlo_intervals.csv')
    d = d[d.scenario.eq('baseline')].copy()
    d['lo'] = d['share_within_60min_pct_p2_5']
    d['hi'] = d['share_within_60min_pct_p97_5']
    d['mid'] = (d.lo + d.hi) / 2
    d = d.sort_values('mid')
    fig, ax = plt.subplots(figsize=(7.6, 3.4))
    y = np.arange(len(d))
    ax.hlines(y, d.lo, d.hi, color='#9ecae1', lw=3)
    ax.scatter(d.mid, y, s=16, color='#08519c', zorder=3)
    ax.set_yticks(y)
    ax.set_yticklabels(d.iso3 + ' ' + d.service.str[:4], fontsize=5)
    ax.set_xlabel('60-min access, 2.5th-97.5th percentile (%)')
    ax.set_title('Monte Carlo uncertainty (baseline scenarios)')
    save(fig, 'figS8_monte_carlo')


def fig_s9():
    d = pd.read_csv(ROOT / 'output/experiments/experiment_19_21_south_sofala_noded'
                    / 'south_sofala_noded_investment_summary.csv')
    d = d[d.strategy.eq('population_dependency')]
    # restoration rows report the gain against the hazard-before state; the
    # paving/budget experiments report it in access_gain60_pp.
    d['gain'] = d.access_gain60_pp.fillna(d.restored60_minus_hazard_before_pp)
    fig, ax = plt.subplots(figsize=(5.0, 3.4))
    styles = {('restoration', 'hazard'): ('#08519c', 'o'),
              ('paving_fraction', 'hazard'): ('#d94801', 's'),
              ('paving_fraction', 'baseline'): ('#238b45', '^')}
    for (exp, scen), (color, marker) in styles.items():
        sub = d[(d.experiment == exp) & (d.scenario == scen)].sort_values('fraction')
        for svc, ls, slab in (('health', '-', 'health'), ('school', '--', 'education')):
            s2 = sub[sub.service == svc]
            if len(s2):
                ax.plot(s2.fraction * 100, s2.gain, ls, color=color, marker=marker,
                        ms=3, label=f'{exp} {scen} {slab}')
    ax.set_xlabel('Budget / length fraction (%)')
    ax.set_ylabel('60-min access gain (pp)')
    ax.set_title('Intervention returns, noded South Sofala')
    ax.legend(frameon=False, fontsize=4.5, ncol=2)
    save(fig, 'figS9_intervention_curves')


def fig_s10():
    d = pd.read_csv(ROOT / 'output/experiments/benchmark_validation'
                    / 'map_health_travel_time_vs_model.csv').dropna(
        subset=['model_share_60min_corrected'])
    fig, ax = plt.subplots(figsize=(4.6, 3.6))
    ax.scatter(d.benchmark_share_60min_pct, d.model_share_60min_corrected, s=20,
               color='#08519c', linewidths=0)
    lim = [25, 105]
    ax.plot(lim, lim, '--', color='black', lw=.8)
    ax.set_xlim(lim); ax.set_ylim(lim)
    for _, row in d.iterrows():
        if abs(row.model_share_60min_corrected - row.benchmark_share_60min_pct) > 8:
            ax.annotate(row.iso3, (row.benchmark_share_60min_pct, row.model_share_60min_corrected),
                        textcoords='offset points', xytext=(3, 3), fontsize=5)
    ax.set_xlabel('MAP 2020 travel time, 60-min share (%)')
    ax.set_ylabel('This model (%)')
    r = d.benchmark_share_60min_pct.corr(d.model_share_60min_corrected)
    rho = d.benchmark_share_60min_pct.corr(d.model_share_60min_corrected, method='spearman')
    ax.set_title('Independent benchmark, 30 countries')
    ax.text(.03, .05, f'r = {r:.2f}, rho = {rho:.2f}, n = {len(d)}', transform=ax.transAxes,
            fontsize=6.5)
    save(fig, 'figS10_map_benchmark')


if __name__ == '__main__':
    for fn in (fig_s1, fig_s2, fig_s3, fig_s4, fig_s5, fig_s6, fig_s7, fig_s8, fig_s9, fig_s10):
        try:
            fn()
        except Exception as exc:
            print(f'{fn.__name__} failed: {type(exc).__name__} {exc}')
