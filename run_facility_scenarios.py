# -*- coding: utf-8 -*-
"""Facility-definition and amenity-rescue scenarios (P1-2 and P1-4).

For every sample country the same corrected graph is evaluated with different facility
sets, all with area-weighted population counts:

health
  ``hospital_clinic``  canonical hospital + clinic,
  ``hospital_only``    hospitals only (level sensitivity),
  ``all_health_points`` every record in the HOT health export (pharmacies, doctors,
                       dentists included) - an upper-bound "any care point" definition,
  ``rescue_untagged``  canonical plus records whose amenity tag is missing (building
                       footprints of unknown type) - upper bound under tag incompleteness;
education
  ``school``           canonical schools only,
  ``rescue_untagged``  schools plus untagged footprints.

Outputs ``output/experiments/facility_scenarios/facility_scenario_shares.csv``.
"""
from __future__ import annotations

import argparse
import gc
import time
from pathlib import Path

import duckdb
import geopandas as gpd
import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import dijkstra
from scipy.spatial import cKDTree

import run_experiment_29_corrected_countries as canon
import run_experiment_29_weight_sensitivity as sens

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'output/experiments/facility_scenarios'
CORE = ['PAK', 'MOZ', 'BGD', 'ETH', 'KEN', 'COL', 'PHL']
ADDITIONS = ['EGY', 'GEO', 'GHA', 'GTM', 'HND', 'IDN', 'IND', 'JOR', 'KGZ', 'KHM', 'LKA',
             'MEX', 'MLI', 'NGA', 'NPL', 'PER', 'PNG', 'RWA', 'SEN', 'TUR', 'TZA', 'VNM', 'ZMB']


def _stamp(t0, msg):
    print(f'[{time.strftime("%H:%M:%S")}] {msg} (elapsed {time.time() - t0:,.0f}s)', flush=True)


def facility_sets(iso: str, kind: str) -> dict[str, gpd.GeoDataFrame]:
    fac = canon.load_facilities(iso, kind)
    amenity = fac.amenity.astype(str).str.lower().str.strip()
    missing = fac.amenity.isna() | amenity.isin(['none', 'nan', ''])
    if kind == 'health':
        canonical = fac[amenity.isin(['hospital', 'clinic'])]
        return {
            'hospital_clinic': canonical,
            'hospital_only': fac[amenity == 'hospital'],
            'all_health_points': fac[~missing],
            'rescue_untagged': fac[amenity.isin(['hospital', 'clinic']) | missing],
        }
    canonical = fac[amenity == 'school']
    return {'school': canonical, 'rescue_untagged': fac[(amenity == 'school') | missing]}


def run_country(iso: str) -> list[dict]:
    t0 = time.time()
    pieces = sens.build_pieces(iso)
    con = duckdb.connect()
    con.execute("SET memory_limit='5GB'")
    con.execute(f"CREATE TABLE pieces AS SELECT sx, sy, ex, ey, tt_mercator FROM "
                f"read_parquet('{pieces.as_posix()}')")
    con.execute("CREATE TABLE endpoints AS SELECT sx AS x, sy AS y FROM pieces UNION "
                "SELECT ex, ey FROM pieces")
    con.execute("CREATE TABLE nodes AS SELECT (row_number() OVER (ORDER BY x, y) - 1)::BIGINT "
                "AS nid, x, y FROM endpoints")
    node_tbl = con.execute("SELECT x, y FROM nodes ORDER BY nid").fetch_arrow_table()
    node_xy = np.column_stack([node_tbl.column('x').to_numpy(), node_tbl.column('y').to_numpy()])
    con.execute("CREATE TABLE e AS SELECT a.nid AS u, b.nid AS v, min(x.w) AS w FROM ("
                "SELECT sx, sy, ex, ey, tt_mercator AS w FROM pieces "
                "WHERE (sx <> ex OR sy <> ey) AND isfinite(tt_mercator)) AS x "
                "JOIN nodes a ON a.x = x.sx AND a.y = x.sy "
                "JOIN nodes b ON b.x = x.ex AND b.y = x.ey GROUP BY 1, 2")
    us, vs, ws = [], [], []
    for tb in con.execute("SELECT u, v, w FROM e").fetch_record_batch(4_000_000):
        us.append(tb.column('u').to_numpy()); vs.append(tb.column('v').to_numpy())
        ws.append(tb.column('w').to_numpy())
    con.close()
    u = np.concatenate(us); v = np.concatenate(vs); w = np.concatenate(ws)
    csr = csr_matrix((np.concatenate((w, w)), (np.concatenate((u, v)), np.concatenate((v, u)))),
                     shape=(len(node_xy), len(node_xy)))
    del us, vs, ws, u, v, w
    gc.collect()
    x3857, y3857 = canon.TRANSFORMER.transform(node_xy[:, 0], node_xy[:, 1])
    tree = cKDTree(np.column_stack((x3857, y3857)))
    nodes = np.arange(len(node_xy))
    _, _, _, counts = sens.population_weights(iso)
    xy, xy3857, _, _ = sens.population_weights(iso)
    _, idx = tree.query(xy3857)
    cells = nodes[idx]
    rows = []
    for kind in ('health', 'education'):
        for name, fac in facility_sets(iso, kind).items():
            if len(fac) == 0:
                continue
            src, snap = canon.source_nodes(fac, nodes, tree)
            dist = dijkstra(csr, directed=False, indices=np.asarray(sorted(src), dtype=np.int32),
                            min_only=True) if src else np.full(len(node_xy), np.inf)
            d = dist[cells]
            valid = np.isfinite(d)
            rows.append({'iso3': iso, 'service': kind, 'scenario': name,
                         'facility_records': len(fac), 'facility_source_nodes': len(src),
                         'share_30min_pct': 100 * counts[valid & (d <= 30)].sum() / counts.sum(),
                         'share_60min_pct': 100 * counts[valid & (d <= 60)].sum() / counts.sum(),
                         'share_120min_pct': 100 * counts[valid & (d <= 120)].sum() / counts.sum()})
            del dist, d, fac
            gc.collect()
    _stamp(t0, f'{iso} scenarios={len(rows)}')
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--countries', nargs='+', default=CORE + ADDITIONS)
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    done = set()
    csv = OUT / 'facility_scenario_shares.csv'
    if csv.exists():
        prev = pd.read_csv(csv)
        rows = prev.to_dict('records')
        done = set(prev.iso3.unique())
    for iso in a.countries:
        if iso in done:
            print(f'{iso} already done')
            continue
        try:
            rows.extend(run_country(iso))
        except Exception as exc:
            print(f'{iso} failed: {type(exc).__name__} {exc}', flush=True)
        pd.DataFrame(rows).to_csv(csv, index=False, encoding='utf-8-sig')
    print('done', csv)


if __name__ == '__main__':
    main()
