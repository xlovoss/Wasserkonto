# wasserkonto

An archive and analysis toolkit for German water data, built around a single
premise: **we cannot manage what we cannot attribute.**

Germany measures water more densely than almost any other environmental
variable. All sixteen states run public gauge portals that update
continuously, and more than 17,000 groundwater wells carry long records. Yet
when the Oder fish kill of August 2022 was investigated, the official report
could not determine where the decisive salt load came from. Half the water in
the Spree at Cottbus is pumped mine water, so no measured record holds a
natural reference state for that river at all.

This repository holds two things. An **archive** that captures open water data
every day, including the parts that are overwritten and lost if nobody saves
them. And the **analysis** of 140 Saxon groundwater wells over 32 years that
motivated the project.

## Status

Early. The archive core is complete and tested, with two working sources. The
analysis reproduces the findings in [`docs/FINDINGS.md`](docs/FINDINGS.md).
Everything else is scaffolding.

| Part | State |
|---|---|
| Archive core, ledger, CLI | working, 20 tests |
| PEGELONLINE source | working |
| Bright Sky (DWD) source | working |
| gwdat (Saxony, daily) | archives raw only, download URL unconfirmed |
| Analysis | reproduces the preliminary study |
| Forecast model, drift monitor | not started |

## Why an archive at all

Some of this data is perishable. PEGELONLINE keeps roughly the last 30 days.
Saxony's `gwdat` groundwater snapshot is regenerated and overwritten every
single day. A day that nobody captures is gone permanently, and no budget or
later project brings it back.

That gives the operating rule the whole design follows:

> **Collect greedily where data expires. Collect sparingly where it is
> archived elsewhere.**

Four invariants make it safe to switch sources on and off without ever
damaging what is already stored. They are described in
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) and each one is a test, not a
promise — including pulling the power mid-write.

## Quick start

```bash
pip install -e ".[dev]"
cp config.example.toml config.toml   # then edit it
wasserkonto sources
wasserkonto collect
wasserkonto status
```

A collection run is quiet on success and never aborts because one service is
down. A failed fetch is recorded in the ledger and the run continues.

To run it unattended on a Raspberry Pi, see [`deploy/`](deploy/).

## What the data showed

The preliminary study covers 140 LfULG wells in Saxony, 233,660 weekly values
from 1991 to 2022, taken from the open GEMS-GER reference dataset.

- Recharge responds **disproportionately** to winter precipitation, with an
  elasticity of 1.8. Eighteen percent less winter rain produced twenty-one
  percent less recharge.
- The intuitive thesis that the same rainfall has a weaker effect today is
  **not supported**. Once winter precipitation is controlled for, the time
  trend disappears in all four definitions of the recharge measure that were
  tested.
- A three-parameter interpretable process model, calibrated on 1992 to 2006
  and scored on the unseen 2007 to 2022, reaches NSE above 0.5 for **59
  percent** of wells. The deep-learning benchmark published with GEMS-GER
  reaches 52 percent nationally. The two are not measured on the same subset
  or the same split, so the fair reading is that interpretability does not
  appear to cost much accuracy here, not that the simple model wins.

Full detail, including what was retracted and why, is in
[`docs/FINDINGS.md`](docs/FINDINGS.md).

## Repository layout

```
src/wasserkonto/     archive core: storage, ledger, HTTP, CLI
src/wasserkonto/sources/   one file per data source
analysis/            the preliminary study, as it was run
tests/               invariants and parsers, no network needed
docs/                architecture, data sources, findings
deploy/              systemd units for unattended collection
```

## Data sources and licences

Each source, what it offers, how perishable it is and under what terms, is
listed in [`docs/DATA_SOURCES.md`](docs/DATA_SOURCES.md). Attribution
requirements differ by provider and are the user's responsibility.

This repository contains no third-party data. The GEMS-GER dataset is
available separately under its own licence and is not redistributed here.

## Licence

MIT, see [LICENSE](LICENSE).
