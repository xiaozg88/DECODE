# -*- coding: utf-8 -*-
"""Non-random missing-road stress test (reviewer concern: OSM local roads are
*selectively* under-mapped in rural, low-population and remote areas, not thinned
uniformly at random).

For each country we classify every local (OSM motorable) edge by its midpoint:

  * urban/rural        -- GHS-SMOD 2020 (codes 11/12/13 -> rural)
  * population context -- nearest WorldPop 2020 populated cell (density)
  * remoteness         -- GRIP4 total road density (low density -> remote)

and recompute the 60-minute share and the pure local-edge effect after
*non-random* deletion of local edges in those strata, each paired with a
*random* deletion at the SAME fraction so the "spatial-selectivity penalty"
(excess loss versus matched random thinning) can be read off directly.

The result upgrades the existing random-only stress test (SI Table S16) with the
answer to "is the amount of missing road, or *where* it is missing, that matters?".

Usage:
  python run_nonrandom_missing_road_stress.py --countries KHM MOZ PNG
"""
from __future__ import annotations

import argparse
import time
from pathlib import Path

import numpy as np
import pandas as pd
import pyogrio
import rasterio

import run_nested_counterfactual as rnc
from run_experiment_15_urban_rural import sample_smod, classify_smod

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'output/experiments/nonrandom_missing_road_stress'

SUBSET = ['KHM', 'GTM', 'BGD', 'SEN', 'NGA', 'ETH', 'MOZ', 'PNG', 'EGY', 'TUR']
GRIP_TOTAL = (ROOT / 'data/external/grip4/GRIP4_density_total'
              / 'grip4_total_dens_m_km2.asc')
RNG_SEED = 20261003


def _sample_grip4(lon: np.ndarray, lat: np.ndarray) -> np.ndarray:
    """Sample GRIP4 total density (m/km2) at arbitrary lon/lat; NaN outside."""
    with rasterio.open(GRIP_TOTAL) as src:
        rows, cols = rasterio.transform.rowcol(src.transform, lon, lat)
        rows = np.asarray(rows)
        cols = np.asarray(cols)
        valid = (rows >= 0) & (rows < src.height) & (cols >= 0) & (cols < src.width)
        out = np.full(len(lon), np.nan, dtype='float32')
        if valid.any():
            rr = rows[valid]
            cc = cols[valid]
            data = src.read(1)
            vals = data[rr, cc].astype('float32')
            if src.nodata is not None:
                vals = np.where(vals == src.nodata, np.nan, vals)
            out[valid] = vals
    return out


def _sample_worldpop(iso: str, lon: np.ndarray, lat: np.ndarray) -> np.ndarray:
    """Sample WorldPop 2020 population density directly at edge midpoints."""
    path = ROOT / 'data/external/hdx/countries' / iso / f'{iso.lower()}_pd_2020_1km.tif'
    with rasterio.open(path) as src:
        rows, cols = rasterio.transform.rowcol(src.transform, lon, lat)
        rows = np.asarray(rows)
        cols = np.asarray(cols)
        valid = (rows >= 0) & (rows < src.height) & (cols >= 0) & (cols < src.width)
        out = np.full(len(lon), np.nan, dtype='float32')
        if valid.any():
            data = src.read(1)
            vals = data[rows[valid], cols[valid]].astype('float32')
            if src.nodata is not None:
                vals = np.where(vals == src.nodata, np.nan, vals)
            out[valid] = vals
    return out


