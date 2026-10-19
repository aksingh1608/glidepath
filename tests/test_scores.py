import numpy as np

from pipeline.diagnostics import interval_score, pinball


def test_interval_score_inside_is_width():
    # Truth inside the interval: score is the width only (seconds to minutes).
    assert np.allclose(interval_score([0], [120], [60], alpha=0.2), [2.0])


def test_interval_score_penalises_miss():
    # Truth 60 s above the upper end adds 2 / alpha * 60 s.
    assert np.allclose(interval_score([0], [120], [180], alpha=0.2), [(120 + 10 * 60) / 60])


def test_pinball_zero_when_exact():
    y = np.array([300.0, 600.0])
    assert np.allclose(pinball({0.1: y, 0.5: y, 0.9: y}, y), 0)


def test_pinball_asymmetric():
    # Predicting 60 s too low costs q * 60, too high costs (1 - q) * 60.
    assert np.isclose(pinball({0.9: np.array([0.0])}, np.array([60.0]))[0], 0.9)
    assert np.isclose(pinball({0.9: np.array([120.0])}, np.array([60.0]))[0], 0.1)
