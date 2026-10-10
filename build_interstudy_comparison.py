# -*- coding: utf-8 -*-
"""Review item R6: make the motivating claim ("estimates for the same country
differ by tens of percentage points") verifiable with our own data.

For all 30 sample countries we compute the population-weighted share of people
within 60 minutes under four defensible measurement conventions:

  1. Weiss/Nelson 2015 travel time to the nearest urban area of >=50k people
     (``travel_time_to_cities_11.tif``, CC BY 4.0; Weiss et al. 2018, Nature)
  2. MAP 2020 motorised travel time to the nearest healthcare facility
  3. this model, Planet arterial layer only ("arterial-only")
  4. this model, Planet + OSM local roads, published corrected convention

WorldPop 2020 1 km cells are used as the common population basis. The vintage
mismatch (2015 cities layer vs 2020 population) is disclosed in the paper.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
from rasterio.windows import from_bounds

import prototype_multicountry_access as base

ROOT = Path(__file__).resolve().parent
WEISS = ROOT / 'data/external/accessibility_products/weiss_2015/travel_time_to_cities_11.tif'
OUT = ROOT / 'output/experiments/interstudy_comparison'
COUNTRY_DIR = ROOT / 'data/external/hdx/countries'
COUNTRIES = sorted(p.name for p in COUNTRY_DIR.iterdir()
                   if p.is_dir() and list(p.glob('*_pd_2020_1km.tif')))
NAME = {}
_main = ROOT / 'output/experiments/corrected_main/corrected_main_access_30countries.csv'
if _main.exists():
    _m = pd.read_csv(_main)[['iso3', 'country']].drop_duplicates()
    NAME = dict(zip(_m.iso3, _m.country))
else:  # pragma: no cover - only before the corrected table exists
    NAME = dict(base.COUNTRIES)


def country_name(iso):
    return NAME.get(iso, iso)


def weiss_shares(iso: str, lon, lat, pop):
    with rasterio.open(WEISS) as src:
        w = from_bounds(lon.min() - 0.05, lat.min() - 0.05, lon.max() + 0.05, lat.max() + 0.05,
                        transform=src.transform)
        arr = src.read(1, window=w, boundless=True, fill_value=65535)
        tr = src.window_transform(w)
    col = ((lon - tr.c) / tr.a).astype(int)
    row = ((lat - tr.f) / tr.e).astype(int)
    ok = (row >= 0) & (row < arr.shape[0]) & (col >= 0) & (col < arr.shape[1])
    vals = np.full(len(lon), np.nan)
    vals[ok] = arr[row[ok], col[ok]].astype(float)
    vals[(vals == 65535)] = np.nan
    valid = np.isfinite(vals)
    out = {'weiss_cells': int(valid.sum()),
           'weiss_pop_covered_pct': float(100 * pop[valid].sum() / pop.sum())}
    for t in (30, 60, 120):
        out[f'weiss_{t}min_pct'] = float(100 * pop[valid & (vals <= t)].sum() / pop.sum())
    out['weiss_median_min'] = float(np.median(vals[valid])) if valid.any() else np.nan
    return out


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for iso in COUNTRIES:
        try:
            xy, xy3857, pop = base.load_population(iso)
            r = {'iso3': iso, 'country': country_name(iso), 'population_millions':
                 float(pop.sum() / 1e6)}
            r.update(weiss_shares(iso, xy[:, 0], xy[:, 1], pop))
            rows.append(r)
            print(f'{iso}: weiss 60-min share {r["weiss_60min_pct"]:.1f}% '
                  f'(cells {r["weiss_cells"]:,})', flush=True)
        except Exception as exc:
            print(f'{iso}: FAILED {type(exc).__name__} {exc}', flush=True)
    w = pd.DataFrame(rows)
    w.to_csv(OUT / 'weiss_60min_by_country.csv', index=False, encoding='utf-8-sig')

    main_tbl = pd.read_csv(ROOT / 'output/experiments/corrected_main/'
                                 'corrected_main_access_30countries.csv')
    map_tbl = pd.read_csv(ROOT / 'output/experiments/benchmark_validation/'
                                'map_health_travel_time_vs_model.csv')
    out = []
    for iso in COUNTRIES:
        h = main_tbl[(main_tbl.iso3 == iso) & (main_tbl.service == 'health')]
        m = map_tbl[map_tbl.iso3 == iso]
        ww = w[w.iso3 == iso]
        if h.empty or m.empty or ww.empty:
            continue
        vals = {
            'weiss_2015_cities': float(ww.weiss_60min_pct.iloc[0]),
            'map_2020_health': float(m.benchmark_share_60min_pct.iloc[0]),
            'this_arterial_only': float(h.arterial_60min_pct.iloc[0]),
            'this_corrected': float(h.share_60min_pct_counts_geodesic_none.iloc[0]),
        }
        spread = max(vals.values()) - min(vals.values())
        out.append({'iso3': iso, 'country': country_name(iso), **vals,
                    'max_minus_min_pp': spread,
                    'spread_excluding_arterial': max(vals['weiss_2015_cities'],
                                                     vals['map_2020_health'],
                                                     vals['this_corrected'])
                    - min(vals['weiss_2015_cities'], vals['map_2020_health'],
                          vals['this_corrected'])})
    df = pd.DataFrame(out).sort_values('max_minus_min_pp', ascending=False)
    df.to_csv(OUT / 'interstudy_60min_comparison.csv', index=False, encoding='utf-8-sig')
    summ = {
        'countries': len(df),
        'median_spread_all_four_pp': float(df.max_minus_min_pp.median()),
        'max_spread_all_four_pp': float(df.max_minus_min_pp.max()),
        'n_countries_spread_gt_20pp': int((df.max_minus_min_pp > 20).sum()),
        'n_countries_spread_gt_30pp': int((df.max_minus_min_pp > 30).sum()),
        'median_spread_three_products_pp': float(df.spread_excluding_arterial.median()),
        'max_spread_three_products_pp': float(df.spread_excluding_arterial.max()),
        'n_three_products_gt_20pp': int((df.spread_excluding_arterial > 20).sum()),
    }
    pd.Series(summ).to_csv(OUT / 'interstudy_summary.csv', encoding='utf-8-sig')
    print(summ)
    print(df[['iso3', 'weiss_2015_cities', 'map_2020_health', 'this_arterial_only',
              'this_corrected', 'max_minus_min_pp']].round(1).to_string(index=False))


if __name__ == '__main__':
    main()
