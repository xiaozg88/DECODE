# -*- coding: utf-8 -*-
"""Download curated historical flood footprints for Experiment 4.

The archive keeps file sizes moderate while covering distinct years/events.
Existing single-event footprints from ``data/external/hdx/hazards`` are reused
as the ``current`` event and are not downloaded again.
"""
from __future__ import annotations

import zipfile
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "data/external/hdx/hazards/multi_events"

EVENTS = {
    "PAK": {
        "flood_2022_viirs": "https://data.humdata.org/dataset/f685e623-a539-4af0-92ff-19b737ec95b3/resource/fa89ec39-8dd0-4abe-b97e-0a3d9e9627a5/download/viirs_20220701_20220831_floodextent_pak.zip",
        "flood_2023_07": "https://unosat.org/static/unosat_filesystem/3649/FL20230729PAK_SHP.zip",
        "flood_2024_08_early": "https://unosat.org/static/unosat_filesystem/3911/FL20240804PAK_SHP.zip",
    },
    "MOZ": {
        "cyclone_2022_01": "https://unosat-maps.web.cern.ch/MZ/TC20220124MOZ/TC20220124MOZ_SHP.zip",
        "cyclone_2024_03": "https://unosat.org/static/unosat_filesystem/3811/TC20240313MOZ_shp.zip",
    },
    "BGD": {
        "flood_2018_teknaf": "https://unosat-maps.web.cern.ch/unosat-maps/BD/FL20180518BGD/FL20180518BGD_SHP.zip",
    },
    "ETH": {
        "flood_2018_05": "https://data.humdata.org/dataset/74f5d67a-75e6-4d00-bb1e-8342a166aa3b/resource/d5ee1331-ea91-4d24-8fbe-cf9be1cab31a/download/st20180501_somali_flood_water.zip",
    },
    "KEN": {
        "flood_2019_11": "https://unosat-maps.web.cern.ch/unosat-maps/KE/FL20191031KEN/FL20191031KEN_SHP.zip",
        "flood_2023_03": "https://unosat.org/static/unosat_filesystem/3547/FL20230321KEN_SHP.zip",
    },
    "PHL": {
        "flood_2021_04": "https://unosat-maps.web.cern.ch/unosat-maps/PH/FL20220412PHL/FL20220412PHL_SHP.zip",
        "typhoon_2022_10": "https://unosat.org/static/unosat_filesystem/3432/TC20221028PHL_SHP.zip",
    },
}


def download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 0:
        print(f"exists: {dest.relative_to(ROOT)} ({dest.stat().st_size / 1e6:.1f} MB)")
        return
    print(f"downloading: {url}")
    with requests.get(url, stream=True, timeout=300) as response:
        response.raise_for_status()
        tmp = dest.with_suffix(dest.suffix + ".part")
        with tmp.open("wb") as f:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)
        tmp.replace(dest)
    print(f"saved: {dest.relative_to(ROOT)} ({dest.stat().st_size / 1e6:.1f} MB)")


def extract(zip_path: Path) -> None:
    target = zip_path.with_suffix("")
    marker = target / ".extracted"
    if marker.exists():
        return
    target.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as zf:
        for member in zf.infolist():
            # Archives are public data; reject absolute paths and parent traversal.
            destination = (target / member.filename).resolve()
            if not str(destination).startswith(str(target.resolve())):
                raise RuntimeError(f"Unsafe zip member: {member.filename}")
            zf.extract(member, target)
    marker.write_text("ok\n", encoding="utf-8")
    print(f"extracted: {target.relative_to(ROOT)}")


def main() -> None:
    for iso, events in EVENTS.items():
        for event_id, url in events.items():
            suffix = Path(url).suffix.lower() or ".zip"
            zip_path = OUT / iso / event_id / f"hazard{suffix}"
            download(url, zip_path)
            if suffix == ".zip":
                extract(zip_path)
    print("Done.")


if __name__ == "__main__":
    main()
