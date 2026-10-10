# -*- coding: utf-8 -*-
"""Probe HDX for flood/cyclone extent datasets covering the expansion countries."""
from __future__ import annotations

import json

import requests

API = 'https://data.humdata.org/api/3/action/package_search'
QUERIES = ['flood extent', 'flood water', 'cyclone track flood']
LOCATIONS = ['ind', 'idn', 'nga', 'vnm', 'per', 'egy', 'tur', 'mex', 'phl', 'pak', 'bgd']


def search(query: str, location: str, rows: int = 5) -> list[dict]:
    params = {'q': query, 'fq': f'groups:{location}', 'rows': rows, 'sort': 'metadata_modified desc'}
    try:
        r = requests.get(API, params=params, timeout=60)
    except Exception as exc:  # pragma: no cover
        return [{'error': str(exc)}]
    if r.status_code != 200:
        return [{'error': f'http {r.status_code}'}]
    out = []
    for pkg in r.json().get('result', {}).get('results', []):
        resources = [res for res in pkg.get('resources', [])
                     if str(res.get('format', '')).lower() in {'shp', 'zip', 'geojson', 'gpkg'}]
        out.append({'title': pkg.get('title'), 'org': (pkg.get('organization') or {}).get('title'),
                    'modified': pkg.get('metadata_modified', '')[:10],
                    'n_resources': len(resources),
                    'first_resource': resources[0]['url'] if resources else '',
                    'resource_name': resources[0].get('name', '') if resources else ''})
    return out


def main() -> None:
    for loc in LOCATIONS:
        print(f'=== {loc} ===')
        seen = set()
        for q in QUERIES:
            for hit in search(q, loc, rows=4):
                key = hit.get('title')
                if not key or key in seen:
                    continue
                seen.add(key)
                print(f"  {hit.get('modified')} | {hit.get('org')} | {key} | {hit.get('resource_name')}")
                if hit.get('first_resource'):
                    print(f"      {hit['first_resource'][:130]}")
        if not seen:
            print('  no datasets found')


if __name__ == '__main__':
    main()
