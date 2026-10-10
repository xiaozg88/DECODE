# -*- coding: utf-8 -*-
"""Experiment 15: urban-rural heterogeneity in service accessibility."""
from __future__ import annotations

import argparse
import os
import time
from pathlib import Path

import geopandas as gpd
import networkx as nx
import numpy as np
import pandas as pd
import rasterio
from pyproj import Transformer
from rasterio.windows import from_bounds
from scipy.spatial import cKDTree

import prototype_multicountry_access as base

os.environ.setdefault("GDAL_HTTP_TIMEOUT", "120")

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output/experiments/experiment_15_urban_rural"
SMOD_URL = (
    "https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/GHSL/GHS_SMOD_GLOBE_R2023A/"
    "GHS_SMOD_E2020_GLOBE_R2023A_54009_1000/V1-0/"
    "GHS_SMOD_E2020_GLOBE_R2023A_54009_1000_V1_0.zip"
)
SMOD_PATH = f"zip+{SMOD_URL}!/GHS_SMOD_E2020_GLOBE_R2023A_54009_1000_V1_0.tif"
LOCAL_SMOD = ROOT / "data/external/ghs/GHS_SMOD_E2020_GLOBE_R2023A_54009_1000_V1_0.tif"
SMOD_PATH = str(LOCAL_SMOD) if LOCAL_SMOD.exists() else SMOD_PATH
SMOD_TO_54009 = Transformer.from_crs(4326, "ESRI:54009", always_xy=True)

SMOD_LABELS = {
    10: "water",
    11: "very_low_density_rural",
    12: "low_density_rural",
    13: "rural",
    21: "suburban_peri_urban",
    22: "semi_dense_urban",
    23: "dense_urban",
    30: "urban_centre",
}


