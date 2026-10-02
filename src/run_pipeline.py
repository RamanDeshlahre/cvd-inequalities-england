"""Run the full analysis: clean -> QA -> analysis -> figures -> summary.

    python -m src.run_pipeline
    python -m src.run_pipeline --raw-dir data/raw_synthetic --out-dir outputs_synthetic

The second form runs on synthetic test data (see src/make_synthetic.py).
Synthetic results are NOT real findings and must never be published.
"""
from __future__ import annotations

import argparse

import numpy as np
import pandas as pd

from src import clean, figures, qa
from src import stats as st
from src.utils import get_logger, load_config, paths

log = get_logger("pipeline")
SOURCE = "Source: OHID Fingertips; CVDPREVENT (NHS England); English Indices of Deprivation 2025. Analysis: {author}."


def _key(cfg, role):
    keys = [k for k, v in cfg["indicators"].items() if v["role"] == role and v.get("id")]
    return keys[0] if keys else None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw-dir")
    ap.add_argument("--out-dir")
    args = ap.parse_args()

    cfg = load_config()
    T = cfg.get("chart_titles", {})
    p = paths(args.raw_dir, args.out_dir)
    synthetic = bool(args.raw_dir and "synthetic" in args.raw_dir)
    source = ("SYNTHETIC TEST DATA - NOT REAL FINDINGS" if synthetic
              else SOURCE.format(author=cfg.get("author", "[Your name]")))
    if synthetic:   # synthetic files exist for every indicator, even unconfigured ones
        for v in cfg["indicators"].values():
            v["id"] = v["id"] or -1

    tables = clean.build(cfg, p)
    qa_results = qa.run(cfg, tables, p)
    if any(r[0] == "FAIL" for r in qa_results):
        log.error("QA has FAIL results - fix before trusting any output.")

    area, long, england = tables["area"], tables["long"], tables["england"]
    acfg = cfg["analysis"]
    out_k = _key(cfg, "outcome")
    dep_k = _key(cfg, "deprivation")
    rf_keys = [k for k, v in cfg["indicators"].items()
               if v["role"] == "risk_factor" and v.get("id")]
    summary: dict = {}
    eng_latest = (england.sort_values("period_sortable")
                  .groupby("indicator_key")["value"].last().to_dict())

    # ------------------------------------------------------------------
    # OUTCOMES: under-75 CVD mortality
    # ------------------------------------------------------------------
    period_of = (long.sort_values("period_sortable").groupby("indicator_key")["period"]
                 .last().to_dict())
    qs = st.quintile_summary(area, out_k)
    qs.to_csv(p["tables"] / "outcome_by_quintile.csv", index=False)
    summary["mortality_gap"] = st.gap_ratio(qs)
    pop = f"{out_k}_denominator"
    summary["mortality_sii"] = st.sii(area, out_k, dep_k, pop)
    figures.quintile_bars(
        qs, T.get("mortality_quintile", "Early deaths from heart and circulatory disease by deprivation"),
        f"Under-75 CVD mortality, mean of local authorities, {period_of.get(out_k)}",
        "Deaths per 100,000 (age-standardised)", source,
        p["figures"] / "01_mortality_by_quintile.png", eng_latest.get(out_k))

    target = eng_latest.get(out_k, area[out_k].median())
    area["expected_deaths"] = area[pop] * target / 1e5
    fd = area.dropna(subset=[out_k, "expected_deaths"])
    od = st.overdispersion(fd[out_k], fd["expected_deaths"], target)
    summary["overdispersion"] = od
    lo_p, hi_p = st.funnel_limits(target, area["expected_deaths"].clip(lower=1), 0.998)
    lo_a, hi_a = st.adjusted_limits(target, area["expected_deaths"].clip(lower=1), od["tau2"], 0.998)
    area["funnel_poisson"] = np.where(area[out_k] > hi_p, "Above", np.where(area[out_k] < lo_p, "Below", "Within"))
    area["funnel_status"] = np.where(area[out_k] > hi_a, "Above limits",
                                     np.where(area[out_k] < lo_a, "Below limits", "Within limits"))
    area.loc[area[out_k].isna(), ["funnel_poisson", "funnel_status"]] = np.nan
    figures.funnel_plot(
        area, out_k, "expected_deaths", target, acfg["funnel_limits"],
        T.get("funnel", "Which areas have unusually high early death rates?"),
        f"Under-75 CVD mortality by local authority, {period_of.get(out_k)}",
        source, p["figures"] / "02_mortality_funnel.png", tau2=od["tau2"])
    summary["funnel_counts_poisson"] = area["funnel_poisson"].value_counts().to_dict()
    summary["funnel_counts"] = area["funnel_status"].value_counts().to_dict()
    summary["funnel_above"] = (area.loc[area["funnel_status"] == "Above limits"]
                               .sort_values(out_k, ascending=False)["area_name"].tolist())

    # Trend: Q1 vs Q5 and SII per year (uses latest IMD for every year).
    trend_rows, sii_rows = [], []
    mort = long[long["indicator_key"] == out_k]
    for yr, g in mort.groupby("year"):
        if g["value"].notna().sum() < acfg["trend_min_areas"]:
            continue
        s = st.quintile_summary(g, "value")
        s["year"] = int(yr)
        trend_rows.append(s)
        r = st.sii(g, "value", "deprivation_score", "denominator")
        r["year"] = int(yr)
        sii_rows.append(r)
    if trend_rows:
        trend = pd.concat(trend_rows)
        sii_t = pd.DataFrame(sii_rows)
        trend.to_csv(p["tables"] / "outcome_trend_by_quintile.csv", index=False)
        sii_t.to_csv(p["tables"] / "outcome_sii_trend.csv", index=False)
        figures.trend_gap(
            trend, T.get("trend", "Is the gap in early heart deaths closing?"),
            "Under-75 CVD mortality, mean of local authorities by deprivation fifth "
            "(shaded = 95% CI)", source, p["figures"] / "03_mortality_trend_gap.png")
        summary["sii_first_last"] = (sii_t.iloc[0][["year", "sii", "sii_lci", "sii_uci"]].to_dict(),
                                     sii_t.iloc[-1][["year", "sii", "sii_lci", "sii_uci"]].to_dict())

    # ------------------------------------------------------------------
    # RISK: detection gap and risk factors
    # ------------------------------------------------------------------
    U = "undiagnosed_hypertension_pct"
    risk_tables = {}
    for col in [U] + rf_keys:
        if area[col].notna().sum() > 10:
            risk_tables[col] = st.quintile_summary(area, col)
            risk_tables[col].assign(measure=col).to_csv(
                p["tables"] / f"risk_{col}_by_quintile.csv", index=False)
    if U in risk_tables:
        und_k = _key(cfg, "risk_undiagnosed")
        figures.quintile_bars(
            risk_tables[U], T.get("undiagnosed_quintile", "Undiagnosed high blood pressure by deprivation"),
            f"Estimated % of adults (16+) with undiagnosed hypertension, {period_of.get(und_k)}",
            "% of adults", source, p["figures"] / "04_undiagnosed_by_quintile.png",
            eng_latest.get(und_k))
        summary["undiagnosed_total"] = float(area["estimated_undiagnosed"].sum())
        summary["undiagnosed_spearman_deprivation"] = st.spearman(area, U, dep_k)
        summary["undiagnosed_spearman_mortality"] = st.spearman(area, U, out_k)
        figures.scatter_quintile(
            area, U, out_k, "Undiagnosed hypertension (% of adults)",
            "Under-75 CVD deaths per 100,000",
            T.get("undiagnosed_vs_mortality", "Undiagnosed high blood pressure and early deaths"),
            "Each point is a local authority (association, not cause)", source,
            p["figures"] / "05_undiagnosed_vs_mortality.png")
    for i, k in enumerate(rf_keys):
        figures.quintile_bars(
            risk_tables[k], T.get(k, f"{cfg['indicators'][k]['label']} by deprivation"),
            f"Mean of local authorities, {period_of.get(k)}", "%", source,
            p["figures"] / f"06{chr(97 + i)}_{k}_by_quintile.png", eng_latest.get(k))
    summary["risk_gaps"] = {k: st.gap_ratio(v) for k, v in risk_tables.items()}
    summary["risk_spearman_deprivation"] = {k: st.spearman(area, k, dep_k) for k in rf_keys}

    # ------------------------------------------------------------------
    # CARE: CVDPREVENT by deprivation quintile (national)
    # ------------------------------------------------------------------
    care_path = p["raw"] / cfg["cvdprevent"]["file"]
    if care_path.exists():
        allc = pd.read_csv(care_path)
        if cfg["cvdprevent"]["quintile_1_is_most_deprived"]:
            allc["quintile"] = acfg["n_quintiles"] + 1 - allc["quintile"]
        allc = allc.sort_values(["indicator", "quintile"])
        det_codes = cfg["cvdprevent"].get("detection_codes", [])
        care = allc[~allc["indicator_code"].isin(det_codes)].copy()
        short = cfg["cvdprevent"].get("short_names", {})
        care["indicator"] = care["indicator_code"].map(short).fillna(care["indicator"])
        det = allc[allc["indicator_code"].isin(det_codes)]
        per = allc["period"].iloc[0]
        if not care.empty:
            figures.care_chart(care, T.get("care", "Treatment by deprivation"),
                               f"CVDPREVENT, England, patients by deprivation quintile, {per} (95% CI)",
                               source, p["figures"] / "07_care_by_quintile.png")
        if not det.empty:
            d0 = det[det["indicator_code"] == det["indicator_code"].iloc[0]]
            figures.quintile_bars(
                d0.rename(columns={"lower_ci": "lci", "upper_ci": "uci", "value": "mean"}),
                T.get("detection", "Unconfirmed high blood pressure readings by deprivation"),
                f"% of patients with one high BP reading and no hypertension diagnosis, CVDPREVENT, {per}",
                "% of patients", source,
                p["figures"] / "08_detection_cvdprevent_by_quintile.png",
                xlabel="Patient deprivation quintile", decimals=2)
        # Gap in people: how many more (or fewer) people would meet the measure
        # if the most deprived quintile matched the least deprived.
        rows = []
        for code, g in allc.groupby("indicator_code"):
            least = g[g["quintile"] == 1].iloc[0]
            most = g[g["quintile"] == acfg["n_quintiles"]].iloc[0]
            rows.append({"indicator_code": code, "indicator": most["indicator"],
                         "least_deprived_pct": least["value"], "most_deprived_pct": most["value"],
                         "gap_pp": round(most["value"] - least["value"], 2),
                         "people_difference_if_matched": round(
                             (least["value"] - most["value"]) / 100 * most["denominator"]),
                         "most_deprived_denominator": most["denominator"]})
        gaps = pd.DataFrame(rows)
        gaps.to_csv(p["tables"] / "cvdprevent_gaps.csv", index=False)
        summary["care"] = gaps.to_dict("records")
    else:
        log.warning("No CVDPREVENT file at %s - care section skipped.", care_path)

    # ------------------------------------------------------------------
    # MODEL + PRIORITIES
    # ------------------------------------------------------------------
    xs = [c for c in [dep_k, U] + rf_keys if area[c].notna().sum() > 30]
    reg, fit = st.ols_hc3(area, out_k, xs)
    reg.to_csv(p["tables"] / "regression_mortality.csv", index=False)
    summary["regression"] = fit

    # Detection is not used as a priority domain: the modelled undiagnosed estimate
    # tracks overall (age-driven) prevalence - see QA notes and technical explainer.
    domains = {
        "Risk": [(k, True) for k in rf_keys],
        "Outcome": [(out_k, True)],
    }
    pri = st.priority_flags(area, domains, acfg["priority_top_share"],
                            acfg["priority_min_domains"])
    pri = pri.merge(area[["area_code", "deprivation_quintile", out_k, "funnel_status",
                          "undiagnosed_hypertension_pct"] + rf_keys], on="area_code")
    pri.sort_values(["n_domains_flagged", out_k], ascending=False).to_csv(
        p["tables"] / "priority_areas.csv", index=False)
    summary["n_priority"] = int(pri["priority_area"].sum())
    summary["priority_names"] = pri.loc[pri["priority_area"], "area_name"].tolist()
    summary["priority_share_q5"] = (
        float((pri.loc[pri["priority_area"], "deprivation_quintile"] == 5).mean())
        if summary["n_priority"] else np.nan)

    # Power BI exports
    area.merge(pri[["area_code"] + [c for c in pri if c.endswith(("_score", "_flag"))]
                   + ["n_domains_flagged", "priority_area"]], on="area_code") \
        .to_csv(p["tables"] / "powerbi_area_latest.csv", index=False)
    long.to_csv(p["tables"] / "powerbi_long_all_years.csv", index=False)

    _write_summary(summary, cfg, period_of, p, synthetic)
    log.info("Done. Figures: %s | Tables: %s", p["figures"], p["tables"])


