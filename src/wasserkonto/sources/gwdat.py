"""gwdat: Saxony's daily groundwater snapshot (LfULG).

This is the perishable source the whole archive exists for. gwdat is a point
dataset regenerated **every day** and overwritten in place, so a day that is
not captured is gone permanently. Per the Steckbrief it carries, for each
monitoring point: identifier, name, type, coordinates in EPSG:25833, measuring
point and ground elevation, the latest and previous reading in metres below
ground with their dates, the difference, **the deviation from the long-term
monthly mean**, the lowest and highest value ever recorded with dates, the mean
high level or mean discharge, the data period, and the number of complete
hydrological years. The field `DART` separates groundwater level from spring
discharge.

That deviation column matters twice over. It is LfULG's own anomaly figure, so
it is an official reference against which this project's anomaly calculation
can be checked rather than merely asserted.

**Status.** Archiving works and is the urgent half: the raw file is fetched and
stored verbatim under the ledger, which is what cannot be done retroactively.
Parsing the attribute table into observations is not implemented yet, because
the download URL has not been confirmed against the live service and this
project does not ship a guessed endpoint. Set `url` in the configuration to
switch the source on; until then it stays disabled and the core never imports
it.

Attribution required by the data terms: Saxon State Office for Environment,
Agriculture and Geology (LfULG), no warranty.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator

from .base import Context, Record

log = logging.getLogger(__name__)


class Gwdat:
    name = "gwdat"

    def collect(self, ctx: Context) -> Iterator[Record]:
        url = ctx.config.get("url")
        if not url:
            raise RuntimeError(
                "gwdat needs an explicit 'url' in the configuration. "
                "The daily snapshot is published by LfULG; confirm the current "
                "download link before enabling this source.")

        # Raw first: preserve today's snapshot before anything tries to read
        # it. Even with no parser, this is the half that cannot be redone.
        payload = ctx.get(url, "gwdat_snapshot")
        log.info("archived gwdat snapshot, %d bytes, sha256 %s",
                 len(payload.body), payload.sha256[:12])

        # Parsing deliberately not implemented. See the module docstring.
        return
        yield  # pragma: no cover - keeps the function a generator
