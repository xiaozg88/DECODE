# -*- coding: utf-8 -*-
"""
Multi-country prototype: road-quality-adjusted access under baseline, no-unpaved, and hazard scenarios
======================================================================================================
This script generalizes the Madagascar prototype to seven high-risk countries.

For each country it:
1. Loads the HDX Planet road surface / width / passability GPKG.
2. Builds a routable graph from road endpoints.
3. Loads OSM health and education facilities.
4. Loads WorldPop 2020 1 km population density.
5. Loads one recent flood footprint.
6. Computes population-weighted travel time to the nearest hospital/clinic and school under:
   - baseline
   - no_unpaved
   - hazard
7. Writes:
   - country-level summary CSV
   - 0.05-degree access surface GeoJSON
   - health baseline and disruption-delta maps

Countries:
- Pakistan
- Mozambique
- Bangladesh
- Ethiopia
- Kenya
- Philippines
- Colombia

Notes
-----
- Road graph uses arterial roads only.
- Hazard rule:
  * roads whose representative point falls inside the hazard footprint are removed if unpaved
  * affected paved or unknown roads are slowed by a factor of two
- Absolute travel times are conservative because local roads are not included.
"""
from __future__ import annotations

import argparse
import math
import time
import warnings
from pathlib import Path

import geopandas as gpd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd
import pyogrio
import rasterio
from pyproj import Geod, Transformer
from scipy.spatial import cKDTree

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parent
ROAD_DIR = ROOT / "data/external/hdx/roads"
COUNTRY_DIR = ROOT / "data/external/hdx/countries"
HAZARD_DIR = ROOT / "data/external/hdx/hazards"
WORLD = ROOT / "data/ne_110m_admin_0_countries.zip"
OUT = ROOT / "output/prototype/multicountry"

COUNTRIES = {
    "PAK": "Pakistan",
    "MOZ": "Mozambique",
    "BGD": "Bangladesh",
    "ETH": "Ethiopia",
    "KEN": "Kenya",
    "PHL": "Philippines",
    "COL": "Colombia",
}

SPLIT_EXPORTS = {"PAK", "PHL"}

ROAD_FILES = {
    "PAK": "heigit_PK_planet_roadsurface_lines.gpkg",
    "MOZ": "heigit_MZ_planet_roadsurface_lines.gpkg",
    "BGD": "heigit_BD_planet_roadsurface_lines.gpkg",
    "ETH": "heigit_ET_planet_roadsurface_lines.gpkg",
    "KEN": "heigit_KE_planet_roadsurface_lines.gpkg",
    "PHL": "heigit_PH_planet_roadsurface_lines.gpkg",
    "COL": "heigit_CO_planet_roadsurface_lines.gpkg",
}

HAZARD_FILES = {
    "PAK": HAZARD_DIR / "PAK/extracted/FL-20250911-PAK-00.gpkg",
    "MOZ": HAZARD_DIR / "MOZ/extracted/FL-20250318-MOZ-00.gpkg",
    "BGD": HAZARD_DIR / "BGD/extracted/ST20180615_Sylhet_Flood_Water.shp",
    "ETH": HAZARD_DIR / "ETH/extracted/FL20230327SOM_SHP/S2_20230328_WaterExtent_ShabelleDistrict_ETH.shp",
    "KEN": HAZARD_DIR / "KEN/extracted/FL20180508KEN_shp/ST_20180508_WaterExtent_CumulativeKenya.shp",
    "PHL": HAZARD_DIR / "PHL/extracted/Flood-Impact_RCM1-20260712.shp",
    "COL": HAZARD_DIR / "COL/extracted/FL20241112COL_SHP/TDX_20241117_WaterExtent_BojayaMunicipality.shp",
}

BASE_SPEED = {
    "motorway": 100,
    "trunk": 80,
    "primary": 70,
    "primary_link": 45,
    "secondary": 55,
    "secondary_link": 35,
    "tertiary": 40,
    "tertiary_link": 25,
    "residential": 30,
    "unclassified": 30,
}

SURFACE_MULT = {
    "paved": 1.00,
    "unpaved": 0.55,
    "unknown": 0.75,
}

WIDTH_MULT = {
    1: 0.65,
    2: 0.80,
    3: 1.00,
}

