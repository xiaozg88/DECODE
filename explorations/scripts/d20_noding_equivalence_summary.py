# -*- coding: utf-8 -*-
"""Experiment G: run validate_tiled_vs_canonical for 5 diverse countries and summarise."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import validate_tiled_vs_canonical as val  # noqa: E402

ISO_LIST = ["KGZ", "COL", "TZA", "PER", "NGA"]
TILED_OUT = ROOT / "output" / "experiments" / "experiment_29_global_expansion" / "validation_tiled_v2"
CANON = ROOT / "output" / "experiments" / "experiment_29_global_expansion" / "corrected_countries"
MAIN_ACCESS = ROOT / "output" / "paper_ready_main_access.csv"


def main():
    rows = []
    main_acc = pd.read_csv(MAIN_ACCESS)
    for iso in ISO_LIST:
        low = iso.lower()
        can_gpkg = ROOT / "data/external/hdx/countries" / iso / "local_roads" / f"{low}_noded_segments.gpkg"
        til_parquet = ROOT / "data/external/hdx/countries" / iso / "local_roads" / f"{low}_tiledtest_noded_segments.parquet"
        geo_c, geo_t = val.geometry_totals(can_gpkg, til_parquet)
        # tiled baseline shares
        til = pd.read_csv(TILED_OUT / low / f"{low}_corrected_baseline.csv")
        # canonical baseline shares
        if iso == "COL":
            can = main_acc[(main_acc.iso3 == "COL") & (main_acc.scenario == "baseline")].copy()
            can = can.rename(columns={"share_60min_pct": "share_60min_pct"})
            can["service"] = can["service"].replace({"health": "health", "education": "education"})
        else:
            can = pd.read_csv(CANON / low / f"{low}_corrected_baseline.csv")
        deltas = {}
        for svc in ("health", "education"):
            c = can[can.service == svc].iloc[0]["share_60min_pct"]
            t = til[til.service == svc].iloc[0]["share_60min_pct"]
            deltas[svc] = t - c
        max_abs = max(abs(deltas["health"]), abs(deltas["education"]))
        # geometry conservation (relative %)
        len_rel = (geo_t["length_m"] - geo_c["length_m"]) / geo_c["length_m"] * 100
        tt_rel = (geo_t["travel_time_min"] - geo_c["travel_time_min"]) / geo_c["travel_time_min"] * 100
        rows.append({
            "iso3": iso,
            "canonical_segments": geo_c["segments"],
            "tiled_segments": geo_t["segments"],
            "length_rel_pct": len_rel,
            "travel_time_rel_pct": tt_rel,
            "max_share_delta_pp": max_abs,
            "health_share_delta_pp": deltas["health"],
            "education_share_delta_pp": deltas["education"],
        })
        print(f"{iso}: max|delta| share = {max_abs:.4f} pp | length rel {len_rel:+.4f}% | tt rel {tt_rel:+.4f}%", flush=True)
    df = pd.DataFrame(rows)
    out = ROOT / "explorations" / "output" / "d20_noding_equivalence.csv"
    df.to_csv(out, index=False, encoding="utf-8-sig")
    print("\n=== 汇总 ===")
    print(df.round(5).to_string(index=False))
    print("\n最大份额差 < 0.1 pp 的国家占比:", (df.max_share_delta_pp < 0.1).mean())
    print("最大份额差 < 0.5 pp 的国家占比:", (df.max_share_delta_pp < 0.5).mean())
    print("saved", out)


if __name__ == "__main__":
    main()
