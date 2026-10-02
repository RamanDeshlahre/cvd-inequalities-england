"""Unit tests for the statistical methods. Each test uses data with a KNOWN answer."""
import numpy as np
import pandas as pd

from src import stats as st


def test_sii_recovers_known_gradient():
    # value rises exactly 20 per unit of deprivation rank -> SII must be 20
    n = 100
    df = pd.DataFrame({"dep": np.arange(n), "pop": np.full(n, 1000.0)})
    rank = (np.arange(n) + 0.5) / n
    df["val"] = 50 + 20 * rank
    r = st.sii(df, "val", "dep", "pop")
    assert abs(r["sii"] - 20) < 1e-6
    assert abs(r["rii"] - 20 / 60) < 1e-6


def test_sii_zero_when_no_gradient():
    df = pd.DataFrame({"dep": range(50), "pop": 500.0, "val": 70.0})
    df.loc[::2, "val"] = 72.0                    # noise unrelated to deprivation order
    r = st.sii(df, "val", "dep", "pop")
    assert r["sii_lci"] < 0 < r["sii_uci"]


def test_quintile_summary_ci_contains_mean():
    rng = np.random.default_rng(1)
    df = pd.DataFrame({"x": rng.normal(50, 5, 150), "deprivation_quintile": np.repeat(range(1, 6), 30)})
    q = st.quintile_summary(df, "x")
    assert len(q) == 5
    assert ((q["lci"] < q["mean"]) & (q["mean"] < q["uci"])).all()


def test_funnel_limits_bracket_target_and_narrow():
    lo, hi = st.funnel_limits(70.0, np.array([20, 200, 2000]), 0.998)
    assert (lo < 70).all() and (hi > 70).all()
    assert (np.diff(hi - lo) < 0).all()          # limits narrow as areas get bigger


def test_overdispersion_detects_extra_variation():
    rng = np.random.default_rng(2)
    expected = rng.uniform(50, 500, 150)
    target = 70.0
    poisson_rates = rng.poisson(expected) / expected * target
    od_none = st.overdispersion(poisson_rates, expected, target)
    noisy = poisson_rates + rng.normal(0, 15, 150)   # add real between-area variation
    od_big = st.overdispersion(noisy, expected, target)
    assert od_none["phi"] < 2
    assert od_big["phi"] > 3 and od_big["tau2"] > 0


def test_ols_hc3_recovers_coefficient():
    rng = np.random.default_rng(3)
    df = pd.DataFrame({"x": rng.normal(0, 1, 500)})
    df["y"] = 10 + 4 * df["x"] + rng.normal(0, 1, 500)
    tbl, fit = st.ols_hc3(df, "y", ["x"])
    b = tbl.loc[tbl["term"] == "x"].iloc[0]
    # coefficient is per 1 SD of x (sd ~ 1), so close to 4
    assert b["lci"] < 4 * df["x"].std() < b["uci"]
    assert fit["r2"] > 0.9


def test_priority_flags_need_both_domains():
    df = pd.DataFrame({"area_code": list("ABCDE"), "area_name": list("ABCDE"),
                       "risk": [1, 2, 3, 4, 10], "death": [10, 2, 3, 4, 9]})
    out = st.priority_flags(df, {"Risk": [("risk", True)], "Outcome": [("death", True)]}, 0.2, 2)
    assert out.loc[out["area_code"] == "E", "priority_area"].item()
    assert not out.loc[out["area_code"] == "A", "priority_area"].item()
