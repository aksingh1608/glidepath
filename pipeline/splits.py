"""Train, calibration and test splits by whole flights."""

from __future__ import annotations

import pandas as pd

from . import config as C


def _span(arrivals: pd.DataFrame, ids) -> dict:
    td = arrivals.loc[arrivals["flight_id"].isin(ids), "touchdown"]
    if td.empty:
        return {"flights": 0, "first_touchdown_utc": None, "last_touchdown_utc": None}
    fmt = lambda x: pd.to_datetime(x, unit="s", utc=True).strftime("%Y-%m-%d %H:%M:%S UTC")
    return {"flights": int(len(td)), "first_touchdown_utc": fmt(td.min()),
            "last_touchdown_utc": fmt(td.max())}


def assign_splits(arrivals: pd.DataFrame) -> tuple[dict, dict]:
    """Return ({flight_id: split}, info)."""
    a = arrivals.sort_values("touchdown").reset_index(drop=True)
    day = (pd.to_datetime(a["touchdown"], unit="s", utc=True)
           .dt.tz_convert(C.LOCAL_TZ).dt.date)
    counts = day.value_counts().sort_index()
    full_days = [d for d, n in counts.items() if n >= C.MIN_ARRIVALS_PER_DAY]
    split = {}
    if len(full_days) >= C.MIN_SPLIT_DAYS:
        test_day, cal_day = full_days[-1], full_days[-2]
        for fid, d in zip(a["flight_id"], day):
            if d == test_day:
                split[fid] = "test"
            elif d == cal_day:
                split[fid] = "calibration"
            elif d < cal_day:
                split[fid] = "train"
        scheme = "by_day"
        detail = {"test_day": str(test_day), "calibration_day": str(cal_day)}
    else:
        n = len(a)
        n_train = int(round(C.TRAIN_FRAC * n))
        n_cal = int(round(C.CAL_FRAC * n))
        for i, fid in enumerate(a["flight_id"]):
            split[fid] = ("train" if i < n_train else
                          "calibration" if i < n_train + n_cal else "test")
        scheme = "time_block"
        detail = {"train_frac": C.TRAIN_FRAC, "calibration_frac": C.CAL_FRAC,
                  "test_frac": round(1 - C.TRAIN_FRAC - C.CAL_FRAC, 10)}
    info = {"scheme": scheme, **detail,
            "arrivals_per_local_day": {str(k): int(v) for k, v in counts.items()}}
    for s in ("train", "calibration", "test"):
        info[s] = _span(a, [f for f, v in split.items() if v == s])
    return split, info
