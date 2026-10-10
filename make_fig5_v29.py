"""Generate v29 fig5_facility_definitions.png with font sizes +2."""
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'figures' / 'v29'
EXP = ROOT / 'output/experiments/experiment_29_global_expansion'
OUT.mkdir(parents=True, exist_ok=True)

plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 8.5,
                     'axes.titlesize': 9.5, 'axes.titleweight': 'bold',
                     'axes.labelsize': 8.5, 'axes.spines.top': False,
                     'axes.spines.right': False, 'figure.dpi': 160,
                     'savefig.dpi': 300})

fig, axs = plt.subplots(1, 4, figsize=(14.0, 3.6))

# (a) independent registry gains
ax = axs[0]
reg_path = ROOT / 'output/experiments/facility_registry/facility_registry_bottleneck.csv'
if reg_path.exists():
    r = pd.read_csv(reg_path).sort_values('registry_gain_60min_pp')
    labels = r.iso3 + '\n' + r.service
    colors = ['#08519c' if s == 'health' else '#238b45' for s in r.service]
    ax.barh(np.arange(len(r)), r.registry_gain_60min_pp, color=colors)
    ax.set_yticks(np.arange(len(r)))
    ax.set_yticklabels(labels, fontsize=6.5)
    ax.set_xlabel('60-min access gain from registry (pp)')
    ax.set_title('a  Facility bottleneck generalises')

# (b) measurement-convention effects
ax = axs[1]
env = pd.read_csv(ROOT / 'output/experiments/uncertainty/uncertainty_envelope_60min.csv')
env['abs_len'] = env.length_effect_pp.abs()
env = env.sort_values('abs_len').tail(15)
y = np.arange(len(env))
ax.barh(y - .18, env.length_effect_pp, height=.34, color='#fdae6b', label='Length metric')
ax.barh(y + .18, env.pop_effect_pp, height=.34, color='#3182bd', label='Population units')
ax.set_yticks(y)
ax.set_yticklabels(env.iso3 + ' ' + env.service.str[:4], fontsize=6.5)
ax.axvline(0, color='black', lw=.6)
ax.set_xlabel('Effect on 60-min access (pp)')
ax.set_title('b  Measurement conventions')
ax.legend(frameon=False, fontsize=7)

# (c) facility-tag completeness
ax = axs[2]
fq = pd.read_csv(EXP / 'facility_quality_by_country.csv')
fq = fq[(fq.raw_records > 0)].sort_values('usable_of_unique_pct')
for kind, color in (('health', '#08519c'), ('education', '#238b45')):
    sub = fq[fq.service == kind]
    ax.hist(sub.usable_of_unique_pct, bins=np.arange(0, 105, 7.5), alpha=.65,
            color=color, label=kind)
ax.set_xlabel('Usable share of unique facility records (%)')
ax.set_ylabel('Countries')
ax.set_title('c  Facility-tag completeness')
ax.legend(frameon=False, fontsize=7)

# (d) facility-level sensitivity
ax = axs[3]
scen_path = ROOT / 'output/experiments/facility_scenarios/facility_scenario_shares.csv'
if scen_path.exists():
    s = pd.read_csv(scen_path)
    s = s[s.service == 'health']
    p = s.pivot_table(index='iso3', columns='scenario', values='share_60min_pct')
    p['delta'] = p.hospital_clinic - p.hospital_only
    p = p.sort_values('delta').tail(14)
    ax.barh(np.arange(len(p)), p.delta, color='#6a51a3')
    ax.set_yticks(np.arange(len(p)))
    ax.set_yticklabels(p.index, fontsize=6.5)
    ax.set_xlabel('60-min access lost if only hospitals count (pp)')
    ax.set_title('d  Facility-level definition')

fig.tight_layout()
for ext in ('png', 'pdf'):
    fig.savefig(OUT / f'fig5_facility_definitions.{ext}', bbox_inches='tight')
plt.close(fig)
print('saved fig5_facility_definitions')
