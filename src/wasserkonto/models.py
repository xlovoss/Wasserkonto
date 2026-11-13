"""Core records that flow from a source into the archive.

Everything a source produces is one of these three. Keeping them dumb and
immutable means the parsing code can be tested without a database, a network
connection, or a configuration file.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime


def _as_utc(ts: datetime) -> datetime:
    """Normalise to timezone-aware UTC.

    German hydrological services publish timestamps in several flavours: with a
    +01:00/+02:00 offset, in MEZ year-round without an offset, or as naive local
    time. A naive timestamp is ambiguous, so we refuse it rather than silently
    guessing an offset and poisoning the archive with an hour-shifted series.
    """
    if ts.tzinfo is None:
        raise ValueError(
            f"refusing naive timestamp {ts!r}: the source parser must attach "
            "the timezone the service documents"
        )
    return ts.astimezone(UTC)


@dataclass(frozen=True, slots=True)
class Observation:
    """One measured value, at one place, at one point in time."""

    source: str
    station: str
    parameter: str
    ts: datetime
    value: float
    unit: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "ts", _as_utc(self.ts))

    @property
    def key(self) -> tuple[str, str, str, str]:
        """The identity of this measurement. Two records with the same key are
        the same measurement, which is what makes re-collection idempotent."""
        return (self.source, self.station, self.parameter, self.ts.isoformat())


@dataclass(frozen=True, slots=True)
class StationInfo:
    """Metadata about a measuring point.

    Station metadata changes over time (stations get renamed, re-surveyed,
    decommissioned), so the archive keeps first_seen/last_seen rather than
    pretending this is a static lookup table.
    """

    source: str
    station: str
    name: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    water: str | None = None
    meta: dict = field(default_factory=dict)

    def meta_json(self) -> str:
        return json.dumps(self.meta, ensure_ascii=False, sort_keys=True)


@dataclass(frozen=True, slots=True)
class Payload:
    """A raw response, already written to the archive and logged in the ledger."""

    url: str
    slug: str
    body: bytes
    fetch_id: int
    sha256: str
    fetched_at: datetime

    def json(self):
        return json.loads(self.body.decode("utf-8"))

    def text(self, encoding: str = "utf-8") -> str:
        return self.body.decode(encoding, errors="replace")
