# -*- coding: utf-8 -*-
"""
Planet Roads Plots — 本地可运行分析脚本
========================================
基于 notebooks/ExplorativeAnalysis_Documented.ipynb 的分析逻辑，
使用 data/ 目录下已有的中间产物（2 度网格 GeoJSON）复现：
  1. 网格级铺装度（pavedness）2020/2024/变化 —— total/urban/rural
  2. 网格级未知道路比例（unknown share）2020/2024/变化
  3. 国家级铺装度汇总表（ISO3 + World Bank region，取自 Natural Earth）
  4. Mollweide 投影世界地图（铺装度 / 未知比例 / 国家 choropleth）

原始逐路 parquet（road_surfaces 2016/2020/2024）不在本地，
其聚合结果已由 data/final_grid_urban_rural_with_explicit_total.geojson 提供。

运行：python run_analysis.py
输出：output/maps/*.gpkg, output/plots/*.png, output/tables/*.csv
"""
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.colors import LinearSegmentedColormap

warnings.filterwarnings("ignore")

# ------------------------------------------------------------------ 配置
ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
GRID_GEOJSON = DATA_DIR / "final_grid_urban_rural_with_explicit_total.geojson"
WORLD_ZIP = DATA_DIR / "ne_110m_admin_0_countries.zip"

OUTPUT_DIR = ROOT / "output"
MAPS_DIR = OUTPUT_DIR / "maps"
PLOTS_DIR = OUTPUT_DIR / "plots"
TABLES_DIR = OUTPUT_DIR / "tables"
for d in (MAPS_DIR, PLOTS_DIR, TABLES_DIR):
    d.mkdir(parents=True, exist_ok=True)

CRS_WGS84 = "EPSG:4326"
CRS_MOLLWEIDE = "ESRI:54009"
YEARS = (2016, 2020, 2024)
AREAS = ("total", "urban", "rural")

# 论文配色（README / Coverage notebook 一致）
COLORS = {"paved": "#6A8E5A", "unpaved": "#C4A46A", "unknown": "#B8B8B8"}

t0 = time.time()


def log(msg):
    print(f"[{time.time() - t0:7.1f}s] {msg}", flush=True)


# ------------------------------------------------------------------ 1. 加载数据
log("加载网格 GeoJSON（46 万行，约 20 秒）...")
gdf = gpd.read_file(GRID_GEOJSON)
log(f"网格记录: {len(gdf):,}  CRS: {gdf.crs}")
log(f"urban_rural 取值: {gdf['urban_rural'].value_counts().to_dict()}")

log("加载 Natural Earth 国家边界...")
world = gpd.read_file(WORLD_ZIP)
world_no_antarctica = world[world["NAME"] != "Antarctica"].copy()

# ISO2 -> ISO3 映射（替代 notebook 中的 pycountry + World Bank API）
iso_map = {}
for _, r in world.iterrows():
    a2, a3 = str(r.get("ISO_A2_EH", "")), str(r.get("ISO_A3_EH", ""))
    if len(a2) == 2 and a2 != "-9" and len(a3) == 3 and a3 != "-99":
        iso_map[a2] = a3
log(f"ISO2->ISO3 映射：{len(iso_map)} 个国家")

