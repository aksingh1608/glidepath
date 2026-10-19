import numpy as np
import pandas as pd

from pipeline import config as C
from pipeline.features import build_features


def test_features_do_not_change_when_later_rows_are_deleted(synthetic_arrivals):
    arrivals, points, _ = synthetic_arrivals
    full = build_features(points, arrivals)
    t0 = float(np.median(points["t"]))
    cut = build_features(points[points["t"] <= t0], arrivals)
    key = ["flight_id", "t"]
    a = full[full["t"] <= t0].set_index(key).sort_index()[C.FEATURES]
    b = cut.set_index(key).sort_index()[C.FEATURES]
    assert len(a) == len(b) and len(a) > 1000
    pd.testing.assert_frame_equal(a, b, check_dtype=False)


def test_synthetic_has_arrivals_and_ignores_others(synthetic_arrivals):
    arrivals, _, stats = synthetic_arrivals
    assert stats["arrivals_kept"] > 100
    assert stats["drop_reasons"].get("not_arrival_no_touchdown", 0) > 50
    assert set(arrivals["direction"]) <= {"25", "07", "unk"}
    assert (arrivals["direction"] == "07").any() and (arrivals["direction"] == "25").any()
