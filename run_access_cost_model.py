# -*- coding: utf-8 -*-
"""Explicit access-cost (last-mile) model for all 30 countries (review item:
"replace zero-cost nearest-node snapping with an explicit access-cost model and
re-run 30 countries").

The zero-cost convention snaps each population cell to its nearest road node and
adds no access time.  Here we add a per-cell off-network access time
    access_time(min) = distance(m) * circuity / (speed_kmh * 1000) * 60
using two speeds:
  * walk5  = 5 km/h  (standard walking)  + circuity 1.4
  * slow20 = 20 km/h (slow motorised, matching SI S8) + circuity 1.4

For each country-service we recompute, on the full network (B_full) and the
arterial-only network (A), the 60-min share under zero-cost vs each access-cost
speed, so we can report (i) the access-cost effect on the absolute share and
(ii) whether the pure edge effect (full minus arterial) stays non-negative once
the access cost is explicit.

Usage:
  python run_access_cost_model.py --countries KGZ RWA ...
  (omit --countries to process all 30)
"""
from __future__ import annotations

import argparse
import time
from pathlib import Path

import numpy as np
import pandas as pd

import run_nested_counterfactual as rnc

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'output/experiments/access_cost_model'
CIRCUITY = 1.4


def _access_time(dist_m: np.ndarray, speed_kmh: float) -> np.ndarray:
    return dist_m * CIRCUITY / (speed_kmh * 1000.0) * 60.0


def _share(values: np.ndarray, pop: np.ndarray, threshold=60.0) -> float:
    ok = np.isfinite(values)
    return float(100 * pop[ok & (values <= threshold)].sum() / pop.sum())


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
    # tree_shared is built on the arterial-node SUBSET, so its query indices are
    # local positions that must be mapped back to global node ids.
    cell_art_global = shared_ids[cell_art]
    w5_all = _access_time(np.asarray(d_all), 5.0)
    w20_all = _access_time(np.asarray(d_all), 20.0)
    w5_art = _access_time(np.asarray(d_art), 5.0)
    w20_art = _access_time(np.asarray(d_art), 20.0)

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
        src = fac_all[svc]
        src_art = fac_art[svc]
        if len(src) == 0:
            continue
        road_full = rnc.dijkstra(csr_all, indices=src, min_only=True)[cell_all]
        src_art_global = shared_ids[src_art]
        road_art = rnc.dijkstra(csr_art, indices=src_art_global,
                                min_only=True)[cell_art_global]
        rows.append({
            'iso3': iso, 'service': 'health' if svc == 'health' else 'education',
            'full_zero_60': _share(road_full, pop),
            'full_walk5_60': _share(road_full + w5_all, pop),
            'full_slow20_60': _share(road_full + w20_all, pop),
            'arterial_zero_60': _share(road_art, pop),
            'arterial_walk5_60': _share(road_art + w5_art, pop),
            'arterial_slow20_60': _share(road_art + w20_art, pop),
            'edge_zero_pp': _share(road_full, pop) - _share(road_art, pop),
            'edge_walk5_pp': (_share(road_full + w5_all, pop)
                              - _share(road_art + w5_art, pop)),
        })
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
        try:
            df = process(iso)
            df.to_csv(OUT / f'{iso.lower()}_access_cost.csv', index=False,
                      encoding='utf-8-sig')
            frames.append(df)
            print(f'{iso}: walk5 effect on full = '
                  f'{(df.full_walk5_60 - df.full_zero_60).mean():+.2f} pp, '
                  f'edge_walk5 = {df.edge_walk5_pp.mean():+.2f} pp '
                  f'({time.time()-t0:.1f}s)', flush=True)
        except Exception as exc:
            print(f'{iso}: FAILED {type(exc).__name__} {exc}', flush=True)
            raise
    if frames:
        allf = pd.concat(frames, ignore_index=True)
        allf.to_csv(OUT / 'access_cost_all_countries.csv', index=False,
                    encoding='utf-8-sig')
        allf['walk5_effect_pp'] = allf.full_walk5_60 - allf.full_zero_60
        allf['slow20_effect_pp'] = allf.full_slow20_60 - allf.full_zero_60
        print('\n=== access-cost effect on full-network 60-min share (pp) ===')
        print(allf[['walk5_effect_pp', 'slow20_effect_pp']].agg(['mean', 'min', 'max'])
              .round(2).to_string())
        print('\n=== pure edge effect (full - arterial), zero vs walk5 (pp) ===')
        print(allf[['edge_zero_pp', 'edge_walk5_pp']].agg(['mean', 'min', 'max'])
              .round(2).to_string())
        print('\nedge_walk5 negative rows:',
              int((allf.edge_walk5_pp < 0).sum()), '/', len(allf))


if __name__ == '__main__':
    main()
