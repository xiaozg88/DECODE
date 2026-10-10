# -*- coding: utf-8 -*-
"""Shapley / two-order decomposition of the local-road delta (review items:
"handle path dependence", "use order-invariant or Shapley decomposition").

The published decomposition used the order  edges-first  (A -> B_shared -> B_full):
    edge_1 = B_shared - A          (add local edges, hold snapping at arterial nodes)
    snap_1 = B_full  - B_shared    (change snapping, hold edges at full network)

This script adds the missing fourth scenario  A_snap  (arterial edges, but origins
and facilities snapped to the FULL network's nearest nodes), giving the opposite
order  snapping-first  (A -> A_snap -> B_full):
    snap_0 = A_snap - A
    edge_2 = B_full - A_snap

Shapley (order-averaged) components:
    shapley_edge = (edge_1 + edge_2) / 2
    shapley_snap = (snap_0 + snap_1) / 2      ->  edge + snap == B_full - A exactly

The spread across the two orders is reported as the path-dependence range.

Usage:
  python run_shapley_decomposition.py --countries KGZ RWA JOR ...
  (omit --countries to process all 30 cached countries)
"""
from __future__ import annotations

import argparse
import time
from pathlib import Path

import numpy as np
import pandas as pd

import run_nested_counterfactual as rnc

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'output/experiments/shapley_decomposition'
NEST = ROOT / 'output/experiments/nested_counterfactual'


def _cached_iso_list() -> list[str]:
    return sorted(p.name.split('_')[0].upper() for p in NEST.glob('*_nested_counterfactual.csv'))


def process(iso: str) -> pd.DataFrame:
    d = rnc.load_segments(iso)
    keys, uid, vid = rnc.build_nodes(d)
    n_nodes = len(keys)
    shared_mask = np.zeros(n_nodes, dtype=bool)
    shared_mask[uid[d['art']]] = True
    shared_mask[vid[d['art']]] = True
    shared_ids = np.flatnonzero(shared_mask)

    csr_art = rnc.csr_min(uid, vid, d['w'], n_nodes, mask=d['art'])
    x3857, y3857 = rnc.base.TRANSFORMER.transform(keys[:, 0], keys[:, 1])
    node3857 = np.column_stack([x3857, y3857])
    tree_all = rnc.cKDTree(node3857)
    tree_shared = rnc.cKDTree(node3857[shared_ids])

    cellxy, cellxy3857, pop = rnc.base.load_population(iso)
    cells3857_xy = np.asarray(cellxy3857)

    fac = {}
    for name, kind in (('health', 'health'), ('school', 'education')):
        gdf = rnc.facilities(iso, kind)
        if kind == 'health':
            gdf = gdf[gdf.amenity.isin(['hospital', 'clinic'])]
        else:
            gdf = gdf[gdf.amenity.eq('school')]
        pts = gdf.geometry.representative_point().to_crs(3857)
        fac[name] = np.column_stack([pts.geometry.x, pts.geometry.y])

    # cached A / B_shared / B_full (already deposited)
    cache = pd.read_csv(NEST / f'{iso.lower()}_nested_counterfactual.csv')
    def cached(scen, service, col='share_60min_pct'):
        return float(cache[(cache.scenario == scen) & (cache.service == service)][col].iloc[0])

    rows = []
    for service, xy in fac.items():
        A = cached('A_arterial_nested', service)
        Bs = cached('B_shared', service)
        Bf = cached('B_full', service)
        As = rnc.access(csr_art, tree_all, None, cells3857_xy, xy, pop)['share_60min_pct']
        edge_1 = Bs - A
        edge_2 = Bf - As
        snap_0 = As - A
        snap_1 = Bf - Bs
        rows.append({
            'iso3': iso, 'service': 'health' if service == 'health' else 'education',
            'A_arterial': A, 'A_snap': As, 'B_shared': Bs, 'B_full': Bf,
            'edge_first': edge_1, 'edge_second': edge_2,
            'snap_first': snap_0, 'snap_second': snap_1,
            'shapley_edge': (edge_1 + edge_2) / 2,
            'shapley_snap': (snap_0 + snap_1) / 2,
            'path_range_edge': abs(edge_1 - edge_2),
            'path_range_snap': abs(snap_0 - snap_1),
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
            df.to_csv(OUT / f'{iso.lower()}_shapley.csv', index=False, encoding='utf-8-sig')
            frames.append(df)
            print(f'{iso}: shapley_edge={df.shapley_edge.mean():+.2f} '
                  f'shapley_snap={df.shapley_snap.mean():+.2f} '
                  f'path_edge={df.path_range_edge.max():.2f} '
                  f'path_snap={df.path_range_snap.max():.2f} ({time.time()-t0:.1f}s)',
                  flush=True)
        except Exception as exc:
            print(f'{iso}: FAILED {type(exc).__name__} {exc}', flush=True)
            raise
    if frames:
        allf = pd.concat(frames, ignore_index=True)
        allf.to_csv(OUT / 'shapley_all_countries.csv', index=False, encoding='utf-8-sig')
        # merge with arterial coverage for interpretation
        dec = pd.read_csv(ROOT / 'output/experiments/direction_law_v2/nested_decomposition.csv')
        m = allf.merge(dec[['iso3', 'service', 'arterial_coverage', 'delta_published',
                            'delta_edges', 'delta_snapping', 'delta_residual']],
                       on=['iso3', 'service'], how='left')
        m.to_csv(OUT / 'shapley_merged.csv', index=False, encoding='utf-8-sig')
        s = allf[['shapley_edge', 'shapley_snap', 'path_range_edge', 'path_range_snap']].agg(
            ['mean', 'min', 'max'])
        print('\n=== Shapley summary (pp) ===')
        print(s.round(2).to_string())
        print(f'\nedge+snap vs total: mean residual '
              f'{(allf.shapley_edge + allf.shapley_snap - (allf.B_full - allf.A_arterial)).abs().max():.4f}')


if __name__ == '__main__':
    main()
