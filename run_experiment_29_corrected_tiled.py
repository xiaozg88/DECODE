# -*- coding: utf-8 -*-
"""Tiled, memory-bounded corrected noded baseline for large Experiment 29 additions.

Why this module exists
----------------------
The canonical runner (``run_experiment_29_corrected_countries.py``) nodes the whole
country Planet+OSM union in a single ``shapely.union_all()`` call and then runs one
global ``gpd.sjoin_nearest()``.  That worked for the 22 small/medium additions, but
India has 10.4M motorable OSM ways plus 0.37M Planet arterials (10.8M originals,
~24M noded segments expected) and the global union exhausts the 16 GB machine
(the first attempt died right after ``originals combined=10,768,876``).

How the tiled version stays equivalent
--------------------------------------
* A tile reads every original whose bbox intersects the tile rectangle and nodes
  only that subset with ``shapely.union_all()``; the union is then clipped to the
  tile rectangle, so the tiles partition the plane exactly.  A piece crossing a
  tile border is split there: this adds nodes, it never removes one.
* Attributes are inherited from the tile-local originals with the same
  ``sjoin_nearest`` + ``(distance, source_priority, original_index)`` lexsort rule.
  This is the canonical answer, not an approximation: for a noded piece the
  nearest original is the one the piece was cut from (distance 0), and every
  original at distance 0 from that piece touches the piece, therefore has a point
  inside the tile rectangle, therefore is in the local candidate set.  The argmin
  is unchanged, so the selected original, its attributes and even its reported
  distance are identical to the global join.
* Over-splitting is travel-time neutral: travel time is linear in segment length
  and both halves of a split inherit the same speed, so multi-source Dijkstra
  distances and every reported access share are unchanged.
* Original ways whose bbox spans more than two tiles (> ~330 km at the default
  1.5 degree tile size) are kept in a separate parquet so the row-group pruning of
  the tile queries stays exact.

Node/edge collapsing runs in DuckDB (spilling to disk), so the graph stage needs
only a few GB of RAM even at ~20M nodes.

Validation
----------
``--outdir`` / ``--cache-suffix`` make it possible to re-run a country that already
has canonical artifacts and compare.  LKA (Sri Lanka) was used; see
``output/experiments/experiment_29_global_expansion/validation_tiled/``.
"""
from __future__ import annotations

import argparse
import gc
import importlib
import time
from pathlib import Path

import duckdb
import geopandas as gpd
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pyogrio
import shapely
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import dijkstra
from scipy.spatial import cKDTree

import prototype_multicountry_access as base
import run_experiment_29_corrected_countries as canon

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'output/experiments/experiment_29_global_expansion/corrected_countries'
TRANSFORMER = canon.TRANSFORMER
DEFAULT_TILE = 1.5
PRUNE_WINDOW = 2          # tiles of slack for the center-tile row-group pruning
OSM_CHUNK = 1_500_000
END_DECIMALS = 7          # same node rounding as the canonical graph builder

ORIGINALS_SCHEMA = pa.schema([
    ('original_index', pa.int32()),
    ('source_priority', pa.int8()),
    ('source', pa.dictionary(pa.int32(), pa.string())),
    ('highway', pa.dictionary(pa.int32(), pa.string())),
    ('surface_class', pa.dictionary(pa.int32(), pa.string())),
    ('width_multiplier', pa.float64()),
    ('tix_c', pa.int32()),
    ('tiy_c', pa.int32()),
    ('minx', pa.float64()), ('miny', pa.float64()),
    ('maxx', pa.float64()), ('maxy', pa.float64()),
    ('geom_wkb', pa.binary()),
])

PIECES_SCHEMA = pa.schema([
    ('tile_ix', pa.int32()), ('tile_iy', pa.int32()),
    ('original_index', pa.int32()),
    ('index_right', pa.int64()),
    ('source', pa.dictionary(pa.int32(), pa.string())),
    ('highway', pa.dictionary(pa.int32(), pa.string())),
    ('surface_class', pa.dictionary(pa.int32(), pa.string())),
    ('width_multiplier', pa.float64()),
    ('source_priority', pa.int8()),
    ('attribute_match_distance_m', pa.float64()),
    ('length_m', pa.float64()),
    ('speed_kmh', pa.float64()),
    ('travel_time_min', pa.float64()),
    ('hazard_intersect', pa.bool_()),
    ('sx', pa.float64()), ('sy', pa.float64()),
    ('ex', pa.float64()), ('ey', pa.float64()),
    ('minx', pa.float64()), ('miny', pa.float64()),
    ('maxx', pa.float64()), ('maxy', pa.float64()),
    ('geom_wkb', pa.binary()),
])

