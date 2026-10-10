import os
import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
from rasterio.features import rasterize
from scipy import ndimage
from pyproj import Transformer

from common import ROOT, OUT, COUNTRIES, worldpop_path

ISO2 = {"BGD": "BD", "COL": "CO", "EGY": "EG", "ETH": "ET", "GEO": "GE",
        "GHA": "GH", "GTM": "GT", "HND": "HN", "IDN": "ID", "IND": "IN",
        "JOR": "JO", "KEN": "KE", "KGZ": "KG", "KHM": "KH", "LKA": "LK",
        "MEX": "MX", "MLI": "ML", "MOZ": "MZ", "NGA": "NG", "NPL": "NP",
        "PAK": "PK", "PER": "PE", "PHL": "PH", "PNG": "PG", "RWA": "RW",
        "SEN": "SN", "TUR": "TR", "TZA": "TZ", "VNM": "VN", "ZMB": "ZM"}

GHS = os.path.join(ROOT, "data", "external", "ghs", "GHS_SMOD_E2020_GLOBE_R2023A_54009_1000_V1_0.tif")


def planet_path(iso):
    return os.path.join(ROOT, "data", "external", "hdx", "roads",
                        f"heigit_{ISO2[iso]}_planet_roadsurface_lines.gpkg")


def _raster_lines(geoms, transform, shape):
    return rasterize(((g, 1) for g in geoms), out_shape=shape, transform=transform,
                     fill=0, all_touched=True).astype(np.uint8)


def run():
    # load GHS-SMOD once
    with rasterio.open(GHS) as gds:
        smod = gds.read(1)
        gtr = gds.transform  # a,c,e,f used for row/col
    a, c, e, f = gtr.a, gtr.c, gtr.e, gtr.f
    transformer = Transformer.from_crs("EPSG:4326", "ESRI:54009", always_xy=True)

    rows = []
    for iso in COUNTRIES:
        rec = {"iso3": iso}
        try:
            cells = pd.read_parquet(os.path.join(ROOT, "output", "experiments",
                                                 "cell_travel_times", f"{iso}.parquet"))
            lon = cells["lon"].to_numpy()
            lat = cells["lat"].to_numpy()
            pop = cells["population_counts"].to_numpy(dtype="float64")

            # rural mask via GHS-SMOD point sampling
            x, y = transformer.transform(lon, lat)
            gcol = ((x - c) / a).astype(int)
            grow = ((y - f) / e).astype(int)
            valid = (grow >= 0) & (grow < smod.shape[0]) & (gcol >= 0) & (gcol < smod.shape[1])
            smod_val = np.full(len(lon), -1, dtype=np.int16)
            smod_val[valid] = smod[grow[valid], gcol[valid]]
            rural = (smod_val >= 21) & (smod_val <= 23)  # village / low-density / very-low-density rural
            rec["rural_pop"] = pop[rural].sum()

            planet = gpd.read_file(planet_path(iso))
            paved = planet[planet["DL_road_class_2024"] == "paved"]
            with rasterio.open(worldpop_path(iso)) as wds:
                wtr, wshape = wds.transform, wds.shape
            # map cells to WorldPop pixel indices
            col = ((lon - wtr.c) / wtr.a).astype(int)
            row = ((lat - wtr.f) / wtr.e).astype(int)
            ok = (row >= 0) & (row < wshape[0]) & (col >= 0) & (col < wshape[1])

            def in_buffer(geoms):
                m = _raster_lines(geoms, wtr, wshape)
                m = ndimage.binary_dilation(m > 0, iterations=2).astype(np.uint8)
                res = np.zeros(len(lon), dtype=bool)
                res[ok] = m[row[ok], col[ok]] > 0
                return res

            inpaved = in_buffer([g for g in paved.geometry if g is not None and not g.is_empty])
            inall = in_buffer([g for g in planet.geometry if g is not None and not g.is_empty])
            rpop = rec["rural_pop"]
            rec["rai_paved_rural"] = pop[rural & inpaved].sum() / rpop if rpop else np.nan
            rec["rai_all_rural"] = pop[rural & inall].sum() / rpop if rpop else np.nan
            rec["surface_gap_rural_pp"] = (rec["rai_all_rural"] - rec["rai_paved_rural"]) * 100
            rec["misclassified_rural_pop"] = (rec["rai_all_rural"] - rec["rai_paved_rural"]) * rpop
            rec["misclassified_rural_pop_millions"] = rec["misclassified_rural_pop"] / 1e6
        except Exception as exc:
            rec["error"] = repr(exc)[:200]
        rows.append(rec)
        print(iso, "done", {k: (round(rec[k], 3) if isinstance(rec.get(k), float) else rec.get(k))
                            for k in ["rural_pop", "rai_paved_rural", "rai_all_rural", "surface_gap_rural_pp", "misclassified_rural_pop_millions"]}, flush=True)

    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(OUT, "d08_sdg_rai_rural.csv"), index=False)
    tot_mis = df["misclassified_rural_pop"].sum()
    print("=" * 60)
    print("total misclassified rural population (millions):", round(tot_mis / 1e6, 1))
    print("max surface gap (rural, pp):", df["surface_gap_rural_pp"].max().round(1), "at", df.loc[df["surface_gap_rural_pp"].idxmax(), "iso3"])
    print("top 6 by misclassified rural pop (millions):")
    print(df[["iso3", "rural_pop", "surface_gap_rural_pp", "misclassified_rural_pop_millions"]].sort_values("misclassified_rural_pop_millions", ascending=False).head(6).round(2).to_string(index=False))


if __name__ == "__main__":
    run()
