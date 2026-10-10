# -*- coding: utf-8 -*-
"""Weight/length sensitivity for the Experiment 29 corrected expansion baselines.

Motivation (see ``EXPANSION_DATA_AUDIT.md``):

* the pipeline reads WorldPop ``*_pd_2020_1km.tif`` rasters, which store population
  *density* per km2 (verified against the companion ``*_ppp_*_Aggregated.tif`` count
  rasters in 12/12 sampled countries: sum(density x cell_area) == sum(counts)), but
  uses the raw values as population *counts*.  That inflates absolute population by
  1.16-1.82x and slightly re-weights population-weighted access shares;
* the canonical pipeline derives ``length_m`` with ``EPSG:3857`` lengths, which
  overstate ground distance by 1/cos(latitude): 1.005 (Rwanda) to 1.35 (Georgia).

This script re-evaluates every addition under

    population weight : density (canonical) | counts (corrected)
    segment length    : Web Mercator (canonical) | WGS84 geodesic
    surface scenario  : none | no unpaved (impassable) | unknown as unpaved

plus a ``no_unpaved`` / ``unknown_as_unpaved`` stress test, all on the cached graph
topology so no re-noding is required.  Variant ``density_mercator_none`` must
reproduce the published baseline CSV (that is the harness self-check).
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
import pyarrow as pa
import pyarrow.parquet as pq
import pyogrio
import rasterio
import shapely
from pyproj import Geod
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import dijkstra
from scipy.spatial import cKDTree

import prototype_multicountry_access as base
import run_experiment_29_corrected_countries as canon

ROOT = Path(__file__).resolve().parent
EXP = ROOT / 'output/experiments/experiment_29_global_expansion'
COUNTRIES = ROOT / 'data/external/hdx/countries'
OUT_CSV = EXP / 'weight_length_sensitivity.csv'
GEOD = Geod(ellps='WGS84')
CHUNK = 2_000_000

ADDITIONS = ['EGY', 'GEO', 'GHA', 'GTM', 'HND', 'IDN', 'IND', 'JOR', 'KGZ', 'KHM', 'LKA',
             'MEX', 'MLI', 'NGA', 'NPL', 'PER', 'PNG', 'RWA', 'SEN', 'TUR', 'TZA', 'VNM', 'ZMB']
VARIANTS = [
    ('density_mercator_none', 'density', 'mercator', 'none'),
    ('counts_mercator_none', 'counts', 'mercator', 'none'),
    ('density_geodesic_none', 'density', 'geodesic', 'none'),
    ('counts_geodesic_none', 'counts', 'geodesic', 'none'),
    ('counts_geodesic_no_unpaved', 'counts', 'geodesic', 'no_unpaved'),
    ('counts_geodesic_unknown_as_unpaved', 'counts', 'geodesic', 'unknown_as_unpaved'),
]


def _stamp(t0, msg):
    print(f'[{time.strftime("%H:%M:%S")}] {msg} (elapsed {time.time() - t0:,.0f}s)', flush=True)


def cache_path(iso: str) -> Path | None:
    local = COUNTRIES / iso / 'local_roads'
    for cand in (local / f'{iso.lower()}_noded_segments.parquet',
                 local / f'{iso.lower()}_noded_segments.gpkg'):
        if cand.exists() and cand.stat().st_size > 0:
            return cand
    # core-country caches use ad-hoc names (e.g. mozambique_noded_segments.gpkg)
    for cand in sorted(local.glob('*_noded_segments.gpkg')) + sorted(local.glob('*_noded_segments.parquet')):
        if cand.stat().st_size > 0:
            return cand
    return None


def population_weights(iso: str):
    """Return (lon/lat, 3857, density values, count values)."""
    path = COUNTRIES / iso / f'{iso.lower()}_pd_2020_1km.tif'
    with rasterio.open(path) as src:
        a = src.read(1).astype('float32')
        transform = src.transform
        nodata = src.nodata
        rows_idx = np.arange(src.height)
        lat = transform.f + (rows_idx + 0.5) * transform.e
        dx = abs(transform.a) * 111.32 * np.cos(np.radians(lat))
        dy = abs(transform.e) * 110.574
        area = (dx * dy)[:, None]
    valid = np.isfinite(a) & (a != nodata) & (a > 0)
    rows, cols = np.where(valid)
    density = a[valid]
    counts = density * area[rows, 0]
    lon = transform.c + (cols + .5) * transform.a
    lat = transform.f + (rows + .5) * transform.e
    xy = np.column_stack([lon, lat])
    return xy, np.column_stack(canon.TRANSFORMER.transform(xy[:, 0], xy[:, 1])), density, counts


def build_pieces(iso: str, force: bool = False) -> Path:
    """Cache per-segment Mercator/geodesic times and surface flags."""
    out = COUNTRIES / iso / 'local_roads' / f'{iso.lower()}_pieces_sensitivity.parquet'
    if out.exists() and not force:
        return out
    cache = cache_path(iso)
    assert cache is not None, iso
    schema = pa.schema([('sx', pa.float64()), ('sy', pa.float64()), ('ex', pa.float64()),
                        ('ey', pa.float64()), ('tt_mercator', pa.float64()),
                        ('tt_geodesic', pa.float64()), ('tt_unknown_unpaved', pa.float64()),
                        ('is_unpaved', pa.bool_()), ('is_unknown', pa.bool_())])
    writer = pq.ParquetWriter(out, schema, compression='zstd')
    t0 = time.time()
    n = 0
    try:
        if cache.suffix == '.parquet':
            con = duckdb.connect()
            con.execute("SET memory_limit='5GB'")
            reader = con.execute(
                "SELECT sx, sy, ex, ey, travel_time_min, speed_kmh, surface_class, geom_wkb "
                f"FROM read_parquet('{cache.as_posix()}')").fetch_record_batch(CHUNK)
            chunks = ([tb.column('sx').to_numpy(), tb.column('sy').to_numpy(),
                       tb.column('ex').to_numpy(), tb.column('ey').to_numpy(),
                       tb.column('travel_time_min').to_numpy(),
                       tb.column('speed_kmh').to_numpy(),
                       tb.column('surface_class').to_numpy(zero_copy_only=False),
                       tb.column('geom_wkb').to_numpy(zero_copy_only=False)]
                      for tb in reader)
        else:
            info = pyogrio.read_info(cache)
            total = info['features']

            def gen():
                for start in range(0, total, CHUNK):
                    df = pyogrio.read_dataframe(
                        cache, columns=['travel_time_min', 'speed_kmh', 'surface_class'],
                        skip_features=start, max_features=min(CHUNK, total - start))
                    yield [np.full(len(df), np.nan), np.full(len(df), np.nan),
                           np.full(len(df), np.nan), np.full(len(df), np.nan),
                           df.travel_time_min.to_numpy(), df.speed_kmh.to_numpy(),
                           df.surface_class.to_numpy(), df.geometry.to_wkb().to_numpy()]
            chunks = gen()

        for sx, sy, ex, ey, tt_merc, speed, surf, wkb in chunks:
            geoms = shapely.from_wkb(wkb)
            coords, idx = shapely.get_coordinates(geoms, return_index=True)
            if len(coords) > 1:
                _, _, dist = GEOD.inv(coords[:-1, 0], coords[:-1, 1], coords[1:, 0], coords[1:, 1])
                dist = np.where(idx[1:] == idx[:-1], dist, 0.0)
                len_geo = np.bincount(idx[:-1], weights=dist, minlength=len(geoms))
            else:
                len_geo = np.zeros(len(geoms))
            surf_str = pd.Series(surf).astype(str).to_numpy()
            is_unpaved = surf_str == 'unpaved'
            is_unknown = (surf_str == 'unknown') | pd.isna(surf)
            # canonical speed = base * surface_mult * width; recover base*width and re-apply
            mult = pd.Series(surf_str).map(lambda x: base.SURFACE_MULT.get(x, .75)).to_numpy()
            base_width = speed / np.where((mult > 0) & np.isfinite(speed), mult, np.nan)
            tt_geo = len_geo / 1000.0 / speed * 60.0
            tt_unknown_unpaved = np.where(is_unknown, len_geo / 1000.0 /
                                          (base_width * base.SURFACE_MULT['unpaved']) * 60.0,
                                          tt_geo)
            if not np.isfinite(ex).all():  # gpkg path: take endpoints from geometry
                first = coords[np.r_[True, idx[1:] != idx[:-1]]]
                last_idx = np.r_[np.flatnonzero(idx[1:] != idx[:-1]), len(idx) - 1]
                sx, sy = first[:, 0], first[:, 1]
                ex, ey = coords[last_idx, 0], coords[last_idx, 1]
            tbl = pa.table({
                'sx': np.round(sx, 7).astype('float64'), 'sy': np.round(sy, 7).astype('float64'),
                'ex': np.round(ex, 7).astype('float64'), 'ey': np.round(ey, 7).astype('float64'),
                'tt_mercator': tt_merc.astype('float64'), 'tt_geodesic': tt_geo,
                'tt_unknown_unpaved': tt_unknown_unpaved,
                'is_unpaved': is_unpaved, 'is_unknown': is_unknown}, schema=schema)
            writer.write_table(tbl)
            n += len(geoms)
            del geoms, coords, idx, tbl
            gc.collect()
    finally:
        writer.close()
    _stamp(t0, f'{iso} sensitivity pieces={n:,}')
    return out


def graph_for_variant(con, variant, length_mode, scenario):
    """Create nodes/edges tables for one variant; returns (n_nodes, n_edges)."""
    wcol = 'tt_geodesic' if length_mode == 'geodesic' else 'tt_mercator'
    if scenario == 'no_unpaved':
        scenario_sql = wcol
        where = f'WHERE NOT is_unpaved AND isfinite({scenario_sql})'
    elif scenario == 'unknown_as_unpaved':
        scenario_sql = 'tt_unknown_unpaved'
        where = f'WHERE isfinite({scenario_sql})'
    else:
        scenario_sql = wcol
        where = f'WHERE isfinite({scenario_sql})'
    con.execute(f'DROP TABLE IF EXISTS {variant}')
    con.execute(
        f"CREATE TABLE {variant} AS SELECT a.nid AS u, b.nid AS v, min(x.w) AS w FROM ("
        f"SELECT sx, sy, ex, ey, {scenario_sql} AS w FROM pieces "
        f"WHERE (sx <> ex OR sy <> ey) AND {where.replace('WHERE ', '')}) AS x "
        f"JOIN nodes a ON a.x = x.sx AND a.y = x.sy "
        f"JOIN nodes b ON b.x = x.ex AND b.y = x.ey GROUP BY 1, 2")
    return con.execute(f'SELECT count(*) FROM {variant}').fetchone()[0]


def run_country(iso: str, services=('health', 'education'), force=False) -> list[dict]:
    rows = []
    cache = cache_path(iso)
    if cache is None:
        return [{'iso3': iso, 'variant': 'MISSING_CACHE'}]
    t0 = time.time()
    pieces = build_pieces(iso, force=force)
    con = duckdb.connect()
    con.execute("SET memory_limit='5GB'")
    con.execute(f"SET temp_directory='{(COUNTRIES / iso / 'local_roads' / 'duck_tmp').as_posix()}'")
    con.execute(f"CREATE TABLE pieces AS SELECT * FROM read_parquet('{pieces.as_posix()}')")
    con.execute("CREATE TABLE endpoints AS SELECT sx AS x, sy AS y FROM pieces UNION "
                "SELECT ex, ey FROM pieces")
    con.execute("CREATE TABLE nodes AS SELECT (row_number() OVER (ORDER BY x, y) - 1)::BIGINT "
                "AS nid, x, y FROM endpoints")
    node_xy = con.execute("SELECT x, y FROM nodes ORDER BY nid").fetch_arrow_table()
    node_xy = np.column_stack([node_xy.column('x').to_numpy(), node_xy.column('y').to_numpy()])
    n_nodes = len(node_xy)
    x3857, y3857 = canon.TRANSFORMER.transform(node_xy[:, 0], node_xy[:, 1])
    tree = cKDTree(np.column_stack((x3857, y3857)))
    nodes = np.arange(n_nodes)
    xy, xy3857, density, counts = population_weights(iso)
    _, idx = tree.query(xy3857)
    cells = nodes[idx]
    _stamp(t0, f'{iso} nodes={n_nodes:,} population cells={len(cells):,}')
    for variant, pop_mode, length_mode, scenario in VARIANTS:
        n_edges = graph_for_variant(con, variant, length_mode, scenario)
        blocks = con.execute(f'SELECT u, v, w FROM {variant}').fetch_record_batch(4_000_000)
        us, vs, ws = [], [], []
        for tb in blocks:
            us.append(tb.column('u').to_numpy())
            vs.append(tb.column('v').to_numpy())
            ws.append(tb.column('w').to_numpy())
        u = np.concatenate(us); v = np.concatenate(vs); w = np.concatenate(ws)
        csr = csr_matrix((np.concatenate((w, w)), (np.concatenate((u, v)), np.concatenate((v, u)))),
                         shape=(n_nodes, n_nodes))
        del us, vs, ws, u, v, w
        gc.collect()
        pop = counts if pop_mode == 'counts' else density
        for service, kind, vals in (('health', 'health', ['hospital', 'clinic']),
                                    ('education', 'education', ['school'])):
            fac = canon.load_facilities(iso, kind)
            fac = fac[fac.amenity.astype(str).isin(vals)].copy()
            src, snap = canon.source_nodes(fac, nodes, tree)
            dist = dijkstra(csr, directed=False, indices=np.asarray(sorted(src), dtype=np.int32),
                            min_only=True) if src else np.full(n_nodes, np.inf)
            d = dist[cells]
            valid = np.isfinite(d)
            row = {'iso3': iso, 'service': service, 'variant': variant,
                   'population_mode': pop_mode, 'length_mode': length_mode, 'scenario': scenario,
                   'graph_nodes': n_nodes, 'graph_edges': n_edges,
                   'population_total_millions': float(pop.sum()) / 1e6,
                   'population_unreachable_millions': float(pop[~valid].sum()) / 1e6,
                   'mean_travel_reachable_min': float(np.average(d[valid], weights=pop[valid]))
                   if valid.any() else np.nan}
            for t in (30, 60, 120, 240):
                row[f'share_{t}min_pct'] = 100 * pop[valid & (d <= t)].sum() / pop.sum()
            rows.append(row)
            del fac, dist, d
            gc.collect()
        con.execute(f'DROP TABLE {variant}')
    con.close()
    _stamp(t0, f'{iso} variants done')
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--countries', nargs='+', default=ADDITIONS)
    ap.add_argument('--force', action='store_true')
    ap.add_argument('--out', default=str(OUT_CSV))
    a = ap.parse_args()
    out = Path(a.out)
    done = set()
    if out.exists():
        prev = pd.read_csv(out)
        done = set(prev.iso3.unique())
    all_rows = [pd.read_csv(out)] if out.exists() else []
    for iso in a.countries:
        if iso in done and not a.force:
            print(f'{iso} already in {out.name}, skipping')
            continue
        rows = run_country(iso, force=a.force)
        all_rows.append(pd.DataFrame(rows))
        pd.concat(all_rows, ignore_index=True).to_csv(out, index=False, encoding='utf-8-sig')
        print(f'{iso}: {len(rows)} rows written', flush=True)
    print('done', out)


if __name__ == '__main__':
    main()
