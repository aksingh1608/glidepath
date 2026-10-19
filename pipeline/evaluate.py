"""Evaluation on the test split. All intervals resample whole flights."""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

from . import config as C
from .trust import trust_table

CHUNK = 500


# Flight-level bootstrap
def _draws(n, seed=C.SEED, n_boot=C.N_BOOT):
    rng = np.random.default_rng(seed)
    done = 0
    while done < n_boot:
        size = min(CHUNK, n_boot - done)
        yield rng.integers(0, n, size=(size, n))
        done += size


def boot_ratio(num, den, seed=C.SEED):
    num, den = np.asarray(num, float), np.asarray(den, float)
    if len(num) == 0 or den.sum() == 0:
        return np.nan, np.nan, np.nan
    point = num.sum() / den.sum()
    with np.errstate(invalid="ignore", divide="ignore"):
        boot = np.concatenate([num[i].sum(1) / den[i].sum(1) for i in _draws(len(num), seed)])
    lo, hi = np.nanpercentile(boot, [2.5, 97.5])
    return float(point), float(lo), float(hi)


def boot_median(v, seed=C.SEED):
    v = np.asarray(v, float)
    if len(v) == 0:
        return np.nan, np.nan, np.nan
    boot = np.concatenate([np.median(v[i], axis=1) for i in _draws(len(v), seed)])
    lo, hi = np.percentile(boot, [2.5, 97.5])
    return float(np.median(v)), float(lo), float(hi)


