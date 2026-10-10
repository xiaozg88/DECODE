# -*- coding: utf-8 -*-
"""下载 CPAS/Data for Children 100 m 同服务卫生设施旅行时间栅格。

资源来自 HDX package_show，实际对象位于 S3 eidf.ac.uk。只下载 motorised
版本，与本文机动车路网口径对齐。
"""
import argparse
import hashlib
import os
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'data/external/accessibility_products/cpas'
OUT.mkdir(parents=True, exist_ok=True)

RESOURCES = {
    'KEN': {
        'name': 'kenya-motorised-travel-time-in-seconds-to-nearest-health-centre',
        'resource': 'service-area-kenya-motorised.tif',
        'url': ('https://s3.eidf.ac.uk/eidf158-motorised-travel-time-maps/'
                'service_area_KE_mot.tif'),
        'size': 606877914,
        'sha256': None,
    },
    'ETH': {
        'name': 'ethiopia-motorised-travel-time-in-seconds-to-nearest-health-centre',
        'resource': 'service-area-ethiopia-motorised.tif',
        'url': ('https://s3.eidf.ac.uk/eidf158-motorised-travel-time-maps/'
                'service_area_Ethiopia_motorised.tif'),
        'size': 1391945996,
        'sha256': None,
    },
    'MOZ': {
        'name': 'mozambique-motorised-travel-time-in-seconds-to-nearest-health-centre',
        'resource': 'service-area-mozambique-motorised.tif',
        'url': ('https://s3.eidf.ac.uk/eidf158-motorised-travel-time-maps/'
                'service_area_Mozambique_mot.tif'),
        'size': 1416563900,
        'sha256': None,
    },
}


def download(url, dest, size, resume=True):
    if dest.exists() and dest.stat().st_size >= size:
        print(f'exists complete: {dest} ({dest.stat().st_size/1e6:.1f} MB)')
        return
    start = dest.stat().st_size if (resume and dest.exists()) else 0
    chunk_size = 32 * 1024 * 1024
    with dest.open('ab') as f:
        pos = start
        while pos < size:
            end = min(pos + chunk_size - 1, size - 1)
            got = False
            for attempt in range(6):
                try:
                    r = requests.get(
                        url,
                        headers={'Range': f'bytes={pos}-{end}'},
                        stream=True,
                        timeout=(30, 120),
                    )
                    if r.status_code not in (200, 206):
                        raise RuntimeError(f'HTTP {r.status_code}')
                    data = bytearray()
                    for part in r.iter_content(1024 * 1024):
                        if part:
                            data.extend(part)
                            if len(data) > chunk_size:
                                break
                    expected = end - pos + 1
                    if len(data) != expected:
                        raise RuntimeError(
                            f'short chunk {len(data)}/{expected}')
                    f.write(data)
                    pos = end + 1
                    got = True
                    print(f'  {dest.name}: {pos/1e6:.1f}/{size/1e6:.1f} MB',
                          flush=True)
                    break
                except Exception as e:
                    print(f'  retry {attempt+1}/6 at {pos/1e6:.1f} MB: {e}',
                          flush=True)
                    time.sleep(2 * (attempt + 1))
            if not got:
                raise RuntimeError(f'failed to download chunk at {pos}')
    print(f'saved: {dest} ({dest.stat().st_size/1e6:.1f} MB)')


def sha256_of(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--countries', default='KEN,ETH,MOZ')
    ap.add_argument('--checksum', action='store_true')
    args = ap.parse_args()
    for iso in [x.strip().upper() for x in args.countries.split(',')]:
        if iso not in RESOURCES:
            print(f'skip unknown: {iso}')
            continue
        info = RESOURCES[iso]
        dest = OUT / info['resource']
        print(f'\n[{iso}] {info["name"]}\n  {info["url"]}')
        download(info['url'], dest, info['size'])
        if args.checksum:
            print(f'  sha256: {sha256_of(dest)}')


if __name__ == '__main__':
    main()
