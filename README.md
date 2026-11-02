# Remote Work and Cross-Border Open-Source Innovation

Quantitative course research project (Group 1): *Does remote work shift open-source
collaboration from domestic to cross-border, and does institutional distance
moderate this?*

**Design**: country-pair panel regression with a Remote × Distance interaction.
**Data (course-designated, all registered/public)**: G-SWA (microdata W1/W2 +
official W3 summary), GitHub Innovation Graph (bilateral collaborators),
Hofstede (cultural distance), EWCS/EWCTS 2021 (EU robustness), plus CEPII
Gravity, World Bank WDI/WGI as controls.

## Final outputs

| Output | Location |
|---|---|
| Final paper | `paper/paper.docx` / `paper/paper.md` |
| Figures | `paper/figures/` |
| Main tables (v2) | `output/tables/tab_v2_*.csv`, `output/tables/tab_ewcs_eu.csv` |
| Interim tables (superseded, kept for audit) | `output/tables/tab2..tab8*.csv` |
| Estimation panels | `data/processed/panel_A_3wave.csv`, `panel_B_2wave.csv`, `ewcs_pairs.csv`, `longdiff_v2_*.csv` |

## Headline results

1. **H1 (cross-border shift)** — supported in Europe with the independent EWCS
   measure: +10pp destination telework ⇒ +5.6 log points bilateral
   collaboration (p<0.001), +1.5 points of 2021→23 growth; origin effects half
   as large. Globally, within-pair average effects ≈0 (remote work operates
   through developer-base growth, a mediator).
2. **H2 (distance moderation)** — supported with the Hofstede Kogut-Singh
   index: Panel A TWFE −0.671**; 2022→2023 long difference −0.842* (p=0.045),
   robust to dropping China (−0.434, p=0.055) and the US (−1.191*),
   winsorising (−0.530**); EWCS EU levels −0.003*. Marginal effect of +1
   planned WFH day: +0.91 log points at z(cult. dist)=−1 vs −0.78 at z=+1.
   Null placebo for 2021→2022; flat event-study pre-trends.

## Pipeline

Registered data (user-obtained, not redistributable in this repo):
- `data/raw/gswa_micro/` — WFH Research replication file (G-SWA.dta)
- `data/raw/ewcs/` — UKDS SN 9026 (EWCTS 2021 Stata)

```
# public data
python scripts/01_download_wb.py          # WDI + country codes (World Bank API)
python scripts/03_parse_wgi_hofstede.py   # WGI, Hofstede, Eurostat, CEPII
# registered microdata
python scripts/10_parse_gswa_micro.py     # -> gswa_micro_country_wave.csv
python scripts/11_parse_ewcs.py           # -> ewcs_telework.csv
# panels & estimation
python scripts/12_build_panel_v2.py       # Panels A (3-wave) and B (2-wave)
python scripts/13_regressions_v2.py       # TWFE/PPML/event study/long diffs
python scripts/14_ewcs_eu.py              # EU robustness with EWCS
python scripts/15_figures_v2.py           # paper figures
python scripts/md2docx.py                 # paper.md -> paper.docx
```

(02, 04–09 document the superseded interim design based on published
two-point summaries; kept for audit trail.)

## Notes

- Kogut-Singh standardization uses the full-country reference sample.
- Wave→quarter mapping by fielding dates: W1→2021Q3+, W2→2022Q1+, W3→2023Q2+.
- GitHub bilateral counts are privacy-censored; zero-filled + PPML.
- Interim deviations (published summaries for G-SWA; Eurostat for EWCS) were
  replaced once registered microdata arrived — see paper Appendix A.