# ------------------------------------------------------------------ 2. 铺装度计算（notebook cell 17）
def compute_pavedness(gdf_in, region_type="total"):
    """网格级铺装度 = paved 长度 / (paved + unpaved) 长度 × 100%。"""
    gdf_work = gdf_in.to_crs(CRS_MOLLWEIDE).copy()

    def aggregate_year(year):
        rc, ln = f"road_class_{year}", f"length_{year}"
        df = gdf_work[(gdf_work[rc].isin(["paved", "unpaved"])) &
                      (gdf_work["urban_rural"] == region_type)]
        grouped = df.groupby(["grid_id", "geometry", rc])[ln].sum().reset_index()
        grouped = gpd.GeoDataFrame(grouped, geometry="geometry", crs=gdf_work.crs)
        paved = grouped[grouped[rc] == "paved"].copy()
        unpaved = grouped[grouped[rc] == "unpaved"].copy()
        merged = paved.merge(unpaved, on=["grid_id", "geometry"], suffixes=("_paved", "_unpaved"))
        merged["pavedness"] = 100 * merged[f"{ln}_paved"] / (
            merged[f"{ln}_paved"] + merged[f"{ln}_unpaved"])
        return merged

    g2020, g2024 = aggregate_year(2020), aggregate_year(2024)
    change = g2024.merge(g2020, on=["grid_id", "geometry"], suffixes=("_2024", "_2020"))
    change["change"] = change["pavedness_2024"] - change["pavedness_2020"]
    change = gpd.GeoDataFrame(change, geometry="geometry", crs=gdf_work.crs)
    return {"2020": g2020, "2024": g2024, "change": change}


# ------------------------------------------------------------------ 3. 未知比例计算（notebook cell 18）
def compute_unknown_share(gdf_in, region_type="total"):
    """网格级 unknown 长度占全部道路长度比例（%）。"""
    gdf_work = gdf_in.to_crs(CRS_MOLLWEIDE).copy()

    def aggregate_year(year):
        rc, ln = f"road_class_{year}", f"length_{year}"
        df = gdf_work[(gdf_work[rc].isin(["paved", "unpaved", "unknown"])) &
                      (gdf_work["urban_rural"] == region_type)]
        grouped = df.groupby(["grid_id", "geometry", rc])[ln].sum().reset_index()
        grouped = gpd.GeoDataFrame(grouped, geometry="geometry", crs=gdf_work.crs)
        paved = grouped[grouped[rc] == "paved"].rename(columns={ln: "length_paved"})
        unpaved = grouped[grouped[rc] == "unpaved"].rename(columns={ln: "length_unpaved"})
        unknown = grouped[grouped[rc] == "unknown"].rename(columns={ln: "length_unknown"})
        merged = (paved.merge(unpaved, on=["grid_id", "geometry"], how="outer")
                       .merge(unknown, on=["grid_id", "geometry"], how="outer"))
        for col in ("length_paved", "length_unpaved", "length_unknown"):
            merged[col] = merged[col].fillna(0)
        denom = merged["length_paved"] + merged["length_unpaved"] + merged["length_unknown"]
        merged["unknown_share"] = np.where(denom > 0, 100 * merged["length_unknown"] / denom, 0.0)
        return gpd.GeoDataFrame(merged, geometry="geometry", crs=gdf_work.crs)

    g2020, g2024 = aggregate_year(2020), aggregate_year(2024)
    change = g2024.merge(g2020, on=["grid_id", "geometry"], suffixes=("_2024", "_2020"))
    change["change"] = change["unknown_share_2024"] - change["unknown_share_2020"]
    change = gpd.GeoDataFrame(change, geometry="geometry", crs=gdf_work.crs)
    return {"2020": g2020, "2024": g2024, "change": change}


# ------------------------------------------------------------------ 4. 运行并导出 GeoPackage
pavedness_gpkg = MAPS_DIR / "pavedness.gpkg"
unknown_gpkg = MAPS_DIR / "unknown_share.gpkg"
for p in (pavedness_gpkg, unknown_gpkg):
    if p.exists():
        p.unlink()

pavedness_results, unknown_results = {}, {}
for rt in AREAS:
    log(f"计算铺装度 ({rt}) ...")
    res = compute_pavedness(gdf, rt)
    pavedness_results[rt] = res
    for tag, g in res.items():
        g.to_crs(CRS_WGS84).to_file(pavedness_gpkg, layer=f"pavedness_{tag}_{rt}" if tag != "change" else f"change_2020_2024_{rt}", driver="GPKG")
    log(f"  铺装度图层: 2020={len(res['2020'])}, 2024={len(res['2024'])}, change={len(res['change'])}")

