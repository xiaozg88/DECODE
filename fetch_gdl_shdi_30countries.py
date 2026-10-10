# -*- coding: utf-8 -*-
"""Stage 3: build the subnational SHDI table for all 30 sample countries.

The Global Data Lab table page accepts a ``countries=ISO3`` filter, so the 30 sample
countries can be fetched one request at a time and parsed with the project's existing
parser (`run_experiment_16_socioeconomic.parse_gdl_shdi`).

Writes ``data/external/socioeconomic/gdl/shdi_table_30countries.json``.
"""
from __future__ import annotations

import json
import re
import time
from pathlib import Path

import pandas as pd
import requests

import run_experiment_16_socioeconomic as old16

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'data/external/socioeconomic/gdl/shdi_table_30countries.json'
URL = 'https://globaldatalab.org/shdi/table/shdi/?countries={iso}'
COUNTRIES = ['PAK', 'MOZ', 'BGD', 'ETH', 'KEN', 'COL', 'PHL', 'EGY', 'GEO', 'GHA', 'GTM',
             'HND', 'IDN', 'IND', 'JOR', 'KGZ', 'KHM', 'LKA', 'MEX', 'MLI', 'NGA', 'NPL',
             'PER', 'PNG', 'RWA', 'SEN', 'TUR', 'TZA', 'VNM', 'ZMB']


def main() -> None:
    tables = {}
    for iso in COUNTRIES:
        for attempt in range(3):
            try:
                r = requests.get(URL.format(iso=iso), timeout=90,
                                 headers={'User-Agent': 'Mozilla/5.0 (research)'})
                if r.status_code != 200:
                    raise RuntimeError(f'HTTP {r.status_code}')
                match = re.search(r'<table[^>]*>.*?</table>', r.text, re.I | re.S)
                if not match:
                    raise RuntimeError('no table')
                tables[iso] = match.group(0)
                print(f'{iso}: {len(match.group(0)) / 1000:.0f} KB', flush=True)
                break
            except Exception as exc:
                print(f'{iso}: attempt {attempt + 1} failed ({type(exc).__name__})', flush=True)
                time.sleep(4 * (attempt + 1))
        time.sleep(1.0)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({'tables': tables}, ensure_ascii=False), encoding='utf-8')
    print(f'wrote {OUT} with {len(tables)} countries')
    # parse using the project parser by temporarily pointing it at the new file
    shdi = pd.DataFrame()
    if len(tables) == 1:
        OUT.write_text(json.dumps({'table': list(tables.values())[0]}, ensure_ascii=False),
                       encoding='utf-8')
    try:
        frames = []
        for iso, html in tables.items():
            tmp = OUT.parent / f'_tmp_{iso}.json'
            tmp.write_text(json.dumps({'table': html}, ensure_ascii=False), encoding='utf-8')
            old16.SHDI_JSON = tmp
            parsed = old16.parse_gdl_shdi()
            parsed['iso3'] = iso
            frames.append(parsed)
            tmp.unlink(missing_ok=True)
        shdi = pd.concat(frames, ignore_index=True)
        shdi.to_csv(OUT.with_suffix('.csv'), index=False, encoding='utf-8-sig')
        print('parsed rows', len(shdi), 'countries', shdi.iso3.nunique(),
              'years', sorted(shdi.year.unique())[-3:])
    except Exception as exc:
        print('parse failed:', type(exc).__name__, str(exc)[:160])


if __name__ == '__main__':
    main()
