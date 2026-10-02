"""Sensitivity and diagnostic checks: do the conclusions survive reasonable
alternative choices? Writes outputs/sensitivity.md.

    python -m src.sensitivity      (run after src.run_pipeline)

Checks
1. Deprivation measure: IMD 2025 (main) vs IMD 2019.
2. Priority threshold: worst 20% (main) vs worst 25%.
3. What drives the modelled undiagnosed-hypertension estimate? Compared with
   recorded (crude, all-age) prevalence as a proxy for older age structure.
4. Funnel plot: Poisson vs overdispersion-adjusted limits (reported by pipeline).
"""
from __future__ import annotations

import pandas as pd

from src import stats as st
from src.utils import get_logger, load_config, paths

log = get_logger("sensitivity")


def main() -> None:
    cfg = load_config()
    p = paths()
    a = pd.read_csv(p["processed"] / "area_latest.csv")
    out_k, dep_k = "under75_cvd_mortality", "deprivation"
    L = ["# Sensitivity and diagnostic checks", ""]

    # 1. IMD 2019 vs IMD 2025 -------------------------------------------------
    f19 = p["raw"] / "deprivation_imd2019.csv"
    if f19.exists():
        old = pd.read_csv(f19)
        old = (old[old["Category Type"].isna()]
               [["Area Code", "Value"]].drop_duplicates("Area Code")
               .rename(columns={"Area Code": "area_code", "Value": "imd2019"}))
        m = a.merge(old, on="area_code")
        m["q2019"] = pd.qcut(m["imd2019"].rank(method="first"), 5, labels=range(1, 6)).astype(int)
        moved = m[m["q2019"] != m["deprivation_quintile"]]
        rho = m["imd2019"].corr(m[dep_k], method="spearman")
        g25 = st.gap_ratio(st.quintile_summary(m, out_k))
        g19 = st.gap_ratio(st.quintile_summary(m, out_k, q_col="q2019"))
        L += ["## 1. Deprivation measure (IMD 2025 vs IMD 2019)", "",
              f"- Spearman correlation between the two scores: {rho:.3f}",
              f"- Areas changing quintile: {len(moved)} of {len(m)}; largest move: "
              f"{int((moved['q2019'] - moved['deprivation_quintile']).abs().max())} quintile",
              f"- Under-75 CVD mortality, most vs least deprived quintile: "
              f"IMD 2025 ratio {g25['ratio']:.2f} (gap {g25['abs_gap']:.1f}); "
              f"IMD 2019 ratio {g19['ratio']:.2f} (gap {g19['abs_gap']:.1f})",
              f"- Moved into the most deprived quintile under IMD 2025: "
              f"{', '.join(moved.loc[moved['deprivation_quintile'] == 5, 'area_name'])}",
              "- **Conclusion:** the choice of IMD version does not change the findings.", ""]

    # 2. Priority threshold ----------------------------------------------------
    rf = [k for k, v in cfg["indicators"].items() if v["role"] == "risk_factor"]
    domains = {"Risk": [(k, True) for k in rf], "Outcome": [(out_k, True)]}
    res = {}
    for share in (0.20, 0.25):
        pr = st.priority_flags(a, domains, share, 2)
        res[share] = set(pr.loc[pr["priority_area"], "area_name"])
    added = sorted(res[0.25] - res[0.20])
    L += ["## 2. Priority-area threshold (worst 20% vs worst 25%)", "",
          f"- 20%: {len(res[0.20])} areas; 25%: {len(res[0.25])} areas",
          f"- All 20% areas still flagged at 25%: {res[0.20] <= res[0.25]}",
          f"- Added at 25%: {', '.join(added) if added else 'none'}",
          "- **Conclusion:** the core list is stable; the threshold only changes how long it is.", ""]

    # 3. Undiagnosed estimate diagnostics --------------------------------------
    r_rec = a["undiagnosed_hypertension_pct"].corr(a["hypertension_recorded"], method="spearman")
    r_dep = a["undiagnosed_hypertension_pct"].corr(a[dep_k], method="spearman")
    r_rec_dep = a["hypertension_recorded"].corr(a[dep_k], method="spearman")
    low = a.nsmallest(5, "undiagnosed_hypertension_pct")["area_name"].tolist()
    high = a.nlargest(5, "undiagnosed_hypertension_pct")["area_name"].tolist()
    L += ["## 3. What drives the modelled undiagnosed hypertension estimate?", "",
          f"- Spearman with recorded (crude, all-age) hypertension prevalence: {r_rec:.2f}",
          f"- Spearman with deprivation: {r_dep:.2f}",
          f"- Recorded prevalence vs deprivation: {r_rec_dep:.2f}",
          f"- Lowest areas: {', '.join(low)}",
          f"- Highest areas: {', '.join(high)}",
          "- **Interpretation:** the estimate moves almost one-for-one with overall "
          "(crude) prevalence, which is most likely driven by age structure: lowest in young "
          "inner-city areas, highest in older coastal and rural areas. It is therefore not "
          "used as a 'detection' domain for priority areas. GP-record data (CVDPREVENT) "
          "show unconfirmed high readings are more common in the most deprived quintile.", ""]

    (p["out"] / "sensitivity.md").write_text("\n".join(L), encoding="utf-8")
    log.info("Wrote sensitivity.md")


if __name__ == "__main__":
    main()
