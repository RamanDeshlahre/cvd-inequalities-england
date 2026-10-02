# Statistics sign-off record

**Outputs covered:** Hidden Risk report, technical explainer, press summary, figures 01–08
**Checklist:** `docs/06_stats_signoff_checklist.md` | **Date:** October 2026 | **Version:** 1.0

| Area | Status | Evidence / comment |
|---|---|---|
| **A. Source and provenance** | ✅ | Every figure footnoted with source and period; indicator IDs in `config.yaml`; download record in `data/raw/manifest.json` |
| Latest data used | ✅ | Mortality 2025, IMD 2025, CVDPREVENT to March 2026. The undiagnosed estimate (2021) is the latest published; its age is stated |
| **B. Accuracy** | ✅ | All report numbers traced to `outputs/results_summary.md` and `outputs/tables/` |
| Spot-checks against source | ⚠️ Partly | 5 undiagnosed values and 1 CVDPREVENT value checked. **To do:** 3 mortality values |
| Second-person check | ⬜ To do | Ask a colleague or peer to check 10 numbers in the report against the tables |
| Units and rounding | ✅ | per 100,000, %, percentage points; rounded to whole numbers in the public report |
| **C. Statistical validity** | ✅ | CIs shown on all quintile charts; funnel limits adjusted for overdispersion |
| No over-claiming of change | ✅ | Segmented trend: flat 2011–2019, post-2019 trend interval includes zero, so the gap is described as "stopped closing around 2011" and "slightly wider since the pandemic", not "widening" |
| Claims corrected after deeper analysis | ✅ | The earlier wording "narrowed until 2019" was replaced in all outputs once the break-year analysis showed the fall ended around 2011 |
| Approximate figures | ✅ | Excess deaths (~10,000/yr) are rounded and labelled approximate |
| Code tested | ✅ | Unit tests of each statistical method against known answers; end-to-end synthetic test (`pytest`) |
| Age-standardisation | ✅ | Mortality is age-standardised. The undiagnosed estimate is not, and its age effect is explicitly discussed |
| Small numbers / suppression | ✅ | City of London and Isles of Scilly excluded from mortality; stated |
| **D. Interpretation** | ✅ | Language says "linked to", not "caused by"; ecological fallacy stated |
| Named areas | ✅ | Only the 4 areas outside overdispersion-adjusted limits are named as outliers. Priority areas are named with their rule stated |
| Surprising results | ✅ | Statin reverse gradient and conflicting undiagnosed measures are presented with possible explanations, not conclusions |
| **E. Communication** | ✅ | Chart titles state findings; natural frequencies in the public report; media lines tested against hard questions |
| Accessibility | ✅ | Colour-blind-safe palette; values labelled on bars; scatter uses different marker shapes as well as colours |
| **F. Reproducibility and governance** | ✅ | Pipeline runs end to end from raw files; settings in config; synthetic test included |
| Disclosure | ✅ | Aggregate published statistics only; no personal data |

**Outstanding before publication:** mortality spot-checks; second-person number check.

**Signed off by:** ____________
