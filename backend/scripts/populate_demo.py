"""Demo populator — builds the LoadArea YN baseline scenario via the public API.

This mirrors how a real customer onboards: it registers the area, its 24 charging
stations and the baseline charging sessions — all through real REST calls, never
by touching the database directly. The system itself ships EMPTY; this script (or
the Postman 'Onboarding' folder) builds it up, so the running demo reflects real
usage rather than simulated/pre-seeded data.

Idempotent: safe to run on top of a partially-onboarded area (it only creates
what's missing). YN has exactly 24 stations — none beyond that are registered.

Usage:
    python scripts/populate_demo.py [--base-url http://localhost:8000]
    docker compose exec backend python scripts/populate_demo.py
"""
from __future__ import annotations

import argparse
import sys

import httpx

AREA = "YN"
AREA_NAME = "Ydre Nørrebro"
MAX_CAPACITY_KW = 240.0
CHARGER_COUNT = 24
CHARGER_POWER_KW = 11.0

# Baseline load: YN-01..YN-21 at 11 kW + YN-22 at 2 kW = 233 kW (WARNING).
# YN-23 and YN-24 are deliberately left free for the regulation demo.
BASELINE: dict[str, float] = {f"{AREA}-{g:02d}": CHARGER_POWER_KW for g in range(1, 22)}
BASELINE[f"{AREA}-22"] = 2.0


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the YN demo baseline via the API")
    parser.add_argument("--base-url", default="http://localhost:8000")
    base = parser.parse_args().base_url.rstrip("/")

    with httpx.Client(base_url=base, timeout=10.0) as client:
        try:
            client.get("/health").raise_for_status()
        except (httpx.HTTPError, httpx.InvalidURL) as exc:
            print(f"API not reachable at {base}: {exc}")
            return 1

        # 1) Register the load area (the customer's onboarding step).
        if client.get(f"/load-areas/{AREA}/status").status_code == 404:
            resp = client.post(
                "/load-areas",
                json={"areaCode": AREA, "areaName": AREA_NAME, "maxCapacityKw": MAX_CAPACITY_KW},
            )
            print(f"create area {AREA}: HTTP {resp.status_code}")
        else:
            print(f"area {AREA} already exists — skipping")

        # 2) Register the 24 charging stations (only the missing ones).
        existing = {c["chargerId"] for c in client.get(f"/load-areas/{AREA}/chargers").json()}
        registered = 0
        for g in range(1, CHARGER_COUNT + 1):
            charger_id = f"{AREA}-{g:02d}"
            if charger_id in existing:
                continue
            resp = client.post(
                f"/load-areas/{AREA}/chargers",
                json={"chargerId": charger_id, "maxPowerKw": CHARGER_POWER_KW},
            )
            registered += resp.status_code == 201
        print(f"chargers: {len(existing)} existed, {registered} registered ({CHARGER_COUNT} total)")

        # 3) Start the baseline sessions on the currently-free baseline chargers.
        occupied = {s["chargerId"] for s in client.get(f"/load-areas/{AREA}/sessions").json()}
        started = 0
        for charger_id, power_kw in BASELINE.items():
            if charger_id in occupied:
                continue
            resp = client.post(
                f"/load-areas/{AREA}/sessions",
                json={"chargerId": charger_id, "powerLevelKw": power_kw},
            )
            started += resp.status_code == 201
        print(f"baseline sessions: {started} started")

        # 4) Report the result.
        s = client.get(f"/load-areas/{AREA}/status").json()
        print(
            f"\nBaseline klar: {s['currentLoadKw']} kW / {s['maxCapacityKw']} kW "
            f"({s['status']}), {s['activeSessionCount']} aktive sessioner.\n"
            f"Ledige standere til regulerings-demoen: YN-23, YN-24."
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