NODED_COLUMNS = [
    'segment_id', 'original_index', 'index_right', 'source', 'highway',
    'surface_class', 'width_multiplier', 'source_priority',
    'attribute_match_distance_m', 'length_m', 'speed_kmh', 'travel_time_min',
    'hazard_intersect',
]


def _stamp(t0, msg):
    print(f'[{time.strftime("%H:%M:%S")}] {msg} (elapsed {time.time() - t0:,.0f}s)', flush=True)


def _duck(tmp=None, memory_limit='6GB', threads=None):
    con = duckdb.connect()
    if tmp:
        Path(tmp).mkdir(parents=True, exist_ok=True)
        con.execute(f"SET temp_directory='{Path(tmp).as_posix()}'")
    con.execute(f"SET memory_limit='{memory_limit}'")
    con.execute(f"SET threads={threads or 2}")
    return con


def _paths(iso, suffix=''):
    local = ROOT / 'data/external/hdx/countries' / iso / 'local_roads'
    tag = iso.lower() + suffix
    return {
        'local': local,
        'meta': local / f'{tag}_originals_meta.json',
        'originals_raw': local / f'{tag}_originals_raw.parquet',
        'originals': local / f'{tag}_originals.parquet',
        'originals_long': local / f'{tag}_originals_long.parquet',
        'tiles': local / f'{tag}_tiles',
        'noded_parquet': local / f'{tag}_noded_segments.parquet',
        'noded_gpkg': local / f'{tag}_noded_segments.gpkg',
        'tmp': local / f'{tag}_duckdb_tmp',
    }


def _country_inputs(iso, iso2):
    planet = ROOT / 'data/external/hdx/roads' / f'heigit_{iso2}_planet_roadsurface_lines.gpkg'
    osm_dir = ROOT / 'data/external/hdx/countries' / iso / 'local_roads' / 'hotosm_roads_gpkg'
    osm = list(osm_dir.rglob('*.gpkg'))
    assert planet.exists(), planet
    assert osm, osm_dir
    return planet, osm[0]


# ---------------------------------------------------------------- originals ---

def _originals_table(df, start_index, tile_size, gx0, gy0):
    """Canonical attribute preparation + bbox/center-tile columns for one chunk."""
    geoms = df.geometry.to_numpy()
    b = shapely.bounds(geoms)
    cx = (b[:, 0] + b[:, 2]) / 2.0
    cy = (b[:, 1] + b[:, 3]) / 2.0
    tix_c = np.floor((cx - gx0) / tile_size).astype('int32')
    tiy_c = np.floor((cy - gy0) / tile_size).astype('int32')
    n = len(df)
    def clean(values):
        s = pd.Series(values, dtype=object)
        return s.where(s.notna(), None).to_numpy()

    cols = {
        'original_index': np.arange(start_index, start_index + n, dtype='int32'),
        'source_priority': df.source_priority.to_numpy(dtype='int8'),
        'source': df.source.to_numpy(),
        'highway': clean(df.highway.to_numpy()),
        'surface_class': clean(df.surface_class.to_numpy()),
        'width_multiplier': df.width_multiplier.to_numpy(dtype='float64'),
        'tix_c': tix_c, 'tiy_c': tiy_c,
        'minx': b[:, 0], 'miny': b[:, 1], 'maxx': b[:, 2], 'maxy': b[:, 3],
        'geom_wkb': shapely.to_wkb(geoms),
    }
    return pa.table(cols, schema=ORIGINALS_SCHEMA)


def _is_long(b, tile_size, gx0, gy0):
    ix0 = np.floor((b[:, 0] - gx0) / tile_size)
    ix1 = np.floor((b[:, 2] - gx0) / tile_size)
    iy0 = np.floor((b[:, 1] - gy0) / tile_size)
    iy1 = np.floor((b[:, 3] - gy0) / tile_size)
    return ((ix1 - ix0) > 1) | ((iy1 - iy0) > 1)


