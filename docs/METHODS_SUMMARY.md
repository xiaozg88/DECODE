# Methods summary

Road network: Planet arterial road-surface lines (HeiGIT HDX) unioned and topologically
noded with HOT/OSM motorable local roads; noding is done per 1.5-degree tile with adaptive
sub-tiling so that continental networks fit in 16 GB of RAM (validated against the
canonical single-shot union on Sri Lanka and Nepal: access shares within 0.05 pp, noded
length within 0.005%).

Travel times: speed = road class x surface class x width multiplier (M3), with travel
time proportional to segment length.  The published convention uses EPSG:3857 lengths; the
convention-corrected variant uses WGS84 geodesic lengths.

Population: WorldPop 2020 1 km rasters.  Note the published convention sums the raster
values (a density) directly; the corrected variant multiplies by the cell area to obtain
counts (verified against the WorldPop count rasters in 12/12 sampled countries).

Facilities: HOT/OSM hospital/clinic (health) and school (education) exports, optionally
unioned with independent registries (OCHA ROAP/OCHA country offices/OCHA ROCCA, Giga);
facilities are snapped to the nearest noded node within 1 km.

Hazard rule: a road segment is affected when its representative point falls inside the
event footprint; affected unpaved segments are impassable and other affected segments have
their travel time doubled.

Access metric: population share with finite travel time to the nearest facility within
30/60/120/240 minutes, computed with multi-source Dijkstra on the min-collapsed graph.
