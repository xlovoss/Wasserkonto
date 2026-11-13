"""PEGELONLINE: gauges on Germany's federal waterways (WSV).

A REST API with no key and no rate limit, which is precisely why the client is
deliberately slow. The service keeps roughly the last 30 days, so every day not
collected is lost for good. That is what makes this source perishable and worth
a daily job rather than an occasional download.

One index call with `includeTimeseries=true` returns every station together
with the series it offers and their units, which keeps the per-station calls
down to the measurements themselves.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from datetime import datetime

from ..http import FetchError
from ..models import Observation, StationInfo
from .base import Context, Record

log = logging.getLogger(__name__)

BASE = "https://www.pegelonline.wsv.de/webservices/rest-api/v2"


def parse_index(payload: bytes) -> tuple[list[StationInfo], dict[str, dict[str, str]]]:
    """Station metadata and the unit of each available time series.

    Pure function over the index response, so it is testable against a fixture.
    """
    import json

    stations: list[StationInfo] = []
    units: dict[str, dict[str, str]] = {}
    for entry in json.loads(payload.decode("utf-8")):
        uuid = entry.get("uuid")
        if not uuid:
            continue
        water = (entry.get("water") or {}).get("longname")
        stations.append(StationInfo(
            source="pegelonline", station=uuid,
            name=entry.get("longname") or entry.get("shortname"),
            latitude=entry.get("latitude"), longitude=entry.get("longitude"),
            water=water,
            meta={k: entry.get(k) for k in ("number", "shortname", "km", "agency")},
        ))
        units[uuid] = {
            ts["shortname"]: ts.get("unit", "")
            for ts in entry.get("timeseries", []) if ts.get("shortname")
        }
    return stations, units


def parse_measurements(payload: bytes, station: str, parameter: str,
                       unit: str) -> list[Observation]:
    """Measurements for one station and one series.

    PEGELONLINE timestamps carry an explicit UTC offset, so they are
    unambiguous and `Observation` normalises them to UTC.
    """
    import json

    out: list[Observation] = []
    for row in json.loads(payload.decode("utf-8")):
        ts, value = row.get("timestamp"), row.get("value")
        if ts is None or value is None:
            continue
        out.append(Observation(
            source="pegelonline", station=station, parameter=parameter,
            ts=datetime.fromisoformat(ts), value=float(value), unit=unit))
    return out


class PegelOnline:
    name = "pegelonline"

    def collect(self, ctx: Context) -> Iterator[Record]:
        cfg = ctx.config
        wanted = [s.upper() for s in cfg.get("timeseries", ["W", "Q"])]
        hours = int(cfg.get("lookback_hours", 72))
        only = set(cfg.get("stations") or [])

        index = ctx.get(f"{BASE}/stations.json", "stations",
                        {"includeTimeseries": "true"})
        stations, units = parse_index(index.body)

        if only:
            stations = [s for s in stations
                        if s.station in only
                        or (s.meta.get("shortname") or "") in only
                        or (s.name or "") in only]

        yield from stations

        for station in stations:
            for series in wanted:
                unit = units.get(station.station, {}).get(series)
                if unit is None:
                    continue
                url = f"{BASE}/stations/{station.station}/{series}/measurements.json"
                slug = f"{station.station}_{series}"
                try:
                    payload = ctx.get(url, slug, {"start": f"PT{hours}H"})
                except FetchError as exc:
                    # A single gauge being unreachable is routine. Log it and
                    # carry on; the ledger already holds the failed attempt.
                    log.warning("skipping %s: %s", slug, exc)
                    continue
                yield from parse_measurements(payload.body, station.station,
                                              series, unit)