def build_originals(iso, iso2, p, tile_size, force=False):
    if p['originals'].exists() and not force:
        info = pq.ParquetFile(p['originals']).metadata
        return info.num_rows
    planet_p, osm_p = _country_inputs(iso, iso2)
    t0 = time.time()

    # global grid origin from both inputs (planet first, then OSM in file order)
    bbox = [np.inf, np.inf, -np.inf, -np.inf]
    for src in (planet_p, osm_p):
        b = pyogrio.read_info(src)['total_bounds']
        bbox[0] = min(bbox[0], float(b[0])); bbox[1] = min(bbox[1], float(b[1]))
        bbox[2] = max(bbox[2], float(b[2])); bbox[3] = max(bbox[3], float(b[3]))
    gx0 = np.floor(bbox[0] / tile_size) * tile_size
    gy0 = np.floor(bbox[1] / tile_size) * tile_size

    meta = {'bbox': bbox, 'grid': [float(gx0), float(gy0)], 'tile_size': float(tile_size),
            'planet': str(planet_p), 'osm': str(osm_p)}
    raw = pq.ParquetWriter(p['originals_raw'], ORIGINALS_SCHEMA, compression='zstd')
    long_writer = pq.ParquetWriter(p['originals_long'], ORIGINALS_SCHEMA, compression='zstd')
    try:
        planet = gpd.read_file(
            planet_p,
            columns=['osm_tags_highway', 'DL_road_class_2024', 'rw_class', 'geometry'])
        if planet.crs is None:
            planet = planet.set_crs(4326)
        planet = planet[planet.geometry.notna() & ~planet.geometry.is_empty].to_crs(4326).copy()
        planet['source'] = 'planet_arterial'
        planet['highway'] = planet.osm_tags_highway
        planet['surface_class'] = planet.DL_road_class_2024
        planet['width_multiplier'] = planet.rw_class.map(
            lambda x: base.WIDTH_MULT.get(float(x), .8) if pd.notna(x) else .8)
        planet['source_priority'] = 0
        tbl = _originals_table(planet, 0, tile_size, gx0, gy0)
        b = shapely.bounds(planet.geometry.to_numpy())
        mask = _is_long(b, tile_size, gx0, gy0)
        raw.write_table(tbl.filter(pa.array(~mask)))
        long_writer.write_table(tbl.filter(pa.array(mask)))
        n_planet = len(planet)
        meta['n_planet_arterial'] = int(n_planet)
        del planet, tbl, b, mask
        gc.collect()
        _stamp(t0, f'{iso} planet originals={n_planet:,}')

        total = pyogrio.read_info(osm_p)['features']
        written, n_osm = n_planet, 0
        for start in range(0, total, OSM_CHUNK):
            chunk = pyogrio.read_dataframe(
                osm_p, columns=['highway', 'surface'], skip_features=start,
                max_features=min(OSM_CHUNK, total - start))
            if len(chunk) == 0:
                continue
            chunk = chunk[chunk.highway.isin(canon.MOTORABLE) & chunk.geometry.notna()
                          & ~chunk.geometry.is_empty]
            if len(chunk) == 0:
                continue
            if chunk.crs is None:
                chunk = chunk.set_crs(4326)
            chunk = chunk.to_crs(4326).copy()
            chunk['surface_class'] = chunk.surface.map(canon.osm_surface)
            chunk['width_multiplier'] = .8
            chunk['source'] = 'osm_motorable'
            chunk['highway'] = chunk.highway.astype(str)
            chunk['source_priority'] = 1
            tbl = _originals_table(chunk, written, tile_size, gx0, gy0)
            b = shapely.bounds(chunk.geometry.to_numpy())
            mask = _is_long(b, tile_size, gx0, gy0)
            raw.write_table(tbl.filter(pa.array(~mask)))
            long_writer.write_table(tbl.filter(pa.array(mask)))
            written += len(chunk)
            n_osm += len(chunk)
            del chunk, tbl, b, mask
            gc.collect()
            _stamp(t0, f'{iso} osm chunk {start + OSM_CHUNK:,}/{total:,} '
                        f'motorable so far={n_osm:,}')
    finally:
        raw.close()
        long_writer.close()
    meta['n_osm_motorable'] = int(n_osm)
    meta['n_originals'] = int(n_planet + n_osm)
    p['meta'].write_text(
        pd.Series(meta).to_json(indent=2), encoding='utf-8')
    _stamp(t0, f'{iso} originals written={meta["n_originals"]:,}')

    # sort by center tile so the per-tile row-group pruning is effective
    con = _duck(p['tmp'], memory_limit='4GB', threads=4)
    con.execute(
        f"COPY (SELECT * FROM read_parquet('{p['originals_raw'].as_posix()}') "
        f"ORDER BY tiy_c, tix_c) TO '{p['originals'].as_posix()}' "
        f"(FORMAT PARQUET, COMPRESSION ZSTD, ROW_GROUP_SIZE 262144)")
    con.close()
    p['originals_raw'].unlink(missing_ok=True)
    _stamp(t0, f'{iso} originals sorted for tile pruning')
    return meta['n_originals']


# -------------------------------------------------------------------- tiles ---

