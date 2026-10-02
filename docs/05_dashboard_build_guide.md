# Dashboard build guide (Power BI)

**Purpose:** let a decision-maker answer "how does my area compare, and is it a prevention priority?" in under a minute.

## Data

Load two CSVs from `outputs/tables/`:

| Table | Grain | Use |
|---|---|---|
| `powerbi_area_latest.csv` | one row per local authority | cards, bars, area explorer, priority list |
| `powerbi_long_all_years.csv` | indicator x area x period | trend charts |

In Power Query: set `priority_area` and `*_flag` columns to True/False, `deprivation_quintile` to whole number, `year` to whole number.
Relationship: `area_latest[area_code]` 1 -> many `long_all_years[area_code]`.

## Measures (DAX)

```DAX
Avg Early CVD Deaths = AVERAGE ( powerbi_area_latest[under75_cvd_mortality] )

Most Deprived Q5 = CALCULATE ( [Avg Early CVD Deaths], powerbi_area_latest[deprivation_quintile] = 5 )
Least Deprived Q1 = CALCULATE ( [Avg Early CVD Deaths], powerbi_area_latest[deprivation_quintile] = 1 )
Deprivation Ratio = DIVIDE ( [Most Deprived Q5], [Least Deprived Q1] )

Undiagnosed Hypertension = SUM ( powerbi_area_latest[estimated_undiagnosed] )

Priority Areas =
CALCULATE ( COUNTROWS ( powerbi_area_latest ), powerbi_area_latest[priority_area] = TRUE () )

England Early CVD Deaths = 71.5   -- England 2025 value (data/processed/england.csv)


Selected vs England =
VAR sel = SELECTEDVALUE ( powerbi_area_latest[under75_cvd_mortality] )
RETURN IF ( ISBLANK ( sel ), BLANK (), sel - [England Early CVD Deaths] )

Trend Value = AVERAGE ( powerbi_long_all_years[value] )
```

## Pages

**1. Overview** - four KPI cards (England rate, Deprivation Ratio, Undiagnosed Hypertension, Priority Areas); bar chart of Avg Early CVD Deaths by quintile; one-sentence text box with the headline finding.

**2. My area** - slicer on `area_name` (search enabled); cards for each indicator with the England value underneath; "Selected vs England" with conditional colour; text showing quintile and number of priority domains flagged.

**3. Inequality over time** - line chart of Trend Value by `year`, legend = `deprivation_quintile`, filtered to the mortality indicator and quintiles 1 and 5.

**4. Prevention priorities** - table of priority areas sorted by domains flagged: area, quintile, early death rate, funnel status, estimated undiagnosed. Optional shape map (ONS boundary file converted to TopoJSON) coloured by `n_domains_flagged`.

## Design rules
- Same colours as the report (light-to-dark blue for deprivation, red for England).
- Every visual has a title that states what it shows and a footnote with data period.
- An "About" button linking to the technical explainer.
- Test on a laptop screen at 100% zoom; nothing should need scrolling on page 1.

## Evidence for the application
Save screenshots of each page to `outputs/report/` and publish (if you can) to the Power BI public web, or record a 90-second screen video walking through it.
