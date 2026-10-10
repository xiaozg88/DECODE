# -*- coding: utf-8 -*-
"""Check which expansion additions have a genuinely independent facility registry.

Healthsites is OSM-derived (its CSV carries ``osm_id``), so it cannot serve as an
independent registry.  The plausible independent providers are Giga (UNICEF/ITU school
geolocation compiled with ministries) and OCHA/partner facility layers.  This script
records their country coverage across the 23 additions.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent
EXP = ROOT / 'output/experiments/experiment_29_global_expansion'
API = 'https://data.humdata.org/api/3/action/package_search'
ADDITIONS = ['EGY', 'GEO', 'GHA', 'GTM', 'HND', 'IDN', 'IND', 'JOR', 'KGZ', 'KHM', 'LKA',
             'MEX', 'MLI', 'NGA', 'NPL', 'PER', 'PNG', 'RWA', 'SEN', 'TUR', 'TZA', 'VNM', 'ZMB']


def search(query: str, location: str, rows: int = 20) -> list[dict]:
    try:
        r = requests.get(API, params={'q': query, 'fq': f'groups:{location}', 'rows': rows,
                                      'sort': 'metadata_modified desc'}, timeout=60)
    except Exception:
        return []
    return r.json().get('result', {}).get('results', []) if r.status_code == 200 else []


def main() -> None:
    sample = pd.read_csv(EXP / 'country_sample_and_input_availability.csv')
    rows = []
    for iso in ADDITIONS:
        country = sample.loc[sample.iso3 == iso, 'country'].iloc[0]
        for loc in (iso.lower(), country.lower().replace(' ', '-')):
            for query in ('school geolocation', 'education facilities', 'health facilities'):
                for pkg in search(query, loc):
                    org = ((pkg.get('organization') or {}).get('title') or '')
                    title = pkg.get('title') or ''
                    blob = f'{org} {title}'.lower()
                    independent = ('giga' in blob or 'ocha' in blob or 'ministry' in blob
                                   or 'unicef' in blob) and 'healthsite' not in blob
                    if not independent:
                        continue
                    for res in pkg.get('resources', []):
                        fmt = str(res.get('format', '')).lower()
                        if fmt not in {'csv', 'shp', 'geojson', 'gpkg', 'zip', 'xlsx'}:
                            continue
                        rows.append({'iso3': iso, 'organization': org, 'package_title': title,
                                     'resource_name': res.get('name'), 'format': fmt,
                                     'size_bytes': res.get('size'), 'url': res.get('url')})
            if any(r['iso3'] == iso for r in rows):
                break
        print(f'{iso}: {sum(1 for r in rows if r["iso3"] == iso)} resources', flush=True)
    df = pd.DataFrame(rows).drop_duplicates(subset=['iso3', 'url'])
    OUT = EXP / 'independent_facility_registries.csv'
    df.to_csv(OUT, index=False, encoding='utf-8-sig')
    pd.set_option('display.width', 240)
    pd.set_option('display.max_colwidth', 60)
    pd.set_option('display.max_rows', 100)
    print(f'wrote {OUT} ({len(df)} resources, {df.iso3.nunique() if len(df) else 0} countries)')
    if len(df):
        print(df[['iso3', 'organization', 'package_title', 'resource_name', 'format']].to_string(index=False))
        print('coverage:', sorted(df.iso3.unique()))
        print('missing:', sorted(set(ADDITIONS) - set(df.iso3.unique())))


if __name__ == '__main__':
    main()
