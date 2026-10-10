# Limitations

1. Access is defined by the nearest facility of a given type; capacity, service readiness,
   referral level and competition are not modelled.
2. Population weights under the published convention use the WorldPop density raster
   directly, which inflates absolute populations by 1.16-1.82x; absolute totals should be
   taken from the counts-based columns only.
3. Segment lengths under the published convention use EPSG:3857, which overstates ground
   distance by up to 35% at high latitude; the geodesic variant is provided.
4. WGS84 geodesic and count-weighted variants are available for all 30 countries; the
   30-minute metric is the most sensitive to the length convention.
5. Independent facility registries exist for 11 of the 23 additions; elsewhere the OSM
   baseline is a lower bound whose tightness varies with local amenity tagging.
6. Event footprints exist for 14 of 23 additions; national-scale losses are usually small
   (<0.5 pp in 70% of event-country rows) and are governed by the affected share of the
   unpaved network.
7. The expansion sample is a stratified convenience sample of 30 countries, not a random
   global sample.
8. Hazard footprints are scenario inputs (observed events), not annual expected loss.


## Manuscript v33 limitation statement

Limitations: (i) estimates remain baseline-dependent; (ii) the sign of the contrast depends on the speed convention (31/60 Δ_total rows are negative at baseline speeds, 26/60 when all speeds are multiplied by 1.15, and 24/60 at 1.30); (iii) input years are not synchronised (Planet 2024, WorldPop/GHS-SMOD/SHDI 2020, and OSM/HOT 2026 snapshots); (iv) hazard footprints represent scenario losses rather than expected annual losses; (v) road-network completeness cannot be adjudicated from the available inventories; (vi) facility capacity and service readiness are unidentifiable from open data; (vii) health and education constraints differ by country, so basic-service accessibility is not a single scalar; (viii) the 30-country purposive sample maximises mechanistic heterogeneity rather than representativeness and does not support global inference; and (ix) external-target contrasts are not fully independent because one side uses our convention, so we claim only that the difference form can generate an apparent pattern.
