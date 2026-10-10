# 数据与处理管线记录（Data Pipeline Record）

> 用途：把「原始数据 → 派生数据 → 论文级产物」的完整链路固化下来，方便复现、审计与后续换方向挖掘。
> 更新日期：2026-10-04
> 与本文件并列的索引文件：`DATA_SOURCES.md`（112 条数据源逐项记录）、`EXPERIMENT_REGISTER.md`、`EXPERIMENT_STATUS.md`、`FINAL_MODEL_SPEC.md`。

## 1. 计算环境

- conda 环境 `logistics`，Python 3.11.11。
- 关键版本约束（不可升级，否则破坏 tensorflow 2.12）：numpy 固定在 1.26.4，geopandas 固定在 1.0.1。
- 依赖清单见 `env.yaml`。
- 主要空间栈：geopandas / shapely / rasterio / networkx / scipy。

## 2. 原始数据清单（data/external/，10 类）

1. Planet 主干路面（HeiGIT / HDX 逐国发布）
   - `data/external/hdx/roads/heigit_XX_planet_roadsurface_lines.gpkg`，共 30 个文件（约 30 国）。
   - 关键字段：`DL_road_class_2020`、`DL_road_class_2024`、`rw_class`（宽度）、`Passability_*`（通行性）、`osm_id`。
   - 角色：提供「表面 + 宽度 + 通行性」的主干网络，是 M3 赋速模型的属性来源。

2. HOT OSM 本地道路 + 拓扑 noding 产物
   - `data/external/hdx/countries/{CC}/local_roads/hotosm_roads_gpkg/`（原始本地路）。
   - `data/external/hdx/countries/{CC}/local_roads/{cc}_noded_segments.gpkg`（noding 后的路段，30 国）。
   - 大国另存 parquet 图：`{cc}_noded_segments.parquet` + `_graph_edges.parquet` + `_graph_nodes.parquet`（IND/LKA/NPL 等）。

3. 设施点位（卫生 + 教育，多源并集）
   - OSM/HOT：`data/external/hdx/countries/{CC}/hotosm_{cc}_{health|education}_facilities_*`（points 与 polygons）。
   - 官方注册库（validation/registry）：BGD LGED 教育(2017)、ETH 卫生(2025)、MOZ OCHA MFL 卫生(2017)、IDN 医院+学校 registry、HND 教育 registry。
   - 模型规则（`FINAL_MODEL_SPEC.md`）：官方注册库与 OSM 并集；其余国/服务对用 HOT OSM。

4. WorldPop 2020 1km 人口
   - `data/external/hdx/countries/{CC}/{cc}_pd_2020_1km.tif`（30 国）。
   - ⚠️ 单位是「人口密度」而非绝对人数；若误当绝对人口读取会被高估 1.16–1.82 倍（审计见 EXPERIMENT_STATUS.md 第 7 条）。

5. GHS-SMOD 2020 城乡分类
   - `data/external/ghs/GHS_SMOD_E2020_GLOBE_R2023A_54009_1000_V1_0.tif`（1km）。
   - 已汇总为 `data/final_grid_urban_rural_with_explicit_total.geojson`（约 258 MB）。

6. Global Data Lab SHDI（亚国家发展指数）
   - `data/external/socioeconomic/`：`gdl_regions_v6_7.geojson`、`shdi_30countries_long.csv`、`shdi_table_levels_1_4.json` 等。
   - 覆盖 30 国、约 461 个亚国家单元，可做「发展 × 可达性」耦合分析。

7. 灾害足迹（HDX / UNOSAT / Copernicus EMS）
   - `data/external/hdx/hazards/`：`multi_events/`（BGD/ETH/KEN/MOZ/PAK/PHL 多事件）、`expansion/`（30 国扩展事件）、`validation/`（Idai、Nepal 2026 实测封路）。
   - `data/external/unosat/validation/`：BGD Sylhet 2024、KEN Nairobi 2024 洪泛验证。

8. JRC 洪泛危险性
   - `data/external/jrc_flood/floodMapGL_rp100y/`（100 年一遇洪泛范围）。

9. GRIP4 全球道路密度
   - `data/external/grip4/GRIP4_density_{total,tp1..tp5}/`（按道路类型分级密度栅格）。

10. 外部基准与验证产品
    - `data/external/accessibility_products/weiss_2015/`（Weiss et al. 2015 旅行时间面）。
    - `data/external/map/`（MAP）、`data/external/healthsites/`、`data/external/facility_validation/`。
    - 路由/基准验证：OSRM 553 路线（robust n=181）、Colombia REPS、OCHA ROCCA、Map 基准。

11. Meta/Facebook「Map With AI」AI 预测缺路（卫星提取的第三方独立路网清册，实验 B）
    - 来源：`https://rapideditor.org/country_exports/{CC}_mapwithai_road_data.gpkg.tar.gz`（GeoPackage，gzip 压缩）。
    - 口径：Maxar Premium 高分影像深度学习预测、**缺于 OSM 的道路**；字段 `way_fbid` / `highway_tag` / `wkt` / LineString（EPSG:4326）。
    - 覆盖 10 个代表国：KHM/GTM/BGD/SEN/NGA/ETH/MOZ/PNG/EGY/TUR（与 GRIP4 校准删除 `SUBSET` 一致）。
    - 下载脚本：`explorations/scripts/d21_download_mapwithai.py`；⚠️ rapiditor.org 并发下载会挂起，必须顺序下载并带 (connect, read) 超时重试。
    - 命名澄清：这不是「Meta RADD」——PyPI `radd` 是认知建模包，遥感 RADD 是森林扰动告警，均非路网。

