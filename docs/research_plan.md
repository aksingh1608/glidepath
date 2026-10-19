# Research plan

Status: written before any results exist. Any change after the first test run must be logged in section 9 with a date and a reason.

**Question.** How early can a ground team at Frankfurt (EDDF) trust a landing time?

We predict touchdown for arrivals at EDDF from open OpenSky ADS-B data. Each prediction carries an 80 percent interval, calibrated with conformalized quantile regression [romano2019conformalized]. For each flight we measure the trust point and the trust lead defined below. Keys in brackets refer to `references.bib`.

Each rule below now points to the code that implements it. The constants live in pipeline/config.py and are copied into results/results.json under config.

## 1. Definitions

**Flight and prediction times.** A flight *i* is one arrival at EDDF with a known touchdown time *T_i*. We make a prediction for flight *i* at each sample time *t_ik*, one per collector poll, from the first sample inside the prediction range until the last sample before touchdown. The prediction range is config.max_distance_nm, and a row also needs a remaining time of at most config.method.max_y_hours (pipeline/data.py, build_rows).

**Target.** The target at time *t_ik* is the time remaining to touchdown, *y_ik = T_i − t_ik*, in minutes. *T_i* is the touchdown label from the pipeline. The pipeline takes the first ground report near the airport after the flight was airborne beyond config.method.arrival_start_nm. If the last airborne report is close in time, *T_i* is the midpoint between the two. Otherwise it extrapolates from the last airborne report, capped by config.method.extrap_cap_s. If there is no ground report, a fallback extrapolates from the last low airborne report near the airport. The method used for each flight is counted in results.json (pipeline/data.py, label_flight).

**Interval.** For miscoverage level α, the model gives a lower and an upper bound, *[L_ik, U_ik]*, meant to contain *y_ik* with probability 1 − α. The main setting is α = 0.2, an 80 percent interval.

**Coverage.** The share of rows (flight, time pairs) with *L_ik ≤ y_ik ≤ U_ik*. We report it overall and per distance band. Distance bands are fixed before the test run. The bands are listed in config.bands (pipeline/config.py, BAND_EDGES).

**Interval width.** *U_ik − L_ik*, in minutes. We report the mean per distance band.

**Trust point.** For window *W* (2, 5 or 10 minutes), the trust point of flight *i*, *τ_i(W)*, is the earliest *t_ik* such that, for this sample and every later sample of the same flight, the interval width is less than *W* and the interval contains *y*.

**Trust lead.** *T_i − τ_i(W)*, in minutes.

**Never trusted.** A flight is never trusted at window *W* if no sample meets the trust point condition. This includes a flight whose last interval misses the truth. For medians and paired tests we set the trust lead of a never-trusted flight to zero, since the team never gets a usable lead. We also report the share of never-trusted flights for every result. The pipeline implements this rule (pipeline/trust.py).

**Note on use.** The trust point uses the true touchdown, so it is an evaluation measure, not a live signal. It answers how early the estimates would have been safe to act on.

## 2. Hypotheses

H1. Conformal calibration brings 80 percent interval coverage on the test day within 5 points of 80 in every distance band. Uncalibrated quantile intervals miss this in at least one band.

H2. At W = 5 minutes, the model gives a longer median trust lead than baseline B.

H3. Trust lead is shorter in the busiest third of traffic than in the quietest third.

H4. Flights with holding have a shorter trust lead than flights without.

**Grouping rules, fixed now.**

* *Traffic* (H3). Each test flight gets one traffic value. The measure is the mean of the traffic_50 feature (aircraft within the middle traffic radius) over the flight's prediction rows (pipeline/evaluate.py). We split test flights into thirds by this value and compare the top third with the bottom third.
* *Holding* (H4). A flight has holding if the pipeline holding detector flags it. The rule is cumulative heading change over the last config.method.turn_window_s seconds above config.method.holding_turn_deg degrees (pipeline/features.py). It was fixed before the first real run.

**Decision rules.** Each hypothesis gets one of three verdicts.

