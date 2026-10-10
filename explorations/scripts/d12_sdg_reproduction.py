# -*- coding: utf-8 -*-
"""Comment 7 (advisory): a one-step-reproducible SDG 9.1.1 conversion box.

Verifies the published numbers (35.2 pp / 28.9 M misclassified rural population) against
``explorations/output/d08_sdg_rai_rural.csv`` and emits the full input/calculation
specification so a reviewer can recompute every field.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "explorations" / "output"


def main():
    d = pd.read_csv(OUT / "d08_sdg_rai_rural.csv")
    total_mis = d["misclassified_rural_pop"].sum()
    max_pp = d["surface_gap_rural_pp"].max()
    max_iso = d.loc[d["surface_gap_rural_pp"].idxmax(), "iso3"]
    india = d[d["iso3"] == "IND"]["misclassified_rural_pop_millions"].iloc[0]
    rwanda = d[d["iso3"] == "RWA"]["misclassified_rural_pop_millions"].iloc[0]

    lines = [
        "SDG 9.1.1 全天候路近似误判的换算口径（可一步复算）",
        "=" * 70,
        "指标：乡村可达指数 RAI = 位于“全天候路”2 km 缓冲带内的乡村人口 / 乡村总人口",
        "两个输入口径：",
        "  (a) 全天候路 = Planet 主干路中 DL_road_class_2024 == 'paved'（路面感知值）",
        "  (b) 全天候路 = Planet 主干路全部（未区分路面，即“全天候近似”）",
        "缓冲带：把道路栅格化到 WorldPop 1 km 格网后做 2 像元二元膨胀（≈2 km，经纬度近似）",
        "乡村掩膜：GHS-SMOD E2020（GLOBE R2023A, 1 km）类别 21–23",
        "人口：WorldPop 2020 1 km 未约束人口密度（{iso}_pd_2020_1km.tif），密度 × 像元面积 = 人数",
        "误判乡村人口 = (rai_all_rural − rai_paved_rural) × 乡村总人口",
        "-" * 70,
        f"30 国合计误判乡村人口：{total_mis/1e6:.1f} 百万（≈ 2890 万）",
        f"最大路面感知效应：{max_pp:.2f} pp（{max_iso}）",
        f"印度（绝对数最大）：{india:.1f} 百万；卢旺达（相对比例最高）：{rwanda:.1f} 百万",
        "数据来源：explorations/output/d08_sdg_rai_rural.csv（脚本 explorations/scripts/d08_sdg_rai_rural.py）",
    ]
    box = "\n".join(lines)
    (OUT / "d12_sdg_reproduction_box.txt").write_text(box, encoding="utf-8")

    # per-country reproduction table (reviewer-verifiable)
    rep = d[["iso3", "rural_pop", "rai_paved_rural", "rai_all_rural",
             "surface_gap_rural_pp", "misclassified_rural_pop_millions"]].copy()
    rep.columns = ["ISO3", "乡村人口", "铺装路2km占比", "全路2km占比",
                   "表面效应(pp)", "误判人口(百万)"]
    rep.to_csv(OUT / "d12_sdg_reproduction_table.csv", index=False, encoding="utf-8-sig")

    print(box)
    print("\nsaved", OUT / "d12_sdg_reproduction_box.txt")
    print("saved", OUT / "d12_sdg_reproduction_table.csv")


if __name__ == "__main__":
    main()