for rt in AREAS:
    log(f"计算未知比例 ({rt}) ...")
    res = compute_unknown_share(gdf, rt)
    unknown_results[rt] = res
    for tag, g in res.items():
        g.to_crs(CRS_WGS84).to_file(unknown_gpkg, layer=f"unknown_share_{tag}_{rt}" if tag != "change" else f"unknown_share_change_{rt}", driver="GPKG")
    log(f"  未知比例图层: 2020={len(res['2020'])}, 2024={len(res['2024'])}, change={len(res['change'])}")

log(f"已导出 {pavedness_gpkg.relative_to(ROOT)} 与 {unknown_gpkg.relative_to(ROOT)}")

# ------------------------------------------------------------------ 5. 国家级汇总表（notebook cell 15/20 思路）
log("计算国家级铺装度表 ...")
ctry = gdf.copy()
ctry["iso_A3"] = ctry["country"].map(iso_map)

rows = []
for year in YEARS:
    rc, ln = f"road_class_{year}", f"length_{year}"
    d = ctry[ctry[rc].isin(["paved", "unpaved"])]
    grp = d.groupby(["iso_A3", "urban_rural", rc])[ln].sum().reset_index()
    for (iso3, area), sub in grp.groupby(["iso_A3", "urban_rural"]):
        lp = sub.loc[sub[rc] == "paved", ln].sum()
        lu = sub.loc[sub[rc] == "unpaved", ln].sum()
        if lp + lu > 0:
            rows.append({"iso_A3": iso3, "urban_rural": area, "year": year,
                         "length_paved_m": lp, "length_unpaved_m": lu,
                         "pavedness_pct": 100 * lp / (lp + lu)})
country_long = pd.DataFrame(rows)

# 世界银行区域信息取自 Natural Earth（替代 World Bank API）
ne_regions = world_no_antarctica[["ISO_A3_EH", "REGION_WB", "CONTINENT", "SUBREGION"]].drop_duplicates("ISO_A3_EH")
country_long = country_long.merge(ne_regions, left_on="iso_A3", right_on="ISO_A3_EH", how="left")
country_long.drop(columns=["ISO_A3_EH"], inplace=True)
country_long.to_csv(TABLES_DIR / "country_pavedness_long.csv", index=False, encoding="utf-8-sig")

# 宽表（每国一行：total/urban/rural）
wide = country_long.pivot_table(index=["iso_A3", "year"], columns="urban_rural",
                                values="pavedness_pct").reset_index()
wide.columns.name = None
wide = wide.rename(columns={"total": "pavedness_total_pct",
                            "urban": "pavedness_urban_pct",
                            "rural": "pavedness_rural_pct"})
wide = wide.merge(ne_regions, left_on="iso_A3", right_on="ISO_A3_EH", how="left").drop(columns=["ISO_A3_EH"])
wide.to_csv(TABLES_DIR / "country_pavedness_wide.csv", index=False, encoding="utf-8-sig")
log(f"国家级表：{wide['iso_A3'].nunique()} 个国家，{len(wide)} 行 -> output/tables/")

# 区域汇总（World Bank region）
region_summary = (country_long[country_long["urban_rural"] == "total"]
                  .groupby(["year", "REGION_WB"])["pavedness_pct"]
                  .agg(["mean", "std", "count"]).round(2).reset_index())
region_summary.to_csv(TABLES_DIR / "pavedness_by_wb_region.csv", index=False, encoding="utf-8-sig")

# world_merged GeoPackage：国家边界 + 2024 铺装度
w24 = wide[wide["year"] == 2024].drop(columns=["year"])
# 去掉与 NE 重复的区域字段；GPKG 字段名不区分大小写，改用 paved_iso3 避免与 ISO_A3 冲突
w24 = (w24.drop(columns=["REGION_WB", "CONTINENT", "SUBREGION"], errors="ignore")
          .rename(columns={"iso_A3": "paved_iso3"}))
