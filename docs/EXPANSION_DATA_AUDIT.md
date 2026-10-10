# Experiment 29 Expansion Data Audit

Audit date: 2026-10-02. Scope: the 30-country expansion sample (23 additions plus the
seven core countries) — inputs, derived corrected baselines, and the shared modelling
assumptions that the expansion inherits from the core pipeline.

Machine-readable findings: `output/experiments/experiment_29_global_expansion/expansion_data_audit.csv`.
Reproduction: `python audit_experiment_29_data.py` (writes `expansion_data_audit.csv`
and `expansion_data_audit_report.txt`).

## 1. Findings summary

| ID | Severity | Finding | Evidence | Status |
|---|---|---|---|---|
| A1 | High | WorldPop `*_pd_2020_1km.tif` rasters store population **density per km2**, but the pipeline uses the raw cell values as population **counts**. Absolute populations are inflated by 1.16–1.82x and population weights are systematically distorted (more so at high latitude). | Companion count rasters (`*_ppp_2020_1km_Aggregated.tif`) reproduce `sum(density x cell_area)` to within 0.4% in 12/12 sampled countries (`worldpop_units_check.txt`) | Quantified with `run_experiment_29_weight_sensitivity.py`; corrected totals + shares in `weight_length_sensitivity.csv` |
| A2 | High (high-latitude countries) | Segment lengths are computed in EPSG:3857, which inflates ground distance by 1/cos(latitude): 1.005 (Rwanda) up to 1.35 (Georgia). Travel times are therefore overstated, which understates short-threshold access. | Sampled 20k segments per addition (`length_metric` rows in the audit CSV) | Quantified in `weight_length_sensitivity.csv` (geodesic variants) |
| A3 | Medium | The 23 additions had **no hazard event footprints**; only the seven core countries do. | `hazard` section of the audit CSV: 23/23 `MISSING` | Partly closed: uniform `no_unpaved` / `unknown_as_unpaved` stress tests for all 23 (`weight_length_sensitivity.csv`) plus an observed-event pilot for VNM 2020 (national cyclone/flood), IDN 2025 (Aceh) and NGA 2022 (Yobe) — 19 additions still need footprint sourcing |
| A4 | Medium | The full-road download log covers only 9 of the 23 additions (`download_experiment_29_full_osm_roads.py` rewrote the log for later runs); the other 14 URLs had to be reconstructed from the availability key. | `full_osm_road_download_log.csv` vs `full_osm_road_availability.csv` | Reconstructed URLs recorded in `expansion_data_provenance.csv` (`osm_roads_provenance_status`) |
| A5 | Low | Cache-format heterogeneity: India's noded cache is Parquet (+ GPKG mirror), the other 22 are GPKG only. | `derived` section of the audit CSV | Documented in `EXPANSION_DATA_PROVENANCE.md` |
| A6 | Low | Facility exports are dominated by non-target amenities in several countries, so export size does not reflect usable facility count: Turkey keeps 4 198 of ~61 000 health records (6.8%, 22 994 pharmacies), Viet Nam 2 157 (12.9%), Peru 3 434 (15.1%), Georgia 597 (17.0%). | `facilities` rows in the audit CSV | Expected (the model keeps hospital/clinic and school only), but health-facility completeness is country-dependent; interpret cross-country facility counts with care |
| A7 | Info | Even after the units fix, some country totals differ from UN WPP 2020: Jordan 0.70x, Kyrgyzstan 0.87x, Ethiopia 0.90x, Colombia 1.25x, Philippines 1.18x, Nepal 1.38x. | `area_weighted_sum_over_un_wpp` rows | Upstream WorldPop vintage/mask characteristics; do not quote absolute population from this layer without a second source |
| A8 | Info | All internal consistency checks pass for the 46 baseline rows: access shares monotonically increase with the threshold, population partitions close, `graph_edges <= noded_segments`, facility source nodes <= facility records, median facility snap <= 1 km. | `consistency` rows in the audit CSV | — |
| A9 | Info | Corrected access is *below* arterial-only access in PNG (-24.7 pp), Mali (-10.8 pp), Zambia (-7.7 pp), Nepal (-6.6 pp), Tanzania (-2.2 pp) and Peru (-1.8 pp). | `arterial_vs_corrected_expansion.csv` | Expected behaviour of the corrected model (local roads carry slower/`unknown` surfaces); always report both |
| A10 | Info | India noded cache health check: 31 365 996 segments, 4.59 million km, 100% of segments inherit attributes at distance 0, Planet share 22.1% of length, unknown surface 70.1% of length. | `python inspect_india_noded_cache.py` | — |

## 2. What was checked and what it means

