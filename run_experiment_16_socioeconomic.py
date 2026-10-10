# -*- coding: utf-8 -*-
"""Experiment 16: accessibility heterogeneity by subnational development.

This experiment replaces the population-density proxy in Experiment 17 with:
1. GDL Subnational HDI at the GDL region level.
2. World Bank country income groups.
3. World Bank national poverty headcounts (where available).

Cells from the 0.05-degree accessibility surfaces are assigned to GDL regions
and aggregated with population weights. National poverty maps are not yet
available, so poverty remains country-level rather than spatial.
"""
from __future__ import annotations

import html
import json
import re
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

import prototype_multicountry_access as base

ROOT = Path(__file__).resolve().parent
GDL_DIR = ROOT / "data/external/socioeconomic/gdl"
WB_DIR = ROOT / "data/external/socioeconomic/worldbank"
OUT = ROOT / "output/experiments/experiment_16_socioeconomic"
SHDI_JSON = GDL_DIR / "shdi_table_levels_1_4.json"
GDL_GEOJSON = GDL_DIR / "gdl_regions_v6_7.geojson"
COUNTRIES = ["PAK", "MOZ", "BGD", "ETH", "KEN", "PHL", "COL"]
COUNTRY_NAMES = base.COUNTRIES


def parse_gdl_shdi() -> pd.DataFrame:
    payload = json.loads(SHDI_JSON.read_text(encoding="utf-8"))
    table = payload["table"]
    rows: list[dict] = []
    country = ""
    for attrs, row_html in re.findall(r"<tr\b([^>]*)>(.*?)</tr>", table, re.I | re.S):
        cells_raw = re.findall(r"<t[hd]\b[^>]*>(.*?)</t[hd]>", row_html, re.I | re.S)
        cells = [html.unescape(re.sub(r"<[^>]+>", "", x)).strip() for x in cells_raw]
        if "country" in attrs.lower():
            country = cells[0] if cells else ""
            continue
        if not cells or len(cells) < 2 or not country:
            continue
        code_match = re.search(r'title=["\']([^"\']+?)\s*:', cells_raw[0], re.I)
        region_code = html.unescape(code_match.group(1).strip()) if code_match else ""
        if not any(region_code.startswith(iso) for iso in COUNTRIES):
            continue
        # The country header contains a continent suffix in the JSON fragment;
        # map to the canonical project country name using the GDL region code.
        country = COUNTRY_NAMES[region_code[:3]]
        for year, value in zip(range(1990, 2024), cells[1:]):
            try:
                shdi = float(value.replace(",", ""))
            except ValueError:
                continue
            rows.append(
                {
                    "country": country,
                    "iso3": region_code[:3],
                    "region_code": region_code,
                    "region": cells[0],
                    "year": year,
                    "shdi": shdi,
                }
            )
    return pd.DataFrame(rows)


def weighted_mean(values: np.ndarray, weights: np.ndarray) -> float:
    valid = np.isfinite(values) & np.isfinite(weights) & (weights > 0)
    if not valid.any():
        return np.nan
    return float(np.average(values[valid], weights=weights[valid]))


def weighted_correlation(x: np.ndarray, y: np.ndarray, weights: np.ndarray) -> float:
    valid = np.isfinite(x) & np.isfinite(y) & np.isfinite(weights) & (weights > 0)
    if valid.sum() < 3:
        return np.nan
    x, y, w = x[valid], y[valid], weights[valid]
    mx, my = np.average(x, weights=w), np.average(y, weights=w)
    cov = np.average((x - mx) * (y - my), weights=w)
    vx = np.average((x - mx) ** 2, weights=w)
    vy = np.average((y - my) ** 2, weights=w)
    return float(cov / np.sqrt(vx * vy)) if vx > 0 and vy > 0 else np.nan


