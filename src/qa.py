"""STEP 3 - Automated quality assurance.

Writes outputs/qa_report.md. Each check is PASS, WARN or FAIL.
WARN means "look at this and document your decision", not "stop".
This mirrors a statistics sign-off process: nothing is published until
every WARN has a written explanation in the technical explainer.
"""
from __future__ import annotations

import pandas as pd

from src.utils import active_indicators, get_logger

log = get_logger("qa")


def run(cfg: dict, tables: dict, p: dict) -> list[tuple[str, str, str]]:
    long, area = tables["long"], tables["area"]
    results: list[tuple[str, str, str]] = []

    def add(status: str, check: str, detail: str) -> None:
        results.append((status, check, detail))

    inds = active_indicators(cfg)
    missing_cfg = [k for k, v in cfg["indicators"].items() if v.get("id") is None]
    add("WARN" if missing_cfg else "PASS", "All indicators configured",
        f"Not configured: {missing_cfg}" if missing_cfg else "All indicator IDs set.")

    # Coverage: areas per indicator in its latest period.
    latest = long[long["period_sortable"] ==
                  long.groupby("indicator_key")["period_sortable"].transform("max")]
    counts = latest.groupby("indicator_key")["area_code"].nunique()
    all_areas = set(area["area_code"])
    for key in inds:
        n = int(counts.get(key, 0))
        have = set(latest.loc[latest["indicator_key"] == key, "area_code"])
        gaps = sorted(all_areas - have)
        status = "PASS" if n >= 140 and not gaps else "WARN"
        add(status, f"Coverage: {key}",
            f"{n} areas in latest period; missing: {gaps[:10]}{' ...' if len(gaps) > 10 else ''}")

    # Duplicates.
    dup = long.duplicated(["indicator_key", "area_code", "period"]).sum()
    add("PASS" if dup == 0 else "FAIL", "No duplicate area-period rows",
        f"{dup} duplicates (fix the sex/age filters in config.yaml)" if dup else "None found.")

    # Plausible ranges.
    for key, spec in inds.items():
        v = long.loc[long["indicator_key"] == key, "value"].dropna()
        if v.empty:
            add("FAIL", f"Values present: {key}", "No numeric values.")
            continue
        if spec.get("unit") == "%":
            bad = ((v < 0) | (v > 100)).sum()
        else:
            bad = (v < 0).sum()
        add("PASS" if bad == 0 else "FAIL", f"Plausible range: {key}",
            f"min {v.min():.2f}, max {v.max():.2f}, out of range: {bad}")

    # Confidence intervals bracket the value.
    ci = long.dropna(subset=["value", "lci", "uci"])
    bad_ci = ((ci["lci"] > ci["value"]) | (ci["uci"] < ci["value"])).sum()
    add("PASS" if bad_ci == 0 else "FAIL", "CIs contain point estimate",
        f"{bad_ci} rows where value lies outside its CI")

    # Suppressed or missing values.
    miss = latest[latest["value"].isna()]
    if len(miss):
        notes = miss.groupby("indicator_key")["value_note"].first().to_dict()
        add("WARN", "Suppressed / missing values (latest period)",
            f"{len(miss)} rows. Notes: {notes}")
    else:
        add("PASS", "Suppressed / missing values (latest period)", "None.")

    # Period alignment - indicators often have different latest years.
    periods = latest.groupby("indicator_key")["period"].first().to_dict()
    add("WARN" if len(set(periods.values())) > 1 else "PASS",
        "Latest periods aligned", f"{periods} - state these in every chart footnote")

    # Ages used per indicator - must match what the report says.
    ages = {k: long.loc[long["indicator_key"] == k, "age"].dropna().unique().tolist()
            for k in inds}
    multi = {k: v for k, v in ages.items() if len(v) != 1}
    add("PASS" if not multi else "FAIL", "One age group per indicator",
        f"{ages}" if not multi else f"Several ages kept: {multi}")

    # Indicators with only one period cannot be used for trends.
    n_per = long.groupby("indicator_key")["period"].nunique().to_dict()
    single = [k for k, n in n_per.items() if n == 1]
    add("WARN" if single else "PASS", "Periods available per indicator",
        f"{n_per}. Single period only: {single} - cross-sectional use only")

    # Areas without deprivation score (boundary changes).
    no_dep = area[area["deprivation_quintile"].isna()]["area_name"].tolist()
    add("PASS" if not no_dep else "WARN", "Every area has a deprivation score",
        f"Missing: {no_dep}" if no_dep else "All matched.")

    # Quintile sizes.
    qs = {int(k): int(v) for k, v in area["deprivation_quintile"].value_counts().sort_index().items()}
    add("PASS", "Deprivation quintile sizes", f"{qs}")

    _write(results, p)
    n_fail = sum(r[0] == "FAIL" for r in results)
    n_warn = sum(r[0] == "WARN" for r in results)
    log.info("QA finished: %s FAIL, %s WARN. See qa_report.md", n_fail, n_warn)
    return results


def _write(results, p) -> None:
    lines = ["# QA report", "",
             "Every WARN needs a written decision in the technical explainer "
             "before outputs are signed off.", "",
             "| Status | Check | Detail |", "|---|---|---|"]
    for status, check, detail in results:
        lines.append(f"| {status} | {check} | {str(detail).replace('|', '/')} |")
    (p["out"] / "qa_report.md").write_text("\n".join(lines), encoding="utf-8")
