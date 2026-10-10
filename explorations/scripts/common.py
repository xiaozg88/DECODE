import os
import numpy as np
import pandas as pd
import geopandas as gpd

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "explorations", "output")
os.makedirs(OUT, exist_ok=True)

# 30-country sample, in the order used by the paper expansion
COUNTRIES = ["BGD", "COL", "EGY", "ETH", "GEO", "GHA", "GTM", "HND", "IDN", "IND",
             "JOR", "KEN", "KGZ", "KHM", "LKA", "MEX", "MLI", "MOZ", "NGA", "NPL",
             "PAK", "PER", "PHL", "PNG", "RWA", "SEN", "TUR", "TZA", "VNM", "ZMB"]

# noded segment file stem differs only for Mozambique
NODED_STEM = {"MOZ": "mozambique"}

def noded_stem(iso):
    return NODED_STEM.get(iso, iso.lower())

def cell_path(iso):
    return os.path.join(ROOT, "output", "experiments", "cell_travel_times", f"{iso}.parquet")

def seg_path(iso):
    return os.path.join(ROOT, "data", "external", "hdx", "countries", iso, "local_roads",
                        f"{noded_stem(iso)}_noded_segments.gpkg")

def worldpop_path(iso):
    return os.path.join(ROOT, "data", "external", "hdx", "countries", iso, f"{iso.lower()}_pd_2020_1km.tif")

def load_cells(iso):
    return pd.read_parquet(cell_path(iso))

def load_segments(iso):
    return gpd.read_file(seg_path(iso))

GDL_GEOM = os.path.join(ROOT, "data", "external", "socioeconomic", "gdl", "gdl_regions_v6_7.geojson")
SHDI_LONG = os.path.join(ROOT, "data", "external", "socioeconomic", "gdl", "shdi_30countries_long.csv")

