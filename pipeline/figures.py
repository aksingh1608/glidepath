"""Figures. White background, 150 dpi, one message each."""

from __future__ import annotations

import os
import shutil

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from . import config as C  # noqa: E402

plt.rcParams.update({
    "figure.facecolor": "white", "axes.facecolor": "white", "savefig.facecolor": "white",
    "axes.grid": True, "grid.color": C.COLOR_GRID, "grid.linewidth": 0.7,
    "axes.spines.top": False, "axes.spines.right": False, "font.size": 10,
    "legend.frameon": False, "lines.linewidth": 2, "savefig.dpi": C.FIG_DPI,
    "savefig.bbox": "tight",
})

SERIES = {
    "model_calibrated": ("model, calibrated", C.COLOR_MODEL),
    "model_uncalibrated": ("model, uncalibrated", C.COLOR_UNCAL),
    "baseline_b_calibrated": ("baseline B, calibrated", C.COLOR_BASELINE_B),
}


def _title(ax, text, synthetic):
    ax.set_title(("SYNTHETIC TEST: " if synthetic else "") + text, loc="left", fontsize=10)


def trust_lead(trust: dict, out: str, synthetic: bool):
    fig, axes = plt.subplots(1, len(C.WINDOWS_MIN), figsize=(11, 3.4), sharey=True)
    for ax, w in zip(axes, C.WINDOWS_MIN):
        for key, (label, color) in SERIES.items():
            v = np.sort(trust[key].query("window_min == @w")["lead_min"].to_numpy())
            if v.size:
                ax.step(v, np.arange(1, v.size + 1) / v.size, where="post", color=color, label=label)
        ax.set_xlabel("trust lead (min)")
        ax.set_title(f"W = {w} min", fontsize=10, loc="left")
    axes[0].set_ylabel("share of test flights")
    axes[-1].legend(loc="lower right", fontsize=8)
    fig.suptitle(("SYNTHETIC TEST: " if synthetic else "")
                 + "Trust lead per flight (curve further right is better)", x=0.01, ha="left",
                 fontsize=10)
    fig.savefig(os.path.join(out, "trust_lead.png"))
    plt.close(fig)


def coverage(cov: pd.DataFrame, out: str, synthetic: bool):
    fig, ax = plt.subplots(figsize=(7, 3.6))
    bands = list(C.BAND_LABELS)
    x = np.arange(len(bands))
    width = 0.26
    for i, key in enumerate(["model_uncalibrated", "model_calibrated", "baseline_b_calibrated"]):
        label, color = SERIES[key]
        g = cov[cov["method"] == key].set_index("band").reindex(bands)
        y = 100 * g["coverage"].to_numpy()
        err = np.vstack([y - 100 * g["coverage_lo"].to_numpy(), 100 * g["coverage_hi"].to_numpy() - y])
        ax.bar(x + (i - 1) * width, y, width * 0.92, color=color, label=label,
               yerr=np.nan_to_num(err), error_kw={"ecolor": "#333333", "elinewidth": 1})
    ax.axhline(100 * (1 - C.ALPHA), color="#333333", lw=1.2, ls="--",
               label=f"target {100 * (1 - C.ALPHA):g} percent")
    ax.set_xticks(x, bands)
    ax.set_ylabel("coverage on test flights (%)")
    ax.set_ylim(0, 105)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.12), fontsize=8, ncol=4)
    _title(ax, "Interval coverage by distance band", synthetic)
    fig.savefig(os.path.join(out, "coverage.png"))
    plt.close(fig)


def width_vs_distance(test: pd.DataFrame, out: str, synthetic: bool):
    fig, ax = plt.subplots(figsize=(7, 3.6))
    dbin = (test["distance_nm"] // 5) * 5 + 2.5
    for key, lo, hi in (("model_uncalibrated", "p10", "p90"),
                        ("model_calibrated", "p10_cal", "p90_cal"),
                        ("baseline_b_calibrated", "baseline_b_lo", "baseline_b_hi")):
        label, color = SERIES[key]
        w = ((test[hi] - test[lo]) / 60).groupby(dbin).mean()
        ax.plot(w.index, w.to_numpy(), color=color, label=label)
    for wmin in C.WINDOWS_MIN:
        ax.axhline(wmin, color="#999999", lw=0.8, ls=":")
    ax.set_xlabel("distance to EDDF (nm)")
    ax.set_ylabel("mean interval width (min)")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.18), fontsize=8, ncol=3)
    _title(ax, "Interval width shrinks as the aircraft gets closer (dotted lines: W)", synthetic)
    fig.savefig(os.path.join(out, "width.png"))
    plt.close(fig)


