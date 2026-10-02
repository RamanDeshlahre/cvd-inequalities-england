"""End-to-end test: the full pipeline runs on synthetic data with built-in effects,
QA raises no FAIL, and the analysis finds the deprivation gradient we planted."""
import pandas as pd

from src import make_synthetic, run_pipeline
from src.utils import ROOT


def test_pipeline_runs_on_synthetic_data(tmp_path=None):
    out = (tmp_path or ROOT / "outputs_test")
    make_synthetic.main()
    qa = run_pipeline.main(["--raw-dir", str(ROOT / "data" / "raw_synthetic"), "--out-dir", str(out)])
    assert not any(r[0] == "FAIL" for r in qa)
    q = pd.read_csv(out / "tables" / "outcome_by_quintile.csv")
    assert q.loc[q["quintile"] == 5, "mean"].item() > q.loc[q["quintile"] == 1, "mean"].item()
    for f in ["01_mortality_by_quintile.png", "02_mortality_funnel.png", "03_mortality_trend_gap.png"]:
        assert (out / "figures" / f).exists()
