# -*- coding: utf-8 -*-
"""v34 实验E6（方案 C）：30 国可比外部产品 —— SDG 9.1.1 / Rural Access Index (RAI)。

动机
----
方案 A（E4）与方案 B（E5）已证明："加入本地路前后"这一差分形式本身就能产生
高 R² 的表观规律，与具体实现无关。E6 再加一个**覆盖全部 30 国、独立于 MAP 2020**
的外部产品：CIESIN/SEDAC 与 World Bank 联合发布的 SDG 9.1.1 RAI（2023 Release，
CC BY 4.0，doi:10.7910/DVN/FFQ1WT）。

RAI 官方定义：乡村人口中位于"全天候（铺装）道路"2 km 缓冲带内的比例。
本脚本用本文同一套人口（WorldPop 2020）、同一套乡村掩膜（GHS-SMOD E2020，1 km，
类别 11–13）与同一套路网，计算本文的两套 RAI 等价量：

    RAI_arterial  = 铺装主干路（Planet arterial & surface_class=='paved'）2 km 覆盖
    RAI_full      = 含本地路的全路网 2 km 覆盖
    RAI_full_paved= 全路网中仅铺装（surface_class=='paved'）2 km 覆盖（敏感性）

再构造差分并重跑与 E4 相同的推断（OLS / LOCO / 方向正确率 / 负值国 /
块自举零模型 / 完全打乱零模型）。

关键点：RAI 域的"主干覆盖"不是主稿 60 分钟的 `arterial_coverage`
（那是"主干-only 60 分钟卫生可达份额"，与 2 km 近路几乎不相关，r ≈ −0.13），
而是 `RAI_arterial`（仅铺装主干路 2 km 覆盖）。用正确的 RAI 域自变量后：

    (RAI_full − RAI_arterial) ~ RAI_arterial   -> R² ≈ 0.75（与主稿 60 分钟域
        (corrected − arterial) ~ arterial 的 R² = 0.746、r = −0.864 几乎一致）

即"加本地路的纠正量"对"主干覆盖"的差分形式，在 RAI 域同样制造高 R² 表观规律，
与 30 国 60 分钟可达性的核心发现一致。此外，外部靶子 magnitude 直接显示：
本文主干-only 口径比官方 RAI 平均低 ~32 pp（0/30 为负），含本地路后基本贴合官方值。

数据来源（RAI national CSV）：
    data/external/accessibility_products/rai_sdg911/sdgi-9-1-1-rai-2023-csv/
        sdgi-9-1-1-rai-2023-national.csv
    （从 Harvard Dataverse doi:10.7910/DVN/FFQ1WT 下载；CC BY 4.0）
"""
from __future__ import annotations

import argparse
import json
import os
import time

import numpy as np
import pandas as pd
import pyogrio
import pyproj
import rasterio
import shapely
from rasterio.features import rasterize
from rasterio.transform import from_origin
from scipy.ndimage import distance_transform_edt
from scipy import stats
from statsmodels.regression.linear_model import OLS
from statsmodels.tools import add_constant

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, 'output/experiments/v34')
os.makedirs(OUT, exist_ok=True)
CACHE = os.path.join(OUT, '_country_cache')
os.makedirs(CACHE, exist_ok=True)

GHS = os.path.join(ROOT, 'data/external/ghs',
                   'GHS_SMOD_E2020_GLOBE_R2023A_54009_1000_V1_0.tif')
RAI_CSV = os.path.join(
    ROOT, 'data/external/accessibility_products/rai_sdg911',
    'sdgi-9-1-1-rai-2023-csv', 'sdgi-9-1-1-rai-2023-national.csv')
DECOMP = os.path.join(ROOT, 'output/experiments/direction_law_v2',
                      'nested_decomposition.csv')

COUNTRY_DIR = os.path.join(ROOT, 'data/external/hdx/countries')
NODED_STEM = {'MOZ': 'mozambique'}

SEED = 20261007
NPERM = 2000
BUFFER_M = 2000.0
GRID_M = 1000.0

# GHS-SMOD E2020 类别：11 低密度乡村、12 低密度乡村、13 乡村聚落。
# （21–23 与 30 为城镇/城郊/城市中心。）
RURAL_CLASSES = {11, 12, 13}


def _log(msg):
    print(msg, flush=True)


def noded_path(iso: str) -> str:
    stem = NODED_STEM.get(iso, iso.lower())
    d = os.path.join(COUNTRY_DIR, iso, 'local_roads')
    cands = [p for p in sorted(os.listdir(d))
             if p.startswith(stem) and p.endswith('_noded_segments.gpkg')
             and 'tiled' not in p]
    if not cands:
        raise FileNotFoundError(f'no noded segments under {d}')
    return os.path.join(d, cands[0])