def error_by_horizon(acc: pd.DataFrame, out: str, synthetic: bool):
    fig, ax = plt.subplots(figsize=(7, 3.6))
    colors = {"model": C.COLOR_MODEL, "baseline_a": C.COLOR_BASELINE_A,
              "baseline_b": C.COLOR_BASELINE_B}
    labels = {"model": "model (P50)", "baseline_a": "baseline A", "baseline_b": "baseline B"}
    hs = list(C.HORIZONS_NM)
    x = np.arange(len(hs))
    for i, m in enumerate(["model", "baseline_a", "baseline_b"]):
        g = acc[acc["method"] == m].set_index("horizon_nm").reindex(hs)
        ax.bar(x + (i - 1) * 0.26, g["mae_s"] / 60, 0.24, color=colors[m], label=labels[m])
    ax.set_xticks(x, [f"{h} nm" for h in hs])
    ax.set_ylabel("mean absolute error (min)")
    ax.legend(loc="upper right", fontsize=8)
    _title(ax, "Landing time error at fixed distances", synthetic)
    fig.savefig(os.path.join(out, "error_by_horizon.png"))
    plt.close(fig)


def shap_width(shap: list[dict], out: str, synthetic: bool):
    fig, ax = plt.subplots(figsize=(7, 3.6))
    names = [r["feature"] for r in shap][::-1]
    vals = [r["mean_abs_width_contribution_min"] for r in shap][::-1]
    ax.barh(names, vals, color=C.COLOR_MODEL)
    ax.set_xlabel("mean absolute contribution to interval width (min)")
    _title(ax, "What drives interval width (P90 minus P10 contributions)", synthetic)
    fig.savefig(os.path.join(out, "shap_width.png"))
    plt.close(fig)


def example_flight(g: pd.DataFrame, trust_y: float | None, title: str, path: str,
                   synthetic: bool):
    g = g.sort_values("t")
    x = g["y"].to_numpy() / 60
    fig, ax = plt.subplots(figsize=(7, 3.4))
    ax.fill_between(x, (g["p10_cal"] - g["y"]) / 60, (g["p90_cal"] - g["y"]) / 60,
                    color=C.COLOR_MODEL, alpha=0.3, lw=0, label="calibrated interval minus truth")
    ax.plot(x, (g["p50"] - g["y"]) / 60, color=C.COLOR_MODEL, lw=1.2, label="P50 minus truth")
    ax.axhline(0, color="#111111", lw=1, label="truth")
    if trust_y is not None:
        ax.axvline(trust_y / 60, color="#333333", ls="--", lw=1.2,
                   label=f"trust point, W = {C.MAIN_WINDOW_MIN} min")
    ax.invert_xaxis()
    ax.set_xlabel("minutes to touchdown")
    ax.set_ylabel("error (min)")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.2), fontsize=8, ncol=2)
    _title(ax, title, synthetic)
    fig.savefig(path)
    plt.close(fig)


SPLIT_COLORS = {"train": "#9a9a94", "calibration": C.COLOR_UNCAL, "test": C.COLOR_MODEL}


def data_overview(by_hour: list[dict], out: str, synthetic: bool):
    fig, ax = plt.subplots(figsize=(8, 3.4))
    hours = [r["hour_local"][-5:] for r in by_hour]
    x = np.arange(len(hours))
    bottom = np.zeros(len(hours))
    for s, color in SPLIT_COLORS.items():
        v = np.array([r.get(s, 0) for r in by_hour], float)
        ax.bar(x, v, 0.86, bottom=bottom, color=color, label=s, edgecolor="white", linewidth=1)
        bottom += v
    ax.set_xticks(x, hours, rotation=0 if len(hours) <= 12 else 45)
    ax.set_xlabel("touchdown hour (Europe/Berlin)")
    ax.set_ylabel("arrivals kept")
    ax.set_ylim(0, 1.18 * max(bottom.max(), 1))
    ax.legend(loc="upper right", fontsize=8, ncol=3)
    _title(ax, "Arrivals kept per hour, coloured by split (time blocks, no overlap)", synthetic)
    fig.savefig(os.path.join(out, "data_overview.png"))
    plt.close(fig)


def tracks(full: pd.DataFrame, ref: tuple, out: str, synthetic: bool):
    fig, ax = plt.subplots(figsize=(6.4, 5.6))
    for s, color in SPLIT_COLORS.items():
        first = True
        for _, g in full[full["split"] == s].groupby("flight_id", sort=False):
            g = g.sort_values("t")
            ax.plot(g["lon"], g["lat"], color=color, lw=0.8, alpha=0.7,
                    label=s if first else None)
            first = False
    ax.plot(ref[1], ref[0], "o", color="#111111", ms=6, mec="white", mew=1.5, label="EDDF")
    ax.set_aspect(1 / np.cos(np.radians(ref[0])))
    ax.set_xlabel("longitude")
    ax.set_ylabel("latitude")
    ax.legend(loc="upper left", fontsize=8)
    _title(ax, "Arrival tracks used, by split", synthetic)
    fig.savefig(os.path.join(out, "tracks.png"))
    plt.close(fig)


