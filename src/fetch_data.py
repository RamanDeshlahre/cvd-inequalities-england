"""STEP 1 - Download raw indicator data from the Fingertips API.

Usage
-----
    python -m src.fetch_data --list-area-types   # check the area type ID
    python -m src.fetch_data --check-ids         # print indicator names only
    python -m src.fetch_data                     # download everything

Raw files are saved untouched to data/raw/<indicator_key>.csv, and a
manifest.json records what was downloaded and when (data provenance).

If the API is unavailable, download each indicator manually from the
Fingertips website ("Download" tab, data for upper-tier local authorities)
and save it as data/raw/<indicator_key>.csv - the rest of the pipeline
reads the same Fingertips CSV format either way.
"""
from __future__ import annotations

import argparse
import io
import json
import time
from datetime import datetime, timezone

import pandas as pd
import requests

from src.utils import active_indicators, get_logger, load_config, paths

log = get_logger("fetch")


def _get(url: str, params: dict | None = None, retries: int = 3) -> requests.Response:
    for attempt in range(1, retries + 1):
        try:
            r = requests.get(url, params=params, timeout=180)
            r.raise_for_status()
            return r
        except requests.RequestException as exc:
            if attempt == retries:
                raise
            wait = 5 * attempt
            log.warning("Request failed (%s). Retrying in %ss...", exc, wait)
            time.sleep(wait)
    raise RuntimeError("unreachable")


def list_area_types(base: str) -> None:
    data = _get(f"{base}/area_types").json()
    df = pd.DataFrame(data)
    cols = [c for c in ["Id", "Name", "Short"] if c in df.columns]
    print(df[cols].sort_values("Id").to_string(index=False))


def fetch_indicator(base: str, indicator_id: int, area_type_id: int,
                    parent_area_type_id: int) -> pd.DataFrame:
    r = _get(
        f"{base}/all_data/csv/by_indicator_id",
        params={
            "indicator_ids": indicator_id,
            "child_area_type_id": area_type_id,
            "parent_area_type_id": parent_area_type_id,
        },
    )
    return pd.read_csv(io.StringIO(r.text), low_memory=False)


def main(argv: list[str] | None = None) -> dict:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--list-area-types", action="store_true")
    ap.add_argument("--check-ids", action="store_true",
                    help="download, print indicator names, but do not save")
    args = ap.parse_args(argv)

    cfg = load_config()
    ft = cfg["fingertips"]
    if args.list_area_types:
        list_area_types(ft["base_url"])
        return

    p = paths()
    manifest = {"downloaded_utc": datetime.now(timezone.utc).isoformat(),
                "area_type_id": ft["area_type_id"], "indicators": {}}

    missing = [k for k, v in cfg["indicators"].items() if v.get("id") is None]
    for key in missing:
        log.warning("'%s' has no id in config.yaml - skipped.", key)

    targets = dict(active_indicators(cfg))
    targets.update({k: {"id": v} for k, v in cfg.get("sensitivity_indicators", {}).items()})
    for key, spec in targets.items():
        log.info("Fetching %s (id %s)...", key, spec["id"])
        df = fetch_indicator(ft["base_url"], spec["id"], ft["area_type_id"],
                             ft["parent_area_type_id"])
        if df.empty:
            log.error("No rows returned for %s - check id and area type.", key)
            continue
        names = df["Indicator Name"].dropna().unique().tolist()
        log.info("  -> %s rows | Fingertips name: %s", len(df), names)
        if args.check_ids:
            continue
        out = p["raw"] / f"{key}.csv"
        df.to_csv(out, index=False)
        manifest["indicators"][key] = {
            "id": spec["id"], "fingertips_name": names, "rows": len(df),
            "periods": sorted(df["Time period"].dropna().astype(str).unique().tolist()),
            "file": out.name,
        }

    if not args.check_ids:
        with open(p["raw"] / "manifest.json", "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)
        log.info("Saved raw files and manifest.json to %s", p["raw"])
    return manifest


if __name__ == "__main__":
    main()
