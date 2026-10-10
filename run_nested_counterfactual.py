# -*- coding: utf-8 -*-
"""Reviewer-requested nested counterfactual + decomposition of the local-road
correction (review item R1).

Why this exists
---------------
The published delta (corrected - arterial-only) compares two *different* pipelines:

  * ``arterial_60min_pct``  <- run_experiment_06_ablation.prepare_roads/build_variant_graphs
                               (Planet arterial layer only, M3 speeds), with population
                               cells and facilities snapped to *that* graph's nodes;
  * ``noded_60min_pct``     <- Planet+OSM union graph (run_experiment_24 ...), with
                               population cells and facilities snapped to *its* nodes.

Because the origin and facility snapping bases differ, the two networks are not
nested and a negative delta cannot be attributed to "adding local roads" (adding
an edge to a fixed graph can never increase a shortest-path travel time).

This script re-measures the same quantity on ONE node basis, using the cached
``{iso}_noded_segments.gpkg`` products, so that every scenario shares the same node
coordinates, the same population cells and the same facility set:

  A          arterial-only edges, origins/facilities snapped to arterial ("shared") nodes
  B_shared   all edges,          origins/facilities snapped to the SAME shared nodes   (A subset of B_shared)
  B_full     all edges,          origins/facilities snapped to all nodes  (= canonical pipeline)
  B_speed115 all edges with travel times / 1.15  (global speed calibration, item R5)
  B_speed130 all edges with travel times / 1.30

Decomposition of the published delta for each country-service:

  delta_published = corrected_60min_pct - arterial_60min_pct
  delta_edges     = B_shared - A              (pure local-edge effect, >= 0 by construction)
  delta_snapping  = B_full   - B_shared       (effect of the snapping/coverage basis)
  delta_residual  = delta_published - delta_edges - delta_snapping
                  (attribute inheritance + the two different arterial implementations)

Usage:
  python run_nested_counterfactual.py --countries PNG MLI ZMB NPL TZA
"""
from __future__ import annotations

import argparse
import gc
import time
from pathlib import Path

import numpy as np
import pandas as pd
import pyogrio
import shapely
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import dijkstra
from scipy.spatial import cKDTree

import prototype_multicountry_access as base

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'output/experiments/nested_counterfactual'
CHUNK = 750_000
COUNTRY_DIR = ROOT / 'data/external/hdx/countries'


def facilities(iso: str, kind: str):
    """Robust facility loader: handles both the split (points/polygons) and the
    single-file HOT exports, for core and expansion countries alike."""
    import geopandas as gpd

    parts = []
    cands = [COUNTRY_DIR / iso / f'hotosm_{iso.lower()}_{kind}_facilities_{geom}_gpkg'
             for geom in ('points', 'polygons')]
    cands.append(COUNTRY_DIR / iso / f'hotosm_{iso.lower()}_{kind}_facilities_osm_gpkg')
    for pattern in cands:
        for file in sorted(pattern.rglob('*.gpkg')):
            try:
                gdf = gpd.read_file(file)
            except Exception:
                continue
            if len(gdf):
                parts.append(gdf)
    if not parts:
        raise FileNotFoundError(f'no facility gpkg for {iso} {kind}')
    out = gpd.GeoDataFrame(pd.concat(parts, ignore_index=True), crs=parts[0].crs)
    return out.to_crs(4326)


def _log(msg):
    print(msg, flush=True)


def _coords_path(iso: str) -> Path:
    """Resolve the cached noded-segment gpkg (MOZ is stored as 'mozambique_*')."""
    d = ROOT / 'data/external/hdx/countries' / iso / 'local_roads'
    cands = [p for p in sorted(d.glob('*_noded_segments.gpkg')) if 'tiled' not in p.name]
    if not cands:
        raise FileNotFoundError(f'no noded segments under {d}')
    return cands[0]


