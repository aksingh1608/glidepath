"""README.md, docs/research_note.md and docs/summary.md, generated from results.json.

Every number in these files is read from the results dictionary.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

REPO_LINK = "https://github.com/aksingh1608/glidepath"
NOT_OPERATIONAL = "Research demo, not for operational use."
AUTHOR = "Aryan Kumar Singh"
AFFILIATION = "Berlin School of Business and Innovation"
AUTHOR_LINE = (f"{AUTHOR} · MSc student at {AFFILIATION}, Berlin · "
               "[bewithaksingh.com](https://bewithaksingh.com) · "
               "[LinkedIn](https://linkedin.com/in/aksingh06) · [GitHub](https://github.com/aksingh1608)")
LOCAL_TZ = ZoneInfo("Europe/Berlin")

METHOD_NAMES = {"model_calibrated": "Model, calibrated", "model_uncalibrated": "Model, uncalibrated",
                "baseline_b_calibrated": "Baseline B, calibrated", "model": "Model (P50)",
                "baseline_a": "Baseline A", "baseline_b": "Baseline B (P50)"}


def f1(x):
    return "n/a" if x is None else f"{x:.1f}"


def pct(x):
    return "n/a" if x is None else f"{100 * x:.1f}"


def num(x):
    if x is None:
        return "n/a"
    return f"{x:g}" if isinstance(x, float) else str(x)


def table(header, rows):
    out = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


def local_dt(utc_text):
    """'2026-10-18 15:45:52 UTC' to an aware Europe/Berlin datetime."""
    t = datetime.strptime(utc_text, "%Y-%m-%d %H:%M:%S UTC").replace(tzinfo=timezone.utc)
    return t.astimezone(LOCAL_TZ)


def day_text(t):
    return f"{t.day} {t:%B %Y}"


def span_text(a_utc, b_utc):
    """Local span: one date when both ends fall on the same day."""
    a, b = local_dt(a_utc), local_dt(b_utc)
    if a.date() == b.date():
        return f"{day_text(a)}, {a:%H:%M} to {b:%H:%M %Z}"
    return f"{day_text(a)} {a:%H:%M %Z} to {day_text(b)} {b:%H:%M %Z}"


def a_an(word):
    return "an" if str(word)[:1] in "8" or str(word).startswith(("11", "18")) else "a"


def secs_text(s):
    return "a minute" if s == 60 else f"{num(s)} seconds"


def window_text(r):
    d = r["data_window"]
    a, b = local_dt(d["first_utc"]), local_dt(d["last_utc"])
    end = f"{b:%H:%M %Z}"
    if b.date() != a.date():
        end += " the next morning" if (b.date() - a.date()).days == 1 and b.hour < 12 else f" on {day_text(b)}"
    return f"{day_text(a)}, {a:%H:%M %Z} to {end} ({f1(d['hours'])} hours)"


def notice(r):
    d, c = r["data_window"], r["counts"]
    if r["synthetic"]:
        return ("> **SYNTHETIC TEST.** These results come from simulated data made to test the code. "
                "They say nothing about Frankfurt.")
    return (f"> This is a pilot. It uses one evening of live OpenSky data from Frankfurt, "
            f"{window_text(r)}. I kept {c['arrivals_kept']} arrivals and held out the last "
            f"{c['test_flights']} as a test set. The collector is still running, so the next "
            "version will use separate days.")


def hypothesis_text(key, h, r):
    cfg = r["config"]
    s = h["status"]
    if key == "H1":
        if not h.get("eligible_bands"):
            return f"H1 {s}: no distance band has {cfg['h1_min_test_rows']} or more test rows."
        cal = ", ".join(f"{b} {pct(v)}" for b, v in h["calibrated"].items())
        raw = ", ".join(f"{b} {pct(v)}" for b, v in h["uncalibrated"].items())
        return (f"H1 {s}. Calibrated coverage (%) by band: {cal}. Uncalibrated: {raw}. "
                f"Target {num(cfg['coverage_target_pct'])} ± {num(cfg['h1_tolerance_points'])} "
                f"points, bands with at least {cfg['h1_min_test_rows']} test rows.")
    if key == "H2":
        p = "n/a" if h.get("wilcoxon_p") is None else f"{h['wilcoxon_p']:.3g}"
        extra = f" ({h['note']})" if h.get("note") else ""
        out = (f"H2 {s}. Median paired difference in trust lead at W = {h['window_min']} min, "
               f"model minus baseline B: {f1(h['median_diff_min'])} min, 95% bootstrap interval "
               f"{f1(h['ci_lo'])} to {f1(h['ci_hi'])} min, {h['n_flights']} flights, "
               f"Wilcoxon p = {p}{extra}.")
        b = baseline_facts(r)
        if b["base_width"] > h["window_min"]:
            out += (f" Baseline B's mean width ({f1(b['base_width'])} min) is above W, so it cannot "
                    f"qualify at W = {h['window_min']}. At W = {b['wmax']} the medians are "
                    f"{f1(b['model_wmax']['median_min'])} and {f1(b['base_wmax']['median_min'])} min.")
        return out
    if key == "H3":
        base = (f"H3 {s}. Median trust lead {f1(h['median_quiet_min'])} min in the quietest "
                f"traffic tercile ({h['n_quiet']} flights) and {f1(h['median_busy_min'])} min in "
                f"the busiest ({h['n_busy']} flights).")
        if "ci_lo" in h:
            base += (f" Difference quiet minus busy {f1(h['median_diff_quiet_minus_busy_min'])} min, "
                     f"95% interval {f1(h['ci_lo'])} to {f1(h['ci_hi'])}.")
        return base
    if key == "H4":
        base = (f"H4 {s}. {h['n_holding']} test {'flight' if h['n_holding'] == 1 else 'flights'} with holding, {h['n_no_holding']} without "
                f"(minimum for a test: {h['min_holding_flights']}).")
        if "ci_lo" in h:
            base += (f" Median lead {f1(h['median_holding_min'])} min with holding and "
                     f"{f1(h['median_no_holding_min'])} min without. Difference "
                     f"{f1(h['median_diff_no_holding_minus_holding_min'])} min, 95% interval "
                     f"{f1(h['ci_lo'])} to {f1(h['ci_hi'])}.")
        return base
    return f"{key} {s}."


def accuracy_table(r):
    rows = [[f"{a['horizon_nm']} nm", METHOD_NAMES[a["method"]], a["n_flights"],
             f"{a['mae_s']:.0f}" if a["mae_s"] is not None else "n/a",
             f"{a['rmse_s']:.0f}" if a["rmse_s"] is not None else "n/a",
             f"{a['p90_abs_s']:.0f}" if a["p90_abs_s"] is not None else "n/a"]
            for a in r["point_accuracy"]]
    return table(["Distance", "Method", "Flights", "MAE (s)", "RMSE (s)", "P90 abs error (s)"], rows)


def coverage_table(r):
    rows = []
    for c in r["coverage"]:
        rows.append([METHOD_NAMES[c["method"]], c["band"], c["n_rows"], c["n_flights"],
                     f"{pct(c['coverage'])} [{pct(c['coverage_lo'])}, {pct(c['coverage_hi'])}]",
                     f1(c["width_min"])])
    return table(["Method", "Band", "Rows", "Flights", "Coverage (%) [95% CI]", "Mean width (min)"],
                 rows)


def trust_table_md(r):
    rows = [[METHOD_NAMES[t["method"]], t["window_min"], t["n_flights"], f1(t["median_min"]),
             f"{f1(t['q1_min'])} to {f1(t['q3_min'])}", pct(t["share_never_trusted"])]
            for t in r["trust"]]
    return table(["Method", "W (min)", "Flights", "Median lead (min)", "Quartiles (min)",
                  "Never trusted (%)"], rows)


def split_table(r):
    rows = []
    names = {"traffic_tercile": "Traffic tercile", "direction": "Landing direction",
             "holding": "Holding"}
    for k, items in r["splits_w5"].items():
        for it in items:
            rows.append([names[k], it["group"], it["n_flights"], f1(it["median_min"]),
                         pct(it["share_never_trusted"])])
    return table(["Split", "Group", "Flights", "Median lead (min)", "Never trusted (%)"], rows)


def ablation_table(r):
    rows = [[a["ablation"], f"{pct(a['coverage'])} [{pct(a['coverage_lo'])}, {pct(a['coverage_hi'])}]",
             f1(a["width_min"]), f"{f1(a['median_lead_min'])} [{f1(a['median_lead_lo'])}, "
             f"{f1(a['median_lead_hi'])}]", pct(a["share_never_trusted"])] for a in r["ablations"]]
    return table(["Variant", "Coverage (%) [95% CI]", "Mean width (min)",
                  "Median lead (min) [95% CI]", "Never trusted (%)"], rows)


def shap_table(r):
    return table(["Feature", "Mean abs width contribution (min)"],
                 [[s["feature"], f"{s['mean_abs_width_contribution_min']:.2f}"]
                  for s in r["shap_width"]])


def split_text(r):
    s = r["splits"]
    spans = "; ".join(f"{k.capitalize()}: {s[k]['flights']} flights landing "
                      f"{span_text(s[k]['first_touchdown_utc'], s[k]['last_touchdown_utc'])}"
                      for k in ("train", "calibration", "test"))
    if s["scheme"] == "time_block":
        m = r["config"]["method"]
        rule = (f"Fewer than {m['min_split_days']} local days had {m['min_arrivals_per_day']} or "
                f"more arrivals, so flights were sorted by touchdown time and split into blocks: "
                f"first {pct(m['train_frac'])} percent train, next {pct(m['cal_frac'])} percent "
                "calibration, the rest test.")
    else:
        rule = (f"Split by local day: test day {s['test_day']}, calibration day "
                f"{s['calibration_day']}, earlier days train.")
    return f"{rule} {spans}."


def hyp_list(r):
    return "\n".join(f"* {h['summary']}" for h in r["hypotheses"].values())


def key_numbers(r):
    trust = {(t["method"], t["window_min"]): t for t in r["trust"]}
    w = r["config"]["main_window_min"]
    return trust[("model_calibrated", w)], trust[("baseline_b_calibrated", w)], r["paired_w5"]


def baseline_facts(r):
    cfg = r["config"]
    trust = {(t["method"], t["window_min"]): t for t in r["trust"]}
    cov = {(c["method"], c["band"]): c for c in r["coverage"]}
    wmax = max(cfg["windows_min"])
    allb = next(x for x in r["diagnostics"]["scores"] if x["band"] == "all")
    return {"w": cfg["main_window_min"], "wmax": wmax,
            "model_w": trust[("model_calibrated", cfg["main_window_min"])],
            "base_w": trust[("baseline_b_calibrated", cfg["main_window_min"])],
            "model_wmax": trust[("model_calibrated", wmax)],
            "base_wmax": trust[("baseline_b_calibrated", wmax)],
            "base_width": cov[("baseline_b_calibrated", "all")]["width_min"],
            "model_cov": cov[("model_calibrated", "all")]["coverage"],
            "base_cov": cov[("baseline_b_calibrated", "all")]["coverage"],
            "is_model": allb["is_model"], "is_base": allb["is_base"],
            "target": num(cfg["coverage_target_pct"]), "alpha": cfg["alpha"]}


def headline_text(r):
    b = baseline_facts(r)
    return (f"On the {r['counts']['test_flights']} test flights, the landing time became trustworthy "
            f"within {a_an(b['w'])} {b['w']} minute window a median of {f1(b['model_w']['median_min'])} "
            "minutes before touchdown.")


def baseline_note(r, short=False):
    """Why baseline B gets zero at the main window, and the like for like checks."""
    b = baseline_facts(r)
    w, wm = b["w"], b["wmax"]
    first = []
    if b["base_width"] > w and b["base_w"]["share_never_trusted"] == 1:
        first = [f"Baseline B's intervals average {f1(b['base_width'])} minutes wide, so they can "
                 f"never fit {a_an(w)} {w} minute window. Its zero lead at W = {w} comes from that "
                 "width, not from a wrong guess."]
    w10 = (f"at W = {wm}, where the baseline can qualify, the model's median lead is "
           f"{f1(b['model_wmax']['median_min'])} minutes against {f1(b['base_wmax']['median_min'])}")
    score = (f"The interval score, which adds width and a penalty for every miss, is "
             f"{f1(b['is_model'])} minutes for the model and {f1(b['is_base'])} for the baseline.")
    if short:
        return (f"At W = {wm}, where baseline B can qualify, the model's median lead is "
                f"{f1(b['model_wmax']['median_min'])} minutes against "
                f"{f1(b['base_wmax']['median_min'])}. {score}")
    narrow = "too narrow" if b["model_cov"] < 1 - b["alpha"] else "wide enough"
    rest = [f"Two fairer checks: {w10}, and the baseline is never trusted on "
            f"{pct(b['base_wmax']['share_never_trusted'])} percent of flights.", score,
            f"The model's own intervals are {narrow} on test: they hold the truth "
            f"{pct(b['model_cov'])} percent of the time against {a_an(b['target'])} {b['target']} "
            f"percent target. Baseline B holds it {pct(b['base_cov'])} percent of the time."]
    return " ".join(["A note on the baseline."] + first + rest)


def limitations(r):
    c, m = r["counts"], r["config"]["method"]
    lm = r["label_methods"]
    est = lm.get("ground_extrapolated", 0) + lm.get("fallback_extrapolated", 0)
    wmin = min(r["config"]["windows_min"])
    return [
        f"One evening of data. The {c['test_flights']} test flights come from the later part of one evening.",
        "Train, calibration and test are time blocks from the same evening, not separate days.",
        "OpenSky depends on volunteer receivers, so coverage near the ground at Frankfurt has gaps.",
        f"Touchdown is estimated from ADS-B, not taken from an official landing time. {est} of "
        f"{c['arrivals_kept']} touchdowns were estimated across a gap in the reports, not seen "
        f"between two reports under {secs_text(m['midpoint_max_gap_s'])} apart. That error can "
        f"reach {num(m['extrap_cap_s'] / 60)} minutes, so read the W = {wmin} results with care.",
        "The traffic features treat other aircraft as known arrivals, the way a flight plan would.",
        "Conformal coverage holds on average over rows, not for every single flight.",
    ]


def figures_md(r, prefix):
    figs = [("trust_lead.png", "Trust lead per flight for each window"),
            ("coverage.png", "Coverage by distance band"),
            ("width.png", "Mean interval width by distance"),
            ("error_by_horizon.png", "Point error at fixed distances"),
            ("shap_width.png", "Features that drive interval width"),
            ("paired_lead.png", "Trust lead per test flight, model against baseline B"),
            ("interval_score.png", "Interval score by distance band"),
            ("reliability.png", "Quantile reliability"),
            ("coverage_drift.png", "Calibrated coverage per flight over the evening"),
            ("data_overview.png", "Arrivals per hour by split"),
            ("tracks.png", "Arrival tracks by split")]
    figs += [(os.path.basename(e["figure"]), f"Example flight ({e['role']} lead)")
             for e in r["examples"]]
    return "\n\n".join(f"![{t}]({prefix}{f})" for f, t in figs)


SPLIT_NAMES = {"train": "Train", "calibration": "Calibration", "test": "Test"}
VERSUS = {"baseline_a": "Baseline A", "baseline_b": "Baseline B (P50)"}


def ci(x, lo, hi, fmt=None):
    fmt = fmt or f1
    return f"{fmt(x)} ({fmt(lo)} to {fmt(hi)})"


def scores_table(r):
    sc = r["diagnostics"]["scores"]
    return table(["Band", "Flights", "Interval score, model (min)", "Interval score, baseline B (min)",
                  "Difference (95% CI)", "Pinball loss difference (95% CI)"],
                 [[x["band"], x["n_flights"], f1(x["is_model"]), f1(x["is_base"]),
                   ci(x["is_diff"], x["is_diff_lo"], x["is_diff_hi"]),
                   ci(x["pb_diff"], x["pb_diff_lo"], x["pb_diff_hi"], lambda v: f"{v:.2f}")]
                  for x in sc])


def paired_error_table(r):
    return table(["Distance", "Versus", "Flights", "Model minus baseline, mean abs error (min, 95% CI)",
                  "Flights where model is closer (%)"],
                 [[f"{x['horizon_nm']} nm", VERSUS[x["versus"]], x["n_flights"],
                   ci(x["mean_abs_error_diff_min"], x["ci_lo"], x["ci_hi"]),
                   pct(x["share_model_better"])] for x in r["diagnostics"]["paired_point_error"]])


def reliability_table(r):
    rel = r["diagnostics"]["reliability"]
    return table(["Method", "Nominal quantile", "Share of rows below (%)", "95% CI"],
                 [[METHOD_NAMES.get(x["method"], x["method"]), num(x["nominal"]), pct(x["observed"]),
                   f"{pct(x['ci_lo'])} to {pct(x['ci_hi'])}"] for x in rel])


def drift_table(r):
    return table(["Split", "Flights", "Calibrated coverage (%)", "95% CI", "Mean width (min)"],
                 [[SPLIT_NAMES[x["split"]], x["n_flights"], pct(x["coverage"]),
                   f"{pct(x['coverage_lo'])} to {pct(x['coverage_hi'])}", f1(x["width_min"])]
                  for x in r["diagnostics"]["drift"]])


def further_text(r):
    dg = r["diagnostics"]
    sup = dg["superiority_w5"]
    allb = next(x for x in dg["scores"] if x["band"] == "all")
    dr = {x["split"]: x for x in dg["drift"]}
    w = sup["window_min"]
    parts = [
        f"**Who wins per flight.** At W = {w} minutes the model gave a longer trust lead than "
        f"baseline B on {pct(sup['share_model_longer'])} percent of test flights, a tie on "
        f"{pct(sup['share_tie'])} percent and a shorter lead on {pct(sup['share_baseline_longer'])} "
        f"percent. The mean gain was {ci(sup['mean_diff_min'], sup['mean_ci_lo'], sup['mean_ci_hi'])} "
        "minutes.",
        f"**Interval score.** The interval score adds the width of the interval and a penalty for "
        f"each miss, so lower is better and a narrow interval cannot win by missing. Over all "
        f"test rows the model scored {f1(allb['is_model'])} minutes against "
        f"{f1(allb['is_base'])} for baseline B, a difference of "
        f"{ci(allb['is_diff'], allb['is_diff_lo'], allb['is_diff_hi'])} minutes.",
        f"**Calibration drift.** The intervals are too narrow on the test flights. Calibration "
        f"reached {pct(dr['calibration']['coverage'])} percent on the calibration flights, which the "
        f"method guarantees, but only {pct(dr['test']['coverage'])} percent (95% CI "
        f"{pct(dr['test']['coverage_lo'])} to {pct(dr['test']['coverage_hi'])}) on the test flights, "
        f"which landed later in the evening. On its own training flights the model covers "
        f"{pct(dr['train']['coverage'])} percent, so it fits those flights much tighter than new ones. "
        "This gap is why H1 fails. Splitting by whole days, once more data is in, is the fix.",
    ]
    return "\n\n".join(parts)


def further_section(r, prefix, level="###"):
    return f"""{further_text(r)}

