"""Configuration loading.

The config file is TOML and read with the standard library, so a Raspberry Pi
needs no extra dependency for it.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

DEFAULT_USER_AGENT = (
    "wasserkonto/0.1 (research data archive; "
    "https://github.com/your-user/wasserkonto)"
)


@dataclass(slots=True)
class HttpConfig:
    user_agent: str = DEFAULT_USER_AGENT
    timeout_seconds: float = 30.0
    min_interval_seconds: float = 1.0
    max_retries: int = 3


@dataclass(slots=True)
class StorageConfig:
    root: Path = Path("./data")
    compress_raw: bool = True


@dataclass(slots=True)
class Config:
    storage: StorageConfig = field(default_factory=StorageConfig)
    http: HttpConfig = field(default_factory=HttpConfig)
    sources: dict[str, dict[str, Any]] = field(default_factory=dict)
    path: Path | None = None

    def source(self, name: str) -> dict[str, Any]:
        return self.sources.get(name, {})

    def enabled_sources(self) -> list[str]:
        return [
            name
            for name, cfg in sorted(self.sources.items())
            if cfg.get("enabled", False)
        ]


def _resolve_root(root: str, config_path: Path | None) -> Path:
    """Relative storage roots are resolved against the config file, not the
    current working directory -- otherwise a systemd timer and a manual run
    would write to two different archives."""
    p = Path(root).expanduser()
    if p.is_absolute() or config_path is None:
        return p.resolve()
    return (config_path.parent / p).resolve()


def load_config(path: str | Path | None = None) -> Config:
    """Load a config file. With no path, look for config.toml next to the
    repository root and fall back to built-in defaults."""
    if path is None:
        candidate = Path.cwd() / "config.toml"
        if not candidate.exists():
            return Config()
        path = candidate

    config_path = Path(path).expanduser().resolve()
    if not config_path.exists():
        raise FileNotFoundError(f"config file not found: {config_path}")

    with config_path.open("rb") as fh:
        raw = tomllib.load(fh)

    storage_raw = raw.get("storage", {})
    storage = StorageConfig(
        root=_resolve_root(storage_raw.get("root", "./data"), config_path),
        compress_raw=bool(storage_raw.get("compress_raw", True)),
    )

    http_raw = raw.get("http", {})
    http = HttpConfig(
        user_agent=http_raw.get("user_agent", DEFAULT_USER_AGENT),
        timeout_seconds=float(http_raw.get("timeout_seconds", 30.0)),
        min_interval_seconds=float(http_raw.get("min_interval_seconds", 1.0)),
        max_retries=int(http_raw.get("max_retries", 3)),
    )

    return Config(
        storage=storage,
        http=http,
        sources=dict(raw.get("sources", {})),
        path=config_path,
    )
