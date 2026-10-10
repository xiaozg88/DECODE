# -*- coding: utf-8 -*-
"""Urban/rural accessibility gaps for the 30-country sample (core + 23 additions).

Reuses the cached sensitivity pieces (canonical Web-Mercator travel times) to rebuild
each national graph, samples the global GHS-SMOD 2020 layer at every population cell
and reports population-weighted 30/60/120-minute access by urban/rural class.

Outputs ``output/experiments/experiment_29_global_expansion/urban_rural_expansion.csv``.
"""
from __future__ import annotations

import argparse
import gc
import time
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import dijkstra
from scipy.spatial import cKDTree

import run_experiment_29_corrected_countries as canon
import run_experiment_29_weight_sensitivity as sens
from run_experiment_15_urban_rural import classify_smod, sample_smod

ROOT = Path(__file__).resolve().parent
OUT_CSV = (ROOT / 'output/experiments/experiment_29_global_expansion'
           / 'urban_rural_expansion.csv')
CORE = ['PAK', 'MOZ', 'BGD', 'ETH', 'KEN', 'COL', 'PHL']
ADDITIONS = ['EGY', 'GEO', 'GHA', 'GTM', 'HND', 'IDN', 'IND', 'JOR', 'KGZ', 'KHM', 'LKA',
             'MEX', 'MLI', 'NGA', 'NPL', 'PER', 'PNG', 'RWA', 'SEN', 'TUR', 'TZA', 'VNM', 'ZMB']


def _stamp(t0, msg):
    print(f'[{time.strftime("%H:%M:%S")}] {msg} (elapsed {time.time() - t0:,.0f}s)', flush=True)


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
    xy, xy3857, density, counts = sens.population_weights(iso)
    _, idx = tree.query(xy3857)
    cells = nodes[idx]
    smod = sample_smod(xy[:, 0], xy[:, 1])
    _, urban_rural = classify_smod(smod)
    rows = []
    for service, kind, vals in (('health', 'health', ['hospital', 'clinic']),
                                ('education', 'education', ['school'])):
        fac = canon.load_facilities(iso, kind)
        fac = fac[fac.amenity.astype(str).isin(vals)].copy()
        src, snap = canon.source_nodes(fac, nodes, tree)
        dist = dijkstra(csr, directed=False, indices=np.asarray(sorted(src), dtype=np.int32),
                        min_only=True) if src else np.full(len(node_xy), np.inf)
        d = dist[cells]
        valid = np.isfinite(d)
        total = counts.sum()
        for group in ('all', 'urban', 'rural'):
            mask = np.ones(len(xy), dtype=bool) if group == 'all' else (urban_rural == group)
            if mask.sum() == 0:
                continue
            m = mask & valid
            pop = float(counts[mask].sum())
            row = {'iso3': iso, 'service': service, 'group': group,
                   'population_millions': pop / 1e6,
                   'population_cells': int(mask.sum()),
                   'share_30min_pct': 100 * float(counts[m & (d <= 30)].sum()) / max(pop, 1e-9),
                   'share_60min_pct': 100 * float(counts[m & (d <= 60)].sum()) / max(pop, 1e-9),
                   'share_120min_pct': 100 * float(counts[m & (d <= 120)].sum()) / max(pop, 1e-9),
                   'mean_travel_reachable_min': float(np.average(d[m], weights=counts[m]))
                   if m.any() else np.nan,
                   'facilities': len(fac), 'facility_source_nodes': len(src),
                   'unreachable_population_millions': float(counts[mask & ~valid].sum()) / 1e6}
            rows.append(row)
        del fac, dist, d
        gc.collect()
    _stamp(t0, f'{iso} urban/rural done ({len(rows)} rows)')
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--countries', nargs='+', default=CORE + ADDITIONS)
    a = ap.parse_args()
    done = set()
    if OUT_CSV.exists():
        prev = pd.read_csv(OUT_CSV)
        done = set(prev.iso3.unique())
        all_rows = [prev]
    else:
        all_rows = []
    for iso in a.countries:
        if iso in done:
            print(f'{iso} already done')
            continue
        rows = run_country(iso)
        all_rows.append(pd.DataFrame(rows))
        pd.concat(all_rows, ignore_index=True).to_csv(OUT_CSV, index=False, encoding='utf-8-sig')
        print(f'{iso}: {len(rows)} rows written', flush=True)
    print('done', OUT_CSV)


if __name__ == '__main__':
    main()
