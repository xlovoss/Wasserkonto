"""The module contract every source has to satisfy.

A source provides exactly four things: a name, a `collect` generator, pure
parse functions, and a fixture holding a real response. Fetching, writing the
raw copy, the ledger entry and the database write are the core's job, never the
source's.

That split is what makes the toolkit a construction set. Adding a source is one
file, one configuration block and one fixture, with no change to the core, and
the parse functions can be tested without a network.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Any, Protocol

from ..http import FetchError, PoliteSession
from ..models import Observation, Payload, StationInfo
from ..storage import Archive

log = logging.getLogger(__name__)

Record = Observation | StationInfo


class Context:
    """What a source is handed: a way to fetch, and its own configuration.

    `get` performs the request, writes the raw body, records the ledger entry
    and hands back the bytes. A source never touches disk or the database.
    """

    def __init__(self, source: str, session: PoliteSession, archive: Archive,
                 config: dict[str, Any]) -> None:
        self.source = source
        self.config = config
        self._session = session
        self._archive = archive
        self.fetch_ids: list[int] = []

    def get(self, url: str, slug: str,
            params: dict[str, Any] | None = None) -> Payload:
        now = datetime.now(UTC)
        try:
            resp = self._session.get(url, params=params)
        except FetchError as exc:
            self._archive.record_fetch(
                source=self.source, slug=slug, url=url, fetched_at=now,
                http_status=getattr(exc, "status", None), sha256=None,
                nbytes=None, raw_path=None, ok=False, error=str(exc))
            raise

        path, digest, nbytes = self._archive.write_raw(
            self.source, slug, now, resp.body)
        fetch_id = self._archive.record_fetch(
            source=self.source, slug=slug, url=resp.url, fetched_at=now,
            http_status=resp.status, sha256=digest, nbytes=nbytes,
            raw_path=path, ok=True)
        self.fetch_ids.append(fetch_id)
        return Payload(url=resp.url, slug=slug, body=resp.body,
                       fetch_id=fetch_id, sha256=digest, fetched_at=now)


class Source(Protocol):
    """What the registry expects of a source module's class."""

    name: str

    def collect(self, ctx: Context) -> Iterator[Record]:
        """Yield observations and station metadata.

        Raising is allowed and expected: the runner logs the failure and moves
        on to the next source. One unreachable service must never abort a run.
        """
        ...


def run_source(source: Source, session: PoliteSession, archive: Archive,
               config: dict[str, Any], batch: int = 5000) -> dict[str, int]:
    """Drive one source to completion and write what it produced.

    Failures are caught here, not inside the source, so that a collection run
    always captures as much as it can. The whole point of a daily archive is
    that it keeps going unattended.
    """
    ctx = Context(source.name, session, archive, config)
    observations: list[Observation] = []
    stations: list[StationInfo] = []
    inserted = 0
    failed = False

    try:
        for record in source.collect(ctx):
            if isinstance(record, Observation):
                observations.append(record)
                if len(observations) >= batch:
                    inserted += archive.insert_observations(observations)
                    observations.clear()
            else:
                stations.append(record)
    except Exception as exc:  # noqa: BLE001 - deliberate: one source must not
        failed = True          # take the run down with it.
        log.error("source %s failed: %s", source.name, exc)

    inserted += archive.insert_observations(observations)
    n_stations = archive.upsert_stations(stations)
    return {"observations": inserted, "stations": n_stations,
            "fetches": len(ctx.fetch_ids), "failed": int(failed)}