def _tile_list(p, tile_size):
    meta = pd.read_json(p['meta'], typ='series')
    bbox = meta['bbox']
    gx0, gy0 = meta['grid']
    nx = int(np.floor((bbox[2] - gx0) / tile_size)) + 1
    ny = int(np.floor((bbox[3] - gy0) / tile_size)) + 1
    tiles = []
    for j in range(ny):
        for i in range(nx):
            x0 = gx0 + i * tile_size
            y0 = gy0 + j * tile_size
            tiles.append((i, j, x0, y0, x0 + tile_size, y0 + tile_size))
    return tiles


def _to_arrays(tb):
    return {
        'original_index': tb.column('original_index').to_numpy(),
        'source_priority': tb.column('source_priority').to_numpy(),
        'source': tb.column('source').to_numpy(zero_copy_only=False),
        'highway': tb.column('highway').to_numpy(zero_copy_only=False),
        'surface_class': tb.column('surface_class').to_numpy(zero_copy_only=False),
        'width_multiplier': tb.column('width_multiplier').to_numpy(),
        'wkb': tb.column('geom_wkb').to_numpy(zero_copy_only=False),
    }


def _speed_lookup(values):
    """Vectorised equivalent of ``series.map(lambda x: BASE_SPEED.get(str(x), 35))``."""
    codes, cats = pd.factorize(pd.Series(values).astype(str), use_na_sentinel=False)
    table = np.array([base.BASE_SPEED.get(c, 35) for c in cats], dtype='float64')
    return table[codes]


def _surface_lookup(values):
    codes, cats = pd.factorize(pd.Series(values).astype(str), use_na_sentinel=False)
    table = np.array([base.SURFACE_MULT.get(c, .75) for c in cats], dtype='float64')
    return table[codes]


