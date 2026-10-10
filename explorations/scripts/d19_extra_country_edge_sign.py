# -*- coding: utf-8 -*-
"""Experiment A (full): build noded network and test Delta_edge non-negativity for 5 extra countries."""
from __future__ import annotations

import gc
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import prototype_multicountry_access as base  # noqa: E402
import run_experiment_29_corrected_countries as canon  # noqa: E402
import run_nested_counterfactual as rnc  # noqa: E402

OUT = ROOT / "explorations" / "output"
EXTRA = [("FJI", "FJ"), ("TLS", "TL"), ("BTN", "BT"), ("ARM", "AM"), ("NAM", "NA")]


def decompose(iso: str):
    # prepare noded segments if needed
    cache = ROOT / "data" / "external" / "hdx" / "countries" / iso / "local_roads" / f"{iso.lower()}_noded_segments.gpkg"
    if not cache.exists():
        canon.prepare_noded(iso, dict(EXTRA)[iso])
    d = rnc.load_segments(iso)
    keys, uid, vid = rnc.build_nodes(d)
    n = len(keys)
    shared = np.zeros(n, dtype=bool)
    shared[uid[d["art"]]] = True
    shared[vid[d["art"]]] = True
    csr_all = rnc.csr_min(uid, vid, d["w"], n)
    csr_art = rnc.csr_min(uid, vid, d["w"], n, mask=d["art"])
    del d, uid, vid
    gc.collect()
    x3857, y3857 = base.TRANSFORMER.transform(keys[:, 0], keys[:, 1])
    node3857 = np.column_stack([x3857, y3857])
    shared_ids = np.flatnonzero(shared)
    tree_all = cKDTree(node3857)
    tree_shared = cKDTree(node3857[shared_ids])
    cellxy, cellxy3857, pop = base.load_population(iso)
    fac = {}
    for name, kind in (("health", "health"), ("school", "education")):
        g = rnc.facilities(iso, kind)
        if "amenity" not in g.columns:
            raise KeyError(iso, kind)
        if kind == "health":
            g = g[g.amenity.isin(["hospital", "clinic"])]
        else:
            g = g[g.amenity.eq("school")]
        pts = g.geometry.representative_point().to_crs(3857)
        fac[name] = np.column_stack([pts.geometry.x, pts.geometry.y])
    rows = []
    for service, xy in fac.items():
        A = rnc.access(csr_art, tree_shared, shared_ids, cellxy3857, xy, pop)["share_60min_pct"]
        As = rnc.access(csr_art, tree_all, None, cellxy3857, xy, pop)["share_60min_pct"]
        Bs = rnc.access(csr_all, tree_shared, shared_ids, cellxy3857, xy, pop)["share_60min_pct"]
        Bf = rnc.access(csr_all, tree_all, None, cellxy3857, xy, pop)["share_60min_pct"]
        rows.append({"iso3": iso, "service": service,
                     "A": A, "A_snap": As, "B_shared": Bs, "B_full": Bf,
                     "order1_edge_pp": Bs - A, "order2_edge_pp": Bf - As})
    return rows


def main():
    rows = []
    for iso3, iso2 in EXTRA:
        t0 = time.time()
        try:
            r = decompose(iso3)
            rows.extend(r)
            print(iso3, "done", {k: round(v, 2) for k, v in r[0].items() if k in ("order1_edge_pp", "order2_edge_pp")}, f"({time.time()-t0:.0f}s)", flush=True)
        except Exception as e:
            print(iso3, "FAILED", type(e).__name__, str(e)[:160], flush=True)
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "d19_extra_country_edge_sign.csv", index=False, encoding="utf-8-sig")
    if len(df):
        both_nonneg = ((df["order1_edge_pp"] >= -1e-6) & (df["order2_edge_pp"] >= -1e-6))
        print("\nrows:", len(df), "both-order edge non-negative:", both_nonneg.mean())
        print(df[["iso3", "service", "order1_edge_pp", "order2_edge_pp"]].round(3).to_string(index=False))
        print("saved", OUT / "d19_extra_country_edge_sign.csv")


if __name__ == "__main__":
    main()
