# data/raw 数据字典

按角色归类,命名统一为 `变量名_来源`。**注册数据**(下带 ⚠)不入库(.gitignore),按根目录 README 指引各自获取。

```
data/raw/
├── dependent/                                  因变量
│   └── collaborators_github.csv                双边跨境协作者数(GitHub Innovation Graph,季度 2020Q1–2026Q2)
├── remote_work/                                自变量:远程办公(G-SWA)
│   ├── wfh_w1w2_micro_gswa/ ⚠                 W1/W2 注册微观数据(官方复现文件,36,078 应答)
│   └── wfh_w3_summary_gswa.xlsx               W3 官方国家汇总(wfhresearch.com)
├── distance_moderators/                        调节变量
│   ├── culture_6dims_hofstede.csv              Hofstede 六维度(geerthofstede.com,0–100,112 行含区域)
│   └── governance_wgi.xlsx                     WGI 六项治理指标(worldbank,1996–2022 宽表)
├── controls/                                   控制变量
│   ├── developers_github.csv                   各国开发者数(GitHub,季度)
│   ├── pushes_github.csv                       各国 git push 数(GitHub,备用)
│   ├── gravity_cepii.zip ⚠(>100MB)           CEPII Gravity V202211 原始库(脚本 03 解压提取)
│   ├── macro_wdi_worldbank.csv                 GDP/人均 GDP/宽带/人口(世界银行 API)
│   └── country_codes_worldbank.csv             ISO2↔ISO3 代码映射(世界银行)
├── eu_robustness/                              EU 稳健性
│   └── telework_ewcs_ukds/ ⚠                  EWCS/EWCTS 2021 微观数据(UKDS SN 9026)
└── archive/                                    过渡期与参考(不进最终分析)
    ├── wfh_w1w2_nber_table.csv                 NBER 表 A.2 解析值——已被微观数据替代,保留交叉验证(相关 0.995+)
    ├── telework_eurostat_full.json             Eurostat 原始 dump(30MB,过渡期,可由脚本 03 重拉)
    ├── telework_eurostat_clean.csv             过渡期 Eurostat 清洗表(已被 EWCS 替代)
    ├── wfh_timeseries.xlsx                     SWAA 美国月度时序(未使用)
    ├── nber_w30446.pdf                         Aksoy et al. 2022(表 A.1/A.2 解析来源)
    ├── nber_w32374.pdf / gswa_persistence_wp.pdf / pnas_gswa_sapp.pdf / gswa_2023_report.pdf
    └── …                                       调研数据可得性时下载的佐证文献
```

⚠ = 注册获取或超大文件,已被 .gitignore 排除;克隆仓库后按根目录 `README.md` 的命令/注册指引补齐。

对应的清洗中间产物在 `data/processed/`:`culture_dims_hofstede_iso3.csv`(ISO3 化六维)、`governance_wgi_clean.csv`(WGI 长表)、`gravity_cepii_bilateral.csv`(CEPII 双边提取)、`wfh_w3_gswa.csv`(W3 解析表)——由脚本 03/02 生成,脚本统一从 processed 读取。

## 数据流(最终版)

```
remote_work/wfh_w1w2_micro_gswa/ ──10──> processed/gswa_micro_country_wave.csv ─┐
remote_work/wfh_w3_summary_gswa.xlsx ──12───────────────────────────────────────┤
dependent/collaborators_github.csv ─────────────────────────────────────────────┤
controls/developers_github.csv ─────────────────────────────────────────────────┼─12─> panel_A/B ─13─> 回归表
distance_moderators/culture_6dims_hofstede.csv ─03─> processed/…_iso3.csv ─(K-S)┤
distance_moderators/governance_wgi.xlsx ──03──> processed/governance_wgi_clean ┤
controls/gravity_cepii.zip ─03─> processed/gravity_cepii_bilateral.csv ─────────┤
controls/macro_wdi_worldbank.csv / country_codes_worldbank.csv ────────────────┘
eu_robustness/telework_ewcs_ukds/ ──11─> processed/ewcs_telework.csv ──14─> EU 稳健性
```
