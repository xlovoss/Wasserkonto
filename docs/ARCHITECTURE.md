# Architecture

## The two jobs, kept apart

Collecting and analysing have opposite economics, and mixing them is how a
data archive ends up fitting only the model that happened to be current when
it was built.

**Collecting** is cheap, dumb and has to be exhaustive. It runs every day,
forever, with nobody watching. Its failure mode is a gap in the record.

**Analysing** is expensive, narrow and needs a specific question. Its failure
mode is a model nobody can interpret.

So there is a hard boundary. The archive knows nothing about analysis. The
analysis only reads.

## The operating rule

> Collect greedily where data expires. Collect sparingly where it is archived
> elsewhere.

PEGELONLINE keeps about 30 days, and Saxony's `gwdat` snapshot is overwritten
daily, so both are taken in full every day. DWD station history through Bright
Sky is permanently retrievable, so a handful of points is enough and any gap
can be backfilled later. This single rule settles every scope question in the
project without reopening the argument each time.

## Four invariants

These are what make it safe to enable and disable sources at will. Each one is
a test in `tests/test_storage.py`.

### 1. Raw first

Every response is written to disk verbatim before anything parses it. The
SQLite database is a derived artefact and can be rebuilt from the raw store at
any time.

A parser bug therefore costs a re-run and nothing more. Without this rule,
every parser bug is permanent data loss, because the response it misread is
already gone from the service.

### 2. Append-only and idempotent

An observation is identified by `(source, station, parameter, timestamp)` and
written with `INSERT OR IGNORE`. Running twice, using overlapping lookback
windows, backfilling the same period: all harmless. There is no "already
done" state that can go stale, and nothing to reconcile after a crash.

### 3. Sources are isolated

A source is a plugin that can only yield records. It cannot touch the schema,
cannot see another source's data, and when it raises, the failure is logged
and the run continues. One unreachable service must never abort a collection
run, because the whole value of a daily archive is that it keeps going
unattended.

### 4. Disabled means absent

If the configuration says `enabled = false`, the module is not imported and
not called. No placeholder rows, no half-initialised state, no side effects.

### The acceptance test

Pull the power during a collection run. Expected result: one incomplete raw
file, no ledger entry for it, an intact database, and the next run fills the
gap by itself. `test_survives_the_power_being_pulled` does exactly this by
killing a writing process outright.

## Two kinds of input

Not everything is a time series, and forcing it to be one bends the schema out
of shape.

**Perishable sources** are fetched daily because they are overwritten:
PEGELONLINE, `gwdat`, Bright Sky. They produce observations.

**Static imports** are fetched once and versioned: the GEMS-GER reference
dataset, mGROWA recharge rasters, annual mean maps. They have no schedule, but
they carry a checksum and a version. They do not belong in the observations
table.

Only the first kind is implemented. The second is a separate module contract
and is deliberately not forced into the same shape.

## The module contract

A source provides exactly four things.

1. A `name`.
2. A `collect(ctx)` generator yielding `Observation` and `StationInfo`.
3. Pure parse functions, with no network access.
4. A fixture holding a real recorded response.

Fetching, writing the raw copy, the ledger entry and the database write are
all the core's job. A source never touches disk or the database.

Adding a source is therefore one file, one configuration block and one
fixture, with no change to the core. That is the construction-set property,
and it is also why the whole test suite runs offline.

```python
class MySource:
    name = "mysource"

    def collect(self, ctx):
        payload = ctx.get("https://example.invalid/data.json", "data")
        yield from parse(payload.body)   # pure, testable against the fixture
```

Register it in `registry.py` and give it a section in the configuration.

## Storage layout

```
data/
  archive.sqlite          derived, rebuildable
  raw/
    pegelonline/2026/11/13/stations_20261113T080000Z.json.gz
    brightsky/2026/11/13/dresden_20261113T080500Z.json.gz
```

Raw paths carry the source, the UTC date and the fetch timestamp, so the store
is browsable without the database and a collision can only happen inside the
same second, where a suffix is added rather than overwriting.

Three tables. `fetches` is the provenance ledger, holding url, timestamp,
status, byte count and SHA-256 for every request, successful or not.
`observations` holds the measurements. `stations` holds metadata with
`first_seen` and `last_seen`, because stations are renamed, re-surveyed and
decommissioned over time.

## Timestamps

Observations refuse naive timestamps. German hydrological services publish
times with an offset, in MEZ year-round without an offset, and occasionally as
bare local time. Guessing produces a series shifted by an hour, which is worse
than a missing one, so the parser has to state the timezone the service
documents and the model normalises to UTC.
