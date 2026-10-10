# -*- coding: utf-8 -*-
"""Review item R3: is the exposure-loss relation (r = 0.953) informative, or is it
reproduced by any random placement of the same affected road length?

For the two events that dominate the pooled correlation (MOZ 2025-03 and
PAK 2025-09, jointly about two thirds of the summed 60-min loss) we:
  1. rebuild the country graph from the cached ``*_noded_segments.gpkg``;
  2. reproduce the observed surface-aware loss (validation of the reconstruction);
  3. draw N random road sets that match the observed affected *length* of unpaved
     and paved roads (the affected share is therefore held constant) and recompute
     the loss for each draw -> a placement null distribution.
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
OUT = ROOT / 'output/experiments/hazard_null_model'
CHUNK = 750_000


def noded_path(iso):
    """Resolve the cached noded-segment gpkg (MOZ is stored as 'mozambique_*')."""
    d = ROOT / 'data/external/hdx/countries' / iso / 'local_roads'
    cands = [p for p in sorted(d.glob('*_noded_segments.gpkg')) if 'tiled' not in p.name]
    if not cands:
        raise FileNotFoundError(f'no noded segments under {d}')
    return cands[0]


def load_segments(iso):
    path = noded_path(iso)
    n = int(pyogrio.read_info(path)['features'])
    acc = {k: [] for k in ('xu', 'yu', 'xv', 'yv', 'w', 'len', 'haz', 'unp')}
    for start in range(0, n, CHUNK):
        meta, tbl = pyogrio.read_arrow(
            path, columns=['travel_time_min', 'length_m', 'hazard_intersect',
                           'surface_class'],
            skip_features=start, max_features=CHUNK)
        geom = shapely.from_wkb(tbl.column(meta['geometry_name']).to_numpy())
        coords = shapely.get_coordinates(geom)
        counts = shapely.get_num_coordinates(geom)
        first = np.concatenate(([0], np.cumsum(counts)[:-1]))
        last = np.cumsum(counts) - 1
        acc['xu'].append(coords[first, 0]); acc['yu'].append(coords[first, 1])
        acc['xv'].append(coords[last, 0]); acc['yv'].append(coords[last, 1])
        acc['w'].append(tbl.column('travel_time_min').to_numpy(zero_copy_only=False).astype('float64'))
        acc['len'].append(tbl.column('length_m').to_numpy(zero_copy_only=False).astype('float64'))
        acc['haz'].append(np.asarray(tbl.column('hazard_intersect').to_numpy(zero_copy_only=False),
                                     dtype=bool))
        sc = tbl.column('surface_class').to_numpy(zero_copy_only=False)
        acc['unp'].append(np.asarray([str(x) == 'unpaved' for x in sc], dtype=bool))
        del tbl, geom, coords
        gc.collect()
    return {k: np.concatenate(v) for k, v in acc.items()}


def node_ids(d):
    ku = np.column_stack([np.round(d['xu'], 7), np.round(d['yu'], 7)])
    kv = np.column_stack([np.round(d['xv'], 7), np.round(d['yv'], 7)])
    keys = np.unique(np.vstack([ku, kv]), axis=0)
    keys = keys[np.lexsort((keys[:, 1], keys[:, 0]))]
    lookup = pd.Series(np.arange(len(keys), dtype=np.int64),
                       index=keys.view([('x', 'f8'), ('y', 'f8')]).ravel())
    uid = lookup.reindex(ku.view([('x', 'f8'), ('y', 'f8')]).ravel()).to_numpy().astype(np.int64)
    vid = lookup.reindex(kv.view([('x', 'f8'), ('y', 'f8')]).ravel()).to_numpy().astype(np.int64)
    return keys, uid, vid


def csr_min(uid, vid, w, n, mask=None):
    if mask is not None:
        uid, vid, w = uid[mask], vid[mask], w[mask]
    keep = uid != vid
    uid, vid, w = uid[keep], vid[keep], w[keep]
    lo = np.minimum(uid, vid).astype(np.int64)
    hi = np.maximum(uid, vid).astype(np.int64)
    g = (pd.DataFrame({'key': lo * np.int64(n) + hi, 'w': w})
         .groupby('key', sort=False)['w'].min())
    key = g.index.to_numpy(); ww = g.to_numpy()
    a = (key // n).astype(np.int64); b = (key % n).astype(np.int64)
    return csr_matrix((np.concatenate([ww, ww]),
                       (np.concatenate([a, b]), np.concatenate([b, a]))), shape=(n, n))


def draw_target(pool, lens, target, rng):
    order = rng.permutation(len(pool))
    cum = np.cumsum(lens[order])
    k = int(np.searchsorted(cum, target)) + 1
    return pool[order[:min(k, len(pool))]]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--countries', nargs='+', default=['MOZ', 'PAK'])
    ap.add_argument('--draws', type=int, default=10)
    ap.add_argument('--seed', type=int, default=20261002)
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    ev = pd.read_csv(ROOT / 'output/experiments/hazard_exposure/hazard_event_table.csv')
    rng = np.random.default_rng(a.seed)
    rows = []
    for iso in a.countries:
        t0 = time.time()
        d = load_segments(iso)
        keys, uid, vid = node_ids(d)
        n = len(keys)
        csr0 = csr_min(uid, vid, d['w'], n)
        print(f'{iso}: segments={len(uid):,} nodes={n:,} '
              f'affected_unpaved={int((d["haz"] & d["unp"]).sum()):,} '
              f'({round(time.time() - t0, 1)}s)', flush=True)
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
            fac[name] = np.unique(np.asarray(idx)[np.asarray(dist) <= 1000].astype(np.int64))

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
        # channel decomposition: which part of the rule produces the loss?
        w_remove_only = d['w'].copy()
        removal_only = shares(csr_min(uid, vid, w_remove_only, n, mask=~haz_pass))
        w_slow_only = d['w'].copy()
        w_slow_only[haz_slow] = w_slow_only[haz_slow] * 2.0
        doubling_only = shares(csr_min(uid, vid, w_slow_only, n))
        w_obs = d['w'].copy()
        w_obs[haz_slow] = w_obs[haz_slow] * 2.0
        observed = shares(csr_min(uid, vid, w_obs, n, mask=~haz_pass))
        len_unp_target = float(d['len'][haz_pass].sum())
        len_pav_target = float(d['len'][haz_slow].sum())
        # the null draws a same-length random set from the WHOLE network (not only
        # from the un-affected remainder, which can be smaller than the target)
        pool_unp = np.flatnonzero(d['unp'])
        pool_pav = np.flatnonzero(~d['unp'])
        len_unp = d['len'][pool_unp]
        len_pav = d['len'][pool_pav]
        null_loss = {k: [] for k in fac}
        for _ in range(a.draws):
            sel_unp = draw_target(pool_unp, len_unp, len_unp_target, rng)
            sel_pav = draw_target(pool_pav, len_pav, len_pav_target, rng)
            mask = np.ones(len(d['w']), dtype=bool)
            mask[sel_unp] = False
            w2 = d['w'].copy()
            w2[sel_pav] = w2[sel_pav] * 2.0
            s = shares(csr_min(uid, vid, w2, n, mask=mask))
            for k in fac:
                null_loss[k].append(baseline[k] - s[k])
        for svc in fac:
            null = np.array(null_loss[svc], dtype=float)
            rows.append({
                'iso3': iso, 'service': svc,
                'baseline_60min_pct': round(baseline[svc], 3),
                'observed_60min_pct': round(observed[svc], 3),
                'observed_loss_pp': round(baseline[svc] - observed[svc], 3),
                'loss_removal_only_pp': round(baseline[svc] - removal_only[svc], 3),
                'loss_doubling_only_pp': round(baseline[svc] - doubling_only[svc], 3),
                'null_mean_loss_pp': round(float(null.mean()), 3),
                'null_p2_5_pp': round(float(np.percentile(null, 2.5)), 3),
                'null_p97_5_pp': round(float(np.percentile(null, 97.5)), 3),
                'draws': a.draws,
                'network_km': round(float(d['len'].sum()) / 1000, 1),
                'unpaved_km_total': round(float(d['len'][d['unp']].sum()) / 1000, 1),
                'affected_unpaved_km_target': round(len_unp_target / 1000, 1),
                'affected_paved_km_target': round(len_pav_target / 1000, 1),
            })
        print(pd.DataFrame(rows).tail(2).to_string(index=False), flush=True)
        pub = ev[(ev.iso3 == iso) & (ev.event_id.str.contains('current'))]
        if len(pub):
            print('published:', flush=True)
            print(pub[['service', 'share_60min_baseline', 'share_60min_hazard',
                       'loss_60min_pp', 'affected_share_pct']].round(2).to_string(index=False),
                  flush=True)
    df = pd.DataFrame(rows)
    df.to_csv(OUT / 'hazard_null_model.csv', index=False, encoding='utf-8-sig')
    print(f'wrote {OUT / "hazard_null_model.csv"}')


if __name__ == '__main__':
    main()
