"""Convert CVDPREVENT Data Explorer exports (.xlsx) into the single care file
the pipeline reads: data/raw/cvdprevent_by_deprivation.csv

    1. Save each export into data/raw/cvdprevent/ (any file name ending .xlsx)
    2. python -m src.load_cvdprevent

Keeps England, all persons, deprivation-quintile rows only. Numerators and
denominators are kept so the 'people affected' calculations are reproducible.
"""
from __future__ import annotations

import pandas as pd

from src.utils import get_logger, load_config, paths

log = get_logger("cvdprevent")


def main() -> None:
    cfg = load_config()
    p = paths()
    folder = p["raw"] / "cvdprevent"
    files = sorted(folder.glob("*.xlsx"))
    if not files:
        raise FileNotFoundError(f"No .xlsx exports in {folder}")
    frames = []
    for f in files:
        df = pd.read_excel(f, sheet_name="sheet1")
        d = df[(df["MetricCategoryTypeName"] == "Deprivation quintile")
               & (df["AreaCode"] == cfg["england_code"])
               & (df["CategoryAttribute"] == "Persons")].copy()
        if d.empty:
            log.warning("%s: no England deprivation-quintile rows.", f.name)
            continue
        d["quintile"] = d["MetricCategoryName"].astype(str).str.extract(r"^(\d)").astype(int)
        frames.append(pd.DataFrame({
            "indicator_code": d["IndicatorCode"],
            "indicator": d["IndicatorShortName"].str.replace(r"\s*\(CVDP\w+\)\s*$", "", regex=True),
            "period": d["TimePeriodName"], "quintile": d["quintile"],
            "numerator": d["Numerator"], "denominator": d["Denominator"],
            "value": d["Value"], "lower_ci": d["LowerConfidenceLimit"],
            "upper_ci": d["UpperConfidenceLimit"],
        }))
        log.info("%s: %s, %s", f.name, d["IndicatorCode"].iloc[0], d["TimePeriodName"].iloc[0])
    out = pd.concat(frames).sort_values(["indicator_code", "quintile"])
    out.to_csv(p["raw"] / cfg["cvdprevent"]["file"], index=False)
    log.info("Wrote %s rows for %s indicators.", len(out), out["indicator_code"].nunique())


if __name__ == "__main__":
    main()
