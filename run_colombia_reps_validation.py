# -*- coding: utf-8 -*-
"""Real-world facility-completeness validation: Colombia REPS health registry.

The Colombian REPS (Registro Especial de Prestadores de Servicios de Salud) is an
official Ministry of Health provider registry, independent of OSM.  We geocode its
``x``/``y`` columns, snap each provider to the corrected noded network (<=1 km, as in
the main model) and recompute 60-minute accessibility with OSM hospital/clinic only
versus the OSM + REPS union.  This is the same protocol used for the ETH/BGD/MOZ
registry corrections and for the S3 independent-registry cases.

Note: the bundled COL SEDES education CSV and the KEN MFL / PAK DHIS files lack usable
coordinates, so only the Colombian health registry is usable offline.

Usage:
  python run_colombia_reps_validation.py
"""
from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

import run_experiment_29_corrected_countries as canon
import run_facility_registry_bottleneck as frb

ROOT = Path(__file__).resolve().parent
REPS = ROOT / 'data/external/facility_validation/COL_REPS_sedes_geo.xlsx'
OUT = ROOT / 'output/experiments/colombia_reps_validation'


def load_reps() -> gpd.GeoDataFrame:
    d = pd.read_excel(REPS)
    x = pd.to_numeric(d['x'], errors='coerce')
    y = pd.to_numeric(d['y'], errors='coerce')
    ok = x.notna() & y.notna() & (x.abs() <= 180) & (y.abs() <= 90)
    d = d[ok].copy()
    d['lon'] = x[ok].to_numpy()
    d['lat'] = y[ok].to_numpy()
    g = gpd.GeoDataFrame(d, geometry=gpd.points_from_xy(d.lon, d.lat), crs=4326)
    return g[g.geometry.notna() & ~g.geometry.is_empty]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    reg = load_reps()
    print(f'COL REPS health: {len(reg)} facilities with valid coordinates')
    print('  nivel distribution:', reg['nivel'].astype(str).value_counts().to_dict())
    row = frb.run_case('COL', 'health', reg)
    df = pd.DataFrame([row])
    df.to_csv(OUT / 'colombia_reps_health.csv', index=False, encoding='utf-8-sig')
    pd.set_option('display.width', 220)
    print(df[['iso3', 'service', 'osm_records', 'registry_records', 'osm_source_nodes',
              'union_source_nodes', 'registry_snap_within_1km_pct',
              'share_60min_osm_counts', 'share_60min_union_counts',
              'registry_gain_60min_pp']].round(2).to_string(index=False))
    print(f'wrote {OUT / "colombia_reps_health.csv"}')


if __name__ == '__main__':
    main()
