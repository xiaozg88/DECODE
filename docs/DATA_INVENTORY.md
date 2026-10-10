# Data inventory (读者向数据清册)

本文件汇总本文用到的**全部数据**：上游输入数据（来源、年份、许可、可复现获取方式）与
本文生成的**派生数据表**（文件、内容、生成脚本、支撑的正文位置），并给出
"关键数字 → 数据文件"对照表，供读者定位、核对与复用。

> 仓库根目录另有 `DATA_PIPELINE_RECORD.md`（管线）、`EXPANSION_DATA_AUDIT.md` /
> `EXPANSION_DATA_PROVENANCE.md`（逐国溯源）；本文件是面向读者的汇总入口。

## 0. 一句话总览

- **样本**：30 国分层目的性样本（7 核心国 + 23 扩充国；3 个收入组、6 个区域、
  路网密度 0.175–2.56 km/km²），总人口 34.5 亿；用于机制性推断，不作全球比例/总量推断。
- **核心输入**：Planet 主干路面线 + HOT/OSM 本地路与设施 + WorldPop 2020 +
  GHS-SMOD 2020 + SHDI 2020 + 灾害足迹/JRC 洪泛。
- **独立对照**：MAP 2020、Weiss & Nelson 2015、CPAS/Data for Children、SDG 9.1.1
  RAI 2023、GRIP4、Meta Map With AI、OSRM。
- **派生数据**：`release/data/` 下约 60 张表，CC BY 4.0；上游原始栅格/线要素不随包
  分发，仅记录来源与校验和。

## 1. 上游输入数据（不随包分发，仅记录来源）

| 数据 | 年份 | 用途 | 来源 / 许可 |
|---|---:|---|---|
| Planet 主干路面/宽度线 | 2024 | 主干路网（路面、宽度、速度） | HeiGIT/HDX `heigit_*_planet_roadsurface_lines.gpkg`；随原数据条款，不再分发线要素 |
| HOT/OSM 本地路 | 2026-05-05 ~ 09-10 快照 | 本地路网、noding | OpenStreetMap/HOT 导出，ODbL 1.0 |
| HOT/OSM 设施（医院/诊所/学校） | 2026 快照 | 服务可达性源点 | OpenStreetMap/HOT，ODbL 1.0 |
| WorldPop 2020 1 km 人口 | 2020 | 人口权重 | WorldPop，CC BY 4.0 |
| GHS-SMOD 2020（1 km） | 2020 | 城乡掩膜（乡村=11–13） | European Commission JRC，署名可复用 |
| Global Data Lab SHDI | 2020 | 发展水平对照 | Global Data Lab |
| 灾害事件足迹 | 2015–2026 | 暴露/损失情景 | UNOSAT/OCHA/WFP via HDX，按各数据集条款 |
| JRC 100 年河流洪泛图 | 1 km | 统一洪泛暴露层 | JRC |
| GRIP4 路网密度 | ≈2009 | 完整度清册锚 | Meijer et al. 2018 |
| MAP 2020 医疗旅行时间 | 2020 | 30 国独立外部靶子 | Malaria Atlas Project，Weiss et al. 2020 |
| Weiss & Nelson 2015 | 2015 | 第二个 30 国外部产品（到 ≥5 万人口城镇） | Weiss et al. 2015 |
| CPAS/Data for Children 100 m 卫生旅行时间 | 最新 | 3 国格网级同服务靶子（ETH/KEN/MOZ） | HDX（见 `data/external/accessibility_products/cpas/README.md`） |
| SDG 9.1.1 Rural Access Index 2023 | 2023 | 30 国官方指标靶子 | CIESIN/NASA SEDAC，CC BY 4.0，doi:10.7910/DVN/FFQ1WT |
| Meta "Map With AI" 缺路 | 最新 | 第二套独立缺路清册 | rapideditor.org 导出 |
| OSRM 路线引擎 | — | 553 条路线验证 | Open Source Routing Machine |

## 2. 派生数据表（随包分发，CC BY 4.0）

完整文件与 SHA256 见 `MANIFEST.csv`。核心表的逐列定义见 `DATA_DICTIONARY.md`；
其余新表（e4/e5/e6、nested_decomposition、interstudy、d08/d09 等）列名在 CSV 表头中
自解释。按主题分组：

### 2.1 主结果与分解

- `corrected_main_access_30countries.csv`：30 国 × 卫生/教育 × 口径/单位/长度的 60 分钟份额与修正量。
- `nested_decomposition.csv`：核心分解（Δ_edge / Δ_conv / Δ_total / 基线差 / 协议差，60 行）。
- `interstudy_60min_comparison.csv`：四产品（Weiss/MAP/主干/全路）60 分钟份额对照。
- `d09_access_identity_flip_summary.csv`：9.85 亿人身份翻转（逐像元口径差）。