{level} Interval score and pinball loss, model minus baseline B (negative favours the model)

{scores_table(r)}

{level} Paired point error at fixed distances

{paired_error_table(r)}

{level} Quantile reliability

{reliability_table(r)}

{level} Calibration drift across the evening

{drift_table(r)}

![Trust lead per test flight]({prefix}paired_lead.png)

![Interval score by band]({prefix}interval_score.png)

![Quantile reliability]({prefix}reliability.png)

![Calibrated coverage per flight]({prefix}coverage_drift.png)"""


def method_steps(r):
    cfg, m = r["config"], r["config"]["method"]
    q = ", ".join(num(x) for x in m["quantiles"])
    return "\n".join([
        f"1. Collect OpenSky state vectors around Frankfurt with `collect_live.py`.",
        f"2. Split tracks into flights after gaps over {num(m['flight_gap_min'])} minutes. Keep "
        f"arrivals seen beyond {num(m['arrival_start_nm'])} nm that touch down within "
        f"{num(m['ground_nm'])} nm of the airport.",
        "3. Label touchdown from the first ground report, or extrapolate from the last airborne "
        "point when the gap is long or there is no ground report.",
        f"4. Build features from data at or before each prediction time: position, speed, "
        f"altitude changes, turning, recent landing direction and traffic.",
        f"5. Train LightGBM quantile models ({q}) on the train flights.",
        f"6. Calibrate with conformalized quantile regression on the calibration flights, per "
        f"distance band, to {num(cfg['coverage_target_pct'])} percent target coverage.",
        f"7. On the test flights, find the trust point for W = "
        f"{', '.join(str(w) for w in cfg['windows_min'])} minutes and compare with baseline B "
        f"(quantiles of time to touchdown by {num(m['baseline_b_bin_nm'])} nm distance bin and "
        "landing direction).",
    ])


RELATED = [
    "DFS Aviation Services, Arrival Manager (AMAN). https://dfs-as.aero/download/12107",
    "FlightAware Foresight. https://flightaware.com/commercial/foresight",
    "Glina, Jordan and Ishutkina (2012), MIT Lincoln Laboratory: quantile regression forests for "
    "landing times at Dallas/Fort Worth. https://www.ll.mit.edu/r-d/publications/tree-based-ensemble-method-prediction-and-uncertainty-quantification-aircraft",
    "Kim, Yoon and Lee (2025), Probabilistic Multi-Agent Aircraft Landing Time Prediction, "
    "arXiv 2512.08281. https://arxiv.org/abs/2512.08281",
    "Romano, Patterson and Candès (2019), Conformalized Quantile Regression, NeurIPS. "
    "https://arxiv.org/abs/1905.03222",
    "Schäfer et al. (2014), Bringing Up OpenSky, IPSN. https://doi.org/10.1109/IPSN.2014.6846743",
]

OPENSKY_CITATION = ("Matthias Schäfer, Martin Strohmeier, Vincent Lenders, Ivan Martinovic and "
                    "Matthias Wilhelm. Bringing Up OpenSky: A Large-scale ADS-B Sensor Network "
                    "for Research. In Proceedings of the 13th IEEE/ACM International Symposium "
                    "on Information Processing in Sensor Networks (IPSN), pages 83 to 94, April 2014.")


STATUS = {"supported": "**Supported**", "not supported": "**Not supported**", "unclear": "Unclear"}
DROP_NAMES = {"not_arrival_no_touchdown": "No touchdown seen (departures, overflights)",
              "too_few_points": "Too few position reports",
              "not_arrival_never_airborne_beyond_30nm": "Never seen far enough out",
              "gap_over_120s_inside_20nm": "Track gap close to the airport",
              "no_airborne_point_before_ground": "No airborne report before the ground report",
              "fallback_rejected_flew_away": "Low pass that flew away again"}
LABEL_NAMES = {"ground_midpoint": "Midpoint between last airborne and first ground report",
               "ground_extrapolated": "Extrapolated from last airborne report to first ground report",
               "fallback_extrapolated": "No ground report: extrapolated from last low report"}
FIG = "results/figures/"


def pair_img(a, b, alt_a, alt_b):
    return (f'<p align="center">\n  <img src="{FIG}{a}" alt="{alt_a}" width="49%">\n'
            f'  <img src="{FIG}{b}" alt="{alt_b}" width="49%">\n</p>')


def details(summary, body):
    return f"<details>\n<summary>{summary}</summary>\n\n{body}\n\n</details>"


def hypothesis_table(r):
    cfg, h = r["config"], r["hypotheses"]
    w = cfg["main_window_min"]
    text = {
        "H1": f"Conformal calibration brings coverage within {num(cfg['h1_tolerance_points'])} "
              f"points of {num(cfg['coverage_target_pct'])} percent in every distance band.",
        "H2": f"At W = {w} min, the model gives a longer trust lead than baseline B.",
        "H3": "Trust lead is shorter in busy traffic than in quiet traffic.",
        "H4": "Flights that hold have a shorter trust lead.",
    }
    rows = [[k, text[k], STATUS[v["status"]], v["summary"].split(". ", 1)[1] if ". " in v["summary"]
             else v["summary"]] for k, v in h.items()]
    return table(["", "Hypothesis", "Result", "Evidence"], rows)


def bold_best(vals, fmt, lower=True):
    """Format values and bold the best one, so emphasis follows the data."""
    ok = [v for v in vals if v is not None]
    best = (min(ok) if lower else max(ok)) if ok else None
    return [(f"**{fmt(v)}**" if v is not None and v == best and len(ok) > 1 else fmt(v))
            if v is not None else "no interval" for v in vals]


def glance_table(r):
    model, base, pair = key_numbers(r)
    b = baseline_facts(r)
    w, wm = b["w"], b["wmax"]
    dg = r["diagnostics"]
    acc = {(a["horizon_nm"], a["method"]): a for a in r["point_accuracy"]}
    hs = sorted({a["horizon_nm"] for a in r["point_accuracy"]})
    h = hs[len(hs) // 2]
    allb = next(x for x in dg["scores"] if x["band"] == "all")
    cov = next(c for c in r["coverage"] if c["method"] == "model_calibrated" and c["band"] == "all")
    bcov = next(c for c in r["coverage"] if c["method"] == "baseline_b_calibrated" and c["band"] == "all")
    mae = lambda k: None if acc[(h, k)]["mae_s"] is None else acc[(h, k)]["mae_s"] / 60
    mins = lambda v: f"{f1(v)} min"
    pcts = lambda v: f"{pct(v)}%"
    target = 1 - r["config"]["alpha"]
    gap = [abs(cov["coverage"] - target), abs(bcov["coverage"] - target)]
    cov_cells = [pcts(cov["coverage"]), pcts(bcov["coverage"])]
    cov_cells[gap.index(min(gap))] = f"**{cov_cells[gap.index(min(gap))]}**"
    rows = table(["Measure", "Model", "Baseline B", "Baseline A"], [
        [f"Median trust lead at W = {w} min (higher is better)",
         *bold_best([model["median_min"], base["median_min"], None], mins, lower=False)],
        [f"Median trust lead at W = {wm} min (higher is better)",
         *bold_best([b["model_wmax"]["median_min"], b["base_wmax"]["median_min"], None], mins,
                    lower=False)],
        [f"Test flights never trusted at W = {w} min",
         *bold_best([model["share_never_trusted"], base["share_never_trusted"], None], pcts)],
        [f"Mean absolute error at {h} nm out",
         *bold_best([mae("model"), mae("baseline_b"), mae("baseline_a")], mins)],
        ["Interval score, all test rows (lower is better)",
         *bold_best([allb["is_model"], allb["is_base"], None], mins)],
        [f"Interval coverage on test (target {num(r['config']['coverage_target_pct'])}%)",
         *cov_cells, "no interval"],
        ["Mean interval width on test", *bold_best([cov["width_min"], bcov["width_min"], None], mins)],
    ])
    note = (f"Baseline B's intervals are wider than {w} minutes, so the W = {wm} row and the interval "
            "score are the like for like comparisons." if b["base_width"] > w else
            "Bold marks the better value in each row.")
    return rows + "\n\n" + note


def data_table(r):
    rows = [[DROP_NAMES.get(k, k), v] for k, v in r["drop_reasons"].items()]
    return table(["Why a track was dropped", "Tracks"], rows)


def label_table(r):
    return table(["How touchdown was labelled", "Arrivals"],
                 [[LABEL_NAMES.get(k, k), v] for k, v in r["label_methods"].items()])


def not_held(r):
    bad = [k for k, h in r["hypotheses"].items() if h["status"] == "not supported"]
    if not bad:
        return "No hypothesis was rejected. I report every result as it came out."
    names = " and ".join([", ".join(bad[:-1]), bad[-1]] if len(bad) > 1 else bad)
    return f"{names} did not hold. I report them as they came out."


def readme(r):
    d, c, cfg = r["data_window"], r["counts"], r["config"]
    model, base, pair = key_numbers(r)
    w = cfg["main_window_min"]
    ex = r["examples"]
    ex_imgs = "\n".join(f'  <img src="{FIG}{os.path.basename(e["figure"])}" '
                        f'alt="Example flight, {e["role"]} lead" width="{"80%" if i == 0 else "49%"}">'
                        + ("\n</p>\n<p align=\"center\">" if i == 0 and len(ex) > 1 else "")
                        for i, e in enumerate(ex))
    windows = ", ".join(str(x) for x in cfg["windows_min"][:-1]) + f" and {cfg['windows_min'][-1]}"
    return f"""# Glidepath

