# Glidepath: when can a ground team trust a landing time?

Aryan Kumar Singh, Berlin School of Business and Innovation, October 2026

Question: How early can a ground team at Frankfurt (EDDF) trust a predicted landing time?

Why it matters: Under A-CDM, the estimated landing time drives stand planning, ground handling and the next departure. A team needs to know when the estimate stops moving.

What I did: (1) Predicted time to touchdown from open OpenSky ADS-B data with LightGBM quantile models. (2) Calibrated the interval per distance band to 80 percent with conformal prediction. (3) Found each flight's trust point for windows of 2, 5 and 10 minutes.

Result: On the 24 test flights, the landing time became trustworthy within a 5 minute window a median of 7.2 minutes before touchdown. At W = 10, where baseline B can qualify, the model's median lead is 7.2 minutes against 1.4. The interval score, which adds width and a penalty for every miss, is 6.8 minutes for the model and 10.5 for the baseline.

Limits: one evening of data, 24 test flights, test coverage 71.1 percent against the 80 percent target, and touchdown labels estimated from ADS-B.

Next: run over separate days, add weather, and compare with official landing times if I can get them.

Code: github.com/aksingh1608/glidepath

Research demo, not for operational use.
