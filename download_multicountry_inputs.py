# -*- coding: utf-8 -*-
"""Download the core inputs for the multi-country access prototype.

Inputs downloaded:
- WorldPop 2020 1 km population density
- OSM health facilities
- OSM education facilities

The road GPKGs are downloaded separately and already live in
data/external/hdx/roads/.
"""
from __future__ import annotations

from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parent
BASE = ROOT / "data/external/hdx/countries"

COUNTRIES = {
    "PAK": "Pakistan",
    "MOZ": "Mozambique",
    "BGD": "Bangladesh",
    "ETH": "Ethiopia",
    "KEN": "Kenya",
    "PHL": "Philippines",
    "COL": "Colombia",
}

# Countries whose HOTOSM exports are split into points and polygons.
SPLIT_EXPORTS = {"PAK", "PHL"}


def download(url: str, dest: Path):
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 0:
        print(f"  exists: {dest.name}")
        return
    print(f"  downloading: {url}")
    with requests.get(url, stream=True, timeout=120) as r:
        r.raise_for_status()
        tmp = dest.with_suffix(dest.suffix + ".part")
        with tmp.open("wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)
        tmp.replace(dest)
    print(f"  saved: {dest.name} ({dest.stat().st_size / 1_000_000:.1f} MB)")


for iso, name in COUNTRIES.items():
    print(f"\n{name} ({iso})")
    country_dir = BASE / iso
    country_dir.mkdir(parents=True, exist_ok=True)

    pop_url = (
        "https://data.worldpop.org/GIS/Population_Density/"
        f"Global_2000_2020_1km/2020/{iso}/{iso.lower()}_pd_2020_1km.tif"
    )
    download(pop_url, country_dir / f"{iso.lower()}_pd_2020_1km.tif")

    if iso in SPLIT_EXPORTS:
        for kind in ["health_facilities", "education_facilities"]:
            for geom in ["points", "polygons"]:
                url = (
                    "https://s3.dualstack.us-east-1.amazonaws.com/"
                    f"production-raw-data-api/ISO3/{iso}/{kind}/{geom}/"
                    f"hotosm_{iso.lower()}_{kind}_{geom}_gpkg.zip"
                )
                download(url, country_dir / f"hotosm_{iso.lower()}_{kind}_{geom}_gpkg.zip")
    else:
        for kind in ["health_facilities", "education_facilities"]:
            url = (
                "https://production-raw-data-api.s3.amazonaws.com/"
                f"ISO3/{iso}/{kind}/hotosm_{iso.lower()}_{kind}_osm_gpkg.zip"
            )
            download(url, country_dir / f"hotosm_{iso.lower()}_{kind}_osm_gpkg.zip")

print("\nDone.")
