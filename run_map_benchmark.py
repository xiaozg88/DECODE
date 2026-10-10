# -*- coding: utf-8 -*-
"""P1.7: independent benchmark against the Malaria Atlas Project healthcare travel-time map.

``Explorer:2020_motorized_travel_time_to_healthcare`` (Weiss et al., Nature Medicine 2020)
is a global 1 km estimate of travel time (motorised, including access to the road
network) to the nearest healthcare facility.  It is produced from different inputs and a
different cost model than our corridor model, so agreement is meaningful evidence rather
than a self-comparison.

For every sample country the script

1. pulls the country window from the MAP WCS service,
2. samples it at the WorldPop cell centres used by the model,
3. computes population-weighted 30/60/120-minute shares and mean travel time,
4. compares them with the model baselines (canonical and convention-corrected).

Outputs ``output/experiments/benchmark_validation/`` (per-country table + scatter figure).
"""
from __future__ import annotations

import argparse
import io
import time
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import rasterio
import requests

import run_experiment_29_weight_sensitivity as sens

ROOT = Path(__file__).resolve().parent
EXP = ROOT / 'output/experiments/experiment_29_global_expansion'
OUT_DIR = ROOT / 'output/experiments/benchmark_validation'
CACHE = ROOT / 'data/external/map'
WCS = 'https://data.malariaatlas.org/geoserver/ows'
COVERAGE = 'Explorer:2020_motorized_travel_time_to_healthcare'
SAMPLE = ['PAK', 'MOZ', 'BGD', 'ETH', 'KEN', 'COL', 'PHL']  # core first, then additions


def fetch_country(iso: str, bbox, res=0.0083333333) -> Path | None:
    CACHE.mkdir(parents=True, exist_ok=True)
    dest = CACHE / f'map_health_{iso}.tif'
    if dest.exists() and dest.stat().st_size > 0:
        return dest
    minx, miny, maxx, maxy = bbox
    width = int(min((maxx - minx) / res, 6000)) or 1
    height = int(min((maxy - miny) / res, 6000)) or 1
    params = {'service': 'WCS', 'version': '1.0.0', 'request': 'GetCoverage',
              'coverage': COVERAGE, 'CRS': 'EPSG:4326',
              'BBOX': f'{minx},{miny},{maxx},{maxy}', 'WIDTH': width, 'HEIGHT': height,
              'FORMAT': 'GeoTIFF'}
    for attempt in range(3):
        try:
            r = requests.get(WCS, params=params, timeout=600)
            if r.status_code != 200 or len(r.content) < 1000:
                print(f'  {iso}: WCS {r.status_code}, {len(r.content)} bytes', flush=True)
                time.sleep(5)
                continue
            dest.write_bytes(r.content)
            return dest
        except Exception as exc:
            print(f'  {iso}: {type(exc).__name__} on attempt {attempt + 1}', flush=True)
            time.sleep(5 * (attempt + 1))
    return None


def country_bbox(iso: str):
    path = ROOT / 'data/external/hdx/countries' / iso / f'{iso.lower()}_pd_2020_1km.tif'
    with rasterio.open(path) as src:
        return src.bounds


