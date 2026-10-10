# -*- coding: utf-8 -*-
"""Hierarchical robustness of the direction regression (reviewer item 7).

The published delta regression ``delta_published ~ arterial_coverage`` is fitted
with (M0) a country random intercept only.  Reviewer item 7 asks whether the
conclusion survives the nested structure country > service.  We therefore add:

  * M1  country random intercept + service random effect (crossed)
  * M2  country random intercept + service fixed effect

and also report the within-service slopes.  The key result is that the service
level contributes almost nothing (service RE variance ~ 0, service FE
coefficient ~ -2.1 pp, p ~ 0.14) and the arterial-coverage slope stays strongly
negative across all specifications.

Usage:
  python run_hierarchical_mixed_model.py
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import warnings

from statsmodels.formula.api import mixedlm

ROOT = Path(__file__).resolve().parent
DEC = ROOT / 'output/experiments/direction_law_v2/nested_decomposition.csv'
OUT = ROOT / 'output/experiments/hierarchical_mixed_model'


def main() -> None:
    warnings.filterwarnings('ignore')
    OUT.mkdir(parents=True, exist_ok=True)
    d = pd.read_csv(DEC)
    lines = []

    def say(t=''):
        print(t)
        lines.append(t)

    say('=== M0: country random intercept (current) ===')
    m0 = mixedlm('delta_published ~ arterial_coverage', d, groups=d['iso3']).fit(
        reml=True, method='lbfgs')
    say(f'slope={m0.params["arterial_coverage"]:.3f} '
        f'SE={m0.bse["arterial_coverage"]:.3f} '
        f'p={m0.pvalues["arterial_coverage"]:.2e} '
        f'country SD={float(np.sqrt(m0.cov_re.iloc[0, 0])):.3f}')

    say()
    say('=== M1: country random intercept + service random effect (crossed) ===')
    try:
        m1 = mixedlm('delta_published ~ arterial_coverage', d, groups=d['iso3'],
                     vc_formula={'svc': '0 + C(service)'}).fit(
            reml=True, method='lbfgs', maxiter=200)
        say(f'slope={m1.params["arterial_coverage"]:.3f} '
            f'SE={m1.bse["arterial_coverage"]:.3f} '
            f'p={m1.pvalues["arterial_coverage"]:.2e}')
        say(f'params: { {k: round(float(v), 3) for k, v in m1.params.items()} }')
    except Exception as exc:
        say(f'M1 failed: {type(exc).__name__} {exc}')

    say()
    say('=== M2: country random intercept + service fixed effect ===')
    m2 = mixedlm('delta_published ~ arterial_coverage + C(service)', d,
                 groups=d['iso3']).fit(reml=True, method='lbfgs')
    say(f'slope={m2.params["arterial_coverage"]:.3f} '
        f'SE={m2.bse["arterial_coverage"]:.3f} '
        f'p={m2.pvalues["arterial_coverage"]:.2e} '
        f'country SD={float(np.sqrt(m2.cov_re.iloc[0, 0])):.3f}')
    say(f'service[health] effect={m2.params["C(service)[T.health]"]:.3f} '
        f'SE={m2.bse["C(service)[T.health]"]:.3f} '
        f'p={m2.pvalues["C(service)[T.health]"]:.3f}')

    say()
    say('=== within-service slopes ===')
    for svc in ('health', 'education'):
        sub = d[d.service == svc]
        b = np.polyfit(sub.arterial_coverage, sub.delta_published, 1)
        r = np.corrcoef(sub.arterial_coverage, sub.delta_published)[0, 1]
        say(f'{svc}: n={len(sub)} slope={b[0]:.3f} r={r:.3f}')

    say()
    say('=== service-level delta means ===')
    say(d.groupby('service').delta_published.agg(['mean', 'std', 'count'])
        .round(2).to_string())

    text = '\n'.join(lines)
    (OUT / 'summary.txt').write_text(text + '\n', encoding='utf-8')
    print(f'\nwrote {OUT / "summary.txt"}')


if __name__ == '__main__':
    main()
