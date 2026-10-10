# -*- coding: utf-8 -*-
"""Experiment C (advisory): positively quantify capacity-attribute availability.

The honest finding is that no open dataset carries usable capacity fields; this
quantifies that absence across four sources (healthsites + three national registries),
which supports the paper's "capacity is not cross-country comparable" limitation.
"""
from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "explorations" / "output"
HS = ROOT / "data" / "external" / "healthsites"
VAL = ROOT / "data" / "external" / "facility_validation"


def main():
    rows = []

    # healthsites: beds/staff coverage
    for f in sorted(HS.glob("*_healthsites.csv")):
        iso = f.stem.split("_")[0].upper()
        df = pd.read_csv(f, low_memory=False)
        n = len(df)
        def col(name):
            if name in df.columns:
                return pd.to_numeric(df[name], errors="coerce").fillna(0)
            return pd.Series(0.0, index=df.index)
        beds = col("beds")
        doctors = col("staff_doctors")
        nurses = col("staff_nurses")
        rows.append({
            "source": "healthsites", "iso3": iso, "records": n,
            "capacity_field": "beds/staff",
            "coverage_pct": 100 * ((beds > 0) | (doctors > 0) | (nurses > 0)).mean(),
            "has_bed_count": bool((beds > 0).any()),
            "has_staff_count": bool(((doctors > 0) | (nurses > 0)).any()),
        })

    # national registries: do they carry capacity?
    reg = {
        "ETH": VAL / "ETH_health_facilities_2025" / "Ethiopian_health_Facilities" / "Ethiopian Health Facilities.shp",
        "MOZ": VAL / "MOZ_MFL_health_2017" / "Mozambique-health-facilities" / "mozambique-healthfacilities.shp",
        "BGD": VAL / "BGD_LGED_education_2017" / "bgd_poi_educationfacilities_lged.shp",
    }
    for iso, f in reg.items():
        try:
            g = gpd.read_file(f)
        except Exception as exc:
            rows.append({"source": f"registry:{iso}", "iso3": iso, "records": 0,
                         "capacity_field": "n/a", "coverage_pct": np.nan,
                         "has_bed_count": False, "has_staff_count": False,
                         "error": type(exc).__name__})
            continue
        cols = [c.lower() for c in g.columns]
        has_bed = any("bed" in c for c in cols)
        has_staff = any(k in c for k in ("staff", "teacher", "student", "doctor", "nurse") for c in cols)
        rows.append({
            "source": f"registry:{iso}", "iso3": iso, "records": len(g),
            "capacity_field": "none" if not (has_bed or has_staff) else "partial",
            "coverage_pct": 0.0,
            "has_bed_count": has_bed,
            "has_staff_count": has_staff,
        })

    df = pd.DataFrame(rows)
    df.to_csv(OUT / "d14_capacity_availability.csv", index=False, encoding="utf-8-sig")
    print(df.to_string(index=False))
    print()
    print("任何来源含床位字段:", bool(df["has_bed_count"].any()))
    print("任何来源含人员/教师字段:", bool(df["has_staff_count"].any()))
    print("saved", OUT / "d14_capacity_availability.csv")


if __name__ == "__main__":
    main()
