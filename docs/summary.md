# Glidepath: how early can a ground team trust a landing time?

> **Pilot study.** One evening of live OpenSky data, 2026-10-18 17:45:52 CEST to 2026-10-19 03:37:12 CEST (9.9 hours). 120 arrivals kept, 24 in the held-out test set. The collector keeps running, so later runs will cover more days.

**Question.** How early can a ground team at Frankfurt (EDDF) trust a predicted landing time?

**Why it matters.** In A-CDM, the estimated landing time drives stand allocation, ground handling and the next departure. A team needs to know from when the estimate stops moving.

**Method.**
1. Predict time to touchdown from open OpenSky ADS-B data with LightGBM quantile models.
2. Calibrate the interval per distance band to 80 percent target coverage with conformal prediction.
3. For each flight, find the first prediction from which every later interval is no wider than W and contains the true touchdown.

**Headline.** In this pilot, a typical Frankfurt arrival had a landing time we could trust within 5 minutes, 7.2 minutes before touchdown (24 test flights). Baseline B: 0.0 minutes. Median paired difference 7.2 minutes (95% interval 4.8 to 7.8). The model beat baseline B on this measure.

**Honest limit.** This is one evening of data (9.9 hours, 24 test flights), split in time blocks. The collector keeps running so the study can grow to separate days.

**Demo.** The replay site is in web/. Run make serve to open it locally.

Research demo. Not for operational use.
