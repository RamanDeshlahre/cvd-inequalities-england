"""Shared helpers: project paths, config loading and logging."""
from __future__ import annotations

import logging
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config.yaml"


def load_config(path: Path = CONFIG_PATH) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def paths(raw_dir: str | None = None, out_dir: str | None = None) -> dict[str, Path]:
    """Return project folders. raw_dir/out_dir let the synthetic test run
    in separate folders so test data never mixes with real data."""
    raw = Path(raw_dir) if raw_dir else ROOT / "data" / "raw"
    out = Path(out_dir) if out_dir else ROOT / "outputs"
    processed = (out / "processed") if out_dir else ROOT / "data" / "processed"
    p = {
        "raw": raw,
        "processed": processed,
        "out": out,
        "figures": out / "figures",
        "tables": out / "tables",
    }
    for folder in p.values():
        folder.mkdir(parents=True, exist_ok=True)
    return p


def get_logger(name: str) -> logging.Logger:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-7s  %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    return logging.getLogger(name)


def indicators_by_role(cfg: dict, role: str) -> list[str]:
    return [k for k, v in cfg["indicators"].items() if v["role"] == role]


def active_indicators(cfg: dict) -> dict:
    """Indicators that have an ID filled in."""
    return {k: v for k, v in cfg["indicators"].items() if v.get("id") is not None}
