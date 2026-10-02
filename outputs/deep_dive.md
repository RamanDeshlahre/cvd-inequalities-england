# Deep dive: further analyses

Run after `src.run_pipeline`. All results use upper-tier local authorities and IMD 2025 quintiles.

## 1. Men and women

- **Males, 2025:** least deprived fifth 78.0, most deprived 138.5 per 100,000 (ratio 1.78); SII 72.0 (95% CI 64.3 to 79.7). SII in 2001: 118.2.
- **Females, 2025:** least deprived fifth 34.7, most deprived 60.7 per 100,000 (ratio 1.75); SII 32.1 (95% CI 27.6 to 36.7). SII in 2001: 61.4.
- The male SII is 2.2 times the female SII. Relative inequality (RII) is 0.69 for men and 0.72 for women.

## 2. When did the gap stop closing?

- A data-driven search (2005-2015) finds the best break year in the pre-pandemic trend is **2011**.
- **2001-2011:** the SII fell by **3.7 per year** (95% CI 3.4 to 4.1), from 88.0 to 48.2 (45% lower).
- **2011-2019:** essentially flat, -0.07 per year (95% CI -0.63 to +0.49).
- **2019-2025:** +0.54 per year (95% CI -1.23 to +2.31). Average SII 53.5 after 2019, vs 49.1 in 2011-2019.
- **Reading:** the gap narrowed quickly in the 2000s, **stopped narrowing around 2011**, and has been slightly higher since the pandemic. Earlier outputs said the gap 'fell until 2019'; this analysis shows almost all of the fall happened by 2011. Outputs were updated to say so.
- The break year is estimated, but with few points per segment; treat it as 'around' that year.

## 3. Excess early deaths

- In 2025, about **10,073** early CVD deaths (28% of 35,820) would not have occurred if every area had the death rate of the least deprived fifth (55.1 per 100,000).
- Average over 2023-2025: **9,927 a year**.
- Approximate: age-standardised rates applied to each area's under-75 population; a scale estimate, not a precise count. Round it in public outputs.

## 4. How much of the deprivation gap do smoking and weight account for?

- Deprivation alone: **15.8** more deaths per 100,000 per 1 SD of deprivation.
- After adding smoking and excess weight: **14.4** (R-squared 0.71, n = 148).
- The deprivation coefficient falls by **9%**. At area level, smoking and weight account for only part of the gap; most of the association with deprivation remains.
- Caution: area averages, survey-based risk factors, and no data on blood pressure, diet, access to care or ethnicity. This is a description, not a causal decomposition.

## 5. Sensitivity: 3-year pooled rates

- 2023 - 25 pooled: Q5/Q1 ratio **1.76**, SII **51.9** (95% CI 46.8 to 57.0).
- Single year 2025: ratio 1.79, SII 51.8.
- **Conclusion:** pooling three years gives the same picture; the main findings do not depend on single-year noise.