def aggregate_regions() -> pd.DataFrame:
    shdi = parse_gdl_shdi()
    shdi_2020 = shdi[shdi.year.eq(2020)].copy()
    regions = gpd.read_file(GDL_GEOJSON)
    regions = regions[regions.iso_code.isin(COUNTRIES)][["iso_code", "country", "gdlcode", "region", "geometry"]].copy()

    all_regions = []
    for iso in COUNTRIES:
        cells_path = ROOT / f"output/prototype/multicountry/{iso.lower()}/access_cells_0p05deg.geojson"
        cells = gpd.read_file(cells_path).drop(columns="geometry")
        cells = gpd.GeoDataFrame(
            cells,
            geometry=gpd.points_from_xy(cells.lon05, cells.lat05),
            crs=4326,
        ).to_crs(3857)
        country_regions = regions[regions.iso_code.eq(iso)].to_crs(3857)
        joined = gpd.sjoin_nearest(
            cells,
            country_regions,
            how="left",
            distance_col="distance_to_gdl_region_m",
        )
        joined = joined.sort_values(["lon05", "lat05", "distance_to_gdl_region_m"]).drop_duplicates(
            ["lon05", "lat05"]
        )
        all_regions.append(joined)

    joined = gpd.GeoDataFrame(pd.concat(all_regions, ignore_index=True), crs=3857)
    rows = []
    for (_, gdlcode), group in joined.groupby(["iso_code", "gdlcode"]):
        pop = group.population.to_numpy(dtype=float)
        row = {
            "country": COUNTRY_NAMES[group.iloc[0]["iso_code"]],
            "iso3": group.iloc[0]["iso_code"],
            "gdlcode": gdlcode,
            "gdl_region": group.iloc[0]["region"],
            "population": float(pop.sum()),
            "access_cells": int(len(group)),
            "median_distance_to_gdl_region_m": float(group.distance_to_gdl_region_m.median()),
        }
        for service in ["health", "school"]:
            for scenario in ["baseline", "no_unpaved", "hazard"]:
                values = group[f"{service}_{scenario}"].to_numpy(dtype=float)
                finite = np.isfinite(values)
                row[f"{service}_{scenario}_mean_travel_min"] = weighted_mean(values, pop)
                # Threshold share keeps unreachable/NaN cells in the denominator.
                row[f"{service}_{scenario}_share_60min_pct"] = 100.0 * pop[values <= 60].sum() / pop.sum()
                row[f"{service}_{scenario}_finite_travel_population_share_pct"] = 100.0 * pop[finite].sum() / pop.sum()
            row[f"{service}_hazard_loss_60min_pct_points"] = (
                row[f"{service}_hazard_share_60min_pct"] - row[f"{service}_baseline_share_60min_pct"]
            )
        rows.append(row)

    region_summary = pd.DataFrame(rows)
    region_summary = region_summary.merge(
        shdi_2020[["region_code", "region", "shdi"]],
        left_on="gdlcode",
        right_on="region_code",
        how="left",
        suffixes=("", "_shdi"),
    ).rename(columns={"shdi": "shdi_2020", "region_shdi": "shdi_region_name"})
    return region_summary.drop(columns=["region_code"])


