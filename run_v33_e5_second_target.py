# -*- coding: utf-8 -*-
"""v33 实验 E5：CPAS 同服务第二外部靶子（cell-level 检验）。

CPAS 只覆盖少数国家，不能复现 30 国跨国家回归，因此改用 0.05° 人口像元：
  1) 把 CPAS 100 m 旅行时间聚合为 0.05° 人口加权 60 分钟份额；
  2) 与本文 arterial-only 基线、含本地路基线对齐；
  3) 以 0.05° 格内的 Planet 主干路长度作为覆盖率协变量；
  4) 比较 Δ(external − arterial) 与 Δ(external − full) 对该协变量的回归。

结论方向预期：CPAS 与本文 arterial-only 基线之差会随主干路密度系统变化；
CPAS 与本文含本地路基线之差则弱得多。
"""
import argparse
import json
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from statsmodels.regression.linear_model import OLS
from statsmodels.tools import add_constant

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'output/experiments/v33'
OUT.mkdir(parents=True, exist_ok=True)

CPAS = ROOT / 'data/external/accessibility_products/cpas'
ROADS = {
    'KEN': ROOT / 'data/external/hdx/roads/heigit_KE_planet_roadsurface_lines.gpkg',
    'ETH': ROOT / 'data/external/hdx/roads/heigit_ET_planet_roadsurface_lines.gpkg',
    'MOZ': ROOT / 'data/external/hdx/roads/heigit_MZ_planet_roadsurface_lines.gpkg',
}
CPAS_FILES = {
    'KEN': 'service-area-kenya-motorised.tif',
    'ETH': 'service-area-ethiopia-motorised.tif',
    'MOZ': 'service-area-mozambique-motorised.tif',
}


def _cell_id(x, y):
    return np.floor(x / 0.05) * 0.05 + 0.025, np.floor(y / 0.05) * 0.05 + 0.025


def load_full_aggregated(iso):
    p = ROOT / 'output/experiments/cell_travel_times' / f'{iso}.parquet'
    df = pd.read_parquet(p)[['lon', 'lat', 'population_counts', 'travel_health_min']]
    lon05, lat05 = _cell_id(df.lon.to_numpy(float), df.lat.to_numpy(float))
    df['lon05'] = np.round(lon05, 3)
    df['lat05'] = np.round(lat05, 3)
    g = df.groupby(['lon05', 'lat05'], as_index=False).apply(
        lambda x: pd.Series({
            'pop': x.population_counts.sum(),
            'full_share': np.average(
                x.travel_health_min <= 60,
                weights=x.population_counts,
            ),
        })
    )
    return g


def load_arterial(iso):
    path = ROOT / 'output/prototype/multicountry' / iso.lower() / 'access_cells_0p05deg.geojson'
    df = gpd.read_file(path).drop(columns='geometry')
    df = df[['lon05', 'lat05', 'population', 'health_baseline']].rename(
        columns={'population': 'pop_art', 'health_baseline': 'art_travel'})
    df['lon05'] = df.lon05.round(3)
    df['lat05'] = df.lat05.round(3)
    df['arterial_share'] = np.where(
        pd.notna(df.art_travel) & (df.art_travel <= 60), 1.0, 0.0)
    return df


def load_cpas(iso):
    tif = CPAS / CPAS_FILES[iso]
    parquet = ROOT / 'output/experiments/cell_travel_times' / f'{iso}.parquet'
    pts = pd.read_parquet(parquet, columns=['lon', 'lat'])
    coords = list(zip(pts.lon.to_numpy(float), pts.lat.to_numpy(float)))
    with rasterio.open(tif) as src:
        vals = np.array([v[0] for v in src.sample(coords)], dtype=float)
    out = pts.copy()
    out['cpas_min'] = vals / 60.0
    return out


def load_road_density(iso):
    gdf = gpd.read_file(ROADS[iso])
    gdf3857 = gdf.to_crs(3857)
    mid = gdf.geometry.representative_point()
    lon05, lat05 = _cell_id(mid.x.to_numpy(float), mid.y.to_numpy(float))
    df = pd.DataFrame({
        'lon05': np.round(lon05, 3), 'lat05': np.round(lat05, 3),
        'length_m': gdf3857.geometry.length.to_numpy(float),
    })
    return df.groupby(['lon05', 'lat05'], as_index=False).length_m.sum()


