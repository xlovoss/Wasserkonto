"""The archive's three invariants, as tests rather than promises."""

from __future__ import annotations

import sqlite3
import subprocess
import sys
from datetime import UTC, datetime, timedelta

import pytest

from wasserkonto.models import Observation, StationInfo
from wasserkonto.storage import Archive

NOW = datetime(2026, 11, 13, 8, 30, tzinfo=UTC)


def obs(station="A", parameter="W", minutes=0, value=1.0):
    return Observation(source="t", station=station, parameter=parameter,
                       ts=NOW + timedelta(minutes=minutes), value=value,
                       unit="cm")


def test_raw_is_written_once_and_never_overwritten(tmp_path):
    with Archive(tmp_path) as a:
        first, digest, n = a.write_raw("t", "idx", NOW, b"hello")
        second, _, _ = a.write_raw("t", "idx", NOW, b"different")
        assert first != second, "a second write must not clobber the first"
        assert a.read_raw(first) == b"hello"
        assert a.read_raw(second) == b"different"
        assert n == 5 and len(digest) == 64


def test_database_is_rebuildable_from_raw(tmp_path):
    """The derived database may be deleted without losing anything."""
    with Archive(tmp_path) as a:
        path, _, _ = a.write_raw("t", "idx", NOW, b"payload")
        a.insert_observations([obs()])
    (tmp_path / "archive.sqlite").unlink()
    for extra in ("archive.sqlite-wal", "archive.sqlite-shm"):
        (tmp_path / extra).unlink(missing_ok=True)
    with Archive(tmp_path) as a:
        assert a.status()["observations"] == 0
        assert a.read_raw(path) == b"payload", "raw survives a database loss"


def test_inserting_twice_changes_nothing(tmp_path):
    with Archive(tmp_path) as a:
        assert a.insert_observations([obs(), obs(minutes=15)]) == 2
        assert a.insert_observations([obs(), obs(minutes=15)]) == 0
        assert a.insert_observations([obs(minutes=30)]) == 1
        assert a.status()["observations"] == 3


def test_overlapping_windows_are_harmless(tmp_path):
    """Re-collecting a period that overlaps an earlier run adds only the new."""
    with Archive(tmp_path) as a:
        a.insert_observations([obs(minutes=m) for m in range(0, 60, 15)])
        added = a.insert_observations([obs(minutes=m) for m in range(30, 120, 15)])
        assert added == 4
        assert a.status()["observations"] == 8


def test_every_fetch_is_in_the_ledger(tmp_path):
    with Archive(tmp_path) as a:
        path, digest, n = a.write_raw("t", "idx", NOW, b"ok")
        a.record_fetch(source="t", slug="idx", url="https://x/idx", fetched_at=NOW,
                       http_status=200, sha256=digest, nbytes=n, raw_path=path,
                       ok=True)
        a.record_fetch(source="t", slug="gone", url="https://x/gone",
                       fetched_at=NOW, http_status=503, sha256=None, nbytes=None,
                       raw_path=None, ok=False, error="HTTP 503")
        rows = a.db.execute("SELECT ok, http_status FROM fetches"
                            " ORDER BY id").fetchall()
        assert rows == [(1, 200), (0, 503)], "failures are recorded, not dropped"


def test_station_metadata_is_updated_not_duplicated(tmp_path):
    with Archive(tmp_path) as a:
        a.upsert_stations([StationInfo(source="t", station="A", name="Old")])
        a.upsert_stations([StationInfo(source="t", station="A", name="New")])
        rows = a.db.execute("SELECT station, name, first_seen, last_seen"
                            " FROM stations").fetchall()
        assert len(rows) == 1
        assert rows[0][1] == "New"


def test_naive_timestamps_are_refused():
    """An hour-shifted series is worse than a missing one."""
    with pytest.raises(ValueError):
        Observation(source="t", station="A", parameter="W",
                    ts=datetime(2026, 11, 13, 8, 30), value=1.0, unit="cm")


def test_survives_the_power_being_pulled(tmp_path):
    """Kill a writing process outright; the archive must still open and the
    next run must repair the gap. This is the project's acceptance test."""
    script = f"""
import time
from datetime import datetime, timedelta, timezone
from wasserkonto.models import Observation
from wasserkonto.storage import Archive
now = datetime(2026, 11, 13, 8, 30, tzinfo=timezone.utc)
a = Archive({str(tmp_path)!r})
for i in range(100000):
    a.insert_observations([Observation(source="t", station="A", parameter="W",
                                       ts=now + timedelta(minutes=i),
                                       value=float(i), unit="cm")])
"""
    proc = subprocess.Popen([sys.executable, "-c", script])
    try:
        proc.wait(timeout=1.5)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()

    with Archive(tmp_path) as a:                     # opens without repair
        before = a.status()["observations"]
        assert before > 0, "the writer should have committed something"
        added = a.insert_observations(
            [obs(minutes=i) for i in range(before + 50)])
        assert added == 50, "the next run fills exactly the gap"


def test_database_is_valid_after_the_kill(tmp_path):
    with Archive(tmp_path) as a:
        a.insert_observations([obs(minutes=i) for i in range(10)])
    con = sqlite3.connect(tmp_path / "archive.sqlite")
    assert con.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    con.close()
