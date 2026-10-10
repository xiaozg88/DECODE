# -*- coding: utf-8 -*-
"""Experiment D (advisory): make MAUP explainable, not merely avoided.

For each country-service-resolution-threshold, compare the canonical cell-level share
("threshold first, then aggregate") with the aggregated share ("population-weighted
average first, then threshold"), and relate the aggregation loss to within-grid-cell
travel-time heterogeneity (population-weighted standard deviation).

Reads the canonical ``output/experiments/cell_travel_times/{iso}.parquet`` only.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
CELL_DIR = ROOT / "output" / "experiments" / "cell_travel_times"
OUT = ROOT / "explorations" / "output"

COUNTRIES = ["BGD", "COL", "EGY", "ETH", "GEO", "GHA", "GTM", "HND", "IDN", "IND",
             "JOR", "KEN", "KGZ", "KHM", "LKA", "MEX", "MLI", "MOZ", "NGA", "NPL",
             "PAK", "PER", "PHL", "PNG", "RWA", "SEN", "TUR", "TZA", "VNM", "ZMB"]
RESOLUTIONS = (0.05, 0.10)
THRESHOLDS = (30, 60, 120)


def _grid(iso: str, service: str, resolution: float):
    cells = pd.read_parquet(CELL_DIR / f"{iso}.parquet")
    pop = cells["population_counts"].to_numpy(dtype="float64")
    tt = cells[f"travel_{service}_min"].to_numpy(dtype="float64")
    glon = np.floor(cells["lon"].to_numpy() / resolution) * resolution + resolution / 2
    glat = np.floor(cells["lat"].to_numpy() / resolution) * resolution + resolution / 2
    valid = np.isfinite(tt)
    frame = pd.DataFrame({
        "glon": glon, "glat": glat, "pop": pop,
        "pop_valid": np.where(valid, pop, 0.0),
        "ttw": np.where(valid, tt * pop, 0.0),
        "tt2w": np.where(valid, tt * tt * pop, 0.0),
    })
    total = pop.sum()
    grp = frame.groupby(["glon", "glat"])
    sums = grp[["pop", "pop_valid", "ttw", "tt2w"]].sum()
    mean_tt = sums["ttw"] / sums["pop_valid"].where(sums["pop_valid"] > 0)
    var_tt = sums["tt2w"] / sums["pop_valid"].where(sums["pop_valid"] > 0) - mean_tt ** 2
    std_tt = np.sqrt(np.maximum(var_tt, 0.0))
    pop_g = sums["pop"]
    out = {}
    for t in THRESHOLDS:
        cell_share = 100 * pop[np.isfinite(tt) & (tt <= t)].sum() / total
        reachable_mask = mean_tt.notna() & (mean_tt <= t)
        agg_share = 100 * pop_g[reachable_mask].sum() / total
        std_valid = std_tt.notna() & (pop_g > 0)
        within_std = np.average(std_tt[std_valid], weights=pop_g[std_valid])
        out[f"cell_share_{t}"] = cell_share
        out[f"agg_share_{t}"] = agg_share
        out[f"loss_pp_{t}"] = cell_share - agg_share
        out["within_cell_std_min"] = within_std
    out["iso3"] = iso
    out["service"] = service
    out["resolution_deg"] = resolution
    out["population"] = float(total)
    return out


def main():
    rows = []
    for iso in COUNTRIES:
        for service in ("health", "education"):
            for res in RESOLUTIONS:
                try:
                    rows.append(_grid(iso, service, res))
                except Exception as exc:
                    print(iso, service, res, "FAILED", type(exc).__name__, exc, flush=True)
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "d10_maup_mechanism.csv", index=False, encoding="utf-8-sig")

    # mechanism regression: loss(60 min) ~ within-cell heterogeneity, pooled
    for res in RESOLUTIONS:
        sub = df[df["resolution_deg"] == res].copy()
        x = sub["within_cell_std_min"].to_numpy()
        y = sub["loss_pp_60"].to_numpy()
        if len(x) > 1 and np.nanstd(y) > 0:
            r = np.corrcoef(x, y)[0, 1]
            slope, intercept = np.polyfit(x, y, 1)
            yhat = intercept + slope * x
            r2 = 1 - np.sum((y - yhat) ** 2) / np.sum((y - y.mean()) ** 2)
            print(f"res={res}: n={len(x)}, r={r:.3f}, R^2={r2:.3f}, "
                  f"slope={slope:.3f} pp/min", flush=True)

    # threshold interaction summary
    print("\nmean aggregation loss (pp) by resolution x threshold:")
    for res in RESOLUTIONS:
        sub = df[df["resolution_deg"] == res]
        for t in THRESHOLDS:
            print(f"  {res} {t}min: {sub[f'loss_pp_{t}'].mean():.2f}")
    print("saved", OUT / "d10_maup_mechanism.csv")


if __name__ == "__main__":
    main()
