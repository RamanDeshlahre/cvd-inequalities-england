# Project plan - step by step

Work through these in order. Each step ends with a **"be able to explain"** check:
if you can't explain it out loud in two minutes, you're not ready to move on.
That's what makes this project yours at interview.

---

## WEEK 1 - Data

### Step 0: Set up (half a day)
- [ ] Create a GitHub repo `cvd-inequalities-england` and copy this project in.
- [ ] Create a virtual environment and `pip install -r requirements.txt`.
- [ ] Run the synthetic test (see README). Open every figure in `outputs_synthetic/figures/`.
- [ ] Read `outputs_synthetic/qa_report.md`. Notice the 4 WARNs - these were planted deliberately.

**Be able to explain:** why test a pipeline on synthetic data with known effects before using real data.

### Step 1: Confirm indicators (half a day)
- [ ] On the Fingertips website, open the *Cardiovascular disease* and *CVD prevention* profiles.
- [ ] For each indicator in `config.yaml`, find it, read its definition ("Definitions" tab) and confirm the ID.
- [ ] Find the **estimated hypertension prevalence** indicator and add its ID (currently `null`).
- [ ] Run `python -m src.fetch_data --list-area-types` and confirm the upper-tier LA area type ID.
- [ ] Run `python -m src.fetch_data --check-ids` and confirm the printed names match.
- [ ] Write one line per indicator in a notes file: what it measures, numerator, denominator, period.

**Be able to explain:** the difference between recorded (QOF) and estimated prevalence, and why they have different denominators.

### Step 2: Download data (1 hour)
- [ ] Run `python -m src.fetch_data`. Check `data/raw/manifest.json`.
- [ ] If the API fails, download manually from the Fingertips "Download" tab and save as `data/raw/<key>.csv`.
- [ ] CVDPREVENT: on the CVDPREVENT data explorer, choose England and the breakdown by deprivation quintile for:
      hypertension treated to target, lipid-lowering therapy for high QRISK, and AF anticoagulation.
      Save as `data/raw/cvdprevent_by_deprivation.csv` with columns:
      `indicator, period, quintile, value, lower_ci, upper_ci`.
- [ ] Check which way CVDPREVENT numbers its quintiles and set `quintile_1_is_most_deprived` in `config.yaml`.

**Be able to explain:** why raw files are never edited by hand, and what the manifest is for.

### Step 3: Clean and QA (1-2 days)
- [ ] Run `python -m src.run_pipeline`.
- [ ] Open `data/processed/cleaning_log.json` - check row counts at each filter make sense.
- [ ] Read `outputs/qa_report.md`. For **every** WARN or FAIL, write your decision in the technical explainer.
- [ ] Spot-check 3 areas by hand: compare values in `area_latest.csv` with the Fingertips website.
- [ ] Read through `clean.py` line by line. Add your own comments where anything was unclear.

**Be able to explain:** what the category-breakdown filter does, how quintiles are formed, and why areas count equally in quintile means.

---

## WEEK 2 - Analysis

### Step 4: Outcomes (1-2 days)
- [ ] Review figures 01-03 and `outcome_*` tables.
- [ ] Is the funnel plot showing lots of areas outside the limits? That's **overdispersion** -
      real differences between areas beyond chance. Read about it (Spiegelhalter 2005, funnel plots) and write a paragraph.
- [ ] Trend: has the SII changed? Do the confidence intervals overlap? Don't call a change "significant" if they overlap heavily.
- [ ] Check the COVID years (2020-21) - are they unusual? Say so.

**Be able to explain:** what the SII means in one plain sentence, and how to read a funnel plot.

### Step 5: Risk and detection (1 day)
- [ ] Review figures 04-06 and the Spearman result.
- [ ] Sense-check the estimated undiagnosed total against published national estimates. If very different, find out why (denominators, ages, years).

**Be able to explain:** why correlation between the diagnosis gap and deaths does not prove that diagnosing more people would reduce deaths, and what evidence would.

### Step 6: Care (half a day)
- [ ] Review figure 07. Check the quintile direction is correct (Q5 = most deprived in the chart).

### Step 7: Model and priorities (1 day)
- [ ] Open `regression_mortality.csv`. Any VIF above ~5? Then predictors overlap heavily with deprivation - interpret individual coefficients cautiously.
- [ ] Open `priority_areas.csv`. Do the priority areas make sense? Change `priority_top_share` to 0.25 and see what changes - write one line on how sensitive the list is.

**Be able to explain:** the ecological fallacy, and why the priority rule is deliberately simple.

---

## WEEK 3 - Outputs

### Step 8: Public report "Hidden Risk" (2 days)
- [ ] Use `docs/02_public_report_template.md`. Write from `outputs/results_summary.md`.
- [ ] Every chart title states the finding. Every number checked against a table.
- [ ] Ask a non-analyst friend to read it. Rewrite anything they stumble on.

### Step 9: Technical explainer (1 day)
- [ ] Use `docs/03_technical_explainer_template.md`. Include every QA decision.

### Step 10: Dashboard (1-2 days)
- [ ] Follow `docs/05_dashboard_build_guide.md`. Save screenshots to `outputs/report/`.

### Step 11: Media and sign-off (half a day)
- [ ] Press summary and 60-second radio script: `docs/04_press_summary_and_media.md`.
- [ ] Record yourself saying the radio script. Listen back. Re-record.
- [ ] Complete `docs/06_stats_signoff_checklist.md` against your own outputs.

### Step 12: Package and apply (half a day)
- [ ] Update README key findings, push to GitHub.
- [ ] Update CV and supporting statement: `docs/07_application_and_interview.md`.

---

## Stretch (if time allows)

- [ ] **Teaching piece:** write a short tutorial "Pulling public health data with Python" for a junior analyst. Evidence for developing others.
- [ ] Spiegelhalter overdispersion adjustment for the funnel plot.
- [ ] Repeat the mortality analysis by sex.
- [ ] Map of priority areas (ONS boundary files + geopandas, or a Power BI shape map).
