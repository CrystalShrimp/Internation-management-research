# data/raw 数据字典

四个子目录/类别 + 状态标记。**"最终用"** = 进入最终论文(v2)的分析;**"过渡期"** = 曾用于被替代的中间设计,保留作审计;**"参考"** = 佐证文献,不进回归。

## 1. 课程指定数据(最终用)

| 文件 | 大小 | 说明 | 消费脚本 |
|---|---|---|---|
| `economy_collaborators.csv` | 1.5MB | **GitHub Innovation Graph** 双边跨境协作者数(因变量),`weight,source,destination,year,quarter`,ISO2,2020Q1–2026Q2 | 04, 07, 08, 12, 14 |
| `developers.csv` | 94KB | GitHub 各国活跃开发者数(规模控制变量),季度 | 04, 07, 12 |
| `hofstede_6d.csv` | 4KB | **Hofstede 官网**六维度原始表(112 行含洲际区域,分号分隔) | 03 |
| `gswa_2023.xlsx` | 26KB | **G-SWA W3(2023)** 官方国家汇总(wfhresearch.com) | 02, 12, 13, 15 |
| `gswa_micro/` | 16MB | **G-SWA W1/W2 微观数据**(注册获取,官方复现文件含 G-SWA.dta + do 文件)。**不入库**(.gitignore) | 10 |
| `ewcs/UKDA-9026-stata/` | 49MB | **EWCS/EWCTS 2021 微观数据**(UKDS SN 9026,注册获取)。**不入库** | 11 |

## 2. 控制变量数据(最终用)

| 文件 | 大小 | 说明 | 消费脚本 |
|---|---|---|---|
| `cepii_bilateral.csv` | 3.5MB | CEPII Gravity V202211 提取的双边变量(距离、时差、共同语言、接壤、社会连接度);由 `gravity_cepii.zip`(198MB,**不入库**)提取 | 04, 07, 08, 12, 14 |
| `worldbank_wgi_wdi.csv` | 175KB | 世界银行 API 拉取:GDP、人均 GDP、宽带、人口(2015–2024) | 04, 07, 12 |
| `wgi_dataset.xlsx` | 2.1MB | WGI 官方完整数据(1996–2022,六指标) | 03 |
| `wb_countries.csv` | 14KB | ISO2↔ISO3 国家代码映射(WB API) | 04, 07, 08, 12, 14 |

## 3. 清洗中间产物(由 03/02 脚本生成,放在 raw 仅为脚本路径统一)

| 文件 | 说明 |
|---|---|
| `hofstede_clean.csv` | Hofstede 原始表 → ISO3 化、剔区域(88 国 × 6 维) |
| `wgi_clean.csv` | WGI 宽表 → 国家 × 六指标(2022 估计值) |
| `eurostat_wfh_clean.csv` | Eurostat WFH 年度率(过渡期 EU 替代,现仅审计用) |
| `gswa_w3.csv` | `gswa_2023.xlsx` 解析出的 W3 国家表(iso3 × 三指标) |

## 4. 过渡期 / 参考文件(不进最终分析)

| 文件 | 说明 |
|---|---|
| `gswa_w1w2.csv` | NBER w30446 表 A.2 解析的 W1+W2 合并值——**已被微观数据替代**(`gswa_micro_country_wave.csv`),保留用于交叉验证(相关系数 0.995+) |
| `eurostat_ehomp.json` | Eurostat 原始全量 dump(30MB)——过渡期 EU 数据,已被 EWCS 替代;可删(能由脚本 03 重新拉取) |
| `wfh_timeseries.xlsx` | SWAA 美国月度时序——调研数据源时下载,本项目未使用;可删 |
| `git_pushes.csv` | GitHub 各国 push 数——调研时下载,最终未用(非双边);保留备用 |
| `nber_w30446.pdf` | Aksoy et al. 2022 工作论文——表 A.1/A.2 的解析来源(脚本 02 读它)+ 参考文献佐证 |
| `nber_w32374.pdf`, `gswa_persistence_wp.pdf`, `pnas_gswa_sapp.pdf`, `gswa_2023_report.pdf` | 调研数据可得性时下载的论文/报告,佐证"W3 无微观、G-SWA 覆盖范围"等论述 |

## 数据流(最终版)

```
gswa_micro/ ──10──> processed/gswa_micro_country_wave.csv ─┐
gswa_2023.xlsx ──12────────────────────────────────────────┤
economy_collaborators.csv ─────────────────────────────────┼──12──> panel_A/B_3|2wave.csv ──13──> 回归表
developers.csv ────────────────────────────────────────────┤
hofstede_6d.csv ──03──> hofstede_clean.csv ──(K-S)────────┤
wgi_dataset.xlsx ──03──> wgi_clean.csv ────────────────────┤
cepii_bilateral.csv / worldbank_wgi_wdi.csv ───────────────┘
ewcs/ ──11──> processed/ewcs_telework.csv ──14──> EU 稳健性(tab_ewcs_eu.csv)
```