def create_quintiles(region: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (country, iso), group in region.groupby(["country", "iso3"], sort=False):
        if len(group) >= 5:
            try:
                group = group.copy()
                group["shdi_quintile"] = pd.qcut(
                    group.shdi_2020,
                    q=5,
                    labels=False,
                    duplicates="drop",
                ).astype(int) + 1
            except ValueError:
                group = group.copy()
                group["shdi_quintile"] = 1
        else:
            group = group.copy()
            group["shdi_quintile"] = 1
        for quintile, qgroup in group.groupby("shdi_quintile"):
            pop = qgroup.population.to_numpy(dtype=float)
            row = {
                "country": country,
                "iso3": iso,
                "shdi_quintile": int(quintile),
                "regions": int(len(qgroup)),
                "population": float(pop.sum()),
                "mean_shdi_2020": float(np.average(qgroup.shdi_2020, weights=pop)),
            }
            for service in ["health", "school"]:
                for scenario in ["baseline", "hazard"]:
                    shares = qgroup[f"{service}_{scenario}_share_60min_pct"].to_numpy(dtype=float)
                    row[f"{service}_{scenario}_share_60min_pct"] = float(np.average(shares, weights=pop))
                row[f"{service}_hazard_loss_pct_points"] = (
                    row[f"{service}_hazard_share_60min_pct"] - row[f"{service}_baseline_share_60min_pct"]
                )
            rows.append(row)
    return pd.DataFrame(rows)


def within_country_correlations(region: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (country, iso), group in region.groupby(["country", "iso3"], sort=False):
        for service in ["health", "school"]:
            rows.append(
                {
                    "country": country,
                    "iso3": iso,
                    "service": service,
                    "regions": int(len(group)),
                    "shdi_vs_baseline60_pearson": float(group.shdi_2020.corr(group[f"{service}_baseline_share_60min_pct"])),
                    "shdi_vs_baseline60_spearman": float(group.shdi_2020.corr(group[f"{service}_baseline_share_60min_pct"], method="spearman")),
                    "shdi_vs_baseline60_weighted_pearson": weighted_correlation(
                        group.shdi_2020.to_numpy(), group[f"{service}_baseline_share_60min_pct"].to_numpy(), group.population.to_numpy()
                    ),
                    "shdi_vs_hazard_loss_weighted_pearson": weighted_correlation(
                        group.shdi_2020.to_numpy(), group[f"{service}_hazard_loss_60min_pct_points"].to_numpy(), group.population.to_numpy()
                    ),
                    "shdi_vs_baseline_finite_coverage_weighted_pearson": weighted_correlation(
                        group.shdi_2020.to_numpy(),
                        group[f"{service}_baseline_finite_travel_population_share_pct"].to_numpy(),
                        group.population.to_numpy(),
                    ),
                }
            )
    return pd.DataFrame(rows)


def load_worldbank() -> tuple[pd.DataFrame, pd.DataFrame]:
    metadata = pd.DataFrame(json.loads((WB_DIR / "country_metadata.json").read_text(encoding="utf-8")))
    meta = metadata[
        ["id", "name", "region", "incomeLevel", "lendingType"]
    ].copy()
    meta.columns = ["iso3", "wb_country", "wb_region", "wb_income_level", "wb_lending_type"]
    meta["wb_region"] = meta.wb_region.map(lambda x: x["value"])
    meta["wb_income_level"] = meta.wb_income_level.map(lambda x: x["value"])
    meta["wb_lending_type"] = meta.wb_lending_type.map(lambda x: x["value"])

    poverty = pd.read_csv(WB_DIR / "poverty_indicators_raw.csv")
    poverty = poverty[poverty.value.notna() & poverty.year.le(2025)].copy()
    poverty = poverty.sort_values(["iso3", "indicator", "year"]).groupby(
        ["iso3", "indicator"], as_index=False
    ).tail(1)
    poverty["metric"] = poverty.indicator.map(
        {"SI.POV.NAHC": "latest_national_poverty_pct", "SI.POV.DDAY": "latest_poverty_215_pct"}
    )
    wide = poverty.pivot(index="iso3", columns="metric", values="value").reset_index()
    wide["poverty_reference_year"] = poverty.groupby("iso3").year.max().reindex(wide.iso3).to_numpy()
    return meta, wide


def national_summary(shdi: pd.DataFrame) -> pd.DataFrame:
    model = pd.read_csv(ROOT / "output/experiments/experiment_06_ablation/ablation_summary.csv")
    model = model[model.model.eq("m3_class_surface_width")].copy()
    total = shdi[shdi.region_code.str.endswith("t") & shdi.year.eq(2020)][
        ["country", "iso3", "shdi"]
    ].rename(columns={"shdi": "national_shdi_2020"})
    # Build explicitly by country and service; country/scenario rows are not
    # unique before service is included, so a pivot here would be ambiguous.
    rows = []
    for (country, iso), group in model.groupby(["country", "iso3"]):
        row = {"country": country, "iso3": iso}
        for service in ["health", "school"]:
            service_row = group[group.service.eq(service)].set_index("scenario")
            row[f"{service}_baseline_60min_pct"] = service_row.loc["baseline", "share_within_60min_pct"]
            row[f"{service}_hazard_60min_pct"] = service_row.loc["hazard", "share_within_60min_pct"]
            row[f"{service}_hazard_loss_pct_points"] = (
                row[f"{service}_hazard_60min_pct"] - row[f"{service}_baseline_60min_pct"]
            )
        rows.append(row)
    model_summary = pd.DataFrame(rows)
    meta, poverty = load_worldbank()
    summary = total.merge(model_summary, on=["country", "iso3"])
    summary = summary.merge(meta, on="iso3", how="left")
    summary = summary.merge(poverty, on="iso3", how="left")
    return summary


def national_correlations(summary: pd.DataFrame) -> pd.DataFrame:
    rows = []
    candidates = [
        "health_baseline_60min_pct",
        "school_baseline_60min_pct",
        "health_hazard_loss_pct_points",
        "school_hazard_loss_pct_points",
    ]
    for column in candidates:
        rows.append(
            {
                "comparison": f"national_shdi_2020 vs {column}",
                "n": int(summary[[column, "national_shdi_2020"]].dropna().shape[0]),
                "pearson": float(summary.national_shdi_2020.corr(summary[column])),
                "spearman": float(summary.national_shdi_2020.corr(summary[column], method="spearman")),
            }
        )
    return pd.DataFrame(rows)


def data_inventory() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"source": "GDL SHDI table", "resolution": "GDL region, 1990-2023", "status": "downloaded", "used": "subnational SHDI 2020"},
            {"source": "GDL Shapefiles V6.7", "resolution": "GDL region polygons", "status": "downloaded", "used": "spatial allocation of 0.05-degree cells"},
            {"source": "World Bank country metadata", "resolution": "country", "status": "downloaded", "used": "income group and region"},
            {"source": "World Bank poverty indicators", "resolution": "country-year", "status": "downloaded; sparse", "used": "latest national poverty headcount"},
            {"source": "Subnational poverty map", "resolution": "desired gridded/admin", "status": "not available", "used": "not used; remains a blocker"},
        ]
    )


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    shdi = parse_gdl_shdi()
    region_path = OUT / "shdi_access_by_gdl_region.csv"
    if region_path.exists():
        region = pd.read_csv(region_path)
    else:
        region = aggregate_regions()
        # Cache immediately; spatial allocation is the slow step.
        region.to_csv(region_path, index=False, encoding="utf-8-sig")
    quintiles = create_quintiles(region)
    correlations = within_country_correlations(region)
    national = national_summary(shdi)
    national_corr = national_correlations(national)
    inventory = data_inventory()

    shdi.to_csv(OUT / "gdl_shdi_long_7countries.csv", index=False, encoding="utf-8-sig")
    region.to_csv(OUT / "shdi_access_by_gdl_region.csv", index=False, encoding="utf-8-sig")
    quintiles.to_csv(OUT / "shdi_quintile_access_summary.csv", index=False, encoding="utf-8-sig")
    correlations.to_csv(OUT / "within_country_shdi_access_correlations.csv", index=False, encoding="utf-8-sig")
    national.to_csv(OUT / "country_socioeconomic_access_summary.csv", index=False, encoding="utf-8-sig")
    national_corr.to_csv(OUT / "country_shdi_access_correlations.csv", index=False, encoding="utf-8-sig")
    inventory.to_csv(OUT / "socioeconomic_data_inventory.csv", index=False, encoding="utf-8-sig")

    print("National summary:")
    print(national.to_string(index=False))
    print("\nCountry correlations:")
    print(national_corr.to_string(index=False))
    print("\nWithin-country correlations:")
    print(correlations.to_string(index=False))


if __name__ == "__main__":
    main()