How early can a ground team at Frankfurt trust a landing time?

{AUTHOR_LINE}

<p>
  <img src="https://img.shields.io/badge/python-3776AB?logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/data-OpenSky%20ADS--B-eb6834" alt="OpenSky ADS-B data">
  <img src="https://img.shields.io/badge/license-MIT-52514e" alt="MIT license">
</p>

{notice(r)}

> ### {headline_text(r)}

{baseline_note(r)}

[Research note](docs/research_note.md) · [One page summary](docs/summary.md) · [Research plan](docs/research_plan.md) · [Related work](docs/related_work.md)

<p align="center">
  <img src="{FIG}paired_lead.png" alt="Trust lead per test flight, model against baseline B" width="70%">
</p>

## The question

Under A-CDM, the estimated landing time feeds stand planning, ground handling and the next departure. A ramp team needs more than a good estimate on average. It needs to know when the estimate has settled enough to act on.

I predict the time to touchdown with {a_an(num(cfg['coverage_target_pct']))} {num(cfg['coverage_target_pct'])} percent interval and look at how each flight's interval behaves as it gets closer:

* Trust point: the first prediction after which every interval is no wider than W minutes and still contains the real touchdown time.
* Trust lead: the minutes from the trust point to touchdown. A flight that never reaches a trust point gets zero.

