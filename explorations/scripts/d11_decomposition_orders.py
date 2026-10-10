# -*- coding: utf-8 -*-
"""Comment 4 (advisory): decomposition ordering robustness / Shapley sign stability.

On the single node basis of the noded-segment cache, compute four scenarios per
country-service:

  A         arterial-only edges, origins/facilities snapped to arterial nodes
  A_snap    arterial-only edges, origins/facilities snapped to ALL nodes
  B_shared  all edges,            snapped to arterial (shared) nodes
  B_full    all edges,            snapped to ALL nodes   (= canonical)

The two decomposition orders are:
  order 1 (add edges first):  edge_1 = B_shared - A,  snap_1 = B_full - B_shared
  order 2 (snap first):       snap_2 = A_snap - A,    edge_2 = B_full - A_snap

Shapley values average the two orders.  Report the sign-consistency of each component
across the 60 country-service rows.
"""
from __future__ import annotations

import gc
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[2]
import sys
sys.path.insert(0, str(ROOT))

import prototype_multicountry_access as base  # noqa: E402
import run_nested_counterfactual as rnc  # noqa: E402

OUT = ROOT / "explorations" / "output"
COUNTRIES = ["BGD", "COL", "EGY", "ETH", "GEO", "GHA", "GTM", "HND", "IDN", "IND",
             "JOR", "KEN", "KGZ", "KHM", "LKA", "MEX", "MLI", "MOZ", "NGA", "NPL",
             "PAK", "PER", "PHL", "PNG", "RWA", "SEN", "TUR", "TZA", "VNM", "ZMB"]


def process(iso: str) -> pd.DataFrame:
    t0 = time.time()
    d = rnc.load_segments(iso)
    keys, uid, vid = rnc.build_nodes(d)
    n_nodes = len(keys)
    shared = np.zeros(n_nodes, dtype=bool)
    shared[uid[d["art"]]] = True
    shared[vid[d["art"]]] = True
    csr_all = rnc.csr_min(uid, vid, d["w"], n_nodes)
    csr_art = rnc.csr_min(uid, vid, d["w"], n_nodes, mask=d["art"])
    del d, uid, vid
    gc.collect()

    x3857, y3857 = base.TRANSFORMER.transform(keys[:, 0], keys[:, 1])
    node3857 = np.column_stack([x3857, y3857])
    shared_ids = np.flatnonzero(shared)
    tree_all = cKDTree(node3857)
    tree_shared = cKDTree(node3857[shared_ids])

    cellxy, cellxy3857, pop = base.load_population(iso)
    fac = {}
    h = rnc.facilities(iso, "health")
    e = rnc.facilities(iso, "education")
    h = h[h.amenity.isin(["hospital", "clinic"])]
    e = e[e.amenity.eq("school")]
    for name, gdf in (("health", h), ("school", e)):
        pts = gdf.geometry.representative_point().to_crs(3857)
        fac[name] = np.column_stack([pts.geometry.x, pts.geometry.y])

    scenarios = [
        ("A", csr_art, tree_shared, shared_ids),
        ("A_snap", csr_art, tree_all, None),
        ("B_shared", csr_all, tree_shared, shared_ids),
        ("B_full", csr_all, tree_all, None),
    ]
    res = {s: {} for s, *_ in scenarios}
    for scen, csr, tree, imap in scenarios:
        for service, xy in fac.items():
            r = rnc.access(csr, tree, imap, cellxy3857, xy, pop)
            res[scen][service] = r["share_60min_pct"]

    rows = []
    for service in ("health", "school"):
        A = res["A"][service]
        As = res["A_snap"][service]
        Bs = res["B_shared"][service]
        Bf = res["B_full"][service]
        edge1 = Bs - A
        snap1 = Bf - Bs
        snap2 = As - A
        edge2 = Bf - As
        rows.append({
            "iso3": iso, "service": service,
            "A": A, "A_snap": As, "B_shared": Bs, "B_full": Bf,
            "order1_edge_pp": edge1, "order1_snap_pp": snap1,
            "order2_snap_pp": snap2, "order2_edge_pp": edge2,
            "shapley_edge_pp": 0.5 * (edge1 + edge2),
            "shapley_snap_pp": 0.5 * (snap1 + snap2),
        })
    print(f"{iso}: done ({time.time() - t0:.0f}s)", flush=True)
    return pd.DataFrame(rows)


def main():
    countries = [c.upper() for c in (sys.argv[1:] or COUNTRIES)]
    frames = []
    for iso in countries:
        try:
            frames.append(process(iso))
        except Exception as exc:
            print(f"{iso}: FAILED {type(exc).__name__} {exc}", flush=True)
            raise
    df = pd.concat(frames, ignore_index=True)
    df.to_csv(OUT / "d11_decomposition_orders.csv", index=False, encoding="utf-8-sig")

    # sign-consistency statistics across the 60 rows
    edge_agree = np.sign(df["order1_edge_pp"]) == np.sign(df["order2_edge_pp"])
    snap_agree = np.sign(df["order1_snap_pp"]) == np.sign(df["order2_snap_pp"])
    edge_nonneg = (df["order1_edge_pp"] >= -1e-9) & (df["order2_edge_pp"] >= -1e-9)
    print("=" * 70)
    print(f"n country-service rows: {len(df)}")
    print(f"edge sign-consistent across orders: {edge_agree.mean():.1%}")
    print(f"snap sign-consistent across orders: {snap_agree.mean():.1%}")
    print(f"edge non-negative in both orders: {edge_nonneg.mean():.1%}")
    print("Shapley edge (pp): mean %.2f, min %.2f, max %.2f" % (
        df["shapley_edge_pp"].mean(), df["shapley_edge_pp"].min(), df["shapley_edge_pp"].max()))
    print("Shapley snap (pp): mean %.2f, min %.2f, max %.2f" % (
        df["shapley_snap_pp"].mean(), df["shapley_snap_pp"].min(), df["shapley_snap_pp"].max()))
    print("order1 vs order2 edge correlation: %.3f" % df[["order1_edge_pp", "order2_edge_pp"]].corr().iloc[0, 1])
    print("order1 vs order2 snap correlation: %.3f" % df[["order1_snap_pp", "order2_snap_pp"]].corr().iloc[0, 1])
    print("saved", OUT / "d11_decomposition_orders.csv")


if __name__ == "__main__":
    main()
