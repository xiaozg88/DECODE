# -*- coding: utf-8 -*-
"""Experiment A (advisory, simplified): three-way口径 sensitivity for 5 extra countries.

For each out-of-sample country, compute the 60-min health share under:
  baseline   mercator length, hospital+clinic, 1km cell
  length     geodesic length (WGS84), hospital+clinic, 1km
  facility   mercator, hospital-only, 1km
  aggregation mercator, hospital+clinic, 0.05deg pop-weighted aggregation
and report the within-country spread (max - min).
"""
from __future__ import annotations

import sys
from pathlib import Path

import geopandas as gpd
import networkx as nx
import numpy as np
import pandas as pd
import pyogrio
import rasterio
from pyproj import Geod, Transformer
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import prototype_multicountry_access as base  # noqa: E402

OUT = ROOT / "explorations" / "output"
EXTRA = [("FJI", "FJ"), ("TLS", "TL"), ("BTN", "BT"), ("ARM", "AM"), ("NAM", "NA")]
GEOD = Geod(ellps="WGS84")


def load_roads(iso2: str):
    p = ROOT / "data" / "external" / "hdx" / "roads" / f"heigit_{iso2}_planet_roadsurface_lines.gpkg"
    r = gpd.read_file(p)
    if r.crs is None:
        r = r.set_crs(4326)
    return r.to_crs(4326)


def speed(row):
    s = base.BASE_SPEED.get(str(row.get("osm_tags_highway", "")), 35) * \
        base.SURFACE_MULT.get(str(row.get("DL_road_class_2024", "unknown")), 0.75)
    try:
        s *= base.WIDTH_MULT.get(float(row.get("rw_class", np.nan)), 0.8)
    except (TypeError, ValueError):
        s *= 0.8
    return s


def build_graph(roads, length_mode="mercator"):
    g = nx.MultiGraph()
    ids = {}
    def node(xy):
        k = (round(float(xy[0]), 7), round(float(xy[1]), 7))
        if k not in ids:
            ids[k] = len(ids)
            g.add_node(ids[k], x=k[0], y=k[1])
        return ids[k]
    merc = roads.to_crs(3857).geometry.length.to_numpy()
    if length_mode == "geodesic":
        lens = np.array([GEOD.geometry_length(geom) if geom is not None else 0.0 for geom in roads.geometry])
    else:
        lens = merc
    for i, r in roads.iterrows():
        geom = r.geometry
        if geom is None or geom.is_empty or geom.geom_type not in {"LineString", "MultiLineString"}:
            continue
        cs = list(geom.coords)
        if len(cs) < 2:
            continue
        a, b = node(cs[0]), node(cs[-1])
        if a == b:
            continue
        tt = float(lens[i]) / 1000.0 / float(speed(r)) * 60.0
        g.add_edge(a, b, key=int(i), travel_time_min=tt)
    return g


def load_pop(iso3: str):
    p = ROOT / "data" / "external" / "hdx" / "countries" / iso3 / f"{iso3.lower()}_pd_2020_1km.tif"
    with rasterio.open(p) as src:
        a = src.read(1).astype("float32")
        tr = src.transform
        nodata = src.nodata
    valid = np.isfinite(a) & (a != nodata) & (a > 0)
    rows, cols = np.where(valid)
    vals = a[valid]
    lon = tr.c + (cols + .5) * tr.a
    lat = tr.f + (rows + .5) * tr.e
    xy = np.column_stack([lon, lat])
    xy3857 = np.column_stack(base.TRANSFORMER.transform(xy[:, 0], xy[:, 1]))
    return xy, xy3857, vals


def load_fac(iso3: str, kind: str):
    d = ROOT / "data" / "external" / "hdx" / "countries" / iso3
    cand = list((d / f"hotosm_{iso3.lower()}_{kind}_facilities_osm_gpkg").rglob("*.gpkg"))
    if not cand:
        raise FileNotFoundError(iso3, kind)
    g = gpd.read_file(cand[0], layer=pyogrio.list_layers(cand[0])[0, 0])
    if g.crs is None:
        g = g.set_crs(4326)
    return g.to_crs(4326)