I use W = {windows} minutes. W = {w} is the main case.

## Results at a glance

{glance_table(r)}

### Hypotheses

{hypothesis_table(r)}

{not_held(r)} The full rules are in the [research plan](docs/research_plan.md).

## 1. Trust lead

<p align="center">
  <img src="{FIG}trust_lead.png" alt="Trust lead per flight for each window" width="100%">
</p>

Each curve shows the share of test flights trusted at or before a given lead, for each window W. Further right is better. The plot at the top of this page pairs each test flight: blue is the model, orange is baseline B.

{details('Trust lead table', trust_table_md(r))}

## 2. Point accuracy

{pair_img('error_by_horizon.png', 'width.png', 'Point error at fixed distances', 'Interval width by distance')}

{accuracy_table(r)}

{details('Paired point error per flight, with bootstrap intervals', paired_error_table(r))}

## 3. Calibrated intervals

{pair_img('coverage.png', 'reliability.png', 'Coverage by distance band', 'Quantile reliability')}

{further_text(r)}

{pair_img('coverage_drift.png', 'interval_score.png', 'Coverage per flight over the evening', 'Interval score by band')}

{details('Coverage and width by band', coverage_table(r))}

{details('Interval score and pinball loss by band', scores_table(r))}

{details('Quantile reliability table', reliability_table(r))}

