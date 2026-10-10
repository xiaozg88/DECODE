# -*- coding: utf-8 -*-
"""Download GDL SHDI and World Bank socioeconomic inputs for Experiment 16."""
from __future__ import annotations

import json
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "data/external/socioeconomic"
GDL = OUT / "gdl"
WB = OUT / "worldbank"
GDL.mkdir(parents=True, exist_ok=True)
WB.mkdir(parents=True, exist_ok=True)

COUNTRIES = ["PAK", "MOZ", "BGD", "ETH", "KEN", "PHL", "COL"]
INDICATORS = {
    "SI.POV.NAHC": "national_poverty_headcount_pct",
    "SI.POV.DDAY": "poverty_215_a_day_pct",
}


def download(url: str, dest: Path) -> None:
    if dest.exists() and dest.stat().st_size > 0:
        print(f"exists: {dest.name} ({dest.stat().st_size / 1e6:.1f} MB)")
        return
    response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=300)
    response.raise_for_status()
    dest.write_bytes(response.content)
    print(f"saved: {dest.name} ({dest.stat().st_size / 1e6:.1f} MB)")


def main() -> None:
    # Public JSON table endpoint used by the GDL web table.
    table_url = "https://globaldatalab.org/shdi/table/shdi/"
    params = {"format": "json", "levels": "1+4", "query_range": "offset"}
    if not (GDL / "shdi_table_levels_1_4.json").exists():
        response = requests.get(
            table_url,
            params=params,
            headers={"User-Agent": "Mozilla/5.0", "X-Requested-With": "XMLHttpRequest"},
            timeout=300,
        )
        response.raise_for_status()
        (GDL / "shdi_table_levels_1_4.json").write_text(
            json.dumps(response.json(), ensure_ascii=False), encoding="utf-8"
        )
        print("saved GDL SHDI table JSON")
    else:
        print("exists: GDL SHDI table JSON")

    download(
        "https://globaldatalab.org/asset/677/GDL%20Shapefiles%20V6.7%20small.json",
        GDL / "gdl_regions_v6_7.geojson",
    )

    metadata = requests.get(
        "https://api.worldbank.org/v2/country/",
        params={"format": "json", "per_page": "400"},
        timeout=120,
    )
    metadata.raise_for_status()
    payload = metadata.json()[1]
    selected = [x for x in payload if x["id"] in COUNTRIES]
    (WB / "country_metadata.json").write_text(
        json.dumps(selected, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    rows = []
    for indicator in INDICATORS:
        response = requests.get(
            f"https://api.worldbank.org/v2/country/{';'.join(COUNTRIES)}/indicator/{indicator}",
            params={"format": "json", "per_page": "20000"},
            timeout=120,
        )
        response.raise_for_status()
        body = response.json()
        records = body[1] if len(body) > 1 else []
        for record in records:
            rows.append(
                {
                    "indicator": indicator,
                    "indicator_name": record["indicator"]["value"],
                    "iso3": record["countryiso3code"],
                    "year": int(record["date"]),
                    "value": record["value"],
                }
            )
    (WB / "poverty_indicators_raw.csv").write_text(
        __import__("pandas").DataFrame(rows).to_csv(index=False), encoding="utf-8"
    )
    print("saved World Bank metadata and poverty indicators")


if __name__ == "__main__":
    main()
