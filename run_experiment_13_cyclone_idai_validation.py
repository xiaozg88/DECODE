# -*- coding: utf-8 -*-
"""Validate Cyclone Idai road-access constraints against flood exposure and surface.

Historical WFP/LogCluster road constraints were recovered from a 2022 Internet
Archive snapshot because the live WFP GeoNode endpoint is currently unreachable.
The same-event flood footprint is the archived raster
``MOZ_TotalFloodExtent12to2.tif`` (1=flood, 255=no data).
"""
from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from shapely.geometry import LineString, MultiLineString

import prototype_multicountry_access as base
import run_experiment_06_ablation as exp06

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output/experiments/experiment_13_hazard_validation/cyclone_idai"
ROADS = ROOT / "data/external/hdx/hazards/validation/moz_trs_roadaccessconstraints_wfp_idai/moz_trs_roadaccessconstraints_wfp.shp"
FLOOD = ROOT / "data/external/hdx/hazards/validation/moz_cyclone_idai_total_flood_extent/MOZ_TotalFloodExtent12to2.tif"
HOT = ROOT / "data/external/hdx/countries/MOZ/local_roads/hotosm_moz_roads_osm_gpkg/roads.gpkg"
PAVED_WFP = {"paved", "asphalt", "concrete", "concrete:plates", "paving_stones"}
UNPAVED_WFP = {"unpaved", "gravel", "ground", "dirt", "sand", "earth", "compacted", "fine_gravel"}


def wfp_surface_class(value) -> str:
    if pd.isna(value):
        return "unknown"
    value = str(value).strip().lower()
    if value in PAVED_WFP:
        return "paved"
    if value in UNPAVED_WFP:
        return "unpaved"
    return "unknown"


def line_samples(geometry, step_m: float = 100.0):
    lines = geometry.geoms if isinstance(geometry, MultiLineString) else [geometry]
    for line in lines:
        if not isinstance(line, LineString) or line.length == 0:
            continue
        n = max(2, int(np.ceil(line.length / step_m)) + 1)
        for distance in np.linspace(0, line.length, n):
            point = line.interpolate(distance)
            yield point.x, point.y


def mark_flood_exposure(roads: gpd.GeoDataFrame) -> np.ndarray:
    projected = roads.to_crs(3857)
    exposed = np.zeros(len(projected), dtype=bool)
    with rasterio.open(FLOOD) as src:
        flood = src.read(1)
        transform = src.transform
        for i, geom in enumerate(projected.geometry):
            rows, cols = [], []
            for x, y in line_samples(geom, step_m=100.0):
                col, row = ~transform * (x, y)
                col, row = int(col), int(row)
                if 0 <= row < src.height and 0 <= col < src.width:
                    rows.append(row)
                    cols.append(col)
            if rows and np.any(flood[np.array(rows), np.array(cols)] == 1):
                exposed[i] = True
    return exposed


def match_planet(wfp: gpd.GeoDataFrame) -> pd.DataFrame:
    planet, _ = exp06.prepare_roads("MOZ")
    left = wfp.to_crs(3857).reset_index(names="constraint_id")
    right = planet.to_crs(3857).reset_index(drop=True)
    right["planet_surface_2024"] = right.surface_2024
    right["planet_highway"] = right.osm_tags_highway
    joined = gpd.sjoin_nearest(
        left,
        right[["geometry", "planet_surface_2024", "planet_highway", "length_m"]],
        how="left",
        distance_col="distance_to_planet_m",
    )
    joined = joined.sort_values(
        ["constraint_id", "distance_to_planet_m", "index_right"]
    ).drop_duplicates("constraint_id")
    return joined.set_index("constraint_id")