def load_segments(iso: str) -> dict:
    """Stream the noded-segment gpkg: endpoint coordinates (rounded to 7 decimals,
    the canonical node key) plus the attributes that define each edge."""
    path = _coords_path(iso)
    info = pyogrio.read_info(path)
    n = int(info['features'])
    u_all, v_all, w_all, art_all, haz_all = [], [], [], [], []
    xs_u, ys_u, xs_v, ys_v = [], [], [], []
    for start in range(0, n, CHUNK):
        meta, tbl = pyogrio.read_arrow(path, columns=['source', 'travel_time_min',
                                                      'hazard_intersect'],
                                       skip_features=start, max_features=CHUNK)
        geom_col = meta['geometry_name'] if meta.get('geometry_name') else 'wkb_geometry'
        geom = shapely.from_wkb(tbl.column(geom_col).to_numpy())
        src = tbl.column('source').to_numpy(zero_copy_only=False)
        w = tbl.column('travel_time_min').to_numpy(zero_copy_only=False).astype('float64')
        haz = np.asarray(tbl.column('hazard_intersect').to_numpy(zero_copy_only=False), dtype=bool)
        coords = shapely.get_coordinates(geom)
        counts = shapely.get_num_coordinates(geom)
        first = np.concatenate(([0], np.cumsum(counts)[:-1]))
        last = np.cumsum(counts) - 1
        xs_u.append(coords[first, 0]); ys_u.append(coords[first, 1])
        xs_v.append(coords[last, 0]); ys_v.append(coords[last, 1])
        art_all.append(src == 'planet_arterial')
        w_all.append(w); haz_all.append(haz)
        del tbl, geom, coords
        gc.collect()
    d = {
        'xu': np.concatenate(xs_u), 'yu': np.concatenate(ys_u),
        'xv': np.concatenate(xs_v), 'yv': np.concatenate(ys_v),
        'w': np.concatenate(w_all), 'art': np.concatenate(art_all),
        'haz': np.concatenate(haz_all),
    }
    return d


def build_nodes(d: dict):
    """Canonical node keys: (lon, lat) rounded to 7 decimals."""
    key_u = np.column_stack([np.round(d['xu'], 7), np.round(d['yu'], 7)])
    key_v = np.column_stack([np.round(d['xv'], 7), np.round(d['yv'], 7)])
    keys = np.unique(np.vstack([key_u, key_v]), axis=0)
    order = np.lexsort((keys[:, 1], keys[:, 0]))
    keys = keys[order]
    nid = np.full(len(keys), -1, dtype=np.int64)
    view = keys.view([('x', 'f8'), ('y', 'f8')]).ravel()
    lookup = pd.Series(np.arange(len(keys), dtype=np.int64), index=view)
    uv = np.column_stack([np.round(d['xu'], 7), np.round(d['yu'], 7)]).view([('x', 'f8'), ('y', 'f8')]).ravel()
    vv = np.column_stack([np.round(d['xv'], 7), np.round(d['yv'], 7)]).view([('x', 'f8'), ('y', 'f8')]).ravel()
    uid = lookup.reindex(uv).to_numpy()
    vid = lookup.reindex(vv).to_numpy()
    del nid
    return keys, uid.astype(np.int64), vid.astype(np.int64)