GEOD = Geod(ellps="WGS84")
TRANSFORMER = Transformer.from_crs(4326, 3857, always_xy=True)


def log(message: str):
    print(message, flush=True)


def load_facilities(iso: str, kind: str) -> gpd.GeoDataFrame:
    """Load OSM health or education facilities for one country."""
    parts = []
    if iso in SPLIT_EXPORTS:
        for geom in ["points", "polygons"]:
            pattern = COUNTRY_DIR / iso / f"hotosm_{iso.lower()}_{kind}_facilities_{geom}_gpkg"
            files = sorted(pattern.rglob("*.gpkg"))
            if not files:
                raise FileNotFoundError(f"No GPKG found for {iso} {kind} {geom}: {pattern}")
            for file in files:
                layers = pyogrio.list_layers(file)
                gdf = gpd.read_file(file, layer=layers[0, 0])
                parts.append(gdf)
    else:
        pattern = COUNTRY_DIR / iso / f"hotosm_{iso.lower()}_{kind}_facilities_osm_gpkg"
        files = sorted(pattern.rglob("*.gpkg"))
        if not files:
            raise FileNotFoundError(f"No GPKG found for {iso} {kind}: {pattern}")
        for file in files:
            layers = pyogrio.list_layers(file)
            gdf = gpd.read_file(file, layer=layers[0, 0])
            parts.append(gdf)

    if not parts:
        raise ValueError(f"No facility parts for {iso} {kind}")

    out = gpd.GeoDataFrame(pd.concat(parts, ignore_index=True), crs=parts[0].crs)
    return out.to_crs(4326)


def load_hazard(iso: str) -> gpd.GeoDataFrame:
    """Load one recent flood footprint for a country."""
    path = HAZARD_FILES[iso]
    if not path.exists():
        raise FileNotFoundError(path)
    layers = pyogrio.list_layers(path)
    gdf = gpd.read_file(path, layer=layers[0, 0])

    # Philippines flood-impact layer contains multiple classes; keep the general flooded-area class.
    if iso == "PHL" and "class_id" in gdf.columns:
        gdf = gdf[gdf["class_id"].eq(1)].copy()

    # Colombia has two municipality water-extent layers; combine both if available.
    if iso == "COL":
        second = path.with_name(path.name.replace("BojayaMunicipality", "RiosucioMunicipality"))
        if second.exists():
            layers2 = pyogrio.list_layers(second)
            gdf2 = gpd.read_file(second, layer=layers2[0, 0])
            gdf = gpd.GeoDataFrame(pd.concat([gdf, gdf2], ignore_index=True), crs=gdf.crs)

    if gdf.crs is None:
        gdf = gdf.set_crs(4326)
    return gdf.to_crs(4326)


