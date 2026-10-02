# Technical explainer
## Cardiovascular Inequalities and Prevention Priorities in England

*Audience: analysts, statisticians, anyone checking or reproducing the work. Target: 2-3 pages.*

---

### 1. Purpose and questions
[Restate the four questions from the README in one paragraph.]

### 2. Data sources

| Measure | Fingertips ID | Period | Numerator | Denominator | Notes |
|---|---|---|---|---|---|
| Under-75 CVD mortality | | | Deaths under 75 from ICD-10 I00-I99 | Mid-year population under 75 | Directly age-standardised to the 2013 European Standard Population - **check definition** |
| Hypertension recorded | | | Patients on QOF hypertension register | GP list size (all ages) | Recorded, not true, prevalence |
| Hypertension estimated | | | Modelled | [check] | Modelled estimate with uncertainty |
| Smoking | | | | | Survey-based (APS) - sampling error |
| Excess weight | | | | | Survey-based |
| Deprivation | | | | | IMD score; single period used for all years |
| CVDPREVENT indicators | n/a | | | | NHS geographies; England by quintile used |

Download date and file details: `data/raw/manifest.json`.

### 3. Geography
Upper-tier local authorities (n = [N]) as of [boundary year]. Areas affected by boundary changes: [list and how handled]. Small areas combined or suppressed in source data: [e.g. City of London, Isles of Scilly].

### 4. Data preparation
[Summarise the filters in `clean.py` with row counts from `cleaning_log.json`: category breakdowns removed, sex/age selected, upper-tier codes kept, latest period selected.]

### 5. QA decisions
*[One line per WARN/FAIL from `qa_report.md`. This section is what a sign-off reviewer reads first.]*

| QA check | Issue | Decision and reason |
|---|---|---|
| Latest periods aligned | Indicators cover different years | Each chart footnote states its period; no adjustment |
| Hypertension measures comparable | Recorded = all ages, estimated = [ages] | [Explain effect on gap - it overstates/understates; treat gap as relative not absolute] |
| | | |

### 6. Methods

**Deprivation quintiles.** Local authorities ranked by IMD score and split into five equal-sized groups (by number of areas, not population). Quintile means are unweighted: they describe the typical area, not the typical person.

**Confidence intervals.** Quintile means: t-distribution 95% CI across areas. Area-level CIs: as published by Fingertips.

**Funnel plot.** Exact Poisson control limits (95% and 99.8%) around the England rate, plotted against each area's number of deaths. Limitation: treating an age-standardised rate as a simple Poisson rate ignores variance from standardisation. [Describe overdispersion seen, if any, and implication: many areas genuinely differ, not just by chance.]

**Slope Index of Inequality.** Population-weighted linear regression of each area's rate on its relative deprivation rank (cumulative population midpoint, 0 = least, 1 = most deprived). SII = modelled absolute gap across the full deprivation range; RII = SII / weighted mean. Trend SII uses the latest IMD for all years (deprivation ranks assumed stable).

**Correlation.** Spearman's rank correlation (robust to outliers and non-linearity).

**Regression.** OLS of under-75 CVD mortality on standardised predictors (deprivation, diagnosis gap, smoking, excess weight), with HC3 robust standard errors. VIFs reported. Ecological model - coefficients describe areas, not individuals.

**Priority areas.** Within each domain (risk, detection, outcome), indicators converted to percentile ranks and averaged. Areas in the worst [20]% of a domain are flagged; priority areas are flagged in at least [2] of 3 domains. Sensitivity: [result of changing threshold to 25%].

### 7. Limitations
- **Ecological fallacy:** area-level associations may not hold for individuals.
- **Causation:** no causal claims are made; confounding by deprivation is likely.
- **Modelled estimates:** estimated hypertension prevalence carries uncertainty not reflected in the gap calculation.
- **Different periods** across indicators.
- **Survey-based** risk factors have sampling error, larger in small areas.
- **Deprivation** measured at one point in time.
- [Anything else you found.]

### 8. Reproducibility
All code: [GitHub link]. Re-run with `python -m src.fetch_data && python -m src.run_pipeline`. Settings in `config.yaml`. Synthetic test: `python -m src.make_synthetic`.