{details('Coverage per split', drift_table(r))}

## 4. What drives the interval

<p align="center">
  <img src="{FIG}shap_width.png" alt="Features that drive interval width" width="70%">
</p>

{details('Width attribution table (SHAP)', shap_table(r))}

{details(f'Ablations at W = {w} min', ablation_table(r))}

{details(f'Trust lead by traffic, runway direction and holding at W = {w} min', split_table(r))}

## 5. Example flights

The band is the calibrated interval minus the true time. The dashed line is the trust point.

<p align="center">
{ex_imgs}
</p>

## Data

<p align="center">
  <img src="{FIG}tracks.png" alt="Arrival tracks by split" width="55%">
</p>

<p align="center">
  <img src="{FIG}data_overview.png" alt="Arrivals per hour by split" width="90%">
</p>

* Source: OpenSky Network state vectors in a box around Frankfurt, polled live.
* Window: {window_text(r)}. {d['raw_rows']} state vectors from {d['aircraft']} aircraft.
* Flights: {c['flights_total']} tracks, {c['arrivals_kept']} arrivals kept, {c['rows']} prediction rows, {c['go_arounds']} go-arounds.
* Split: {split_text(r)}

{details('Why tracks were dropped, and how touchdown was labelled', data_table(r) + chr(10) + chr(10) + label_table(r))}

