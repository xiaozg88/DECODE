# Data dictionary

Column names are stable across the deposit. Access values are percentages of the population with finite travel time; losses are positive percentages points (baseline minus scenario).

## corrected_main_access_30countries.csv

60 rows

- `iso3`
- `country`
- `group`
- `region`
- `income_group`
- `service`
- `arterial_60min_pct`
- `noded_60min_pct`
- `share_60min_pct_density_mercator_none`
- `share_60min_pct_counts_geodesic_none`
- `convention_delta_60min_pp`
- `share_30min_pct_density_mercator_none`
- `share_30min_pct_counts_geodesic_none`
- `convention_delta_30min_pp`
- `population_total_millions_density_mercator_none`
- `population_total_millions_counts_geodesic_none`
- `population_change_pct`
- `no_unpaved_loss_60min_pp`
- `unknown_as_unpaved_loss_60min_pp`
- `urban_rural_gap_60min_pp`
- `hazard_events`
- `worst_event_id`
- `worst_event_loss_60min_pp`
- `noded_segments`

## hazard_event_table.csv

80 rows

- `iso3`
- `service`
- `event_id`
- `event_date`
- `source`
- `footprint_area_km2`
- `population_total_millions`
- `affected_km`
- `affected_unpaved_km`
- `affected_segments`
- `affected_unpaved_segments`
- `network_segments`
- `loss_60min_pp`
- `share_60min_baseline`
- `share_60min_hazard`
- `share_30min_pct__baseline`
- `share_30min_pct__hazard`
- `share_60min_pct__baseline`
- `share_60min_pct__hazard`
- `population_in_footprint`
- `affected_share_pct`
- `affected_unpaved_share_pct`
- `population_in_footprint_share_pct`

## facility_registry_bottleneck.csv

12 rows

- `iso3`
- `service`
- `osm_records`
- `registry_records`
- `osm_source_nodes`
- `union_source_nodes`
- `registry_snap_median_m`
- `registry_snap_within_1km_pct`
- `share_60min_osm_counts`
- `share_30min_osm_counts`
- `share_60min_osm_density`
- `share_30min_osm_density`
- `share_60min_union_counts`
- `share_30min_union_counts`
- `share_60min_union_density`
- `share_30min_union_density`
- `registry_gain_60min_pp`
- `registry_gain_30min_pp`

## facility_quality_by_country.csv

60 rows

- `iso3`
- `country`
- `service`
- `files`
- `raw_records`
- `unique_records`
- `duplicate_records`
- `duplicate_pct`
- `usable_records`
- `usable_unique_records`
- `usable_share_pct`
- `usable_of_unique_pct`
- `top_amenities`

## urban_rural_expansion.csv

180 rows

- `iso3`
- `service`
- `group`
- `population_millions`
- `population_cells`
- `share_30min_pct`
- `share_60min_pct`
- `share_120min_pct`
- `mean_travel_reachable_min`
- `facilities`
- `facility_source_nodes`
- `unreachable_population_millions`

## uncertainty_envelope_60min.csv

60 rows

- `iso3`
- `service`
- `canonical_share_60min_pct`
- `pop_effect_pp`
- `length_effect_pp`
- `facility_effect_pp`
- `facility_case`
- `low_share_60min_pct`
- `high_share_60min_pct`
- `envelope_width_pp`

## expansion_data_provenance.csv

30 rows

- `iso3`
- `country`
- `iso2`
- `region`
- `income_group`
- `hazard_profile`
- `sample_status`
- `planet_source`
- `planet_url`
- `planet_http_status`
- `planet_local_path`
- `planet_bytes`
- `planet_features`
- `planet_last_modified_utc`
- `worldpop_source`
- `worldpop_url`
- `worldpop_http_status`
- `worldpop_local_path`
- `worldpop_bytes`
- `worldpop_last_modified_utc`
- `hazard_events_local`
- `hazard_event_urls`
- `health_export_key`
- `health_export_url`
- `health_export_last_modified`
- `health_archive_path`
- `health_archive_bytes`
- `health_gpkg_path`
- `health_gpkg_bytes`
- `health_features`
- `education_export_key`
- `education_export_url`
- `education_export_last_modified`
- `education_archive_path`
- `education_archive_bytes`
- `education_gpkg_path`
- `education_gpkg_bytes`
- `education_features`
- `osm_roads_export_key`
- `osm_roads_url`
- `osm_roads_provenance_status`
- `osm_roads_last_modified`
- `osm_roads_archive_path`
- `osm_roads_archive_bytes`
- `osm_roads_gpkg_path`
- `osm_roads_gpkg_bytes`
- `osm_roads_features`
- `counterpart_facility_exports`
- `noded_cache_path`
- `noded_cache_bytes`
- `noded_segments`
- `baseline_csv`
- `baseline_written_utc`
- `originals_parquet`

