# -*- coding: utf-8 -*-
"""Download independent facility registries for Experiment 14."""
from __future__ import annotations

import zipfile
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "data/external/facility_validation"

FILES = {
    "PAK_DHIS_health_2012.xlsx": "https://data.humdata.org/dataset/4834fafd-5ab9-4583-bab5-88b1ac56f3e3/resource/7128024f-ff2a-4cb1-9221-433c07e161af/download/list_of_flc_health_facilities_dhis.xlsx",
    "KEN_MFL_health_2017.xlsx": "https://data.humdata.org/dataset/7b9c2851-dc37-4a88-9dcb-62e55eb91baf/resource/df6bfc55-3b25-4309-a1b4-74afba434956/download/kenya-health-facilities-2017_08_02.xlsx",
    "COL_REPS_sedes_geo.xlsx": "https://data.humdata.org/dataset/f9ddf402-c0dd-4d42-b669-ba07a6b37d6d/resource/bf1c0809-0c44-4cee-85e9-61c66c705b2b/download/sedes_geo.xlsx",
    "ETH_health_facilities_2025.zip": "https://data.humdata.org/dataset/0eddd032-1b41-4620-8c37-c6ae5e2fee8e/resource/70d3ec35-d3c6-41d5-985c-ccc7145d7dca/download/ethiopian_health_facilities.zip",
    "MOZ_MFL_health_2017.zip": "https://data.humdata.org/dataset/96a9e919-e09a-465c-8783-a5102cb6986d/resource/54afcdd1-9c5a-47d3-bb74-2491b025809e/download/mozambique-health-facilities.zip",
    "BGD_LGED_education_2017.zip": "https://data.humdata.org/dataset/42908dc9-6a5f-4947-9048-f8f97da749a1/resource/1dbae83a-7629-461e-8b08-63da519b1ee1/download/bgd_poi_educationfacilities_lged.zip",
    "COL_education_sedes.csv": "https://data.humdata.org/dataset/0d2277b0-7198-4778-9027-3d344d8d6db5/resource/3873436e-6f5c-4d2d-b3ad-a07c07a76c87/download/csv_sedessise.csv",
}


def download(name: str, url: str) -> Path:
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / name
    if path.exists() and path.stat().st_size > 0:
        print(f"exists: {path.name} ({path.stat().st_size / 1e6:.1f} MB)")
        return path
    print(f"downloading: {name}")
    response = requests.get(url, timeout=300)
    response.raise_for_status()
    tmp = path.with_suffix(path.suffix + ".part")
    tmp.write_bytes(response.content)
    tmp.replace(path)
    print(f"saved: {path.name} ({path.stat().st_size / 1e6:.1f} MB)")
    return path


def extract(path: Path) -> None:
    if path.suffix.lower() != ".zip":
        return
    target = path.with_suffix("")
    marker = target / ".extracted"
    if marker.exists():
        return
    target.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path) as zf:
        for member in zf.infolist():
            destination = (target / member.filename).resolve()
            if not str(destination).startswith(str(target.resolve())):
                raise RuntimeError(f"Unsafe zip member: {member.filename}")
            zf.extract(member, target)
    marker.write_text("ok\n", encoding="utf-8")


def main() -> None:
    for name, url in FILES.items():
        path = download(name, url)
        extract(path)
    print("Done.")


if __name__ == "__main__":
    main()
