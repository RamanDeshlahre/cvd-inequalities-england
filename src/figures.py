"""Charts. One consistent, accessible style for every figure.

Rules followed (and worth saying at interview):
- titles state the finding, subtitles state the measure and period
- every chart has a source line
- colour is never the only way to read a chart (labels / markers too)
- colourblind-safe palette; deprivation runs light -> dark
"""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.stats import funnel_limits

QUINT_COLOURS = ["#c6dbef", "#9ecae1", "#6baed6", "#3182bd", "#08519c"]
ACCENT = "#c8102e"
GREY = "#6b6b6b"
QUINT_LABELS = {1: "1\nLeast\ndeprived", 2: "2", 3: "3", 4: "4", 5: "5\nMost\ndeprived"}

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 10, "axes.spines.top": False,
    "axes.spines.right": False, "axes.titleweight": "bold", "axes.titlesize": 12,
    "figure.dpi": 150, "savefig.bbox": "tight",
})


def _finish(fig, ax, title, subtitle, source, path):
    ax.set_title(f"{title}\n", loc="left")
    ax.text(0, 1.02, subtitle, transform=ax.transAxes, fontsize=9, color=GREY)
    # Place the source line just below everything else, so it never overlaps.
    fig.canvas.draw()
    bb = ax.get_tightbbox(fig.canvas.get_renderer()).transformed(fig.transFigure.inverted())
    fig.text(bb.x0, bb.y0 - 0.015, source, fontsize=7.5, color=GREY, va="top")
    fig.savefig(path)
    plt.close(fig)


def quintile_bars(summary: pd.DataFrame, title: str, subtitle: str, ylabel: str,
                  source: str, path, england: float | None = None,
                  xlabel: str = "Local authority deprivation quintile", decimals: int = 1) -> None:
    fig, ax = plt.subplots(figsize=(7, 4.2))
    x = summary["quintile"].to_numpy()
    y = summary["mean"].to_numpy()
    err = np.vstack([y - summary["lci"], summary["uci"] - y])
    ax.bar(x, y, color=QUINT_COLOURS[: len(x)], edgecolor="white")
    ax.errorbar(x, y, yerr=err, fmt="none", ecolor="#333333", capsize=4, lw=1)
    for xi, yi in zip(x, y):
        ax.text(xi, yi * 0.5, f"{yi:.{decimals}f}", ha="center", va="center",
                fontsize=9, color="white" if xi >= 4 else "#222222", fontweight="bold")
    if england is not None:
        ax.axhline(england, color=ACCENT, ls="--", lw=1.2)
        ax.text(x.max() + 0.45, england, "England", color=ACCENT, va="center", fontsize=8)
    ax.set_xticks(x, [QUINT_LABELS.get(int(i), str(i)) for i in x])
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    _finish(fig, ax, title, subtitle, source, path)


def funnel_plot(df: pd.DataFrame, rate_col: str, exp_col: str, target: float,
                coverages: list[float], title: str, subtitle: str, source: str,
                path, tau2: float = 0.0, label_n: int = 6) -> None:
    """Funnel plot against expected deaths. Grey lines: Poisson limits.
    Red-dashed lines: limits widened for overdispersion (if tau2 > 0)."""
    from src.stats import adjusted_limits
    fig, ax = plt.subplots(figsize=(8, 5))
    d = df.dropna(subset=[rate_col, exp_col])
    grid = np.linspace(max(5, d[exp_col].min() * 0.8), d[exp_col].max() * 1.05, 400)
    for cov in coverages:
        lo, hi = funnel_limits(target, grid, cov)
        ls = "-" if cov > 0.99 else "--"
        ax.plot(grid, lo, color="#9a9a9a", ls=ls, lw=0.9,
                label=f"{cov:.1%} limits (chance only)".replace(".0%", "%"))
        ax.plot(grid, hi, color="#9a9a9a", ls=ls, lw=0.9)
    if tau2 > 0:
        lo, hi = adjusted_limits(target, grid, tau2, max(coverages))
        ax.plot(grid, lo, color=ACCENT, ls=(0, (4, 2)), lw=1.3,
                label=f"{max(coverages):.1%} limits (allowing for real\nvariation between areas)")
        ax.plot(grid, hi, color=ACCENT, ls=(0, (4, 2)), lw=1.3)
    ax.axhline(target, color="#333333", lw=1, label="England")
    q = d["deprivation_quintile"].fillna(3).astype(int)
    for qi in sorted(q.unique()):
        m = q == qi
        ax.scatter(d.loc[m, exp_col], d.loc[m, rate_col], s=24,
                   color=QUINT_COLOURS[qi - 1], edgecolor="#333333", lw=0.4,
                   label=f"Quintile {qi}" + (" (most deprived)" if qi == 5 else
                                             " (least deprived)" if qi == 1 else ""))
    _, hi = (adjusted_limits(target, d[exp_col].to_numpy(), tau2, max(coverages))
             if tau2 > 0 else funnel_limits(target, d[exp_col].to_numpy(), max(coverages)))
    excess = (d[rate_col] - hi).sort_values(ascending=False).head(label_n)
    for idx in excess.index[excess > 0]:
        ax.annotate(d.at[idx, "area_name"], (d.at[idx, exp_col], d.at[idx, rate_col]),
                    fontsize=7, xytext=(4, 2), textcoords="offset points")
    ax.set_xlabel("Expected deaths under 75 at the England rate (size of area)")
    ax.set_ylabel("Deaths per 100,000 (age-standardised)")
    ax.legend(fontsize=7.5, frameon=False, loc="upper left", bbox_to_anchor=(1.01, 1))
    _finish(fig, ax, title, subtitle, source, path)


