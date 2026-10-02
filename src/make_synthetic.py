"""Create SYNTHETIC test data in the same format as Fingertips downloads.

    python -m src.make_synthetic
    python -m src.run_pipeline --raw-dir data/raw_synthetic --out-dir outputs_synthetic

Purpose: prove the pipeline runs end to end before the real data arrives,
and give you a 'known answer' test (deprivation effects are built in, so
the analysis should find them). Never publish anything made from this.
It also deliberately includes messy rows (sex and category breakdowns,
a suppressed value, a missing area) so the cleaning and QA steps are tested.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.utils import ROOT, load_config

rng = np.random.default_rng(2026)
OUT = ROOT / "data" / "raw_synthetic"
N = 153
COLS = ["Indicator ID", "Indicator Name", "Parent Code", "Parent Name", "Area Code",
        "Area Name", "Area Type", "Sex", "Age", "Category Type", "Category",
        "Time period", "Value", "Lower CI 95.0 limit", "Upper CI 95.0 limit", "Count",
        "Denominator", "Value note", "Time period Sortable"]


def _areas() -> pd.DataFrame:
    prefixes = rng.choice(["E06", "E08", "E09", "E10"], N, p=[0.4, 0.24, 0.22, 0.14])
    return pd.DataFrame({
        "code": [f"{pfx}{i:06d}" for i, pfx in enumerate(prefixes, start=1)],
        "name": [f"Synthetic Area {i:03d}" for i in range(1, N + 1)],
        "dep": rng.uniform(5, 45, N),
        "pop": rng.lognormal(np.log(330_000), 0.5, N).round(),
    })


def _rows(ind_id, name, areas, year, values, lci=None, uci=None, count=None,
          denom=None, sex="Persons", age="All ages"):
    df = pd.DataFrame({
        "Indicator ID": ind_id, "Indicator Name": name, "Parent Code": "E92000001",
        "Parent Name": "England", "Area Code": areas["code"].values,
        "Area Name": areas["name"].values, "Area Type": "Counties & UAs (from Apr 2023)",
        "Sex": sex, "Age": age, "Category Type": np.nan, "Category": np.nan,
        "Time period": str(year), "Value": np.round(values, 2),
        "Lower CI 95.0 limit": None if lci is None else np.round(lci, 2),
        "Upper CI 95.0 limit": None if uci is None else np.round(uci, 2),
        "Count": count, "Denominator": denom, "Value note": np.nan,
        "Time period Sortable": year * 10000,
    })
    eng = df.iloc[[0]].copy()
    eng[["Area Code", "Area Name", "Area Type"]] = ["E92000001", "England", "England"]
    w = denom if denom is not None else np.ones(len(values))
    eng["Value"] = round(float(np.average(values, weights=w)), 2)
    return pd.concat([df, eng], ignore_index=True)


def _prop_ci(p, n):
    se = np.sqrt(p / 100 * (1 - p / 100) / n) * 100
    return p - 1.96 * se, p + 1.96 * se


def main() -> None:
    cfg = load_config()
    ids = {k: (v["id"] or -1) for k, v in cfg["indicators"].items()}
    OUT.mkdir(parents=True, exist_ok=True)
    a = _areas()
    z = (a["dep"] - a["dep"].mean()) / a["dep"].std()

    # Outcome: under-75 CVD mortality 2013-2023, gap widening slightly after 2019.
    frames = []
    for yr in range(2013, 2024):
        base = 82 - 1.6 * min(yr - 2013, 6) - (0 if yr < 2020 else -1.5)
        slope = 15 + (0.8 * (yr - 2019) if yr > 2019 else 0)
        rate = np.clip(base + slope * z + rng.normal(0, 6, N), 25, None)
        cnt = rng.poisson(rate * a["pop"] / 1e5)
        rate = cnt / a["pop"] * 1e5
        se = rate / np.sqrt(np.maximum(cnt, 1))
        f = _rows(ids["under75_cvd_mortality"], "Under 75 mortality rate from CVD", a, yr,
                  rate, rate - 1.96 * se, rate + 1.96 * se, cnt, a["pop"], age="<75 yrs")
        frames.append(f)
        male = f.copy()
        male["Sex"], male["Value"] = "Male", male["Value"] * 1.6   # must be filtered out
        frames.append(male)
    mort = pd.concat(frames)
    mort["Value note"] = mort["Value note"].astype(object)
    mort.loc[(mort["Area Code"] == a["code"][5]) & (mort["Time period"] == "2023")
             & (mort["Sex"] == "Persons"), ["Value", "Value note"]] = [np.nan, "Value suppressed"]
    mort[COLS].to_csv(OUT / "under75_cvd_mortality.csv", index=False)

    # Hypertension: recorded (QOF, all ages) and undiagnosed (adults 16+, one year).
    list_size = (a["pop"] * 1.25).round()
    rec = 14.5 + 0.4 * z + rng.normal(0, 1.0, N)
    lo, hi = _prop_ci(rec, list_size)
    _rows(ids["hypertension_recorded"], "Hypertension: QOF prevalence", a, 2024, rec,
          lo, hi, (rec / 100 * list_size).round(), list_size)[COLS] \
        .to_csv(OUT / "hypertension_recorded.csv", index=False)
    adults = (a["pop"] * 1.05).round()
    und = 8.6 - 0.3 * z + rng.normal(0, 0.5, N)
    lo, hi = _prop_ci(und, adults)
    _rows(ids["hypertension_undiagnosed"], "Estimated prevalence of undiagnosed adult hypertension",
          a, 2021, und, lo, hi, (und / 100 * adults).round(), adults, age="16+ yrs")[COLS] \
        .to_csv(OUT / "hypertension_undiagnosed.csv", index=False)

    # Risk factors, several years, with a category breakdown that must be dropped.
    for key, label, base, eff, sd in [("smoking", "Smoking Prevalence in adults", 11, 3.2, 2.0),
                                      ("excess_weight", "Overweight (including obesity)", 63, 3.0, 3.0)]:
        fr = []
        for yr in (2021, 2022, 2023):
            v = base - 0.6 * (yr - 2021) + eff * z + rng.normal(0, sd, N)
            n = rng.integers(300, 1200, N)
            lo, hi = _prop_ci(v, n)
            fr.append(_rows(ids[key], label, a, yr, v, lo, hi, (v / 100 * n).round(), n,
                            age="18+ yrs"))
        df = pd.concat(fr)
        cat = df.iloc[:20].copy()
        cat["Category Type"], cat["Category"] = "Ethnic groups", "Group A"
        df = pd.concat([df, cat])
        if key == "smoking":
            df = df[~((df["Area Code"] == a["code"][10]) & (df["Time period"] == "2023"))]
        df[COLS].to_csv(OUT / f"{key}.csv", index=False)

    _rows(ids["deprivation"], "Deprivation score (IMD)", a, 2019, a["dep"])[COLS] \
        .to_csv(OUT / "deprivation.csv", index=False)

    # CVDPREVENT-style national table (quintile 1 = MOST deprived, as configured).
    care = []
    for ind, base, eff in [("Hypertension treated to target (aged under 80)", 66, -2.2),
                           ("On lipid-lowering therapy (QRISK 20%+)", 62, -1.8),
                           ("Atrial fibrillation on anticoagulation", 91, -0.9)]:
        for q in range(1, 6):
            v = base + eff * (3 - q) + rng.normal(0, 0.3)   # q=1 most deprived -> lowest
            care.append({"indicator": ind, "period": "To March 2025", "quintile": q,
                         "value": round(v, 1), "lower_ci": round(v - 0.3, 1),
                         "upper_ci": round(v + 0.3, 1)})
    pd.DataFrame(care).to_csv(OUT / cfg["cvdprevent"]["file"], index=False)
    print(f"Synthetic data written to {OUT}")


if __name__ == "__main__":
    main()