### 2.2 外部靶子

- `e4_external_target.csv / .json`：五组差分形式 × OLS/LOCO/方向/负值/零模型。
- `e4_external_target_sensitivity.csv`：剔除 PNG 后的稳健性。
- `e5_cpas_*.csv / .json`：CPAS 格网级同服务靶子（ETH/KEN/MOZ）。
- `e6_rai_*.csv / .json`：SDG 9.1.1 RAI 外部靶子（30 国）。
- `map_health_travel_time_vs_model.csv`：MAP 2020 与本文模型逐国对照。

### 2.3 敏感性 / 稳健性 / 零模型

- `effect_distributions.csv`：效应分布自助区间与排名敏感性。
- `e1_edge_by_threshold.csv`、`e2b_null_models.json`、`e3_results.json`：边增量阈值、三种置换零模型、稳健推断。
- `spatial_null_model.csv`、`hazard_null_model.csv`：暴露—损失零模型。
- `stress_all.csv`、`stress_nonrandom_summary.csv`、`grip4_calib_summary.csv`、`mapwithai_calib_summary.csv`、`three_way_crosscheck_summary.csv`：路网完整度压力测试与三方清册。
- `access_cost_all_countries.csv`：显式接入成本敏感性。
- `d10_maup_mechanism.csv`、`d11_decomposition_orders.csv`、`d13_facility_road_2x2.csv`：MAUP、分解顺序、设施×路网 2×2。
- `d17_extra_country_sensitivity.csv`、`d19_extra_country_edge_sign.csv`、`d20_noding_equivalence.csv`：5 国样本外与 noding 等价。

### 2.4 SDG 9.1.1 / 城乡 / 服务

- `d01_rai.csv`：全人口 2 km 铺装/全路占比（d01）。
- `d08_sdg_rai_rural_corrected.csv`、`d12_sdg_reproduction_table.csv`：乡村口径（11–13）RAI 与误判人口（4780 万）。
- `urban_rural_expansion.csv`、`facility_scenario_shares.csv`、`facility_registry_bottleneck.csv`、`facility_quality_by_country.csv`：城乡、设施定义、独立登记册。
- `d04_connectivity_all.csv`、`d05_top_education_deserts.csv`、`d05_top_health_deserts.csv`：路网连通性与服务沙漠。

### 2.5 审计 / 溯源 / 框架

- `numerical_audit.csv`：关键数字回算审计。
- `expansion_data_provenance.csv`：逐国输入来源/路径/字节/校验。
- `sample_coverage.csv`：分层目的性样本覆盖。
- `osm_snapshot_dates.csv`：逐国快照日期。
- `shapley_all_countries.csv`：Shapley 分解。

## 3. 关键数字 → 数据文件对照

| 正文关键数字 | 数据文件 |
|---|---|
| 9.85 亿人（28.6%）可达身份取决于口径 | `d09_access_identity_flip_summary.csv` |
| 4780 万乡村人口被误判 / 38.8 pp（SDG 9.1.1） | `d08_sdg_rai_rural_corrected.csv` |
| 外部靶子 MAP−主干 R²=0.754 / LOCO 0.717 | `e4_external_target.csv` |
| CPAS 格网级 R²（ETH/KEN/MOZ） | `e5_cpas_regression.csv` |
| RAI 外部靶子 R²=0.746 / 官方−主干 32.4 pp | `e6_rai_external_target.csv` |
| 同定义 18.8 pp / 跨产品 30.7 pp | `interstudy_60min_comparison.csv` |
| Δ_edge / Δ_conv / Δ_total 分解 | `nested_decomposition.csv` |
| 三种置换零模型分位 | `e2b_null_models.json` |
| 未铺装失效 61.6 pp / 城乡差距 49.2 pp | `corrected_main_access_30countries.csv` |

## 4. 数据可用性（Data availability）

派生数据表以 **CC BY 4.0** 发布于本文数据仓（Zenodo/GitHub，DOI 见投稿版）。分析代码以
**MIT** 许可发布于同一仓库。上游原始数据（Planet 线要素、WorldPop、GHS-SMOD、OSM、灾害
足迹、MAP/CPAS/RAI 等）按各自条款使用、**不随本包分发**；其获取地址、年份、许可与
SHA256 记录于本文方法 §4.1、补充表 S8 及
`data/external/accessibility_products/{cpas,rai_sdg911}/README.md`。