def build_graphs(roads: gpd.GeoDataFrame, hazard: gpd.GeoDataFrame):
    """Build baseline, no-unpaved, and hazard graphs from road lines."""
    roads = roads.reset_index(drop=True).copy()
    roads["surface_2024"] = roads["DL_road_class_2024"]
    roads["width_class"] = roads["rw_class"]

    def speed(row):
        base = BASE_SPEED.get(str(row.get("osm_tags_highway", "")), 35)
        surface = SURFACE_MULT.get(str(row.get("surface_2024", "unknown")), 0.75)
        try:
            width = WIDTH_MULT.get(float(row.get("width_class", np.nan)), 0.80)
        except (TypeError, ValueError):
            width = 0.80
        return base * surface * width

    roads["speed_kmh"] = roads.apply(speed, axis=1)
    roads["length_m"] = roads.to_crs(3857).geometry.length
    roads["travel_time_min"] = (roads["length_m"] / 1000.0) / roads["speed_kmh"] * 60.0

    # Spatial join to identify roads affected by the hazard footprint.
    # Prefilter by the hazard bounding box to avoid expensive intersection
    # tests against every road in large countries.
    minx, miny, maxx, maxy = hazard.total_bounds
    candidates = roads.cx[minx:maxx, miny:maxy]
    road_midpoints = candidates.geometry.representative_point()
    midpoint_gdf = gpd.GeoDataFrame(geometry=road_midpoints, crs=candidates.crs)
    hazard_join = gpd.sjoin(midpoint_gdf, hazard, how="left", predicate="within")
    hazard_indices = set(hazard_join.index[hazard_join["index_right"].notna()].astype(int))
    roads["hazard_intersect"] = roads.index.isin(hazard_indices)

    G = nx.MultiGraph()
    node_xy = {}
    node_id = 0

    for idx, row in roads.iterrows():
        geom = row.geometry
        if geom is None or geom.is_empty:
            continue
        coords = list(geom.coords)
        if len(coords) < 2:
            continue
        endpoints = [coords[0], coords[-1]]
        ids = []
        for xy in endpoints:
            xy = (round(float(xy[0]), 8), round(float(xy[1]), 8))
            if xy not in node_xy:
                node_xy[xy] = node_id
                G.add_node(node_id, x=xy[0], y=xy[1])
                node_id += 1
            ids.append(node_xy[xy])
        if ids[0] == ids[1]:
            continue
        G.add_edge(
            ids[0],
            ids[1],
            key=int(idx),
            road_index=int(idx),
            length_m=float(row["length_m"]),
            speed_kmh=float(row["speed_kmh"]),
            travel_time_min=float(row["travel_time_min"]),
            highway=str(row.get("osm_tags_highway", "")),
            surface=str(row.get("surface_2024", "unknown")),
            width_class=row.get("width_class"),
        )

    H = nx.MultiGraph()
    H.add_nodes_from(G.nodes(data=True))
    for u, v, k, data in G.edges(keys=True, data=True):
        if data.get("surface", "unknown") != "unpaved":
            H.add_edge(u, v, key=k, **data)

    F = nx.MultiGraph()
    F.add_nodes_from(G.nodes(data=True))
    for u, v, k, data in G.edges(keys=True, data=True):
        idx = int(data["road_index"])
        hazard_hit = bool(roads.loc[idx, "hazard_intersect"])
        surface = data.get("surface", "unknown")
        new_data = dict(data)
        new_data["hazard"] = hazard_hit
        if hazard_hit and surface == "unpaved":
            continue
        if hazard_hit:
            new_data["travel_time_min"] = float(data["travel_time_min"]) * 2.0
            new_data["speed_kmh"] = float(data["speed_kmh"]) / 2.0
        F.add_edge(u, v, key=k, **new_data)

    node_ids = np.array(list(G.nodes))
    node_lonlat = np.array([(G.nodes[n]["x"], G.nodes[n]["y"]) for n in node_ids])
    node_xy_3857 = np.column_stack(TRANSFORMER.transform(node_lonlat[:, 0], node_lonlat[:, 1]))
    tree = cKDTree(node_xy_3857)

    stats = {
        "nodes": G.number_of_nodes(),
        "edges": G.number_of_edges(),
        "no_unpaved_edges": H.number_of_edges(),
        "hazard_edges": F.number_of_edges(),
        "hazard_intersect_roads": int(roads["hazard_intersect"].sum()),
    }
    return G, H, F, node_ids, tree, roads, stats


def load_population(iso: str):
    path = COUNTRY_DIR / iso / f"{iso.lower()}_pd_2020_1km.tif"
    with rasterio.open(path) as src:
        pop = src.read(1).astype("float32")
        transform = src.transform
        nodata = src.nodata
    valid = (pop != nodata) & np.isfinite(pop) & (pop > 0)
    rows, cols = np.where(valid)
    values = pop[valid]
    lon = transform.c + (cols + 0.5) * transform.a
    lat = transform.f + (rows + 0.5) * transform.e
    xy = np.column_stack([lon, lat])
    xy_3857 = np.column_stack(TRANSFORMER.transform(xy[:, 0], xy[:, 1]))
    return xy, xy_3857, values


