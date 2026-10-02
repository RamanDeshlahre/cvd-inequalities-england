# Tableau dashboard build guide

**Goal:** a public Tableau dashboard you can link from your CV and README, so a BHF reviewer can explore the findings in two minutes.
**Tool:** Tableau Public (free) — either the desktop app or "Create" in the browser at public.tableau.com.
**Time:** about 3–4 hours.

---

## 1. Data

Three files in `outputs/tableau/` (regenerate with `python -m src.export_tableau`). Connect each as a **separate data source** - no joins needed.

| File | Grain | Used for |
|---|---|---|
| `tableau_areas.csv` | 1 row per local authority (153) | funnel plot, area explorer, priority table, scatter |
| `tableau_trend.csv` | quintile x year (125) | quintile bar chart, trend lines, SII |
| `tableau_cvdprevent.csv` | measure x quintile (20) | treatment and detection charts |

After connecting, check data types: `Deprivation quintile` = Number (whole) but set it to **Dimension / Discrete**; `Year` = Number, **Continuous**.

## 2. Style (use the same look as the report)

| Element | Colour |
|---|---|
| Quintile 1 (least deprived) to 5 (most deprived) | `#c6dbef` `#9ecae1` `#6baed6` `#3182bd` `#08519c` |
| England reference lines, accents | `#c8102e` |
| Secondary text, gridlines | `#6b6b6b` / light grey |

Font: Tableau Book / Tableau Semibold for titles. Every sheet title states the **finding** (copy them from the report). Every dashboard has a source line at the bottom:
*Source: OHID Fingertips; CVDPREVENT (NHS England); English Indices of Deprivation 2025. Analysis: Raman D.*

Set the quintile colours once: right-click `Deprivation quintile label` > Default Properties > Color > assign the five colours.

## 3. Parameter and calculated fields

**Parameter `Select area`** (data source: tableau_areas): String, List, "Add values from" > `Area`. Default: "Blackpool". Right-click > Show Parameter.

Calculated fields in **tableau_areas**:

```
// Selected area flag
[Area] = [Select area]

// Mortality vs England (per 100,000)
[Under-75 CVD deaths per 100,000 (2025)] - [England: under-75 CVD deaths per 100,000]

// Mortality vs England label
IF [Funnel status] = "Above limits" THEN "Well above England (outside adjusted limits)"
ELSEIF [Funnel status] = "Below limits" THEN "Well below England"
ELSE "Within expected range" END

// Times England
[Under-75 CVD deaths per 100,000 (2025)] / [England: under-75 CVD deaths per 100,000]
```

Calculated fields in **tableau_trend**:

```
// CI width (for error bars)
[Upper 95% CI] - [Lower 95% CI]

// Most vs least deprived ratio
{FIXED [Year] : AVG(IF [Deprivation quintile] = 5 THEN [Mean rate per 100,000] END)}
/ {FIXED [Year] : AVG(IF [Deprivation quintile] = 1 THEN [Mean rate per 100,000] END)}
```

Calculated field in **tableau_cvdprevent**:

```
// CI width
[Upper 95% CI] - [Lower 95% CI]
```

## 4. Sheets

### Sheet 1 — KPI tiles (4 small text sheets)
Big number + one-line label each. Use a Text mark, font 28+ for the number.
- **71.5** — under-75 CVD deaths per 100,000, England 2025 (`England: under-75...`, AVG)
- **1.8×** — most vs least deprived areas (`Most vs least deprived ratio`, filter Year = 2025, format 0.0"×")
- **51.8** — slope index of inequality, 2025 (`Slope index of inequality`, AVG, Year = 2025)
- **71,000** — more people with blood pressure on target if the most deprived matched the least (type as text, from `outputs/tables/cvdprevent_gaps.csv`)

### Sheet 2 — Early deaths by deprivation (bar + error bars)
Source: tableau_trend. Filter `Year` = 2025.
1. Columns: `Deprivation quintile label`. Rows: `Mean rate per 100,000` (AVG). Mark: **Bar**, colour = `Deprivation quintile label`. Label = on.
2. Error bars: drag `Lower 95% CI` to Rows (second axis). Mark: **Gantt Bar**, Size = `CI width`, colour dark grey. Right-click axis > **Dual Axis** > **Synchronize Axis**. Hide the second axis.
3. Reference line: Analytics pane > Reference Line > constant, value 71.5, label "England", red dashed.

### Sheet 3 — Is the gap closing? (trend)
Source: tableau_trend.
1. Columns: `Year` (continuous). Rows: `Mean rate per 100,000`. Mark: **Line**, colour = `Deprivation quintile label`.
2. Filter quintile to **1 and 5** (cleaner), or keep all five.
3. Optional band: add `Lower 95% CI` and `Upper 95% CI` on a dual axis as an **Area** mark with 25% opacity, or simply show them in the tooltip.
4. Annotate 2019 (Right-click a point > Annotate > Point): "Gap narrowest in 2019".

**Sheet 3b — SII over time (optional):** Columns `Year`, Rows `Slope index of inequality`, Line; Gantt error bars as in Sheet 2 using SII CIs.