def process(iso: str) -> pd.DataFrame:
    t0 = time.time()
    d = rnc.load_segments(iso)
    keys, uid, vid = rnc.build_nodes(d)
    n_nodes = len(keys)
    art = d['art']
    local = ~art
    n_local = int(local.sum())
    if n_local == 0:
        raise ValueError(f'{iso}: no local edges')

    # midpoint in lon/lat for every segment
    mid_lon = (d['xu'] + d['xv']) / 2.0
    mid_lat = (d['yu'] + d['yv']) / 2.0

    # urban/rural via GHS-SMOD
    smod = sample_smod(mid_lon, mid_lat)
    _detail, ur = classify_smod(smod)
    rural = (ur == 'rural')

    # population context: sample WorldPop density at the midpoint itself
    edge_density = _sample_worldpop(iso, mid_lon, mid_lat)
    local_density_valid = local & np.isfinite(edge_density)
    pop_thresh = float(np.percentile(edge_density[local_density_valid], 25)) \
        if local_density_valid.any() else np.nan
    lowpop = np.isfinite(edge_density) & (edge_density <= pop_thresh)

    # remoteness via GRIP4 total density (low density -> remote)
    grip = _sample_grip4(mid_lon, mid_lat)
    grip_valid = np.isfinite(grip)
    grip_med = float(np.median(grip[local & grip_valid])) if (local & grip_valid).any() else np.nan
    remote = grip_valid & (grip <= grip_med)

    # ---- non-random deletion masks (over ALL segments; arterial never deleted) ----
    masks = {}
    masks['rural_local'] = local & rural
    masks['lowpop_local'] = local & lowpop
    masks['rural_lowpop_local'] = local & rural & lowpop
    masks['remote_local'] = local & remote

    # base graphs
    csr_all = rnc.csr_min(uid, vid, d['w'], n_nodes)
    csr_art = rnc.csr_min(uid, vid, d['w'], n_nodes, mask=art)
    x3857, y3857 = rnc.base.TRANSFORMER.transform(keys[:, 0], keys[:, 1])
    node3857 = np.column_stack([x3857, y3857])
    tree_all = rnc.cKDTree(node3857)
    _cellxy, cellxy3857, pop = rnc.base.load_population(iso)
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
    rng = np.random.default_rng(RNG_SEED)

    rows = []
    for svc in ('health', 'education'):
        rows.append({'iso3': iso, 'service': svc, 'scenario': 'intact',
                     'share_60min_pct': base[svc]['share_60min_pct'],
                     'edge_effect_pp': base[svc]['share_60min_pct']
                                      - base_art[svc]['share_60min_pct'],
                     'deleted_local_frac': 0.0, 'is_random': False,
                     'matched_fraction': np.nan})

    scenarios = []
    for name, mask in masks.items():
        frac = float(mask.sum()) / max(n_local, 1)
        # matched random control at the same fraction
        rnd = np.zeros(len(uid), dtype=bool)
        rnd[local] = rng.random(n_local) < frac
        scenarios.append((name, mask, frac, False))
        scenarios.append((f'{name}_random', rnd, frac, True))

    for name, mask_del, frac, is_rand in scenarios:
        keep = ~mask_del
        csr_del = rnc.csr_min(uid, vid, d['w'], n_nodes, mask=keep)
        sh = shares(csr_del)
        for svc in ('health', 'education'):
            rows.append({'iso3': iso, 'service': svc, 'scenario': name,
                         'share_60min_pct': sh[svc]['share_60min_pct'],
                         'edge_effect_pp': sh[svc]['share_60min_pct']
                                          - base_art[svc]['share_60min_pct'],
                         'deleted_local_frac': frac, 'is_random': is_rand,
                         'matched_fraction': frac})
        print(f'{iso}: {name} (deleted {frac:.3f} of local) '
              f'({time.time()-t0:.1f}s)', flush=True)
    return pd.DataFrame(rows)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--countries', nargs='+', default=SUBSET)
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    frames = []
    for iso in a.countries:
        target = OUT / f'{iso.lower()}_nonrandom_stress.csv'
        if target.exists():
            print(f'{iso}: cached, skip')
            frames.append(pd.read_csv(target))
            continue
        df = process(iso)
        df.to_csv(target, index=False, encoding='utf-8-sig')
        frames.append(df)
    allf = pd.concat(frames, ignore_index=True)
    allf.to_csv(OUT / 'stress_nonrandom_all.csv', index=False, encoding='utf-8-sig')

    # intact share for loss computation
    intact = allf[allf.scenario.eq('intact')].set_index(['iso3', 'service']).share_60min_pct
    sub = allf[~allf.scenario.eq('intact')].copy()
    sub['base'] = sub.scenario.str.replace('_random$', '', regex=True)
    sub['is_random'] = sub.scenario.str.endswith('_random')
    sub['loss_vs_intact_pp'] = (
        intact[sub.set_index(['iso3', 'service']).index].to_numpy() - sub.share_60min_pct
    )

    print('\n=== mean 60-min share loss vs intact (pp): non-random vs matched random ===')
    nr = sub[~sub.is_random].groupby('base').loss_vs_intact_pp.mean()
    rd = sub[sub.is_random].groupby('base').loss_vs_intact_pp.mean()
    frac = sub[~sub.is_random].groupby('base').deleted_local_frac.mean()
    wide = pd.DataFrame({'deleted_frac': frac, 'nonrandom_loss_pp': nr,
                         'random_loss_pp': rd})
    wide['excess_nonrandom_vs_random_pp'] = wide.nonrandom_loss_pp - wide.random_loss_pp
    print(wide.round(2).to_string())

    sub.to_csv(OUT / 'stress_nonrandom_summary.csv', index=False, encoding='utf-8-sig')
    print(f'\nwrote {OUT}')


if __name__ == '__main__':
    main()