world_merged = world.merge(w24, left_on="ISO_A3_EH", right_on="paved_iso3", how="left").drop(columns=["paved_iso3"])
world_merged_path = MAPS_DIR / "world_merged.gpkg"
if world_merged_path.exists():
    world_merged_path.unlink()
world_merged.to_file(world_merged_path, layer="world_merged", driver="GPKG")
log(f"已导出 {world_merged_path.relative_to(ROOT)}")

# ------------------------------------------------------------------ 6. 绘图
PAV_CMAP = LinearSegmentedColormap.from_list(
    "pavedness", ["#C4A46A", "#E8D9A8", "#DCE5C8", "#A8C08A", "#6A8E5A"])
UNK_CMAP = LinearSegmentedColormap.from_list(
    "unknown", ["#FFFFFF", "#D9D9D9", "#B8B8B8", "#8C8C8C", "#595959"])

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.size": 8, "axes.titlesize": 9, "axes.labelsize": 8,
    "xtick.labelsize": 7, "ytick.labelsize": 7,
})


def world_base(ax, title):
    """Mollweide 底图（裁剪 65S 以南）。"""
    ax.set_facecolor("#eef2f5")
    world_no_antarctica.to_crs(CRS_MOLLWEIDE).plot(
        ax=ax, facecolor="lightgrey", edgecolor="white", linewidth=0.4, zorder=1)
    ax.set_xlim(-1.55e7, 1.55e7)
    ax.set_ylim(-9.5e6, 9.5e6)
    ax.set_xticks([]); ax.set_yticks([])
    for s in ax.spines.values():
        s.set_edgecolor("#999999"); s.set_linewidth(0.6)
    ax.set_title(title, fontweight="bold", pad=8)


