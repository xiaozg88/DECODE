# -*- coding: utf-8 -*-
"""Cell-level arterial-only vs full (noded) accessibility identity flip.

Count how many people's accessibility *identity* (accessible within N minutes to the
nearest essential service) flips when the road-network convention changes from
"Planet arterial roads only" to "Planet arterial + local OSM roads" (the corrected /
noded model).  Both scenarios share the same node basis (the noded-segment cache
``{iso}_noded_segments.gpkg`` restricted to ``source == 'planet_arterial'`` for the
arterial-only scenario).  Full-network cell travel times are read from the canonical
``output/experiments/cell_travel_times/{iso}.parquet`` (population = corrected counts
= density x cell area, matching the published corrected model).
"""
from __future__ import annotations

import gc
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import pyogrio
import shapely
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import dijkstra
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "explorations" / "scripts"))

from common import COUNTRIES  # noqa: E402
import prototype_multicountry_access as base  # noqa: E402
import run_nested_counterfactual as rnc  # noqa: E402

OUT = ROOT / "explorations" / "output"
CELL_DIR = ROOT / "output" / "experiments" / "cell_travel_times"
CELL_FLIP_DIR = ROOT / "explorations" / "output" / "d09_arterial_cell"
CHUNK = 750_000
THRESHOLDS = (30, 60, 120)


def _log(msg: str):
    print(msg, flush=True)


def noded_gpkg(iso: str) -> Path:
    d = ROOT / "data" / "external" / "hdx" / "countries" / iso / "local_roads"
    cands = [p for p in sorted(d.glob("*_noded_segments.gpkg")) if "tiled" not in p.name]
    if not cands:
        raise FileNotFoundError(iso)
    return cands[0]


def load_arterial_segments(iso: str) -> dict:
    """Stream the noded-segment gpkg, reading only Planet-arterial segments via the
    OGR ``where`` push-down (so OSM local-road geometry is never read)."""
    path = noded_gpkg(iso)
    xs_u, ys_u, xs_v, ys_v, w_all = [], [], [], [], []
    n_art = 0
    t0 = time.time()
    start = 0
    while True:
        meta, tbl = pyogrio.read_arrow(
            path, columns=["source", "travel_time_min"],
            where="source='planet_arterial'",
            skip_features=start, max_features=CHUNK,
        )
        n = tbl.num_rows
        if n == 0:
            break
        geom_col = meta["geometry_name"] if meta.get("geometry_name") else "wkb_geometry"
        geom = shapely.from_wkb(tbl.column(geom_col).to_numpy())
        w = tbl.column("travel_time_min").to_numpy(zero_copy_only=False).astype("float64")
        coords = shapely.get_coordinates(geom)
        counts = shapely.get_num_coordinates(geom)
        first = np.concatenate(([0], np.cumsum(counts)[:-1]))
        last = np.cumsum(counts) - 1
        xs_u.append(coords[first, 0]); ys_u.append(coords[first, 1])
        xs_v.append(coords[last, 0]); ys_v.append(coords[last, 1])
        w_all.append(w)
        n_art += n
        del tbl, geom, coords, w
        gc.collect()
        if n < CHUNK:
            break
        start += n
    _log(f"{iso}: arterial segments {n_art:,} ({time.time() - t0:.0f}s)")
    if n_art == 0:
        raise RuntimeError(f"{iso}: no planet_arterial segments")
    return {
        "xu": np.concatenate(xs_u), "yu": np.concatenate(ys_u),
        "xv": np.concatenate(xs_v), "yv": np.concatenate(ys_v),
        "w": np.concatenate(w_all),
    }


def arterial_graph(iso: str, cells_lonlat: np.ndarray):
    d = load_arterial_segments(iso)
    keys, uid, vid = rnc.build_nodes(d)
    n_nodes = len(keys)
    csr = rnc.csr_min(uid, vid, d["w"], n_nodes)  # every edge is arterial
    x3857, y3857 = base.TRANSFORMER.transform(keys[:, 0], keys[:, 1])
    node3857 = np.column_stack([x3857, y3857])
    tree = cKDTree(node3857)
    cell3857 = np.column_stack(base.TRANSFORMER.transform(cells_lonlat[:, 0], cells_lonlat[:, 1]))
    _, idx_cell = tree.query(cell3857)
    idx_cell = np.asarray(idx_cell)
    _log(f"{iso}: arterial nodes={n_nodes:,} edges={csr.nnz // 2:,}")
    return csr, n_nodes, tree, idx_cell


def facility_sources(iso: str, kind: str, tree: cKDTree):
    gdf = rnc.facilities(iso, kind)
    if "amenity" not in gdf.columns:
        raise KeyError(f"{iso} {kind}: no amenity column")
    vals = ["hospital", "clinic"] if kind == "health" else ["school"]
    gdf = gdf[gdf["amenity"].isin(vals)]
    if len(gdf) == 0:
        return np.array([], dtype=np.int64)
    pts = gdf.geometry.representative_point().to_crs(3857)
    fac_xy = np.column_stack([pts.geometry.x, pts.geometry.y])
    dfac, ifac = tree.query(fac_xy)
    keep = np.asarray(dfac) <= 1000.0
    return np.unique(np.asarray(ifac)[keep].astype(np.int64))


