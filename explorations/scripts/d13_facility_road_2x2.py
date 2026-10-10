# -*- coding: utf-8 -*-
"""Comment 8 (advisory): facility-definition x road-completeness 2x2 decomposition.

Health 60-min share on a 2x2:
  road:  arterial-only (Planet arterial, same node basis)  vs  full (noded)
  facility: hospital_only (tight) / hospital_clinic (baseline) / all_health_points (loose)

Tests whether the facility-definition effect is amplified when local roads are absent
(i.e. non-additivity of the two measurement choices).  Full-network facility scenarios
are read from the existing ``facility_scenario_shares.csv``; arterial scenarios are
computed here.
"""
from __future__ import annotations

import gc
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.sparse.csgraph import dijkstra
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "explorations" / "scripts"))

import prototype_multicountry_access as base  # noqa: E402
import run_experiment_29_corrected_countries as canon  # noqa: E402
import run_nested_counterfactual as rnc  # noqa: E402
from d09_arterial_cell_access import load_arterial_segments  # noqa: E402

OUT = ROOT / "explorations" / "output"
FULL_CSV = ROOT / "output" / "experiments" / "facility_scenarios" / "facility_scenario_shares.csv"
CELL_DIR = ROOT / "output" / "experiments" / "cell_travel_times"
COUNTRIES = ["BGD", "COL", "EGY", "ETH", "GEO", "GHA", "GTM", "HND", "IDN", "IND",
             "JOR", "KEN", "KGZ", "KHM", "LKA", "MEX", "MLI", "MOZ", "NGA", "NPL",
             "PAK", "PER", "PHL", "PNG", "RWA", "SEN", "TUR", "TZA", "VNM", "ZMB"]
FAC_SETS = ["hospital_clinic", "hospital_only", "all_health_points"]


def facility_sets(iso: str):
    fac = canon.load_facilities(iso, "health")
    amenity = fac.amenity.astype(str).str.lower().str.strip()
    missing = fac.amenity.isna() | amenity.isin(["none", "nan", ""])
    return {
        "hospital_clinic": fac[amenity.isin(["hospital", "clinic"])],
        "hospital_only": fac[amenity == "hospital"],
        "all_health_points": fac[~missing],
    }


def arterial_share(iso: str, fac_gdf, tree: cKDTree, csr, idx_cell, pop):
    pts = fac_gdf.geometry.representative_point().to_crs(3857)
    xy = np.column_stack([pts.geometry.x, pts.geometry.y])
    dfac, ifac = tree.query(xy)
    keep = np.asarray(dfac) <= 1000.0
    src = np.unique(np.asarray(ifac)[keep].astype(np.int64))
    if len(src) == 0:
        return np.nan
    dist = dijkstra(csr, indices=src, min_only=True)
    d = dist[idx_cell]
    valid = np.isfinite(d)
    return 100 * pop[valid & (d <= 60)].sum() / pop.sum()


def process(iso: str) -> list[dict]:
    t0 = time.time()
    cells = pd.read_parquet(CELL_DIR / f"{iso}.parquet")
    pop = cells["population_counts"].to_numpy(dtype="float64")
    lonlat = np.column_stack([cells["lon"].to_numpy(), cells["lat"].to_numpy()])
    d = load_arterial_segments(iso)
    keys, uid, vid = rnc.build_nodes(d)
    n_nodes = len(keys)
    csr = rnc.csr_min(uid, vid, d["w"], n_nodes)
    del d, uid, vid
    gc.collect()
    x3857, y3857 = base.TRANSFORMER.transform(keys[:, 0], keys[:, 1])
    tree = cKDTree(np.column_stack([x3857, y3857]))
    cell3857 = np.column_stack(base.TRANSFORMER.transform(lonlat[:, 0], lonlat[:, 1]))
    _, idx_cell = tree.query(cell3857)
    idx_cell = np.asarray(idx_cell)

    rows = []
    for name, fac in facility_sets(iso).items():
        if len(fac) == 0:
            continue
        rows.append({"iso3": iso, "road": "arterial", "facility": name,
                     "facility_records": int(len(fac)),
                     "share_60min_pct": arterial_share(iso, fac, tree, csr, idx_cell, pop)})
    print(f"{iso}: arterial facility scenarios done ({time.time() - t0:.0f}s)", flush=True)
    return rows


def main():
    countries = [c.upper() for c in (sys.argv[1:] or COUNTRIES)]
    rows = []
    for iso in countries:
        try:
            rows.extend(process(iso))
        except Exception as exc:
            print(f"{iso}: FAILED {type(exc).__name__} {exc}", flush=True)
            raise
    art = pd.DataFrame(rows)
    full = pd.read_csv(FULL_CSV)
    full = full[full["scenario"].isin(FAC_SETS)].copy()
    full = full.rename(columns={"scenario": "facility"})
    full["road"] = "full"
    full = full[["iso3", "road", "facility", "share_60min_pct"]]
    both = pd.concat([art, full], ignore_index=True)
    both.to_csv(OUT / "d13_facility_road_2x2.csv", index=False, encoding="utf-8-sig")

    # clean 2x2 effects from the long-format data
    piv = both.pivot(index="iso3", columns=["road", "facility"], values="share_60min_pct")
    eff = pd.DataFrame(index=piv.index)
    eff["tight_effect_arterial"] = piv[("arterial", "hospital_only")] - piv[("arterial", "hospital_clinic")]
    eff["tight_effect_full"] = piv[("full", "hospital_only")] - piv[("full", "hospital_clinic")]
    eff["loose_effect_arterial"] = piv[("arterial", "all_health_points")] - piv[("arterial", "hospital_clinic")]
    eff["loose_effect_full"] = piv[("full", "all_health_points")] - piv[("full", "hospital_clinic")]
    eff["nonadditivity_tight"] = eff["tight_effect_arterial"] - eff["tight_effect_full"]
    eff["nonadditivity_loose"] = eff["loose_effect_arterial"] - eff["loose_effect_full"]
    eff.to_csv(OUT / "d13_facility_road_2x2_effects.csv", index=True, encoding="utf-8-sig")

    print("=" * 70)
    print("facility-definition effect (pp), tight = hospital_only - hospital_clinic:")
    print("  arterial: mean %.2f, min %.2f, max %.2f" % (
        eff["tight_effect_arterial"].mean(), eff["tight_effect_arterial"].min(),
        eff["tight_effect_arterial"].max()))
    print("  full:     mean %.2f, min %.2f, max %.2f" % (
        eff["tight_effect_full"].mean(), eff["tight_effect_full"].min(),
        eff["tight_effect_full"].max()))
    print("non-additivity (arterial - full tight effect): mean %.2f, min %.2f, max %.2f" % (
        eff["nonadditivity_tight"].mean(), eff["nonadditivity_tight"].min(),
        eff["nonadditivity_tight"].max()))
    print("share with |nonadditivity| > 2pp: %.1f%%" % (
        100 * (eff["nonadditivity_tight"].abs() > 2).mean()))
    print("saved", OUT / "d13_facility_road_2x2.csv")
    print("saved", OUT / "d13_facility_road_2x2_effects.csv")


if __name__ == "__main__":
    main()
