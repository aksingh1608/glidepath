"""Further statistics on the test split. Exploratory: they explain the hypothesis results
but do not change any verdict. All intervals resample whole flights."""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import config as C
from .evaluate import _draws, boot_ratio


def boot_mean(v, seed=C.SEED):
    v = np.asarray(v, float)
    if len(v) == 0:
        return np.nan, np.nan, np.nan
    boot = np.concatenate([v[i].mean(axis=1) for i in _draws(len(v), seed)])
    lo, hi = np.percentile(boot, [2.5, 97.5])
    return float(v.mean()), float(lo), float(hi)


def _per_flight_ratio(d: pd.DataFrame, col: str):
    per = d.groupby("flight_id")[col].agg(["sum", "size"])
    return boot_ratio(per["sum"], per["size"])


def _bands(d: pd.DataFrame):
    out = [(C.BAND_LABELS[b], d[d["band"] == b]) for b in range(len(C.BAND_LABELS))]
    return out + [("all", d)]


# 1. Interval score (Winkler) and pinball loss: lower is better
def interval_score(lo, hi, y, alpha=C.ALPHA):
    """Width plus 2 / alpha times the miss distance, in minutes."""
    lo, hi, y = map(np.asarray, (lo, hi, y))
    return ((hi - lo) + (2 / alpha) * np.clip(lo - y, 0, None)
            + (2 / alpha) * np.clip(y - hi, 0, None)) / 60.0


def pinball(preds: dict, y):
    """Mean quantile loss over the quantiles in preds ({q: array}), in minutes."""
    y = np.asarray(y)
    loss = [np.maximum(q * (y - p), (q - 1) * (y - p)) for q, p in preds.items()]
    return np.mean(loss, axis=0) / 60.0


def scores(test: pd.DataFrame) -> list[dict]:
    d = test.assign(
        is_model=interval_score(test["p10_cal"], test["p90_cal"], test["y"]),
        is_base=interval_score(test["baseline_b_lo"], test["baseline_b_hi"], test["y"]),
        pb_model=pinball({0.1: test["p10"], 0.5: test["p50"], 0.9: test["p90"]}, test["y"]),
        pb_base=pinball({0.1: test["baseline_b_lo_raw"], 0.5: test["baseline_b"],
                         0.9: test["baseline_b_hi_raw"]}, test["y"]))
    d["is_diff"] = d["is_model"] - d["is_base"]
    d["pb_diff"] = d["pb_model"] - d["pb_base"]
    out = []
    for band, g in _bands(d):
        if g.empty:
            continue
        row = {"band": band, "n_rows": int(len(g)), "n_flights": int(g["flight_id"].nunique())}
        for k in ("is_model", "is_base", "is_diff", "pb_model", "pb_base", "pb_diff"):
            row[k], row[k + "_lo"], row[k + "_hi"] = _per_flight_ratio(g, k)
        out.append(row)
    return out


# 2. Paired point error: model P50 minus each baseline, first row inside each distance
def paired_point_error(test: pd.DataFrame) -> list[dict]:
    t = test.sort_values(["flight_id", "t"])
    max_d = t.groupby("flight_id")["distance_nm"].max()
    out = []
    for h in C.HORIZONS_NM:
        seen = max_d[max_d > h].index
        first = t[(t["distance_nm"] <= h) & t["flight_id"].isin(seen)].groupby("flight_id").head(1)
        e_model = (first["p50"] - first["y"]).abs().to_numpy() / 60
        for name, col in (("baseline_a", "baseline_a"), ("baseline_b", "baseline_b")):
            diff = e_model - (first[col] - first["y"]).abs().to_numpy() / 60
            m, lo, hi = boot_mean(diff)
            out.append({"horizon_nm": h, "versus": name, "n_flights": int(len(diff)),
                        "mean_abs_error_diff_min": m, "ci_lo": lo, "ci_hi": hi,
                        "share_model_better": float((diff < 0).mean()) if len(diff) else np.nan})
    return out