## 3. 派生数据清单（output/）

- `output/experiments/`：72 个实验目录，557 个 CSV。
- `output/experiments/cell_travel_times/{CC}.parquet`（30 国）：逐像元（1km）旅行时间 + 人口 —— 后续 RAI / 冗余 / SHDI 陷阱等新方向的直接原料。
- `output/experiments/mapwithai_crosscheck/`：`ai_cells/{ISO3}_cells.csv`（0.05° 格点：pop_density / grip4_dens_m_km2 / ai_len_m / ai_density_km_km2 / urban_rural）、`ai_country.csv`、`three_way_crosscheck_summary.csv`、`three_way_crosscheck_report.txt`。
- `output/experiments/mapwithai_calibrated_stress/`：`{iso}_mapwithai_calib.csv`、`mapwithai_calib_all.csv`、`mapwithai_calib_summary.csv`。
- `output/paper_ready_*.csv`：主可达性、模型消融、灾害规则敏感性、不平等、SHDI 相关、多事件、路面清单等论文级汇总。
- `output/data_source_index.csv`、`output/experiment_register.csv`、`output/experiment_results_index.csv`：数据源与实验索引。
- `output/maps/`、`output/plots/`、`output/tables/`：图与表产物。

## 4. 处理管线（按阶段）

1. 数据获取：`download_*.py`、`fetch_*.py`、`write_*.py`（HDX/WorldPop/GDL/JRC/UNOSAT 等）。
2. 图构建与拓扑 noding：`run_experiment_24_country_noded_network.py` → `{cc}_noded_segments.gpkg`；大图用内存受限的 `run_experiment_29_corrected_tiled.py`。
3. 赋速模型 M3：速度 = 道路等级 × 表面 × 宽度（`run_access_cost_model.py`、`run_access_cost_grid.py`）。
4. 点位吸附：设施吸附到最近 noded 节点（≤1km）；人口吸附到最近节点（不限距）。
5. 可达性：Dijkstra 最短路，主口径「60 分钟内人口占比」，辅以 30/120/240 分钟。
6. 局部路效应分解：`run_nested_counterfactual.py`、`run_shapley_decomposition.py`、置换零模型。
7. 压力测试：`run_missing_road_stress.py`、`run_nonrandom_missing_road_stress.py`、`run_grip4_calibrated_stress.py`（缺路 / 未铺装 / GRIP4 定标）；`explorations/scripts/d21_mapwithai_crosscheck.py`、`d21_ai_calibrated_stress.py`（Meta 卫星缺路三方交叉 + AI 锚定标）。
8. 灾害情景与零模型：`run_hazard_null_model.py`、`run_spatial_null_model.py`（随机布设 vs 实测）。
9. 验证：`run_routing_validation*.py`（OSRM）、Idai / Nepal 2026 实测封路、`run_colombia_reps_validation.py`、`run_map_benchmark.py`。
10. 异质性与社会经济：`run_shdi_30countries.py`、`run_experiment_15_urban_rural.py`、`run_experiment_17_inequality.py`。

## 5. 关键口径与边界（来自 FINAL_MODEL_SPEC.md / EXPERIMENT_STATUS.md）

- 主模型：noded Planet 主干 + HOT OSM 本地路；M3 赋速；WorldPop 2020；官方注册库并集设施；直接表面感知灾害规则。
- 灾害损失口径为正：baseline − surface-aware hazard。
- 禁止声明：全球估计、年度期望损失、未来气候风险、因果社会经济效应、完整门到门可达性、精确投资优化。
- 洪泛足迹是「情景输入」，不是年度期望损失。
- 已知偏误：WorldPop 密度单位误读（人口膨胀）、Web-Mercator 段长（高纬最多 +35% 旅行时间）。

## 6. 复现提示

- 主结果链：先确认 `{cc}_noded_segments.gpkg` 存在 → 跑 `run_access_cost_model.py` 生成成本网格 → 逐国可达性 → 用 `build_paper_ready_results.py` 汇总。
- 快速核对数据源：`DATA_SOURCES.md` + `output/data_source_index.csv`。
- 任何新分析优先复用 `output/experiments/cell_travel_times/*.parquet`（已含逐像元旅行时间与人口），避免重跑 Dijkstra。

## 7. 审稿补充实验 B（三方清册交叉）结果

- 数据：Meta Map With AI AI 预测缺路（10 国，合计约 740 万 km，约为模型本地路 356 万 km 的 2.1 倍）。
- 乡村集中度：10 国平均 86% 的 AI 缺路位于乡村像元（孟加拉国例外 23%，其余 9 国 85–97%）。
- 国别层面：AI 缺路/本地路 与 GRIP4 总密度 Spearman **−0.79**（GRIP4 越稀疏、卫星缺口越大）。
- 双锚校准删除（方向一致）：
  - GRIP4 锚：删除比例均值 0.78，60 分钟份额损失 48.3 pp（同比例随机 61.9 pp，低 13.7 pp）。
  - AI 锚：删除比例均值 0.64，损失 38.1 pp（同比例随机 59.7 pp，低 21.6 pp）。
  - 两锚删除比例 Spearman +0.63、损失 Spearman +0.55。
- 结论：可达性对本地路完整度高度敏感，且该结论对清册选择稳健。
- 产物：`three_way_crosscheck_summary.csv`、`mapwithai_calib_summary.csv`；SI S18.4。
