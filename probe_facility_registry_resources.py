# -*- coding: utf-8 -*-
"""List concrete download resources for candidate official facility registries.

Covers the three usable provider families found by ``resolve_official_facility_sources.py``:
Healthsites per-country packages, OCHA ROAP facility layers and the HDX Sub-Saharan
Africa health-facility compilation.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent
EXP = ROOT / 'output/experiments/experiment_29_global_expansion'
API = 'https://data.humdata.org/api/3/action/package_search'
TARGETS = ['NGA', 'TZA', 'ZMB', 'SEN', 'MLI', 'KHM', 'IDN', 'NPL', 'LKA', 'IND']
QUERIES = [('health', 'health facilities'), ('education', 'education facilities')]
KEEP_FORMATS = {'csv', 'geojson', 'shp', 'gpkg', 'xlsx', 'zip', 'gdb'}


def search(query: str, location: str | None, rows: int = 20) -> list[dict]:
    params = {'q': query, 'rows': rows, 'sort': 'metadata_modified desc'}
    if location:
        params['fq'] = f'groups:{location}'
    try:
        r = requests.get(API, params=params, timeout=60)
    except Exception:
        return []
    if r.status_code != 200:
        return []
    return r.json().get('result', {}).get('results', [])


def main() -> None:
    sample = pd.read_csv(EXP / 'country_sample_and_input_availability.csv')
    rows = []
    # 1. sub-Saharan health-facility compilation (one package, many countries)
    for pkg in search('Health Facilities in Sub-Saharan Africa', None, rows=10):
        if 'sub-saharan' in (pkg.get('title') or '').lower():
            for res in pkg.get('resources', []):
                fmt = str(res.get('format', '')).lower()
                if fmt not in KEEP_FORMATS:
                    continue
                rows.append({'iso3': 'SSA', 'service': 'health',
                             'package_title': pkg.get('title'),
                             'organization': (pkg.get('organization') or {}).get('title'),
                             'resource_name': res.get('name'), 'format': fmt,
                             'size_bytes': res.get('size'), 'url': res.get('url')})
    # 2. per-country healthsites / OCHA facility layers
    for iso in TARGETS:
        country = sample.loc[sample.iso3 == iso, 'country'].iloc[0]
        for kind, query in QUERIES:
            for loc in (iso.lower(), country.lower().replace(' ', '-')):
                for pkg in search(query, loc, rows=12):
                    org = ((pkg.get('organization') or {}).get('title') or '').lower()
                    title = (pkg.get('title') or '').lower()
                    if not any(k in f'{org} {title}' for k in ('healthsite', 'ochа', 'ocha',
                                                              'facilit', 'ministry', 'unicef',
                                                              'health', 'school')):
                        continue
                    for res in pkg.get('resources', []):
                        fmt = str(res.get('format', '')).lower()
                        if fmt not in KEEP_FORMATS:
                            continue
                        rows.append({'iso3': iso, 'service': kind,
                                     'package_title': pkg.get('title'),
                                     'organization': (pkg.get('organization') or {}).get('title'),
                                     'resource_name': res.get('name'), 'format': fmt,
                                     'size_bytes': res.get('size'), 'url': res.get('url')})
                if any(r['iso3'] == iso for r in rows):
                    break
        print(f'{iso} done', flush=True)
    df = pd.DataFrame(rows).drop_duplicates(subset=['iso3', 'service', 'url'])
    OUT = EXP / 'facility_registry_resources.csv'
    df.to_csv(OUT, index=False, encoding='utf-8-sig')
    pd.set_option('display.width', 240)
    pd.set_option('display.max_colwidth', 55)
    pd.set_option('display.max_rows', 80)
    print(f'wrote {OUT} ({len(df)} resources)')
    print(df[['iso3', 'service', 'organization', 'resource_name', 'format', 'size_bytes']]
          .to_string(index=False))


if __name__ == '__main__':
    main()