def classify_smod(values: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    codes = values.astype(int)
    detailed = np.array(["unknown"] * len(codes), dtype=object)
    urban_rural = np.array(["unknown"] * len(codes), dtype=object)
    for code, label in SMOD_LABELS.items():
        mask = codes == code
        detailed[mask] = label
        if code in [11, 12, 13]:
            urban_rural[mask] = "rural"
        elif code in [21, 22, 23, 30]:
            urban_rural[mask] = "urban"
    return detailed, urban_rural


def sample_smod(lon: np.ndarray, lat: np.ndarray) -> np.ndarray:
    x, y = SMOD_TO_54009.transform(lon, lat)
    minx, miny = float(np.min(x)), float(np.min(y))
    maxx, maxy = float(np.max(x)), float(np.max(y))
    with rasterio.open(SMOD_PATH) as src:
        window = from_bounds(minx, miny, maxx, maxy, transform=src.transform)
        data = src.read(1, window=window, boundless=True, fill_value=src.nodata)
        window_transform = src.window_transform(window)
        rows, cols = rasterio.transform.rowcol(window_transform, x, y)
        rows = np.asarray(rows, dtype=int)
        cols = np.asarray(cols, dtype=int)
        valid = (
            (rows >= 0)
            & (rows < data.shape[0])
            & (cols >= 0)
            & (cols < data.shape[1])
        )
        sampled = np.full(len(x), -200, dtype=np.int16)
        sampled[valid] = data[rows[valid], cols[valid]]
        return sampled


def access_table(iso: str):
    path = base.OUT / iso.lower() / "access_cells_0p05deg.geojson"
    cells = gpd.read_file(path)
    xy_3857 = np.column_stack(base.TRANSFORMER.transform(cells.geometry.x, cells.geometry.y))
    tree = cKDTree(xy_3857)
    return cells, tree


def summarize_group(
    name: str,
    iso: str,
    group_field: str,
    group_value: str,
    population: np.ndarray,
    access_values: dict[str, np.ndarray],
    nearest_cell_km: np.ndarray,
) -> list[dict]:
    total_population = float(population.sum())
    rows = []
    for service in ["health", "school"]:
        for scenario in ["baseline", "no_unpaved", "hazard"]:
            column = f"{service}_{scenario}"
            values = access_values[column]
            valid = np.isfinite(values)
            reachable_population = float(population[valid].sum())
            row = {
                "country": name,
                "iso3": iso,
                "group_field": group_field,
                "group": group_value,
                "service": service,
                "scenario": scenario,
                "population_cells": int(len(population)),
                "total_population": total_population,
                "reachable_population": reachable_population,
                "unreachable_population": total_population - reachable_population,
                "mean_nearest_access_cell_km": float(np.average(nearest_cell_km, weights=population)),
            }
            if reachable_population:
                row["mean_travel_time_reachable_min"] = float(
                    np.average(values[valid], weights=population[valid])
                )
                row["median_travel_time_reachable_min"] = float(np.median(values[valid]))
            else:
                row["mean_travel_time_reachable_min"] = np.nan
                row["median_travel_time_reachable_min"] = np.nan
            for threshold in [30, 60, 120, 240]:
                within = valid & (values <= threshold)
                within_population = float(population[within].sum())
                row[f"population_within_{threshold}min"] = within_population
                row[f"share_within_{threshold}min_pct"] = 100 * within_population / total_population
            rows.append(row)
    return rows


def source_nodes(facilities: gpd.GeoDataFrame, node_ids: np.ndarray, tree) -> list[int]:
    points = facilities.geometry.representative_point().to_crs(3857)
    xy = np.column_stack([points.geometry.x, points.geometry.y])
    distances, indices = tree.query(xy)
    usable = distances <= 5000.0
    return [int(node) for node in node_ids[indices[usable]]]


def process_country(iso: str, name: str) -> list[dict]:
    started = time.time()
    print(f"\n=== {name} ({iso}) ===", flush=True)
    road_path = base.ROAD_DIR / base.ROAD_FILES[iso]
    roads = gpd.read_file(road_path)
    if roads.crs is None:
        roads = roads.set_crs(4326)
    roads = roads.to_crs(4326)
    hazard = base.load_hazard(iso)
    G, H, F, node_ids, tree, roads, graph_stats = base.build_graphs(roads, hazard)
    print(f"Graph: {graph_stats}", flush=True)

    health = base.load_facilities(iso, "health")
    education = base.load_facilities(iso, "education")
    health_core = health[health["amenity"].isin(["hospital", "clinic"])].copy()
    schools = education[education["amenity"].eq("school")].copy()
    health_sources = source_nodes(health_core, node_ids, tree)
    school_sources = source_nodes(schools, node_ids, tree)

    cell_lon, cell_xy_3857, population = base.load_population(iso)
    distances, indices = tree.query(cell_xy_3857)
    cell_nodes = node_ids[indices]
    scenarios = {"baseline": G, "no_unpaved": H, "hazard": F}
    access_values = {}
    for service, sources in [("health", health_sources), ("school", school_sources)]:
        for scenario, graph in scenarios.items():
            travel = nx.multi_source_dijkstra_path_length(graph, sources, weight="travel_time_min")
            column = f"{service}_{scenario}"
            access_values[column] = np.array(
                [travel.get(int(node), np.nan) for node in cell_nodes],
                dtype=float,
            )

    smod_values = sample_smod(cell_lon[:, 0], cell_lon[:, 1])
    detailed, urban_rural = classify_smod(smod_values)
    print(
        "SMOD distribution: "
        + str(pd.Series(urban_rural).value_counts(normalize=True).round(3).to_dict()),
        flush=True,
    )

    rows = []
    for group_field, groups in [
        ("urban_rural", urban_rural),
        ("smod_class", detailed),
    ]:
        for group in pd.unique(groups):
            mask = groups == group
            rows.extend(
                summarize_group(
                    name,
                    iso,
                    group_field,
                    str(group),
                    population[mask],
                    {key: value[mask] for key, value in access_values.items()},
                    distances[mask] / 1000.0,
                )
            )

    print(f"Completed {name} in {time.time() - started:.1f}s", flush=True)
    return rows


def create_gap_table(summary: pd.DataFrame) -> pd.DataFrame:
    data = summary[summary["group_field"].eq("urban_rural")].copy()
    key = ["country", "iso3", "service", "scenario"]
    urban = data[data["group"].eq("urban")].set_index(key)
    rural = data[data["group"].eq("rural")].set_index(key)
    joined = urban.join(
        rural,
        lsuffix="_urban",
        rsuffix="_rural",
        how="inner",
    ).reset_index()
    joined["urban_rural_gap_60min_pct_points"] = (
        joined["share_within_60min_pct_urban"] - joined["share_within_60min_pct_rural"]
    )
    joined["hazard_loss_urban_pct_points"] = np.nan
    joined["hazard_loss_rural_pct_points"] = np.nan
    for group in ["urban", "rural"]:
        baseline = joined.loc[joined["scenario"].eq("baseline"), f"share_within_60min_pct_{group}"].to_numpy()
        hazard = joined.loc[joined["scenario"].eq("hazard"), f"share_within_60min_pct_{group}"].to_numpy()
        if len(baseline) == len(hazard):
            joined.loc[joined["scenario"].eq("hazard"), f"hazard_loss_{group}_pct_points"] = hazard - baseline
    return joined


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--countries", nargs="*", default=list(base.COUNTRIES.keys()))
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)

    rows = []
    for iso in args.countries:
        rows.extend(process_country(iso, base.COUNTRIES[iso]))

    summary = pd.DataFrame(rows)
    summary.to_csv(OUT / "urban_rural_access_summary.csv", index=False, encoding="utf-8-sig")
    gaps = create_gap_table(summary)
    gaps.to_csv(OUT / "urban_rural_access_gaps.csv", index=False, encoding="utf-8-sig")
    print(f"Saved: {OUT / 'urban_rural_access_summary.csv'}")
    print(f"Saved: {OUT / 'urban_rural_access_gaps.csv'}")


if __name__ == "__main__":
    main()
