import numpy as np

from pipeline.models import CQR, cqr_q


def test_cqr_coverage_near_80_percent():
    rng = np.random.default_rng(0)
    n = 20000
    x = rng.uniform(0, 1, n)
    y = rng.normal(0, 1 + 3 * x)
    band = (x * 4).astype(int)
    lo, hi = -0.5 * np.ones(n), 0.5 * np.ones(n)  # far too narrow on purpose
    cal = np.arange(n) < n // 2
    m = CQR(per_band=True).fit(lo[cal], hi[cal], y[cal], band[cal])
    l2, h2 = m.apply(lo[~cal], hi[~cal], band[~cal])
    cov = np.mean((l2 <= y[~cal]) & (y[~cal] <= h2))
    raw = np.mean((lo[~cal] <= y[~cal]) & (y[~cal] <= hi[~cal]))
    assert raw < 0.5
    assert abs(cov - 0.8) < 0.02
    for b in range(4):
        sel = band[~cal] == b
        assert abs(np.mean((l2[sel] <= y[~cal][sel]) & (y[~cal][sel] <= h2[sel])) - 0.8) < 0.03


def test_cqr_quantile_level():
    s = np.arange(1.0, 21.0)  # n = 20, level ceil(21 * 0.8) / 20 = 0.85
    assert cqr_q(s) == np.quantile(s, 0.85, method="higher")