def boot_median_diff(a, b, seed=C.SEED):
    """median(a) - median(b), two independent groups of flights."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    ba = np.concatenate([np.median(a[i], axis=1) for i in _draws(len(a), seed)])
    bb = np.concatenate([np.median(b[i], axis=1) for i in _draws(len(b), seed + 1)])
    lo, hi = np.percentile(ba - bb, [2.5, 97.5])
    return float(np.median(a) - np.median(b)), float(lo), float(hi)


# 1. Point accuracy at fixed distances
def point_accuracy(test: pd.DataFrame, methods: dict) -> list[dict]:
    out = []
    t = test.sort_values(["flight_id", "t"])
    max_d = t.groupby("flight_id")["distance_nm"].max()
    for h in C.HORIZONS_NM:
        seen = max_d[max_d > h].index
        inside = t[(t["distance_nm"] <= h) & t["flight_id"].isin(seen)]
        first = inside.groupby("flight_id").head(1)
        for name, col in methods.items():
            err = (first[col] - first["y"]).to_numpy()
            out.append({"horizon_nm": h, "method": name, "n_flights": int(len(first)),
                        "mae_s": float(np.mean(np.abs(err))) if len(err) else np.nan,
                        "rmse_s": float(np.sqrt(np.mean(err ** 2))) if len(err) else np.nan,
                        "p90_abs_s": float(np.quantile(np.abs(err), 0.9)) if len(err) else np.nan})
    return out


# 2. Coverage and width per band
def coverage_width(test: pd.DataFrame, lo_col: str, hi_col: str, method: str) -> list[dict]:
    d = test.assign(hit=(test[lo_col] <= test["y"]) & (test["y"] <= test[hi_col]),
                    width_min=(test[hi_col] - test[lo_col]) / 60.0)
    out = []
    groups = [(C.BAND_LABELS[b], d[d["band"] == b]) for b in range(len(C.BAND_LABELS))]
    groups.append(("all", d))
    for label, g in groups:
        per = g.groupby("flight_id").agg(hits=("hit", "sum"), n=("hit", "size"),
                                         wsum=("width_min", "sum"))
        cov = boot_ratio(per["hits"], per["n"])
        wid = boot_ratio(per["wsum"], per["n"])
        out.append({"method": method, "band": label, "n_rows": int(len(g)),
                    "n_flights": int(len(per)), "coverage": cov[0], "coverage_lo": cov[1],
                    "coverage_hi": cov[2], "width_min": wid[0], "width_lo": wid[1],
                    "width_hi": wid[2]})
    return out


# 3. Trust lead per window
def trust_summary(tt: pd.DataFrame, method: str) -> list[dict]:
    out = []
    for w, g in tt.groupby("window_min"):
        v = g["lead_min"].to_numpy()
        out.append({"method": method, "window_min": int(w), "n_flights": int(len(g)),
                    "median_min": float(np.median(v)), "q1_min": float(np.quantile(v, 0.25)),
                    "q3_min": float(np.quantile(v, 0.75)),
                    "share_never_trusted": float(g["never_trusted"].mean())})
    return out


# 4. Paired difference model minus baseline B
def paired(model_tt: pd.DataFrame, base_tt: pd.DataFrame, window=C.MAIN_WINDOW_MIN) -> dict:
    m = model_tt[model_tt["window_min"] == window].set_index("flight_id")["lead_min"]
    b = base_tt[base_tt["window_min"] == window].set_index("flight_id")["lead_min"]
    ids = m.index.intersection(b.index)
    d = (m[ids] - b[ids]).to_numpy()
    med, lo, hi = boot_median(d)
    nz = d[d != 0]
    if nz.size == 0:
        p, note = None, "all paired differences are zero"
    else:
        p, note = float(stats.wilcoxon(nz, zero_method="wilcox").pvalue), ""
    return {"window_min": window, "n_flights": int(len(d)), "median_diff_min": med,
            "ci_lo": lo, "ci_hi": hi, "wilcoxon_p": p, "n_nonzero": int(nz.size),
            "note": note, "mean_diff_min": float(np.mean(d)) if len(d) else np.nan}


# 5. Splits at W = 5
def flight_groups(test: pd.DataFrame) -> pd.DataFrame:
    inner = test[test["distance_nm"] <= 50]
    f = pd.DataFrame({
        "traffic_50_mean": inner.groupby("flight_id")["traffic_50"].mean(),
        "holding": test.groupby("flight_id")["holding"].max().astype(bool),
        "direction": test.groupby("flight_id")["direction"].first(),
    })
    f["traffic_tercile"] = pd.qcut(f["traffic_50_mean"].rank(method="first"), 3,
                                   labels=["quiet", "middle", "busy"]) if len(f) >= 3 else np.nan
    return f


def split_summary(tt: pd.DataFrame, groups: pd.DataFrame, window=C.MAIN_WINDOW_MIN) -> dict:
    lead = tt[tt["window_min"] == window].set_index("flight_id")
    g = groups.join(lead[["lead_min", "never_trusted"]], how="inner")
    out = {}
    for col in ("traffic_tercile", "direction", "holding"):
        rows = []
        for key, sub in g.groupby(col, observed=True):
            rows.append({"group": str(key).lower() if col == "holding" else str(key),
                         "n_flights": int(len(sub)), "median_min": float(sub["lead_min"].median()),
                         "share_never_trusted": float(sub["never_trusted"].mean())})
        out[col] = rows
    return out, g


# 7. Hypotheses
def _diff_status(point, lo):
    if lo > 0:
        return "supported"
    if point <= 0:
        return "not supported"
    return "unclear"


def hypotheses(cov: list[dict], pair: dict, g: pd.DataFrame) -> dict:
    target = 1 - C.ALPHA
    tol = C.H1_TOLERANCE
    cal = {r["band"]: r for r in cov if r["method"] == "model_calibrated" and r["band"] != "all"}
    raw = {r["band"]: r for r in cov if r["method"] == "model_uncalibrated" and r["band"] != "all"}
    eligible = [b for b, r in cal.items() if r["n_rows"] >= C.H1_MIN_TEST_ROWS]
    inside = lambda r: abs(r["coverage"] - target) <= tol + 1e-12
    if not eligible:
        h1 = {"status": "unclear", "reason": "no band has enough test rows"}
    else:
        cal_ok = all(inside(cal[b]) for b in eligible)
        raw_miss = [b for b in eligible if not inside(raw[b])]
        h1 = {"status": "supported" if cal_ok and raw_miss else "not supported",
              "calibrated_all_within": cal_ok, "uncalibrated_missing_bands": raw_miss}
    h1.update({"eligible_bands": eligible, "target": target, "tolerance": tol,
               "min_test_rows": C.H1_MIN_TEST_ROWS,
               "calibrated": {b: cal[b]["coverage"] for b in eligible},
               "uncalibrated": {b: raw[b]["coverage"] for b in eligible}})

    h2 = {"status": _diff_status(pair["median_diff_min"], pair["ci_lo"])
          if pair["n_flights"] else "unclear", **pair}

    q = g[g["traffic_tercile"] == "quiet"]["lead_min"]
    b = g[g["traffic_tercile"] == "busy"]["lead_min"]
    if min(len(q), len(b)) < C.H3_MIN_FLIGHTS:
        h3 = {"status": "unclear", "reason": "too few flights per tercile"}
    else:
        d, lo, hi = boot_median_diff(q, b)
        h3 = {"status": _diff_status(d, lo), "median_diff_quiet_minus_busy_min": d,
              "ci_lo": lo, "ci_hi": hi}
    h3.update({"n_quiet": int(len(q)), "n_busy": int(len(b)),
               "median_quiet_min": float(q.median()) if len(q) else None,
               "median_busy_min": float(b.median()) if len(b) else None})

    hold = g[g["holding"]]["lead_min"]
    nohold = g[~g["holding"]]["lead_min"]
    if len(hold) < C.H4_MIN_HOLDING_FLIGHTS or len(nohold) == 0:
        h4 = {"status": "unclear", "reason": "fewer holding flights than the minimum"}
    else:
        d, lo, hi = boot_median_diff(nohold, hold)
        h4 = {"status": _diff_status(d, lo), "median_diff_no_holding_minus_holding_min": d,
              "ci_lo": lo, "ci_hi": hi}
    h4.update({"n_holding": int(len(hold)), "n_no_holding": int(len(nohold)),
               "min_holding_flights": C.H4_MIN_HOLDING_FLIGHTS,
               "median_holding_min": float(hold.median()) if len(hold) else None,
               "median_no_holding_min": float(nohold.median()) if len(nohold) else None})
    return {"H1": h1, "H2": h2, "H3": h3, "H4": h4}


# 8. SHAP width attribution
def shap_width(model, test: pd.DataFrame) -> list[dict]:
    sample = test.sample(n=min(C.SHAP_MAX_ROWS, len(test)), random_state=C.SEED)
    c10 = model.contributions(sample, 0.1)[:, :-1]
    c90 = model.contributions(sample, 0.9)[:, :-1]
    imp = np.abs(c90 - c10).mean(axis=0) / 60.0
    order = np.argsort(imp)[::-1][:C.SHAP_TOP]
    return [{"feature": model.features[i], "mean_abs_width_contribution_min": float(imp[i])}
            for i in order]


def ablation_row(name: str, test: pd.DataFrame, lo_col: str, hi_col: str) -> dict:
    cov = coverage_width(test, lo_col, hi_col, name)[-1]
    tt = trust_table(test, lo_col, hi_col, [C.MAIN_WINDOW_MIN])
    med, lo, hi = boot_median(tt["lead_min"])
    return {"ablation": name, "coverage": cov["coverage"], "coverage_lo": cov["coverage_lo"],
            "coverage_hi": cov["coverage_hi"], "width_min": cov["width_min"],
            "median_lead_min": med, "median_lead_lo": lo, "median_lead_hi": hi,
            "share_never_trusted": float(tt["never_trusted"].mean())}
