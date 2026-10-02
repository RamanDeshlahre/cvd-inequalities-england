"""Split one combined Fingertips CSV (several indicator IDs) into the
per-indicator raw files the pipeline expects, and write a manifest.

    python -m src.split_download path/to/indicator-data.csv
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from src.utils import active_indicators, get_logger, load_config, paths

log = get_logger("split")


def main(src: str) -> None:
    cfg = load_config()
    p = paths()
    df = pd.read_csv(src, low_memory=False)
    manifest = {"source_file": Path(src).name,
                "split_utc": datetime.now(timezone.utc).isoformat(),
                "rows_total": len(df), "indicators": {}}
    for key, spec in active_indicators(cfg).items():
        sub = df[df["Indicator ID"] == spec["id"]]
        if sub.empty:
            log.warning("Indicator %s (%s) not in file.", spec["id"], key)
            continue
        sub.to_csv(p["raw"] / f"{key}.csv", index=False)
        manifest["indicators"][key] = {
            "id": spec["id"], "fingertips_name": sub["Indicator Name"].iloc[0],
            "rows": len(sub), "file": f"{key}.csv",
        }
        log.info("%-26s id %-6s %6s rows  %s", key, spec["id"], len(sub),
                 sub["Indicator Name"].iloc[0])
    with open(p["raw"] / "manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)


if __name__ == "__main__":
    main(sys.argv[1])