def scatter_quintile(df: pd.DataFrame, x: str, y: str, xlabel: str, ylabel: str,
                     title: str, subtitle: str, source: str, path) -> None:
    fig, ax = plt.subplots(figsize=(7, 4.6))
    d = df.dropna(subset=[x, y])
    q = d["deprivation_quintile"].fillna(3).astype(int)
    markers = ["o", "s", "^", "D", "v"]
    for qi in sorted(q.unique()):
        m = q == qi
        ax.scatter(d.loc[m, x], d.loc[m, y], s=24, color=QUINT_COLOURS[qi - 1],
                   marker=markers[qi - 1], edgecolor="#333333", lw=0.4,
                   label=f"Q{qi}")
    b = np.polyfit(d[x], d[y], 1)
    xs = np.linspace(d[x].min(), d[x].max(), 50)
    ax.plot(xs, np.polyval(b, xs), color=ACCENT, lw=1.3)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.legend(title="Deprivation quintile", fontsize=7.5, title_fontsize=8, frameon=False)
    _finish(fig, ax, title, subtitle, source, path)


def trend_gap(trend: pd.DataFrame, title: str, subtitle: str, source: str, path) -> None:
    fig, ax = plt.subplots(figsize=(7.5, 4.4))
    for q, colour, lab in [(1, QUINT_COLOURS[2], "Least deprived fifth of areas"),
                           (5, QUINT_COLOURS[4], "Most deprived fifth of areas")]:
        t = trend[trend["quintile"] == q]
        ax.plot(t["year"], t["mean"], color=colour, lw=2.2, marker="o", ms=4)
        ax.fill_between(t["year"], t["lci"], t["uci"], color=colour, alpha=0.2)
        ax.text(t["year"].iloc[-1] + 0.2, t["mean"].iloc[-1], lab, color=colour,
                va="center", fontsize=8, fontweight="bold")
    ax.set_xlabel("Year")
    ax.set_ylabel("Deaths per 100,000 (age-standardised)")
    yrs = sorted(trend["year"].unique())
    ax.set_xticks(yrs[::2] if len(yrs) > 8 else yrs)
    ax.set_xlim(yrs[0] - 0.3, yrs[-1] + 4)
    _finish(fig, ax, title, subtitle, source, path)


def care_chart(care: pd.DataFrame, title: str, subtitle: str, source: str, path) -> None:
    inds = care["indicator"].unique().tolist()
    fig, ax = plt.subplots(figsize=(7.5, 0.9 + 0.75 * len(inds) * 1.4))
    yb = np.arange(len(inds)) * 1.4
    for qi in sorted(care["quintile"].unique()):
        sub = care[care["quintile"] == qi].set_index("indicator").reindex(inds)
        yy = yb + (qi - 3) * 0.2
        ax.errorbar(sub["value"], yy,
                    xerr=[sub["value"] - sub["lower_ci"], sub["upper_ci"] - sub["value"]],
                    fmt="o", color=QUINT_COLOURS[int(qi) - 1], mec="#333333", mew=0.4,
                    ms=6, capsize=2, label=f"Q{int(qi)}")
    ax.set_yticks(yb, [i if len(i) < 45 else i[:42] + "..." for i in inds])
    ax.invert_yaxis()
    ax.set_xlabel("%")
    ax.legend(title="Deprivation quintile\n(5 = most deprived)", fontsize=7.5,
              title_fontsize=7.5, frameon=False, bbox_to_anchor=(1.01, 1), loc="upper left")
    _finish(fig, ax, title, subtitle, source, path)
