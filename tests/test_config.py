"""Configuration, including the rule that disabled means absent."""

from __future__ import annotations

import pytest

from wasserkonto.config import load_config

SAMPLE = """
[storage]
root = "./data"
compress_raw = true

[http]
user_agent = "wasserkonto/test"
min_interval_seconds = 0.0

[sources.pegelonline]
enabled = true
timeseries = ["W", "Q"]

[sources.brightsky]
enabled = false
"""


def write(tmp_path, text=SAMPLE):
    path = tmp_path / "config.toml"
    path.write_text(text, encoding="utf-8")
    return path


def test_relative_root_resolves_against_the_config_file(tmp_path):
    """Otherwise a timer and a manual run write to two different archives."""
    cfg = load_config(write(tmp_path))
    assert cfg.storage.root == (tmp_path / "data").resolve()


def test_only_enabled_sources_are_listed(tmp_path):
    cfg = load_config(write(tmp_path))
    assert cfg.enabled_sources() == ["pegelonline"]
    assert cfg.source("brightsky")["enabled"] is False
    assert cfg.source("absent") == {}


def test_http_defaults_survive_a_partial_section(tmp_path):
    cfg = load_config(write(tmp_path))
    assert cfg.http.user_agent == "wasserkonto/test"
    assert cfg.http.max_retries == 3
    assert cfg.http.timeout_seconds == 30.0


def test_missing_file_is_an_error_not_a_silent_default(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_config(tmp_path / "nope.toml")


def test_no_path_falls_back_to_built_in_defaults(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    cfg = load_config(None)
    assert cfg.enabled_sources() == []
    assert cfg.storage.compress_raw is True
