# -*- coding: utf-8 -*-
"""Download Meta/Facebook "Map With AI" AI-predicted road exports.

The dataset is Meta's satellite-derived road inventory: roads that a deep
learning model predicted from Maxar Premium imagery and that are missing from
OpenStreetMap.  Country exports are provided as gzip-compressed GeoPackages
hosted on ``rapideditor.org`` (see
``facebookmicrosites/Open-Mapping-At-Facebook`` wiki).

This is the actual downloadable Meta road product; the name "RADD" in common
use refers to the unrelated RADD forest-disturbance alerts, and the PyPI
``radd`` package is a cognitive-modelling library, neither of which is a road
inventory.

Downloads are kept in ``data/external/mapwithai/`` as ``*.gpkg.tar.gz``.
"""
from __future__ import annotations

import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[2]
DEST = ROOT / 'data/external/mapwithai'
CELLS = ROOT / 'output/experiments/mapwithai_crosscheck/ai_cells'

COUNTRIES = {
    'KHM': 'KH', 'GTM': 'GT', 'BGD': 'BD', 'SEN': 'SN', 'NGA': 'NG',
    'ETH': 'ET', 'MOZ': 'MZ', 'PNG': 'PG', 'EGY': 'EG', 'TUR': 'TR',
}


def download(iso: str, cc: str) -> tuple[str, str]:
    name = f'{cc}_mapwithai_road_data.gpkg.tar.gz'
    dest = DEST / name
    if dest.exists() and dest.stat().st_size > 0:
        return iso, 'cached'
    url = f'https://rapideditor.org/country_exports/{name}'
    tmp = dest.with_suffix(dest.suffix + '.part')
    for attempt in range(1, 6):
        try:
            with requests.get(url, stream=True, timeout=(30, 120)) as r:
                r.raise_for_status()
                total = int(r.headers.get('content-length') or 0)
                done = 0
                last = time.time()
                with tmp.open('wb') as f:
                    for chunk in r.iter_content(chunk_size=1 << 20):
                        if chunk:
                            f.write(chunk)
                            done += len(chunk)
                            now = time.time()
                            if now - last > 30:
                                print(f'  {iso}: {done/1e6:.0f}/{total/1e6:.0f} MB',
                                      flush=True)
                                last = now
            if total and abs(done - total) > 1:
                raise IOError(f'short download {done} != {total}')
            tmp.replace(dest)
            return iso, f'{dest.stat().st_size / 1e6:.0f} MB'
        except Exception as exc:  # noqa: BLE001
            tmp.unlink(missing_ok=True)
            if attempt == 5:
                return iso, f'ERROR {type(exc).__name__}: {exc}'
            print(f'  {iso}: retry {attempt} ({type(exc).__name__})', flush=True)
            time.sleep(5 * attempt)
    return iso, 'ERROR unknown'


def main() -> None:
    DEST.mkdir(parents=True, exist_ok=True)
    # Sequential downloads: rapiditor.org stalls when several large exports are
    # requested concurrently, so fetch one at a time.
    for iso, cc in COUNTRIES.items():
        if (CELLS / f'{iso}_cells.csv').exists():
            print(f'{iso}: already processed, skip', flush=True)
            continue
        print(f'{iso}: {download(iso, cc)[1]}', flush=True)
    print('download phase done', flush=True)


if __name__ == '__main__':
    main()