def _tile_task(task):
    """Node + attribute-inherit one tile (recursively split if the tile is dense).

    The tile rectangle is partitioned into sub-rectangles, so the union of the
    written pieces is exactly the tile: splitting a region only adds extra cut
    points, which are travel-time neutral.
    """
    import geopandas as gpd
    import numpy as np
    import pandas as pd
    import pyarrow as pa
    import pyarrow.parquet as pq
    import shapely
    from shapely.geometry import box as sbox

    i, j, x0, y0, x1, y1 = task['tile']
    W = task['window']
    con = duckdb.connect()
    con.execute("SET threads=1")
    con.execute("SET memory_limit='3GB'")
    sel = ('SELECT original_index, source_priority, source, highway, surface_class, '
           'width_multiplier, geom_wkb FROM read_parquet(?) ')
    q_near = (sel + 'WHERE tix_c BETWEEN ? AND ? AND tiy_c BETWEEN ? AND ? '
                    'AND maxx >= ? AND minx <= ? AND maxy >= ? AND miny <= ?')
    q_long = sel + 'WHERE maxx >= ? AND minx <= ? AND maxy >= ? AND miny <= ?'
    has_long = bool(task.get('long_parquet')) and Path(task['long_parquet']).exists()

    def fetch(ix, iy, bx0, by0, bx1, by1):
        tables = [con.execute(q_near, [task['originals'], ix - W, ix + W, iy - W, iy + W,
                                       bx0, bx1, by0, by1]).fetch_arrow_table()]
        if has_long:
            tables.append(con.execute(q_long, [task['long_parquet'], bx0, bx1, by0, by1])
                          .fetch_arrow_table())
        tb = pa.concat_tables(tables) if len(tables) > 1 else tables[0]
        arr = _to_arrays(tb)
        del tb, tables
        return arr

    def write_empty(idx):
        pq.write_table(pa.table({f.name: pa.array([], type=f.type) for f in PIECES_SCHEMA},
                                schema=PIECES_SCHEMA), f"{task['out']}_{idx}.parquet",
                       compression='zstd')

    def tile_of(bx, by):
        return (int(np.floor((bx - task['grid'][0]) / task['tile_size'])),
                int(np.floor((by - task['grid'][1]) / task['tile_size'])))

    def node_region(bx0, by0, bx1, by1, depth, tag):
        ix, iy = tile_of(bx0, by0)
        arr = fetch(ix, iy, bx0, by0, bx1, by1)
        n_in = len(arr['original_index'])
        if n_in == 0:
            write_empty(tag)
            return 0, 0
        if n_in > task['max_input'] and depth < task['max_depth']:
            mx, my = (bx0 + bx1) / 2, (by0 + by1) / 2
            del arr
            total_in = total_out = 0
            for k, (qx0, qy0, qx1, qy1) in enumerate(((bx0, by0, mx, my), (mx, by0, bx1, my),
                                                      (bx0, my, mx, by1), (mx, my, bx1, by1))):
                child_in, child_out = node_region(qx0, qy0, qx1, qy1, depth + 1, tag + str(k))
                total_in += child_in
                total_out += child_out
            return total_in, total_out
        return _emit(arr, ix, iy, bx0, by0, bx1, by1, tag)

    def _emit(arr, ix, iy, bx0, by0, bx1, by1, tag):
        geoms = shapely.from_wkb(arr['wkb'])
        union = shapely.union_all(geoms)
        parts = list(canon.flatten(union))
        del union
        if not parts:
            write_empty(tag)
            return len(arr['original_index']), 0
        arr_parts = np.empty(len(parts), dtype=object)
        arr_parts[:] = parts
        del parts
        clipped = shapely.intersection(arr_parts, sbox(bx0, by0, bx1, by1))
        pieces = []
        for g in clipped:
            if g is not None and not g.is_empty:
                pieces.extend(canon.flatten(g))
        del clipped, arr_parts
        if not pieces:
            write_empty(tag)
            return len(arr['original_index']), 0

        left = gpd.GeoDataFrame(geometry=pieces, crs=4326).to_crs(3857)
        del pieces
        right = gpd.GeoDataFrame({
            'original_index': arr['original_index'],
            'source': arr['source'],
            'highway': arr['highway'],
            'surface_class': arr['surface_class'],
            'width_multiplier': arr['width_multiplier'],
            'source_priority': arr['source_priority'],
        }, geometry=geoms, crs=4326).to_crs(3857)
        right.index = arr['original_index']
        del geoms
        joined = gpd.sjoin_nearest(left, right, how='left',
                                   distance_col='attribute_match_distance_m')
        del left, right
        joined = joined.reset_index(names='piece_id')
        joined = joined.sort_values(
            ['piece_id', 'attribute_match_distance_m', 'source_priority', 'original_index'],
            kind='mergesort').drop_duplicates('piece_id')
        length_m = joined.geometry.length.to_numpy()
        wgs = joined.geometry.to_crs(4326)
        coords = shapely.get_coordinates(wgs.to_numpy())
        npts = shapely.get_num_coordinates(wgs.to_numpy())
        starts = np.concatenate(([0], np.cumsum(npts[:-1])))
        first = coords[starts]
        last = coords[starts + npts - 1]
        speed = _speed_lookup(joined.highway.to_numpy()) * _surface_lookup(
            joined.surface_class.to_numpy()) * joined.width_multiplier.to_numpy(dtype='float64')
        b = shapely.bounds(wgs.to_numpy())
        tbl = pa.table({
            'tile_ix': np.full(len(joined), ix, dtype='int32'),
            'tile_iy': np.full(len(joined), iy, dtype='int32'),
            'original_index': joined.original_index.to_numpy(dtype='int32'),
            'index_right': joined.index_right.to_numpy(dtype='int64'),
            'source': joined.source.to_numpy(),
            'highway': joined.highway.to_numpy(),
            'surface_class': joined.surface_class.to_numpy(),
            'width_multiplier': joined.width_multiplier.to_numpy(dtype='float64'),
            'source_priority': joined.source_priority.to_numpy(dtype='int8'),
            'attribute_match_distance_m': joined.attribute_match_distance_m.to_numpy(),
            'length_m': length_m,
            'speed_kmh': speed,
            'travel_time_min': length_m / 1000 / speed * 60,
            'hazard_intersect': np.zeros(len(joined), dtype=bool),
            'sx': np.round(first[:, 0], 7), 'sy': np.round(first[:, 1], 7),
            'ex': np.round(last[:, 0], 7), 'ey': np.round(last[:, 1], 7),
            'minx': b[:, 0], 'miny': b[:, 1], 'maxx': b[:, 2], 'maxy': b[:, 3],
            'geom_wkb': shapely.to_wkb(wgs.to_numpy()),
        }, schema=PIECES_SCHEMA)
        pq.write_table(tbl, f"{task['out']}_{tag}.parquet", compression='zstd',
                       row_group_size=262144)
        return len(arr['original_index']), len(joined)

    try:
        n_in, n_pieces = node_region(x0, y0, x1, y1, 0, 'root')
    finally:
        con.close()
    return {'tile': (i, j), 'n_in': n_in, 'n_pieces': n_pieces}