## Method

```mermaid
flowchart LR
  A[OpenSky API<br/>collect_live.py] --> B[Clean and split<br/>into flights]
  B --> C[Label touchdown<br/>from ADS-B]
  C --> D[Features at time t<br/>no look-ahead]
  D --> E[LightGBM quantiles<br/>train flights]
  E --> F[Conformal calibration<br/>calibration flights]
  F --> G[Trust point and lead<br/>test flights]
  G --> H[results.json<br/>docs, figures, site]
```

{method_steps(r)}

Baselines: Baseline A is distance divided by ground speed, a point estimate. Baseline B is the empirical quantiles of time to touchdown by distance bin and landing direction, calibrated the same way as the model.

Statistics: every interval resamples whole test flights ({cfg['n_boot']} bootstrap draws), because rows inside a flight are not independent. The paired test is a Wilcoxon signed-rank test.

## Limitations

{chr(10).join('* ' + x for x in limitations(r))}

## Run it yourself

```bash
make install              # create .venv and install packages
make test                 # unit tests
make results-synthetic    # SYNTHETIC TEST run of the full pipeline, no API needed
make status               # what the collector has saved so far
make results              # rebuild everything from the live data in data/raw/live
make docs                 # rebuild README and docs from results/results.json only
make serve                # replay site on your own machine at localhost:8000
```

