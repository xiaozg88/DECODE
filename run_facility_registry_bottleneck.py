# -*- coding: utf-8 -*-
"""P0.3: test the facility bottleneck on independent registries (beyond the 3 legacy cases).

Uses the shapefile/GeoJSON/CSV registries from ``probe_independent_registries.py``
(OCHA ROAP / OCHA country offices, OCHA ROCCA, Giga) for five health and seven education
country cases, re-uses the cached corrected graphs, and compares access with

* OSM/HOT facilities only (the current baseline), and
* OSM/HOT + independent registry (union, snapped within 1 km like the main model).

Outputs ``output/experiments/facility_registry/facility_registry_bottleneck.csv``.
"""
from __future__ import annotations

import argparse
import gc
import time
import zipfile
from pathlib import Path

import duckdb
import geopandas as gpd
import numpy as np
import pandas as pd
import shapely
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import dijkstra
from scipy.spatial import cKDTree

import run_experiment_29_corrected_countries as canon
import run_experiment_29_weight_sensitivity as sens

ROOT = Path(__file__).resolve().parent
EXP = ROOT / 'output/experiments/experiment_29_global_expansion'
OUT_DIR = ROOT / 'output/experiments/facility_registry'
OUT_CSV = OUT_DIR / 'facility_registry_bottleneck.csv'

# (iso3, service, resource-name substring in independent_facility_registries.csv)
CASES = [
    ('IDN', 'health', 'IDN_health_facilities_hospital.zip'),
    ('KGZ', 'health', 'kgz_hltfac_gov_shp.zip'),
    ('KHM', 'health', 'health_facility.zip'),
    ('NPL', 'health', 'npl_hltfac_doh_who_wgs84.zip'),
    ('PNG', 'health', 'png_hltfacp_2000_nso_edit.zip'),
    ('HND', 'education', 'hnd_education_facilities.zip'),
    ('IDN', 'education', 'IDN_school_facilities.zip'),
    ('KGZ', 'education', 'kgz_edufac_unicef_shp.zip'),
    ('KHM', 'education', 'khm_edufacp_gov.zip'),
    ('PNG', 'education', 'png_edup_2000_nso_edit.zip'),
    ('SEN', 'education', 'sen_school_mapaction.zip'),
    ('LKA', 'education', 'sri-lanka-school-geolocation-connectivity-data.csv'),
]


def _stamp(t0, msg):
    print(f'[{time.strftime("%H:%M:%S")}] {msg} (elapsed {time.time() - t0:,.0f}s)', flush=True)


def download_resource(iso: str, name: str, url: str) -> Path:
    target = ROOT / 'data/external/hdx/countries' / iso / 'registry'
    target.mkdir(parents=True, exist_ok=True)
    dest = target / name
    if dest.exists() and dest.stat().st_size > 0:
        return dest
    import requests
    for attempt in range(4):
        try:
            with requests.get(url, stream=True, timeout=600) as r:
                r.raise_for_status()
                with dest.open('wb') as f:
                    for chunk in r.iter_content(chunk_size=1 << 20):
                        if chunk:
                            f.write(chunk)
            break
        except Exception as exc:
            print(f'  retry {attempt + 1}/4 {name}: {type(exc).__name__}', flush=True)
            time.sleep(5 * (attempt + 1))
    else:
        raise RuntimeError(f'download failed: {name}')
    if dest.suffix.lower() == '.zip':
        extract = target / dest.stem
        if not extract.exists():
            extract.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(dest) as zf:
                for member in zf.infolist():
                    if member.filename.lower().endswith('.lock'):
                        continue
                    out = (extract / member.filename).resolve()
                    if str(out).startswith(str(extract.resolve())) and len(str(out)) < 250:
                        zf.extract(member, extract)
    return dest


def load_registry(path: Path, service: str) -> gpd.GeoDataFrame:
    if path.suffix.lower() == '.csv':
        df = pd.read_csv(path)
        xcol = next((c for c in df.columns if c.lower() in ('x', 'lon', 'longitude')), None)
        ycol = next((c for c in df.columns if c.lower() in ('y', 'lat', 'latitude')), None)
        if xcol is None or ycol is None:
            raise ValueError(f'no coordinate columns in {path.name}')
        g = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df[xcol], df[ycol]), crs=4326)
    else:
        files = sorted(path.parent.rglob('*.shp')) + sorted(path.parent.rglob('*.geojson'))
        if not files:
            raise FileNotFoundError(f'no vector file under {path.parent}')
        g = gpd.read_file(files[0])
        if g.crs is None:
            g = g.set_crs(4326)
        g = g.to_crs(4326)
    g = g[g.geometry.notna() & ~g.geometry.is_empty]
    # keep the health-relevant subset when the layer exposes a type field
    for col in ('amenity', 'facility_type', 'type', 'fac_type', 'health_facility_type'):
        if col in g.columns:
            vals = g[col].astype(str).str.lower()
            keep = vals.str.contains('hospital|clinic|health cent|health_cent|phc', regex=True)
            if keep.sum() >= 0.2 * len(g):
                g = g[keep]
            break
    return g


