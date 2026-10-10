# -*- coding: utf-8 -*-
"""Missing-road stress test (review item: "systematically handle network data
missingness and non-random omission").  Quantifies how the 60-minute share and the
pure local-edge effect respond when observed local roads are thinned.

For each country we recompute the full-network snap share under:
  - random deletion of 10% / 25% / 50% of local (OSM motorable) edges
  - deletion of all *unpaved* local edges  (surface-selective omission)
  - deletion of all *minor-hierarchy* local edges (residential/track/service/...)

and compare against the intact B_full share and the intact pure edge effect
(B_full - A).  A representative subset of countries is used (the review frames
this as a demonstration, not a 30-country claim).

Usage:
  python run_missing_road_stress.py
"""
from __future__ import annotations

import time
from pathlib import Path

import numpy as np
import pandas as pd
import pyogrio

import run_nested_counterfactual as rnc

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'output/experiments/missing_road_stress'

SUBSET = ['KHM', 'GTM', 'BGD', 'SEN', 'NGA', 'ETH', 'MOZ', 'PNG', 'EGY', 'TUR']
MINOR_HW = {'residential', 'track', 'service', 'unclassified', 'living_street',
            'footway', 'path', 'bridleway', 'cycleway', 'steps', 'pedestrian'}


def _surface(iso: str) -> tuple[np.ndarray, np.ndarray]:
    """Load the per-segment surface_class / highway arrays once."""
    path = rnc._coords_path(iso)
    info = pyogrio.read_info(path)
    n = int(info['features'])
    surfs, hws = [], []
    for start in range(0, n, rnc.CHUNK):
        meta, tbl = pyogrio.read_arrow(path, columns=['surface_class', 'highway'],
                                       skip_features=start, max_features=rnc.CHUNK)
        surfs.append(tbl.column('surface_class').to_numpy(zero_copy_only=False))
        hws.append(tbl.column('highway').to_numpy(zero_copy_only=False))
    surf = np.concatenate(surfs)
    hw = np.concatenate(hws)
    return surf, hw


def process(iso: str) -> pd.DataFrame:
    t0 = time.time()
    d = rnc.load_segments(iso)
    keys, uid, vid = rnc.build_nodes(d)
    n_nodes = len(keys)
    art = d['art']
    local = ~art

    surf, hw = _surface(iso)
    # ensure length matches (should equal the segment count from load_segments)
    assert len(surf) == len(uid), f'{iso}: surface length mismatch {len(surf)} vs {len(uid)}'
    unpaved = surf == 'unpaved'
    minor = np.isin(hw, list(MINOR_HW))

    csr_all = rnc.csr_min(uid, vid, d['w'], n_nodes)
    csr_art = rnc.csr_min(uid, vid, d['w'], n_nodes, mask=art)
    x3857, y3857 = rnc.base.TRANSFORMER.transform(keys[:, 0], keys[:, 1])
    node3857 = np.column_stack([x3857, y3857])
    tree_all = rnc.cKDTree(node3857)
    shared_mask = np.zeros(n_nodes, dtype=bool)
    shared_mask[uid[art]] = True
    shared_mask[vid[art]] = True
    tree_shared = rnc.cKDTree(node3857[np.flatnonzero(shared_mask)])

    cellxy, cellxy3857, pop = rnc.base.load_population(iso)
    cells3857_xy = np.asarray(cellxy3857)

    def shares(csr):
        out = {}
        for kind in ('health', 'education'):
            gdf = rnc.facilities(iso, kind)
            gdf = (gdf[gdf.amenity.isin(['hospital', 'clinic'])] if kind == 'health'
                   else gdf[gdf.amenity.eq('school')])
            pts = gdf.geometry.representative_point().to_crs(3857)
            xy = np.column_stack([pts.geometry.x, pts.geometry.y])
            out[kind] = rnc.access(csr, tree_all, None, cells3857_xy, xy, pop)
        return out

    base = shares(csr_all)
    base_art = shares(csr_art)
    rng = np.random.default_rng(20261003)

    rows = []
    # intact baseline
    for svc in ('health', 'education'):
        rows.append({'iso3': iso, 'service': svc, 'scenario': 'intact',
                     'share_60min_pct': base[svc]['share_60min_pct'],
                     'edge_effect_pp': base[svc]['share_60min_pct']
                                      - base_art[svc]['share_60min_pct'],
                     'deleted_local_frac': 0.0})

    scenarios = []
    for frac in (0.10, 0.25, 0.50):
        mask_del = local & (rng.random(len(uid)) < frac)
        scenarios.append((f'random_{int(frac*100)}pct', mask_del, frac))
    scenarios.append(('unpaved_local', local & unpaved,
                      float((local & unpaved).sum()) / max(local.sum(), 1)))
    scenarios.append(('minor_hierarchy', local & minor,
                      float((local & minor).sum()) / max(local.sum(), 1)))

    for name, mask_del, del_frac in scenarios:
        keep = ~mask_del
        csr_del = rnc.csr_min(uid, vid, d['w'], n_nodes, mask=keep)
        sh = shares(csr_del)
        for svc in ('health', 'education'):
            rows.append({'iso3': iso, 'service': svc, 'scenario': name,
                         'share_60min_pct': sh[svc]['share_60min_pct'],
                         'edge_effect_pp': sh[svc]['share_60min_pct']
                                          - base_art[svc]['share_60min_pct'],
                         'deleted_local_frac': del_frac})
        print(f'{iso}: {name} (deleted {del_frac:.2f} of local) '
              f'({time.time()-t0:.1f}s)', flush=True)
    return pd.DataFrame(rows)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    frames = []
    for iso in SUBSET:
        try:
            df = process(iso)
            df.to_csv(OUT / f'{iso.lower()}_stress.csv', index=False, encoding='utf-8-sig')
            frames.append(df)
        except Exception as exc:
            print(f'{iso}: FAILED {type(exc).__name__} {exc}', flush=True)
            raise
    allf = pd.concat(frames, ignore_index=True)
    allf.to_csv(OUT / 'stress_all.csv', index=False, encoding='utf-8-sig')
    piv = allf.pivot_table(index=['iso3', 'service'], columns='scenario',
                           values='share_60min_pct')
    drop = piv['intact'] - piv[[c for c in piv.columns if c != 'intact']]
    print('\n=== mean 60-min share drop vs intact (pp), across the subset ===')
    print(drop.mean().round(2).to_string())
    print('\n=== edge effect under deletion (pp), mean ===')
    ep = allf.pivot_table(index=['iso3', 'service'], columns='scenario',
                          values='edge_effect_pp')
    print(ep.mean().round(2).to_string())


if __name__ == '__main__':
    main()
