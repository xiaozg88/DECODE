# -*- coding: utf-8 -*-
"""Stage 2 helper: fetch the JRC 100-year flood map with parallel HTTP range requests.

The JRC FTP server throttles single connections to a few KB/s, so the 47 MB global
100-year flood map is transferred as N parallel byte ranges and concatenated.
"""
from __future__ import annotations

import concurrent.futures as cf
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent
CACHE = ROOT / 'data/external/jrc_flood'
URL = 'https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/FLOODS/GlobalMaps/floodMapGL_rp100y.zip'
DEST = CACHE / 'floodMapGL_rp100y.zip'
PARTS = CACHE / 'parts'
WORKERS = 16


def size_of(url: str) -> int:
    r = requests.head(url, timeout=60, headers={'User-Agent': 'Mozilla/5.0'})
    return int(r.headers.get('Content-Length', 0))


def fetch_range(args):
    index, start, end, url = args
    dest = PARTS / f'part_{index:03d}'
    if dest.exists() and dest.stat().st_size == end - start + 1:
        return index, dest.stat().st_size
    for attempt in range(4):
        try:
            headers = {'Range': f'bytes={start}-{end}', 'User-Agent': 'Mozilla/5.0'}
            with requests.get(url, headers=headers, stream=True, timeout=(30, 180)) as r:
                if r.status_code not in (200, 206):
                    raise RuntimeError(f'HTTP {r.status_code}')
                with dest.open('wb') as f:
                    for chunk in r.iter_content(chunk_size=1 << 18):
                        if chunk:
                            f.write(chunk)
            if dest.stat().st_size == end - start + 1:
                return index, dest.stat().st_size
        except Exception as exc:
            print(f'  part {index} attempt {attempt + 1}: {type(exc).__name__}', flush=True)
            time.sleep(3 * (attempt + 1))
    return index, dest.stat().st_size if dest.exists() else 0


def main() -> None:
    CACHE.mkdir(parents=True, exist_ok=True)
    PARTS.mkdir(parents=True, exist_ok=True)
    total = size_of(URL)
    if total == 0:
        print('cannot determine size')
        return
    print(f'total {total / 1e6:.1f} MB, {WORKERS} parallel ranges')
    chunk = total // WORKERS + 1
    jobs = [(i, i * chunk, min((i + 1) * chunk - 1, total - 1), URL) for i in range(WORKERS)]
    t0 = time.time()
    with cf.ThreadPoolExecutor(max_workers=WORKERS) as pool:
        results = list(pool.map(fetch_range, jobs))
    got = sum(size for _, size in results)
    print(f'received {got / 1e6:.1f} MB in {time.time() - t0:.0f}s')
    if got < total:
        print('incomplete; rerun to resume missing parts')
        return
    with DEST.open('wb') as out:
        for index in sorted(i for i, _ in results):
            out.write((PARTS / f'part_{index:03d}').read_bytes())
    print(f'wrote {DEST} ({DEST.stat().st_size / 1e6:.1f} MB)')


if __name__ == '__main__':
    main()
