# QA report

Every WARN needs a written decision in the technical explainer before outputs are signed off.

| Status | Check | Detail |
|---|---|---|
| PASS | All indicators configured | All indicator IDs set. |
| PASS | Coverage: under75_cvd_mortality | 153 areas in latest period; missing: [] |
| PASS | Coverage: hypertension_undiagnosed | 153 areas in latest period; missing: [] |
| PASS | Coverage: hypertension_recorded | 153 areas in latest period; missing: [] |
| WARN | Coverage: smoking | 150 areas in latest period; missing: ['E06000063', 'E06000064', 'E06000065'] |
| PASS | Coverage: excess_weight | 153 areas in latest period; missing: [] |
| PASS | Coverage: deprivation | 153 areas in latest period; missing: [] |
| PASS | No duplicate area-period rows | None found. |
| PASS | Plausible range: under75_cvd_mortality | min 29.57, max 238.17, out of range: 0 |
| PASS | Plausible range: hypertension_undiagnosed | min 6.75, max 9.65, out of range: 0 |
| PASS | Plausible range: hypertension_recorded | min 6.86, max 20.98, out of range: 0 |
| PASS | Plausible range: smoking | min 4.10, max 30.53, out of range: 0 |
| PASS | Plausible range: excess_weight | min 38.48, max 77.67, out of range: 0 |
| PASS | Plausible range: deprivation | min 6.10, max 43.47, out of range: 0 |
| PASS | CIs contain point estimate | 0 rows where value lies outside its CI |
| WARN | Suppressed / missing values (latest period) | 5 rows. Notes: {'hypertension_recorded': 'There is a data quality issue with this value', 'smoking': 'Value missing in source data', 'under75_cvd_mortality': 'Value for Cornwall and Isles of Scilly combined'} |
| WARN | Latest periods aligned | {'deprivation': 2025, 'excess_weight': '2024/25', 'hypertension_recorded': '2024/25', 'hypertension_undiagnosed': 2021, 'smoking': '2024', 'under75_cvd_mortality': '2025'} - state these in every chart footnote |
| PASS | One age group per indicator | {'under75_cvd_mortality': ['<75 yrs'], 'hypertension_undiagnosed': ['16+ yrs'], 'hypertension_recorded': ['All ages'], 'smoking': ['18+ yrs'], 'excess_weight': ['18+ yrs'], 'deprivation': ['All ages']} |
| WARN | Periods available per indicator | {'deprivation': 1, 'excess_weight': 10, 'hypertension_recorded': 13, 'hypertension_undiagnosed': 1, 'smoking': 14, 'under75_cvd_mortality': 25}. Single period only: ['deprivation', 'hypertension_undiagnosed'] - cross-sectional use only |
| PASS | Every area has a deprivation score | All matched. |
| PASS | Deprivation quintile sizes | {1: 31, 2: 30, 3: 31, 4: 30, 5: 31} |