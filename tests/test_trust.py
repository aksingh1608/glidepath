import numpy as np

from pipeline.trust import trust_index, trust_lead

Y = np.array([600.0, 500, 400, 300, 200, 100])  # seconds to touchdown


def test_always_ok():
    lead, never = trust_lead(Y - 30, Y + 30, Y, 5)
    assert not never and lead == Y[0] / 60


def test_never_ok():
    lead, never = trust_lead(Y + 10, Y + 20, Y, 5)  # truth always below the interval
    assert never and lead == 0.0


def test_ok_only_at_end():
    lo, hi = Y - 30, Y + 30
    lo[:4] = Y[:4] + 1  # first four rows miss
    assert trust_index(lo, hi, Y, 5) == 4
    lead, never = trust_lead(lo, hi, Y, 5)
    assert not never and lead == Y[4] / 60


def test_last_row_miss_means_never_trusted():
    lo, hi = Y - 30, Y + 30
    lo[-1] = Y[-1] + 1
    assert trust_lead(lo, hi, Y, 5)[1]


def test_width_equal_to_window_is_ok():
    lo, hi = Y - 150, Y + 150  # width exactly 5 minutes
    assert trust_index(lo, hi, Y, 5) == 0
    assert trust_index(lo, hi + 1, Y, 5) is None
