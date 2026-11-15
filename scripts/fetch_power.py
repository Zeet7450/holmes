"""Fetch one full-history NASA POWER point series per curated city.

Raw responses are cached under data/seed/raw/power/. Re-running is a no-op
unless --force is passed. Historical data is immutable.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
CITIES = json.loads((ROOT / "data/seed/cities.json").read_text())
RAW = ROOT / "data/seed/raw/power"
PARAMS = [
    "T2M", "T2M_MIN", "T2M_MAX", "PRECTOTCORR", "GWETROOT",
    "GWETTOP", "RH2M", "WS2M", "ALLSKY_SFC_SW_DWN", "AOD_55",
]
BASE = "https://power.larc.nasa.gov/api/temporal/monthly/point"


async def fetch(client: httpx.AsyncClient, city: dict, force: bool) -> tuple[str, str]:
    path = RAW / f"{city['id']}.json"
    if path.exists() and not force:
        return city["id"], "cached"
    params = {
        "parameters": ",".join(PARAMS),
        "community": "AG",
        "longitude": city["lon"],
        "latitude": city["lat"],
        "start": 1981,
        "end": 2025,
        "format": "JSON",
    }
    for attempt in range(4):
        try:
            response = await client.get(BASE, params=params, timeout=90)
            if response.status_code == 429:
                await asyncio.sleep(5 * (attempt + 1))
                continue
            response.raise_for_status()
            payload = response.json()
            if "properties" not in payload:
                raise ValueError("no properties in response")
            path.write_text(json.dumps(payload))
            return city["id"], "fetched"
        except Exception as exc:
            if attempt == 3:
                return city["id"], f"failed: {exc}"
            await asyncio.sleep(2 * (attempt + 1))
    return city["id"], "failed"


async def main(force: bool) -> int:
    RAW.mkdir(parents=True, exist_ok=True)
    semaphore = asyncio.Semaphore(6)
    failures: list[str] = []

    async with httpx.AsyncClient(follow_redirects=True) as client:
        async def worker(city: dict):
            async with semaphore:
                city_id, status = await fetch(client, city, force)
                print(f"{status:10s} {city_id}", flush=True)
                if status.startswith("failed"):
                    failures.append(city_id)

        await asyncio.gather(*(worker(city) for city in CITIES))

    if failures:
        print(f"FAILED: {len(failures)} cities: {failures}", file=sys.stderr)
        return 1
    print(f"OK: {len(CITIES)} cities cached")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    raise SystemExit(asyncio.run(main(args.force)))