def run_case(iso: str, service: str, registry: gpd.GeoDataFrame) -> dict:
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
    vals = {'health': ['hospital', 'clinic'], 'education': ['school']}[service]
    osm = canon.load_facilities(iso, service)
    osm = osm[osm.amenity.astype(str).isin(vals)].copy()
    reg = registry
    if reg.crs is None:
        reg = reg.set_crs(4326)
    reg = reg.to_crs(4326)
    union = gpd.GeoDataFrame(pd.concat([osm[['geometry']], reg[['geometry']]], ignore_index=True),
                             geometry='geometry', crs=4326)
    src_osm, snap_osm = canon.source_nodes(osm, nodes, tree)
    src_union, snap_union = canon.source_nodes(union, nodes, tree)
    out = {'iso3': iso, 'service': service, 'osm_records': len(osm),
           'registry_records': len(reg), 'osm_source_nodes': len(src_osm),
           'union_source_nodes': len(src_union),
           'registry_snap_median_m': float(np.median(snap_union)) if len(snap_union) else np.nan,
           'registry_snap_within_1km_pct': float(100 * np.mean(np.asarray(snap_union) <= 1000))
           if len(snap_union) else np.nan}
    for label, src in (('osm', src_osm), ('union', src_union)):
        if not src:
            continue
        dist = dijkstra(csr, directed=False, indices=np.asarray(sorted(src), dtype=np.int32),
                        min_only=True)
        d = dist[cells]
        valid = np.isfinite(d)
        for wlabel, pop in (('counts', counts), ('density', density)):
            out[f'share_60min_{label}_{wlabel}'] = 100 * pop[valid & (d <= 60)].sum() / pop.sum()
            out[f'share_30min_{label}_{wlabel}'] = 100 * pop[valid & (d <= 30)].sum() / pop.sum()
        del dist, d
        gc.collect()
    out['registry_gain_60min_pp'] = out.get('share_60min_union_counts', np.nan) - out.get(
        'share_60min_osm_counts', np.nan)
    out['registry_gain_30min_pp'] = out.get('share_30min_union_counts', np.nan) - out.get(
        'share_30min_osm_counts', np.nan)
    _stamp(t0, f'{iso} {service}: +{out["registry_gain_60min_pp"]:.2f} pp (60 min)')
    gc.collect()
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--cases', nargs='+', default=None)
    a = ap.parse_args()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    catalogue = pd.read_csv(EXP / 'independent_facility_registries.csv')
    rows = []
    for iso, service, needle in CASES:
        if a.cases and not any(f'{iso}_{service}' == c for c in a.cases):
            continue
        hit = catalogue[(catalogue.iso3 == iso)
                        & (catalogue.resource_name.astype(str).str.contains(needle.split('.')[0], regex=False))]
        if hit.empty:
            print(f'{iso} {service}: resource {needle} not in catalogue, skipping')
            continue
        url = hit.iloc[0].url
        try:
            path = download_resource(iso, needle, url)
            registry = load_registry(path, service)
        except Exception as exc:
            print(f'{iso} {service}: {type(exc).__name__} {exc} - skipping', flush=True)
            continue
        rows.append(run_case(iso, service, registry))
        pd.DataFrame(rows).to_csv(OUT_CSV, index=False, encoding='utf-8-sig')
    if rows:
        df = pd.DataFrame(rows)
        df.to_csv(OUT_CSV, index=False, encoding='utf-8-sig')
        pd.set_option('display.width', 250)
        print(f'wrote {OUT_CSV} ({len(df)} cases)')
        print(df[['iso3', 'service', 'osm_records', 'registry_records', 'osm_source_nodes',
                  'union_source_nodes', 'registry_snap_within_1km_pct',
                  'share_60min_osm_counts', 'share_60min_union_counts',
                  'registry_gain_60min_pp']].round(2).to_string(index=False))
    print('done')


if __name__ == '__main__':
    main()
