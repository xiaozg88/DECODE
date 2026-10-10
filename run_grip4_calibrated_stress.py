# -*- coding: utf-8 -*-
"""GRIP4-calibrated missing-road stress test.

GRIP4 is an independent, inventory-based, pre-OSM road reference.  For each
country we delete local roads *in a realistic order* (rural -> low-population ->
low-GRIP4-density first, i.e. the edges least likely to be captured by an
inventory) until the remaining total road density equals GRIP4's total density.
This replaces the arbitrary stratum fractions of the stratified stress test with
an external completeness anchor.  A matched random deletion at the same fraction
is run as a control.

Usage:
  python run_grip4_calibrated_stress.py --countries KHM MOZ PNG
"""
from __future__ import annotations

import argparse
import time
from pathlib import Path

import numpy as np
import pandas as pd

import run_nested_counterfactual as rnc
import run_nonrandom_missing_road_stress as nrs
from run_experiment_15_urban_rural import sample_smod, classify_smod

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'output/experiments/grip4_calibrated_stress'
SUBSET = ['KHM', 'GTM', 'BGD', 'SEN', 'NGA', 'ETH', 'MOZ', 'PNG', 'EGY', 'TUR']


def _calib_frac(iso: str) -> tuple[float, float, float]:
    nc = pd.read_csv(ROOT / 'output/experiments/network_completeness'
                     / 'network_completeness_by_country.csv').set_index('iso3')
    gr = pd.read_csv(ROOT / 'output/experiments/grip4_completeness'
                     / 'grip4_vs_network_density.csv').set_index('iso3')
    model = float(nc.loc[iso, 'road_density_km_per_km2'])
    grip = float(gr.loc[iso, 'grip_all_mean_density']) / 1000.0  # m/km2 -> km/km2
    local_density = float(nc.loc[iso, 'local_km'] / nc.loc[iso, 'area_km2'])
    f = (model - grip) / max(local_density, 1e-12)
    return float(min(max(f, 0.0), 1.0)), model, grip


def process(iso: str) -> pd.DataFrame:
    t0 = time.time()
    f_calib, model_dens, grip_dens_km = _calib_frac(iso)
    d = rnc.load_segments(iso)
    keys, uid, vid = rnc.build_nodes(d)
    n_nodes = len(keys)
    art = d['art']
    local = ~art
    n_local = int(local.sum())
    if n_local == 0:
        raise ValueError(f'{iso}: no local edges')

    mid_lon = (d['xu'] + d['xv']) / 2.0
    mid_lat = (d['yu'] + d['yv']) / 2.0
    smod = sample_smod(mid_lon, mid_lat)
    _detail, ur = classify_smod(smod)
    rural = (ur == 'rural')
    density = nrs._sample_worldpop(iso, mid_lon, mid_lat)
    grip_here = nrs._sample_grip4(mid_lon, mid_lat)

    # deletion priority: rural first, then low population, then low GRIP4 density
    d_rank = np.where(np.isfinite(density), density, np.inf)
    g_rank = np.where(np.isfinite(grip_here), grip_here, np.inf)
    order = np.lexsort((g_rank, d_rank, -rural.astype(int)))
    local_sorted = _rank_local(order, local)

    # delete the first f_calib fraction of local edges in priority order
    n_del = int(round(f_calib * n_local))
    mask_priority = np.zeros(len(uid), dtype=bool)
    mask_priority[local_sorted[:n_del]] = True

    rng = np.random.default_rng(nrs.RNG_SEED)
    mask_random = np.zeros(len(uid), dtype=bool)
    mask_random[local] = rng.random(n_local) < f_calib

    csr_all = rnc.csr_min(uid, vid, d['w'], n_nodes)
    x3857, y3857 = rnc.base.TRANSFORMER.transform(keys[:, 0], keys[:, 1])
    tree_all = rnc.cKDTree(np.column_stack([x3857, y3857]))
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

    intact = shares(csr_all)
    rows = []
    for name, mask in (('grip4_calibrated', mask_priority),
                       ('grip4_calibrated_random', mask_random)):
        csr = rnc.csr_min(uid, vid, d['w'], n_nodes, mask=~mask)
        sh = shares(csr)
        for svc in ('health', 'education'):
            rows.append({'iso3': iso, 'service': svc, 'scenario': name,
                         'share_60min_pct': sh[svc]['share_60min_pct'],
                         'intact_share_60min_pct': intact[svc]['share_60min_pct'],
                         'deleted_local_frac': f_calib,
                         'model_density_km_km2': model_dens,
                         'grip4_density_km_km2': grip_dens_km,
                         'is_random': name.endswith('_random')})
        print(f'{iso}: {name} (f={f_calib:.3f}, model={model_dens:.3f}, '
              f'grip4={grip_dens_km:.3f} km/km2) ({time.time()-t0:.1f}s)', flush=True)
    return pd.DataFrame(rows)


def _rank_local(order: np.ndarray, local: np.ndarray) -> np.ndarray:
    """Return local-edge indices sorted by the global deletion priority order."""
    local_idx = np.flatnonzero(local)
    pos = np.empty(len(order), dtype=np.int64)
    pos[order] = np.arange(len(order))
    return local_idx[np.argsort(pos[local_idx])]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--countries', nargs='+', default=SUBSET)
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    frames = []
    for iso in a.countries:
        target = OUT / f'{iso.lower()}_grip4_calib.csv'
        if target.exists():
            print(f'{iso}: cached, skip')
            frames.append(pd.read_csv(target))
            continue
        df = process(iso)
        df.to_csv(target, index=False, encoding='utf-8-sig')
        frames.append(df)
    allf = pd.concat(frames, ignore_index=True)
    allf.to_csv(OUT / 'grip4_calib_all.csv', index=False, encoding='utf-8-sig')
    allf['loss_pp'] = allf.intact_share_60min_pct - allf.share_60min_pct

    print('\n=== GRIP4-calibrated deletion: mean loss (pp) ===')
    nr = allf[~allf.is_random].groupby('iso3').loss_pp.mean()
    rd = allf[allf.is_random].groupby('iso3').loss_pp.mean()
    frac = allf.groupby('iso3').deleted_local_frac.first()
    summ = pd.DataFrame({'f_calib': frac, 'calib_loss_pp': nr, 'random_loss_pp': rd})
    summ['excess_pp'] = summ.calib_loss_pp - summ.random_loss_pp
    print(summ.round(2).to_string())
    print(f'\nmean: f_calib={summ.f_calib.mean():.2f}, '
          f'calib_loss={summ.calib_loss_pp.mean():.1f} pp, '
          f'random={summ.random_loss_pp.mean():.1f} pp, '
          f'excess={summ.excess_pp.mean():+.1f} pp')
    summ.to_csv(OUT / 'grip4_calib_summary.csv', encoding='utf-8-sig')
    print(f'\nwrote {OUT}')


if __name__ == '__main__':
    main()
