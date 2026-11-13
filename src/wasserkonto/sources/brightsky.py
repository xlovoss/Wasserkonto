"""Bright Sky: DWD station observations as a free JSON API.

Deliberately the opposite shape to PEGELONLINE. It is queried by coordinate
rather than by station, returns a different parameter set, and its history is
permanently retrievable. Under the operating rule -- collect greedily where
data expires, sparingly where it is archived -- a handful of points is enough
here, and any gap can be backfilled later.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from datetime import date, datetime, timedelta

from ..models import Observation, StationInfo
from .base import Context, Record

BASE = "https://api.brightsky.dev/weather"

# Only the fields that matter for a water balance, with their documented units.
PARAMETERS = {
    "precipitation": "mm",
    "temperature": "degC",
    "relative_humidity": "percent",
    "sunshine": "min",
    "wind_speed": "km/h",
    "pressure_msl": "hPa",
    "dew_point": "degC",
    "solar": "kWh/m2",
}


def parse_weather(payload: bytes, station: str) -> list[Observation]:
    """Hourly records for one point. Pure, so it tests against a fixture."""
    data = json.loads(payload.decode("utf-8"))
    out: list[Observation] = []
    for row in data.get("weather", []):
        ts = row.get("timestamp")
        if not ts:
            continue
        when = datetime.fromisoformat(ts)
        for name, unit in PARAMETERS.items():
            value = row.get(name)
            if value is None:
                continue
            out.append(Observation(source="brightsky", station=station,
                                   parameter=name, ts=when,
                                   value=float(value), unit=unit))
    return out


class BrightSky:
    name = "brightsky"

    def collect(self, ctx: Context) -> Iterator[Record]:
        cfg = ctx.config
        days = int(cfg.get("lookback_days", 3))
        last = date.today()
        first = last - timedelta(days=days)

        for point in cfg.get("points", []):
            name = point["name"]
            yield StationInfo(source="brightsky", station=name, name=name,
                              latitude=point.get("lat"),
                              longitude=point.get("lon"),
                              meta={"kind": "query point"})
            payload = ctx.get(BASE, name, {
                "lat": point["lat"], "lon": point["lon"],
                "date": first.isoformat(), "last_date": last.isoformat(),
            })
            yield from parse_weather(payload.body, name)
