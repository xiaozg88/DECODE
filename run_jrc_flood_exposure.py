# -*- coding: utf-8 -*-
"""Stage 2: uniform 100-year flood exposure for all 30 countries (JRC global flood map).

Source: ``floodMapGL_rp100y.zip`` (JRC global river flood hazard map, 100-year return
period, water depth in metres) from the JRC open-data FTP server.

For every country we compute

* population exposure: share of population (area-weighted counts) in cells with depth > 0
  and > 0.5 m,
* network exposure: share of noded network length whose segment midpoint is flooded,
  overall and for unpaved segments,

and relate network exposure to the observed-event affected shares used by the exposure law.

Outputs ``output/experiments/jrc_flood_exposure/``.
"""
from __future__ import annotations

import zipfile
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
import rasterio
import requests

import run_experiment_29_weight_sensitivity as sens

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'output/experiments/jrc_flood_exposure'
CACHE = ROOT / 'data/external/jrc_flood'
URL = 'https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/FLOODS/GlobalMaps/floodMapGL_rp100y.zip'


def fetch() -> list[Path]:
    CACHE.mkdir(parents=True, exist_ok=True)
    zip_path = CACHE / 'floodMapGL_rp100y.zip'
    if not (zip_path.exists() and zip_path.stat().st_size > 0):
        with requests.get(URL, stream=True, timeout=600,
                          headers={'User-Agent': 'Mozilla/5.0 (research)'}) as r:
            r.raise_for_status()
            with zip_path.open('wb') as f:
                for chunk in r.iter_content(chunk_size=1 << 20):
                    if chunk:
                        f.write(chunk)
    extract = CACHE / 'floodMapGL_rp100y'
    if not extract.exists():
        extract.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(zip_path) as zf:
            for member in zf.infolist():
                target = (extract / member.filename).resolve()
                if str(target).startswith(str(extract.resolve())) and len(str(target)) < 250:
                    zf.extract(member, extract)
    files = sorted(list(extract.rglob('*.tif')) + list(extract.rglob('*.asc')))
    return files


