# -*- coding: utf-8 -*-
"""Record Experiment 29 data provenance: source URL/API, local storage, derived outputs.

Combines the download/audit logs in ``output/experiments/experiment_29_global_expansion``
with the local filesystem (sizes, mtimes, feature counts) and writes

* ``output/experiments/experiment_29_global_expansion/expansion_data_provenance.csv``
* ``EXPANSION_DATA_PROVENANCE.md``
"""
from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

import pandas as pd
import pyogrio

from download_experiment_04_hazards import EVENTS as HAZARD_EVENTS

ROOT = Path(__file__).resolve().parent
EXP = ROOT / 'output/experiments/experiment_29_global_expansion'
COUNTRY_DIR = ROOT / 'data/external/hdx/countries'
ROADS = ROOT / 'data/external/hdx/roads'
HAZARDS = ROOT / 'data/external/hdx/hazards'
CSV_OUT = EXP / 'expansion_data_provenance.csv'
MD_OUT = ROOT / 'EXPANSION_DATA_PROVENANCE.md'
ADDITIONS = ['EGY', 'GEO', 'GHA', 'GTM', 'HND', 'IDN', 'IND', 'JOR', 'KGZ', 'KHM', 'LKA',
             'MEX', 'MLI', 'NGA', 'NPL', 'PER', 'PNG', 'RWA', 'SEN', 'TUR', 'TZA', 'VNM', 'ZMB']


def _info(path: Path) -> tuple[int, int, int | None]:
    """(bytes, mtime epoch, feature count or None)."""
    if not path.exists():
        return 0, 0, None
    st = path.stat()
    feats = None
    if path.suffix.lower() in {'.gpkg', '.parquet'}:
        try:
            if path.suffix.lower() == '.gpkg':
                feats = int(pyogrio.read_info(path)['features'])
            else:
                import pyarrow.parquet as pq
                feats = pq.ParquetFile(path).metadata.num_rows
        except Exception:
            feats = None
    return st.st_size, int(st.st_mtime), feats


def _first(pattern_root: Path, pattern: str = '*.gpkg') -> Path | None:
    hits = sorted(pattern_root.rglob(pattern)) if pattern_root.exists() else []
    return hits[0] if hits else None