| | Supported | Not supported | Unclear |
|---|---|---|---|
| H1 | Calibrated point coverage in [75, 85] in every band, and uncalibrated coverage outside [75, 85] in at least one band | Calibrated coverage outside [75, 85] in any band, or uncalibrated coverage inside in every band | Point estimates meet the rule, but a 95 percent bootstrap interval crosses 75 or 85 in some band |
| H2 | Bootstrap interval of the median paired difference (model minus B) lies above zero | Point estimate of the median difference at or below zero | Point estimate above zero, but the interval includes zero |
| H3 | Interval of the median difference (quiet minus busy) lies above zero | Point estimate at or below zero | Point estimate above zero, interval includes zero |
| H4 | Interval of the median difference (no holding minus holding) lies above zero | Point estimate at or below zero | Point estimate above zero, interval includes zero |

## 3. Protocol

**Day splits.** We split by whole days, in time order: training days, then one calibration day, then one test day. No day appears in two splits. The pilot has only one evening, so it uses the time block split from the change log instead (pipeline/splits.py). The split spans are written to results.json under splits.

**Model.** A quantile regression model gives the lower, median and upper quantiles. The conformal step learns one correction per distance band on the calibration day [romano2019conformalized, angelopoulos2023conformal]. The model is LightGBM quantile regression, one model per quantile (pipeline/models.py, QuantileModel).

**Baselines.** Baseline A is distance to the airport divided by ground speed, a point estimate only. Baseline B is the empirical quantiles of remaining time per distance bin and landing direction from the training flights (pipeline/models.py). Both baselines must give an interval so that a trust lead exists. If a baseline gives only a point estimate, we form its interval from the empirical residual quantiles per distance band on the calibration day. This is the same budget of calibration data the model gets.

**No tuning on calibration or test days.** We pick all hyperparameters, features and band edges using only training days, with cross validation grouped by day. The calibration day is used only to fit the conformal correction. The test day is used once, for the final numbers. If we change anything after seeing test results, we log the change in section 9 and report both runs.

## 4. Statistics

**Unit of resampling.** Rows inside a flight are not independent. We resample whole flights with replacement and recompute every statistic on the resampled set.

**Bootstrap.** 10,000 flight resamples, percentile 95 percent intervals, fixed random seed. We report bootstrap intervals for coverage per band, mean width per band, and median trust lead per window.

**H1.** Coverage per distance band, before and after calibration, with bootstrap intervals.

**H2.** For each test flight, the paired difference *d_i* = model trust lead minus baseline B trust lead at W = 5 minutes. We report the median of *d_i* with its bootstrap interval, a Wilcoxon signed-rank test on *d_i*, and the matched-pairs rank-biserial correlation as the effect size.

**H3 and H4.** Two independent groups of flights. We report the difference in median trust lead with a bootstrap interval (resampling flights within each group), a Mann-Whitney U test, and the rank-biserial correlation as the effect size. We also report group sizes, because a small holding group gives a wide interval.

**Effect sizes first.** We report effect sizes and intervals for every test. P values come second. We test four hypotheses; we report raw p values and also Holm-adjusted p values for H2 to H4. For the pilot, Holm adjustment is not applied (see the change log).

## 5. Ablations

All at W = 5 minutes, α = 0.2, on the test day. Each row reports coverage, mean width and median trust lead, with bootstrap intervals, plus the share never trusted.

| Variant | Change from the full model |
|---|---|
| Full model | none |
| No traffic features | drop all traffic features, retrain |
| No landing direction | drop the runway direction feature, retrain |
| No conformal step | use raw quantile intervals |
| Global conformal | one conformal correction for all distances instead of one per band |

## 6. Sensitivity

* α = 0.1 and α = 0.2 (90 and 80 percent intervals). The coverage target for α = 0.1 is 90 percent with the same 5 point band.
* W = 2, 5 and 10 minutes, for the model and baseline B.

Sensitivity results are descriptive. They do not change the verdicts in section 2.

## 6a. Case studies

The pilot shows up to three test flights at W = 5 minutes: a typical flight (trust lead closest to the median among trusted flights), the flight with the shortest lead, and a holding flight if any (lead closest to the median among holding flights).

## 7. Threats to validity