def depth_at(rasters: list[Path], lon: np.ndarray, lat: np.ndarray) -> np.ndarray:
    out = np.full(len(lon), np.nan, dtype='float32')
    for path in rasters:
        with rasterio.open(path) as src:
            rows, cols = rasterio.transform.rowcol(src.transform, lon, lat)
            rows = np.asarray(rows); cols = np.asarray(cols)
            inside = (rows >= 0) & (rows < src.height) & (cols >= 0) & (cols < src.width)
            if not inside.any():
                continue
            window = rasterio.windows.Window(cols[inside].min(), rows[inside].min(),
                                             cols[inside].max() - cols[inside].min() + 1,
                                             rows[inside].max() - rows[inside].min() + 1)
            data = src.read(1, window=window).astype('float32')
            if src.nodata is not None:
                data = np.where(data == src.nodata, np.nan, data)
            r2 = rows[inside] - int(window.row_off)
            c2 = cols[inside] - int(window.col_off)
            out[inside] = data[r2, c2]
    return out


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    rasters = fetch()
    if not rasters:
        print('no JRC raster found; stage blocked')
        return
    with rasterio.open(rasters[0]) as src:
        print('raster:', rasters[0].name, 'crs', src.crs, 'res', src.res,
              'size', (src.width, src.height), 'nodata', src.nodata)
    rows = []
    for iso in sorted(pd.read_csv(ROOT / 'output/experiments/network_completeness'
                                  / 'network_completeness_by_country.csv').iso3.unique()):
        xy, xy3857, density, counts = sens.population_weights(iso)
        pop_depth = depth_at(rasters, xy[:, 0], xy[:, 1])
        # the JRC map stores ONLY flooded cells (nodata elsewhere), so exposure is measured
        # against the full population/network denominator and non-finite cells count as dry
        flooded_pop = np.isfinite(pop_depth) & (pop_depth > 0)
        deep_pop = np.isfinite(pop_depth) & (pop_depth > 0.5)
        pop_total = float(counts.sum())
        rec = {'iso3': iso, 'population_millions': pop_total / 1e6,
               'population_exposed_pct': 100 * counts[flooded_pop].sum() / max(pop_total, 1e-9),
               'population_exposed_gt0p5m_pct': 100 * counts[deep_pop].sum() / max(pop_total, 1e-9)}
        # network exposure from cached segments (midpoint test, straight-line length weight)
        pieces = sens.build_pieces(iso)
        con = duckdb.connect()
        tbl = con.execute(
            f"SELECT sx, sy, ex, ey, is_unpaved FROM read_parquet('{pieces.as_posix()}')"
        ).fetch_arrow_table()
        con.close()
        sx = tbl.column('sx').to_numpy(); sy = tbl.column('sy').to_numpy()
        ex = tbl.column('ex').to_numpy(); ey = tbl.column('ey').to_numpy()
        unpaved = tbl.column('is_unpaved').to_numpy(zero_copy_only=False)
        mid_lon = (sx + ex) / 2.0
        mid_lat = (sy + ey) / 2.0
        depth = depth_at(rasters, mid_lon, mid_lat)
        length_km = np.sqrt(((ex - sx) * 111.32 * np.cos(np.radians(mid_lat))) ** 2
                            + ((ey - sy) * 110.574) ** 2)
        valid = length_km > 0
        total = float(length_km[valid].sum())
        flooded_mask = valid & np.isfinite(depth) & (depth > 0)
        deep_mask = valid & np.isfinite(depth) & (depth > 0.5)
        flooded = float(length_km[flooded_mask].sum())
        flooded_deep = float(length_km[deep_mask].sum())
        unpaved_flooded = float(length_km[flooded_mask & unpaved].sum())
        rec.update({'network_km': total / 1000,
                    'network_exposed_pct': 100 * flooded / max(total, 1e-9),
                    'network_exposed_gt0p5m_pct': 100 * flooded_deep / max(total, 1e-9),
                    'unpaved_exposed_pct_of_network': 100 * unpaved_flooded / max(total, 1e-9)})
        rows.append(rec)
        print(f'{iso}: pop exposed {rec["population_exposed_pct"]:.2f}% | '
              f'network exposed {rec["network_exposed_pct"]:.2f}%', flush=True)
        pd.DataFrame(rows).to_csv(OUT / 'jrc_100y_exposure_30countries.csv', index=False,
                                  encoding='utf-8-sig')
        del tbl
    df = pd.DataFrame(rows)
    df.to_csv(OUT / 'jrc_100y_exposure_30countries.csv', index=False, encoding='utf-8-sig')
    # relate to observed-event exposure where available
    ev = pd.read_csv(ROOT / 'output/experiments/hazard_exposure/hazard_event_table.csv')
    obs = ev.groupby('iso3').affected_share_pct.max().rename('observed_max_affected_share_pct')
    merged = df.merge(obs, on='iso3', how='left')
    merged.to_csv(OUT / 'jrc_vs_observed_exposure.csv', index=False, encoding='utf-8-sig')
    lines = []

    def say(t=''):
        print(t)
        lines.append(t)

    say('=== JRC 100-year exposure (30 countries) ===')
    say(df.sort_values('network_exposed_pct', ascending=False)
        [['iso3', 'population_exposed_pct', 'network_exposed_pct',
          'network_exposed_gt0p5m_pct', 'unpaved_exposed_pct_of_network']]
        .round(2).to_string(index=False))
    sub = merged.dropna(subset=['observed_max_affected_share_pct'])
    if len(sub) > 3:
        say()
        say(f'corr(JRC 100-yr network exposure, max observed event affected share) = '
            f'{sub.network_exposed_pct.corr(sub.observed_max_affected_share_pct, method="spearman"):+.3f} '
            f'(n={len(sub)})')
    (OUT / 'jrc_exposure_summary.txt').write_text('\n'.join(lines), encoding='utf-8')
    print(f'wrote {OUT}')


if __name__ == '__main__':
    main()
