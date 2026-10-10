# -*- coding: utf-8 -*-
"""P1-5: network-completeness diagnostics using data already on disk.

Explains the two anomalies a reviewer will notice: the MAP benchmark outliers
(e.g. Papua New Guinea) and the residuals of the correction-direction law.  Proxies are
built from the corrected noded caches (road density, local-road share), the population
rasters (density, area) and the urban/rural table (urban population share).

Outputs ``output/experiments/network_completeness/``.
"""
from __future__ import annotations

from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
import pyogrio
import rasterio

import run_experiment_29_weight_sensitivity as sens

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'output/experiments/network_completeness'
EXP = ROOT / 'output/experiments/experiment_29_global_expansion'


def cache_stats(iso: str) -> dict:
    path = sens.cache_path(iso)
    if path is None:
        return {}
    if path.suffix == '.parquet':
        con = duckdb.connect()
        row = con.execute(
            "SELECT count(*) AS segments, sum(length_m)/1000 AS km, "
            "sum(CASE WHEN source='planet_arterial' THEN length_m ELSE 0 END)/1000 AS planet_km "
            f"FROM read_parquet('{path.as_posix()}')").fetchone()
        con.close()
    else:
        df = pyogrio.read_dataframe(path, columns=['length_m', 'source'], read_geometry=False)
        row = (len(df), float(df.length_m.sum()) / 1000,
               float(df.loc[df.source.astype(str) == 'planet_arterial', 'length_m'].sum()) / 1000)
    return {'noded_segments': int(row[0]), 'noded_km': float(row[1]),
            'planet_km': float(row[2]),
            'local_km': float(row[1] - row[2]),
            'local_share_pct': 100 * float(row[1] - row[2]) / max(float(row[1]), 1e-9)}


