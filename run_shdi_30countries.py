# -*- coding: utf-8 -*-
"""P1-3: extend the SHDI-access heterogeneity analysis to all 30 countries.

Uses the per-cell travel times exported by ``export_cell_travel_times.py`` together with
the Global Data Lab subnational regions (already local) and the SHDI table to compute
population-weighted SHDI-access correlations per country and service.

Outputs ``output/experiments/shdi_30countries/`` (region table + correlation table).
"""
from __future__ import annotations

import argparse
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

import run_experiment_16_socioeconomic as old16

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'output/experiments/shdi_30countries'
CELLS = ROOT / 'output/experiments/cell_travel_times'
REGIONS = ROOT / 'data/external/socioeconomic/gdl/gdl_regions_v6_7.geojson'


def weighted_corr(x: np.ndarray, y: np.ndarray, w: np.ndarray) -> float:
    ok = np.isfinite(x) & np.isfinite(y) & np.isfinite(w) & (w > 0)
    if ok.sum() < 4:
        return np.nan
    x, y, w = x[ok], y[ok], w[ok]
    mx = np.average(x, weights=w)
    my = np.average(y, weights=w)
    cov = np.average((x - mx) * (y - my), weights=w)
    sx = np.sqrt(np.average((x - mx) ** 2, weights=w))
    sy = np.sqrt(np.average((y - my) ** 2, weights=w))
    return float(cov / (sx * sy)) if sx > 0 and sy > 0 else np.nan


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--countries', nargs='+', default=None)
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    files = sorted(CELLS.glob('*.parquet'))
    if a.countries:
        files = [f for f in files if f.stem in set(a.countries)]
    if not files:
        print('no cell travel-time files found')
        return
    regions_all = gpd.read_file(REGIONS)
    wide_csv = ROOT / 'data/external/socioeconomic/gdl/shdi_30countries_long.csv'
    if wide_csv.exists():
        shdi = pd.read_csv(wide_csv)
        shdi = shdi[shdi.year == 2020][['gdlcode', 'iso3', 'shdi']].rename(
            columns={'shdi': 'shdi_2020'})
        print(f'SHDI table: {shdi.iso3.nunique()} countries, {len(shdi)} regions (2020)')
    else:
        shdi = old16.parse_gdl_shdi()
        shdi = shdi[shdi.year == 2020][['region_code', 'iso3', 'shdi']].rename(
            columns={'region_code': 'gdlcode', 'shdi': 'shdi_2020'})
    region_rows, corr_rows = [], []
    for path in files:
        iso = path.stem
        try:
            cells = pd.read_parquet(path)
        except Exception as exc:
            print(f'{iso}: cannot read cells ({exc})')
            continue
        regions = regions_all[regions_all.iso_code.astype(str) == iso][
            ['gdlcode', 'region', 'geometry']]
        if len(regions) == 0:
            print(f'{iso}: no GDL regions')
            continue
        pts = gpd.GeoDataFrame(cells, geometry=gpd.points_from_xy(cells.lon, cells.lat), crs=4326)
        joined = gpd.sjoin(pts, regions, how='left', predicate='within')
        # points exactly on a shared border can match twice; keep the first match
        joined = joined[~joined.index.duplicated(keep='first')].reindex(pts.index)
        missing = joined.gdlcode.isna()
        if missing.any():
            subset = pts.loc[missing[missing].index]
            near = gpd.sjoin_nearest(subset, regions[['gdlcode', 'geometry']], how='left')
            near = near[~near.index.duplicated(keep='first')].reindex(subset.index)
            joined.loc[near.index, 'gdlcode'] = near.gdlcode.to_numpy()
        agg = joined.groupby('gdlcode').agg(population=('population_counts', 'sum'))
        for service in ('health', 'education'):
            # population-weighted within-60 count (matches the core SHDI analysis)
            inside = joined.population_counts.where(joined[f'travel_{service}_min'].le(60), 0.0)
            agg[f'pop60_{service}'] = inside.groupby(joined.gdlcode).sum()
        agg = agg.reset_index()
        agg['iso3'] = iso
        agg = agg.merge(shdi[shdi.iso3 == iso][['gdlcode', 'shdi_2020']], on='gdlcode', how='left')
        region_rows.append(agg)
        for service in ('health', 'education'):
            share = 100 * agg[f'pop60_{service}'] / agg.population.replace(0, np.nan)
            corr_rows.append({
                'iso3': iso, 'service': service, 'regions': int(agg.gdlcode.nunique()),
                'population_weighted_pearson': weighted_corr(agg.shdi_2020.to_numpy(float),
                                                             share.to_numpy(float),
                                                             agg.population.to_numpy(float)),
                'unweighted_pearson': float(agg.shdi_2020.corr(share)) if len(agg) > 3 else np.nan})
        pd.concat(region_rows, ignore_index=True).to_csv(
            OUT / 'shdi_access_regions_30countries.csv', index=False, encoding='utf-8-sig')
        pd.DataFrame(corr_rows).to_csv(OUT / 'shdi_access_correlations_30countries.csv',
                                       index=False, encoding='utf-8-sig')
        print(f'{iso}: regions={len(agg)}', flush=True)
    corr = pd.DataFrame(corr_rows)
    if len(corr):
        pd.set_option('display.width', 220)
        pd.set_option('display.max_rows', 80)
        print()
        print(corr.round(3).sort_values('population_weighted_pearson').to_string(index=False))
        print()
        print(corr.groupby('service').population_weighted_pearson.describe().round(3).to_string())
    print(f'wrote {OUT}')


if __name__ == '__main__':
    main()
