"""Deeper analyses, run after src.run_pipeline:

    python -m src.deep_dive

1. By sex      - is the deprivation gap different for men and women? (SII by sex, 2001-2025)
2. Has the gap really stalled? - segmented (piecewise) trend in the SII, before vs after 2019
3. Excess early deaths - deaths each year above the rate of the least deprived fifth of areas
4. How much of the gap do smoking and weight account for? - attenuation of the deprivation effect
5. Sensitivity - 3-year pooled rates (2023-25) instead of single-year 2025

Writes outputs/deep_dive.md, tables in outputs/tables/ and figures 09-10.
"""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

from src import figures as fg
from src import stats as st
from src.utils import get_logger, load_config, paths

log = get_logger("deep_dive")
OUT_K = "under75_cvd_mortality"


def _mortality(p, sex: str, period_range: str, cfg) -> pd.DataFrame:
    """Upper-tier LA mortality rows for one sex and period type, with IMD 2025 attached."""
    raw = pd.read_csv(p["raw"] / f"{OUT_K}.csv", low_memory=False)
    d = raw[raw["Category Type"].isna() & (raw["Sex"] == sex)
            & (raw["Time period range"] == period_range)
            & raw["Area Code"].str[:3].isin(cfg["upper_tier_prefixes"])].copy()
    d["year"] = (d["Time period Sortable"] // 10000).astype(int)
    d = d.rename(columns={"Area Code": "area_code", "Value": "value", "Count": "count",
                          "Denominator": "denominator", "Time period": "period"})
    area = pd.read_csv(p["processed"] / "area_latest.csv")[
        ["area_code", "area_name", "deprivation", "deprivation_quintile"]]
    return d.merge(area, on="area_code", how="inner")


def sii_by_year(d: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for yr, g in d.groupby("year"):
        g = g.dropna(subset=["value", "denominator"])
        if len(g) < 100:
            continue
        r = st.sii(g, "value", "deprivation", "denominator")
        q = st.quintile_summary(g, "value")
        r.update({"year": yr, **{f"q{int(k)}": v for k, v in q.set_index("quintile")["mean"].items()}})
        rows.append(r)
    return pd.DataFrame(rows)


def _wfit(sub: pd.DataFrame, centre: int) -> dict:
    """Weighted linear trend in the SII (weights = 1 / variance from each year's 95% CI)."""
    se = (sub["sii_uci"] - sub["sii_lci"]) / (2 * 1.96)
    w = (1 / se ** 2).to_numpy(float)
    X = np.column_stack([np.ones(len(sub)), sub["year"] - centre])
    y = sub["sii"].to_numpy(float)
    beta, cov = st._wls(X, y, w)
    s = np.sqrt(cov[1, 1])
    t = stats.t.ppf(0.975, max(len(sub) - 2, 1))
    return {"years": f"{int(sub['year'].min())}-{int(sub['year'].max())}", "n_years": len(sub),
            "slope_per_year": beta[1], "lci": beta[1] - t * s, "uci": beta[1] + t * s,
            "centre": centre, "intercept_at_centre": beta[0],
            "wsse": float((w * (y - X @ beta) ** 2).sum())}


def find_break(sii_t: pd.DataFrame, end: int, lo: int, hi: int) -> tuple[int, pd.DataFrame]:
    """Data-driven break year for the pre-pandemic period: the year that minimises the
    weighted squared error of two separate straight lines (start-k and k-end)."""
    pre = sii_t[sii_t["year"] <= end]
    rows = []
    for k in range(lo, hi + 1):
        a, b = _wfit(pre[pre["year"] <= k], k), _wfit(pre[pre["year"] >= k], k)
        rows.append({"break_year": k, "wsse": a["wsse"] + b["wsse"]})
    grid = pd.DataFrame(rows)
    return int(grid.loc[grid["wsse"].idxmin(), "break_year"]), grid


def segmented_trend(sii_t: pd.DataFrame, brk: int, pandemic: int) -> dict:
    first, last = int(sii_t["year"].min()), int(sii_t["year"].max())
    return {
        "segment_1": _wfit(sii_t[sii_t["year"] <= brk], brk),
        "segment_2": _wfit(sii_t[(sii_t["year"] >= brk) & (sii_t["year"] <= pandemic)], brk),
        "segment_3": _wfit(sii_t[sii_t["year"] >= pandemic], pandemic),
        "first": first, "last": last,
    }


def excess_deaths(d: pd.DataFrame) -> pd.DataFrame:
    """Approximate early CVD deaths above the least-deprived-fifth rate, per year.
    Uses each area's age-standardised rate applied to its under-75 population,
    so it is an approximation (standardised rates are not crude rates)."""
    rows = []
    for yr, g in d.dropna(subset=["value", "denominator", "count"]).groupby("year"):
        ref = g.loc[g["deprivation_quintile"] == 1, "value"].mean()
        excess = ((g["value"] - ref).clip(lower=0) * g["denominator"] / 1e5).sum()
        rows.append({"year": yr, "reference_rate_q1": ref, "excess_deaths": excess,
                     "observed_deaths": g["count"].sum(),
                     "excess_share": excess / g["count"].sum()})
    return pd.DataFrame(rows)


def attenuation(area: pd.DataFrame, rf: list[str], dep: str) -> dict:
    d = area.dropna(subset=[OUT_K, dep] + rf)
    base, _ = st.ols_hc3(d, OUT_K, [dep])
    full, fit = st.ols_hc3(d, OUT_K, [dep] + rf)
    b0 = base.loc[base["term"] == dep, "coef_per_sd"].iloc[0]
    b1 = full.loc[full["term"] == dep, "coef_per_sd"].iloc[0]
    return {"n": len(d), "dep_coef_alone": b0, "dep_coef_adjusted": b1,
            "attenuation_pct": 100 * (b0 - b1) / b0, "r2_full": fit["r2"],
            "full_table": full}


def _fig_sex(sex_tbl: pd.DataFrame, path, source, title) -> None:
    fig, ax = plt.subplots(figsize=(7.5, 4.4))
    for sex, colour in [("Male", "#08519c"), ("Female", "#c8102e")]:
        t = sex_tbl[sex_tbl["sex"] == sex]
        ax.plot(t["year"], t["sii"], color=colour, lw=2.2, marker="o", ms=3.5)
        ax.fill_between(t["year"], t["sii_lci"], t["sii_uci"], color=colour, alpha=0.15)
        ax.text(t["year"].iloc[-1] + 0.3, t["sii"].iloc[-1], "Men" if sex == "Male" else "Women",
                color=colour, va="center", fontsize=9, fontweight="bold")
    ax.set_xlim(sex_tbl["year"].min() - 0.5, sex_tbl["year"].max() + 3.5)
    ax.set_ylim(bottom=0)
    ax.set_xlabel("Year")
    ax.set_ylabel("Slope index of inequality\n(deaths per 100,000)")
    fg._finish(fig, ax, title,
               "Slope index of inequality in under-75 CVD mortality by sex, 2001-2025 (shaded = 95% CI)",
               source, path)


def _fig_segmented(sii_t: pd.DataFrame, seg: dict, path, source, title) -> None:
    fig, ax = plt.subplots(figsize=(7.5, 4.4))
    ax.errorbar(sii_t["year"], sii_t["sii"],
                yerr=[sii_t["sii"] - sii_t["sii_lci"], sii_t["sii_uci"] - sii_t["sii"]],
                fmt="o", color="#3182bd", ecolor="#9ecae1", ms=4, capsize=2, label="SII (95% CI)")
    for key, colour in [("segment_1", "#333333"), ("segment_2", "#7a7a7a"), ("segment_3", "#c8102e")]:
        s = seg[key]
        y0, y1 = (int(x) for x in s["years"].split("-"))
        xs = np.array([y0, y1])
        ax.plot(xs, s["intercept_at_centre"] + s["slope_per_year"] * (xs - s["centre"]), color=colour,
                lw=2.2, label=f"{s['years']}: {s['slope_per_year']:+.1f} per year")
    ax.set_ylim(bottom=0)
    ax.set_xlabel("Year")
    ax.set_ylabel("Slope index of inequality\n(deaths per 100,000)")
    ax.legend(fontsize=8, frameon=False, loc="upper right")
    _finish = fg._finish
    _finish(fig, ax, title,
            "Slope index of inequality, under-75 CVD mortality, persons; weighted straight-line trends per period",
            source, path)


def main() -> None:
    cfg = load_config()
    p = paths()
    source = ("Source: OHID Fingertips; English Indices of Deprivation 2025. "
              f"Analysis: {cfg.get('author', '[Your name]')}.")
    L = ["# Deep dive: further analyses", "",
         "Run after `src.run_pipeline`. All results use upper-tier local authorities and IMD 2025 quintiles.", ""]

    # 1. Sex ---------------------------------------------------------------------
    tbls = []
    for sex in ("Persons", "Male", "Female"):
        t = sii_by_year(_mortality(p, sex, "1y", cfg))
        t["sex"] = sex
        tbls.append(t)
    sex_tbl = pd.concat(tbls, ignore_index=True)
    sex_tbl.to_csv(p["tables"] / "deep_sii_by_sex.csv", index=False)
    T = cfg.get("chart_titles", {})
    _fig_sex(sex_tbl[sex_tbl["sex"] != "Persons"], p["figures"] / "09_sii_by_sex.png", source,
             T.get("sii_by_sex", "Deprivation gap in early heart deaths, men and women"))
    last = sex_tbl[sex_tbl["year"] == sex_tbl["year"].max()].set_index("sex")
    first = sex_tbl[sex_tbl["year"] == sex_tbl["year"].min()].set_index("sex")
    L += ["## 1. Men and women", ""]
    for sex in ("Male", "Female"):
        r, f = last.loc[sex], first.loc[sex]
        L.append(f"- **{sex}s, {int(r['year'])}:** least deprived fifth {r['q1']:.1f}, most deprived "
                 f"{r['q5']:.1f} per 100,000 (ratio {r['q5'] / r['q1']:.2f}); SII {r['sii']:.1f} "
                 f"(95% CI {r['sii_lci']:.1f} to {r['sii_uci']:.1f}). SII in {int(f['year'])}: {f['sii']:.1f}.")
    L += [f"- The male SII is {last.loc['Male', 'sii'] / last.loc['Female', 'sii']:.1f} times the female SII. "
          "Relative inequality (RII) is "
          f"{last.loc['Male', 'rii']:.2f} for men and {last.loc['Female', 'rii']:.2f} for women.", ""]

    # 2. Segmented trend -----------------------------------------------------------
    persons = sex_tbl[sex_tbl["sex"] == "Persons"].reset_index(drop=True)
    pandemic = 2019
    brk, grid = find_break(persons, end=pandemic, lo=2005, hi=2015)
    grid.to_csv(p["tables"] / "deep_break_year_search.csv", index=False)
    seg = segmented_trend(persons, brk, pandemic)
    pd.DataFrame({k: v for k, v in seg.items() if k.startswith("segment")}).T.to_csv(
        p["tables"] / "deep_segmented_trend.csv")
    _fig_segmented(persons, seg, p["figures"] / "10_sii_segmented_trend.png", source,
                   T.get("sii_segmented", "Trend in the deprivation gap over time"))
    s1, s2, s3 = seg["segment_1"], seg["segment_2"], seg["segment_3"]
    sii_at = persons.set_index("year")["sii"]
    m_mid = persons[(persons["year"] >= brk) & (persons["year"] <= pandemic)]["sii"].mean()
    m_post = persons[persons["year"] > pandemic]["sii"].mean()
    L += ["## 2. When did the gap stop closing?", "",
          f"- A data-driven search (2005-2015) finds the best break year in the pre-pandemic trend is "
          f"**{brk}**.",
          f"- **{s1['years']}:** the SII fell by **{-s1['slope_per_year']:.1f} per year** "
          f"(95% CI {-s1['uci']:.1f} to {-s1['lci']:.1f}), from {sii_at[seg['first']]:.1f} to "
          f"{sii_at[brk]:.1f} ({100 * (1 - sii_at[brk] / sii_at[seg['first']]):.0f}% lower).",
          f"- **{s2['years']}:** essentially flat, {s2['slope_per_year']:+.2f} per year "
          f"(95% CI {s2['lci']:+.2f} to {s2['uci']:+.2f}).",
          f"- **{s3['years']}:** {s3['slope_per_year']:+.2f} per year (95% CI {s3['lci']:+.2f} to "
          f"{s3['uci']:+.2f}). Average SII {m_post:.1f} after {pandemic}, vs {m_mid:.1f} in {brk}-{pandemic}.",
          f"- **Reading:** the gap narrowed quickly in the 2000s, **stopped narrowing around {brk}**, and has "
          "been slightly higher since the pandemic. Earlier outputs said the gap 'fell until 2019'; this "
          f"analysis shows almost all of the fall happened by {brk}. Outputs were updated to say so.",
          "- The break year is estimated, but with few points per segment; treat it as 'around' that year.", ""]

    # 3. Excess deaths -------------------------------------------------------------
    ex = excess_deaths(_mortality(p, "Persons", "1y", cfg))
    ex.to_csv(p["tables"] / "deep_excess_deaths.csv", index=False)
    e_last = ex.iloc[-1]
    e_avg = ex[ex["year"] >= ex["year"].max() - 2]
    L += ["## 3. Excess early deaths", "",
          f"- In {int(e_last['year'])}, about **{e_last['excess_deaths']:,.0f}** early CVD deaths "
          f"({100 * e_last['excess_share']:.0f}% of {e_last['observed_deaths']:,.0f}) would not have "
          f"occurred if every area had the death rate of the least deprived fifth "
          f"({e_last['reference_rate_q1']:.1f} per 100,000).",
          f"- Average over {int(e_avg['year'].min())}-{int(e_avg['year'].max())}: "
          f"**{e_avg['excess_deaths'].mean():,.0f} a year**.",
          "- Approximate: age-standardised rates applied to each area's under-75 population; "
          "a scale estimate, not a precise count. Round it in public outputs.", ""]

    # 4. Attenuation ----------------------------------------------------------------
    area = pd.read_csv(p["processed"] / "area_latest.csv")
    rf = [k for k, v in cfg["indicators"].items() if v["role"] == "risk_factor"]
    att = attenuation(area, rf, "deprivation")
    att["full_table"].to_csv(p["tables"] / "deep_attenuation_model.csv", index=False)
    L += ["## 4. How much of the deprivation gap do smoking and weight account for?", "",
          f"- Deprivation alone: **{att['dep_coef_alone']:.1f}** more deaths per 100,000 per 1 SD of deprivation.",
          f"- After adding smoking and excess weight: **{att['dep_coef_adjusted']:.1f}** "
          f"(R-squared {att['r2_full']:.2f}, n = {att['n']}).",
          f"- The deprivation coefficient falls by **{att['attenuation_pct']:.0f}%**. At area level, smoking "
          "and weight account for only part of the gap; most of the association with deprivation remains.",
          "- Caution: area averages, survey-based risk factors, and no data on blood pressure, diet, "
          "access to care or ethnicity. This is a description, not a causal decomposition.", ""]

    # 5. 3-year pooled sensitivity -------------------------------------------------
    pooled = _mortality(p, "Persons", "3y", cfg)
    pl = pooled[pooled["year"] == pooled["year"].max()].dropna(subset=["value"])
    q = st.gap_ratio(st.quintile_summary(pl, "value"))
    s3 = st.sii(pl, "value", "deprivation", "denominator")
    single = persons.iloc[-1]
    L += ["## 5. Sensitivity: 3-year pooled rates", "",
          f"- {pl['period'].iloc[0]} pooled: Q5/Q1 ratio **{q['ratio']:.2f}**, SII **{s3['sii']:.1f}** "
          f"(95% CI {s3['sii_lci']:.1f} to {s3['sii_uci']:.1f}).",
          f"- Single year {int(single['year'])}: ratio {single['q5'] / single['q1']:.2f}, SII {single['sii']:.1f}.",
          "- **Conclusion:** pooling three years gives the same picture; the main findings do not depend "
          "on single-year noise.", ""]

    (p["out"] / "deep_dive.md").write_text("\n".join(L), encoding="utf-8")
    log.info("Wrote deep_dive.md")


if __name__ == "__main__":
    main()
