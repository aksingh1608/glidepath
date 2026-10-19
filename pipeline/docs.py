"""README.md, docs/research_note.md and docs/summary.md, generated from results.json.

Every number in these files is read from the results dictionary.
"""

from __future__ import annotations

import os

DEMO_LINK = ""  # set to the Vercel URL once deployed
DEMO_TEXT = DEMO_LINK or "The replay site is in web/. Run make serve to open it locally."
REPO_LINK = "https://github.com/aksingh1608/glidepath"
NOT_OPERATIONAL = "Research demo. Not for operational use."

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


def notice(r):
    d, c = r["data_window"], r["counts"]
    if r["synthetic"]:
        return ("> **SYNTHETIC TEST.** These results come from simulated data made to test the code. "
                "They say nothing about Frankfurt.")
    return (f"> **Pilot study.** One evening of live OpenSky data, {d['first_local']} to "
            f"{d['last_local']} ({f1(d['hours'])} hours). {c['arrivals_kept']} arrivals kept, "
            f"{c['test_flights']} in the held-out test set. The collector keeps running, so later "
            "runs will cover more days.")


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
        return (f"H2 {s}. Median paired difference in trust lead at W = {h['window_min']} min, "
                f"model minus baseline B: {f1(h['median_diff_min'])} min, 95% bootstrap interval "
                f"{f1(h['ci_lo'])} to {f1(h['ci_hi'])} min, {h['n_flights']} flights, "
                f"Wilcoxon p = {p}{extra}.")
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
    spans = "; ".join(f"{k.capitalize()}: {s[k]['flights']} flights, {s[k]['first_touchdown_utc']} to "
                      f"{s[k]['last_touchdown_utc']}" for k in ("train", "calibration", "test"))
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
        f"**Calibration drift.** The conformal step reached {pct(dr['calibration']['coverage'])} "
        f"percent coverage on the calibration flights, as it should by design, but "
        f"{pct(dr['test']['coverage'])} percent (95% CI {pct(dr['test']['coverage_lo'])} to "
        f"{pct(dr['test']['coverage_hi'])}) on the test flights, which landed later in the "
        f"evening. On the train flights coverage was {pct(dr['train']['coverage'])} percent: the "
        "quantile model fits its own training flights much more tightly than new flights. Both "
        "facts point the same way. The gap between calibration and test is the main reason H1 "
        "fails, and more days of data, split by day, is the fix.",
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


