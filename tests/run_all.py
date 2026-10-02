"""Run all tests without pytest:  python -m tests.run_all"""
import inspect
import sys
import traceback

from tests import test_pipeline, test_stats

failed = 0
for mod in (test_stats, test_pipeline):
    for name, fn in inspect.getmembers(mod, inspect.isfunction):
        if name.startswith("test_"):
            try:
                fn()
                print(f"PASS  {mod.__name__}.{name}")
            except Exception:
                failed += 1
                print(f"FAIL  {mod.__name__}.{name}")
                traceback.print_exc()
print(f"\n{failed} failed")
sys.exit(1 if failed else 0)