def node_tiles(iso, p, tile_size, workers=4, max_tiles=None, force=False,
               max_input=150_000, max_depth=6):
    tiles = _tile_list(p, tile_size)
    if max_tiles:
        tiles = tiles[:max_tiles]
    tdir = p['tiles']
    tdir.mkdir(parents=True, exist_ok=True)
    if force:
        for f in tdir.glob('tile_*.parquet'):
            f.unlink()
    done_prefix = {f.name.rsplit('_', 1)[0] for f in tdir.glob('tile_*.parquet')}
    todo = [t for t in tiles if f'tile_{t[0]:05d}_{t[1]:05d}' not in done_prefix]
    if not todo:
        n = sum(1 for _ in tdir.glob('tile_*.parquet'))
        return n, len(tiles)
    meta = pd.read_json(p['meta'], typ='series')
    grid = [float(meta['grid'][0]), float(meta['grid'][1])]
    tasks = [{'tile': t, 'originals': str(p['originals']),
              'long_parquet': str(p['originals_long']), 'window': PRUNE_WINDOW,
              'grid': grid, 'tile_size': tile_size, 'max_input': max_input,
              'max_depth': max_depth,
              'out': str(tdir / f'tile_{t[0]:05d}_{t[1]:05d}')} for t in todo]
    t0 = time.time()
    done = 0
    total_pieces = 0
    import multiprocessing as mp
    ctx = mp.get_context('spawn')
    with ctx.Pool(processes=workers, maxtasksperchild=40) as pool:
        for res in pool.imap_unordered(_tile_task, tasks, chunksize=1):
            done += 1
            total_pieces += res['n_pieces']
            if done % 10 == 0 or done == len(tasks):
                _stamp(t0, f'{iso} tiles {done}/{len(tasks)} '
                            f'(last in={res["n_in"]:,} pieces={res["n_pieces"]:,}, '
                            f'total pieces={total_pieces:,})')
    return done + (len(tiles) - len(todo)), len(tiles)


def merge_tiles(iso, p, force=False):
    if p['noded_parquet'].exists() and not force:
        return pq.ParquetFile(p['noded_parquet']).metadata.num_rows
    if force:
        p['noded_parquet'].unlink(missing_ok=True)
    con = _duck(p['tmp'], memory_limit='6GB', threads=4)
    glob = (p['tiles'] / 'tile_*.parquet').as_posix()
    con.execute(
        f"COPY (SELECT row_number() OVER (ORDER BY tile_iy, tile_ix) - 1 AS segment_id, "
        f"original_index, index_right, source, highway, surface_class, width_multiplier, "
        f"source_priority, attribute_match_distance_m, length_m, speed_kmh, travel_time_min, "
        f"hazard_intersect, sx, sy, ex, ey, minx, miny, maxx, maxy, geom_wkb "
        f"FROM read_parquet('{glob}', union_by_name=true)) "
        f"TO '{p['noded_parquet'].as_posix()}' "
        f"(FORMAT PARQUET, COMPRESSION ZSTD, ROW_GROUP_SIZE 500000)")
    con.close()
    return pq.ParquetFile(p['noded_parquet']).metadata.num_rows


def write_gpkg(iso, p, batch=400_000):
    """Optional canonical-format mirror of the tiled noded cache."""
    if p['noded_gpkg'].exists() and p['noded_gpkg'].stat().st_size > 0:
        return p['noded_gpkg']
    con = _duck(p['tmp'], memory_limit='3GB', threads=2)
    reader = con.execute(
        f"SELECT {', '.join(NODED_COLUMNS[1:])}, geom_wkb "
        f"FROM read_parquet('{p['noded_parquet'].as_posix()}')").fetch_record_batch(batch)
    first = True
    for tb in reader:
        df = pd.DataFrame({c: tb.column(c).to_numpy(zero_copy_only=False) for c in NODED_COLUMNS[1:]})
        geom = shapely.from_wkb(tb.column('geom_wkb').to_numpy(zero_copy_only=False))
        g = gpd.GeoDataFrame(df, geometry=geom, crs=4326)
        pyogrio.write_dataframe(g, p['noded_gpkg'], layer='noded_segments', driver='GPKG',
                                append=not first)
        first = False
        del df, geom, g
    con.close()
    return p['noded_gpkg']


# -------------------------------------------------------------------- graph ---

