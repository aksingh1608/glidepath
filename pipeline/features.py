"""Features. Every feature at time t uses only data at or before t.

Inbound status of other flights is taken as known, like a flight plan; their
positions are used only up to the end of the last complete 30 s bucket.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import config as C
from .data import angle_diff


def _lag_delta(t: np.ndarray, x: np.ndarray, lag: float) -> np.ndarray:
    target = t - lag
    j = np.searchsorted(t, target, side="right") - 1
    valid = (j >= 0) & (target - t[np.clip(j, 0, None)] <= C.LAG_TOL_S)
    out = np.full(t.shape, np.nan)
    out[valid] = x[valid] - x[j[valid]]
    return out


def _turn_5min(t: np.ndarray, track: np.ndarray) -> np.ndarray:
    step = np.zeros(t.shape)
    if t.size > 1:
        d = angle_diff(track[1:], track[:-1])
        ok = (np.diff(t) <= C.TURN_STEP_MAX_S) & ~np.isnan(d)
        step[1:] = np.where(ok, d, 0.0)
    cum = np.cumsum(step)
    k0 = np.searchsorted(t, t - C.TURN_WINDOW_S, side="right")
    before = np.where(k0 > 0, cum[np.clip(k0 - 1, 0, None)], 0.0)
    return cum - before


def flight_features(g: pd.DataFrame) -> pd.DataFrame:
    """Features that need only this flight's own past points. g sorted by t."""
    t = g["t"].to_numpy(dtype=float)
    out = pd.DataFrame(index=g.index)
    for lag in C.LAGS_S:
        out[f"d_alt_{lag}"] = _lag_delta(t, g["alt_m"].to_numpy(dtype=float), lag)
        out[f"d_gs_{lag}"] = _lag_delta(t, g["gs_kt"].to_numpy(dtype=float), lag)
    out["turn_5min_deg"] = _turn_5min(t, g["true_track_deg"].to_numpy(dtype=float))
    return out


def direction_codes(arrivals: pd.DataFrame, t: np.ndarray) -> np.ndarray:
    """Majority direction of the last 3 landings at or before t (1 = 25, 0 = 07, -1 none)."""
    known = arrivals[arrivals["direction"].isin(C.DIRECTION_CODES)].sort_values("touchdown")
    td = known["touchdown"].to_numpy(dtype=float)
    codes = known["direction"].map(C.DIRECTION_CODES).to_numpy()
    code_at = np.full(len(td) + 1, -1)
    for n in range(1, len(td) + 1):
        last = codes[max(0, n - C.DIRECTION_LAST_N):n]
        ones = int((last == 1).sum())
        zeros = len(last) - ones
        code_at[n] = 1 if ones > zeros else 0 if zeros > ones else last[-1]
    return code_at[np.searchsorted(td, t, side="right")]


def traffic_features(points: pd.DataFrame, t: np.ndarray, own_dist: np.ndarray,
                     own_flight: np.ndarray) -> pd.DataFrame:
    """Inbound arrivals within each radius in the last complete 30 s bucket,
    this flight's distance rank among them (1 = closest)."""
    b = (points["t"] // C.TRAFFIC_BUCKET_S).astype(np.int64)
    last = (points.assign(bucket=b).sort_values("t")
            .groupby(["bucket", "flight_id"], sort=False)["distance_nm"].last().reset_index())
    sorted_d = {k: np.sort(v.to_numpy()) for k, v in last.groupby("bucket")["distance_nm"]}
    own_prev = last.set_index(["bucket", "flight_id"])["distance_nm"]
    prev_bucket = (t // C.TRAFFIC_BUCKET_S).astype(np.int64) - 1
    res = {f"traffic_{r}": np.zeros(t.shape) for r in C.TRAFFIC_RADII_NM}
    rank = np.ones(t.shape)
    empty = np.array([])
    for i, (pb, d, fid) in enumerate(zip(prev_bucket, own_dist, own_flight)):
        arr = sorted_d.get(pb, empty)
        for r in C.TRAFFIC_RADII_NM:
            res[f"traffic_{r}"][i] = np.searchsorted(arr, r, side="right")
        closer = np.searchsorted(arr, d, side="left")
        mine = own_prev.get((pb, fid))
        if mine is not None and mine < d:
            closer -= 1
        rank[i] = closer + 1
    out = pd.DataFrame(res)
    out["distance_rank"] = rank
    return out


def build_features(points: pd.DataFrame, arrivals: pd.DataFrame) -> pd.DataFrame:
    """Feature table, one row per airborne point of an arrival before touchdown."""
    p = points.sort_values(["flight_id", "t"]).reset_index(drop=True)
    own = pd.concat([flight_features(g) for _, g in p.groupby("flight_id", sort=False)])
    p = p.join(own)
    t = p["t"].to_numpy(dtype=float)

    rad = np.radians(p["bearing_deg"].to_numpy(dtype=float))
    p["bearing_sin"] = np.sin(rad)
    p["bearing_cos"] = np.cos(rad)
    course_to_airport = (p["bearing_deg"] + 180) % 360
    p["course_offset_deg"] = angle_diff(p["true_track_deg"], course_to_airport)
    p["speed_toward_kt"] = p["gs_kt"] * np.cos(np.radians(p["course_offset_deg"]))
    p["holding"] = (p["turn_5min_deg"] > C.HOLDING_TURN_DEG).astype(int)

    p["direction_code"] = direction_codes(arrivals, t)
    tr = traffic_features(points, t, p["distance_nm"].to_numpy(), p["flight_id"].to_numpy())
    p = pd.concat([p, tr], axis=1)
    td = np.sort(arrivals["touchdown"].to_numpy(dtype=float))
    p["landings_30min"] = (np.searchsorted(td, t, side="right")
                           - np.searchsorted(td, t - C.LANDINGS_WINDOW_S, side="right"))
    p["local_hour"] = (pd.to_datetime(p["t"], unit="s", utc=True)
                       .dt.tz_convert(C.LOCAL_TZ).dt.hour)
    cat = arrivals.set_index("flight_id")["category"]
    p["category"] = p["flight_id"].map(cat).fillna(-1).astype(float)
    p["band"] = pd.cut(p["distance_nm"], bins=list(C.BAND_EDGES_NM), right=False,
                       labels=False).astype(int)
    return p