**Inputs (30 countries).** Planet arterial lines, WorldPop 2020 1 km rasters, HOT health and
education facility exports and (for the 23 additions) full HOT OSM road archives are present for
every country, with per-country URLs and local paths in `expansion_data_provenance.csv`.

**Derived baselines (23 additions).** Every addition has a two-row baseline CSV, a `.complete`
marker and a noded cache; segment counts range from 241 094 (PNG) to 31 365 996 (India).

**Population layer (A1).** `*_pd_2020_1km.tif` values are densities. Summing them (as the pipeline
does) inflates the country total by a factor equal to `1 / cell_area_km2`, which grows with
latitude (0.63 km2 at 42 deg N, 0.85 km2 at 5 deg N). Shares move only slightly because the factor
varies smoothly inside a country, but absolute population, `population_unreachable` and any
downstream absolute loss figures are wrong by that factor.

**Length metric (A2).** `length_m` comes from `GeoDataFrame.to_crs(3857).length`. The expansion
sample spans 42 deg N (Georgia, Kyrgyzstan) to 12 deg S (Zambia), so the bias ranges from
negligible to +35%. This is inherited from the core pipeline; the expansion makes it visible
because it added high-latitude countries.

**Hazards (A3).** The core multi-event archive covers PAK, MOZ, BGD, ETH, KEN, PHL. No event
footprints had been sourced for the additions. `probe_hdx_hazards.py` shows UNOSAT flood extents
exist for most additions (e.g. VNM 2020, NGA 2022, IND 2015 Chennai, IDN 2025, PER 2023), so the
gap is sourcing effort rather than data availability.

**Provenance hygiene (A4).** Log files written with a fixed filename per run were overwritten when
later runs covered different country sets (the same failure mode previously hit
`corrected_expansion_baseline_summary.csv`, fixed by `build_corrected_expansion_summary.py`).

## 3. Recommended fixes

1. Replace `pop.sum()` population weights with area-weighted counts
   (`value x cell_area_km2`) in `prototype_multicountry_access.load_population` and
   `run_experiment_29_corrected_countries.population`; the correction is a one-line change but it
   changes every published absolute population and slightly changes shares, so the core
   seven-country results need a documented re-run rather than a silent patch.
2. Compute `length_m` geodesically (or in an equal-area/local projection) instead of EPSG:3857.
   If the core results are to stay comparable, report both the canonical and the geodesic variant.
3. Keep log files append-only (or keyed by run date) so provenance survives later runs.
4. Source event footprints for the additions from UNOSAT/HDX with the query helper, and extend
   `run_experiment_29_hazard_pilot.py` beyond the current four-country pilot.

## 4. Corrected variants produced by this audit

| Artifact | Content |
|---|---|
| `output/experiments/experiment_29_global_expansion/weight_length_sensitivity.csv` | 23 additions x 2 services x 6 variants: density vs counts weights, Mercator vs geodesic lengths, plus `no_unpaved` and `unknown_as_unpaved` stress tests |
| `output/experiments/experiment_29_global_expansion/expansion_hazard_pilot.csv` | Observed-event hazard pilot (baseline vs affected) for the additions with public UNOSAT footprints |
| `output/experiments/experiment_29_global_expansion/expansion_data_provenance.csv` + `EXPANSION_DATA_PROVENANCE.md` | Source URL/API, local storage path, size, feature count and derived outputs per country |
| `output/experiments/experiment_29_global_expansion/worldpop_units_check.txt` | WorldPop density-vs-counts verification table |

Hazard pilot detail (national population-weighted 30-minute access):

| Event | Footprint | Population in footprint | Affected segments (unpaved) | 30-min loss | 60-min loss |
|---|---:|---:|---:|---:|---:|
| VNM 2020-10-28 cyclone/flood | 2 962 km2 | 2.56 M | 229 869 (10 227) | health -0.71 pp, education -0.89 pp | health -0.25 pp, education -0.43 pp |
| IDN 2025-11-26 Aceh flood | 2 664 km2 | 2.31 M | 100 845 (1 886) | health -0.21 pp, education -0.11 pp | health -0.10 pp, education -0.05 pp |
| NGA 2022-07 Yobe flood | 21 km2 | 0.002 M | 0 (0) | 0.00 pp | 0.00 pp |
| IND 2015-11 Chennai/coastal Tamil Nadu flood | 16 087 km2 | 4.36 M | 104 236 (5 704) | health -0.04 pp, education -0.07 pp | health -0.02 pp, education -0.02 pp |

The pilot confirms the expected scale difference: single observed events move national
shares by less than 1 pp, while the uniform `no_unpaved` stress test reaches tens of pp.
Perceived event severity therefore depends on whether the question is national coverage
or the loss inside the affected area.