def _f(x, d=1):
    return "n/a" if x is None or (isinstance(x, float) and np.isnan(x)) else f"{x:,.{d}f}"


def _write_summary(s, cfg, period_of, p, synthetic):
    L = ["# Results summary (auto-generated)", ""]
    if synthetic:
        L += ["> **SYNTHETIC TEST DATA. These numbers are invented to test the code.**", ""]
    L += ["Use these numbers to write the report. Re-check each one against the "
          "tables before quoting it.", "", "## Outcomes"]
    g = s["mortality_gap"]
    L.append(f"- Under-75 CVD mortality ({period_of.get('under75_cvd_mortality')}): "
             f"least deprived fifth of areas {_f(g['q1_mean'])}, most deprived "
             f"{_f(g['q5_mean'])} per 100,000 - a gap of {_f(g['abs_gap'])} "
             f"({_f(g['ratio'], 2)} times higher).")
    m = s["mortality_sii"]
    L.append(f"- Slope index of inequality: {_f(m['sii'])} per 100,000 "
             f"(95% CI {_f(m['sii_lci'])} to {_f(m['sii_uci'])}); RII {_f(m['rii'], 2)}.")
    if "sii_first_last" in s:
        a, b = s["sii_first_last"]
        L.append(f"- SII changed from {_f(a['sii'])} in {int(a['year'])} to "
                 f"{_f(b['sii'])} in {int(b['year'])}. Overlapping CIs? "
                 f"{a['sii_lci']:.1f}-{a['sii_uci']:.1f} vs {b['sii_lci']:.1f}-{b['sii_uci']:.1f}.")
    od = s["overdispersion"]
    L.append(f"- Funnel plot, Poisson 99.8% limits: {s['funnel_counts_poisson']} - overdispersion "
             f"phi = {od['phi']:.1f} (1 = none), tau = {od['tau']:.1f} per 100,000.")
    L.append(f"- Funnel plot, overdispersion-adjusted 99.8% limits: {s['funnel_counts']}. "
             f"Above: {', '.join(s['funnel_above'])}")
    L += ["", "## Risk and detection"]
    if "undiagnosed_total" in s:
        L.append(f"- Estimated adults with undiagnosed hypertension (sum of areas): "
                 f"{_f(s['undiagnosed_total'], 0)}")
        for lab, key in [("deprivation", "undiagnosed_spearman_deprivation"),
                         ("early deaths", "undiagnosed_spearman_mortality")]:
            c = s[key]
            L.append(f"- Spearman, undiagnosed % vs {lab}: rho = {c['rho']:.2f} "
                     f"(p = {c['p_value']:.3g}, n = {c['n']}).")
    for k, c in s.get("risk_spearman_deprivation", {}).items():
        L.append(f"- Spearman, {k} vs deprivation: rho = {c['rho']:.2f} (p = {c['p_value']:.3g}).")
    for k, v in s["risk_gaps"].items():
        d = 2 if abs(v['q1_mean']) < 2 else 1
        L.append(f"- {k}: Q1 {_f(v['q1_mean'], d)} vs Q5 {_f(v['q5_mean'], d)} "
                 f"(gap {_f(v['abs_gap'], d)}).")
    if "care" in s:
        L += ["", "## Care and detection (CVDPREVENT, patient-level)"]
        for r in s["care"]:
            L.append(f"- {r['indicator']}: least deprived {r['least_deprived_pct']}% vs most "
                     f"deprived {r['most_deprived_pct']}% (gap {r['gap_pp']:+.2f} pp). People "
                     f"difference if most deprived matched least: {r['people_difference_if_matched']:,}.")
    L += ["", "## Model and priorities",
          f"- Regression R-squared {s['regression']['r2']:.2f} (n = {s['regression']['n']}); "
          "see tables/regression_mortality.csv and check VIFs before interpreting.",
          f"- Priority areas (worst fifth on both risk and early deaths): "
          f"{s['n_priority']}; share in most deprived quintile: "
          f"{_f(100 * s['priority_share_q5'], 0)}%.",
          f"- Priority areas: {', '.join(s['priority_names'])}"]
    (p["out"] / "results_summary.md").write_text("\n".join(L), encoding="utf-8")


if __name__ == "__main__":
    main()
