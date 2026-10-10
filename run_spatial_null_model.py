# -*- coding: utf-8 -*-
"""Spatially-clustered placement null model for the exposure-loss relation
(review item: the equal-length random-placement null does not preserve the
spatial clustering of a real flood footprint).

Instead of drawing a *dispersed* same-length road set, this null draws a
*spatially clustered* set: a random centre is chosen in the country, then roads
are selected in increasing distance from that centre (a concentric disk) until
the observed affected unpaved length and affected paved length are matched.
The surface-aware rule (unpaved impassable, paved doubled) is then re-applied.

Comparing observed loss, dispersed-null loss (hazard_null_model.csv) and
clustered-null loss tells us whether any additional location effect survives
once the null preserves clustering.

Usage:
  python run_spatial_null_model.py --countries MOZ PAK --draws 10
"""
from __future__ import annotations

import argparse
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.sparse.csgraph import dijkstra
from scipy.spatial import cKDTree

import run_hazard_null_model as hz
import prototype_multicountry_access as base

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'output/experiments/spatial_null_model'


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--countries', nargs='+', default=['MOZ', 'PAK'])
    ap.add_argument('--draws', type=int, default=10)
    ap.add_argument('--seed', type=int, default=20261003)
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(a.seed)
    rows = []
    for iso in a.countries:
        t0 = time.time()
        d = hz.load_segments(iso)
        keys, uid, vid = hz.node_ids(d)
        n = len(keys)
        csr0 = hz.csr_min(uid, vid, d['w'], n)
        # segment midpoints in EPSG:3857 for the distance-to-centre sort
        mx = (d['xu'] + d['xv']) / 2.0
        my = (d['yu'] + d['yv']) / 2.0
        mx3857, my3857 = base.TRANSFORMER.transform(mx, my)
        mxy = np.column_stack([mx3857, my3857])
        lo_x, hi_x = mxy[:, 0].min(), mxy[:, 0].max()
        lo_y, hi_y = mxy[:, 1].min(), mxy[:, 1].max()

        _, cellxy3857, pop = base.load_population(iso)
        x3857, y3857 = base.TRANSFORMER.transform(keys[:, 0], keys[:, 1])
        tree = cKDTree(np.column_stack([x3857, y3857]))
        _, cell_nodes = tree.query(np.asarray(cellxy3857))
        cell_nodes = np.asarray(cell_nodes)
        fac = {}
        h = base.load_facilities(iso, 'health')
        h = h[h.amenity.isin(['hospital', 'clinic'])]
        e = base.load_facilities(iso, 'education')
        e = e[e.amenity.eq('school')]
        for name, gdf in (('health', h), ('school', e)):
            pts = gdf.geometry.representative_point().to_crs(3857)
            fxy = np.column_stack([pts.geometry.x, pts.geometry.y])
            dist, idx = tree.query(fxy)
            fac[name] = np.unique(np.asarray(idx)[np.asarray(dist) <= 1000]
                                  .astype(np.int64))

        def shares(csr):
            out = {}
            for svc, src in fac.items():
                if len(src) == 0:
                    out[svc] = 0.0
                    continue
                v = dijkstra(csr, indices=src, min_only=True)[cell_nodes]
                ok = np.isfinite(v)
                out[svc] = float(100 * pop[ok & (v <= 60)].sum() / pop.sum())
            return out

        baseline = shares(csr0)
        haz_pass = d['haz'] & d['unp']
        haz_slow = d['haz'] & ~d['unp']
        w_obs = d['w'].copy()
        w_obs[haz_slow] = w_obs[haz_slow] * 2.0
        observed = shares(hz.csr_min(uid, vid, w_obs, n, mask=~haz_pass))
        len_unp_target = float(d['len'][haz_pass].sum())
        len_pav_target = float(d['len'][haz_slow].sum())

        unp_idx = np.flatnonzero(d['unp'])
        pav_idx = np.flatnonzero(~d['unp'])
        len_unp = d['len'][unp_idx]
        len_pav = d['len'][pav_idx]
        print(f'{iso}: segments={len(uid):,} affected_unpaved_km='
              f'{len_unp_target/1000:.0f} affected_paved_km={len_pav_target/1000:.0f} '
              f'({time.time()-t0:.1f}s)', flush=True)

        null_loss = {k: [] for k in fac}
        for draw in range(a.draws):
            cx = float(rng.uniform(lo_x, hi_x))
            cy = float(rng.uniform(lo_y, hi_y))
            dd = np.sqrt((mxy[:, 0] - cx) ** 2 + (mxy[:, 1] - cy) ** 2)
            # concentric disk: order each surface class by distance to centre
            order_unp = np.argsort(dd[unp_idx])
            cum_unp = np.cumsum(len_unp[order_unp])
            k_unp = int(np.searchsorted(cum_unp, len_unp_target)) + 1
            sel_unp = unp_idx[order_unp[:min(k_unp, len(unp_idx))]]
            order_pav = np.argsort(dd[pav_idx])
            cum_pav = np.cumsum(len_pav[order_pav])
            k_pav = int(np.searchsorted(cum_pav, len_pav_target)) + 1
            sel_pav = pav_idx[order_pav[:min(k_pav, len(pav_idx))]]
            mask = np.ones(len(d['w']), dtype=bool)
            mask[sel_unp] = False
            w2 = d['w'].copy()
            w2[sel_pav] = w2[sel_pav] * 2.0
            s = shares(hz.csr_min(uid, vid, w2, n, mask=mask))
            for k in fac:
                null_loss[k].append(baseline[k] - s[k])
            if (draw + 1) % 5 == 0:
                print(f'  {iso} draw {draw+1}/{a.draws} '
                      f'({time.time()-t0:.1f}s)', flush=True)
        for svc in fac:
            null = np.array(null_loss[svc], dtype=float)
            rows.append({
                'iso3': iso, 'service': svc,
                'observed_loss_pp': round(baseline[svc] - observed[svc], 3),
                'clustered_null_mean_pp': round(float(null.mean()), 3),
                'clustered_null_p2_5_pp': round(float(np.percentile(null, 2.5)), 3),
                'clustered_null_p97_5_pp': round(float(np.percentile(null, 97.5)), 3),
                'draws': a.draws,
                'affected_unpaved_km_target': round(len_unp_target / 1000, 1),
                'affected_paved_km_target': round(len_pav_target / 1000, 1),
            })
    df = pd.DataFrame(rows)
    df.to_csv(OUT / 'spatial_null_model.csv', index=False, encoding='utf-8-sig')
    print(df.to_string(index=False))
    print(f'wrote {OUT / "spatial_null_model.csv"}')


if __name__ == '__main__':
    main()
