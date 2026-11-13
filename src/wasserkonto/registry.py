"""Which sources exist, and the rule that a disabled one does not.

A source listed here is only imported when the configuration enables it. That
is the fourth invariant: disabled means absent, not idle. No placeholder rows,
no half-initialised module, no side effects.
"""

from __future__ import annotations

import importlib
from typing import Any

# name -> "module:class". Importing happens on demand, never at start-up.
SOURCES: dict[str, str] = {
    "pegelonline": "wasserkonto.sources.pegelonline:PegelOnline",
    "brightsky": "wasserkonto.sources.brightsky:BrightSky",
    "gwdat": "wasserkonto.sources.gwdat:Gwdat",
}


def available() -> list[str]:
    return sorted(SOURCES)


def load(name: str) -> Any:
    try:
        target = SOURCES[name]
    except KeyError:
        raise KeyError(
            f"unknown source {name!r}; known: {', '.join(available())}") from None
    module_name, class_name = target.split(":")
    module = importlib.import_module(module_name)
    return getattr(module, class_name)()
