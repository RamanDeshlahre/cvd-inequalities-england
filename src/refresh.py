"""Automated refresh: one command that rebuilds every output, detects what
changed in the source data, and stops if quality checks fail.

    python -m src.refresh            # rebuild from the raw files already in data/raw
    python -m src.refresh --fetch    # download the latest Fingertips data first

Designed to run on a schedule (see .github/workflows/refresh.yml). The source
data are published monthly to quarterly, so a monthly scheduled refresh keeps
the project current; true real-time streaming would add complexity for no gain.

Writes
    outputs/run_log.json     what ran, when, data fingerprints, latest periods, QA result
    outputs/data_changes.md  plain-English summary of what is new since the last run
Exit code 1 if any QA check FAILS, so a scheduled run never publishes bad outputs.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone

import pandas as pd

from src import deep_dive, export_tableau, run_pipeline, sensitivity
from src.utils import get_logger, load_config, paths

log = get_logger("refresh")


def _fingerprints(raw_dir) -> dict:
    out = {}
    for f in sorted(raw_dir.rglob("*")):
        if f.is_file() and f.suffix in {".csv", ".xlsx"}:
            out[str(f.relative_to(raw_dir))] = hashlib.sha256(f.read_bytes()).hexdigest()[:16]
    return out


def _latest_periods(p) -> dict:
    e = pd.read_csv(p["processed"] / "long_all_years.csv", low_memory=False)
    per = (e.sort_values("period_sortable").groupby("indicator_key")["period"].last()
           .astype(str).to_dict())
    cfg = load_config()
    care = p["raw"] / cfg["cvdprevent"]["file"]
    if care.exists():
        per["cvdprevent"] = str(pd.read_csv(care)["period"].iloc[0])
    return per


def _cvdprevent_age_months(period: str) -> int | None:
    m = re.search(r"([A-Za-z]+)\s+(\d{4})", period or "")
    if not m:
        return None
    d = datetime.strptime(f"1 {m.group(1)} {m.group(2)}", "%d %B %Y")
    now = datetime.now()
    return (now.year - d.year) * 12 + now.month - d.month


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fetch", action="store_true", help="download latest Fingertips data first")
    args = ap.parse_args(argv)
    cfg = load_config()
    p = paths()
    log_path = p["out"] / "run_log.json"
    previous = json.loads(log_path.read_text()) if log_path.exists() else {}

    started = datetime.now(timezone.utc)
    if args.fetch:
        from src import fetch_data
        fetch_data.main([])

    qa = run_pipeline.main([])
    sensitivity.main()
    deep_dive.main()
    export_tableau.main()

    n_fail = sum(r[0] == "FAIL" for r in qa)
    n_warn = sum(r[0] == "WARN" for r in qa)
    fps, periods = _fingerprints(p["raw"]), _latest_periods(p)
    run = {"started_utc": started.isoformat(), "finished_utc": datetime.now(timezone.utc).isoformat(),
           "fetched": args.fetch, "qa_fail": n_fail, "qa_warn": n_warn,
           "latest_periods": periods, "fingerprints": fps}

    # ---- what changed since the last run ----------------------------------------
    L = ["# Data changes since last run", "",
         f"Run: {run['finished_utc'][:16].replace('T', ' ')} UTC | QA: {n_fail} FAIL, {n_warn} WARN", ""]
    old_p, old_f = previous.get("latest_periods", {}), previous.get("fingerprints", {})
    if not previous:
        L.append("- First recorded run: no previous run to compare with.")
    else:
        new_periods = [f"- **{k}**: new latest period {v} (was {old_p.get(k, 'none')})"
                       for k, v in periods.items() if old_p.get(k) != v]
        changed = [k for k, v in fps.items() if old_f.get(k) != v]
        L += new_periods or ["- No new periods in any indicator."]
        L.append(f"- Raw files changed: {', '.join(changed) if changed else 'none'}")
        if changed and not new_periods:
            L.append("  (Values were revised without a new period - check the QA report and tables.)")
    age = _cvdprevent_age_months(periods.get("cvdprevent", ""))
    if age is not None and age > cfg["cvdprevent"].get("max_age_months", 6):
        L.append(f"- **Action:** CVDPREVENT data are {age} months old. Download new exports "
                 "into data/raw/cvdprevent/ and run `python -m src.load_cvdprevent`.")
    if n_fail:
        L.append("- **QA FAILED - outputs must not be published until fixed.** See outputs/qa_report.md.")
    (p["out"] / "data_changes.md").write_text("\n".join(L), encoding="utf-8")
    log_path.write_text(json.dumps(run, indent=2), encoding="utf-8")
    log.info("Refresh complete: %s FAIL, %s WARN.", n_fail, n_warn)
    return 1 if n_fail else 0


if __name__ == "__main__":
    sys.exit(main())