def cell_path(iso: str) -> str:
    return os.path.join(ROOT, 'output/experiments/cell_travel_times', f'{iso}.parquet')


def utm_epsg(lon: float, lat: float) -> int:
    zone = int((lon + 180.0) // 6.0) + 1
    return 32600 + zone if lat >= 0 else 32700 + zone


def load_ghs_smod():
    with rasterio.open(GHS) as gds:
        smod = gds.read(1)
        tr = gds.transform
    return smod, tr.a, tr.c, tr.e, tr.f


def rural_mask(lon, lat, smod, a, c, e, f):
    """逐点采样 GHS-SMOD，返回乡村掩膜（类别 11–13）。"""
    t = pyproj.Transformer.from_crs('EPSG:4326', 'ESRI:54009', always_xy=True)
    x, y = t.transform(lon, lat)
    col = ((x - c) / a).astype(np.int64)
    row = ((y - f) / e).astype(np.int64)
    valid = (row >= 0) & (row < smod.shape[0]) & (col >= 0) & (col < smod.shape[1])
    val = np.full(len(lon), -1, dtype=np.int16)
    val[valid] = smod[row[valid], col[valid]]
    return np.isin(val, list(RURAL_CLASSES))


def road_grid(iso: str, sel, utm_crs, transform, shape):
    """把 noded 路网按 sel(DataFrame -> bool ndarray) 过滤后栅格化到 UTM 网格。

    返回 uint8 网格（1=有路）。分块读取，避免一次性把整国路网载入内存。
    """
    path = noded_path(iso)
    n = int(pyogrio.read_info(path)['features'])
    to_utm = pyproj.Transformer.from_crs('EPSG:4326', utm_crs, always_xy=True)
    grid = np.zeros(shape, dtype=np.uint8)
    CHUNK = 750_000

    def _proj(coords):
        x, y = to_utm.transform(coords[:, 0], coords[:, 1])
        return np.column_stack([x, y])

    for start in range(0, n, CHUNK):
        meta, tbl = pyogrio.read_arrow(
            path, columns=['source', 'surface_class'],
            skip_features=start, max_features=CHUNK)
        geom_col = meta['geometry_name'] if meta.get('geometry_name') else 'wkb_geometry'
        geom = shapely.from_wkb(tbl.column(geom_col).to_numpy())
        src = tbl.column('source').to_numpy(zero_copy_only=False)
        sc = tbl.column('surface_class').to_numpy(zero_copy_only=False)
        keep = sel(src, sc)
        if not keep.any():
            continue
        geoms = shapely.transform(geom[keep], _proj)
        geoms = [g for g in geoms.tolist() if g is not None and not g.is_empty]
        if geoms:
            rasterize(((g, 1) for g in geoms), out=grid, transform=transform,
                      fill=0, all_touched=True)
        del geom, tbl, geoms
    return grid


def rai_for_country(iso, smod, a, c, e, f):
    cells = pd.read_parquet(cell_path(iso))
    lon = cells['lon'].to_numpy(float)
    lat = cells['lat'].to_numpy(float)
    pop = cells['population_counts'].to_numpy(float)

    rural = rural_mask(lon, lat, smod, a, c, e, f)
    if rural.sum() == 0:
        raise ValueError(f'{iso}: no rural population cells')

    # 以人口像元质心为界，加少量缓冲；选择局部 UTM 投影。
    cx, cy = lon.mean(), lat.mean()
    epsg = utm_epsg(cx, cy)
    utm_crs = f'EPSG:{epsg}'
    to_utm = pyproj.Transformer.from_crs('EPSG:4326', utm_crs, always_xy=True)
    pad = 0.05
    xmin_l, ymin_l = lon.min() - pad, lat.min() - pad
    xmax_l, ymax_l = lon.max() + pad, lat.max() + pad
    xs, ys = to_utm.transform([xmin_l, xmax_l], [ymin_l, ymax_l])
    x0, x1 = sorted(xs)
    y0, y1 = sorted(ys)
    width = max(1, int(np.ceil((x1 - x0) / GRID_M)))
    height = max(1, int(np.ceil((y1 - y0) / GRID_M)))
    transform = from_origin(x0, y1, GRID_M, GRID_M)
    shape = (height, width)

    def sel_arterial_paved(src, sc):
        return (src == 'planet_arterial') & (sc == 'paved')

    def sel_full(src, sc):
        return np.ones(len(src), dtype=bool)

    def sel_full_paved(src, sc):
        return (sc == 'paved')

    grids = {}
    for name, sel in (('arterial_paved', sel_arterial_paved),
                      ('full', sel_full),
                      ('full_paved', sel_full_paved)):
        g = road_grid(iso, sel, utm_crs, transform, shape)
        # 距离变换：到最近道路像元的欧氏距离（米）。
        dist = distance_transform_edt(g == 0, sampling=(GRID_M, GRID_M))
        grids[name] = dist

    # 每个乡村像元在 UTM 网格中的行列，取最近网格像元的距离。
    px, py = to_utm.transform(lon, lat)
    col = ((px - x0) / GRID_M).astype(np.int64)
    row = ((y1 - py) / GRID_M).astype(np.int64)
    ok = (row >= 0) & (row < height) & (col >= 0) & (col < width)

    rural_pop = pop[rural].sum()
    rec = {'iso3': iso, 'rural_pop': float(rural_pop)}
    for name, dist in grids.items():
        within = np.zeros(len(lon), dtype=bool)
        within[ok] = dist[row[ok], col[ok]] <= BUFFER_M
        rec[f'rai_{name}_pct'] = float(100.0 * pop[rural & within].sum() / rural_pop)
    return rec


def fit_ols(x, y):
    x = np.asarray(x, float); y = np.asarray(y, float)
    r = OLS(y, add_constant(x)).fit()
    return dict(slope=float(r.params[1]), intercept=float(r.params[0]),
                se=float(r.bse[1]), t=float(r.tvalues[1]),
                r2=float(r.rsquared), n=len(x))


def loco(x, y):
    x = np.asarray(x, float); y = np.asarray(y, float)
    oof = np.full(len(y), np.nan)
    for i in range(len(y)):
        tr = np.ones(len(y), bool); tr[i] = False
        beta = np.linalg.lstsq(
            np.column_stack([np.ones(tr.sum()), x[tr]]), y[tr], rcond=None)[0]
        oof[~tr] = np.column_stack([np.ones(1), x[~tr]]) @ beta
    m = ~np.isnan(oof)
    ss_res = float(((y[m] - oof[m]) ** 2).sum())
    ss_tot = float(((y[m] - y[m].mean()) ** 2).sum())
    return dict(oof_r2=1 - ss_res / ss_tot,
                mae=float(np.abs(y[m] - oof[m]).mean()),
                dir_acc=float((np.sign(y[m]) == np.sign(oof[m])).mean() * 100))


def block_bootstrap_null(x, y, rng, nboot=NPERM):
    x = np.asarray(x, float); y = np.asarray(y, float)
    r2s = []
    for _ in range(nboot):
        idx = rng.integers(0, len(y), len(y))
        if len(np.unique(x[idx])) < 2:
            continue
        b, a = np.polyfit(x[idx], y[idx], 1)
        pred = a + b * x[idx]
        ss_res = float(((y[idx] - pred) ** 2).sum())
        ss_tot = float(((y[idx] - y[idx].mean()) ** 2).sum())
        if ss_tot > 0:
            r2s.append(1 - ss_res / ss_tot)
    return np.asarray(r2s)


def permute_null(x, y, rng, nperm=NPERM):
    x = np.asarray(x, float); y = np.asarray(y, float)
    r2s = []
    for _ in range(nperm):
        d = rng.permutation(y)
        b, a = np.polyfit(x, d, 1)
        pred = a + b * x
        ss_res = float(((d - pred) ** 2).sum())
        ss_tot = float(((d - d.mean()) ** 2).sum())
        r2s.append(1 - ss_res / ss_tot)
    return np.asarray(r2s)


def run_regressions(df):
    # RAI 域的"主干覆盖"用 RAI_arterial（仅铺装主干路 2 km 覆盖）。
    # 注意：主稿 60 分钟的 `arterial_coverage` 是"主干-only 60 分钟卫生可达份额"，
    # 与 RAI（2 km 近路）是不同构造，二者几乎不相关（r ≈ −0.13），不能混用。
    cov = df['rai_arterial_paved_pct'].to_numpy(float)
    rng = np.random.default_rng(SEED)
    pairs = [
        # 差分形式（内部）：加本地路的"纠正量"对主干覆盖的回归。
        # 与主稿 60 分钟域 (corrected − arterial) ~ arterial 对应。
        ('RAI_full - RAI_arterial (本地路纠正)',
         'rai_full_pct', 'rai_arterial_paved_pct', 'internal_difference_form'),
        # 外部靶子：官方 RAI 与本文两套口径的差值对主干覆盖的回归。
        ('RAI_official - RAI_arterial (外部 vs 主干)',
         'SDG911pct', 'rai_arterial_paved_pct', 'external_vs_arterial'),
        ('RAI_official - RAI_full (外部 vs 含本地路)',
         'SDG911pct', 'rai_full_pct', 'external_vs_full'),
        ('RAI_official - RAI_full_paved (外部 vs 含本地路·仅铺装)',
         'SDG911pct', 'rai_full_paved_pct', 'full_paved_sensitivity'),
    ]
    rows, res = [], {}
    for label, a_col, b_col, role in pairs:
        delta = df[a_col].to_numpy(float) - df[b_col].to_numpy(float)
        o = fit_ols(cov, delta)
        lc = loco(cov, delta)
        bb = block_bootstrap_null(cov, delta, rng)
        pm = permute_null(cov, delta, rng)
        pct_bb = float((bb < o['r2']).mean() * 100)
        pct_pm = float((pm < o['r2']).mean() * 100)
        pear = float(np.corrcoef(cov, delta)[0, 1])
        spear = float(stats.spearmanr(cov, delta).statistic)
        nneg = int((delta < 0).sum())
        res[label] = dict(role=role, ols=o, loco=lc, pearson=pear, spearman=spear,
                          n_negative=nneg,
                          null_block=dict(mean=float(bb.mean()), sd=float(bb.std()),
                                          pct=pct_bb),
                          null_perm=dict(mean=float(pm.mean()), sd=float(pm.std()),
                                         pct=pct_pm))
        rows.append(dict(pair=label, role=role, slope=o['slope'], r2=o['r2'],
                         t=o['t'], pearson=pear, spearman=spear,
                         loco_r2=lc['oof_r2'], loco_dir=lc['dir_acc'],
                         block_pct=pct_bb, perm_pct=pct_pm, n_neg=nneg))
        _log(f'    {label}  (X = RAI_arterial)')
        _log(f'      delta mean {delta.mean():+.2f} pp, median {np.median(delta):+.2f}, '
             f'min {delta.min():+.2f}, max {delta.max():+.2f}, neg {nneg}/30')
        _log(f'      OLS slope {o["slope"]:+.3f} (t {o["t"]:.2f}) R2 {o["r2"]:.3f} '
             f'Pearson {pear:+.3f} Spearman {spear:+.3f}')
        _log(f'      LOCO R2 {lc["oof_r2"]:.3f} dir {lc["dir_acc"]:.1f}% | '
             f'block pct {pct_bb:.1f}% perm pct {pct_pm:.1f}%')
    return rows, res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--countries', nargs='*', default=None)
    a = ap.parse_args()

    rai = pd.read_csv(RAI_CSV, encoding='utf-8-sig')
    rai.columns = [c.strip() for c in rai.columns]
    rai = rai[['ISO3', 'NAME_0', 'SDG911pct']].rename(columns={'ISO3': 'iso3'})

    dec = pd.read_csv(DECOMP, encoding='utf-8-sig')
    cov = dec[dec['service'] == 'health'][['iso3', 'arterial_coverage']]

    iso30 = sorted(cov['iso3'].unique())
    if a.countries:
        iso30 = [i for i in a.countries if i in iso30]

    smod, g_a, g_c, g_e, g_f = load_ghs_smod()
    recs = []
    for iso in iso30:
        cache_f = os.path.join(CACHE, f'{iso}.json')
        if os.path.exists(cache_f):
            recs.append(json.load(open(cache_f, encoding='utf-8')))
            _log(f'{iso}: cached')
            continue
        t0 = time.time()
        try:
            r = rai_for_country(iso, smod, g_a, g_c, g_e, g_f)
            recs.append(r)
            json.dump(r, open(cache_f, 'w', encoding='utf-8'))
            _log(f'{iso}: RAI_arterial {r["rai_arterial_paved_pct"]:.1f}% '
                 f'RAI_full {r["rai_full_pct"]:.1f}% '
                 f'RAI_full_paved {r["rai_full_paved_pct"]:.1f}% '
                 f'({time.time()-t0:.1f}s)')
        except Exception as exc:
            _log(f'{iso}: FAILED {type(exc).__name__} {exc}')

    rdf = pd.DataFrame(recs)
    df = rai.merge(cov, on='iso3', how='inner').merge(rdf, on='iso3', how='inner')
    assert len(df) == len(iso30), f'expected {len(iso30)} rows, got {len(df)}'

    rows, res = run_regressions(df)

    pd.DataFrame(rows).to_csv(os.path.join(OUT, 'e6_rai_external_target.csv'),
                              index=False, encoding='utf-8-sig')
    json.dump(res, open(os.path.join(OUT, 'e6_rai_external_target.json'), 'w'),
              indent=1, ensure_ascii=False)
    df.to_csv(os.path.join(OUT, 'e6_rai_country_values.csv'),
              index=False, encoding='utf-8-sig')
    _log(f'\nwrote {OUT}')

    print('\n' + '=' * 78)
    print('  汇总：外部 RAI 与本文两套口径差分的拟合优度对比')
    print('=' * 78)
    print('  %-44s %8s %9s %9s %9s' % ('差分形式', 'R2', 'LOCO R2', '块自举%', '打乱%'))
    for r in rows:
        print('  %-44s %8.3f %9.3f %9.1f %9.1f'
              % (r['pair'], r['r2'], r['loco_r2'], r['block_pct'], r['perm_pct']))


if __name__ == '__main__':
    main()
