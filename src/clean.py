"""STEP 2 - Clean raw Fingertips files into tidy analysis tables.

Outputs (in data/processed/):
    long_all_years.csv  one row per indicator x area x period (tidy)
    england.csv         England values, used as the benchmark
    area_latest.csv     one row per upper-tier LA, latest period of each
                        indicator, with deprivation quintile and derived measures
    cleaning_log.json   every filtering decision, with row counts
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from src.utils import active_indicators, get_logger

log = get_logger("clean")

RENAME = {
    "Indicator ID": "indicator_id", "Indicator Name": "indicator_name",
    "Area Code": "area_code", "Area Name": "area_name", "Area Type": "area_type",
    "Sex": "sex", "Age": "age", "Category Type": "category_type",
    "Category": "category", "Time period": "period",
    "Time period Sortable": "period_sortable", "Value": "value",
    "Lower CI 95.0 limit": "lci", "Upper CI 95.0 limit": "uci",
    "Count": "count", "Denominator": "denominator", "Value note": "value_note",
    "Time period range": "period_range",
}
KEEP = ["indicator_key", "indicator_id", "indicator_name", "area_code", "area_name",
        "sex", "age", "period", "period_sortable", "year", "value", "lci", "uci",
        "count", "denominator", "value_note"]


def _read_one(path, key: str, spec: dict, log_entries: dict) -> pd.DataFrame:
    df = pd.read_csv(path, low_memory=False).rename(columns=RENAME)
    steps = {"raw_rows": len(df)}

    # 1. Drop breakdown rows (e.g. by ethnicity or deprivation decile inside an area).
    if "category_type" in df.columns:
        df = df[df["category_type"].isna()]
    steps["after_drop_category_breakdowns"] = len(df)

    # 2. Pick one sex / age breakdown, as configured.
    for col in ("sex", "age"):
        wanted = spec.get(col)
        if col in df.columns:
            options = df[col].dropna().unique().tolist()
            if wanted:
                df = df[df[col] == wanted]
            elif len(options) > 1:
                log.warning("%s has several %s values %s; set '%s' in config.yaml. "
                            "Using the most common.", key, col, options, col)
                df = df[df[col] == df[col].value_counts().idxmax()]
            steps[f"after_{col}_filter"] = len(df)

    # 3. Single-year vs pooled periods share the same sortable period, so pick one.
    if spec.get("period_range") and "period_range" in df.columns:
        df = df[df["period_range"] == spec["period_range"]]
        steps["after_period_range_filter"] = len(df)

    df = df.copy()
    df["indicator_key"] = key
    for c in ("value", "lci", "uci", "count", "denominator", "period_sortable"):
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
        else:
            df[c] = np.nan
    if "value_note" not in df.columns:
        df["value_note"] = np.nan
    # Fingertips sortable periods look like 20230000 -> 2023.
    df["year"] = (df["period_sortable"] // 10000).astype("Int64")
    log_entries[key] = steps
    return df[[c for c in KEEP if c in df.columns]]


def build(cfg: dict, p: dict) -> dict[str, pd.DataFrame]:
    log_entries: dict = {}
    frames = []
    for key, spec in active_indicators(cfg).items():
        f = p["raw"] / f"{key}.csv"
        if not f.exists():
            log.warning("Missing raw file %s - run src.fetch_data first.", f.name)
            continue
        frames.append(_read_one(f, key, spec, log_entries))
    if not frames:
        raise FileNotFoundError("No raw data found. Run python -m src.fetch_data")
    long = pd.concat(frames, ignore_index=True)

    # England appears twice in Fingertips files (with and without a parent).
    england = (long[long["area_code"] == cfg["england_code"]]
               .drop_duplicates(["indicator_key", "period"]).copy())
    prefixes = tuple(cfg["upper_tier_prefixes"])
    long = long[long["area_code"].astype(str).str.startswith(prefixes)].copy()
    log_entries["upper_tier_rows_all_indicators"] = len(long)

    # ---- latest period, one row per area -------------------------------
    latest_period = long.groupby("indicator_key")["period_sortable"].transform("max")
    latest = long[long["period_sortable"] == latest_period]
    area = (latest.pivot_table(index=["area_code"], columns="indicator_key",
                               values="value", aggfunc="first"))
    names = latest.groupby("area_code")["area_name"].first()
    area.insert(0, "area_name", names)

    # Extra columns needed for funnel plot, SII and undiagnosed estimates.
    for key in [k for k, v in cfg["indicators"].items() if v["role"] == "outcome"]:
        sub = latest[latest["indicator_key"] == key].set_index("area_code")
        for c in ("lci", "uci", "count", "denominator"):
            area[f"{key}_{c}"] = sub[c]
    und = [k for k, v in cfg["indicators"].items()
           if v["role"] == "risk_undiagnosed" and v.get("id")]
    if und and und[0] in area:
        sub = latest[latest["indicator_key"] == und[0]].set_index("area_code")
        area["undiagnosed_hypertension_pct"] = area[und[0]]
        area["estimated_undiagnosed"] = sub["count"].round()
        area["undiagnosed_adult_population"] = sub["denominator"]
    else:
        log.warning("Undiagnosed hypertension indicator missing.")
        area["undiagnosed_hypertension_pct"] = np.nan
        area["estimated_undiagnosed"] = np.nan

    # ---- deprivation quintiles -----------------------------------------
    dep = [k for k, v in cfg["indicators"].items() if v["role"] == "deprivation"][0]
    n_q = cfg["analysis"]["n_quintiles"]
    has_dep = area[dep].notna()
    area["deprivation_quintile"] = pd.Series(pd.NA, index=area.index, dtype="Int64")
    area.loc[has_dep, "deprivation_quintile"] = pd.qcut(
        area.loc[has_dep, dep].rank(method="first"), n_q, labels=range(1, n_q + 1)
    ).astype(int)
    log_entries["areas_in_latest_table"] = int(len(area))
    log_entries["areas_without_deprivation"] = area.index[~has_dep].tolist()

    # ---- deprivation for every year (for trends, uses latest IMD) --------
    long = long.merge(area[[dep, "deprivation_quintile"]].reset_index()
                      .rename(columns={dep: "deprivation_score"}),
                      on="area_code", how="left")

    area = area.reset_index()
    long.to_csv(p["processed"] / "long_all_years.csv", index=False)
    england.to_csv(p["processed"] / "england.csv", index=False)
    area.to_csv(p["processed"] / "area_latest.csv", index=False)
    with open(p["processed"] / "cleaning_log.json", "w", encoding="utf-8") as fh:
        json.dump(log_entries, fh, indent=2, default=str)
    log.info("Clean tables saved: %s areas, %s indicators.",
             len(area), long["indicator_key"].nunique())
    return {"long": long, "england": england, "area": area}
