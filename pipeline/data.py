"""Load collector CSVs, split tracks into flights, label touchdown, build rows."""

from __future__ import annotations

import glob
import os
from collections import Counter

import numpy as np
import pandas as pd

from . import config as C


def haversine_nm(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(np.radians, (lat1, lon1, lat2, lon2))
    a = (np.sin((lat2 - lat1) / 2) ** 2
         + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2)
    return 2 * C.EARTH_RADIUS_NM * np.arcsin(np.sqrt(np.clip(a, 0, 1)))


def bearing_deg(lat1, lon1, lat2, lon2):
    """Initial bearing from point 1 to point 2, degrees clockwise from north."""
    lat1, lon1, lat2, lon2 = map(np.radians, (lat1, lon1, lat2, lon2))
    x = np.sin(lon2 - lon1) * np.cos(lat2)
    y = np.cos(lat1) * np.sin(lat2) - np.sin(lat1) * np.cos(lat2) * np.cos(lon2 - lon1)
    return (np.degrees(np.arctan2(x, y)) + 360) % 360


def angle_diff(a, b):
    """Absolute smallest difference between two headings, degrees."""
    return np.abs((np.asarray(a) - np.asarray(b) + 180) % 360 - 180)


def _to_bool(s: pd.Series) -> pd.Series:
    if s.dtype == bool:
        return s
    return s.astype(str).str.strip().str.lower().isin(["true", "1"])


def load_raw(raw: str) -> pd.DataFrame:
    files = sorted(glob.glob(os.path.join(raw, "states_*.csv")))
    if not files:
        raise FileNotFoundError(f"no states_*.csv files in {raw}")
    df = pd.concat((pd.read_csv(f, dtype={"icao24": str, "callsign": str, "squawk": str})
                    for f in files), ignore_index=True)
    df["n_files"] = len(files)
    return df


def clean(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["t"] = pd.to_numeric(df["time_position"], errors="coerce")
    df = df.dropna(subset=["t", "lat", "lon"])
    df["t"] = df["t"].astype(np.int64)
    df = df.drop_duplicates(subset=["icao24", "t"], keep="last")
    df["on_ground"] = _to_bool(df["on_ground"])
    for col in ("baro_alt_m", "geo_alt_m", "velocity_ms", "true_track_deg",
                "vertical_rate_ms", "category"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["alt_m"] = df["baro_alt_m"].fillna(df["geo_alt_m"])
    df["gs_kt"] = df["velocity_ms"] * C.MS_TO_KT
    df["vrate_ms"] = df["vertical_rate_ms"]
    df["distance_nm"] = haversine_nm(C.REF_LAT, C.REF_LON, df["lat"], df["lon"])
    df["bearing_deg"] = bearing_deg(C.REF_LAT, C.REF_LON, df["lat"], df["lon"])
    df["callsign"] = df["callsign"].fillna("").astype(str).str.strip()
    return df.sort_values(["icao24", "t"]).reset_index(drop=True)


def split_flights(df: pd.DataFrame) -> pd.DataFrame:
    new = (df["icao24"] != df["icao24"].shift()) | (df["t"].diff() > C.FLIGHT_GAP_S)
    seg = new.cumsum()
    first_t = df.groupby(seg)["t"].transform("first")
    df = df.assign(flight_id=df["icao24"] + "_" + first_t.astype(str))
    return df


def _extrapolate(row) -> float:
    vr = row["vrate_ms"]
    rate = -vr if pd.notna(vr) and vr < C.DESCENT_THRESHOLD_MS else C.DEFAULT_DESCENT_MS
    alt = row["alt_m"]
    if pd.isna(alt):
        return 0.0
    return max(0.0, (alt - C.FIELD_ELEV_M) / rate)


def label_flight(g: pd.DataFrame):
    """Return (touchdown_t, method) or (None, drop_reason). g is sorted by t."""
    air = ~g["on_ground"].to_numpy()
    dist = g["distance_nm"].to_numpy()
    t = g["t"].to_numpy()
    far = np.flatnonzero(air & (dist >= C.ARRIVAL_START_NM))
    if far.size == 0:
        return None, "not_arrival_never_airborne_beyond_30nm"
    i30 = far[0]
    ground = np.flatnonzero((~air) & (dist <= C.GROUND_NM) & (np.arange(len(g)) > i30))
    if ground.size:
        gi = ground[0]
        prev_air = np.flatnonzero(air[:gi])
        prev_air = prev_air[prev_air >= i30]
        if prev_air.size == 0:
            return None, "no_airborne_point_before_ground"
        ai = prev_air[-1]
        gap = float(t[gi] - t[ai])
        if gap <= C.MIDPOINT_MAX_GAP_S:
            return t[ai] + gap / 2, "ground_midpoint"
        dt = min(_extrapolate(g.iloc[ai]), gap, C.EXTRAP_CAP_S)
        return t[ai] + dt, "ground_extrapolated"
    alt = g["alt_m"].to_numpy()
    cand = np.flatnonzero(air & (dist <= C.GROUND_NM) & (alt < C.FALLBACK_MAX_ALT_M)
                          & (np.arange(len(g)) > i30))
    if cand.size == 0:
        return None, "not_arrival_no_touchdown"
    ci = cand[-1]
    if (dist[ci + 1:] > C.FALLBACK_REJECT_NM).any():
        return None, "fallback_rejected_flew_away"
    dt = min(_extrapolate(g.iloc[ci]), C.EXTRAP_CAP_S)
    return t[ci] + dt, "fallback_extrapolated"


def circular_mean_deg(deg: np.ndarray) -> float:
    r = np.radians(deg[~np.isnan(deg)])
    if r.size == 0:
        return np.nan
    return float((np.degrees(np.arctan2(np.sin(r).mean(), np.cos(r).mean())) + 360) % 360)


def landing_direction(before: pd.DataFrame) -> str:
    near = before[before["distance_nm"] <= C.DIRECTION_NM]
    mean = circular_mean_deg(near["true_track_deg"].to_numpy(dtype=float))
    if np.isnan(mean):
        return "unk"
    for name, hdg in C.RUNWAY_HEADINGS.items():
        if angle_diff(mean, hdg) <= C.DIRECTION_TOL_DEG:
            return name
    return "unk"


def go_around(before: pd.DataFrame) -> bool:
    inner = before[before["distance_nm"] <= C.GO_AROUND_NM]["alt_m"].dropna()
    if inner.empty:
        return False
    return bool((inner - inner.cummin() > C.GO_AROUND_CLIMB_M).any())


def build_arrivals(df: pd.DataFrame):
    """Label arrivals. Returns (arrivals, points, stats).

    arrivals: one row per kept arrival (flight_id, icao24, callsign, touchdown,
              label_method, direction, go_around, category)
    points:   all cleaned airborne points of kept arrivals before touchdown
    """
    drops, methods = Counter(), Counter()
    arrivals, keep = [], []
    n_flights = 0
    for fid, g in df.groupby("flight_id", sort=False):
        n_flights += 1
        if len(g) < C.MIN_POINTS:
            drops["too_few_points"] += 1
            continue
        td, how = label_flight(g)
        if td is None:
            drops[how] += 1
            continue
        before = g[(~g["on_ground"]) & (g["t"] < td)]
        inner_t = before.loc[before["distance_nm"] <= C.INNER_GAP_NM, "t"].to_numpy()
        if inner_t.size == 0 or (np.diff(inner_t) > C.INNER_MAX_GAP_S).any():
            drops["gap_over_120s_inside_20nm"] += 1
            continue
        methods[how] += 1
        arrivals.append({
            "flight_id": fid, "icao24": g["icao24"].iloc[0],
            "callsign": next((c for c in g["callsign"] if c), ""),
            "touchdown": float(td), "label_method": how,
            "direction": landing_direction(before), "go_around": go_around(before),
            "category": g["category"].dropna().iloc[-1] if g["category"].notna().any() else -1,
        })
        keep.append(before)
    arrivals = pd.DataFrame(arrivals)
    points = (pd.concat(keep, ignore_index=True) if keep else df.iloc[0:0].copy())
    stats = {"flights_total": n_flights, "arrivals_kept": len(arrivals),
             "drop_reasons": dict(drops), "label_methods": dict(methods)}
    return arrivals, points, stats


def build_rows(features: pd.DataFrame, arrivals: pd.DataFrame) -> pd.DataFrame:
    """Prediction rows: 0 < y <= 3 h and distance <= 150 nm."""
    rows = features.merge(arrivals[["flight_id", "touchdown", "direction", "go_around",
                                    "label_method"]], on="flight_id")
    rows["y"] = rows["touchdown"] - rows["t"]
    rows = rows[(rows["y"] > 0) & (rows["y"] <= C.MAX_Y_S)
                & (rows["distance_nm"] <= C.MAX_DISTANCE_NM)]
    return rows.reset_index(drop=True)