def build_graph(iso, p, tmp, force=False):
    """DuckDB node/edge collapse -> scipy CSR min-weight graph."""
    t0 = time.time()
    nodes_parquet = p['local'] / f'{p["noded_parquet"].stem}_graph_nodes.parquet'
    edges_parquet = p['local'] / f'{p["noded_parquet"].stem}_graph_edges.parquet'
    if force:
        nodes_parquet.unlink(missing_ok=True)
        edges_parquet.unlink(missing_ok=True)
    con = _duck(tmp, memory_limit='5GB', threads=4)
    src = f"read_parquet('{p['noded_parquet'].as_posix()}')"
    if not (nodes_parquet.exists() and edges_parquet.exists()):
        con.execute(f"CREATE TABLE pieces AS SELECT sx, sy, ex, ey, travel_time_min FROM {src}")
        edges_added = con.execute(
            "SELECT count(*) FROM pieces WHERE NOT (sx = ex AND sy = ey)").fetchone()[0]
        con.execute("CREATE TABLE endpoints AS SELECT sx AS x, sy AS y FROM pieces "
                    "UNION SELECT ex, ey FROM pieces")
        n_nodes = con.execute("SELECT count(*) FROM endpoints").fetchone()[0]
        _stamp(t0, f'{iso} graph inputs: nodes={n_nodes:,} edge insertions={edges_added:,}')
        # canonical node keys: 4326 coordinates rounded to 7 decimals (unique endpoints)
        con.execute("CREATE TABLE nodes AS SELECT (row_number() OVER (ORDER BY x, y) - 1)::BIGINT "
                    "AS nid, x, y FROM endpoints")
        con.execute("CREATE TABLE edges AS SELECT a.nid AS u, b.nid AS v, "
                    "min(p.travel_time_min) AS w FROM pieces p "
                    "JOIN nodes a ON a.x = p.sx AND a.y = p.sy "
                    "JOIN nodes b ON b.x = p.ex AND b.y = p.ey "
                    "WHERE NOT (p.sx = p.ex AND p.sy = p.ey) GROUP BY 1, 2")
        n_edges = con.execute("SELECT count(*) FROM edges").fetchone()[0]
        _stamp(t0, f'{iso} collapsed directed pairs={n_edges:,}')
        con.execute(f"COPY (SELECT x, y FROM nodes ORDER BY nid) TO '{nodes_parquet.as_posix()}' "
                    f"(FORMAT PARQUET, COMPRESSION ZSTD)")
        con.execute(f"COPY (SELECT u, v, w FROM edges) TO '{edges_parquet.as_posix()}' "
                    f"(FORMAT PARQUET, COMPRESSION ZSTD)")
        con.execute("DROP TABLE pieces")
        _ = n_edges
    read = _duck(tmp, memory_limit='3GB', threads=2)
    coords = read.execute(
        f"SELECT x, y FROM read_parquet('{nodes_parquet.as_posix()}') ORDER BY x, y"
    ).fetch_arrow_table()
    node_xy = np.column_stack([coords.column('x').to_numpy(), coords.column('y').to_numpy()])
    n_nodes = len(node_xy)
    del coords
    edges_added = read.execute(
        f"SELECT count(*) FROM read_parquet('{p['noded_parquet'].as_posix()}') "
        "WHERE NOT (sx = ex AND sy = ey)").fetchone()[0]
    rows, cols, data = [], [], []
    for tb in read.execute(f"SELECT u, v, w FROM read_parquet('{edges_parquet.as_posix()}')"
                           ).fetch_record_batch(4_000_000):
        rows.append(tb.column('u').to_numpy())
        cols.append(tb.column('v').to_numpy())
        data.append(tb.column('w').to_numpy())
    con.close()
    read.close()
    u = np.concatenate(rows); v = np.concatenate(cols); w = np.concatenate(data)
    del rows, cols, data
    csr = csr_matrix((np.concatenate((w, w)),
                      (np.concatenate((u, v)), np.concatenate((v, u)))),
                     shape=(n_nodes, n_nodes))
    del u, v, w
    gc.collect()
    _stamp(t0, f'CSR graph ready nnz={csr.nnz:,}')
    x3857, y3857 = TRANSFORMER.transform(node_xy[:, 0], node_xy[:, 1])
    tree = cKDTree(np.column_stack((x3857, y3857)))
    del x3857, y3857
    gc.collect()
    _stamp(t0, 'node KD-tree ready')
    return csr, tree, node_xy, n_nodes, int(edges_added)


def access_csr(dist, cells, pop):
    v = dist[cells]
    valid = np.isfinite(v)
    r = {
        'population_total': float(pop.sum()),
        'population_finite': float(pop[valid].sum()),
        'population_unreachable': float(pop[~valid].sum()),
        'mean_travel_reachable_min': float(np.average(v[valid], weights=pop[valid])) if valid.any() else np.nan,
    }
    for t in (30, 60, 120, 240):
        r[f'share_{t}min_pct'] = 100 * pop[valid & (v <= t)].sum() / pop.sum()
    return r


