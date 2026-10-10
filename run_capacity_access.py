# -*- coding: utf-8 -*-
"""Stage 4: capacity-threshold accessibility where facility capacity attributes exist.

Healthsites country CSVs (OSM-derived, but carrying ``beds``/``staff_doctors``/
``staff_nurses``) are used to test how much reported access depends on counting any health
point versus only staffed or bedded facilities.  This is the capacity analogue of the
facility-level sensitivity in the main text.

Outputs ``output/experiments/capacity_access/``.
"""
from __future__ import annotations

import gc
import time
from pathlib import Path

import duckdb
import geopandas as gpd
import numpy as np
import pandas as pd
import requests
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import dijkstra
from scipy.spatial import cKDTree

import run_experiment_29_corrected_countries as canon
import run_experiment_29_weight_sensitivity as sens

ROOT = Path(__file__).resolve().parent
EXP = ROOT / 'output/experiments/experiment_29_global_expansion'
OUT = ROOT / 'output/experiments/capacity_access'
CACHE = ROOT / 'data/external/healthsites'


def healthsites_urls() -> dict:
    cat = pd.read_csv(EXP / 'facility_registry_resources.csv')
    cat = cat[(cat.organization.str.contains('Healthsite', case=False, na=False))
              & (cat.service == 'health') & (cat.format == 'csv')]
    out = {}
    for _, r in cat.iterrows():
        out.setdefault(r.iso3, r.url)
    return out


def fetch(iso: str, url: str):
    CACHE.mkdir(parents=True, exist_ok=True)
    dest = CACHE / f'{iso.lower()}_healthsites.csv'
    if dest.exists() and dest.stat().st_size > 0:
        return dest
    for attempt in range(3):
        try:
            with requests.get(url, stream=True, timeout=300,
                              headers={'User-Agent': 'Mozilla/5.0 (research)'}) as r:
                r.raise_for_status()
                with dest.open('wb') as f:
                    for chunk in r.iter_content(chunk_size=1 << 20):
                        if chunk:
                            f.write(chunk)
            return dest
        except Exception as exc:
            print(f'  {iso}: retry {attempt + 1} ({type(exc).__name__})', flush=True)
            time.sleep(4 * (attempt + 1))
    return None


def load_capacity(path: Path) -> gpd.GeoDataFrame:
    df = pd.read_csv(path)
    xcol = 'X' if 'X' in df.columns else ('lon' if 'lon' in df.columns else None)
    ycol = 'Y' if 'Y' in df.columns else ('lat' if 'lat' in df.columns else None)
    if xcol is None or ycol is None:
        raise ValueError('no coordinate columns')
    for col in ('beds', 'staff_doctors', 'staff_nurses'):
        if col not in df.columns:
            df[col] = np.nan
    geom = gpd.points_from_xy(df[xcol], df[ycol])
    g = gpd.GeoDataFrame(df, geometry=geom, crs=4326)
    return g[g.geometry.notna() & ~g.geometry.is_empty]


def graph_for(iso: str):
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
        us.append(tb.column('u').to_numpy())
        vs.append(tb.column('v').to_numpy())
        ws.append(tb.column('w').to_numpy())
    con.close()
    u = np.concatenate(us); v = np.concatenate(vs); w = np.concatenate(ws)
    csr = csr_matrix((np.concatenate((w, w)), (np.concatenate((u, v)), np.concatenate((v, u)))),
                     shape=(len(node_xy), len(node_xy)))
    del us, vs, ws, u, v, w
    gc.collect()
    x3857, y3857 = canon.TRANSFORMER.transform(node_xy[:, 0], node_xy[:, 1])
    tree = cKDTree(np.column_stack((x3857, y3857)))
    return csr, tree, np.arange(len(node_xy))


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    urls = healthsites_urls()
    print(f'Healthsites CSVs available for {len(urls)} countries: {sorted(urls)}', flush=True)
    coverage, shares = [], []
    for iso, url in sorted(urls.items()):
        path = fetch(iso, url)
        if path is None:
            continue
        try:
            fac = load_capacity(path)
        except Exception as exc:
            print(f'{iso}: {type(exc).__name__} {exc}')
            continue
        beds = pd.to_numeric(fac.beds, errors='coerce').fillna(0)
        doctors = pd.to_numeric(fac.staff_doctors, errors='coerce').fillna(0)
        nurses = pd.to_numeric(fac.staff_nurses, errors='coerce').fillna(0)
        staffed = (doctors > 0) | (nurses > 0)
        coverage.append({'iso3': iso, 'records': len(fac),
                         'beds_recorded_pct': 100 * (beds > 0).mean(),
                         'beds_ge10_pct': 100 * (beds >= 10).mean(),
                         'staff_recorded_pct': 100 * staffed.mean(),
                         'beds_total': float(beds.sum())})
        sets = {'healthsites_all': fac, 'beds_ge_1': fac[beds >= 1],
                'beds_ge_10': fac[beds >= 10], 'staffed': fac[staffed]}
        osm = canon.load_facilities(iso, 'health')
        sets['osm_hospital_clinic'] = osm[osm.amenity.astype(str).isin(['hospital', 'clinic'])]
        csr, tree, nodes = graph_for(iso)
        xy, xy3857, density, counts = sens.population_weights(iso)
        _, idx = tree.query(xy3857)
        cells = nodes[idx]
        for name, subset in sets.items():
            if len(subset) == 0:
                continue
            src, snap = canon.source_nodes(subset, nodes, tree)
            dist = dijkstra(csr, directed=False, indices=np.asarray(sorted(src), dtype=np.int32),
                            min_only=True) if src else np.full(len(nodes), np.inf)
            d = dist[cells]
            valid = np.isfinite(d)
            shares.append({'iso3': iso, 'facility_set': name, 'facilities': len(subset),
                           'source_nodes': len(src),
                           'share_30min_pct': 100 * counts[valid & (d <= 30)].sum() / counts.sum(),
                           'share_60min_pct': 100 * counts[valid & (d <= 60)].sum() / counts.sum()})
            del dist, d
            gc.collect()
            print(f'{iso} {name}: {shares[-1]["share_60min_pct"]:.2f}%', flush=True)
        pd.DataFrame(coverage).to_csv(OUT / 'capacity_attribute_coverage.csv', index=False,
                                      encoding='utf-8-sig')
        pd.DataFrame(shares).to_csv(OUT / 'capacity_threshold_shares.csv', index=False,
                                    encoding='utf-8-sig')
    print('done')


if __name__ == '__main__':
    main()
