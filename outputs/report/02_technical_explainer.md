# Technical explainer
## Cardiovascular Inequalities and Prevention Priorities in England: how risk, care and early deaths differ by deprivation

*Raman D. | October 2026 | Audience: analysts and statisticians reviewing or reproducing this work*

---

### 1. Purpose

To describe how cardiovascular risk factors, detection and treatment of risk, and early deaths vary with deprivation across England, and to identify areas where prevention may have the greatest impact. All analysis is reproducible from the code in this repository.

### 2. Data sources

| Measure | Source / ID | Period | Geography | Notes |
|---|---|---|---|---|
| Under-75 CVD mortality | Fingertips 40401 | 2001–2025 (single years) | Upper-tier LA | Directly age-standardised rate per 100,000 |
| Undiagnosed adult hypertension | Fingertips 94111 | 2021 | Upper-tier LA | Modelled estimate, adults 16+ |
| Recorded hypertension (QOF) | Fingertips 219 | 2024/25 | Upper-tier LA | Crude, all-age GP list; used as a diagnostic only |
| Smoking prevalence | Fingertips 92443 | 2024 | Upper-tier LA | Annual Population Survey, adults 18+ |
| Overweight or obese | Fingertips 93088 | 2024/25 | Upper-tier LA | Active Lives survey, adults 18+ |
| Deprivation score | Fingertips 94240 (IMD 2025) | 2025 | Upper-tier LA | IMD 2019 (93553) used for sensitivity |
| Treatment and detection | CVDPREVENT: CVDP007HYP, CVDP003CHOL, CVDP002AF, CVDP005HYP | To March 2026 | England, by patient deprivation quintile | Numerators and denominators retained |

Geography: 153 upper-tier local authorities (Counties & UAs, April 2023 boundaries; Fingertips area type 502). Download details are recorded in `data/raw/manifest.json`.

### 3. Data preparation

The Fingertips download contained 52,006 rows. `src/clean.py` applies these steps in order, with row counts logged in `data/processed/cleaning_log.json`:

1. Remove breakdown rows (by ethnicity, socioeconomic group, deprivation decile, etc.). Only whole-area values are kept.
2. Keep one sex (Persons) and the configured age group for each indicator (e.g. 18+ for smoking, rather than age bands).
3. Keep **single-year** periods only. Fingertips publishes both single-year and 3-year pooled mortality rates, and both share the same sortable period code, so mixing them would double-count.
4. Keep upper-tier LA codes (E06, E08, E09, E10) and separate out England as the benchmark. England appears twice in the file and is de-duplicated.

CVDPREVENT Data Explorer exports were read by `src/load_cvdprevent.py`, keeping England, Persons and the deprivation-quintile rows. CVDPREVENT numbers quintiles with 1 = most deprived; these were reversed so every output reads 1 = least deprived.

### 4. QA decisions

Automated checks are in `outputs/qa_report.md`. Result: **0 FAIL, 4 WARN**. Each warning and its decision:

| Check | Issue | Decision |
|---|---|---|
| Smoking coverage | No 2024 value for Cumberland, Westmorland and Furness, North Yorkshire (councils created April 2023) | Excluded from smoking analyses; listed here |
| Missing values | City of London and Isles of Scilly have no mortality value (small numbers; Scilly published with Cornwall). Scilly has a QOF data-quality flag | Excluded from mortality analyses (n = 151). Negligible effect on national results |
| Period alignment | Latest periods range from 2021 to 2025/26 | Every chart states its period. The undiagnosed estimate (2021) is the oldest and is interpreted with caution |
| Single-period indicators | Undiagnosed hypertension and IMD have one period | Used cross-sectionally only. Trends use the latest IMD for all years (deprivation ranks assumed stable) |

Manual checks: undiagnosed hypertension values for Barking and Dagenham, Dorset, Isle of Wight, Torbay and Devon match the Fingertips website. The CVDPREVENT England value for CVDP007HYP (74.01%) matches the Data Explorer. [Add: three under-75 mortality values checked against the website.] The total of area-level undiagnosed counts (3,982,918) matches the England figure (3,982,916), allowing for rounding.

### 5. Methods

**Deprivation quintiles.** Local authorities are ranked by IMD 2025 score and split into five groups of 30 to 31 areas. Quintile means are unweighted: they describe the typical *area* in each quintile, not the typical person.

**Confidence intervals.** For quintile means, t-based 95% intervals are calculated across areas. Area-level intervals are as published by Fingertips. CVDPREVENT intervals are as published.

**Slope Index of Inequality (SII) and Relative Index (RII).** Each area's rate is regressed on its relative position in the deprivation distribution: the cumulative population midpoint, from 0 = least deprived to 1 = most deprived. The regression is weighted by population under 75. SII is the modelled absolute gap across the whole distribution; RII = SII / population-weighted mean. Calculated for every year from 2001 to 2025.

**Funnel plot and overdispersion.** Each area's rate is plotted against its expected deaths at the England rate, with exact Poisson control limits. Of 151 areas, 65 fell outside the 99.8% Poisson limits, far more than the 0.2% expected by chance. This is overdispersion: genuine between-area variation that chance alone doesn't explain (dispersion factor φ = 10.9). Following Spiegelhalter (2005), an additive random-effects term was estimated from winsorised (10%) z-scores (τ = 14.3 per 100,000). Limits were widened accordingly, so that only areas unusual *even allowing for real variation between areas* are flagged. Limitation: treating an age-standardised rate as Poisson ignores the extra variance from standardisation.