def run_country(iso):
    print(f'[{iso}] assembling cell-level frame', flush=True)
    full = load_full_aggregated(iso)
    art = load_arterial(iso)
    cpas = load_cpas(iso)
    cpas['lon05'], cpas['lat05'] = _cell_id(
        cpas.lon.to_numpy(float), cpas.lat.to_numpy(float))
    cpas['lon05'] = cpas.lon05.round(3)
    cpas['lat05'] = cpas.lat05.round(3)
    cpas_agg = cpas.groupby(['lon05', 'lat05'], as_index=False).apply(
        lambda x: pd.Series({'cpas_mean_min': x.cpas_min.mean()}))
    roads = load_road_density(iso)

    frame = full.merge(art, on=['lon05', 'lat05'], how='left')
    frame = frame.merge(cpas_agg, on=['lon05', 'lat05'], how='left')
    frame = frame.merge(roads, on=['lon05', 'lat05'], how='left')
    frame['length_m'] = frame['length_m'].fillna(0.0)
    frame['pop'] = frame['pop'].fillna(frame['pop_art'])
    frame = frame[frame['pop'] > 0]
    frame['cpas_share'] = frame['cpas_mean_min'] <= 60
    frame['y_ext_art'] = frame['cpas_share'].astype(float) - frame['arterial_share']
    frame['y_ext_full'] = frame['cpas_share'].astype(float) - frame['full_share']
    frame['log_length'] = np.log1p(frame['length_m'])

    # 人口加权的 cell-level 份额，用于国家汇总
    weights = frame['pop']
    country = {
        'iso3': iso,
        'n_cells': int(len(frame)),
        'pop_million': float(weights.sum() / 1e6),
        'cpas_share_60': float(np.average(frame['cpas_share'], weights=weights)),
        'arterial_share_60': float(np.average(frame['arterial_share'], weights=weights)),
        'full_share_60': float(np.average(frame['full_share'], weights=weights)),
        'flip_ext_vs_art_share': float(
            np.average(frame['cpas_share'] < frame['arterial_share'], weights=weights)),
        'flip_ext_vs_full_share': float(
            np.average(frame['cpas_share'] < frame['full_share'], weights=weights)),
    }

    regs = []
    for yname, label in [('y_ext_art', 'external_vs_arterial'),
                         ('y_ext_full', 'external_vs_full')]:
        sub = frame[['log_length', 'pop', yname]].dropna().copy()
        x = sub['log_length'].to_numpy(float)
        y = sub[yname].to_numpy(float)
        o = OLS(y, add_constant(x)).fit()
        w = sub['pop'].to_numpy(float)
        ow = OLS(y, add_constant(x), hasconst=True).fit(
            cov_type='HC1', weights=w)
        regs.append({
            'iso3': iso, 'contrast': label, 'n_cells': len(sub),
            'ols_r2': float(o.rsquared), 'slope': float(o.params[1]),
            'p': float(o.pvalues[1]),
            'wls_r2': float(ow.rsquared), 'wls_slope': float(ow.params[1]),
            'wls_p': float(ow.pvalues[1]),
        })
    return pd.DataFrame([country]), pd.DataFrame(regs)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--countries', default='KEN,ETH,MOZ')
    args = ap.parse_args()
    countries = [x.strip().upper() for x in args.countries.split(',')]
    country_rows, reg_rows = [], []
    for iso in countries:
        if not (CPAS / CPAS_FILES[iso]).exists():
            print(f'skip {iso}: CPAS file missing')
            continue
        try:
            c, r = run_country(iso)
            country_rows.append(c)
            reg_rows.append(r)
        except Exception as e:
            print(f'{iso} failed: {type(e).__name__} {e}', flush=True)
    if country_rows:
        cs = pd.concat(country_rows, ignore_index=True)
        rs = pd.concat(reg_rows, ignore_index=True)
        cs.to_csv(OUT / 'e5_cpas_country_summary.csv', index=False,
                  encoding='utf-8-sig')
        rs.to_csv(OUT / 'e5_cpas_regression.csv', index=False,
                  encoding='utf-8-sig')
        json.dump({
            'country_summary': cs.to_dict(orient='records'),
            'regression': rs.to_dict(orient='records'),
        }, open(OUT / 'e5_cpas_second_target.json', 'w'), indent=2,
            ensure_ascii=False)
        print('\ncountry summary')
        print(cs.to_string(index=False))
        print('\nregression')
        print(rs.to_string(index=False))


if __name__ == '__main__':
    main()
