#!/usr/bin/env python3
"""Glidepath live collector: OpenSky state vectors around Frankfurt (EDDF).

Standard library only. Reads clientId and clientSecret from ./credentials.json
(client_id and client_secret are also accepted) and appends one CSV row per
aircraft per poll to data/raw/live/states_YYYYMMDD_HH.csv (UTC hour).

Usage:
    python3 collect_live.py            # run until stopped
    python3 collect_live.py --status   # summary of collected data

Environment:
    GLIDEPATH_POLL_SECONDS   poll interval in seconds (default 10)
"""

import argparse
import csv
import glob
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

TOKEN_URL = ("https://auth.opensky-network.org/auth/realms/opensky-network/"
             "protocol/openid-connect/token")
STATES_URL = "https://opensky-network.org/api/states/all"
BBOX = {"lamin": 48.20, "lamax": 51.87, "lomin": 5.72, "lomax": 11.42}
OUT_DIR = os.path.join("data", "raw", "live")
CREDENTIALS = "credentials.json"
TOKEN_MARGIN_S = 120
DEFAULT_RETRY_S = 600
TIMEOUT_S = 30

COLUMNS = ["poll_time", "icao24", "callsign", "origin_country", "time_position",
           "last_contact", "lon", "lat", "baro_alt_m", "on_ground", "velocity_ms",
           "true_track_deg", "vertical_rate_ms", "geo_alt_m", "squawk", "spi",
           "position_source", "category"]


def log(msg):
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    print(f"{stamp} {msg}", flush=True)


def read_credentials(path=CREDENTIALS):
    with open(path) as f:
        cred = json.load(f)
    cid = cred.get("clientId") or cred.get("client_id")
    secret = cred.get("clientSecret") or cred.get("client_secret")
    if not cid or not secret:
        raise SystemExit(f"{path} needs clientId and clientSecret")
    return cid, secret


class Token:
    def __init__(self, client_id, client_secret):
        self.client_id = client_id
        self.client_secret = client_secret
        self.value = None
        self.expires_at = 0.0

    def get(self):
        if self.value is None or time.time() >= self.expires_at - TOKEN_MARGIN_S:
            self.refresh()
        return self.value

    def refresh(self):
        body = urllib.parse.urlencode({
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }).encode()
        req = urllib.request.Request(TOKEN_URL, data=body, method="POST", headers={
            "Content-Type": "application/x-www-form-urlencoded"})
        with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
            data = json.load(resp)
        self.value = data["access_token"]
        self.expires_at = time.time() + float(data.get("expires_in", 1800))
        log(f"token ok, expires in {int(self.expires_at - time.time())} s")


def fetch_states(token):
    url = STATES_URL + "?" + urllib.parse.urlencode({**BBOX, "extended": 1})
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
        return json.load(resp), resp.headers


def to_rows(payload, poll_time):
    rows = []
    for s in payload.get("states") or []:
        s = list(s) + [None] * (18 - len(s))
        lon, lat = s[5], s[6]
        if lat is None or lon is None:
            continue
        rows.append([poll_time, s[0], (s[1] or "").strip(), s[2], s[3], s[4], lon, lat,
                     s[7], s[8], s[9], s[10], s[11], s[13], s[14], s[15], s[16], s[17]])
    return rows


def write_rows(rows, poll_time):
    os.makedirs(OUT_DIR, exist_ok=True)
    hour = datetime.fromtimestamp(poll_time, timezone.utc).strftime("%Y%m%d_%H")
    path = os.path.join(OUT_DIR, f"states_{hour}.csv")
    new = not os.path.exists(path)
    with open(path, "a", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(COLUMNS)
        w.writerows(rows)
        f.flush()
        os.fsync(f.fileno())
    return path


def run():
    interval = float(os.environ.get("GLIDEPATH_POLL_SECONDS", "10"))
    token = Token(*read_credentials())
    log(f"collector start, poll every {interval:g} s, bbox {BBOX}")
    while True:
        started = time.time()
        try:
            try:
                payload, headers = fetch_states(token.get())
            except urllib.error.HTTPError as e:
                if e.code != 401:
                    raise
                log("401, getting a new token")
                token.refresh()
                payload, headers = fetch_states(token.get())
            poll_time = int(time.time())
            rows = to_rows(payload, poll_time)
            if rows:
                write_rows(rows, poll_time)
            log(f"poll ok aircraft={len(rows)} "
                f"rate_limit_remaining={headers.get('X-Rate-Limit-Remaining', 'n/a')}")
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait = e.headers.get("X-Rate-Limit-Retry-After-Seconds") or e.headers.get(
                    "Retry-After") or DEFAULT_RETRY_S
                wait = float(wait)
                log(f"429 rate limited, sleeping {wait:g} s")
                time.sleep(wait)
                continue
            log(f"http error {e.code}: {e.reason}")
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError, ValueError) as e:
            log(f"network error: {e!r}")
        time.sleep(max(0.0, interval - (time.time() - started)))


def status():
    files = sorted(glob.glob(os.path.join(OUT_DIR, "states_*.csv")))
    if not files:
        print("no files in", OUT_DIR)
        return
    rows, polls, aircraft = 0, set(), set()
    for path in files:
        n = 0
        with open(path, newline="") as f:
            for r in csv.DictReader(f):
                n += 1
                polls.add(r["poll_time"])
                aircraft.add(r["icao24"])
        rows += n
        print(f"{path}: {n} rows")
    times = sorted(int(p) for p in polls)
    fmt = lambda t: datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    print(f"files={len(files)} rows={rows} polls={len(polls)} aircraft={len(aircraft)}")
    print(f"time range: {fmt(times[0])} to {fmt(times[-1])} "
          f"({(times[-1] - times[0]) / 60:.1f} minutes)")


def main():
    p = argparse.ArgumentParser(description="Glidepath OpenSky live collector")
    p.add_argument("--status", action="store_true", help="print a summary and exit")
    args = p.parse_args()
    if args.status:
        status()
    else:
        try:
            run()
        except KeyboardInterrupt:
            log("collector stopped")
            sys.exit(0)


if __name__ == "__main__":
    main()
