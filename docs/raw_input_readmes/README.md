# SDG Indicator 9.1.1: Rural Access Index (RAI), 2023 Release

## 数据用途

用于论文“第二个 30 国可比外部产品”实验（`run_v34_e6_rai_external_target.py`，
实验 E6 / 方案 C）。该产品由 CIESIN（Columbia University）与 NASA SEDAC 联合
发布，覆盖 **209 个国家 + 45 个次国家级单位**，与 MAP 2020 相互独立，定义明确：

> 乡村人口中，居住点位于最近“全天候（铺装）道路”2 km 缓冲带内的比例（百分比）。

本文仅使用国家级值（`SDG911pct`）作外部靶子，不参与任何估计/分解，也不用于
“医疗 60 分钟符号反转”主张（RAI 是“到道路的 2 km 近邻”，不是“到设施的出行时间”）。

## 来源

- 官方数据页（SEDAC）：
  <https://sedac.ciesin.columbia.edu/data/set/sdgi-9-1-1-rai-2023/data-download>
- Harvard Dataverse 镜像（本仓库实际下载源）：
  <https://doi.org/10.7910/DVN/FFQ1WT>
- 许可：**CC BY 4.0**（`http://creativecommons.org/licenses/by/4.0/`）
- 生产日期：2023-09-05；Dataverse 发布：2025-09-11；访问日期：2026-10-07
- 引用：
  Center for International Earth Science Information Network - CIESIN -
  Columbia University. 2023. *SDG Indicator 9.1.1: Rural Access Index (RAI),
  2023 Release*. Palisades, NY: NASA Socioeconomic Data and Applications Center
  (SEDAC). <https://doi.org/10.7910/DVN/FFQ1WT>.

## 文件与校验

| 文件 | 大小 | SHA256 |
|---|---:|---|
| `sdgi-9-1-1-rai-2023-csv.zip`（Dataverse 外层包） | 2,867,741 B | `524547C158E428561B2C6C2A9E67CE04FCA34A3F1737F8CC3ECFCD433E368268` |
| `sdgi-9-1-1-rai-2023-csv/sdgi-9-1-1-rai-2023-national.csv` | 24,385 B | `2BA4866484ED216F857BF5369015AB7224159EABB6A55EA7BCF57E8CF4C636C3` |
| `sdgi-9-1-1-rai-2023-csv/sdgi-9-1-1-rai-2023-subnational.csv` | 8,209,285 B | `B69D4E416E1DFEBD3BA93C8AE6F390614BFFCD601DB9563B761685B7FCAFAE26` |

> 注意：Dataverse 下载对 `sdgi-9-1-1-rai-2023-csv.zip` 做了 Guestbook
> 登记（`guestbookId=643`，字段 email/name/institution/position）。脚本用
> `POST /api/access/datafiles/{id}` 提交通用登记信息后取得签名 URL 下载，
> 得到的是一个“外层 zip 包内再嵌套一个同名 zip”的结构；解压两次后得到上表 CSV。

## 复现脚本

- 下载与解压：本目录无独立脚本（下载命令见 `WORK_LOG.md` 2026-10-07 方案 C 节；
  核心是 Dataverse Data Access API + Guestbook）。
- 分析：仓库根目录 `run_v34_e6_rai_external_target.py`。

## 说明（乡村掩膜口径）

RAI 的乡村人口使用 GHS-SMOD E2020（GLOBE R2023A，1 km）类别 **11–13**
（低密度乡村、低密度乡村、乡村聚落）。此处与旧探索脚本 `explorations/scripts/d08_sdg_rai_rural.py`
使用的 21–23 不同——21–23 在 GHS-SMOD 标准中为城郊/半密集/密集城市类别，
故 E6 采用标准 11–13（见 `run_v34_e6_rai_external_target.py` 头注）。
