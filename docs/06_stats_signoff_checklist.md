# Statistics sign-off checklist

The Health Analytics Lead manages BHF's statistics sign-off process. This is the
checklist you apply to your own work - and can talk through at interview as
"how I'd run sign-off".

Complete one copy per output (report, explainer, dashboard, press summary).
Every item: **Yes / No / N/A + comment**.

## A. Source and provenance
- [ ] Every number traces to a named source, indicator ID and period.
- [ ] Download date recorded (manifest).
- [ ] The most recent available data is used, or the reason for older data is stated.

## B. Accuracy
- [ ] Every number in the text matches the underlying table (checked by a second person if possible).
- [ ] Three areas spot-checked against the original source website.
- [ ] Rounding consistent and sensible; totals add up.
- [ ] Units stated everywhere (per 100,000; %; percentage points).

## C. Statistical validity
- [ ] Uncertainty shown where it matters (CIs, funnel limits).
- [ ] No claim of a difference or change where intervals overlap substantially.
- [ ] Rates are age-standardised where comparing areas with different age structures.
- [ ] Small numbers / suppressed values handled and explained.
- [ ] Comparable denominators, or the difference explained.

## D. Interpretation
- [ ] No causal language for associations ("linked to", not "causes").
- [ ] Ecological fallacy considered - no statements about individuals from area data.
- [ ] Ranked or named areas are only those clearly outside control limits.
- [ ] Limitations stated in proportion - neither buried nor overstated.

## E. Communication
- [ ] Headline is supported by the evidence and not exaggerated.
- [ ] Charts: titles state findings, axes labelled, source and period footnoted.
- [ ] Accessible: not reliant on colour alone; readable by a non-specialist.
- [ ] Media lines tested against the hard questions.

## F. Reproducibility and governance
- [ ] Code runs end to end from raw data on a clean environment.
- [ ] Settings in config, not hard-coded.
- [ ] No personal or disclosive data in any output.
- [ ] README lets a new analyst re-run the work without asking anyone.

**Signed off by:** ____________  **Date:** ________  **Version:** ______