* **ADS-B coverage gaps.** OpenSky relies on volunteer receivers [schafer2014bringing]. Gaps near the airport can hide the last part of the approach and shift the touchdown label. We report the share of flights dropped for gaps.
* **30 second sampling.** The trust point can only fall on a sample time, so it carries up to 30 seconds of rounding. This matters most at W = 2 minutes.
* **Label noise.** Touchdown is inferred from ADS-B, not taken from an official actual landing time. Errors in *T_i* move both the target and the trust lead.
* **Few days of data.** One calibration day and one test day may not cover rare conditions such as storms or a runway closure. Flight-level bootstrap intervals do not capture day-to-day variation.
* **Test day differs from calibration day.** Split conformal coverage assumes the calibration and test data are exchangeable. A different weather or traffic pattern on the test day can break this [gibbs2021adaptive, forster2024probabilistic].
* **Marginal coverage only.** The guarantee holds on average over rows, not for each flight or each condition. Per-band calibration helps for distance, but not for traffic or holding.
* **Trust point is strict.** One miss late in the approach resets the trust point. This is intended, but it makes the measure sensitive to label noise near touchdown.

## 8. What would count against our idea

* H1: Calibrated coverage on the test day falls outside 75 to 85 percent in at least one distance band.
* H2: At W = 5 minutes the median paired difference, model minus baseline B, is zero or negative.
* H3: Busy-traffic flights have a median trust lead equal to or longer than quiet-traffic flights.
* H4: Flights with holding have a median trust lead equal to or longer than flights without.

## 9. Change log

| Date | Change | Reason |
|---|---|---|
| 2026-10-18 | Pilot protocol adopted, before any real results: trust condition uses width no wider than W; distance bands 0 to 20, 20 to 50, 50 to 100 and over 100 nm; time block split (first 60 percent of flights by touchdown train, next 20 percent calibration, rest test) until 3 local days with 150 or more arrivals exist; H1 counts only bands with 50 or more test rows; H3 terciles use mean traffic within 50 nm per flight; H4 is unclear with fewer than 5 holding flights; never-trusted flights get lead 0; Holm adjustment and the alpha sensitivity grid are not part of the pilot run. | One evening of live data. Settings live in `pipeline/config.py`. |
| 2026-10-18 | Code moved from the earlier `evaluate/` package to `pipeline/` and `run.py`. | Single pipeline from raw collector CSVs to results, site and docs. |
| 2026-10-19 | Added exploratory statistics after the first real results: interval score, pinball loss, paired point error, quantile reliability, coverage per split and per-flight win share (`pipeline/diagnostics.py`). | They explain the hypothesis results. They were added after seeing results, so they do not change any hypothesis, threshold or verdict. |

## 10. Where each number comes from

Every number in the README, the research note, the summary and the site comes from `results/results.json`, written by `run.py`. Tables are also written to `results/tables/`.

| Number | Location in `results/results.json` | Table |
|---|---|---|
| Data window, counts, drop reasons, label methods | `data_window`, `counts`, `drop_reasons`, `label_methods` | |
| Split scheme and time spans | `splits` | |
| Point accuracy at 100, 50, 20 nm | `point_accuracy` | `results/tables/point_accuracy.csv` |
| Coverage and width per band | `coverage` | `results/tables/coverage.csv` |
| Trust lead per window | `trust` | `results/tables/trust_lead.csv` |
| Paired difference at W = 5 | `paired_w5` | |
| Traffic, direction and holding splits | `splits_w5` | `results/tables/split_*.csv` |
| Ablations | `ablations` | `results/tables/ablations.csv` |
| Hypotheses H1 to H4 | `hypotheses` | |
| Width attribution (SHAP) | `shap_width` | `results/tables/shap_width.csv` |
| Interval score and pinball loss | `diagnostics.scores` | `results/tables/scores.csv` |
| Paired point error | `diagnostics.paired_point_error` | `results/tables/paired_point_error.csv` |
| Quantile reliability | `diagnostics.reliability` | `results/tables/reliability.csv` |
| Coverage per split | `diagnostics.drift` | `results/tables/drift.csv`, `results/tables/coverage_per_flight.csv` |
| Per-flight win share | `diagnostics.superiority_w5` | |
| Arrivals per hour | `diagnostics.arrivals_by_hour` | `results/tables/arrivals_by_hour.csv` |