## planet_surface_availability.csv

30 rows

- `iso3`
- `planet_segments`
- `planet_arterial_km`
- `planet_known_share_pct`

## correction_direction_matrix.csv

60 rows

- `iso3`
- `service`
- `arterial_60min_pct`
- `corrected_60min_pct`
- `corrected_minus_arterial_pp`
- `group`
- `noded_segments`
- `country`
- `region`
- `income_group`
- `hazard_profile`
- `planet_segments`
- `planet_arterial_km`
- `planet_known_share_pct`
- `corrected_counts_geodesic_60min_pct`
- `geodesic_30min_delta_pp`
- `sign`

## map_health_travel_time_vs_model.csv

30 rows

- `iso3`
- `benchmark_cells`
- `benchmark_population_millions`
- `benchmark_mean_travel_min`
- `benchmark_share_30min_pct`
- `benchmark_share_60min_pct`
- `benchmark_share_120min_pct`
- `model_share_60min_canonical`
- `model_share_60min_corrected`
- `model_share_30min_corrected`
- `arterial_60min_pct`

## direction_law_bootstrap.csv

2000 rows

- `slope`
- `intercept`
- `r2`
- `breakeven_arterial_pct`

## direction_law_leave_one_group_out.csv

10 rows

- `held_out_by`
- `held_out`
- `n_train`
- `n_test`
- `slope`
- `intercept`
- `train_r2`
- `test_mae_pp`
- `test_bias_pp`

## network_completeness_by_country.csv

30 rows

- `iso3`
- `noded_segments`
- `noded_km`
- `planet_km`
- `local_km`
- `local_share_pct`
- `area_km2`
- `population_counts_millions`
- `urban_share_pct`
- `road_density_km_per_km2`
- `population_density_per_km2`
- `mean_correction_pp`
- `direction_residual_pp`
- `benchmark_gap_pp`
- `benchmark_share_60min_pct`
- `model_share_60min_corrected`
- `planet_known_share_pct`

## direction_law_two_predictor.csv

60 rows

- `iso3`
- `service`
- `arterial_60min_pct`
- `corrected_60min_pct`
- `corrected_minus_arterial_pp`
- `group`
- `noded_segments`
- `country`
- `region`
- `income_group`
- `hazard_profile`
- `planet_segments`
- `planet_arterial_km`
- `planet_known_share_pct`
- `corrected_counts_geodesic_60min_pct`
- `geodesic_30min_delta_pp`
- `sign`
- `urban_share_pct`
- `pred_two`

## facility_scenario_shares.csv

180 rows

- `iso3`
- `service`
- `scenario`
- `facility_records`
- `facility_source_nodes`
- `share_30min_pct`
- `share_60min_pct`
- `share_120min_pct`

## shdi_access_correlations_core7.csv

14 rows

- `iso3`
- `service`
- `regions`
- `population_weighted_pearson`
- `unweighted_pearson`

## grip4_vs_network_density.csv

30 rows

- `iso3`
- `noded_segments`
- `noded_km`
- `planet_km`
- `local_km`
- `local_share_pct`
- `area_km2`
- `population_counts_millions`
- `urban_share_pct`
- `road_density_km_per_km2`
- `population_density_per_km2`
- `mean_correction_pp`
- `direction_residual_pp`
- `benchmark_gap_pp`
- `benchmark_share_60min_pct`
- `model_share_60min_corrected`
- `planet_known_share_pct`
- `cells`
- `grip_area_mean_density`
- `grip_tp1_mean_density`
- `grip_tp2_mean_density`
- `grip_tp3_mean_density`
- `grip_tp4_mean_density`
- `grip_tp5_mean_density`
- `grip_local_mean_density`
- `grip_total_mean_density`
- `grip_all_mean_density`
- `grip_over_model_density`

## jrc_100y_exposure_30countries.csv

30 rows

- `iso3`
- `population_millions`
- `population_exposed_pct`
- `population_exposed_gt0p5m_pct`
- `network_km`
- `network_exposed_pct`
- `network_exposed_gt0p5m_pct`
- `unpaved_exposed_pct_of_network`

## shdi_access_correlations_26countries.csv

60 rows

- `iso3`
- `service`
- `regions`
- `population_weighted_pearson`
- `unweighted_pearson`

## capacity_attribute_coverage.csv

9 rows

- `iso3`
- `records`
- `beds_recorded_pct`
- `beds_ge10_pct`
- `staff_recorded_pct`
- `beds_total`

## capacity_threshold_shares.csv

22 rows

- `iso3`
- `facility_set`
- `facilities`
- `source_nodes`
- `share_30min_pct`
- `share_60min_pct`
