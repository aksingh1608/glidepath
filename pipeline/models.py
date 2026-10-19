"""Baselines A and B, LightGBM quantile model, conformal calibration (CQR)."""

from __future__ import annotations

import math

import lightgbm as lgb
import numpy as np
import pandas as pd

from . import config as C


# Baseline A: distance over ground speed
def baseline_a_point(df: pd.DataFrame) -> np.ndarray:
    gs = np.clip(df["gs_kt"].fillna(C.BASELINE_A_MIN_KT).to_numpy(), C.BASELINE_A_MIN_KT, None)
    return df["distance_nm"].to_numpy() / gs * 3600.0


class BaselineA:
    def fit(self, train: pd.DataFrame):
        res = train["y"].to_numpy() - baseline_a_point(train)
        g = pd.Series(res).groupby(train["band"].to_numpy())
        self.lo = g.quantile(0.1).to_dict()
        self.hi = g.quantile(0.9).to_dict()
        self.lo_all, self.hi_all = np.quantile(res, [0.1, 0.9])
        return self

    def predict(self, df: pd.DataFrame):
        p = baseline_a_point(df)
        band = df["band"].to_numpy()
        lo = p + np.array([self.lo.get(b, self.lo_all) for b in band])
        hi = p + np.array([self.hi.get(b, self.hi_all) for b in band])
        return lo, p, hi


# Baseline B: empirical quantiles of y by 5 nm distance bin and direction
class BaselineB:
    def __init__(self, fallback: BaselineA):
        self.fallback = fallback

    @staticmethod
    def _bin(df):
        return (df["distance_nm"] // C.BASELINE_B_BIN_NM).astype(int).to_numpy()

    def fit(self, train: pd.DataFrame):
        tb = train.assign(dbin=self._bin(train))
        q = lambda g: pd.Series({"n": len(g), "p10": g.quantile(0.1),
                                 "p50": g.quantile(0.5), "p90": g.quantile(0.9)})
        self.by_dir = tb.groupby(["dbin", "direction_code"])["y"].apply(q).unstack()
        self.by_bin = tb.groupby("dbin")["y"].apply(q).unstack()
        return self

    def predict(self, df: pd.DataFrame):
        dbin = self._bin(df)
        dcode = df["direction_code"].to_numpy()
        a_lo, a_p, a_hi = self.fallback.predict(df)
        out = np.column_stack([a_lo, a_p, a_hi]).astype(float)
        source = np.full(len(df), "baseline_a", dtype=object)
        cols = ["p10", "p50", "p90"]
        by_dir = {k: tuple(r[cols]) for k, r in self.by_dir.iterrows()
                  if r["n"] >= C.BASELINE_B_MIN_ROWS}
        by_bin = {k: tuple(r[cols]) for k, r in self.by_bin.iterrows()
                  if r["n"] >= C.BASELINE_B_MIN_ROWS}
        for i, (b, d) in enumerate(zip(dbin, dcode)):
            r = by_dir.get((b, d))
            if r is not None:
                source[i] = "bin_direction"
            else:
                r = by_bin.get(b)
                if r is None:
                    continue
                source[i] = "bin"
            out[i] = r
        self.last_source = source
        return out[:, 0], out[:, 1], out[:, 2]


# Main model: LightGBM quantile regression
class QuantileModel:
    def __init__(self, features: list[str]):
        self.features = list(features)
        self.boosters = {}
        self.best_iter = {}

    def fit(self, train: pd.DataFrame):
        rng = np.random.default_rng(C.SEED)
        flights = np.array(sorted(train["flight_id"].unique()))
        n_val = max(1, int(round(C.VALID_FLIGHT_FRAC * len(flights))))
        val_ids = set(rng.choice(flights, size=n_val, replace=False))
        is_val = train["flight_id"].isin(val_ids).to_numpy()
        X, y = train[self.features], train["y"].to_numpy()
        for q in C.QUANTILES:
            params = {**C.LGB_PARAMS, "alpha": q, "seed": C.SEED}
            dtr = lgb.Dataset(X[~is_val], y[~is_val])
            dva = lgb.Dataset(X[is_val], y[is_val], reference=dtr)
            b = lgb.train(params, dtr, num_boost_round=C.LGB_MAX_ROUNDS, valid_sets=[dva],
                          callbacks=[lgb.early_stopping(C.EARLY_STOPPING_ROUNDS, verbose=False)])
            best = max(1, b.best_iteration or C.LGB_MAX_ROUNDS)
            self.best_iter[q] = best
            self.boosters[q] = lgb.train(params, lgb.Dataset(X, y), num_boost_round=best)
        return self

    def predict(self, df: pd.DataFrame):
        X = df[self.features]
        preds = np.column_stack([self.boosters[q].predict(X) for q in C.QUANTILES])
        preds.sort(axis=1)  # quantiles never cross
        return preds[:, 0], preds[:, 1], preds[:, 2]

    def contributions(self, df: pd.DataFrame, q: float) -> np.ndarray:
        return self.boosters[q].predict(df[self.features], pred_contrib=True)


# Conformalized quantile regression (Romano et al. 2019)
def cqr_q(scores: np.ndarray, alpha: float = C.ALPHA) -> float:
    n = len(scores)
    if n == 0:
        return 0.0
    level = math.ceil((n + 1) * (1 - alpha)) / n
    if level > 1:
        return float(np.max(scores))
    return float(np.quantile(scores, level, method="higher"))


class CQR:
    def __init__(self, per_band: bool = True):
        self.per_band = per_band

    def fit(self, lo, hi, y, band):
        scores = np.maximum(np.asarray(lo) - y, np.asarray(y) - hi)
        self.global_q = cqr_q(scores)
        self.band_q, self.band_n = {}, {}
        if self.per_band:
            for b in np.unique(band):
                s = scores[band == b]
                self.band_n[int(b)] = int(len(s))
                if len(s) >= C.CQR_MIN_BAND_ROWS:
                    self.band_q[int(b)] = cqr_q(s)
        return self

    def apply(self, lo, hi, band):
        q = np.array([self.band_q.get(int(b), self.global_q) for b in band])
        return np.asarray(lo) - q, np.asarray(hi) + q

    def summary(self) -> dict:
        return {"global_q_s": self.global_q,
                "band_q_s": {str(k): v for k, v in self.band_q.items()},
                "band_calibration_rows": {str(k): v for k, v in self.band_n.items()}}