def summarise(iso, iso2, name, p, outdir, noded_segments, force=False):
    out = outdir / iso.lower()
    out.mkdir(parents=True, exist_ok=True)
    summary = out / f'{iso.lower()}_corrected_baseline.csv'
    marker = out / '.complete'
    if marker.exists() and summary.exists() and not force:
        print(iso + ' complete', flush=True)
        return
    t0 = time.time()
    csr, tree, node_xy, n_nodes, edges_added = build_graph(iso, p, p['tmp'], force=force)
    nodes = np.arange(n_nodes)
    xy, xy3857, pop = canon.population(iso)
    _, idx = tree.query(xy3857)
    cells = nodes[idx]
    _stamp(t0, f'population cells={len(cells):,}')
    rows = []
    for service, kind, vals in (('health', 'health', ['hospital', 'clinic']),
                                ('education', 'education', ['school'])):
        fac = canon.load_facilities(iso, kind)
        fac = fac[fac.amenity.astype(str).isin(vals)].copy()
        src, snap = canon.source_nodes(fac, nodes, tree)
        if src:
            dist = dijkstra(csr, directed=False, indices=np.asarray(sorted(src), dtype=np.int32),
                            min_only=True)
        else:
            dist = np.full(n_nodes, np.inf)
        r = {
            'country': name, 'iso3': iso, 'service': service,
            'facility_records': len(fac), 'facility_source_nodes': len(src),
            'median_facility_snap_m': float(np.median(snap[snap <= 1000])) if np.any(snap <= 1000) else np.nan,
            'noded_segments': noded_segments, 'graph_nodes': n_nodes, 'graph_edges': edges_added,
            'noded_cache': str(p['noded_parquet']), **access_csr(dist, cells, pop)}
        rows.append(r)
        _stamp(t0, f'{iso} {service}: facilities={r["facility_records"]:,} sources={len(src):,} '
                    f'60min={r["share_60min_pct"]:.2f}%')
        del fac, dist
        gc.collect()
    pd.DataFrame(rows).to_csv(summary, index=False, encoding='utf-8-sig')
    marker.write_text('ok\n', encoding='utf-8')
    _stamp(t0, f'{iso} corrected baseline COMPLETE')


def process(iso, iso2, name, outdir=OUT, tile_size=DEFAULT_TILE, workers=4,
            suffix='', max_tiles=None, stages=('originals', 'tiles', 'merge', 'summary'),
            force=False, gpkg=False):
    p = _paths(iso, suffix)
    p['local'].mkdir(parents=True, exist_ok=True)
    if 'originals' in stages:
        n = build_originals(iso, iso2, p, tile_size, force=force)
        print(iso + ' originals=' + str(n), flush=True)
    if 'tiles' in stages:
        done, total = node_tiles(iso, p, tile_size, workers=workers, max_tiles=max_tiles,
                                 force=force)
        print(iso + f' tiles done={done}/{total}', flush=True)
    if 'merge' in stages and not max_tiles:
        n = merge_tiles(iso, p, force=force)
        print(iso + ' noded segments=' + str(n), flush=True)
        if gpkg:
            t0 = time.time()
            write_gpkg(iso, p)
            _stamp(t0, f'{iso} noded GPKG written')
    if 'summary' in stages and not max_tiles:
        n = pq.ParquetFile(p['noded_parquet']).metadata.num_rows
        summarise(iso, iso2, name, p, outdir, n, force=force)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--countries', nargs='+', default=['IND'])
    ap.add_argument('--tile-size', type=float, default=DEFAULT_TILE)
    ap.add_argument('--workers', type=int, default=4)
    ap.add_argument('--max-tiles', type=int, default=None)
    ap.add_argument('--suffix', default='')
    ap.add_argument('--outdir', default=str(OUT))
    ap.add_argument('--stages', nargs='+', default=['originals', 'tiles', 'merge', 'summary'])
    ap.add_argument('--force', action='store_true')
    ap.add_argument('--gpkg', action='store_true')
    a = ap.parse_args()
    q = pd.read_csv(ROOT / 'output/experiments/experiment_29_global_expansion/country_sample_and_input_availability.csv')
    names = {r.iso3: (r.iso2, r.country) for _, r in q.iterrows()}
    for iso in a.countries:
        iso2, name = names[iso]
        process(iso, iso2, name, outdir=Path(a.outdir), tile_size=a.tile_size, workers=a.workers,
                suffix=a.suffix, max_tiles=a.max_tiles, stages=a.stages, force=a.force, gpkg=a.gpkg)


if __name__ == '__main__':
    main()
