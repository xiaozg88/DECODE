# -*- coding: utf-8 -*-
"""Review item S4: per-country OSM/HOT extract snapshots, so the paper can state
the vintage of every local-road and facility layer instead of "2024-2026 snapshot".

Reads the oex/HOT ``Readme.txt`` files that ship with the HDX exports.
"""
from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
COUNTRIES = ROOT / 'data/external/hdx/countries'
OUT = ROOT / 'output/experiments/osm_snapshots'
SNAP = re.compile(r'Snapshot:\s*([0-9]{4}-[0-9]{2}-[0-9]{2})')
GEN = re.compile(r'(?:Generated|Exported Timestamp[^:]*):\s*([0-9]{4}-[0-9]{2}-[0-9]{2})')


def scan(folder: Path):
    for readme in sorted(folder.rglob('Readme.txt')):
        try:
            txt = readme.read_text(encoding='utf-8', errors='ignore')
        except Exception:
            continue
        m = SNAP.search(txt) or GEN.search(txt)
        if m:
            return m.group(1), readme.parent.name
    return None, None


def main():
    rows = []
    for d in sorted(p for p in COUNTRIES.iterdir() if p.is_dir()):
        iso = d.name
        roads, roads_src = scan(d / 'local_roads')
        fac, fac_src = scan(d)
        rows.append({'iso3': iso, 'osm_roads_snapshot': roads, 'osm_facilities_snapshot': fac})
    df = pd.DataFrame(rows)
    OUT.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT / 'osm_snapshot_dates.csv', index=False, encoding='utf-8-sig')
    have = df.dropna(subset=['osm_roads_snapshot'])
    print(f'{len(df)} countries, {len(have)} with a road snapshot date')
    print(f"roads snapshot range: {have.osm_roads_snapshot.min()} .. {have.osm_roads_snapshot.max()}")
    f = df.dropna(subset=['osm_facilities_snapshot'])
    print(f"facilities snapshot range: {f.osm_facilities_snapshot.min()} .. "
          f"{f.osm_facilities_snapshot.max()} ({len(f)}/{len(df)})")
    print(df.to_string(index=False))


if __name__ == '__main__':
    main()