def process_country(iso: str, name: str, make_maps: bool = True):
    t0 = time.time()
    country_out = OUT / iso.lower()
    country_out.mkdir(parents=True, exist_ok=True)
    log(f"\n=== {name} ({iso}) ===")

    road_path = ROAD_DIR / ROAD_FILES[iso]
    roads = gpd.read_file(road_path)
    if roads.crs is None:
        roads = roads.set_crs(4326)
    roads = roads.to_crs(4326)

    health = load_facilities(iso, "health")
    education = load_facilities(iso, "education")
    health_core = health[health["amenity"].isin(["hospital", "clinic"])].copy()
    schools = education[education["amenity"].eq("school")].copy()
    log(f"Roads: {len(roads):,}; hospitals/clinics: {len(health_core):,}; schools: {len(schools):,}")

    hazard = load_hazard(iso)
    log(f"Hazard features: {len(hazard):,}")

    G, H, F, node_ids, tree, roads, graph_stats = build_graphs(roads, hazard)
    log(f"Graph: {graph_stats}")

    # Map facilities to graph nodes.
    def map_facilities(gdf):
        geom = gdf.geometry.representative_point()
        pts = np.column_stack([geom.x, geom.y])
        pts_3857 = np.column_stack(TRANSFORMER.transform(pts[:, 0], pts[:, 1]))
        dist, idx = tree.query(pts_3857)
        keep = dist <= 10_000
        return node_ids[idx[keep]], dist[keep]

    health_nodes, health_dist = map_facilities(health_core)
    school_nodes, school_dist = map_facilities(schools)
    health_sources = list(map(int, set(health_nodes)))
    school_sources = list(map(int, set(school_nodes)))
    log(f"Usable graph nodes: health={len(health_sources):,}, school={len(school_sources):,}")

    # Population cells.
    cell_xy, cell_xy_3857, pop_values = load_population(iso)
    cell_dist, cell_idx = tree.query(cell_xy_3857)
    cell_nodes = node_ids[cell_idx]
    log(f"Populated cells: {len(pop_values):,}; population: {pop_values.sum():,.0f}")

    scenarios = {
        "baseline": G,
        "no_unpaved": H,
        "hazard": F,
    }

    travel = {}
    for service, sources in [("health", health_sources), ("school", school_sources)]:
        for scenario, graph in scenarios.items():
            key = f"{service}_{scenario}"
            if sources:
                travel[key] = nx.multi_source_dijkstra_path_length(graph, sources, weight="travel_time_min")
            else:
                travel[key] = {}
            log(f"  {key}: reachable nodes={len(travel[key]):,}")

    # Cell-level accessibility.
    records = []
    for i, node in enumerate(cell_nodes):
        rec = {
            "lon": float(cell_xy[i, 0]),
            "lat": float(cell_xy[i, 1]),
            "population": float(pop_values[i]),
            "nearest_node": int(node),
            "nearest_node_km": float(cell_dist[i] / 1000.0),
        }
        for key, d in travel.items():
            rec[key] = d.get(int(node), np.nan)
        records.append(rec)

    cells = pd.DataFrame(records)
    cells["lon05"] = np.floor(cells["lon"] / 0.05) * 0.05 + 0.025
    cells["lat05"] = np.floor(cells["lat"] / 0.05) * 0.05 + 0.025
    travel_cols = list(travel.keys())

    agg = cells.groupby(["lon05", "lat05"], as_index=False)[["population"] + travel_cols].apply(
        lambda x: pd.Series({
            "population": x["population"].sum(),
            **{
                c: np.average(x[c], weights=x["population"]) if x[c].notna().any() else np.nan
                for c in travel_cols
            },
        })
    )
    agg_geo = gpd.GeoDataFrame(
        agg,
        geometry=gpd.points_from_xy(agg["lon05"], agg["lat05"]),
        crs=4326,
    )
    agg_geo.to_file(country_out / "access_cells_0p05deg.geojson", driver="GeoJSON")

    # Summary.
    summary_rows = []
    for service in ["health", "school"]:
        for scenario in ["baseline", "no_unpaved", "hazard"]:
            col = f"{service}_{scenario}"
            valid_pop = cells[col].notna()
            total_pop = float(cells["population"].sum())
            reachable_pop = float(cells.loc[valid_pop, "population"].sum())
            unreachable_pop = float(cells.loc[~valid_pop, "population"].sum())
            censored = cells[col].fillna(999.0)
            row = {
                "country": name,
                "iso3": iso,
                "service": service,
                "scenario": scenario,
                "total_population": total_pop,
                "population_with_finite_travel_time": reachable_pop,
                "population_unreachable_on_graph": unreachable_pop,
                "mean_travel_time_reachable_min": float(np.average(cells.loc[valid_pop, col], weights=cells.loc[valid_pop, "population"])),
                "median_travel_time_reachable_min": float(cells.loc[valid_pop, col].median()),
                "mean_censored_travel_time_min": float(np.average(censored, weights=cells["population"])),
                "median_censored_travel_time_min": float(censored.median()),
                "road_nodes": graph_stats["nodes"],
                "road_edges": graph_stats["edges"],
                "hazard_intersect_roads": graph_stats["hazard_intersect_roads"],
            }
            for threshold in [30, 60, 120, 240]:
                reachable = valid_pop & (cells[col] <= threshold)
                pop = cells.loc[reachable, "population"].sum()
                row[f"population_within_{threshold}min"] = float(pop)
                row[f"share_within_{threshold}min_pct"] = float(100 * pop / total_pop) if total_pop else np.nan
            summary_rows.append(row)

    summary = pd.DataFrame(summary_rows)
    summary.to_csv(country_out / "access_summary.csv", index=False, encoding="utf-8-sig")

    if make_maps:
        world = gpd.read_file(WORLD)
        country = world[world["NAME"].eq(name)]
        if country.empty:
            country = world[world["ADMIN"].str.contains(name, case=False, na=False)]
        country = country.to_crs(3857)

        # Health baseline map.
        col = "health_baseline"
        fig, ax = plt.subplots(figsize=(7, 8), dpi=180)
        if not country.empty:
            country.boundary.plot(ax=ax, color="#333333", linewidth=0.8, zorder=3)
        pts = agg_geo.to_crs(3857)
        sc = ax.scatter(pts.geometry.x, pts.geometry.y, c=pts[col], s=2, cmap="viridis_r", vmin=0, vmax=240, alpha=0.7, linewidths=0, zorder=2)
        cb = fig.colorbar(sc, ax=ax, fraction=0.035, pad=0.02)
        cb.set_label("Travel time (minutes)")
        ax.set_title(f"{name}: road-quality-adjusted access to nearest hospital/clinic", fontsize=11, fontweight="bold")
        ax.set_axis_off()
        fig.tight_layout()
        fig.savefig(country_out / "health_access_baseline.png", bbox_inches="tight", facecolor="white")
        plt.close(fig)

        # Disruption delta maps.
        for comparison in ["no_unpaved", "hazard"]:
            delta = agg[f"health_{comparison}"] - agg["health_baseline"]
            fig, ax = plt.subplots(figsize=(7, 8), dpi=180)
            if not country.empty:
                country.boundary.plot(ax=ax, color="#333333", linewidth=0.8, zorder=3)
            pts = agg_geo.to_crs(3857)
            sc = ax.scatter(pts.geometry.x, pts.geometry.y, c=delta, s=2, cmap="magma", vmin=0, vmax=np.nanpercentile(delta, 98), alpha=0.7, linewidths=0, zorder=2)
            cb = fig.colorbar(sc, ax=ax, fraction=0.035, pad=0.02)
            cb.set_label("Additional travel time (minutes)")
            label = "unpaved-road failure" if comparison == "no_unpaved" else "flood scenario"
            ax.set_title(f"{name}: {label} impact on hospital/clinic access", fontsize=11, fontweight="bold")
            ax.set_axis_off()
            fig.tight_layout()
            fig.savefig(country_out / f"health_access_delta_{comparison}.png", bbox_inches="tight", facecolor="white")
            plt.close(fig)

    elapsed = time.time() - t0
    log(f"Completed {name} in {elapsed:.1f}s")
    return summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--countries", nargs="*", default=list(COUNTRIES.keys()))
    parser.add_argument("--no-maps", action="store_true")
    args = parser.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    all_summaries = []
    for iso in args.countries:
        if iso not in COUNTRIES:
            raise ValueError(f"Unknown country code: {iso}")
        summary = process_country(iso, COUNTRIES[iso], make_maps=not args.no_maps)
        all_summaries.append(summary)

    combined = pd.concat(all_summaries, ignore_index=True)
    combined.to_csv(OUT / "multicountry_access_summary.csv", index=False, encoding="utf-8-sig")
    log(f"\nSaved combined summary: {OUT / 'multicountry_access_summary.csv'}")
    log(combined.to_string(index=False))


if __name__ == "__main__":
    main()