def grid_map(g, column, cmap, vmin, vmax, title, fname, label):
    fig, ax = plt.subplots(figsize=(10, 5.2), dpi=200)
    world_base(ax, title)
    g.plot(column=column, cmap=cmap, vmin=vmin, vmax=vmax, ax=ax,
           edgecolor="none", zorder=2, legend=False)
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(vmin=vmin, vmax=vmax))
    cb = fig.colorbar(sm, ax=ax, orientation="horizontal", fraction=0.035, pad=0.04)
    cb.set_label(label, fontsize=8)
    fig.tight_layout()
    fig.savefig(PLOTS_DIR / fname, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    log(f"  图: plots/{fname}")


log("绘制地图 ...")
for rt in AREAS:
    grid_map(pavedness_results[rt]["2024"], "pavedness", PAV_CMAP, 0, 100,
             f"Grid-cell road pavedness 2024 — {rt}", f"pavedness_2024_{rt}.png",
             "Pavedness (%)")
    grid_map(pavedness_results[rt]["2020"], "pavedness", PAV_CMAP, 0, 100,
             f"Grid-cell road pavedness 2020 — {rt}", f"pavedness_2020_{rt}.png",
             "Pavedness (%)")
    ch = pavedness_results[rt]["change"]
    vmax = float(np.nanmax(np.abs(ch["change"]))) or 1
    grid_map(ch, "change", plt.cm.RdYlGn, -vmax, vmax,
             f"Pavedness change 2020–2024 — {rt}", f"pavedness_change_{rt}.png",
             "Δ pavedness (pp)")
    grid_map(unknown_results[rt]["2024"], "unknown_share", UNK_CMAP, 0, 100,
             f"Unknown road surface share 2024 — {rt}", f"unknown_share_2024_{rt}.png",
             "Unknown share (%)")

# 国家 choropleth（2024 total）
fig, ax = plt.subplots(figsize=(10, 5.2), dpi=200)
world_base(ax, "Country-level road pavedness 2024 (model prediction)")
wplot = world_merged[world_merged["NAME"] != "Antarctica"].to_crs(CRS_MOLLWEIDE)
missing = wplot["pavedness_total_pct"].isna()
wplot[missing].plot(ax=ax, facecolor="#f0f0f0", edgecolor="white", linewidth=0.4, zorder=2)
wplot[~missing].plot(column="pavedness_total_pct", cmap=PAV_CMAP, vmin=0, vmax=100,
                     ax=ax, edgecolor="white", linewidth=0.4, zorder=3, legend=False)
sm = plt.cm.ScalarMappable(cmap=PAV_CMAP, norm=plt.Normalize(0, 100))
cb = fig.colorbar(sm, ax=ax, orientation="horizontal", fraction=0.035, pad=0.04)
cb.set_label("Pavedness (%)", fontsize=8)
fig.tight_layout()
fig.savefig(PLOTS_DIR / "country_pavedness_2024.png", bbox_inches="tight", facecolor="white")
plt.close(fig)
log("  图: plots/country_pavedness_2024.png")

# 区域柱状图（2024）
fig, ax = plt.subplots(figsize=(8, 4.2), dpi=200)
reg = (country_long[(country_long["year"] == 2024) & (country_long["urban_rural"].isin(["urban", "rural"]))]
       .groupby(["REGION_WB", "urban_rural"])["pavedness_pct"].mean().unstack())
reg = reg.sort_values("rural", ascending=False)
x = np.arange(len(reg)); w = 0.38
ax.bar(x - w/2, reg["urban"], w, label="Urban", color="#5B7FBC", edgecolor="white", linewidth=0.5)
ax.bar(x + w/2, reg["rural"], w, label="Rural", color="#C4A46A", edgecolor="white", linewidth=0.5)
ax.set_xticks(x)
ax.set_xticklabels([t.replace(" ", "\n", 1) for t in reg.index], fontsize=7)
ax.set_ylabel("Mean pavedness (%)")
ax.set_title("Mean road pavedness by World Bank region, 2024", fontweight="bold")
ax.legend(frameon=False)
ax.grid(axis="y", color="#e0e0e0", linewidth=0.5)
ax.set_axisbelow(True)
fig.tight_layout()
fig.savefig(PLOTS_DIR / "pavedness_by_region_2024.png", bbox_inches="tight", facecolor="white")
plt.close(fig)
log("  图: plots/pavedness_by_region_2024.png")

# ------------------------------------------------------------------ 7. 摘要
log("生成摘要 ...")
summary = []
for rt in AREAS:
    p24 = pavedness_results[rt]["2024"]
    p20 = pavedness_results[rt]["2020"]
    u24 = unknown_results[rt]["2024"]
    tot24 = gdf[(gdf["urban_rural"] == rt)]["length_2024"].sum() / 1000
    summary.append({
        "area": rt,
        "grid_cells_2024": len(p24),
        "mean_pavedness_2020_pct": round(p20["pavedness"].mean(), 2),
        "mean_pavedness_2024_pct": round(p24["pavedness"].mean(), 2),
        "length_weighted_pavedness_2024_pct": round(
            100 * p24["length_2024_paved"].sum() /
            (p24["length_2024_paved"].sum() + p24["length_2024_unpaved"].sum()), 2),
        "mean_unknown_share_2024_pct": round(u24["unknown_share"].mean(), 2),
        "total_road_length_2024_km": round(tot24, 0),
    })
summary_df = pd.DataFrame(summary)
summary_df.to_csv(TABLES_DIR / "summary.csv", index=False, encoding="utf-8-sig")

print("\n" + "=" * 78)
print("运行完成 — 摘要")
print("=" * 78)
print(summary_df.to_string(index=False))
print("\n输出目录：")
print(f"  地图图层  output/maps/   (pavedness.gpkg, unknown_share.gpkg, world_merged.gpkg)")
print(f"  图形文件  output/plots/  ({len(list(PLOTS_DIR.glob('*.png')))} 张 PNG)")
print(f"  数据表    output/tables/ (country_pavedness_long/wide.csv, summary.csv 等)")
log(f"总耗时 {time.time() - t0:.1f}s")
