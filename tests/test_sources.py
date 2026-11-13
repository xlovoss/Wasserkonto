"""Parsing tests run against recorded responses, so they need no network.

That is the point of the module contract: the parse functions are pure, so a
source can be verified offline and in CI.
"""

from __future__ import annotations

import json
from datetime import UTC
from pathlib import Path

import pytest

from wasserkonto import registry
from wasserkonto.sources.brightsky import parse_weather
from wasserkonto.sources.pegelonline import parse_index, parse_measurements

FIXTURES = Path(__file__).parent / "fixtures"


def fixture(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


def test_pegelonline_index_gives_stations_and_units():
    stations, units = parse_index(fixture("pegelonline_stations.json"))
    assert [s.name for s in stations] == ["DRESDEN", "SCHOENA"]
    dresden = stations[0]
    assert dresden.water == "ELBE"
    assert dresden.latitude == pytest.approx(51.054459)
    assert units[dresden.station] == {"W": "cm", "Q": "m³/s"}
    # The second gauge offers no discharge, which the collector must respect.
    assert "Q" not in units[stations[1].station]


def test_pegelonline_measurements_are_normalised_to_utc():
    rows = parse_measurements(fixture("pegelonline_measurements.json"),
                              station="abc", parameter="W", unit="cm")
    assert len(rows) == 3
    first = rows[0]
    assert first.ts.tzinfo is UTC
    assert first.ts.hour == 5, "+01:00 local becomes 05:00 UTC"
    assert first.value == 142.0 and first.unit == "cm"


def test_pegelonline_skips_rows_without_a_value():
    payload = json.dumps([
        {"timestamp": "2026-11-10T06:00:00+01:00", "value": 1.0},
        {"timestamp": "2026-11-10T06:15:00+01:00"},
        {"value": 2.0},
    ]).encode()
    rows = parse_measurements(payload, "abc", "W", "cm")
    assert len(rows) == 1


def test_brightsky_expands_one_record_into_parameters():
    rows = parse_weather(fixture("brightsky_weather.json"), station="goerlitz")
    names = {r.parameter for r in rows}
    assert {"precipitation", "temperature", "wind_speed"} <= names
    # solar is null in the first hour and present in the second, so it appears
    # once rather than as a fabricated zero.
    assert sum(r.parameter == "solar" for r in rows) == 1
    assert all(r.ts.tzinfo is UTC for r in rows)
    precip = [r for r in rows if r.parameter == "precipitation"]
    assert [r.value for r in precip] == [0.4, 0.0]
    assert {r.unit for r in precip} == {"mm"}


def test_registry_only_imports_what_is_asked_for():
    assert registry.available() == ["brightsky", "gwdat", "pegelonline"]
    assert registry.load("pegelonline").name == "pegelonline"
    with pytest.raises(KeyError):
        registry.load("nope")


def test_gwdat_refuses_to_guess_its_endpoint():
    """A source without a confirmed URL must fail loudly, not invent one."""
    source = registry.load("gwdat")

    class Ctx:
        config: dict = {}

    with pytest.raises(RuntimeError, match="url"):
        list(source.collect(Ctx()))
