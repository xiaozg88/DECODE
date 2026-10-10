# -*- coding: utf-8 -*-
"""Experiment B (part 2): Map-With-AI-calibrated missing-road stress test.

Mirrors ``run_grip4_calibrated_stress.py``, but replaces the GRIP4 total-density
anchor with Meta/Facebook's independent satellite-derived road predictions
(``Map With AI``).  Those AI roads are roads a deep-learning model found in
Maxar imagery that are missing from OSM, so a cell with a high AI-road density
is a cell where the mapped local network is most likely incomplete.

For each country we therefore delete local edges in the order
``rural -> low-population -> high-AI-road-density`` until the deleted fraction
equals ``AI_km / (local_km + AI_km)`` (the satellite-implied under-mapping
share), and run a matched random deletion at the same fraction as a control.
The GRIP4 run and this run together form the dual-anchor robustness check.
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import run_nested_counterfactual as rnc  # noqa: E402
import run_nonrandom_missing_road_stress as nrs  # noqa: E402
from run_experiment_15_urban_rural import classify_smod, sample_smod  # noqa: E402

OUT = ROOT / 'output/experiments/mapwithai_calibrated_stress'
CELLS = ROOT / 'output/experiments/mapwithai_crosscheck/ai_cells'
SUBSET = ['KHM', 'GTM', 'BGD', 'SEN', 'NGA', 'ETH', 'MOZ', 'PNG', 'EGY', 'TUR']
CELL = 0.05


def _ai_fraction(iso: str) -> tuple[float, float, float]:
    nc = pd.read_csv(ROOT / 'output/experiments/network_completeness'
                     / 'network_completeness_by_country.csv').set_index('iso3')
    ai = pd.read_csv(ROOT / 'output/experiments/mapwithai_crosscheck'
                     / 'ai_country.csv').set_index('iso3')
    local = float(nc.loc[iso, 'local_km'])
    ai_km = float(ai.loc[iso, 'ai_km_mercator'])
    f = ai_km / max(local + ai_km, 1e-12)
    return float(min(max(f, 0.0), 1.0)), local, ai_km


def _ai_lookup(iso: str) -> dict[tuple[int, int], float]:
    cells = pd.read_csv(CELLS / f'{iso}_cells.csv')
    out = {}
    for ci, cj, d in zip(cells['ci'], cells['cj'], cells['ai_density_km_km2']):
        out[(int(ci), int(cj))] = float(d)
    return out


def process(iso: str) -> pd.DataFrame:
    t0 = time.time()
    f_ai, local_km, ai_km = _ai_fraction(iso)
    lookup = _ai_lookup(iso)
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

    ci = np.floor(mid_lon / CELL).astype(np.int64)
    cj = np.floor(mid_lat / CELL).astype(np.int64)
    ai = np.array([lookup.get((int(a), int(b)), 0.0) for a, b in zip(ci, cj)],
                  dtype='float64')

    d_rank = np.where(np.isfinite(density), density, np.inf)
    ai_rank = np.where(np.isfinite(ai), -ai, np.inf)  # high AI density first
    order = np.lexsort((ai_rank, d_rank, -rural.astype(int)))
    local_sorted = _rank_local(order, local)

    n_del = int(round(f_ai * n_local))
    mask_priority = np.zeros(len(uid), dtype=bool)
    mask_priority[local_sorted[:n_del]] = True

    rng = np.random.default_rng(nrs.RNG_SEED)
    mask_random = np.zeros(len(uid), dtype=bool)
    mask_random[local] = rng.random(n_local) < f_ai

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
    for name, mask in (('mapwithai_calibrated', mask_priority),
                       ('mapwithai_calibrated_random', mask_random)):
        csr = rnc.csr_min(uid, vid, d['w'], n_nodes, mask=~mask)
        sh = shares(csr)
        for svc in ('health', 'education'):
            rows.append({'iso3': iso, 'service': svc, 'scenario': name,
                         'share_60min_pct': sh[svc]['share_60min_pct'],
                         'intact_share_60min_pct': intact[svc]['share_60min_pct'],
                         'deleted_local_frac': f_ai,
                         'local_km': local_km,
                         'ai_km': ai_km,
                         'is_random': name.endswith('_random')})
        print(f'{iso}: {name} (f={f_ai:.3f}, local={local_km:.1f} km, '
              f'ai={ai_km:.1f} km) ({time.time()-t0:.1f}s)', flush=True)
    return pd.DataFrame(rows)


def _rank_local(order: np.ndarray, local: np.ndarray) -> np.ndarray:
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
        target = OUT / f'{iso.lower()}_mapwithai_calib.csv'
        if target.exists():
            print(f'{iso}: cached, skip')
            frames.append(pd.read_csv(target))
            continue
        df = process(iso)
        df.to_csv(target, index=False, encoding='utf-8-sig')
        frames.append(df)
    allf = pd.concat(frames, ignore_index=True)
    allf.to_csv(OUT / 'mapwithai_calib_all.csv', index=False, encoding='utf-8-sig')
    allf['loss_pp'] = allf.intact_share_60min_pct - allf.share_60min_pct

    print('\n=== Map-With-AI-calibrated deletion: mean loss (pp) ===')
    nr = allf[~allf.is_random].groupby('iso3').loss_pp.mean()
    rd = allf[allf.is_random].groupby('iso3').loss_pp.mean()
    frac = allf.groupby('iso3').deleted_local_frac.first()
    summ = pd.DataFrame({'f_ai': frac, 'ai_loss_pp': nr, 'random_loss_pp': rd})
    summ['excess_pp'] = summ.ai_loss_pp - summ.random_loss_pp
    print(summ.round(2).to_string())
    print(f'\nmean: f_ai={summ.f_ai.mean():.2f}, '
          f'ai_loss={summ.ai_loss_pp.mean():.1f} pp, '
          f'random={summ.random_loss_pp.mean():.1f} pp, '
          f'excess={summ.excess_pp.mean():+.1f} pp')
    summ.to_csv(OUT / 'mapwithai_calib_summary.csv', encoding='utf-8-sig')
    print(f'\nwrote {OUT}')


if __name__ == '__main__':
    main()
