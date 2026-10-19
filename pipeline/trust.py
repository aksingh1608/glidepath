"""Trust point and trust lead.

Per flight, sorted by t: ok = (width <= W x 60) and (lo <= y <= hi). The trust
point is the row after the last row that is not ok. If no row remains, the
flight is never trusted and its lead is 0. Lead = y at the trust point / 60.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def trust_index(lo, hi, y, window_min: float):
    """Index of the trust point in time-sorted arrays, or None if never trusted."""
    lo, hi, y = map(np.asarray, (lo, hi, y))
    ok = ((hi - lo) <= window_min * 60) & (lo <= y) & (y <= hi)
    bad = np.flatnonzero(~ok)
    k = 0 if bad.size == 0 else bad[-1] + 1
    return None if k >= len(y) else int(k)


def trust_lead(lo, hi, y, window_min: float) -> tuple[float, bool]:
    k = trust_index(lo, hi, y, window_min)
    if k is None:
        return 0.0, True
    return float(np.asarray(y)[k]) / 60.0, False


def trust_table(df: pd.DataFrame, lo_col: str, hi_col: str, windows) -> pd.DataFrame:
    """One row per flight and window: lead_min, never_trusted, trust_t."""
    rows = []
    for fid, g in df.sort_values(["flight_id", "t"]).groupby("flight_id", sort=False):
        lo, hi, y, t = (g[lo_col].to_numpy(), g[hi_col].to_numpy(), g["y"].to_numpy(),
                        g["t"].to_numpy())
        for w in windows:
            k = trust_index(lo, hi, y, w)
            rows.append({"flight_id": fid, "window_min": w,
                         "lead_min": 0.0 if k is None else y[k] / 60.0,
                         "never_trusted": k is None,
                         "trust_t": np.nan if k is None else float(t[k])})
    return pd.DataFrame(rows)