### Sheet 4 — Which areas stand out? (funnel plot)
Source: tableau_areas. **Analysis menu > untick Aggregate Measures** (so each area is its own point).
1. Columns: `Expected deaths at England rate`. Rows: `Under-75 CVD deaths per 100,000 (2025)`. Mark: **Circle**, colour = `Deprivation quintile label`, Detail = `Area`.
2. Funnel lines: drag **Measure Values** to Rows as a second axis. Filter Measure Names to the four `Funnel ...` fields. Mark: **Line**, colour = `Measure Names` (greys for 95% chance-only, red for 99.8% adjusted). Lines join points in order along the x-axis.
   *If the lines zig-zag instead of forming smooth curves:* right-click `Expected deaths at England rate` > **Convert to Dimension** (keep it Continuous), so Tableau draws the line in order along the x-axis.
3. **Dual Axis** > **Synchronize Axis**. Move the circles to front (right-click axis > Move marks to front).
4. Reference line at 71.5 (England).
5. Label only areas with `Funnel status` = "Above limits": drag `Area` to Label, then Label > "Selected" or use a calc `IF [Funnel status]="Above limits" THEN [Area] END`.
6. Highlight the selected area: drag `Selected area flag` to Size or Shape.

Tooltip:
```
<Area> (quintile <Deprivation quintile label>)
Under-75 CVD deaths: <Under-75 CVD deaths per 100,000 (2025)> per 100,000
95% CI: <Mortality lower 95% CI> to <Mortality upper 95% CI>
England: 71.5 | Status: <Mortality vs England label>
```

### Sheet 5 — My area scorecard
Source: tableau_areas. Filter: `Selected area flag` = True.
Text table with rows for each measure and two columns: **Area** and **England**. Easiest way: put **Measure Values** on Text, filter Measure Names to the 4 area measures + their England equivalents, and arrange; or build 4 tiny BAN sheets. Add `Deprivation quintile label`, `Funnel status` and `Priority area` as text lines.

### Sheet 6 — Prevention priority areas (table)
Source: tableau_areas. Filter `Priority area` = Yes.
Rows: `Area`. Columns (Measure Values): `Under-75 CVD deaths...`, `Smoking %`, `Overweight or obese %`, plus `Deprivation quintile label` and `Funnel status`. Sort by deaths descending. Colour the deaths column with a light-to-dark red sequential palette.

### Sheet 7 — Treatment by deprivation (dot plot)
Source: tableau_cvdprevent. Filter `Measure type` = Treatment.
Rows: `Measure`. Columns: `Percent`. Mark: **Circle**, colour = `Deprivation quintile label`, size large. Add Gantt CI bars as in Sheet 2 if you like. Fix the x-axis to start around 55.

### Sheet 8 — Unconfirmed high blood pressure readings
Same source, filter `Measure type` = Detection. Bar chart by `Deprivation quintile label`, label values to 2 decimals.

### Sheet 9 (optional) — Map
Download the **Counties and Unitary Authorities (2023 boundaries), generalised** boundary file (GeoJSON or shapefile) from the ONS Open Geography Portal. Add it as a second connection and **relate** its area-code field (named like `CTYUA23CD`) to `Area code`. Drag `Geometry` to the view; colour by `Under-75 CVD deaths...` or `Priority area`. If any areas don't match, list them in your technical explainer.

## 5. Dashboards

**Dashboard 1 — "The gap" (fixed size 1200 x 900)**
- Top: title "Early heart deaths are 1.8 times higher in England's most deprived areas" + one sentence subtitle + KPI tiles (Sheet 1).
- Middle left: Sheet 2 (quintile bars). Middle right: Sheet 3 (trend).
- Bottom left: Sheet 4 (funnel). Bottom right: Sheet 6 (priority table).
- Footer: source line + "Areas, not individuals. Associations, not causes."

**Dashboard 2 — "My area"**
- `Select area` parameter at the top.
- Sheet 5 (scorecard) left; Sheet 4 (funnel, with the selected area highlighted) right.
- Dashboard action: Dashboard > Actions > **Change Parameter** — source sheet Sheet 4, target `Select area`, field `Area`. Clicking a dot now updates the scorecard.

**Dashboard 3 — "Care and detection"**
- Sheet 7 and Sheet 8 side by side, with a text box explaining the statin finding and the two undiagnosed measures (copy from the report, section 4–5).

Optionally combine them as a **Story** (Story > New Story), one point per dashboard.

## 6. Check before publishing (your sign-off)
- [ ] Every number on the dashboard matches `outputs/results_summary.md`.
- [ ] Quintile colours run light (least) to dark (most) everywhere.
- [ ] Each title states a finding; each dashboard has the source line.
- [ ] Tooltips are readable (no raw field names like "AGG(...)").
- [ ] Test the area selector with 3 areas (e.g. Blackpool, Rutland, Manchester).
- [ ] View in Device Preview > Phone — at least Dashboard 1 should be readable.

## 7. Publish
File > **Save to Tableau Public**. Name it "Cardiovascular Inequalities in England". On your Tableau Public profile, add a description and the GitHub link. Copy the dashboard URL into:
- the README (replace the Tableau placeholder),
- your CV project line,
- and take a screenshot of Dashboard 1 → save as `outputs/figures/tableau_dashboard.png` and add it to the README.
