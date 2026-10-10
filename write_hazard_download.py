from pathlib import Path
text = r'''# -*- coding: utf-8 -*-
"""Download one recent flood/hazard footprint for each prototype country."""
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parent
BASE = ROOT / "data/external/hdx/hazards"

URLS = {
    "PAK": "https://data.humdata.org/dataset/28f19981-ac0c-4799-9576-6a742fc546c3/resource/5b3d27f8-9a50-41d1-8b28-bc98488ca972/download/pak_wfpadam_flood_20250911.zip",
    "MOZ": "https://data.humdata.org/dataset/0620c9f6-565d-4530-ac3b-2f5384ef7be0/resource/16d8002e-32ed-4dba-81bc-ac14b6723959/download/moz_wfpadam_flood_20250318.zip",
    "BGD": "https://unosat-maps.web.cern.ch/unosat-maps/BD/FL20180619BGD/FL20180619BGD_SHP.zip",
    "ETH": "https://unosat.org/static/unosat_filesystem/3550/FL20230327SOM_SHP.zip",
    "KEN": "https://unosat-maps.web.cern.ch/unosat-maps/KE/FL20180508KEN/FL20180508KEN_shp.zip",
    "COL": "https://unosat.org/static/unosat_filesystem/4030/FL20241112COL_SHP.zip",
    "PHL": "https://data.humdata.org/dataset/e3acf178-25fb-4972-a026-a387b52e1761/resource/f986573f-65a8-462a-8867-e7a0361307a1/download/20260712_1748_fld_rcm_shp.zip",
}


def download(url: str, dest: Path):
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 0:
        print(f"exists: {dest.name}")
        return
    print(f"downloading: {url}")
    with requests.get(url, stream=True, timeout=180) as r:
        r.raise_for_status()
        tmp = dest.with_suffix(dest.suffix + ".part")
        with tmp.open("wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)
        tmp.replace(dest)
    print(f"saved: {dest.name} ({dest.stat().st_size / 1_000_000:.1f} MB)")


for iso, url in URLS.items():
    suffix = Path(url).suffix or ".zip"
    download(url, BASE / iso / f"hazard{suffix}")

print("Done.")
'''
Path('download_multicountry_hazards.py').write_text(text, encoding='utf-8')
print('written download_multicountry_hazards.py')