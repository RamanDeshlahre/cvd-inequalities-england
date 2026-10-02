"""Statistical methods used in the analysis.

Written with numpy/scipy only so every calculation is transparent and
easy to explain at interview. Each function says what it assumes.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats


# ---------------------------------------------------------------------
# 1. Quintile summaries
# ---------------------------------------------------------------------
def quintile_summary(df: pd.DataFrame, col: str,
                     q_col: str = "deprivation_quintile") -> pd.DataFrame:
    """Mean of area values per deprivation quintile with a t-based 95% CI.

    Assumes each area counts equally (unweighted). This describes the
    'typical area' in each quintile, not the typical person - say so.
    """
    rows = []
    for q, g in df.dropna(subset=[col, q_col]).groupby(q_col):
        x = g[col].to_numpy(float)
        n, m = len(x), x.mean()
        se = x.std(ddof=1) / np.sqrt(n) if n > 1 else np.nan
        t = stats.t.ppf(0.975, n - 1) if n > 1 else np.nan
        rows.append({"quintile": int(q), "n_areas": n, "mean": m,
                     "lci": m - t * se, "uci": m + t * se, "median": np.median(x)})
    return pd.DataFrame(rows)


def gap_ratio(summary: pd.DataFrame) -> dict:
    """Absolute and relative gap between most (Q5) and least (Q1) deprived."""
    q1 = summary.loc[summary["quintile"] == summary["quintile"].min(), "mean"].iloc[0]
    q5 = summary.loc[summary["quintile"] == summary["quintile"].max(), "mean"].iloc[0]
    return {"q1_mean": q1, "q5_mean": q5, "abs_gap": q5 - q1,
            "ratio": q5 / q1 if q1 else np.nan}


# ---------------------------------------------------------------------
# 2. Funnel plot control limits
# ---------------------------------------------------------------------
def funnel_limits(target_rate: float, count_grid: np.ndarray,
                  coverage: float) -> tuple[np.ndarray, np.ndarray]:
    """Exact Poisson control limits for a rate, plotted against event count.

    Treats each area's count of deaths as Poisson with mean equal to the
    count expected at the England rate. For age-standardised rates this is
    an approximation (it ignores the extra variance from standardisation);
    state that in the technical explainer.
    """
    a = 1 - coverage
    e = np.asarray(count_grid, float)
    lower = stats.chi2.ppf(a / 2, 2 * e) / 2 / e
    upper = stats.chi2.ppf(1 - a / 2, 2 * (e + 1)) / 2 / e
    return target_rate * lower, target_rate * upper


def funnel_classify(df: pd.DataFrame, rate_col: str, count_col: str,
                    target: float, coverage: float = 0.998) -> pd.Series:
    lo, hi = funnel_limits(target, df[count_col].clip(lower=1).to_numpy(), coverage)
    out = np.where(df[rate_col] > hi, "Above limits",
                   np.where(df[rate_col] < lo, "Below limits", "Within limits"))
    return pd.Series(out, index=df.index)


def overdispersion(rate: np.ndarray, expected: np.ndarray, target: float,
                   winsor: float = 0.1) -> dict:
    """Spiegelhalter (2005) additive random-effects adjustment for funnel plots.

    When many areas sit outside Poisson limits, differences between areas are
    larger than chance alone would produce (overdispersion). We estimate the
    extra between-area variance tau^2 from winsorised z-scores and widen the
    limits by it, so only areas that are unusual *even allowing for real
    variation between areas* are flagged.
    """
    rate = np.asarray(rate, float)
    se = target / np.sqrt(np.asarray(expected, float))
    z = (rate - target) / se
    lo, hi = np.quantile(z, [winsor, 1 - winsor])
    zw = np.clip(z, lo, hi)
    n = len(z)
    phi = float(np.mean(zw ** 2))
    w = 1 / se ** 2
    tau2 = max(0.0, (n * phi - (n - 1)) / (w.sum() - (w ** 2).sum() / w.sum()))
    return {"phi": phi, "tau2": tau2, "tau": float(np.sqrt(tau2)), "n": n}


def adjusted_limits(target: float, expected: np.ndarray, tau2: float,
                    coverage: float) -> tuple[np.ndarray, np.ndarray]:
    zc = stats.norm.ppf(1 - (1 - coverage) / 2)
    sd = np.sqrt(target ** 2 / np.asarray(expected, float) + tau2)
    return target - zc * sd, target + zc * sd


# ---------------------------------------------------------------------
# 3. Slope Index of Inequality (SII) and Relative Index (RII)
# ---------------------------------------------------------------------
def sii(df: pd.DataFrame, value_col: str, dep_col: str, pop_col: str) -> dict:
    """SII: population-weighted regression of the value on each area's
    relative rank in the deprivation distribution (0 = least, 1 = most
    deprived). The slope is the modelled gap between the very most and very
    least deprived ends of England. RII = SII / population-weighted mean.
    """
    d = df.dropna(subset=[value_col, dep_col, pop_col]).sort_values(dep_col)
    w = d[pop_col].to_numpy(float)
    cum = np.cumsum(w) / w.sum()
    rank = cum - (w / w.sum()) / 2          # midpoint of each area's population share
    y = d[value_col].to_numpy(float)
    X = np.column_stack([np.ones_like(rank), rank])
    beta, cov = _wls(X, y, w)
    se = np.sqrt(cov[1, 1])
    tcrit = stats.t.ppf(0.975, len(y) - 2)
    wmean = np.average(y, weights=w)
    return {"sii": beta[1], "sii_lci": beta[1] - tcrit * se,
            "sii_uci": beta[1] + tcrit * se, "rii": beta[1] / wmean,
            "weighted_mean": wmean, "n_areas": len(y)}


def _wls(X: np.ndarray, y: np.ndarray, w: np.ndarray):
    W = np.diag(w / w.mean())
    xtwx_inv = np.linalg.inv(X.T @ W @ X)
    beta = xtwx_inv @ X.T @ W @ y
    resid = y - X @ beta
    sigma2 = (resid @ W @ resid) / (len(y) - X.shape[1])
    return beta, sigma2 * xtwx_inv


# ---------------------------------------------------------------------
# 4. Correlation
# ---------------------------------------------------------------------
def spearman(df: pd.DataFrame, x: str, y: str) -> dict:
    d = df.dropna(subset=[x, y])
    rho, pval = stats.spearmanr(d[x], d[y])
    return {"x": x, "y": y, "rho": rho, "p_value": pval, "n": len(d)}


# ---------------------------------------------------------------------
# 5. Multiple regression with robust (HC3) standard errors
# ---------------------------------------------------------------------
def ols_hc3(df: pd.DataFrame, y: str, xs: list[str]) -> tuple[pd.DataFrame, dict]:
    """OLS of y on standardised predictors (coefficients = change in y per
    1 SD change in x), with HC3 robust SEs and variance inflation factors.

    Ecological model: describes areas, not individuals.
    """
    d = df.dropna(subset=[y] + xs)
    Z = (d[xs] - d[xs].mean()) / d[xs].std(ddof=1)
    X = np.column_stack([np.ones(len(d)), Z.to_numpy(float)])
    yy = d[y].to_numpy(float)
    xtx_inv = np.linalg.inv(X.T @ X)
    beta = xtx_inv @ X.T @ yy
    resid = yy - X @ beta
    h = np.einsum("ij,jk,ik->i", X, xtx_inv, X)
    meat = X.T @ np.diag(resid**2 / (1 - h) ** 2) @ X
    cov = xtx_inv @ meat @ xtx_inv
    se = np.sqrt(np.diag(cov))
    dof = len(yy) - X.shape[1]
    tcrit = stats.t.ppf(0.975, dof)
    pvals = 2 * stats.t.sf(np.abs(beta / se), dof)
    names = ["intercept"] + xs
    table = pd.DataFrame({"term": names, "coef_per_sd": beta, "se_hc3": se,
                          "lci": beta - tcrit * se, "uci": beta + tcrit * se,
                          "p_value": pvals})
    table["vif"] = [np.nan] + [_vif(Z, c) for c in xs]
    r2 = 1 - (resid @ resid) / ((yy - yy.mean()) @ (yy - yy.mean()))
    return table, {"n": len(yy), "r2": r2,
                   "adj_r2": 1 - (1 - r2) * (len(yy) - 1) / dof}


def _vif(Z: pd.DataFrame, col: str) -> float:
    others = [c for c in Z.columns if c != col]
    if not others:
        return 1.0
    X = np.column_stack([np.ones(len(Z)), Z[others].to_numpy(float)])
    y = Z[col].to_numpy(float)
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    r2 = 1 - ((y - X @ beta) ** 2).sum() / ((y - y.mean()) ** 2).sum()
    return 1 / (1 - r2) if r2 < 1 else np.inf


# ---------------------------------------------------------------------
# 6. Prevention priority flags
# ---------------------------------------------------------------------
def priority_flags(df: pd.DataFrame, domains: dict[str, list[tuple[str, bool]]],
                   top_share: float, min_domains: int) -> pd.DataFrame:
    """Flag areas in the worst `top_share` on each domain.

    domains = {"Risk": [(col, higher_is_worse), ...], ...}. Within a domain,
    columns are converted to percentile ranks (worst = 1) and averaged.
    Transparent by design: a rule anyone can re-run and challenge.
    """
    out = df[["area_code", "area_name"]].copy()
    flag_cols = []
    for name, cols in domains.items():
        usable = [(c, hw) for c, hw in cols if c in df and df[c].notna().any()]
        if not usable:
            continue
        ranks = [df[c].rank(pct=True, ascending=hw) for c, hw in usable]
        score = pd.concat(ranks, axis=1).mean(axis=1)
        out[f"{name}_score"] = score
        out[f"{name}_flag"] = score >= (1 - top_share)
        flag_cols.append(f"{name}_flag")
    out["n_domains_flagged"] = out[flag_cols].sum(axis=1)
    out["priority_area"] = out["n_domains_flagged"] >= min_domains
    return out
