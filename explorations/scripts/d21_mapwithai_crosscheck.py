# -*- coding: utf-8 -*-
"""Experiment B (part 1): three-way road-inventory cross-check.

Adds Meta/Facebook's satellite-derived "Map With AI" road predictions (roads a
deep-learning model found in Maxar imagery but which are missing from OSM) as a
third, methodologically independent road inventory alongside the model network
(Planet arterial + HOTOSM local) and GRIP4 (inventory-based, pre-OSM).

For each of the 10 representative countries this script:

  * extracts the downloaded ``*.gpkg.tar.gz`` and raster-free samples the AI
    linework onto the same 0.05-degree grid used for the accessibility cells,
  * aggregates WorldPop population and GRIP4 total density onto the same grid,
  * attaches GHS-SMOD urban/rural classification,
  * writes a per-cell table and a per-country summary, and then deletes the
    bulky GeoPackage/archive to conserve disk.

Lengths are computed in EPSG:3857 to match the ``length_m`` convention of the
model noded caches exactly (see ``prototype_multicountry_access.py``).
"""
from __future__ import annotations

import collections
import argparse
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import pyogrio

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import run_experiment_29_weight_sensitivity as sens  # noqa: E402
import run_grip4_completeness as rgc  # noqa: E402
from run_experiment_15_urban_rural import classify_smod, sample_smod  # noqa: E402

SRC = ROOT / 'data/external/mapwithai'
OUT = ROOT / 'output/experiments/mapwithai_crosscheck'
OUT_CELLS = OUT / 'ai_cells'
GRIP_TOTAL = (ROOT / 'data/external/grip4/GRIP4_density_total'
              / 'grip4_total_dens_m_km2.asc')
SUBSET = ['KHM', 'GTM', 'BGD', 'SEN', 'NGA', 'ETH', 'MOZ', 'PNG', 'EGY', 'TUR']
ISO2 = {'KHM': 'KH', 'GTM': 'GT', 'BGD': 'BD', 'SEN': 'SN', 'NGA': 'NG',
        'ETH': 'ET', 'MOZ': 'MZ', 'PNG': 'PG', 'EGY': 'EG', 'TUR': 'TR'}
CELL = 0.05