**Correlation.** Spearman rank correlation is used, as it is robust to outliers and non-linearity.

**Regression.** Ordinary least squares regression of under-75 CVD mortality on standardised predictors (deprivation, undiagnosed hypertension, smoking, excess weight), with HC3 robust standard errors. Variance inflation factors were all below 2.4, so collinearity is acceptable. This is an ecological model: coefficients describe areas, not individuals.

**People affected (CVDPREVENT).** (least-deprived rate − most-deprived rate) × most-deprived denominator. This is the number of additional people who would meet the measure if the most deprived quintile matched the least deprived.

**Prevention priority areas.** For risk (smoking and excess weight, averaged as percentile ranks) and outcome (under-75 CVD mortality), areas in the worst 20% are flagged. Priority areas are flagged on **both**.

### 6. Key results

| Result | Value |
|---|---|
| Under-75 CVD mortality, most vs least deprived quintile (2025) | 98.7 vs 55.1 per 100,000 (ratio 1.79) |
| SII 2025 | 51.8 per 100,000 (95% CI 46.2 to 57.5); RII 0.71 |
| SII 2001 → 2019 → 2025 | 88.0 → 46.1 → 51.8 |
| Areas above overdispersion-adjusted 99.8% limits | Kingston upon Hull, Blackpool, Salford, Manchester |
| Smoking, Q1 vs Q5 | 7.9% vs 13.7% (Spearman with IMD ρ = 0.66) |
| Excess weight, Q1 vs Q5 | 60.6% vs 67.9% (ρ = 0.44) |
| BP treated to target, least vs most deprived | 75.9% vs 71.9%; about 71,000 people |
| Statins, QRISK ≥ 20%, least vs most deprived | 61.8% vs 70.1% (reverse gradient) |
| AF on anticoagulants | 92.3% vs 91.8% |
| Unconfirmed high BP reading, least vs most deprived | 1.84% vs 2.15% |
| Regression R² (n = 148) | 0.73; deprivation +12.5 per SD (95% CI 10.0 to 15.1); excess weight +5.6 (3.2 to 8.0); smoking +0.1 (−2.5 to 2.7) |
| Priority areas | 11, of which 9 are in the most deprived quintile |

**Interpreting the trend.** The SII almost halved between 2001 and 2019, then rose in 2020. The 2019 and 2025 confidence intervals overlap (41.6–50.6 vs 46.2–57.5), so the report says the gap has *stopped narrowing*, not that it has significantly widened.

**Interpreting the regression.** Smoking has no independent association with mortality once deprivation is included. This does **not** mean smoking is unimportant. Smoking and deprivation overlap strongly at area level, and the model cannot separate them. The negative coefficient for modelled undiagnosed hypertension most likely reflects age structure (see below), not a protective effect.

### 7. Two findings that needed extra scrutiny

**The modelled undiagnosed estimate.** It is lower in more deprived areas (ρ = −0.30) but correlates at ρ = 0.92 with crude recorded prevalence, which is largely driven by age. It is lowest in young inner-city boroughs (e.g. Tower Hamlets) and highest in older coastal and rural areas (e.g. Dorset). This indicates the estimate mainly reflects demography. GP-record data (CVDPREVENT CVDP005HYP) point the other way: unconfirmed high readings are most common in the most deprived quintile. **Decision:** the modelled estimate is reported descriptively, but not used to define priority areas.

**Statins and QRISK.** Statin coverage among people with QRISK ≥ 20% is higher in the most deprived quintile. Possible explanations, not tested here:
- QRISK includes a deprivation term, so the group above the threshold differs by deprivation.
- Targeted prevention programmes may be reaching deprived areas.
- Rates of declining statins may differ.

The report presents this as a finding to investigate, not an explanation.

### 8. Sensitivity checks (`outputs/sensitivity.md`)

- **IMD 2025 vs IMD 2019.** Scores correlate at ρ = 0.978; 26 areas change quintile, each by one step only. The mortality ratio is 1.79 vs 1.82. Conclusions are unchanged.
- **Priority threshold, 20% vs 25%.** All 11 areas remain flagged at 25%, with 5 more added. The core list is stable.
- **Funnel limits.** With Poisson limits, 35 areas are above; with overdispersion-adjusted limits, 4 are. The report uses the adjusted limits to avoid over-identifying outliers.

### 9. Limitations

- **Ecological fallacy:** area-level associations may not hold for individuals.
- **No causal inference:** associations may be confounded, most obviously by age and deprivation.
- **Mixed periods:** the undiagnosed estimate (2021) predates the other measures.
- **Modelled and survey estimates:** undiagnosed prevalence is modelled; smoking and weight come from surveys with sampling error.
- **Geography mismatch:** CVDPREVENT is analysed at national level by quintile, not by local authority.
- **Unweighted quintile means:** these describe typical areas; large and small authorities count equally.
- **Funnel approximation:** the Poisson approximation for age-standardised rates is simplified.

### 10. Reproducibility

```bash
pip install -r requirements.txt
python -m src.split_download data/raw/<fingertips_download>.csv
python -m src.load_cvdprevent
python -m src.run_pipeline
python -m src.sensitivity
```

All settings are in `config.yaml`. Synthetic test: `python -m src.make_synthetic`, then `python -m src.run_pipeline --raw-dir data/raw_synthetic --out-dir outputs_synthetic`.

### References

Spiegelhalter DJ (2005). Funnel plots for comparing institutional performance. *Statistics in Medicine* 24(8):1185–1202.

*Contains public sector information licensed under the Open Government Licence v3.0.*
