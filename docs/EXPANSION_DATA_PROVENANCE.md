# Experiment 29 Expansion Data Provenance

Generated: 2026-10-02 from the download/audit logs and the local filesystem.
Machine-readable version: `output/experiments/experiment_29_global_expansion/expansion_data_provenance.csv`.

## Upstream sources

| Role | Source | Access | Local storage |
|---|---|---|---|
| Planet arterial road surface lines | HeiGIT HDX production raw-data API (`heigit_{ISO2}_planet_roadsurface_lines.gpkg`) | per-country URL recorded in `country_sample_and_input_availability.csv` | `data/external/hdx/roads/` |
| Population (2020, 1 km) | WorldPop `Population_Density/Global_2000_2020_1km/2020/{ISO3}/{iso3}_pd_2020_1km.tif` | per-country URL in `country_sample_and_input_availability.csv` | `data/external/hdx/countries/{ISO3}/` |
| Health / education facilities | HOT / HDX `production-raw-data-api` exports (`hotosm_{iso3}_{kind}_facilities_*`) | `facility_gpkg_availability.csv` + `facility_download_log.csv` | `data/external/hdx/countries/{ISO3}/hotosm_*_facilities_*/` |
| Full local road network (23 additions) | HOT / HDX `production-raw-data-api` road archives (`hotosm_{iso3}_roads_*`) | `full_osm_road_availability.csv` + `full_osm_road_download_log.csv` | `data/external/hdx/countries/{ISO3}/local_roads/` |
| Hazard event footprints (7 core countries) | UNOSAT / HDX flood and cyclone extents | URLs in `download_experiment_04_hazards.py` and the provenance CSV | `data/external/hdx/hazards/{ISO3}/`, `.../hazards/multi_events/{ISO3}/` |
| Country sample design | pre-specified stratified 30-country sample | `output/experiments/experiment_29_global_expansion/country_sample_and_input_availability.csv` | `output/experiments/experiment_29_global_expansion/` |

## Storage layout

```
data/external/hdx/roads/                       # Planet arterial road surface lines (30 countries)
data/external/hdx/countries/{ISO3}/            # WorldPop raster, facility exports, local_roads/
data/external/hdx/countries/{ISO3}/local_roads/ # HOT OSM road archive, originals + noded cache, tiles
data/external/hdx/hazards/{ISO3}/              # core-country hazard footprints (7 countries)
data/external/hdx/hazards/multi_events/{ISO3}/ # curated 18-event archive (core countries)
output/experiments/experiment_29_global_expansion/
    arterial_baseline/                        # 23-country arterial-only baseline
    corrected_countries/{iso3}/               # per-country corrected baseline CSV + .complete
    validation_tiled_v2/                      # tiled-vs-canonical validation (LKA, NPL)
    expansion_data_provenance.csv             # this table
```

## Per-country inventory

| ISO3 | Country | Planet (MB) | WorldPop (MB) | Facilities (MB) | OSM roads (MB / features) | Noded cache (MB / segments) |
|---|---|---:|---:|---:|---:|---:|
| PAK | Pakistan | 24.3 | 5.2 | 1.0 | — | — |
| MOZ | Mozambique | 4.1 | 4.3 | 1.3 | — | — |
| BGD | Bangladesh | 8.5 | 0.8 | 7.6 | — | — |
| ETH | Ethiopia | 12.0 | 5.8 | 2.9 | — | — |
| KEN | Kenya | 9.6 | 3.0 | 5.3 | — | — |
| PHL | Philippines | 39.9 | 1.9 | 2.0 | — | — |
| COL | Colombia | 30.4 | 5.9 | 17.4 | — | — |
| NPL | Nepal | 10.6 | 0.9 | 13.9 | 437 / 612,813 | 393 / 1,068,283 |
| LKA | Sri Lanka | 8.4 | 0.4 | 4.5 | 169 / 348,948 | 258 / 905,799 |
| IND | India | 258.0 | 18.1 | 89.8 | 5,631 / 10,706,850 | 8,751 / 31,365,996 |
| IDN | Indonesia | 101.1 | 10.5 | 2.6 | 1,671 / 5,279,610 | 3,778 / 12,957,203 |
| VNM | Viet Nam | 47.4 | 1.9 | 0.7 | 905 / 3,013,643 | 1,942 / 6,667,874 |
| PNG | Papua New Guinea | 2.7 | 2.5 | 3.8 | 71 / 97,882 | 83 / 241,094 |
| KHM | Cambodia | 2.7 | 1.0 | 1.6 | 100 / 231,278 | 158 / 559,225 |
| NGA | Nigeria | 20.0 | 4.8 | 4.3 | 838 / 1,761,800 | 1,462 / 4,933,822 |
| GHA | Ghana | 5.4 | 1.3 | 3.3 | 174 / 388,117 | 269 / 902,155 |
| SEN | Senegal | 3.2 | 1.1 | 2.2 | 195 / 405,699 | 267 / 921,067 |
| RWA | Rwanda | 5.6 | 0.1 | 1.1 | 114 / 173,151 | 138 / 441,085 |
| TZA | Tanzania | 8.9 | 4.7 | 37.9 | 1,388 / 2,125,295 | 1,396 / 4,010,330 |
| ZMB | Zambia | 3.0 | 3.9 | 3.5 | 276 / 390,836 | 328 / 843,289 |
| MLI | Mali | 3.2 | 6.5 | 3.7 | 210 / 357,061 | 315 / 937,154 |
| PER | Peru | 45.2 | 6.9 | 12.1 | 419 / 868,617 | 1,010 / 3,431,587 |
| HND | Honduras | 3.5 | 0.6 | 1.6 | 101 / 198,265 | 158 / 506,037 |
| GTM | Guatemala | 6.7 | 0.6 | 1.6 | 170 / 360,254 | 270 / 895,600 |
| MEX | Mexico | 94.3 | 10.7 | 6.3 | 1,309 / 4,482,041 | 3,183 / 11,448,670 |
| EGY | Egypt | 21.2 | 1.3 | 0.4 | 449 / 1,804,655 | 1,006 / 3,777,671 |
| JOR | Jordan | 5.0 | 0.5 | 0.9 | 85 / 164,764 | 139 / 480,803 |
| GEO | Georgia | 5.8 | 0.5 | 3.0 | 152 / 349,932 | 204 / 685,700 |
| KGZ | Kyrgyzstan | 2.4 | 1.3 | 2.4 | 66 / 138,260 | 88 / 309,670 |
| TUR | Turkey | 67.3 | 5.3 | 3.0 | 895 / 2,494,072 | 1,951 / 6,486,417 |

## Notes

1. Facility exports are the HOT/OSM "osm_gpkg" bundle where available, otherwise the
   points/polygons bundles (`hotosm_{iso3}_{kind}_facilities_{points,polygons}_gpkg`).
2. WorldPop `*_pd_2020_1km.tif` rasters store population **density** (people per km2),
   not counts; see `EXPANSION_DATA_AUDIT.md` and `run_experiment_29_weight_sensitivity.py`.
3. Hazard footprints exist only for the seven core countries; the 23 additions have no
   local event footprints yet (see the audit table).
4. India is the only addition whose noded cache is stored as Parquet (plus a GPKG mirror);
   all other additions use the canonical `*_noded_segments.gpkg`.
