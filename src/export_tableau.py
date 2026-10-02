"""Export clean, Tableau-ready tables (friendly column names, labels,
precomputed funnel limits) to outputs/tableau/.

    python -m src.export_tableau        (run after src.run_pipeline)

Files
    tableau_areas.csv       one row per local authority: all measures, quintile,
                            funnel limits, priority flags
    tableau_trend.csv       mortality by deprivation quintile and year, plus England and SII
    tableau_cvdprevent.csv  treatment and detection by patient deprivation quintile
"""
from __future__ import annotations

import pandas as pd

from src import stats as st
from src.utils import get_logger, load_config, paths

log = get_logger("tableau")
QLAB = {1: "1 - Least deprived", 2: "2", 3: "3", 4: "4", 5: "5 - Most deprived"}


def main() -> None:
    cfg = load_config()
    p = paths()
    out = p["out"] / "tableau"
    out.mkdir(exist_ok=True)

    a = pd.read_csv(p["tables"] / "powerbi_area_latest.csv")
    eng = (pd.read_csv(p["processed"] / "england.csv").sort_values("period_sortable")
           .groupby("indicator_key")["value"].last())
    target = eng["under75_cvd_mortality"]

    # Funnel limits at each area's own expected deaths (draw as lines sorted by x).
    e = a["expected_deaths"].clip(lower=1)
    od_tau2 = st.overdispersion(a.dropna(subset=["under75_cvd_mortality", "expected_deaths"])
                                ["under75_cvd_mortality"],
                                a.dropna(subset=["under75_cvd_mortality", "expected_deaths"])
                                ["expected_deaths"], target)["tau2"]
    lo95, hi95 = st.funnel_limits(target, e, 0.95)
    lo998, hi998 = st.adjusted_limits(target, e, od_tau2, 0.998)

    areas = pd.DataFrame({
        "Area code": a["area_code"],
        "Area": a["area_name"],
        "Deprivation score (IMD 2025)": a["deprivation"].round(2),
        "Deprivation quintile": a["deprivation_quintile"],
        "Deprivation quintile label": a["deprivation_quintile"].map(QLAB),
        "Under-75 CVD deaths per 100,000 (2025)": a["under75_cvd_mortality"].round(1),
        "Mortality lower 95% CI": a["under75_cvd_mortality_lci"].round(1),
        "Mortality upper 95% CI": a["under75_cvd_mortality_uci"].round(1),
        "Under-75 CVD deaths (count)": a["under75_cvd_mortality_count"],
        "Expected deaths at England rate": a["expected_deaths"].round(1),
        "Funnel 95% lower (chance only)": lo95.round(1),
        "Funnel 95% upper (chance only)": hi95.round(1),
        "Funnel 99.8% lower (adjusted)": lo998.round(1),
        "Funnel 99.8% upper (adjusted)": hi998.round(1),
        "Funnel status": a["funnel_status"],
        "Smoking % (2024)": a["smoking"].round(1),
        "Overweight or obese % (2024/25)": a["excess_weight"].round(1),
        "Recorded hypertension % (QOF 2024/25)": a["hypertension_recorded"].round(1),
        "Undiagnosed hypertension % (2021, modelled)": a["undiagnosed_hypertension_pct"].round(2),
        "Undiagnosed hypertension (people, 2021)": a["estimated_undiagnosed"],
        "Risk score (percentile)": (a["Risk_score"] * 100).round(0),
        "Outcome score (percentile)": (a["Outcome_score"] * 100).round(0),
        "Priority area": a["priority_area"].map({True: "Yes", False: "No"}),
        "England: under-75 CVD deaths per 100,000": round(target, 1),
        "England: smoking %": round(eng["smoking"], 1),
        "England: overweight or obese %": round(eng["excess_weight"], 1),
        "England: undiagnosed hypertension %": round(eng["hypertension_undiagnosed"], 2),
    })
    areas.to_csv(out / "tableau_areas.csv", index=False)

    t = pd.read_csv(p["tables"] / "outcome_trend_by_quintile.csv")
    sii = pd.read_csv(p["tables"] / "outcome_sii_trend.csv")[["year", "sii", "sii_lci", "sii_uci"]]
    em = (pd.read_csv(p["processed"] / "england.csv")
          .query("indicator_key == 'under75_cvd_mortality'")[["year", "value"]]
          .rename(columns={"value": "England rate"}))
    trend = (t.assign(**{"Deprivation quintile label": t["quintile"].map(QLAB)})
             .merge(sii, on="year").merge(em, on="year", how="left")
             .rename(columns={"year": "Year", "quintile": "Deprivation quintile",
                              "mean": "Mean rate per 100,000", "lci": "Lower 95% CI",
                              "uci": "Upper 95% CI", "n_areas": "Areas",
                              "sii": "Slope index of inequality", "sii_lci": "SII lower 95% CI",
                              "sii_uci": "SII upper 95% CI"})
             .drop(columns=["median"]).round(2))
    trend.to_csv(out / "tableau_trend.csv", index=False)

    c = pd.read_csv(p["raw"] / cfg["cvdprevent"]["file"])
    if cfg["cvdprevent"]["quintile_1_is_most_deprived"]:
        c["quintile"] = 6 - c["quintile"]
    short = cfg["cvdprevent"].get("short_names", {})
    det = cfg["cvdprevent"].get("detection_codes", [])
    c["Measure"] = c["indicator_code"].map(short).fillna(c["indicator"])
    c["Measure type"] = c["indicator_code"].apply(lambda x: "Detection" if x in det else "Treatment")
    c["Deprivation quintile label"] = c["quintile"].map(QLAB)
    c = c.rename(columns={"indicator_code": "Indicator code", "period": "Period",
                          "quintile": "Deprivation quintile", "numerator": "Numerator",
                          "denominator": "Denominator", "value": "Percent",
                          "lower_ci": "Lower 95% CI", "upper_ci": "Upper 95% CI"})
    c.drop(columns=["indicator"]).to_csv(out / "tableau_cvdprevent.csv", index=False)
    log.info("Tableau files written to %s", out)


if __name__ == "__main__":
    main()
