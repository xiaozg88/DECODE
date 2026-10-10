# -*- coding: utf-8 -*-
"""Compare a tiled Experiment 29 run against the canonical artifacts of a country.

Usage:
    python validate_tiled_vs_canonical.py --iso3 LKA --suffix _tiledtest \
        --tiled-outdir output/experiments/experiment_29_global_expansion/validation_tiled

Checks
------
1. noded geometry integrity: total segment length and total travel time of the
   canonical noded GPKG vs the tiled noded parquet (noding must conserve both);
2. baseline CSV metrics (facility counts, graph size, access shares) with deltas.

Writes ``<tiled-outdir>/<iso3>/tiled_vs_canonical_<iso3>.csv`` and prints a summary.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import duckdb
import pandas as pd
import pyogrio

ROOT = Path(__file__).resolve().parent
CANON = ROOT / 'output/experiments/experiment_29_global_expansion/corrected_countries'

METRICS = ['facility_records', 'facility_source_nodes', 'median_facility_snap_m',
           'noded_segments', 'graph_nodes', 'graph_edges', 'population_total',
           'population_finite', 'population_unreachable', 'mean_travel_reachable_min',
           'share_30min_pct', 'share_60min_pct', 'share_120min_pct', 'share_240min_pct']


def geometry_totals(gpkg, parquet):
    gdf = pyogrio.read_dataframe(gpkg, columns=['length_m', 'travel_time_min'])
    canonical = {'segments': len(gdf), 'length_m': float(gdf.length_m.sum()),
                 'travel_time_min': float(gdf.travel_time_min.sum())}
    con = duckdb.connect()
    row = con.execute(
        "SELECT count(*) AS segments, sum(length_m) AS length_m, "
        "sum(travel_time_min) AS travel_time_min FROM read_parquet(?)", [str(parquet)]).fetchone()
    con.close()
    tiled = {'segments': int(row[0]), 'length_m': float(row[1]), 'travel_time_min': float(row[2])}
    return canonical, tiled


def metric_deltas(canon_csv, tiled_csv):
    can = pd.read_csv(canon_csv)
    til = pd.read_csv(tiled_csv)
    rows = []
    for service in ('health', 'education'):
        c = can[can.service == service].iloc[0]
        t = til[til.service == service].iloc[0]
        for k in METRICS:
            cv, tv = float(c[k]), float(t[k])
            rows.append({'service': service, 'metric': k, 'canonical': cv, 'tiled': tv,
                         'delta': tv - cv, 'delta_pct': (tv - cv) / cv * 100 if cv else float('nan')})
    return pd.DataFrame(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--iso3', required=True)
    ap.add_argument('--suffix', default='')
    ap.add_argument('--tiled-outdir', default=str(ROOT / 'output/experiments/experiment_29_global_expansion/validation_tiled'))
    ap.add_argument('--canonical-outdir', default=str(CANON))
    a = ap.parse_args()
    iso = a.iso3
    low = iso.lower()
    can_dir = Path(a.canonical_outdir) / low
    til_dir = Path(a.tiled_outdir) / low
    can_gpkg = ROOT / 'data/external/hdx/countries' / iso / 'local_roads' / f'{low}_noded_segments.gpkg'
    til_parquet = (ROOT / 'data/external/hdx/countries' / iso / 'local_roads'
                   / f'{low}{a.suffix}_noded_segments.parquet')
    print(f'canonical cache : {can_gpkg}')
    print(f'tiled cache     : {til_parquet}')
    geo_c, geo_t = geometry_totals(can_gpkg, til_parquet)
    print('\nnoding integrity (tiled vs canonical)')
    for k in geo_c:
        rel = (geo_t[k] - geo_c[k]) / geo_c[k] * 100 if geo_c[k] else float('nan')
        print(f'  {k:<16} canonical={geo_c[k]:>18,.3f}  tiled={geo_t[k]:>18,.3f}  delta={rel:+.4f}%')
    d = metric_deltas(can_dir / f'{low}_corrected_baseline.csv',
                      til_dir / f'{low}_corrected_baseline.csv')
    out = til_dir / f'tiled_vs_canonical_{low}.csv'
    d.to_csv(out, index=False, encoding='utf-8-sig')
    print('\nbaseline metric deltas (absolute = pp for shares)')
    print(d.to_string(index=False, float_format=lambda x: f'{x:,.4f}'))
    worst = d[d.metric.str.contains('share')].delta.abs().max()
    print(f'\nmax |delta| on access shares: {worst:.4f} pp')
    print(f'wrote {out}')


if __name__ == '__main__':
    main()