def rule_metrics(frame: pd.DataFrame, predicted: str, actual: str = "actual_restricted") -> dict:
    yhat = frame[predicted].astype(bool)
    y = frame[actual].astype(bool)
    tp = int((yhat & y).sum())
    fp = int((yhat & ~y).sum())
    fn = int((~yhat & y).sum())
    tn = int((~yhat & ~y).sum())
    precision = tp / (tp + fp) if tp + fp else np.nan
    recall = tp / (tp + fn) if tp + fn else np.nan
    specificity = tn / (tn + fp) if tn + fp else np.nan
    accuracy = (tp + tn) / len(frame) if len(frame) else np.nan
    return {
        "rule": predicted,
        "n": int(len(frame)),
        "true_positive": tp,
        "false_positive": fp,
        "false_negative": fn,
        "true_negative": tn,
        "precision": precision,
        "recall": recall,
        "specificity": specificity,
        "accuracy": accuracy,
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    wfp = gpd.read_file(ROADS).to_crs(4326).reset_index(drop=True)
    wfp["status_clean"] = wfp.status.astype(str).str.strip().str.title()
    wfp["known_road_status"] = wfp.status_clean.isin(["Open", "Restricted", "Closed"])
    wfp["actual_restricted"] = wfp.status_clean.isin(["Restricted", "Closed"])
    wfp["wfp_surface_class"] = wfp.srftpe.map(wfp_surface_class)
    wfp["idai_flood_exposed"] = mark_flood_exposure(wfp)

    planet_match = match_planet(wfp)
    wfp = wfp.join(
        planet_match[["distance_to_planet_m", "planet_surface_2024", "planet_highway"]]
    )
    wfp["matched_planet_within_1km"] = wfp.distance_to_planet_m.le(1000)
    wfp["predicted_unpaved_removed"] = (
        wfp.idai_flood_exposed
        & wfp.planet_surface_2024.eq("unpaved")
        & wfp.matched_planet_within_1km
    )
    wfp["predicted_any_flood_disrupted"] = wfp.idai_flood_exposed
    wfp["predicted_planet_unpaved_anywhere"] = wfp.planet_surface_2024.eq("unpaved") & wfp.matched_planet_within_1km

    # Exact historical-to-current OSM matching by way ID.
    hot = gpd.read_file(HOT, columns=["id", "geometry"])
    hot["historical_osm_id"] = hot.id.astype(str).str.replace("way/", "", regex=False)
    historical_ids = wfp.osm_id.dropna().astype(float).astype(np.int64).astype(str)
    current_ids = set(hot.historical_osm_id)
    wfp["matched_current_osm_way"] = historical_ids.isin(current_ids).reindex(wfp.index, fill_value=False)

    # Status summaries.
    status_rows = []
    for status, group in wfp.groupby("status_clean"):
        status_rows.append(
            {
                "status": status,
                "roads": int(len(group)),
                "share_pct": 100.0 * len(group) / len(wfp),
                "flood_exposed_share_pct": 100.0 * group.idai_flood_exposed.mean(),
                "wfp_unpaved_share_pct": 100.0 * group.wfp_surface_class.eq("unpaved").mean(),
                "planet_unpaved_share_pct_1km": 100.0 * group.loc[group.matched_planet_within_1km, "planet_surface_2024"].eq("unpaved").mean(),
                "planet_match_within_1km_pct": 100.0 * group.matched_planet_within_1km.mean(),
                "matched_current_osm_way_pct": 100.0 * group.matched_current_osm_way.mean(),
            }
        )

    surface_rows = []
    known = wfp[wfp.wfp_surface_class.ne("unknown") & wfp.matched_planet_within_1km]
    for wfp_surface, group in known.groupby("wfp_surface_class"):
        for planet_surface, subgroup in group.groupby("planet_surface_2024"):
            surface_rows.append(
                {
                    "wfp_surface": wfp_surface,
                    "planet_surface_2024": planet_surface,
                    "roads": int(len(subgroup)),
                    "row_share_pct": 100.0 * len(subgroup) / len(known),
                }
            )

    validation_frame = wfp[wfp.matched_planet_within_1km & wfp.known_road_status].copy()
    metrics = pd.DataFrame(
        [
            rule_metrics(validation_frame, "predicted_any_flood_disrupted"),
            rule_metrics(validation_frame, "predicted_unpaved_removed"),
            rule_metrics(validation_frame, "predicted_planet_unpaved_anywhere"),
            rule_metrics(validation_frame, "idai_flood_exposed"),
        ]
    )

    source_inventory = pd.DataFrame(
        [
            {
                "source": "WFP/LogCluster Cyclone Idai road access constraints",
                "retrieval": "Internet Archive snapshot 2022-05-12; live WFP GeoNode currently unreachable",
                "records": int(len(wfp)),
                "path": str(ROADS.relative_to(ROOT)),
                "event": "Cyclone Idai, March 2019",
            },
            {
                "source": "Cyclone Idai total flood extent raster",
                "retrieval": "HDX archived ZIP",
                "records": 1,
                "path": str(FLOOD.relative_to(ROOT)),
                "event": "12-26 March 2019; raster value 1=flood",
            },
            {
                "source": "Current HOT OSM roads",
                "retrieval": "HDX GPKG",
                "records": int(len(hot)),
                "path": str(HOT.relative_to(ROOT)),
                "event": "used for historical OSM way-ID persistence check",
            },
        ]
    )

    wfp.to_csv(OUT / "cyclone_idai_road_status_inventory.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(status_rows).to_csv(OUT / "cyclone_idai_status_summary.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(surface_rows).to_csv(OUT / "cyclone_idai_surface_confusion.csv", index=False, encoding="utf-8-sig")
    metrics.to_csv(OUT / "cyclone_idai_rule_validation_metrics.csv", index=False, encoding="utf-8-sig")
    source_inventory.to_csv(OUT / "cyclone_idai_validation_source_inventory.csv", index=False, encoding="utf-8-sig")

    print("Status summary:")
    print(pd.DataFrame(status_rows).to_string(index=False))
    print("\nRule metrics among Planet 1-km matches:")
    print(metrics.to_string(index=False))
    print(f"Exact current-OSM way matches: {int(wfp.matched_current_osm_way.sum())}/{len(wfp)}")


if __name__ == "__main__":
    main()
