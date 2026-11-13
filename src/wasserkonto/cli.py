"""Command line: collect, status, sources, export.

Designed for a timer on a small machine, so it is quiet on success, loud on
failure, and it never needs an argument it could read from the configuration.
"""

from __future__ import annotations

import argparse
import contextlib
import csv
import json
import logging
import sys
from pathlib import Path

from . import registry
from .config import load_config
from .http import PoliteSession
from .sources.base import run_source
from .storage import Archive

log = logging.getLogger("wasserkonto")


def _setup_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
    )


def cmd_collect(args: argparse.Namespace) -> int:
    cfg = load_config(args.config)
    names = args.source or cfg.enabled_sources()
    if not names:
        log.error("no source enabled; see config.example.toml")
        return 2

    failures = 0
    with Archive(cfg.storage.root, cfg.storage.compress_raw) as archive, \
            PoliteSession(cfg.http) as session:
        for name in names:
            source_cfg = cfg.source(name)
            if not args.source and not source_cfg.get("enabled", False):
                continue
            try:
                source = registry.load(name)
            except KeyError as exc:
                log.error("%s", exc)
                failures += 1
                continue
            result = run_source(source, session, archive, source_cfg)
            failures += result["failed"]
            log.info("%s: %d new observations, %d stations, %d fetches%s",
                     name, result["observations"], result["stations"],
                     result["fetches"], " (with errors)" if result["failed"] else "")
    return 1 if failures else 0


def cmd_status(args: argparse.Namespace) -> int:
    cfg = load_config(args.config)
    with Archive(cfg.storage.root, cfg.storage.compress_raw) as archive:
        status = archive.status()
    if args.json:
        json.dump(status, sys.stdout, indent=2)
        print()
        return 0
    print(f"archive   {cfg.storage.root}")
    print(f"stations  {status['stations']}")
    print(f"values    {status['observations']}")
    for row in status["by_source"]:
        print(f"  {row['source']:<14} {row['observations']:>9}  "
              f"{(row['first'] or '')[:10]} .. {(row['last'] or '')[:10]}")
    for row in status["fetches"]:
        if row["ok"] != row["total"]:
            print(f"  ! {row['source']}: {row['total'] - row['ok']} failed fetches")
    return 0


def cmd_sources(_: argparse.Namespace) -> int:
    for name in registry.available():
        print(name)
    return 0


def cmd_export(args: argparse.Namespace) -> int:
    cfg = load_config(args.config)
    with Archive(cfg.storage.root, cfg.storage.compress_raw) as archive:
        query = ("SELECT source, station, parameter, ts, value, unit"
                 " FROM observations")
        params: list[str] = []
        if args.source:
            query += " WHERE source = ?"
            params.append(args.source)
        query += " ORDER BY source, station, parameter, ts"
        rows = archive.db.execute(query, params)
        with contextlib.ExitStack() as stack:
            if args.output == "-":
                handle = sys.stdout
            else:
                handle = stack.enter_context(
                    Path(args.output).open("w", newline="", encoding="utf-8"))
            out = csv.writer(handle)
            out.writerow(["source", "station", "parameter", "ts", "value", "unit"])
            out.writerows(rows)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="wasserkonto")
    parser.add_argument("-c", "--config", help="path to config.toml")
    parser.add_argument("-v", "--verbose", action="store_true")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("collect", help="fetch and archive the enabled sources")
    p.add_argument("source", nargs="*", help="limit to these sources")
    p.set_defaults(func=cmd_collect)

    p = sub.add_parser("status", help="what the archive currently holds")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_status)

    p = sub.add_parser("sources", help="list known sources")
    p.set_defaults(func=cmd_sources)

    p = sub.add_parser("export", help="write observations as CSV")
    p.add_argument("-o", "--output", default="-")
    p.add_argument("--source")
    p.set_defaults(func=cmd_export)

    args = parser.parse_args(argv)
    _setup_logging(args.verbose)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