def shares(g, src_nodes, cells, pop, aggr=None, xy=None):
    nodes = np.array(list(g))
    ll = np.array([(g.nodes[n]["x"], g.nodes[n]["y"]) for n in nodes])
    xy3857_nodes = np.column_stack(base.TRANSFORMER.transform(ll[:, 0], ll[:, 1]))
    tree = cKDTree(xy3857_nodes)
    _, idx = tree.query(xy if xy is None else None)
    # recompute: query cell coords
    return _shares(g, src_nodes, cells, pop, tree, nodes, idx)


def _shares(g, src_nodes, cells, pop, tree, nodes, idx):
    d = nx.multi_source_dijkstra_path_length(g, src_nodes, weight="travel_time_min") if src_nodes else {}
    v = np.array([d.get(int(n), np.nan) for n in cells])
    valid = np.isfinite(v)
    return 100 * pop[valid & (v <= 60)].sum() / pop.sum()


def compute(iso3, iso2):
    roads = load_roads(iso2)
    xy, xy3857, pop = load_pop(iso3)

    def run(length_mode, facility_mode, aggr):
        g = build_graph(roads, length_mode)
        nodes = np.array(list(g))
        ll = np.array([(g.nodes[n]["x"], g.nodes[n]["y"]) for n in nodes])
        tree = cKDTree(np.column_stack(base.TRANSFORMER.transform(ll[:, 0], ll[:, 1])))
        _, idx = tree.query(xy3857)
        cells = nodes[idx]
        fac = load_fac(iso3, "health")
        am = fac.amenity.astype(str)
        if facility_mode == "hospital_only":
            fac = fac[am == "hospital"]
        else:
            fac = fac[am.isin(["hospital", "clinic"])]
        pts = fac.geometry.representative_point().to_crs(3857)
        facxy = np.column_stack([pts.geometry.x, pts.geometry.y])
        dfac, ifac = tree.query(facxy)
        src = list(map(int, set(nodes[ifac[dfac <= 1000]])))
        d = nx.multi_source_dijkstra_path_length(g, src, weight="travel_time_min") if src else {}
        v = np.array([d.get(int(n), np.nan) for n in cells])
        valid = np.isfinite(v)
        if aggr == "1km":
            return 100 * pop[valid & (v <= 60)].sum() / pop.sum()
        # aggregate to 0.05deg pop-weighted mean
        glon = np.floor(xy[:, 0] / 0.05) * 0.05 + 0.025
        glat = np.floor(xy[:, 1] / 0.05) * 0.05 + 0.025
        df = pd.DataFrame({"glon": glon, "glat": glat, "pop": pop, "tt": np.where(valid, v, np.nan)})
        gmean = df.groupby(["glon", "glat"]).apply(lambda g: np.average(g["tt"], weights=g["pop"]) if g["tt"].notna().any() else np.nan)
        gpop = df.groupby(["glon", "glat"])["pop"].sum()
        return 100 * gpop[gmean.notna() & (gmean <= 60)].sum() / pop.sum()

    return {
        "iso3": iso3,
        "baseline": run("mercator", "hospital_clinic", "1km"),
        "length": run("geodesic", "hospital_clinic", "1km"),
        "facility": run("mercator", "hospital_only", "1km"),
        "aggregation": run("mercator", "hospital_clinic", "0.05"),
    }


def main():
    rows = []
    for iso3, iso2 in EXTRA:
        try:
            r = compute(iso3, iso2)
            vals = [r[k] for k in ("baseline", "length", "facility", "aggregation")]
            r["spread_pp"] = max(vals) - min(vals)
            rows.append(r)
            print(iso3, {k: round(v, 2) for k, v in r.items() if k not in ("iso3",)}, flush=True)
        except Exception as e:
            print(iso3, "FAILED", type(e).__name__, str(e)[:120], flush=True)
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "d17_extra_country_sensitivity.csv", index=False, encoding="utf-8-sig")
    if len(df):
        print("\n口径极差 (pp):", [round(x, 1) for x in df["spread_pp"]])
        print("均值 %.1f 范围 %.1f–%.1f" % (df["spread_pp"].mean(), df["spread_pp"].min(), df["spread_pp"].max()))
        print("saved", OUT / "d17_extra_country_sensitivity.csv")


if __name__ == "__main__":
    main()
