# -*- coding: utf-8 -*-
"""Access-cost grid for the reviewer's request that the zero-cost snapping be
upgraded from a sensitivity knob to the main identification axis.

For each country-service we report the population-weighted 60-min share and the
pure edge increment (full minus arterial, same snap basis) across a grid of
explicit access-cost assumptions:
    access_time(min) = distance(m) * circuity / (speed_kmh * 1000) * 60
with circuity in {1.2, 1.4, 1.6} and speed in {3, 5, 6, 10} km/h (3/5/6 walking,
10 slow motorised).  Zero cost is the reference (scale = 0).

The share is computed once per country from the per-cell road time and distance
arrays (no extra dijkstra), so the grid is cheap after the network load.
"""
from __future__ import annotations

import argparse
import time
from pathlib import Path

import numpy as np
import pandas as pd

import run_nested_counterfactual as rnc

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'output/experiments/access_cost_grid'

GRID = [('zero', 0.0),
        ('k1.2_v10', 1.2 * 60 / 10000), ('k1.2_v5', 1.2 * 60 / 5000),
        ('k1.2_v3', 1.2 * 60 / 3000),
        ('k1.4_v10', 1.4 * 60 / 10000), ('k1.4_v6', 1.4 * 60 / 6000),
        ('k1.4_v5', 1.4 * 60 / 5000), ('k1.4_v3', 1.4 * 60 / 3000),
        ('k1.6_v5', 1.6 * 60 / 5000), ('k1.6_v3', 1.6 * 60 / 3000)]


def _share(road: np.ndarray, dist: np.ndarray, pop: np.ndarray, scale: float) -> float:
    total = float(pop.sum())
    if scale == 0.0:
        ok = np.isfinite(road) & (road <= 60)
    else:
        walk = dist * scale
        ok = np.isfinite(road) & ((road + walk) <= 60)
    return float(100 * pop[ok].sum() / total) if total > 0 else 0.0


def _cached_iso_list() -> list[str]:
    return sorted(p.name.split('_')[0].upper()
                  for p in (ROOT / 'output/experiments/nested_counterfactual')
                  .glob('*_nested_counterfactual.csv'))


def process(iso: str) -> pd.DataFrame:
    d = rnc.load_segments(iso)
    keys, uid, vid = rnc.build_nodes(d)
    n_nodes = len(keys)
    shared_mask = np.zeros(n_nodes, dtype=bool)
    shared_mask[uid[d['art']]] = True
    shared_mask[vid[d['art']]] = True
    shared_ids = np.flatnonzero(shared_mask)
    csr_all = rnc.csr_min(uid, vid, d['w'], n_nodes)
    csr_art = rnc.csr_min(uid, vid, d['w'], n_nodes, mask=d['art'])
    x3857, y3857 = rnc.base.TRANSFORMER.transform(keys[:, 0], keys[:, 1])
    node3857 = np.column_stack([x3857, y3857])
    tree_all = rnc.cKDTree(node3857)
    tree_shared = rnc.cKDTree(node3857[shared_ids])
    cellxy, cellxy3857, pop = rnc.base.load_population(iso)
    cells = np.asarray(cellxy3857)
    d_all, cell_all = tree_all.query(cells)
    d_art, cell_art = tree_shared.query(cells)
    cell_all = np.asarray(cell_all); cell_art = np.asarray(cell_art)
    cell_art_global = shared_ids[cell_art]

    fac_all, fac_art = {}, {}
    for name, kind in (('health', 'health'), ('school', 'education')):
        gdf = rnc.facilities(iso, kind)
        gdf = (gdf[gdf.amenity.isin(['hospital', 'clinic'])] if kind == 'health'
               else gdf[gdf.amenity.eq('school')])
        pts = gdf.geometry.representative_point().to_crs(3857)
        xy = np.column_stack([pts.geometry.x, pts.geometry.y])
        da, ia = tree_all.query(xy)
        fac_all[name] = np.unique(np.asarray(ia)[np.asarray(da) <= 1000].astype(np.int64))
        ds, ish = tree_shared.query(xy)
        fac_art[name] = np.unique(np.asarray(ish)[np.asarray(ds) <= 1000].astype(np.int64))

    rows = []
    for svc in fac_all:
        src = fac_all[svc]; src_art = fac_art[svc]
        if len(src) == 0:
            continue
        road_full = rnc.dijkstra(csr_all, indices=src, min_only=True)[cell_all]
        src_art_global = shared_ids[src_art]
        road_art = rnc.dijkstra(csr_art, indices=src_art_global, min_only=True)[cell_art_global]
        svc_name = 'health' if svc == 'health' else 'education'
        for name, scale in GRID:
            sf = _share(road_full, np.asarray(d_all), pop, scale)
            sa = _share(road_art, np.asarray(d_art), pop, scale)
            rows.append({'iso3': iso, 'service': svc_name, 'assumption': name,
                         'scale': scale, 'full_60min': sf, 'arterial_60min': sa,
                         'edge_pp': sf - sa})
    return pd.DataFrame(rows)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--countries', nargs='*', default=None)
    a = ap.parse_args()
    isos = [c.upper() for c in a.countries] if a.countries else _cached_iso_list()
    OUT.mkdir(parents=True, exist_ok=True)
    frames = []
    for iso in isos:
        t0 = time.time()
        df = process(iso)
        df.to_csv(OUT / f'{iso.lower()}_access_grid.csv', index=False, encoding='utf-8-sig')
        frames.append(df)
        print(f'{iso}: edge zero={df[df.assumption=="zero"].edge_pp.mean():+.1f} pp, '
              f'edge walk5={df[df.assumption=="k1.4_v5"].edge_pp.mean():+.1f} pp '
              f'({time.time()-t0:.1f}s)', flush=True)
    allf = pd.concat(frames, ignore_index=True)
    allf.to_csv(OUT / 'access_grid_all.csv', index=False, encoding='utf-8-sig')
    piv = allf.pivot_table(index='assumption', values='edge_pp', aggfunc=['mean', 'min', 'max'])
    print('\n=== edge increment (full - arterial) by access-cost assumption ===')
    print(piv.round(2).to_string())


if __name__ == '__main__':
    main()
