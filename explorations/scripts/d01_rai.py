import os
import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
from rasterio.features import rasterize
from scipy import ndimage

from common import ROOT, OUT, COUNTRIES, worldpop_path, load_cells


ISO2 = {"BGD": "BD", "COL": "CO", "EGY": "EG", "ETH": "ET", "GEO": "GE",
        "GHA": "GH", "GTM": "GT", "HND": "HN", "IDN": "ID", "IND": "IN",
        "JOR": "JO", "KEN": "KE", "KGZ": "KG", "KHM": "KH", "LKA": "LK",
        "MEX": "MX", "MLI": "ML", "MOZ": "MZ", "NGA": "NG", "NPL": "NP",
        "PAK": "PK", "PER": "PE", "PHL": "PH", "PNG": "PG", "RWA": "RW",
        "SEN": "SN", "TUR": "TR", "TZA": "TZ", "VNM": "VN", "ZMB": "ZM"}


def planet_path(iso):
    return os.path.join(ROOT, "data", "external", "hdx", "roads",
                        f"heigit_{ISO2[iso]}_planet_roadsurface_lines.gpkg")


def _clean_pop(pop, nodata):
    pop = pop.astype("float64")
    pop = np.where(pop == nodata, 0.0, pop)
    pop = np.where(pop < 0, 0.0, pop)
    return pop


def _raster_lines(geoms, transform, shape):
    return rasterize(((g, 1) for g in geoms), out_shape=shape, transform=transform,
                     fill=0, all_touched=True).astype(np.uint8)


def _rai(pop, mask, tot):
    if tot == 0:
        return np.nan
    dil = ndimage.binary_dilation(mask > 0, iterations=2).astype(np.uint8)
    return pop[dil > 0].sum() / tot


def run():
    rows = []
    for iso in COUNTRIES:
        rec = {"iso3": iso}
        try:
            cells = load_cells(iso)
            pop_c = cells["population_counts"].to_numpy(dtype="float64")
            h = cells["travel_health_min"].to_numpy()
            e = cells["travel_education_min"].to_numpy()
            tot_cells = pop_c.sum()
            rec["pop_cells"] = tot_cells
            rec["share_h60"] = pop_c[h <= 60].sum() / tot_cells if tot_cells else np.nan
            rec["share_e60"] = pop_c[e <= 60].sum() / tot_cells if tot_cells else np.nan

            planet = gpd.read_file(planet_path(iso))
            rec["n_planet_lines"] = len(planet)
            paved = planet[planet["DL_road_class_2024"] == "paved"]
            rec["n_planet_paved"] = len(paved)

            with rasterio.open(worldpop_path(iso)) as ds:
                pop = _clean_pop(ds.read(1), ds.nodata)
                transform, shape = ds.transform, ds.shape
            tot_tif = pop.sum()
            rec["pop_tif"] = tot_tif

            geoms_paved = [g for g in paved.geometry if g is not None and not g.is_empty]
            geoms_all = [g for g in planet.geometry if g is not None and not g.is_empty]
            rec["rai_planet_paved_2km"] = _rai(pop, _raster_lines(geoms_paved, transform, shape), tot_tif) if geoms_paved else 0.0
            rec["rai_planet_all_2km"] = _rai(pop, _raster_lines(geoms_all, transform, shape), tot_tif) if geoms_all else np.nan
        except Exception as exc:
            rec["error"] = repr(exc)[:200]
        rows.append(rec)
        print(iso, "done", {k: rec.get(k) for k in ["n_planet_lines", "n_planet_paved", "rai_planet_paved_2km", "rai_planet_all_2km"]}, flush=True)

    df = pd.DataFrame(rows)
    out = os.path.join(OUT, "d01_rai.csv")
    df.to_csv(out, index=False)
    print("saved", out)
    print(df[["iso3", "rai_planet_paved_2km", "rai_planet_all_2km", "share_h60", "share_e60"]].round(4).to_string())


if __name__ == "__main__":
    run()