def area_and_population(iso: str) -> dict:
    path = ROOT / 'data/external/hdx/countries' / iso / f'{iso.lower()}_pd_2020_1km.tif'
    with rasterio.open(path) as src:
        a = src.read(1).astype('float32')
        nodata = src.nodata
        valid = (np.isfinite(a) & (a != nodata) & (a > 0)) if nodata is not None else (a > 0)
        rows = np.arange(src.height)
        lat = src.transform.f + (rows + 0.5) * src.transform.e
        dx = abs(src.transform.a) * 111.32 * np.cos(np.radians(lat))
        dy = abs(src.transform.e) * 110.574
        cell_area = np.repeat((dx * dy)[:, None], src.width, axis=1)[valid]
        pop = float((a[valid] * cell_area).sum())
    return {'area_km2': float(cell_area.sum()), 'population_counts_millions': pop / 1e6}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    direction = pd.read_csv(ROOT / 'output/experiments/correction_direction'
                            / 'correction_direction_matrix.csv')
    residuals = pd.read_csv(ROOT / 'output/experiments/direction_law_validation'
                            / 'direction_law_residuals.csv')
    residuals = residuals.groupby('iso3').residual_pp.mean().rename('direction_residual_pp')
    bench = pd.read_csv(ROOT / 'output/experiments/benchmark_validation'
                        / 'map_health_travel_time_vs_model.csv')
    bench['benchmark_gap_pp'] = bench.benchmark_share_60min_pct - bench.model_share_60min_corrected
    ur = pd.read_csv(EXP / 'urban_rural_expansion.csv')
    urb = (ur[ur.group == 'urban'].groupby('iso3').population_millions.first()
           / ur[ur.group == 'all'].groupby('iso3').population_millions.first() * 100)
    rows = []
    for iso in sorted(direction.iso3.unique()):
        rec = {'iso3': iso}
        rec.update(cache_stats(iso))
        rec.update(area_and_population(iso))
        rec['urban_share_pct'] = float(urb.get(iso, np.nan))
        rows.append(rec)
    df = pd.DataFrame(rows)
    df['road_density_km_per_km2'] = df.noded_km / df.area_km2
    df['population_density_per_km2'] = df.population_counts_millions * 1e6 / df.area_km2
    df = df.merge(direction.groupby('iso3').corrected_minus_arterial_pp.mean()
                  .rename('mean_correction_pp'), on='iso3', how='left')
    df = df.merge(residuals, on='iso3', how='left')
    df = df.merge(bench[['iso3', 'benchmark_gap_pp', 'benchmark_share_60min_pct',
                         'model_share_60min_corrected']], on='iso3', how='left')
    planet = pd.read_csv(ROOT / 'output/experiments/correction_direction'
                         / 'planet_surface_availability.csv')
    df = df.merge(planet[['iso3', 'planet_known_share_pct']], on='iso3', how='left')
    df = df.sort_values('road_density_km_per_km2')
    df.to_csv(OUT / 'network_completeness_by_country.csv', index=False, encoding='utf-8-sig')
    lines = []

    def say(t=''):
        print(t)
        lines.append(t)

    say('=== lowest road density (noded km per km2) ===')
    say(df.head(8)[['iso3', 'noded_km', 'area_km2', 'road_density_km_per_km2', 'local_share_pct',
                    'urban_share_pct', 'benchmark_gap_pp']].round(3).to_string(index=False))
    say()
    say('=== Spearman correlations with the benchmark gap (MAP - model) ===')
    for col in ('road_density_km_per_km2', 'local_share_pct', 'urban_share_pct',
                'population_density_per_km2', 'planet_known_share_pct', 'noded_km'):
        sub = df.dropna(subset=[col, 'benchmark_gap_pp'])
        say(f'  {col:30s} rho = {sub.benchmark_gap_pp.corr(sub[col], method="spearman"):+.3f} '
            f'(n={len(sub)})')
    say()
    say('=== Spearman correlations with the direction-law residual ===')
    for col in ('road_density_km_per_km2', 'local_share_pct', 'urban_share_pct',
                'population_density_per_km2', 'planet_known_share_pct'):
        sub = df.dropna(subset=[col, 'direction_residual_pp'])
        say(f'  {col:30s} rho = {sub.direction_residual_pp.corr(sub[col], method="spearman"):+.3f} '
            f'(n={len(sub)})')
    # two-predictor refinement of the direction law: arterial coverage + urban share
    say()
    say('=== two-predictor direction law (arterial coverage + urban share) ===')
    d2 = direction.dropna(subset=['arterial_60min_pct', 'corrected_minus_arterial_pp']).copy()
    d2 = d2.merge(df[['iso3', 'urban_share_pct']], on='iso3', how='left')
    d2 = d2.dropna(subset=['urban_share_pct'])
    X = np.column_stack([np.ones(len(d2)), d2.arterial_60min_pct, d2.urban_share_pct])
    y = d2.corrected_minus_arterial_pp.to_numpy(float)
    coef, *_ = np.linalg.lstsq(X, y, rcond=None)
    pred = X @ coef
    r2_two = 1 - float(((y - pred) ** 2).sum()) / float(((y - y.mean()) ** 2).sum())
    x1 = d2.arterial_60min_pct.to_numpy(float)
    coef1, *_ = np.linalg.lstsq(np.column_stack([np.ones(len(d2)), x1]), y, rcond=None)
    r2_one = 1 - float(((y - np.column_stack([np.ones(len(d2)), x1]) @ coef1) ** 2).sum()) \
        / float(((y - y.mean()) ** 2).sum())
    say(f'  delta = {coef[0]:.1f} {coef[1]:+.3f} x arterial {coef[2]:+.3f} x urban_share')
    say(f'  R2 = {r2_two:.3f} vs {r2_one:.3f} for arterial alone (n={len(d2)} countries-services)')
    d2['pred_two'] = pred
    d2.to_csv(OUT / 'direction_law_two_predictor.csv', index=False, encoding='utf-8-sig')
    (OUT / 'network_completeness_summary.txt').write_text('\n'.join(lines), encoding='utf-8')
    print(f'wrote {OUT}')


if __name__ == '__main__':
    main()