def main() -> None:
    sample = pd.read_csv(EXP / 'country_sample_and_input_availability.csv')
    osm_avail = pd.read_csv(EXP / 'full_osm_road_availability.csv').set_index('iso3')
    osm_log = pd.read_csv(EXP / 'full_osm_road_download_log.csv')
    osm_log = osm_log.drop_duplicates('iso3').set_index('iso3')
    fac_avail = pd.read_csv(EXP / 'facility_gpkg_availability.csv')
    fac_avail_map = {(r.iso3, r.facility_type.replace('_facilities', '')): r for _, r in fac_avail.iterrows()}
    try:
        counterpart = pd.read_csv(EXP / 'facility_counterpart_download_log.csv')
        counterpart_map = {}
        for _, r in counterpart.iterrows():
            counterpart_map.setdefault(r.iso3, []).append(str(r.get('key', '')))
    except FileNotFoundError:
        counterpart_map = {}
    RAW_API = 'https://production-raw-data-api.s3.amazonaws.com/'
    rows = []
    for _, r in sample.iterrows():
        iso, iso2 = r.iso3, r.iso2
        cdir = COUNTRY_DIR / iso
        planet = ROADS / f'heigit_{iso2}_planet_roadsurface_lines.gpkg'
        p_bytes, p_mtime, p_feats = _info(planet)
        worldpop = cdir / f'{iso.lower()}_pd_2020_1km.tif'
        w_bytes, w_mtime, _ = _info(worldpop)
        rec = {
            'iso3': iso, 'country': r.country, 'iso2': iso2, 'region': r.region,
            'income_group': r.income_group, 'hazard_profile': r.hazard_profile,
            'sample_status': r.sample_status,
            'planet_source': 'HeiGIT HDX Planet road surface lines (production API)',
            'planet_url': r.road_url, 'planet_http_status': r.road_http_status,
            'planet_local_path': str(planet.relative_to(ROOT)) if planet.exists() else '',
            'planet_bytes': p_bytes, 'planet_features': p_feats,
            'planet_last_modified_utc': r.road_last_modified,
            'worldpop_source': 'WorldPop 2020 1 km population density (people per km2)',
            'worldpop_url': r.population_url, 'worldpop_http_status': r.population_http_status,
            'worldpop_local_path': str(worldpop.relative_to(ROOT)) if worldpop.exists() else '',
            'worldpop_bytes': w_bytes, 'worldpop_last_modified_utc': r.population_last_modified,
            'hazard_events_local': ';'.join(sorted(
                [d.name for d in (HAZARDS / iso / 'extracted').iterdir() if d.is_dir()]
                if (HAZARDS / iso / 'extracted').exists() else []) +
                sorted([d.name for d in (HAZARDS / 'multi_events' / iso).iterdir() if d.is_dir()]
                       if (HAZARDS / 'multi_events' / iso).exists() else [])),
            'hazard_event_urls': ';'.join(HAZARD_EVENTS.get(iso, {}).values()),
        }
        for kind in ('health', 'education'):
            key = (iso, kind)
            avail = fac_avail_map.get(key)
            archive = cdir / f'hotosm_{iso.lower()}_{kind}_facilities_osm_gpkg.zip'
            gpkg = _first(cdir / f'hotosm_{iso.lower()}_{kind}_facilities_osm_gpkg')
            if gpkg is None:
                gpkg = _first(cdir / f'hotosm_{iso.lower()}_{kind}_facilities_points_gpkg')
            if gpkg is None:
                gpkg = _first(cdir / f'hotosm_{iso.lower()}_{kind}_facilities_polygons_gpkg')
            g_bytes, g_mtime, g_feats = _info(gpkg) if gpkg else (0, 0, None)
            rec.update({
                f'{kind}_export_key': avail.chosen_key if avail is not None else '',
                f'{kind}_export_url': (RAW_API + avail.chosen_key) if avail is not None else '',
                f'{kind}_export_last_modified': avail.chosen_last_modified if avail is not None else '',
                f'{kind}_archive_path': str(archive.relative_to(ROOT)) if archive.exists() else '',
                f'{kind}_archive_bytes': archive.stat().st_size if archive.exists() else 0,
                f'{kind}_gpkg_path': str(gpkg.relative_to(ROOT)) if gpkg else '',
                f'{kind}_gpkg_bytes': g_bytes, f'{kind}_features': g_feats,
            })
        if iso in ADDITIONS:
            key = osm_avail.loc[iso]
            if iso in osm_log.index:
                log = osm_log.loc[iso]
                url = log.url
                archive = Path(log.archive)
                log_status = 'logged'
            else:
                log = None
                url = RAW_API + key.chosen_key
                archive = cdir / 'local_roads' / 'hotosm_roads_gpkg.zip'
                log_status = 'reconstructed_from_availability_key'
            osm_gpkg = _first(cdir / 'local_roads' / 'hotosm_roads_gpkg')
            o_bytes, _, o_feats = _info(osm_gpkg) if osm_gpkg else (0, 0, None)
            a_bytes, _, _ = _info(archive) if archive.exists() else (0, 0, None)
            rec.update({
                'osm_roads_export_key': key.chosen_key,
                'osm_roads_url': url,
                'osm_roads_provenance_status': log_status,
                'osm_roads_last_modified': key.chosen_last_modified,
                'osm_roads_archive_path': str(archive.relative_to(ROOT)) if archive.exists() else '',
                'osm_roads_archive_bytes': a_bytes or int(key.chosen_size_bytes),
                'osm_roads_gpkg_path': str(osm_gpkg.relative_to(ROOT)) if osm_gpkg else '',
                'osm_roads_gpkg_bytes': o_bytes, 'osm_roads_features': o_feats,
                'counterpart_facility_exports': ';'.join(counterpart_map.get(iso, [])),
            })
            base = EXP / 'corrected_countries' / iso.lower()
            csv = base / f'{iso.lower()}_corrected_baseline.csv'
            parquet = cdir / 'local_roads' / f'{iso.lower()}_noded_segments.parquet'
            gpkg_noded = cdir / 'local_roads' / f'{iso.lower()}_noded_segments.gpkg'
            chosen = gpkg_noded if gpkg_noded.exists() else parquet
            c_bytes, c_mtime, c_feats = _info(chosen)
            rec.update({
                'noded_cache_path': str(chosen.relative_to(ROOT)) if chosen.exists() else '',
                'noded_cache_bytes': c_bytes, 'noded_segments': c_feats,
                'baseline_csv': str(csv.relative_to(ROOT)) if csv.exists() else '',
                'baseline_written_utc': datetime.utcfromtimestamp(csv.stat().st_mtime).strftime('%Y-%m-%d %H:%M')
                if csv.exists() else '',
                'originals_parquet': str((cdir / 'local_roads' / f'{iso.lower()}_originals.parquet').relative_to(ROOT))
                if (cdir / 'local_roads' / f'{iso.lower()}_originals.parquet').exists() else '',
            })
        rows.append(rec)
    df = pd.DataFrame(rows)
    CSV_OUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(CSV_OUT, index=False, encoding='utf-8-sig')

    lines = [
        '# Experiment 29 Expansion Data Provenance',
        '',
        f'Generated: {datetime.now().strftime("%Y-%m-%d")} from the download/audit logs and the local filesystem.',
        'Machine-readable version: `output/experiments/experiment_29_global_expansion/expansion_data_provenance.csv`.',
        '',
        '## Upstream sources',
        '',
        '| Role | Source | Access | Local storage |',
        '|---|---|---|---|',
        '| Planet arterial road surface lines | HeiGIT HDX production raw-data API (`heigit_{ISO2}_planet_roadsurface_lines.gpkg`) | per-country URL recorded in `country_sample_and_input_availability.csv` | `data/external/hdx/roads/` |',
        '| Population (2020, 1 km) | WorldPop `Population_Density/Global_2000_2020_1km/2020/{ISO3}/{iso3}_pd_2020_1km.tif` | per-country URL in `country_sample_and_input_availability.csv` | `data/external/hdx/countries/{ISO3}/` |',
        '| Health / education facilities | HOT / HDX `production-raw-data-api` exports (`hotosm_{iso3}_{kind}_facilities_*`) | `facility_gpkg_availability.csv` + `facility_download_log.csv` | `data/external/hdx/countries/{ISO3}/hotosm_*_facilities_*/` |',
        '| Full local road network (23 additions) | HOT / HDX `production-raw-data-api` road archives (`hotosm_{iso3}_roads_*`) | `full_osm_road_availability.csv` + `full_osm_road_download_log.csv` | `data/external/hdx/countries/{ISO3}/local_roads/` |',
        '| Hazard event footprints (7 core countries) | UNOSAT / HDX flood and cyclone extents | URLs in `download_experiment_04_hazards.py` and the provenance CSV | `data/external/hdx/hazards/{ISO3}/`, `.../hazards/multi_events/{ISO3}/` |',
        '| Country sample design | pre-specified stratified 30-country sample | `output/experiments/experiment_29_global_expansion/country_sample_and_input_availability.csv` | `output/experiments/experiment_29_global_expansion/` |',
        '',
        '## Storage layout',
        '',
        '```',
        'data/external/hdx/roads/                       # Planet arterial road surface lines (30 countries)',
        'data/external/hdx/countries/{ISO3}/            # WorldPop raster, facility exports, local_roads/',
        'data/external/hdx/countries/{ISO3}/local_roads/ # HOT OSM road archive, originals + noded cache, tiles',
        'data/external/hdx/hazards/{ISO3}/              # core-country hazard footprints (7 countries)',
        'data/external/hdx/hazards/multi_events/{ISO3}/ # curated 18-event archive (core countries)',
        'output/experiments/experiment_29_global_expansion/',
        '    arterial_baseline/                        # 23-country arterial-only baseline',
        '    corrected_countries/{iso3}/               # per-country corrected baseline CSV + .complete',
        '    validation_tiled_v2/                      # tiled-vs-canonical validation (LKA, NPL)',
        '    expansion_data_provenance.csv             # this table',
        '```',
        '',
        '## Per-country inventory',
        '',
        '| ISO3 | Country | Planet (MB) | WorldPop (MB) | Facilities (MB) | OSM roads (MB / features) | Noded cache (MB / segments) |',
        '|---|---|---:|---:|---:|---:|---:|',
    ]
    for _, r in df.iterrows():
        fac_mb = (r.get('health_gpkg_bytes', 0) + r.get('education_gpkg_bytes', 0)) / 1e6
        osm_mb = r.get('osm_roads_gpkg_bytes')
        osm_txt = (f'{osm_mb/1e6:,.0f} / {r.get("osm_roads_features"):,.0f}'
                   if pd.notna(osm_mb) and osm_mb else '—')
        noded = r.get('noded_cache_bytes')
        noded_txt = (f'{noded/1e6:,.0f} / {r.get("noded_segments"):,.0f}'
                     if pd.notna(noded) and noded else '—')
        lines.append(f'| {r.iso3} | {r.country} | {r.planet_bytes/1e6:,.1f} | {r.worldpop_bytes/1e6:,.1f} | '
                     f'{fac_mb:,.1f} | {osm_txt} | {noded_txt} |')
    lines += [
        '',
        '## Notes',
        '',
        '1. Facility exports are the HOT/OSM "osm_gpkg" bundle where available, otherwise the',
        '   points/polygons bundles (`hotosm_{iso3}_{kind}_facilities_{points,polygons}_gpkg`).',
        '2. WorldPop `*_pd_2020_1km.tif` rasters store population **density** (people per km2),',
        '   not counts; see `EXPANSION_DATA_AUDIT.md` and `run_experiment_29_weight_sensitivity.py`.',
        '3. Hazard footprints exist only for the seven core countries; the 23 additions have no',
        '   local event footprints yet (see the audit table).',
        '4. India is the only addition whose noded cache is stored as Parquet (plus a GPKG mirror);',
        '   all other additions use the canonical `*_noded_segments.gpkg`.',
        '',
    ]
    MD_OUT.write_text('\n'.join(lines), encoding='utf-8')
    print(f'wrote {CSV_OUT} ({len(df)} countries) and {MD_OUT}')


if __name__ == '__main__':
    main()