The collector needs an OpenSky API client in `credentials.json`, which is never committed:

```bash
GLIDEPATH_POLL_SECONDS=30 nohup systemd-inhibit --what=idle:sleep --why=glidepath python3 collect_live.py >> collector.log 2>&1 &
```

## Repository

```
collect_live.py        OpenSky collector, standard library only
run.py                 one command from raw CSVs to results, figures, docs and site data
pipeline/              data, features, splits, models, trust, evaluation, diagnostics, figures, docs
tests/                 leakage, split, trust, conformal and scoring tests
results/               results.json, tables and figures
docs/                  research note, summary, research plan, related work
web/                   static replay site (MapLibre)
```

## Related work

{chr(10).join('* ' + x for x in RELATED)}

More in [docs/related_work.md](docs/related_work.md) and [references.bib](references.bib).

## Data source and citation

Data from [The OpenSky Network](https://opensky-network.org). If you use this work, please cite:

> {OPENSKY_CITATION}

## License

MIT, see [LICENSE](LICENSE).

<sub>All numbers in this README come from results/results.json. Run make results to rebuild it from the raw data. {NOT_OPERATIONAL}</sub>
"""


def discussion(r):
    model, base, pair = key_numbers(r)
    h = r["hypotheses"]
    w = r["config"]["main_window_min"]
    parts = []
    if h["H2"]["status"] == "supported":
        parts.append(f"At W = {w} minutes the model gave a longer trust lead than baseline B, and "
                     "the bootstrap interval of the paired difference lies above zero.")
    elif h["H2"]["status"] == "not supported":
        parts.append(f"At W = {w} minutes the model did not give a longer trust lead than baseline "
                     f"B. The median paired difference was {f1(pair['median_diff_min'])} minutes. "
                     "This is a negative result for the main claim, and I report it as such.")
    else:
        parts.append(f"At W = {w} minutes the median paired difference was "
                     f"{f1(pair['median_diff_min'])} minutes, but its bootstrap interval includes "
                     "zero. With this sample I cannot tell the model and baseline B apart.")
    parts.append(baseline_note(r, short=True))
    parts.append(f"{pct(model['share_never_trusted'])} percent of test flights were never trusted by "
                 f"the calibrated model at W = {w} minutes, against "
                 f"{pct(base['share_never_trusted'])} percent for baseline B. The trust point is "
                 "strict. One late miss resets it, and an interval built to miss a share of rows "
                 "will often miss close to touchdown.")
    if h["H1"]["status"] == "supported":
        parts.append("Calibration brought coverage close to the target in every band with enough "
                     "test rows, while raw quantiles missed in at least one band.")
    else:
        parts.append(f"H1 is {h['H1']['status']}. Calibration on one block of the evening does not "
                     "guarantee coverage on the next block when traffic changes.")
    parts.append("H3 and H4 rest on small groups in a pilot of one evening. Read their results "
                 f"({h['H3']['status']} and {h['H4']['status']}) as a first look.")
    return "\n\n".join(parts)


def data_source(r):
    if r["synthetic"]:
        return (f"SYNTHETIC TEST: the data come from `pipeline/synthetic.py`, simulated in the "
                f"collector format for {window_text(r)}.")
    return (f"I polled the OpenSky Network REST API for state vectors around Frankfurt on "
            f"{window_text(r)}.")


def research_note(r):
    d, c, cfg = r["data_window"], r["counts"], r["config"]
    model, base, pair = key_numbers(r)
    b = baseline_facts(r)
    w = cfg["main_window_min"]
    title = "How early can a ground team trust a landing time? A pilot study at Frankfurt"
    if r["synthetic"]:
        title = "SYNTHETIC TEST: " + title
    month = local_dt(d["first_utc"])
    narrow = ("below target, which points to drift within the evening" if b["model_cov"] < 1 - b["alpha"]
              else "on target")
    cant = (f" An empirical baseline could not qualify at that window because its intervals were wider "
            f"than {w} minutes; at W = {b['wmax']} its median lead was {f1(b['base_wmax']['median_min'])} "
            "minutes." if b["base_width"] > w else
            f" An empirical baseline had a median trust lead of {f1(base['median_min'])} minutes.")
    return f"""# {title}

{AUTHOR}, {AFFILIATION}, Berlin. {month:%B %Y}.

{notice(r)}

## Abstract

Ground teams at A-CDM airports plan stands and handling around the estimated landing time. They need to know when that estimate can be trusted, not only how accurate it is on average. I study this for arrivals at Frankfurt (EDDF) using open ADS-B data from the OpenSky Network. LightGBM quantile models predict the time to touchdown, and conformalized quantile regression calibrates the interval per distance band to {num(cfg['coverage_target_pct'])} percent target coverage. For each flight I define a trust point: the first prediction after which every interval is no wider than a window W and contains the true touchdown. On {f1(d['hours'])} hours of live data, the {c['test_flights']} held out test flights had a median trust lead of {f1(model['median_min'])} minutes at W = {w}.{cant} The model's test coverage was {pct(b['model_cov'])} percent, {narrow}. This is a pilot, and data collection continues.

## 1. Introduction

In Airport Collaborative Decision Making (A-CDM), the estimated landing time (ELDT) feeds the estimated in-block time, stand and gate planning, and the target off-block time of the next departure. The EUROCONTROL A-CDM manual names both the accuracy and the timeliness of ELDT as performance indicators. A ground team needs both at once. An estimate that is right on average but still moves in the last minutes forces late decisions.

I ask how early a ground team at Frankfurt can trust a landing time. I answer with a prediction interval and a trust point for each flight. Earlier work predicts landing time well (for example DFS AMAN, FlightAware Foresight, and research models at Dallas/Fort Worth and Incheon), and some work gives intervals (Glina et al. 2012, Kim, Yoon and Lee 2025). I did not find a study that measures when the interval for one flight becomes both narrow and correct. The full review is in `docs/related_work.md`.

## 2. Data

{data_source(r)} This gave {d['raw_rows']} state vectors from {d['aircraft']} aircraft. I split the tracks into {c['flights_total']} flights and kept {c['arrivals_kept']} arrivals.

{data_table(r)}

{label_table(r)}

Landing directions: {', '.join(f'{k} {v}' for k, v in c['directions'].items())}.

{split_text(r)}

## 3. Method

{method_steps(r)}

Baselines: Baseline A divides distance by ground speed. Baseline B takes empirical quantiles of time to touchdown in training, by distance bin and recent landing direction, and gets the same conformal correction as the model.

Further statistics: the interval score and the pinball loss are proper scores [gneiting2007strictly], so they reward intervals that are both narrow and correct. I also report paired point error per flight, quantile reliability and coverage per split.

Statistics: every interval comes from {cfg['n_boot']} bootstrap resamples of whole test flights, because rows inside a flight are not independent. The paired comparison uses a Wilcoxon signed-rank test.

## 4. Results

{headline_text(r)}

{baseline_note(r)}

{trust_table_md(r)}

![Trust lead]({'../results/figures/trust_lead.png'})

{coverage_table(r)}

![Coverage]({'../results/figures/coverage.png'})

{accuracy_table(r)}

{split_table(r)}

{ablation_table(r)}

{shap_table(r)}

Hypotheses:

{hyp_list(r)}

![Width by distance](../results/figures/width.png)

![Point error at fixed distances](../results/figures/error_by_horizon.png)

![Width drivers](../results/figures/shap_width.png)

{chr(10).join(f"![Example flight, {e['role']} lead](../{'results/' + e['figure']})" for e in r['examples'])}

### 4.1 Further statistics

These are exploratory. They explain the hypothesis results and do not change any verdict.

{further_section(r, '../results/figures/', level='####')}

![Arrivals per hour by split](../results/figures/data_overview.png)

![Arrival tracks by split](../results/figures/tracks.png)

## 5. Discussion

{discussion(r)}

## 6. Limitations

{chr(10).join('* ' + x for x in limitations(r))}

## 7. Future work

* Run the collector over many days and split by day, as the pipeline already does once enough days exist.
* Use the OpenSky Trino history to train and test over months.
* Add weather, for example METAR wind, which drives runway choice and approach speed.
* Regularise the quantile model more strongly. Train coverage near one hundred percent shows it fits its own flights too tightly. Any such change must be chosen on train and calibration flights only, never on test.
* Recalibrate on a rolling window of recent flights to follow drift through the evening.
* Repeat the study at more airports.

## References

See `references.bib`.

{NOT_OPERATIONAL}
"""


def summary(r):
    d, c, cfg = r["data_window"], r["counts"], r["config"]
    b = baseline_facts(r)
    month = local_dt(d["first_utc"])
    windows = ", ".join(str(x) for x in cfg["windows_min"][:-1]) + f" and {cfg['windows_min'][-1]}"
    return f"""# Glidepath: when can a ground team trust a landing time?

{AUTHOR}, {AFFILIATION}, {month:%B %Y}

Question: How early can a ground team at Frankfurt (EDDF) trust a predicted landing time?

Why it matters: Under A-CDM, the estimated landing time drives stand planning, ground handling and the next departure. A team needs to know when the estimate stops moving.

What I did: (1) Predicted time to touchdown from open OpenSky ADS-B data with LightGBM quantile models. (2) Calibrated the interval per distance band to {num(cfg['coverage_target_pct'])} percent with conformal prediction. (3) Found each flight's trust point for windows of {windows} minutes.

Result: {headline_text(r)} {baseline_note(r, short=True)}

Limits: one evening of data, {c['test_flights']} test flights, test coverage {pct(b['model_cov'])} percent against the {b['target']} percent target, and touchdown labels estimated from ADS-B.

Next: run over separate days, add weather, and compare with official landing times if I can get them.

Code: {REPO_LINK.replace('https://', '')}

{NOT_OPERATIONAL}
"""


def write_all(r):
    os.makedirs("docs", exist_ok=True)
    with open("README.md", "w") as f:
        f.write(readme(r))
    with open("docs/research_note.md", "w") as f:
        f.write(research_note(r))
    with open("docs/summary.md", "w") as f:
        f.write(summary(r))
