import numpy as np
import pandas as pd

from pipeline.splits import assign_splits


def _check(split, ids):
    assert set(split) <= set(ids)
    assert set(split.values()) <= {"train", "calibration", "test"}
    # a dict maps each flight to exactly one split
    assert len(split) == len(set(split))


def test_time_block_split(synthetic_arrivals):
    arrivals, _, _ = synthetic_arrivals
    split, info = assign_splits(arrivals)
    _check(split, arrivals["flight_id"])
    assert info["scheme"] == "time_block"
    td = arrivals.set_index("flight_id")["touchdown"]
    by = {s: td[[f for f, v in split.items() if v == s]] for s in ("train", "calibration", "test")}
    assert by["train"].max() <= by["calibration"].min()
    assert by["calibration"].max() <= by["test"].min()


def test_day_split():
    base = pd.Timestamp("2026-10-10 12:00", tz="Europe/Berlin").timestamp()
    rows = [{"flight_id": f"f{d}_{i}", "touchdown": base + d * 86400 + i * 60}
            for d in range(4) for i in range(160)]
    a = pd.DataFrame(rows)
    split, info = assign_splits(a)
    _check(split, a["flight_id"])
    assert info["scheme"] == "by_day"
    assert {v for f, v in split.items() if f.startswith("f3_")} == {"test"}
    assert {v for f, v in split.items() if f.startswith("f2_")} == {"calibration"}
    assert {v for f, v in split.items() if f.startswith("f0_")} == {"train"}
