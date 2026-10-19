"""SYNTHETIC TEST data in the collector CSV format. For testing only.

A 6 hour evening at EDDF: arrivals from four streams, routed via an entry fix
at 25 nm and a final approach fix 12 nm out, a minimum landing gap enforced by
holding circles or path stretch, a runway direction switch from 25 to 07,
ground points after touchdown, random dropouts, departures and overflights.

Usage: python -m pipeline.synthetic --out data/synthetic
"""

from __future__ import annotations

import argparse
import csv
import math
import os
from datetime import datetime, timezone

import numpy as np

from . import config as C

START_UTC = datetime(2026, 10, 14, 15, 0, tzinfo=timezone.utc).timestamp()  # 17:00 local
HOURS = 6
ARRIVALS_PER_HOUR = 34
DEPARTURES_PER_HOUR = 24
OVERFLIGHTS_PER_HOUR = 20
STREAM_BEARINGS = (25, 115, 195, 300)
ENTRY_NM = (118, 135)
ENTRY_FIX_NM = 25
FAF_NM = 12
MIN_GAP_S = 95
HOLD_CIRCLE_S = 180
SWITCH_AT = 0.65
GROUND_POINTS = 8
DROPOUT = 0.03
POLL_S = 10
DT = 2.0
M_PER_NM_3DEG = 96.9
CRUISE_M = 11000.0

COLUMNS = ["poll_time", "icao24", "callsign", "origin_country", "time_position",
           "last_contact", "lon", "lat", "baro_alt_m", "on_ground", "velocity_ms",
           "true_track_deg", "vertical_rate_ms", "geo_alt_m", "squawk", "spi",
           "position_source", "category"]


def xy(bearing, dist):
    b = math.radians(bearing)
    return np.array([dist * math.sin(b), dist * math.cos(b)])


def to_latlon(p):
    lat = C.REF_LAT + p[1] / 60.0
    lon = C.REF_LON + p[0] / (60.0 * math.cos(math.radians(C.REF_LAT)))
    return lat, lon


def heading(v):
    return (math.degrees(math.atan2(v[0], v[1])) + 360) % 360


def speed_kt(s_rem):
    return 140.0 + 310.0 * min(1.0, max(0.0, s_rem) / 100.0) ** 0.7


def alt_m(s_rem):
    return C.FIELD_ELEV_M + min(max(s_rem, 0.0) * M_PER_NM_3DEG, CRUISE_M)


class Path:
    def __init__(self, pts):
        self.pts = [np.asarray(p, float) for p in pts]
        seg = [np.linalg.norm(b - a) for a, b in zip(self.pts, self.pts[1:])]
        self.cum = np.concatenate([[0.0], np.cumsum(seg)])
        self.length = self.cum[-1]

    def at(self, along):
        along = min(max(along, 0.0), self.length)
        i = min(int(np.searchsorted(self.cum, along, side="right")) - 1, len(self.pts) - 2)
        a, b = self.pts[i], self.pts[i + 1]
        f = (along - self.cum[i]) / max(self.cum[i + 1] - self.cum[i], 1e-9)
        return a + f * (b - a), heading(b - a)


def nominal_time(path: Path, start_along=0.0):
    t, along = 0.0, start_along
    while along < path.length:
        along += speed_kt(path.length - along) / 3600 * DT
        t += DT
    return t


