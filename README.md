# Cardiovascular Inequalities and Prevention Priorities in England
### How risk, care and early deaths differ by deprivation

A reproducible analysis of how cardiovascular risk, detection, treatment and early deaths vary with deprivation across England's 153 upper-tier local authorities, and where prevention could make the biggest difference.

📄 **[Read the report: *Hidden Risk*](outputs/report/01_hidden_risk_report.md)** · 🔬 [Technical explainer](outputs/report/02_technical_explainer.md) · 🎙️ [Press summary and radio script](outputs/report/03_press_summary_and_radio.md) · ✅ [Statistics sign-off](outputs/report/04_statistics_signoff.md) · 📊 [Interactive Tableau dashboard]([add your Tableau Public link])

![Trend in the gap](outputs/figures/03_mortality_trend_gap.png)

## Key findings

- **Early deaths are 1.8 times higher in the most deprived areas.** Under-75 CVD mortality in 2025 was 98.7 per 100,000 in the most deprived fifth of local authorities, vs 55.1 in the least deprived (slope index of inequality 51.8, 95% CI 46.2–57.5).
- **The gap almost halved from 2001 to 2019, then stopped narrowing.** The SII fell from 88.0 to 46.1, then rose to 54.4 in 2020 and stood at 51.8 in 2025.
- **Four areas stand out after allowing for overdispersion:** Kingston upon Hull, Blackpool, Salford and Manchester.
- **Blood pressure control is lower in deprived groups.** 71.9% of patients are treated to target in the most deprived quintile vs 75.9% in the least deprived, about **71,000 people**.
- **Not every gap goes the same way.** Statin use among high-risk patients (QRISK ≥ 20%) is *higher* in the most deprived quintile (70.1% vs 61.8%).
- **Two undiagnosed-hypertension measures disagree.** The modelled estimate tracks age structure (ρ = 0.92 with crude prevalence), while GP records show unconfirmed high readings are most common in the most deprived quintile.
- **11 prevention priority areas** rank in the worst fifth for both risk factors and early deaths; 9 of them are in the most deprived quintile.

## What's in this repository

| Output | Audience | File |
|---|---|---|
| *Hidden Risk* public report | Public, media, policy | `outputs/report/01_hidden_risk_report.md` |
| Technical explainer | Analysts, statisticians | `outputs/report/02_technical_explainer.md` |
| Press summary, radio script, media Q&A | Media | `outputs/report/03_press_summary_and_radio.md` |
| Statistics sign-off record | Reviewers | `outputs/report/04_statistics_signoff.md` |
| QA report | Reviewers | `outputs/qa_report.md` |
| Sensitivity checks | Reviewers | `outputs/sensitivity.md` |
| Figures (8) and tables | All | `outputs/figures/`, `outputs/tables/` |
| Tableau-ready data and build guide | Dashboard | `outputs/tableau/`, `docs/08_tableau_build_guide.md` |
| Power BI-ready data | Dashboard | `outputs/tables/powerbi_*.csv` |

## Data sources

| Source | Measures |
|---|---|
| OHID Fingertips | Under-75 CVD mortality (40401), undiagnosed hypertension (94111), recorded hypertension (219), smoking (92443), excess weight (93088), IMD 2025 (94240) and IMD 2019 (93553) |
| CVDPREVENT (NHS England) | CVDP007HYP, CVDP005HYP, CVDP003CHOL, CVDP002AF, by deprivation quintile, to March 2026 |

All data are published aggregate statistics. No personal data is used.

## Methods

Deprivation quintiles · quintile means with 95% CIs · population-weighted Slope and Relative Index of Inequality (2001–2025) · funnel plot with Spiegelhalter overdispersion adjustment · Spearman correlation · OLS regression with HC3 robust SEs and VIFs · transparent priority-area rule · sensitivity checks (IMD version, priority threshold) · automated QA. Full details: [technical explainer](outputs/report/02_technical_explainer.md).

## How to reproduce

```bash
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt

python -m src.run_pipeline      # clean -> QA -> analysis -> figures -> tables
python -m src.sensitivity       # sensitivity checks
python -m src.export_tableau    # Tableau-ready tables
```

Raw data are included in `data/raw/`. To refresh from source:
`python -m src.fetch_data` (Fingertips API), save new CVDPREVENT exports into `data/raw/cvdprevent/`, then run `python -m src.load_cvdprevent`.

To test the pipeline without real data: `python -m src.make_synthetic`, then `python -m src.run_pipeline --raw-dir data/raw_synthetic --out-dir outputs_synthetic`.

## Project structure

```
config.yaml              all settings: indicators, geography, thresholds, chart titles
src/fetch_data.py        download from the Fingertips API, with provenance manifest
src/split_download.py    split a combined Fingertips download into per-indicator files
src/load_cvdprevent.py   convert CVDPREVENT exports into one tidy file
src/clean.py             filtering, joining, deprivation quintiles
src/qa.py                automated quality checks -> outputs/qa_report.md
src/stats.py             statistical methods
src/figures.py           accessible, consistent charts
src/run_pipeline.py      runs everything
src/sensitivity.py       sensitivity and diagnostic checks
src/export_tableau.py    Tableau-ready tables -> outputs/tableau/
src/make_synthetic.py    synthetic test data with known effects
docs/                    project plan, templates, sign-off checklist, dashboard guide
```

## Limitations

This is an ecological analysis: it describes areas and groups, not individuals, and shows associations, not causes. Indicators cover different periods (2021 to 2026). See the technical explainer for the full list.

## Author

Raman D. · [LinkedIn](https://www.linkedin.com/in/raman-deshlahre/) · Analysis, code and reports by the author; AI tools were used to help scaffold code and draft text, and all results were checked by the author.

*Contains public sector information licensed under the Open Government Licence v3.0.*
