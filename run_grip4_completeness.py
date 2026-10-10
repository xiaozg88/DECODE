# -*- coding: utf-8 -*-
"""Stage 1: independent road-network reference from GRIP4 (Meijer et al. 2018).

Downloads the GRIP4 road-density rasters (road-type aggregates tp1-tp4, ~10 MB total, Zenodo
record 6426133/6420961), samples them on the same WorldPop cell grid used by the model and
compares per-country GRIP4 density with our noded-network density, the MAP benchmark gap and
the direction-law residuals.

GRIP4 is an inventory-based, pre-OSM-era reference, so it is used as an independent
*relative* completeness indicator, not as a like-for-like network.

Outputs ``output/experiments/grip4_completeness/``.
"""
from __future__ import annotations

import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
import requests

import run_experiment_29_weight_sensitivity as sens

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'output/experiments/grip4_completeness'
CACHE = ROOT / 'data/external/grip4'
BASE = 'https://zenodo.org/api/records/6420961/files/'
FILES = ['GRIP4_density_tp1.zip', 'GRIP4_density_tp2.zip', 'GRIP4_density_tp3.zip',
         'GRIP4_density_tp4.zip', 'GRIP4_density_tp5.zip', 'GRIP4_density_total.zip']


def fetch(name: str) -> Path | None:
    CACHE.mkdir(parents=True, exist_ok=True)
    dest = CACHE / name
    if dest.exists() and dest.stat().st_size > 0:
        return dest
    for attempt in range(3):
        try:
            with requests.get(BASE + name + '/content', stream=True, timeout=600) as r:
                if r.status_code != 200:
                    print(f'  {name}: HTTP {r.status_code}')
                    return None
                with dest.open('wb') as f:
                    for chunk in r.iter_content(chunk_size=1 << 20):
                        if chunk:
                            f.write(chunk)
            print(f'  downloaded {name} ({dest.stat().st_size/1e6:.1f} MB)')
            return dest
        except Exception as exc:
            print(f'  {name}: retry {attempt+1} ({type(exc).__name__})')
    return None


def extract(path: Path) -> list[Path]:
    target = path.with_suffix('')
    if not target.exists():
        target.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(path) as zf:
            for member in zf.infolist():
                out = (target / member.filename).resolve()
                if str(out).startswith(str(target.resolve())) and len(str(out)) < 250:
                    zf.extract(member, target)
    return sorted(list(target.rglob('*.tif')) + list(target.rglob('*.asc')))


def sample(path: Path, lon: np.ndarray, lat: np.ndarray) -> np.ndarray:
    with rasterio.open(path) as src:
        rows, cols = rasterio.transform.rowcol(src.transform, lon, lat)
        rows = np.asarray(rows); cols = np.asarray(cols)
        valid = (rows >= 0) & (rows < src.height) & (cols >= 0) & (cols < src.width)
        out = np.full(len(lon), np.nan, dtype='float32')
        if valid.any():
            window = rasterio.windows.Window(cols[valid].min(), rows[valid].min(),
                                             cols[valid].max() - cols[valid].min() + 1,
                                             rows[valid].max() - rows[valid].min() + 1)
            data = src.read(1, window=window).astype('float32')
            if src.nodata is not None:
                data = np.where(data == src.nodata, np.nan, data)
            r2 = rows[valid] - int(window.row_off)
            c2 = cols[valid] - int(window.col_off)
            out[valid] = data[r2, c2]
    return out


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    tifs = []
    for name in FILES:
        path = fetch(name)
        if path:
            tifs.extend(extract(path))
    tifs = [t for t in tifs if t.exists()]
    print(f'{len(tifs)} GRIP4 rasters available')
    if not tifs:
        print('no GRIP4 rasters; stage blocked')
        return
    with rasterio.open(tifs[0]) as src:
        print('example raster:', tifs[0].name, src.crs, src.res, src.width, src.height)
    network = pd.read_csv(ROOT / 'output/experiments/network_completeness'
                          / 'network_completeness_by_country.csv')
    rows = []
    for iso in sorted(network.iso3.unique()):
        try:
            xy, xy3857, density, counts = sens.population_weights(iso)
        except Exception as exc:
            print(f'{iso}: population raster missing ({type(exc).__name__})')
            continue
        rec = {'iso3': iso, 'cells': len(xy)}
        for tif in tifs:
            tag = tif.stem.lower()
            if 'total' in tag:
                key = 'grip_total_mean_density'
            else:
                key = 'grip_' + tag.split('_')[1] + '_mean_density'
            vals = sample(tif, xy[:, 0], xy[:, 1])
            ok = np.isfinite(vals)
            rec[key] = float(np.mean(vals[ok])) if ok.any() else np.nan
            if 'total' in tag:
                rec['grip_all_mean_density'] = rec[key]
            if 'tp5' in tag:
                rec['grip_local_mean_density'] = rec[key]
        rows.append(rec)
        print(f'{iso} done', flush=True)
    grip = pd.DataFrame(rows)
    grip.to_csv(OUT / 'grip4_density_by_country.csv', index=False, encoding='utf-8-sig')
    merged = network.merge(grip, on='iso3', how='left')
    merged['grip_over_model_density'] = merged.grip_all_mean_density / merged.road_density_km_per_km2
    merged.to_csv(OUT / 'grip4_vs_network_density.csv', index=False, encoding='utf-8-sig')
    lines = []

    def say(t=''):
        print(t)
        lines.append(t)

    say('=== GRIP4 density vs model network density ===')
    cols = ['iso3', 'road_density_km_per_km2', 'grip_all_mean_density',
            'grip_over_model_density', 'benchmark_gap_pp', 'direction_residual_pp']
    say(merged[cols].sort_values('grip_over_model_density').round(3).to_string(index=False))
    say()
    for target in ('benchmark_gap_pp', 'direction_residual_pp'):
        sub = merged.dropna(subset=['grip_over_model_density', target])
        if len(sub) > 5:
            say(f'corr(GRIP/model density ratio, {target}) = '
                f'{sub.grip_over_model_density.corr(sub[target], method="spearman"):+.3f} (n={len(sub)})')
    (OUT / 'grip4_summary.txt').write_text('\n'.join(lines), encoding='utf-8')
    print(f'wrote {OUT}')


if __name__ == '__main__':
    main()