def arrival_track(rng, t_entry, delay, stream, runway):
    rwy_hdg = C.RUNWAY_HEADINGS[runway]
    faf = xy(rwy_hdg + 180, FAF_NM)
    entry = xy(stream + rng.uniform(-6, 6), rng.uniform(*ENTRY_NM))
    fix = xy(stream, ENTRY_FIX_NM)
    pts = [entry, fix]
    off = (stream - (rwy_hdg + 180) + 540) % 360 - 180
    if abs(off) > 90:  # come round the side instead of over the field
        pts.append(xy(rwy_hdg + 180 + math.copysign(70, off), 18))
    pts += [faf, np.zeros(2)]
    path = Path(pts)
    fix_along = path.cum[1]
    n_circles = int(delay // HOLD_CIRCLE_S) if delay >= 150 else 0
    stretch = delay - n_circles * HOLD_CIRCLE_S
    tail = nominal_time(path, fix_along)
    slow = (tail + stretch) / tail if tail > 0 else 1.0

    out, t, along = [], t_entry, 0.0
    held = False
    while along < path.length:
        s_rem = path.length - along
        if not held and along >= fix_along and n_circles:
            v = speed_kt(s_rem)
            radius = v * HOLD_CIRCLE_S / 3600 / (2 * math.pi)
            p0, h0 = path.at(along)
            centre = p0 + radius * np.array([math.cos(math.radians(h0)),
                                             -math.sin(math.radians(h0))])
            a0 = math.atan2(*(p0 - centre))
            steps = int(n_circles * HOLD_CIRCLE_S / DT)
            for k in range(steps):
                ang = a0 + 2 * math.pi * k * DT / HOLD_CIRCLE_S
                pos = centre + radius * np.array([math.sin(ang), math.cos(ang)])
                out.append((t, pos, (math.degrees(ang) + 90) % 360, v, alt_m(s_rem), False))
                t += DT
            held = True
        pos, hdg = path.at(along)
        v = speed_kt(s_rem) / (slow if along >= fix_along else 1.0)
        out.append((t, pos, hdg, v, alt_m(s_rem), False))
        along += v / 3600 * DT
        t += DT
    touchdown = t
    pos = np.zeros(2)
    v = 140.0
    for k in range(GROUND_POINTS * int(POLL_S / DT)):
        out.append((t, pos.copy(), rwy_hdg, v, None, True))
        pos = pos + xy(rwy_hdg, v / 3600 * DT)
        v = max(15.0, v - 4.0)
        t += DT
    return out, touchdown


def departure_track(rng, t0, runway):
    rwy_hdg = C.RUNWAY_HEADINGS[runway]
    exit_b = rng.choice(STREAM_BEARINGS) + rng.uniform(15, 40)
    out, t = [], t0
    pos = xy(rwy_hdg + 180, 1.5)
    for _ in range(int(40 / DT)):
        out.append((t, pos.copy(), rwy_hdg, 10.0, None, True))
        t += DT
    alt, v, hdg = C.FIELD_ELEV_M, 150.0, rwy_hdg
    while np.linalg.norm(pos) < 140:
        if alt > 1500:
            target = exit_b
            diff = (target - hdg + 540) % 360 - 180
            hdg = (hdg + max(-3 * DT, min(3 * DT, diff))) % 360
        pos = pos + xy(hdg, v / 3600 * DT)
        alt = min(CRUISE_M, alt + 12 * DT)
        v = min(450.0, v + 1.0 * DT)
        out.append((t, pos.copy(), hdg, v, alt, False))
        t += DT
    return out


def overflight_track(rng, t0):
    hdg = rng.uniform(0, 360)
    miss = rng.uniform(15, 80) * rng.choice([-1, 1])
    start = xy(hdg + 180, 150) + xy(hdg + 90, miss)
    out, t, pos = [], t0, start
    v = rng.uniform(420, 490)
    alt = rng.uniform(9500, 11800)
    flown = 0.0
    while flown <= 300:
        out.append((t, pos.copy(), hdg, v, alt, False))
        pos = pos + xy(hdg, v / 3600 * DT)
        flown += v / 3600 * DT
        t += DT
    return out


def poisson_times(rng, rate_per_hour, start, end):
    t, times = start, []
    while True:
        t += rng.exponential(3600 / rate_per_hour)
        if t >= end:
            return times
        times.append(t)


def generate(out_dir: str, seed: int = 7) -> str:
    rng = np.random.default_rng(seed)
    end = START_UTC + HOURS * 3600
    switch_t = START_UTC + SWITCH_AT * HOURS * 3600
    runway_at = lambda t: "25" if t < switch_t else "07"

    # Arrivals: schedule touchdowns with a minimum gap, then fly the delay.
    # Regular spacing with jitter: a Poisson stream at this rate saturates the runway.
    spacing = 3600 / ARRIVALS_PER_HOUR
    entries = [START_UTC - 1800 + k * spacing + rng.uniform(-0.45, 0.45) * spacing
               for k in range(int((end - START_UTC) / spacing))]
    plans = []
    for te in entries:
        stream = int(rng.choice(STREAM_BEARINGS))
        plans.append({"t_entry": te, "stream": stream})
    for p in plans:
        rwy = runway_at(p["t_entry"] + 1500)
        rough, _ = arrival_track(np.random.default_rng(0), p["t_entry"], 0.0, p["stream"], rwy)
        p["t0"] = [r for r in rough if r[5]][0][0]
    plans.sort(key=lambda p: p["t0"])
    last = -1e18
    tracks = []
    for p in plans:
        land = max(p["t0"], last + MIN_GAP_S)
        last = land
        rwy = runway_at(land)
        trk, _ = arrival_track(rng, p["t_entry"], land - p["t0"], p["stream"], rwy)
        tracks.append(trk)
    for t0 in poisson_times(rng, DEPARTURES_PER_HOUR, START_UTC, end):
        tracks.append(departure_track(rng, t0, runway_at(t0)))
    for t0 in poisson_times(rng, OVERFLIGHTS_PER_HOUR, START_UTC - 1200, end):
        tracks.append(overflight_track(rng, t0))

    os.makedirs(out_dir, exist_ok=True)
    for f in os.listdir(out_dir):
        if f.startswith("states_") and f.endswith(".csv"):
            os.remove(os.path.join(out_dir, f))
    writers = {}
    files = {}
    used = set()
    meta = []
    for trk in tracks:
        while True:
            icao = "%06x" % rng.integers(0x300000, 0x4fffff)
            if icao not in used:
                used.add(icao)
                break
        meta.append((icao, "SYN%04d" % len(meta), int(rng.choice([3, 4, 6]))))

    for poll in np.arange(START_UTC, end, POLL_S):
        hour = datetime.fromtimestamp(poll, timezone.utc).strftime("%Y%m%d_%H")
        if hour not in writers:
            files[hour] = open(os.path.join(out_dir, f"states_{hour}.csv"), "w", newline="")
            writers[hour] = csv.writer(files[hour])
            writers[hour].writerow(COLUMNS)
        w = writers[hour]
        for trk, (icao, cs, cat) in zip(tracks, meta):
            if not (trk[0][0] <= poll <= trk[-1][0]) or rng.random() < DROPOUT:
                continue
            tp = int(poll - rng.uniform(0, 4))
            k = min(range(len(trk)), key=lambda i: abs(trk[i][0] - tp)) if len(trk) < 50 else \
                int(np.clip(round((tp - trk[0][0]) / DT), 0, len(trk) - 1))
            t, pos, hdg, v, alt, ground = trk[k]
            k2 = max(0, k - 5)
            vr = 0.0 if ground or alt is None or trk[k2][4] is None else \
                (alt - trk[k2][4]) / max(t - trk[k2][0], 1e-9)
            lat, lon = to_latlon(pos)
            w.writerow([int(poll), icao, cs, "Synthetic", tp, tp, round(lon, 5), round(lat, 5),
                        None if alt is None else round(alt, 1), ground,
                        round(v / C.MS_TO_KT, 2), round(hdg, 1), round(vr, 2),
                        None if alt is None else round(alt + 30, 1), "1000", False, 0, cat])
    for f in files.values():
        f.close()
    with open(os.path.join(out_dir, "SYNTHETIC"), "w") as f:
        f.write("SYNTHETIC TEST data from pipeline.synthetic\n")
    return out_dir


def main():
    p = argparse.ArgumentParser(description="write SYNTHETIC TEST collector CSVs")
    p.add_argument("--out", default="data/synthetic")
    p.add_argument("--seed", type=int, default=7)
    a = p.parse_args()
    print(f"wrote SYNTHETIC TEST data to {generate(a.out, a.seed)}")


if __name__ == "__main__":
    main()