def paired_lead(model_tt: pd.DataFrame, base_tt: pd.DataFrame, window: int, out: str,
                synthetic: bool):
    m = model_tt[model_tt["window_min"] == window].set_index("flight_id")["lead_min"]
    b = base_tt[base_tt["window_min"] == window].set_index("flight_id")["lead_min"]
    ids = m.index.intersection(b.index)
    order = m[ids].sort_values(kind="stable").index
    y = np.arange(len(order))
    fig, ax = plt.subplots(figsize=(7, max(3, 0.18 * len(order) + 1.2)))
    ax.hlines(y, b[order], m[order], color="#bbbbbb", lw=1)
    ax.plot(b[order], y, "o", color=C.COLOR_BASELINE_B, ms=6, label="baseline B, calibrated")
    ax.plot(m[order], y, "o", color=C.COLOR_MODEL, ms=6, label="model, calibrated")
    ax.set_yticks([])
    ax.set_ylabel("test flights (sorted by model lead)")
    ax.set_xlabel(f"trust lead at W = {window} min (min)")
    ax.legend(loc="lower right", fontsize=8)
    _title(ax, "Trust lead per test flight, model against baseline B", synthetic)
    fig.savefig(os.path.join(out, "paired_lead.png"))
    plt.close(fig)


def coverage_drift(per_flight: pd.DataFrame, drift: list[dict], out: str, synthetic: bool):
    fig, ax = plt.subplots(figsize=(8, 3.6))
    t = (pd.to_datetime(per_flight["touchdown"], unit="s", utc=True).dt.tz_convert(C.LOCAL_TZ)
         .dt.tz_localize(None))
    for s, color in SPLIT_COLORS.items():
        k = per_flight["split"] == s
        ax.plot(t[k], 100 * per_flight.loc[k, "coverage"], "o", ms=5, color=color, alpha=0.8,
                label=s)
        r = next(d for d in drift if d["split"] == s)
        if k.any():
            ax.hlines(100 * r["coverage"], t[k].min(), t[k].max(), color=color, lw=2.5)
    ax.axhline(100 * (1 - C.ALPHA), color="#333333", lw=1.2, ls="--",
               label=f"target {100 * (1 - C.ALPHA):g} percent")
    ax.set_ylim(-5, 105)
    ax.set_xlabel("touchdown time (Europe/Berlin)")
    ax.set_ylabel("rows covered per flight (%)")
    ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%H:%M"))
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.18), fontsize=8, ncol=4)
    _title(ax, "Calibrated coverage per flight over the evening (bars: split mean)", synthetic)
    fig.savefig(os.path.join(out, "coverage_drift.png"))
    plt.close(fig)


def reliability(rel: list[dict], out: str, synthetic: bool):
    fig, ax = plt.subplots(figsize=(7, 3.6))
    ax.plot([0, 1], [0, 1], color="#333333", lw=1, ls="--", label="perfect")
    for key, (label, color) in SERIES.items():
        g = [r for r in rel if r["method"] == key]
        x = np.array([r["nominal"] for r in g])
        y = np.array([r["observed"] for r in g])
        err = np.vstack([y - [r["ci_lo"] for r in g], [r["ci_hi"] for r in g] - y])
        ax.errorbar(x, y, yerr=np.nan_to_num(err), fmt="o-", color=color, ms=6, capsize=3,
                    label=label)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_xlabel("nominal quantile")
    ax.set_ylabel("share of rows below quantile")
    ax.legend(loc="upper left", fontsize=8)
    _title(ax, "Quantile reliability on test flights", synthetic)
    fig.savefig(os.path.join(out, "reliability.png"))
    plt.close(fig)


def interval_scores(sc: list[dict], out: str, synthetic: bool):
    fig, ax = plt.subplots(figsize=(7, 3.6))
    bands = [r["band"] for r in sc]
    x = np.arange(len(bands))
    for i, (key, label, color) in enumerate((("is_model", "model, calibrated", C.COLOR_MODEL),
                                             ("is_base", "baseline B, calibrated",
                                              C.COLOR_BASELINE_B))):
        y = np.array([r[key] for r in sc])
        err = np.vstack([y - [r[key + "_lo"] for r in sc], [r[key + "_hi"] for r in sc] - y])
        ax.bar(x + (i - 0.5) * 0.36, y, 0.34, color=color, label=label, yerr=np.nan_to_num(err),
               error_kw={"ecolor": "#333333", "elinewidth": 1})
    ax.set_xticks(x, bands)
    ax.set_ylabel("mean interval score (min)")
    ax.legend(loc="upper left", fontsize=8)
    _title(ax, "Interval score by distance band (lower is better)", synthetic)
    fig.savefig(os.path.join(out, "interval_score.png"))
    plt.close(fig)


def copy_to_web(src: str, dst: str):
    os.makedirs(dst, exist_ok=True)
    for f in os.listdir(dst):
        if f.endswith(".png"):
            os.remove(os.path.join(dst, f))
    for f in os.listdir(src):
        if f.endswith(".png"):
            shutil.copy(os.path.join(src, f), os.path.join(dst, f))