# 3. Quantile reliability: share of rows with truth below each predicted quantile
def reliability(test: pd.DataFrame) -> list[dict]:
    cols = [("model_uncalibrated", 0.1, "p10"), ("model_uncalibrated", 0.5, "p50"),
            ("model_uncalibrated", 0.9, "p90"),
            ("model_calibrated", 0.1, "p10_cal"), ("model_calibrated", 0.5, "p50"),
            ("model_calibrated", 0.9, "p90_cal"),
            ("baseline_b_calibrated", 0.1, "baseline_b_lo"),
            ("baseline_b_calibrated", 0.5, "baseline_b"),
            ("baseline_b_calibrated", 0.9, "baseline_b_hi")]
    out = []
    for method, q, col in cols:
        share, lo, hi = _per_flight_ratio(test.assign(below=test["y"] <= test[col]), "below")
        out.append({"method": method, "nominal": q, "observed": share, "ci_lo": lo, "ci_hi": hi})
    return out


# 4. Calibration drift: calibrated coverage in each split and per flight
def drift(full: pd.DataFrame) -> tuple[list[dict], pd.DataFrame]:
    d = full.assign(hit=(full["p10_cal"] <= full["y"]) & (full["y"] <= full["p90_cal"]),
                    width_min=(full["p90_cal"] - full["p10_cal"]) / 60)
    rows = []
    for s in ("train", "calibration", "test"):
        g = d[d["split"] == s]
        cov, lo, hi = _per_flight_ratio(g, "hit")
        rows.append({"split": s, "n_flights": int(g["flight_id"].nunique()),
                     "coverage": cov, "coverage_lo": lo, "coverage_hi": hi,
                     "width_min": float(g["width_min"].mean()),
                     "median_true_min": float(g["y"].median() / 60)})
    per = d.groupby("flight_id").agg(split=("split", "first"), touchdown=("touchdown", "first"),
                                     coverage=("hit", "mean"), width_min=("width_min", "mean"))
    return rows, per.reset_index()


# 5. Who wins per flight at the main window
def superiority(model_tt: pd.DataFrame, base_tt: pd.DataFrame, window=C.MAIN_WINDOW_MIN) -> dict:
    m = model_tt[model_tt["window_min"] == window].set_index("flight_id")["lead_min"]
    b = base_tt[base_tt["window_min"] == window].set_index("flight_id")["lead_min"]
    ids = m.index.intersection(b.index)
    d = (m[ids] - b[ids]).to_numpy()
    mean, lo, hi = boot_mean(d)
    n = max(len(d), 1)
    return {"window_min": window, "n_flights": int(len(d)),
            "share_model_longer": float((d > 0).sum() / n), "share_tie": float((d == 0).sum() / n),
            "share_baseline_longer": float((d < 0).sum() / n),
            "mean_diff_min": mean, "mean_ci_lo": lo, "mean_ci_hi": hi}


# 6. Data overview: arrivals per local hour and split
def arrivals_by_hour(arrivals: pd.DataFrame, split_map: dict) -> list[dict]:
    a = arrivals[arrivals["flight_id"].isin(split_map)].copy()
    a["split"] = a["flight_id"].map(split_map)
    a["hour"] = (pd.to_datetime(a["touchdown"], unit="s", utc=True).dt.tz_convert(C.LOCAL_TZ)
                 .dt.floor("h").dt.strftime("%Y-%m-%d %H:00"))
    tab = a.pivot_table(index="hour", columns="split", values="flight_id", aggfunc="count",
                        fill_value=0)
    tab = tab.reindex(columns=["train", "calibration", "test"], fill_value=0)
    return [{"hour_local": h, **{s: int(v) for s, v in r.items()}} for h, r in tab.iterrows()]


def run(full: pd.DataFrame, test: pd.DataFrame, tt: dict, arrivals: pd.DataFrame,
        split_map: dict) -> tuple[dict, pd.DataFrame]:
    drift_rows, per_flight = drift(full)
    out = {"scores": scores(test), "paired_point_error": paired_point_error(test),
           "reliability": reliability(test), "drift": drift_rows,
           "superiority_w5": superiority(tt["model_calibrated"], tt["baseline_b_calibrated"]),
           "arrivals_by_hour": arrivals_by_hour(arrivals, split_map)}
    return out, per_flight