def sample_map(path: Path, lon: np.ndarray, lat: np.ndarray) -> np.ndarray:
    with rasterio.open(path) as src:
        if src.crs is None:
            return np.full(len(lon), np.nan)
        rows, cols = rasterio.transform.rowcol(src.transform, lon, lat)
        rows = np.asarray(rows); cols = np.asarray(cols)
        valid = (rows >= 0) & (rows < src.height) & (cols >= 0) & (cols < src.width)
        out = np.full(len(lon), np.nan, dtype='float32')
        if valid.any():
            window = rasterio.windows.Window(cols[valid].min(), rows[valid].min(),
                                             cols[valid].max() - cols[valid].min() + 1,
                                             rows[valid].max() - rows[valid].min() + 1)
            data = src.read(1, window=window).astype('float32')
            nodata = src.nodata
            if nodata is not None:
                data = np.where(data == nodata, np.nan, data)
            r2 = rows[valid] - int(window.row_off)
            c2 = cols[valid] - int(window.col_off)
            out[valid] = data[r2, c2]
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--countries', nargs='+', default=SAMPLE + [
        'EGY', 'GEO', 'GHA', 'GTM', 'HND', 'IDN', 'IND', 'JOR', 'KGZ', 'KHM', 'LKA',
        'MEX', 'MLI', 'NGA', 'NPL', 'PER', 'PNG', 'RWA', 'SEN', 'TUR', 'TZA', 'VNM', 'ZMB'])
    a = ap.parse_args()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    model = pd.read_csv(ROOT / 'output/experiments/corrected_main'
                        / 'corrected_main_access_30countries.csv')
    rows = []
    for iso in a.countries:
        path = fetch_country(iso, country_bbox(iso))
        if path is None:
            print(f'{iso}: benchmark unavailable')
            continue
        xy, xy3857, density, counts = sens.population_weights(iso)
        tt = sample_map(path, xy[:, 0], xy[:, 1])
        ok = np.isfinite(tt) & (tt > 0)
        if ok.sum() < 100:
            print(f'{iso}: no valid benchmark cells')
            continue
        pop = counts[ok]; t = tt[ok]
        row = {'iso3': iso, 'benchmark_cells': int(ok.sum()),
               'benchmark_population_millions': float(pop.sum()) / 1e6,
               'benchmark_mean_travel_min': float(np.average(t, weights=pop)),
               'benchmark_share_30min_pct': 100 * pop[t <= 30].sum() / pop.sum(),
               'benchmark_share_60min_pct': 100 * pop[t <= 60].sum() / pop.sum(),
               'benchmark_share_120min_pct': 100 * pop[t <= 120].sum() / pop.sum()}
        m = model[(model.iso3 == iso) & (model.service == 'health')]
        if len(m):
            m = m.iloc[0]
            row.update({'model_share_60min_canonical': m.share_60min_pct_density_mercator_none,
                        'model_share_60min_corrected': m.share_60min_pct_counts_geodesic_none,
                        'model_share_30min_corrected': m.share_30min_pct_counts_geodesic_none,
                        'arterial_60min_pct': m.arterial_60min_pct})
        rows.append(row)
        print(f'{iso}: MAP 60min={row["benchmark_share_60min_pct"]:.1f}% '
              f'model={row.get("model_share_60min_corrected", float("nan")):.1f}%', flush=True)
        pd.DataFrame(rows).to_csv(OUT_DIR / 'map_health_travel_time_vs_model.csv', index=False,
                                  encoding='utf-8-sig')
    df = pd.DataFrame(rows)
    if df.empty:
        print('no benchmark rows produced')
        return
    df.to_csv(OUT_DIR / 'map_health_travel_time_vs_model.csv', index=False, encoding='utf-8-sig')
    sub = df.dropna(subset=['model_share_60min_corrected'])
    print()
    print(f'countries compared: {len(sub)}')
    for col in ['model_share_60min_canonical', 'model_share_60min_corrected']:
        r = sub.benchmark_share_60min_pct.corr(sub[col])
        rho = sub.benchmark_share_60min_pct.corr(sub[col], method='spearman')
        bias = (sub[col] - sub.benchmark_share_60min_pct).mean()
        print(f'{col:32s} Pearson {r:.3f}  Spearman {rho:.3f}  mean bias {bias:+.2f} pp')
    fig, ax = plt.subplots(figsize=(3.4, 3.2))
    ax.scatter(sub.benchmark_share_60min_pct, sub.model_share_60min_corrected, s=18,
               color='#08519c', linewidths=0)
    lim = [0, 105]
    ax.plot(lim, lim, '--', color='black', lw=.8)
    ax.set_xlim(lim); ax.set_ylim(lim)
    ax.set_xlabel('MAP travel time to healthcare, 60-min share (%)')
    ax.set_ylabel('This model, corrected convention (%)')
    r = sub.benchmark_share_60min_pct.corr(sub.model_share_60min_corrected)
    ax.set_title('Independent healthcare-access benchmark')
    ax.text(.03, .95, f'r = {r:.2f}, n = {len(sub)} countries', transform=ax.transAxes,
            va='top', fontsize=6.5)
    fig.savefig(OUT_DIR / 'map_benchmark_scatter.png', bbox_inches='tight', dpi=300)
    print(f'wrote {OUT_DIR}')


if __name__ == '__main__':
    main()