LIMITATIONS = [
    "One evening of data. The test set is small and covers one part of one day.",
    "The split is a time block inside the same evening, not separate days.",
    "OpenSky relies on volunteer receivers, so coverage near the ground has gaps.",
    "Touchdown is inferred from ADS-B, not taken from an official landing time, so labels carry noise.",
    "Inbound status of other aircraft is taken as known, like a flight plan, for the traffic features.",
    "Conformal coverage is marginal: it holds on average over rows, not for each flight.",
]

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
    w = r["config"]["main_window_min"]
    dg = r["diagnostics"]
    sup = dg["superiority_w5"]
    acc = {(a["horizon_nm"], a["method"]): a for a in r["point_accuracy"]}
    h = sorted({a["horizon_nm"] for a in r["point_accuracy"]})[len({a["horizon_nm"] for a in r["point_accuracy"]}) // 2]
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
    return table(["Measure", "Model", "Baseline B", "Baseline A"], [
        [f"Median trust lead at W = {w} min (higher is better)",
         *bold_best([model["median_min"], base["median_min"], None], mins, lower=False)],
        [f"Test flights never trusted at W = {w} min",
         *bold_best([model["share_never_trusted"], base["share_never_trusted"], None], pcts)],
        [f"Mean absolute error at {h} nm out",
         *bold_best([mae("model"), mae("baseline_b"), mae("baseline_a")], mins)],
        ["Interval score, all test rows (lower is better)",
         *bold_best([allb["is_model"], allb["is_base"], None], mins)],
        [f"Interval coverage on test (target {num(r['config']['coverage_target_pct'])}%)",
         *cov_cells, "no interval"],
        ["Mean interval width on test", *bold_best([cov["width_min"], bcov["width_min"], None], mins)],
    ]) + (f"\n\nThe model gave the longer trust lead on **{pct(sup['share_model_longer'])}%** of test "
          f"flights and the shorter one on {pct(sup['share_baseline_longer'])}%. Bold marks the "
          "better value in each row.")


def data_table(r):
    rows = [[DROP_NAMES.get(k, k), v] for k, v in r["drop_reasons"].items()]
    return table(["Why a track was dropped", "Tracks"], rows)


def label_table(r):
    return table(["How touchdown was labelled", "Arrivals"],
                 [[LABEL_NAMES.get(k, k), v] for k, v in r["label_methods"].items()])


def readme(r):
    d, c, cfg = r["data_window"], r["counts"], r["config"]
    model, base, pair = key_numbers(r)
    w = cfg["main_window_min"]
    p = "n/a" if pair.get("wilcoxon_p") is None else f"{pair['wilcoxon_p']:.2g}"
    demo = f"**[Live replay]({DEMO_LINK})** · " if DEMO_LINK else ""
    ex = r["examples"]
    ex_imgs = "\n".join(f'  <img src="{FIG}{os.path.basename(e["figure"])}" '
                        f'alt="Example flight, {e["role"]} lead" width="{"80%" if i == 0 else "49%"}">'
                        + ("\n</p>\n<p align=\"center\">" if i == 0 and len(ex) > 1 else "")
                        for i, e in enumerate(ex))
    return f"""<h1 align="center">Glidepath</h1>

<p align="center"><b>How early can a ground team at Frankfurt trust a landing time?</b></p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3776AB?logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/model-LightGBM%20quantile-2a78d6" alt="LightGBM quantile">
  <img src="https://img.shields.io/badge/intervals-conformal%20(CQR)-1baf7a" alt="Conformal">
  <img src="https://img.shields.io/badge/data-OpenSky%20ADS--B-eb6834" alt="OpenSky">
  <img src="https://img.shields.io/badge/status-pilot-eda100" alt="Pilot">
  <img src="https://img.shields.io/badge/license-MIT-52514e" alt="MIT">
</p>

{notice(r)}

> ### {r['headline']}
>
> Baseline B's median trust lead was {f1(base['median_min'])} minutes. Median paired gain {f1(pair['median_diff_min'])} minutes (95% bootstrap interval {f1(pair['ci_lo'])} to {f1(pair['ci_hi'])}), Wilcoxon p = {p}, {pair['n_flights']} flights.

{demo}[Research note](docs/research_note.md) · [One-page summary](docs/summary.md) · [Research plan](docs/research_plan.md) · [Related work](docs/related_work.md)

<p align="center">
  <img src="{FIG}paired_lead.png" alt="Trust lead per test flight, model against baseline B" width="70%">
</p>

## The question

At an A-CDM airport the estimated landing time drives stand allocation, ground handling and the next departure. Accuracy on average is not enough. A ramp team needs to know **from when** the estimate stops moving.

So we predict touchdown with a calibrated interval and measure, for each flight, when that interval becomes both narrow and right:

* **Trust point.** The earliest prediction from which every later interval is no wider than a window W and contains the true touchdown.
* **Trust lead.** Touchdown time minus trust point. A flight that is never trusted gets a lead of zero.

We report W = {', '.join(str(x) for x in cfg['windows_min'])} minutes, with W = {w} minutes as the main case.

## Results at a glance

{glance_table(r)}

### Hypotheses

{hypothesis_table(r)}

We report negative results as they are. Full rules are in the [research plan](docs/research_plan.md).

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

The band is the calibrated interval minus the true time; the dashed line is the trust point.

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

* **Source.** OpenSky Network state vectors in a box around Frankfurt, polled live.
* **Window.** {d['first_local']} to {d['last_local']} ({f1(d['hours'])} hours), {d['raw_rows']} state vectors from {d['aircraft']} aircraft.
* **Flights.** {c['flights_total']} tracks, **{c['arrivals_kept']} arrivals kept**, {c['rows']} prediction rows, {c['go_arounds']} go-arounds.
* **Split.** {split_text(r)}

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

**Baselines.** Baseline A is distance divided by ground speed (a point estimate). Baseline B is the empirical quantiles of time to touchdown by distance bin and landing direction, calibrated the same way as the model.

**Statistics.** All intervals resample whole test flights ({cfg['n_boot']} bootstrap draws), because rows inside a flight are not independent. The paired test is a Wilcoxon signed-rank test.

## Limitations

{chr(10).join('* ' + x for x in LIMITATIONS)}

## Run it yourself

```bash
make install              # create .venv and install packages
make test                 # unit tests
make results-synthetic    # SYNTHETIC TEST run of the full pipeline, no API needed
make status               # what the collector has saved so far
make results              # run on live data in data/raw/live
make serve                # replay site on http://localhost:8000
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
results/               results.json, tables and figures (every number in this README comes from here)
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

MIT, see [LICENSE](LICENSE). {NOT_OPERATIONAL}

<sub>Generated by `run.py` from `results/results.json` on {r['generated_utc']}. No number in this file is typed by hand.</sub>
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
                     "This is a negative result for the main claim, and we report it as such.")
    else:
        parts.append(f"At W = {w} minutes the median paired difference was "
                     f"{f1(pair['median_diff_min'])} minutes, but its bootstrap interval includes "
                     "zero. With this sample we cannot tell the model and baseline B apart.")
    parts.append(f"{pct(model['share_never_trusted'])} percent of test flights were never trusted by "
                 f"the calibrated model at W = {w} minutes, against "
                 f"{pct(base['share_never_trusted'])} percent for baseline B. The trust point is "
                 "strict: one late miss resets it, and an interval built to miss a share of rows "
                 "will often miss close to touchdown.")
    if h["H1"]["status"] == "supported":
        parts.append("Calibration brought coverage close to the target in every band with enough "
                     "test rows, while raw quantiles missed in at least one band.")
    else:
        parts.append(f"H1 is {h['H1']['status']}. Calibration on one block of the evening does not "
                     "guarantee coverage on the next block when traffic changes.")
    parts.append("H3 and H4 depend on small groups in a pilot of one evening. Their verdicts "
                 f"({h['H3']['status']} and {h['H4']['status']}) should be read as a first look.")
    return "\n\n".join(parts)


def data_source(r):
    d = r["data_window"]
    if r["synthetic"]:
        return (f"SYNTHETIC TEST: the data come from `pipeline/synthetic.py`, simulated in the "
                f"collector format for {d['first_local']} to {d['last_local']}.")
    return (f"We polled the OpenSky Network REST API for state vectors around Frankfurt from "
            f"{d['first_local']} to {d['last_local']}.")


def research_note(r):
    d, c, cfg = r["data_window"], r["counts"], r["config"]
    model, base, pair = key_numbers(r)
    w = cfg["main_window_min"]
    title = "How early can a ground team trust a landing time? A pilot study at Frankfurt"
    if r["synthetic"]:
        title = "SYNTHETIC TEST: " + title
    return f"""# {title}

{notice(r)}

*Generated by `run.py` from `results/results.json`. {NOT_OPERATIONAL}*

## Abstract

Ground teams at an A-CDM airport plan stands and handling around the estimated landing time. They need to know from when that estimate can be trusted, not only how accurate it is on average. We study this for arrivals at Frankfurt (EDDF) with open OpenSky ADS-B data. A LightGBM quantile model predicts time to touchdown, and conformalized quantile regression calibrates the interval per distance band to {num(cfg['coverage_target_pct'])} percent target coverage. For each flight we define the trust point as the earliest prediction from which every later interval is no wider than a window W and contains the true touchdown. In this pilot of {f1(d['hours'])} hours of live data, {c['test_flights']} held-out test flights had a median trust lead of {f1(model['median_min'])} minutes at W = {w} minutes, against {f1(base['median_min'])} minutes for an empirical baseline. The median paired difference was {f1(pair['median_diff_min'])} minutes (95% interval {f1(pair['ci_lo'])} to {f1(pair['ci_hi'])}). The study is small and grows as the collector keeps running.

## 1. Introduction

In Airport Collaborative Decision Making (A-CDM), the estimated landing time (ELDT) feeds the estimated in-block time, stand and gate planning, and the target off-block time of the next departure. The EUROCONTROL A-CDM manual names both the accuracy and the timeliness of ELDT as performance indicators. A ground team needs both at once: an estimate that is accurate on average but still moves in the last minutes forces late decisions.

We ask how early a ground team at Frankfurt can trust a landing time. We answer with a prediction interval and a per-flight trust point. Earlier work predicts landing time well (for example DFS AMAN, FlightAware Foresight, and research models at Dallas/Fort Worth and Incheon) and some work gives intervals (Glina et al. 2012, Kim, Yoon and Lee 2025). We did not find a study that measures when the interval for one flight becomes both narrow and correct. The full review is in `docs/related_work.md`.

## 2. Data

{data_source(r)} This gave {d['raw_rows']} state vectors from {d['aircraft']} aircraft. We split tracks into {c['flights_total']} flights and kept {c['arrivals_kept']} arrivals.

Drop reasons: {', '.join(f'{k} {v}' for k, v in r['drop_reasons'].items())}. Label methods: {', '.join(f'{k} {v}' for k, v in r['label_methods'].items())}. Landing directions: {', '.join(f'{k} {v}' for k, v in c['directions'].items())}.

{split_text(r)}

## 3. Method

{method_steps(r)}

**Baselines.** Baseline A divides distance by ground speed. Baseline B takes empirical quantiles of time to touchdown in training, by distance bin and recent landing direction, and gets the same conformal correction as the model.

**Further statistics.** The interval score and the pinball loss are proper scores [gneiting2007strictly], so they reward intervals that are both narrow and correct. We also report paired point error per flight, quantile reliability and coverage per split.

**Statistics.** All intervals come from {cfg['n_boot']} bootstrap resamples of whole test flights, because rows inside a flight are not independent. The paired comparison uses a Wilcoxon signed-rank test.

## 4. Results

{trust_table_md(r)}

![Trust lead]({'../results/figures/trust_lead.png'})

{coverage_table(r)}

![Coverage]({'../results/figures/coverage.png'})

{accuracy_table(r)}

{split_table(r)}

{ablation_table(r)}

{shap_table(r)}

**Hypotheses.**

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

{chr(10).join('* ' + x for x in LIMITATIONS)}

## 7. Future work

* Run the collector over many days and split by day, as the pipeline already does once enough days exist.
* Use the OpenSky Trino history to train and test over months.
* Add weather, for example METAR wind, which drives runway choice and approach speed.
* Regularise the quantile model more strongly. Train coverage near one hundred percent shows it fits its own flights too tightly. Any such change must be chosen on train and calibration flights only, never on test.
* Recalibrate on a rolling window of recent flights to follow drift through the evening.
* Repeat the study at more airports.

## References

See `references.bib`.
"""


def summary(r):
    d, c, cfg = r["data_window"], r["counts"], r["config"]
    model, base, pair = key_numbers(r)
    w = cfg["main_window_min"]
    h2 = r["hypotheses"]["H2"]["status"]
    verdict = {"supported": "The model beat baseline B on this measure.",
               "not supported": "The model did not beat baseline B on this measure.",
               "unclear": "The model and baseline B could not be told apart on this sample."}[h2]
    return f"""# Glidepath: how early can a ground team trust a landing time?

{notice(r)}

**Question.** How early can a ground team at Frankfurt (EDDF) trust a predicted landing time?

**Why it matters.** In A-CDM, the estimated landing time drives stand allocation, ground handling and the next departure. A team needs to know from when the estimate stops moving.

**Method.**
1. Predict time to touchdown from open OpenSky ADS-B data with LightGBM quantile models.
2. Calibrate the interval per distance band to {num(cfg['coverage_target_pct'])} percent target coverage with conformal prediction.
3. For each flight, find the first prediction from which every later interval is no wider than W and contains the true touchdown.

**Headline.** {r['headline']} Baseline B: {f1(base['median_min'])} minutes. Median paired difference {f1(pair['median_diff_min'])} minutes (95% interval {f1(pair['ci_lo'])} to {f1(pair['ci_hi'])}). {verdict}

**Honest limit.** This is one evening of data ({f1(d['hours'])} hours, {c['test_flights']} test flights), split in time blocks. The collector keeps running so the study can grow to separate days.

**Demo.** {DEMO_TEXT}

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