def csr_min(uid, vid, w, n_nodes, mask=None):
    """Symmetric min-weight CSR, matching the canonical 'min edge per node pair' rule."""
    if mask is not None:
        uid, vid, w = uid[mask], vid[mask], w[mask]
    keep = uid != vid
    uid, vid, w = uid[keep], vid[keep], w[keep]
    lo = np.minimum(uid, vid).astype(np.int64)
    hi = np.maximum(uid, vid).astype(np.int64)
    df = pd.DataFrame({'key': lo * np.int64(n_nodes) + hi, 'w': w})
    g = df.groupby('key', sort=False)['w'].min()
    key = g.index.to_numpy()
    ww = g.to_numpy()
    a = (key // n_nodes).astype(np.int64)
    b = (key % n_nodes).astype(np.int64)
    csr = csr_matrix((np.concatenate([ww, ww]),
                      (np.concatenate([a, b]), np.concatenate([b, a]))),
                     shape=(n_nodes, n_nodes))
    return csr


def access(csr, tree, id_map, cells3857, fac_xy, pop):
    """Access shares with origins and facilities snapped to the node set behind `tree`.

    ``id_map`` translates a tree position back to the global CSR node id (``None``
    when the tree was built on every node).
    """
    _, idx_cell = tree.query(cells3857)
    idx_cell = np.asarray(idx_cell)
    if id_map is not None:
        idx_cell = id_map[idx_cell]
    if len(fac_xy):
        dfac, ifac = tree.query(fac_xy)
        keep = np.asarray(dfac) <= 1000.0
        ifac = np.asarray(ifac)[keep]
        if id_map is not None:
            ifac = id_map[ifac]
        src = np.unique(ifac.astype(np.int64))
    else:
        src = np.array([], dtype=np.int64)
    out = {}
    if len(src) == 0:
        out['share_30min_pct'] = 0.0
        out['share_60min_pct'] = 0.0
        out['share_120min_pct'] = 0.0
        out['source_nodes'] = 0
        out['mean_travel_reachable_min'] = float('nan')
        return out
    dist = dijkstra(csr, indices=src, min_only=True)
    v = dist[idx_cell]
    valid = np.isfinite(v)
    out['source_nodes'] = int(len(src))
    out['mean_travel_reachable_min'] = float(np.average(v[valid], weights=pop[valid])) if valid.any() else float('nan')
    for t in (30, 60, 120):
        out[f'share_{t}min_pct'] = float(100 * pop[valid & (v <= t)].sum() / pop.sum())
    return out


def process(iso: str):
    t0 = time.time()
    d = load_segments(iso)
    keys, uid, vid = build_nodes(d)
    n_nodes = len(keys)
    _log(f'{iso}: segments={len(uid):,} nodes={n_nodes:,}')

    shared_mask_nodes = np.zeros(n_nodes, dtype=bool)
    shared_mask_nodes[uid[d['art']]] = True
    shared_mask_nodes[vid[d['art']]] = True
    n_shared = int(shared_mask_nodes.sum())

    csr_all = csr_min(uid, vid, d['w'], n_nodes)
    csr_art = csr_min(uid, vid, d['w'], n_nodes, mask=d['art'])
    csr_115 = csr_min(uid, vid, d['w'] / 1.15, n_nodes)
    csr_130 = csr_min(uid, vid, d['w'] / 1.30, n_nodes)
    _log(f'{iso}: CSR all nnz={csr_all.nnz:,} arterial-only nnz={csr_art.nnz:,} '
         f'({round(time.time() - t0, 1)}s)')

    x3857, y3857 = base.TRANSFORMER.transform(keys[:, 0], keys[:, 1])
    node3857 = np.column_stack([x3857, y3857])
    shared_ids = np.flatnonzero(shared_mask_nodes)
    tree_all = cKDTree(node3857)
    tree_shared = cKDTree(node3857[shared_ids])

    cellxy, cellxy3857, pop = base.load_population(iso)
    cells3857_xy = np.asarray(cellxy3857)

    fac = {}
    h = facilities(iso, 'health')
    e = facilities(iso, 'education')
    if 'amenity' not in h.columns or 'amenity' not in e.columns:
        raise KeyError(f'{iso}: facility export lacks the amenity column')
    h = h[h.amenity.isin(['hospital', 'clinic'])]
    e = e[e.amenity.eq('school')]
    for name, gdf in (('health', h), ('school', e)):
        pts = gdf.geometry.representative_point().to_crs(3857)
        fac[name] = np.column_stack([pts.geometry.x, pts.geometry.y])

    rows = []
    scenarios = [
        ('A_arterial_nested', csr_art, tree_shared, shared_ids),
        ('B_shared', csr_all, tree_shared, shared_ids),
        ('B_full', csr_all, tree_all, None),
        ('B_full_speed115', csr_115, tree_all, None),
        ('B_full_speed130', csr_130, tree_all, None),
    ]
    for scen, csr, tree, imap in scenarios:
        for service, xy in fac.items():
            r = access(csr, tree, imap, cells3857_xy, xy, pop)
            r.update({'iso3': iso, 'scenario': scen, 'service': service})
            rows.append(r)
        _log(f'{iso}: scenario {scen} done ({round(time.time() - t0, 1)}s)')
    df = pd.DataFrame(rows)
    df['n_nodes'] = n_nodes
    df['n_shared_nodes'] = n_shared
    df['n_segments'] = len(uid)
    return df


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--countries', nargs='+', required=True)
    ap.add_argument('--outdir', default=str(OUT))
    a = ap.parse_args()
    outdir = Path(a.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    for iso in a.countries:
        target = outdir / f'{iso.lower()}_nested_counterfactual.csv'
        if target.exists():
            _log(f'{iso}: cached, skip')
            continue
        try:
            df = process(iso)
            df.to_csv(target, index=False, encoding='utf-8-sig')
            _log(f'{iso}: wrote {target.name}')
        except Exception as exc:  # keep the batch going, report the failure
            _log(f'{iso}: FAILED {type(exc).__name__} {exc}')
            raise


if __name__ == '__main__':
    main()
