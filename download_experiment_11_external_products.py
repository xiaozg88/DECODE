# -*- coding: utf-8 -*-
"""Download or document external products used by Experiment 11."""
from __future__ import annotations

import requests
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "data/external/accessibility_products/weiss_2015"
OUT.mkdir(parents=True, exist_ok=True)

WEISS_FILES = {
    "README.txt": "https://ndownloader.figshare.com/files/37847109",
    "metadata.csv": "https://ndownloader.figshare.com/files/37847112",
    "zones.zip": "https://ndownloader.figshare.com/files/15157457",
    # Layer 11: travel time to nearest city with at least 50,000 people.
    "travel_time_to_cities_11.tif": "https://ndownloader.figshare.com/files/14189849",
}
SDG_URL = "https://unstats.un.org/SDGAPI/v1/sdg/Indicator/Data"


def download(url: str, dest: Path) -> None:
    if dest.exists() and dest.stat().st_size > 0:
        print(f"exists: {dest.name} ({dest.stat().st_size / 1e6:.1f} MB)")
        return
    print(f"downloading: {url}")
    with requests.get(url, stream=True, timeout=(30, 600)) as response:
        response.raise_for_status()
        tmp = dest.with_suffix(dest.suffix + ".part")
        with tmp.open("wb") as f:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)
        tmp.replace(dest)
    print(f"saved: {dest.name} ({dest.stat().st_size / 1e6:.1f} MB)")


def download_sdg() -> None:
    response = requests.get(
        SDG_URL,
        params={"indicator": "9.1.1", "pageSize": 100},
        timeout=120,
    )
    response.raise_for_status()
    payload = response.json()
    (OUT / "sdg_9_1_1_global_raw.json").write_text(
        __import__("json").dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"saved SDG records: {len(payload.get('data', []))}")


def main() -> None:
    download_sdg()
    for name, url in WEISS_FILES.items():
        download(url, OUT / name)


if __name__ == "__main__":
    main()
