"""The archive: a write-once raw store plus a derived SQLite database.

Three invariants hold here, and everything else in the project depends on them.

**Raw first.** Every response is written to disk verbatim before anything parses
it. The database is a derived artefact and can be rebuilt from the raw store at
any time. A parser bug therefore costs nothing but a re-run; without this rule
every parser bug is permanent data loss.

**Append-only and idempotent.** An observation is identified by
(source, station, parameter, timestamp) and inserted with INSERT OR IGNORE.
Running twice, overlapping lookback windows and backfilling the same period are
all harmless, so there is no "already done" state that can go stale or corrupt.

**Every fetch is logged.** The `fetches` table records url, timestamp, HTTP
status, byte count and SHA-256 for each request, successful or not. That ledger
is what makes a figure in a paper traceable back to the exact bytes it came
from.
"""

from __future__ import annotations

import gzip
import hashlib
import logging
import sqlite3
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path

from .models import Observation, StationInfo

log = logging.getLogger(__name__)

SCHEMA = """
CREATE TABLE IF NOT EXISTS fetches (
    id          INTEGER PRIMARY KEY,
    source      TEXT NOT NULL,
    slug        TEXT NOT NULL,
    url         TEXT NOT NULL,
    fetched_at  TEXT NOT NULL,
    http_status INTEGER,
    sha256      TEXT,
    bytes       INTEGER,
    raw_path    TEXT,
    ok          INTEGER NOT NULL,
    error       TEXT
);
CREATE INDEX IF NOT EXISTS fetches_source_time ON fetches (source, fetched_at);

CREATE TABLE IF NOT EXISTS observations (
    source    TEXT NOT NULL,
    station   TEXT NOT NULL,
    parameter TEXT NOT NULL,
    ts        TEXT NOT NULL,
    value     REAL NOT NULL,
    unit      TEXT NOT NULL,
    fetch_id  INTEGER REFERENCES fetches (id),
    PRIMARY KEY (source, station, parameter, ts)
) WITHOUT ROWID;
CREATE INDEX IF NOT EXISTS obs_station_time ON observations (source, station, ts);

CREATE TABLE IF NOT EXISTS stations (
    source     TEXT NOT NULL,
    station    TEXT NOT NULL,
    name       TEXT,
    latitude   REAL,
    longitude  REAL,
    water      TEXT,
    meta       TEXT,
    first_seen TEXT NOT NULL,
    last_seen  TEXT NOT NULL,
    PRIMARY KEY (source, station)
);
"""


class Archive:
    """The raw store and the derived database, under one root directory."""

    def __init__(self, root: Path, compress: bool = True) -> None:
        self.root = Path(root)
        self.compress = compress
        self.raw_root = self.root / "raw"
        self.raw_root.mkdir(parents=True, exist_ok=True)
        self.db_path = self.root / "archive.sqlite"
        self.db = sqlite3.connect(self.db_path, isolation_level=None)
        # WAL keeps the database readable while a collection run writes, and
        # survives the power being pulled mid-run -- which is the stated
        # acceptance test for this project.
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA synchronous=NORMAL")
        self.db.executescript(SCHEMA)

    # ------------------------------------------------------------- raw ----

    def raw_path(self, source: str, slug: str, fetched_at: datetime) -> Path:
        stamp = fetched_at.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")
        suffix = ".gz" if self.compress else ""
        day = fetched_at.astimezone(UTC)
        return (self.raw_root / source / f"{day:%Y/%m/%d}"
                / f"{slug}_{stamp}{suffix}")

    def write_raw(self, source: str, slug: str, fetched_at: datetime,
                  body: bytes) -> tuple[Path, str, int]:
        """Write a response verbatim. Never overwrites: the timestamp is part
        of the name, and a collision means the same second, so we suffix."""
        path = self.raw_path(source, slug, fetched_at)
        path.parent.mkdir(parents=True, exist_ok=True)
        n = 1
        while path.exists():
            path = path.with_name(f"{path.stem}~{n}{path.suffix}")
            n += 1
        if self.compress:
            path.write_bytes(gzip.compress(body))
        else:
            path.write_bytes(body)
        return path, hashlib.sha256(body).hexdigest(), len(body)

    def read_raw(self, path: Path) -> bytes:
        data = Path(path).read_bytes()
        return gzip.decompress(data) if str(path).endswith(".gz") else data

    # ---------------------------------------------------------- ledger ----

    def record_fetch(self, *, source: str, slug: str, url: str,
                     fetched_at: datetime, http_status: int | None,
                     sha256: str | None, nbytes: int | None,
                     raw_path: Path | None, ok: bool,
                     error: str | None = None) -> int:
        cur = self.db.execute(
            "INSERT INTO fetches (source, slug, url, fetched_at, http_status,"
            " sha256, bytes, raw_path, ok, error)"
            " VALUES (?,?,?,?,?,?,?,?,?,?)",
            (source, slug, url, fetched_at.astimezone(UTC).isoformat(),
             http_status, sha256, nbytes,
             str(raw_path.relative_to(self.root)) if raw_path else None,
             int(ok), error),
        )
        return int(cur.lastrowid)

    # ------------------------------------------------------ observations ----

    def insert_observations(self, rows: Iterable[Observation],
                            fetch_id: int | None = None) -> int:
        """Insert measurements, ignoring any that are already present.

        Returns the number of genuinely new rows, which is what makes a
        collection run's output meaningful: a re-run reports zero.
        """
        payload = [(o.source, o.station, o.parameter, o.ts.isoformat(),
                    float(o.value), o.unit, fetch_id) for o in rows]
        if not payload:
            return 0
        before = self.db.execute("SELECT count(*) FROM observations").fetchone()[0]
        self.db.executemany(
            "INSERT OR IGNORE INTO observations"
            " (source, station, parameter, ts, value, unit, fetch_id)"
            " VALUES (?,?,?,?,?,?,?)", payload)
        after = self.db.execute("SELECT count(*) FROM observations").fetchone()[0]
        return after - before

    def upsert_stations(self, rows: Iterable[StationInfo]) -> int:
        now = datetime.now(UTC).isoformat()
        payload = [(s.source, s.station, s.name, s.latitude, s.longitude,
                    s.water, s.meta_json(), now, now) for s in rows]
        if not payload:
            return 0
        self.db.executemany(
            "INSERT INTO stations (source, station, name, latitude, longitude,"
            " water, meta, first_seen, last_seen) VALUES (?,?,?,?,?,?,?,?,?)"
            " ON CONFLICT (source, station) DO UPDATE SET"
            " name=excluded.name, latitude=excluded.latitude,"
            " longitude=excluded.longitude, water=excluded.water,"
            " meta=excluded.meta, last_seen=excluded.last_seen", payload)
        return len(payload)

    # ---------------------------------------------------------- status ----

    def status(self) -> dict:
        q = self.db.execute
        sources = q("SELECT source, count(*), min(ts), max(ts)"
                    " FROM observations GROUP BY source ORDER BY source").fetchall()
        fetches = q("SELECT source, sum(ok), count(*)"
                    " FROM fetches GROUP BY source ORDER BY source").fetchall()
        return {
            "observations": q("SELECT count(*) FROM observations").fetchone()[0],
            "stations": q("SELECT count(*) FROM stations").fetchone()[0],
            "by_source": [
                {"source": s, "observations": n, "first": lo, "last": hi}
                for s, n, lo, hi in sources
            ],
            "fetches": [
                {"source": s, "ok": int(ok or 0), "total": total}
                for s, ok, total in fetches
            ],
        }

    def close(self) -> None:
        self.db.close()

    def __enter__(self) -> Archive:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()
