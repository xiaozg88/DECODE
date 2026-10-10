# -*- coding: utf-8 -*-
"""List the WorldPop folder that hosts the expansion ``*_pd_2020_1km.tif`` files."""
from __future__ import annotations

import re

import requests

URLS = [
    'https://data.worldpop.org/GIS/Population_Density/Global_2000_2020_1km/2020/GEO/',
    'https://data.worldpop.org/GIS/Population_Density/Global_2000_2020_1km/2020/',
    'https://data.worldpop.org/GIS/Population/Global_2000_2020_1km/2020/GEO/',
]


def main() -> None:
    for url in URLS:
        try:
            r = requests.get(url, timeout=60)
        except Exception as exc:  # pragma: no cover
            print(f'{url}\n  error: {exc}\n')
            continue
        print(f'{url}\n  status={r.status_code} bytes={len(r.content)}')
        if r.status_code == 200:
            links = re.findall(r'href="([^"]+)"', r.text)
            interesting = [l for l in links if not l.startswith('?') and l not in ('/', '../')]
            for l in interesting[:15]:
                print('   ', l)
        print()


if __name__ == '__main__':
    main()