def run_country(iso: str) -> pd.DataFrame:
    t0 = time.time()
    cells = pd.read_parquet(CELL_DIR / f"{iso}.parquet")
    pop = cells["population_counts"].to_numpy(dtype="float64")
    lonlat = np.column_stack([cells["lon"].to_numpy(), cells["lat"].to_numpy()])
    csr, n_nodes, tree, idx_cell = arterial_graph(iso, lonlat)

    tt = {"full": {}, "arterial": {}}
    for service, kind in (("health", "health"), ("education", "education")):
        src = facility_sources(iso, kind, tree)
        if len(src) == 0:
            art_tt = np.full(len(pop), np.inf)
        else:
            dist = dijkstra(csr, indices=src, min_only=True)
            art_tt = dist[idx_cell].astype("float64")
        full_tt = cells[f"travel_{service}_min"].to_numpy(dtype="float64")
        full_tt = np.where(np.isfinite(full_tt), full_tt, np.inf)
        art_tt = np.where(np.isfinite(art_tt), art_tt, np.inf)
        tt["full"][service] = full_tt
        tt["arterial"][service] = art_tt

    # persist the cell-level comparison
    CELL_FLIP_DIR.mkdir(parents=True, exist_ok=True)
    out_cell = pd.DataFrame({
        "lon": cells["lon"].to_numpy(), "lat": cells["lat"].to_numpy(),
        "population_counts": pop,
        "health_full_min": tt["full"]["health"], "health_arterial_min": tt["arterial"]["health"],
        "education_full_min": tt["full"]["education"], "education_arterial_min": tt["arterial"]["education"],
    })
    out_cell.to_parquet(CELL_FLIP_DIR / f"{iso}_cell_flip.parquet", index=False, compression="zstd")

    rows = []
    for service in ("health", "education"):
        full_tt = tt["full"][service]
        art_tt = tt["arterial"][service]
        for t in THRESHOLDS:
            full_ok = full_tt <= t
            art_ok = art_tt <= t
            flip = full_ok != art_ok
            gained = (~art_ok) & full_ok
            lost = art_ok & (~full_ok)
            rows.append({
                "iso3": iso, "service": service, "threshold_min": t,
                "total_population": float(pop.sum()),
                "n_cells": int(len(pop)),
                "arterial_share_pct": float(100 * pop[art_ok].sum() / pop.sum()),
                "full_share_pct": float(100 * pop[full_ok].sum() / pop.sum()),
                "flip_population": float(pop[flip].sum()),
                "flip_share_pp": float(100 * pop[flip].sum() / pop.sum()),
                "gained_population": float(pop[gained].sum()),
                "lost_population": float(pop[lost].sum()),
            })
    # union: population whose identity flips on health OR education
    for t in THRESHOLDS:
        h_flip = (tt["full"]["health"] <= t) != (tt["arterial"]["health"] <= t)
        e_flip = (tt["full"]["education"] <= t) != (tt["arterial"]["education"] <= t)
        union = h_flip | e_flip
        rows.append({
            "iso3": iso, "service": "either", "threshold_min": t,
            "total_population": float(pop.sum()),
            "n_cells": int(len(pop)),
            "arterial_share_pct": np.nan,
            "full_share_pct": np.nan,
            "flip_population": float(pop[union].sum()),
            "flip_share_pp": float(100 * pop[union].sum() / pop.sum()),
            "gained_population": np.nan,
            "lost_population": np.nan,
        })
    _log(f"{iso}: done ({time.time() - t0:.0f}s)")
    return pd.DataFrame(rows)


def main():
    countries = [c.upper() for c in (sys.argv[1:] or list(COUNTRIES))]
    OUT.mkdir(parents=True, exist_ok=True)
    frames = []
    for iso in countries:
        try:
            frames.append(run_country(iso))
        except Exception as exc:
            _log(f"{iso}: FAILED {type(exc).__name__} {exc}")
            raise
    df = pd.concat(frames, ignore_index=True)
    summary = OUT / "d09_access_identity_flip_summary.csv"
    df.to_csv(summary, index=False, encoding="utf-8-sig")

    h60 = df[df["threshold_min"] == 60].copy()
    health = h60[h60["service"] == "health"].sort_values("flip_population", ascending=False)
    edu = h60[h60["service"] == "education"].sort_values("flip_population", ascending=False)
    either = h60[h60["service"] == "either"].sort_values("flip_population", ascending=False)
    tot_pop = df.groupby("iso3")["total_population"].max().sum()

    lines = ["=" * 70,
             "Cell-level accessibility identity flip (60 minutes), 30-country sample",
             "=" * 70]
    for svc, sub in (("health", health), ("education", edu)):
        tot = sub["flip_population"].sum()
        lines.append(f"{svc}: flip population = {tot:,.0f} (~{tot/1e8:.2f} 亿)")
    tot_union = either["flip_population"].sum()
    lines.append(f"either (health OR education): flip population = {tot_union:,.0f} "
                 f"(~{tot_union/1e8:.2f} 亿)")
    lines.append("-" * 70)
    lines.append(f"health flip total: {health['flip_population'].sum():,.0f} "
                 f"({health['flip_population'].sum()/1e8:.2f} 亿)")
    lines.append(f"education flip total: {edu['flip_population'].sum():,.0f} "
                 f"({edu['flip_population'].sum()/1e8:.2f} 亿)")
    lines.append(f"either flip total: {tot_union:,.0f} ({tot_union/1e8:.2f} 亿)")
    lines.append(f"sample total population: {tot_pop:,.0f} ({tot_pop/1e8:.2f} 亿)")
    lines.append("")
    lines.append("top 8 countries by 'either' flip population:")
    lines.append(either.head(8)[["iso3", "flip_population", "flip_share_pp"]].to_string(index=False))
    report = "\n".join(lines)
    (OUT / "d09_access_identity_flip_report.txt").write_text(report, encoding="utf-8")
    print(report)


if __name__ == "__main__":
    main()