def _key(lon: np.ndarray, lat: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    return np.floor(lon / CELL).astype(np.int64), np.floor(lat / CELL).astype(np.int64)


def ai_cell_lengths(gpkg: Path) -> tuple[dict[tuple[int, int], float], float, int,
                                          dict[str, float]]:
    """Accumulate AI line length (m, EPSG:3857) per 0.05-degree cell.

    Returns ``(cell_len, total_m, n_segments)``.
    """
    info = pyogrio.read_info(gpkg)
    n = info['features']
    acc: dict[tuple[int, int], float] = collections.defaultdict(float)
    tag_len: dict[str, float] = collections.defaultdict(float)
    total = 0.0
    offset = 0
    chunk = 500_000
    while offset < n:
        gdf = pyogrio.read_dataframe(
            gpkg, skip_features=offset, max_features=chunk, columns=['highway_tag'])
        g3857 = gdf.to_crs(3857)
        length = g3857.geometry.length.to_numpy()
        tags = gdf['highway_tag'].astype(str).to_numpy()
        cents = gdf.geometry.centroid
        lon = cents.x.to_numpy()
        lat = cents.y.to_numpy()
        ci, cj = _key(lon, lat)
        df = pd.DataFrame({'ci': ci, 'cj': cj, 'len': length})
        for (c_i, c_j), s in df.groupby(['ci', 'cj']).len.sum().items():
            acc[(int(c_i), int(c_j))] += float(s)
        tdf = pd.DataFrame({'tag': tags, 'len': length})
        for tag, s in tdf.groupby('tag').len.sum().items():
            tag_len[str(tag)] += float(s)
        total += float(length.sum())
        offset += chunk
    return acc, total, n, tag_len


def process(iso: str) -> None:
    cc = ISO2[iso]
    archive = SRC / f'{cc}_mapwithai_road_data.gpkg.tar.gz'
    gpkg = SRC / f'{cc}_mapwithai_road_data.gpkg'
    cells_csv = OUT_CELLS / f'{iso}_cells.csv'
    if cells_csv.exists():
        print(f'{iso}: cached cells, skip')
        return
    if not gpkg.exists() and archive.exists():
        import tarfile
        with tarfile.open(archive, 'r:gz') as tf:
            tf.extractall(SRC)
    if not gpkg.exists():
        print(f'{iso}: no AI GeoPackage, skip')
        return

    t0 = time.time()
    # 1) populated WorldPop 1km cells and GRIP4 density at those cells
    xy, _xy3857, density, _counts = sens.population_weights(iso)
    lon, lat = xy[:, 0], xy[:, 1]
    grip = rgc.sample(GRIP_TOTAL, lon, lat)
    ci, cj = _key(lon, lat)
    wpop = pd.DataFrame({'ci': ci, 'cj': cj, 'pop_density': density, 'grip4_dens_m_km2': grip})
    cells = wpop.groupby(['ci', 'cj'], as_index=False).agg(
        pop_density=('pop_density', 'mean'),
        grip4_dens_m_km2=('grip4_dens_m_km2', 'mean'),
        worldpop_n=('pop_density', 'count'))

    # 2) AI line length per cell
    ai_len, ai_total_m, ai_n, tag_len = ai_cell_lengths(gpkg)
    ai = pd.DataFrame(
        [{'ci': k[0], 'cj': k[1], 'ai_len_m': v} for k, v in ai_len.items()])
    cells = cells.merge(ai, on=['ci', 'cj'], how='left')
    cells['ai_len_m'] = cells['ai_len_m'].fillna(0.0)

    # 3) cell centre + GHS-SMOD urban/rural
    cells['lon'] = (cells['ci'] + 0.5) * CELL
    cells['lat'] = (cells['cj'] + 0.5) * CELL
    smod = sample_smod(cells['lon'].to_numpy(), cells['lat'].to_numpy())
    _detail, ur = classify_smod(smod)
    cells['urban_rural'] = ur
    cells['ai_density_km_km2'] = (cells['ai_len_m'] / 1000.0) / (111.32 * CELL
                                                                 * 110.574 * CELL
                                                                 * np.cos(np.radians(cells['lat'])))

    # 4) country summary
    nc = pd.read_csv(ROOT / 'output/experiments/network_completeness'
                     / 'network_completeness_by_country.csv').set_index('iso3')
    row = {
        'iso3': iso,
        'ai_segments': ai_n,
        'ai_km_mercator': ai_total_m / 1000.0,
        'ai_nonmotorable_km': sum(v for k, v in tag_len.items()
                                  if k in ('path', 'footway', 'pedestrian', 'steps',
                                           'cycleway', 'bridleway')) / 1000.0,
        'ai_density_country_km_km2': (ai_total_m / 1000.0) / float(nc.loc[iso, 'area_km2']),
        'ai_density_popcells_km_km2': (ai_total_m / 1000.0)
                                      / float((cells['worldpop_n'] * 111.32 * CELL
                                               * 110.574 * CELL
                                               * np.cos(np.radians(cells['lat']))).sum()),
        'ai_mean_over_cells_km_km2': float(cells['ai_density_km_km2'].mean()),
        'ai_cells': len(cells),
    }
    OUT_CELLS.mkdir(parents=True, exist_ok=True)
    cells.to_csv(cells_csv, index=False, encoding='utf-8-sig')
    pd.DataFrame([row]).to_csv(OUT / 'ai_country.csv', mode='a',
                               header=not (OUT / 'ai_country.csv').exists(),
                               index=False, encoding='utf-8-sig')
    print(f'{iso}: {ai_n} AI segments, {ai_total_m/1000:.1f} km, '
          f'{len(cells)} cells ({time.time()-t0:.1f}s)', flush=True)

    # free disk: delete the bulky archive + GeoPackage
    gpkg.unlink(missing_ok=True)
    archive.unlink(missing_ok=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--countries', nargs='+', default=SUBSET)
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    OUT_CELLS.mkdir(parents=True, exist_ok=True)
    for iso in a.countries:
        process(iso)
    print('done')


if __name__ == '__main__':
    main()
