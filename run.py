#!/usr/bin/env python3
"""Glidepath pipeline: raw collector CSVs to results, figures, site data and docs.

Usage:
    .venv/bin/python run.py --raw data/raw/live
    .venv/bin/python run.py --raw data/synthetic --synthetic
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from pipeline import config as C
from pipeline import diagnostics as D, docs, evaluate as E, figures as F
from pipeline.data import build_arrivals, build_rows, clean, load_raw, split_flights
from pipeline.features import build_features
from pipeline.models import CQR, BaselineA, BaselineB, QuantileModel
from pipeline.splits import assign_splits
from pipeline.trust import trust_table

PRED_COLS = ["flight_id", "t", "distance_nm", "band", "direction", "holding", "traffic_50",
             "p10", "p50", "p90", "p10_cal", "p90_cal", "baseline_a", "baseline_b",
             "baseline_b_lo", "baseline_b_hi", "touchdown_true", "y", "split"]


def utc(t):
    return datetime.fromtimestamp(float(t), timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def local(t):
    return (pd.Timestamp(float(t), unit="s", tz="UTC").tz_convert(C.LOCAL_TZ)
            .strftime("%Y-%m-%d %H:%M:%S %Z"))


def clean_json(o):
    if isinstance(o, dict):
        return {str(k): clean_json(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [clean_json(v) for v in o]
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating, float)):
        return None if not np.isfinite(o) else float(o)
    if isinstance(o, np.bool_):
        return bool(o)
    return o


def fit_variant(rows, features, split):
    """Train the quantile model on train rows, calibrate on calibration rows."""
    train = rows[split == "train"]
    cal = rows[split == "calibration"]
    m = QuantileModel(features).fit(train)
    lo, mid, hi = m.predict(rows)
    cqr = CQR(per_band=True).fit(lo[split == "calibration"], hi[split == "calibration"],
                                 cal["y"].to_numpy(), cal["band"].to_numpy())
    glob = CQR(per_band=False).fit(lo[split == "calibration"], hi[split == "calibration"],
                                   cal["y"].to_numpy(), cal["band"].to_numpy())
    lo_c, hi_c = cqr.apply(lo, hi, rows["band"].to_numpy())
    lo_g, hi_g = glob.apply(lo, hi, rows["band"].to_numpy())
    return m, cqr, {"p10": lo, "p50": mid, "p90": hi, "p10_cal": lo_c, "p90_cal": hi_c,
                    "p10_glob": lo_g, "p90_glob": hi_g}


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--raw", default="data/raw/live")
    ap.add_argument("--synthetic", action="store_true")
    args = ap.parse_args()
    synthetic = args.synthetic or os.path.exists(os.path.join(args.raw, "SYNTHETIC"))
    label = C.SYNTHETIC_LABEL if synthetic else "PILOT"
    print(f"[{label}] reading {args.raw}")

    raw = load_raw(args.raw)
    n_files = int(raw["n_files"].iloc[0])
    pts = split_flights(clean(raw))
    arrivals, points, lab = build_arrivals(pts)
    if arrivals.empty:
        raise SystemExit("no arrivals found; stopping")
    print(f"[{label}] flights {lab['flights_total']}, arrivals kept {lab['arrivals_kept']}")
    feats = build_features(points, arrivals)
    rows = build_rows(feats, arrivals)

    split_map, split_info = assign_splits(arrivals[arrivals["flight_id"].isin(rows["flight_id"])])
    rows["split"] = rows["flight_id"].map(split_map)
    rows = rows[rows["split"].notna()].reset_index(drop=True)
    split = rows["split"].to_numpy()
    for s in ("train", "calibration", "test"):
        if not (split == s).any():
            raise SystemExit(f"split {s} is empty; need more arrivals")

    # Baselines
    train = rows[split == "train"]
    cal_mask = split == "calibration"
    base_a = BaselineA().fit(train)
    a_lo, a_p, a_hi = base_a.predict(rows)
    base_b = BaselineB(base_a).fit(train)
    b_lo, b_p, b_hi = base_b.predict(rows)
    b_source = pd.Series(base_b.last_source[split == "test"]).value_counts(normalize=True)
    b_cqr = CQR(per_band=True).fit(b_lo[cal_mask], b_hi[cal_mask], rows.loc[cal_mask, "y"].to_numpy(),
                                   rows.loc[cal_mask, "band"].to_numpy())
    b_lo_c, b_hi_c = b_cqr.apply(b_lo, b_hi, rows["band"].to_numpy())
    rows["baseline_a"] = a_p
    rows["baseline_b"] = b_p
    rows["baseline_b_lo_raw"], rows["baseline_b_hi_raw"] = b_lo, b_hi
    rows["baseline_b_lo"], rows["baseline_b_hi"] = b_lo_c, b_hi_c
    rows["touchdown_true"] = rows["touchdown"]

    # Main model and the two retrained ablations
    variants = {
        "full": C.FEATURES,
        "no_traffic": [f for f in C.FEATURES if f not in C.TRAFFIC_FEATURES],
        "no_direction": [f for f in C.FEATURES if f not in C.DIRECTION_FEATURES],
    }
    os.makedirs("data/predictions", exist_ok=True)
    fitted, var_rows = {}, {}
    for name, feat in variants.items():
        print(f"[{label}] training {name}")
        m, cqr, p = fit_variant(rows, feat, split)
        r = rows.copy()
        for k, v in p.items():
            r[k] = v
        r[PRED_COLS].to_parquet(f"data/predictions/{name}.parquet", index=False)
        fitted[name] = (m, cqr)
        var_rows[name] = r
    full = var_rows["full"]
    model, cqr = fitted["full"]
    test = full[full["split"] == "test"].copy()

    # Evaluation
    acc = E.point_accuracy(test, {"model": "p50", "baseline_a": "baseline_a",
                                  "baseline_b": "baseline_b"})
    cov = (E.coverage_width(test, "p10", "p90", "model_uncalibrated")
           + E.coverage_width(test, "p10_cal", "p90_cal", "model_calibrated")
           + E.coverage_width(test, "baseline_b_lo", "baseline_b_hi", "baseline_b_calibrated"))
    tt = {"model_calibrated": trust_table(test, "p10_cal", "p90_cal", C.WINDOWS_MIN),
          "model_uncalibrated": trust_table(test, "p10", "p90", C.WINDOWS_MIN),
          "baseline_b_calibrated": trust_table(test, "baseline_b_lo", "baseline_b_hi",
                                               C.WINDOWS_MIN)}
    trust = sum((E.trust_summary(v, k) for k, v in tt.items()), [])
    pair = E.paired(tt["model_calibrated"], tt["baseline_b_calibrated"])
    groups = E.flight_groups(test)
    splits_w5, g = E.split_summary(tt["model_calibrated"], groups)
    abl = [E.ablation_row("full model", test, "p10_cal", "p90_cal")]
    for name, title in (("no_traffic", "no traffic features"),
                        ("no_direction", "no direction feature")):
        vt = var_rows[name][var_rows[name]["split"] == "test"]
        abl.append(E.ablation_row(title, vt, "p10_cal", "p90_cal"))
    abl.append(E.ablation_row("no conformal step", test, "p10", "p90"))
    abl.append(E.ablation_row("one global conformal correction", test, "p10_glob", "p90_glob"))
    hyp = E.hypotheses(cov, pair, g)
    shap = E.shap_width(model, test)
    diag, per_flight = D.run(full, test, tt, arrivals, split_map)

    main_tt = tt["model_calibrated"].query("window_min == @C.MAIN_WINDOW_MIN")
    lead = float(main_tt["lead_min"].median())
    n_test = int(test["flight_id"].nunique())
    headline = (f"In this pilot, a typical Frankfurt arrival had a landing time we could trust "
                f"within {C.MAIN_WINDOW_MIN} minutes, {lead:.1f} minutes before touchdown "
                f"({n_test} test flights).")
    if synthetic:
        headline = f"{C.SYNTHETIC_LABEL}: " + headline

    # Example flights: typical, shortest lead, holding if any
    ex = main_tt.set_index("flight_id")
    trusted = ex[~ex["never_trusted"]]
    pick = []
    if len(trusted):
        med = trusted["lead_min"].median()
        pick.append(("typical", (trusted["lead_min"] - med).abs().sort_values(kind="stable").index[0]))
    pick.append(("shortest", ex.sort_values(["lead_min"], kind="stable").index[0]))
    hold_ids = [f for f in groups.index[groups["holding"]] if f in ex.index]
    if hold_ids:
        hl = ex.loc[hold_ids, "lead_min"]
        pick.append(("holding", (hl - hl.median()).abs().sort_values(kind="stable").index[0]))

    # Outputs: figures
    figdir = "results/figures"
    os.makedirs(figdir, exist_ok=True)
    for f in os.listdir(figdir):
        if f.endswith(".png"):
            os.remove(os.path.join(figdir, f))
    cov_df = pd.DataFrame(cov)
    F.trust_lead(tt, figdir, synthetic)
    F.coverage(cov_df, figdir, synthetic)
    F.width_vs_distance(test, figdir, synthetic)
    F.error_by_horizon(pd.DataFrame(acc), figdir, synthetic)
    F.shap_width(shap, figdir, synthetic)
    F.data_overview(diag["arrivals_by_hour"], figdir, synthetic)
    F.tracks(full, (C.REF_LAT, C.REF_LON), figdir, synthetic)
    F.paired_lead(tt["model_calibrated"], tt["baseline_b_calibrated"], C.MAIN_WINDOW_MIN, figdir,
                  synthetic)
    F.coverage_drift(per_flight, diag["drift"], figdir, synthetic)
    F.reliability(diag["reliability"], figdir, synthetic)
    F.interval_scores(diag["scores"], figdir, synthetic)
    examples = []
    callsign = arrivals.set_index("flight_id")["callsign"]
    for role, fid in pick:
        r = ex.loc[fid]
        gfl = test[test["flight_id"] == fid].sort_values("t")
        ty = None if r["never_trusted"] else float(gfl.loc[gfl["t"] == r["trust_t"], "y"].iloc[0])
        title = (f"Example, {role} lead: {callsign.get(fid, fid)}, "
                 + ("never trusted" if r["never_trusted"] else f"trust lead {r['lead_min']:.1f} min"))
        F.example_flight(gfl, ty, title, os.path.join(figdir, f"example_{role}.png"), synthetic)
        examples.append({"role": role, "flight_id": fid, "callsign": callsign.get(fid, ""),
                         "lead_min": float(r["lead_min"]), "never_trusted": bool(r["never_trusted"]),
                         "figure": f"figures/example_{role}.png"})
    F.copy_to_web(figdir, "web/figures")

    # Outputs: results.json and tables
    t_all = raw["poll_time"] if "poll_time" in raw else raw["time_position"]
    results = {
        "label": label, "synthetic": synthetic,
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "headline": headline,
        "config": {"alpha": C.ALPHA, "coverage_target_pct": 100 * (1 - C.ALPHA),
                   "windows_min": list(C.WINDOWS_MIN), "main_window_min": C.MAIN_WINDOW_MIN,
                   "n_boot": C.N_BOOT, "seed": C.SEED, "bands": list(C.BAND_LABELS),
                   "horizons_nm": list(C.HORIZONS_NM), "h1_min_test_rows": C.H1_MIN_TEST_ROWS,
                   "h1_tolerance_points": 100 * C.H1_TOLERANCE,
                   "h4_min_holding_flights": C.H4_MIN_HOLDING_FLIGHTS,
                   "max_distance_nm": C.MAX_DISTANCE_NM, "features": C.FEATURES,
                   "method": {"flight_gap_min": C.FLIGHT_GAP_S / 60, "min_points": C.MIN_POINTS,
                              "arrival_start_nm": C.ARRIVAL_START_NM, "ground_nm": C.GROUND_NM,
                              "midpoint_max_gap_s": C.MIDPOINT_MAX_GAP_S,
                              "extrap_cap_s": C.EXTRAP_CAP_S,
                              "inner_gap_nm": C.INNER_GAP_NM, "inner_max_gap_s": C.INNER_MAX_GAP_S,
                              "max_y_hours": C.MAX_Y_S / 3600, "quantiles": list(C.QUANTILES),
                              "baseline_b_bin_nm": C.BASELINE_B_BIN_NM,
                              "baseline_b_min_rows": C.BASELINE_B_MIN_ROWS,
                              "cqr_min_band_rows": C.CQR_MIN_BAND_ROWS,
                              "holding_turn_deg": C.HOLDING_TURN_DEG,
                              "turn_window_s": C.TURN_WINDOW_S,
                              "train_frac": C.TRAIN_FRAC, "cal_frac": C.CAL_FRAC,
                              "min_split_days": C.MIN_SPLIT_DAYS,
                              "min_arrivals_per_day": C.MIN_ARRIVALS_PER_DAY,
                              "replay_step_s": C.REPLAY_STEP_S}},
        "data_window": {"first_utc": utc(t_all.min()), "last_utc": utc(t_all.max()),
                        "first_local": local(t_all.min()), "last_local": local(t_all.max()),
                        "hours": float((t_all.max() - t_all.min()) / 3600),
                        "raw_rows": int(len(raw)), "raw_files": n_files,
                        "aircraft": int(raw["icao24"].nunique()), "source": args.raw},
        "counts": {**{k: v for k, v in lab.items() if k not in ("drop_reasons", "label_methods")},
                   "arrivals_with_rows": int(rows["flight_id"].nunique()),
                   "rows": int(len(rows)),
                   "rows_by_split": {s: int((split == s).sum()) for s in ("train", "calibration", "test")},
                   "flights_by_split": {s: int(rows.loc[split == s, "flight_id"].nunique())
                                        for s in ("train", "calibration", "test")},
                   "test_flights": n_test,
                   "directions": arrivals["direction"].value_counts().to_dict(),
                   "go_arounds": int(arrivals["go_around"].sum())},
        "drop_reasons": lab["drop_reasons"], "label_methods": lab["label_methods"],
        "splits": split_info,
        "models": {"best_iteration": {str(k): v for k, v in model.best_iter.items()},
                   "cqr_model": cqr.summary(), "cqr_baseline_b": b_cqr.summary(),
                   "baseline_b_source_share_test": b_source.to_dict()},
        "point_accuracy": acc, "coverage": cov, "trust": trust, "paired_w5": pair,
        "splits_w5": splits_w5, "ablations": abl, "hypotheses": hyp, "shap_width": shap,
        "examples": examples, "diagnostics": diag,
    }
    results = clean_json(results)
    for k, h in results["hypotheses"].items():
        h["summary"] = docs.hypothesis_text(k, h, results)
    os.makedirs("results/tables", exist_ok=True)
    with open("results/results.json", "w") as f:
        json.dump(results, f, indent=2)
    pd.DataFrame(acc).to_csv("results/tables/point_accuracy.csv", index=False)
    cov_df.to_csv("results/tables/coverage.csv", index=False)
    pd.DataFrame(trust).to_csv("results/tables/trust_lead.csv", index=False)
    pd.DataFrame(abl).to_csv("results/tables/ablations.csv", index=False)
    pd.DataFrame(shap).to_csv("results/tables/shap_width.csv", index=False)
    for k, v in splits_w5.items():
        pd.DataFrame(v).to_csv(f"results/tables/split_{k}.csv", index=False)
    for k in ("scores", "paired_point_error", "reliability", "drift", "arrivals_by_hour"):
        pd.DataFrame(diag[k]).to_csv(f"results/tables/{k}.csv", index=False)
    per_flight.to_csv("results/tables/coverage_per_flight.csv", index=False)
    pd.concat([v.assign(method=k) for k, v in tt.items()]).to_csv(
        "results/tables/trust_lead_per_flight.csv", index=False)

    # Outputs: site data
    os.makedirs("web/data", exist_ok=True)
    rep = test.assign(bucket=(test["t"] // C.REPLAY_STEP_S)).sort_values("t")
    rep = rep.groupby(["flight_id", "bucket"], sort=False).head(1)
    trust_by = {w: tt["model_calibrated"].query("window_min == @w").set_index("flight_id")["trust_t"]
                for w in C.WINDOWS_MIN}
    flights = []
    for fid, gf in rep.groupby("flight_id", sort=False):
        gf = gf.sort_values("t")
        flights.append({
            "id": fid, "callsign": callsign.get(fid, "") or fid.split("_")[0],
            "touchdown": float(gf["touchdown"].iloc[0]),
            "direction": gf["direction"].iloc[0],
            "trust_t": {str(w): (None if pd.isna(trust_by[w].get(fid)) else float(trust_by[w][fid]))
                        for w in C.WINDOWS_MIN},
            "points": [[float(r.t), round(float(r.lat), 5), round(float(r.lon), 5),
                        round(float(r.t + r.p50), 1), round(float(r.t + r.p10_cal), 1),
                        round(float(r.t + r.p90_cal), 1)] for r in gf.itertuples()],
        })
    replay = {"label": label, "synthetic": synthetic, "windows_min": list(C.WINDOWS_MIN),
              "point_fields": ["t", "lat", "lon", "pred_touchdown", "lo_touchdown", "hi_touchdown"],
              "airport": {"lat": C.REF_LAT, "lon": C.REF_LON}, "flights": flights}
    with open("web/data/replay.json", "w") as f:
        json.dump(clean_json(replay), f, separators=(",", ":"))
    with open("web/data/results.json", "w") as f:
        json.dump(results, f, indent=1)

    docs.write_all(results)
    print(f"[{label}] {headline}")


if __name__ == "__main__":
    main()
