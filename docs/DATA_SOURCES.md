# Data sources

What exists, how perishable it is, and on what terms. Attribution
requirements differ by provider and are the user's responsibility.

## Implemented

### PEGELONLINE (WSV)

Gauges on Germany's federal waterways. REST API, no key, no documented rate
limit, which is exactly why the client here waits a second between requests.

- Holds roughly the **last 30 days**. Perishable.
- One index call with `includeTimeseries=true` returns every station with its
  available series and their units.
- Water level in cm, discharge in m³/s. Timestamps carry an explicit offset.
- Base: `https://www.pegelonline.wsv.de/webservices/rest-api/v2`

### Bright Sky (DWD)

An open JSON API over DWD station observations and MOSMIX forecasts.

- History is **permanently retrievable**. Not perishable.
- Queried by coordinate rather than by station.
- Precipitation mm, temperature °C, humidity %, sunshine min, wind km/h,
  pressure hPa, solar kWh/m².
- Base: `https://api.brightsky.dev/weather`

### gwdat (LfULG Saxony) — archiving only

The reason this project has an archive at all.

- A point dataset in EPSG:25833, **regenerated and overwritten every day**.
  Maximally perishable.
- Per monitoring point: identifier, name, type, coordinates, measuring point
  and ground elevation, latest and previous reading in metres below ground
  with dates, the difference, **the deviation from the long-term monthly
  mean**, lowest and highest ever recorded with dates, mean high level or mean
  discharge, data period, and the number of complete hydrological years. The
  field `DART` separates groundwater level from spring discharge.
- Thresholds in the source: a value counts as current only if the latest
  reading is at most seven days old and the previous one at most fourteen.
  Monthly means need at least ten complete hydrological years, the full
  dataset at least four.
- The deviation column is LfULG's **own** anomaly figure, which makes it an
  official reference to check this project's anomaly calculation against
  rather than merely asserting it.
- Attribution: Saxon State Office for Environment, Agriculture and Geology
  (LfULG). No warranty.
- **The download URL is not confirmed here.** The source archives the raw file
  from a URL you configure and does not parse it yet. This project does not
  ship a guessed endpoint.

## Known and not implemented

### GEMS-GER (static import)

The open ML reference dataset the analysis rests on. 3,207 wells, 32 years of
weekly values, meteorological forcing and extensive site attributes.

- CSV, one file per well plus `static_features_MW_1toMW_3207.csv`.
- Zenodo DOI `10.5281/zenodo.15530171`; code `10.5281/zenodo.17855212`.
- Saxony's slice is 140 wells, `MW_2565` to `MW_2704`, operator LfULG.
- A static import, not a scheduled source. Not redistributed in this
  repository.

**Two traps in this dataset, both found the hard way.**

`GWL_flag` reads inversely to the obvious interpretation. 98.8 % of values are
`True` and 1.2 % are `False`. Since the paper reports an average imputation
share of 1.05 %, `False` marks the imputed values and `True` the measured
ones.

The evaporation columns are **daily means in mm/day**, while precipitation is
a **weekly sum**. Summing `DWD_evapo_p` over a year gives 96 mm, which is
absurd; multiplied by seven it gives 674 mm, which is right for Saxony.
Mixing the two scales in a water balance under-weights evaporation sevenfold.
See `docs/FINDINGS.md` for what that cost.

### Länderübergreifendes Hochwasserportal (LHP)

Current gauge readings for all sixteen states through the MIT-licensed
`lhpapi` package. Water level in cm, warning stage 0 to 4, discharge in m³/s.
Current values only, so archiving it is what creates the history.

### iDA / LUIS (Saxony)

Saxony's interactive environmental data portal. Not automatable: export is to
Excel rather than CSV, requires a login, caps daily means at 100 gauges or
100,000 values per export and 15-minute values at one gauge, and offers only
currently active gauges for daily means. A research route for humans, not a
data channel for a machine.

### mGROWA recharge rasters

Groundwater recharge for the climate normal periods 1961–1990, 1971–2000,
1981–2010 and 1991–2020, plus projections. Useful as an independent reference
for recharge estimates. A static import.

## A warning about the open-data portals

The federal harvesters mirror state metadata unevenly. One record filed under
Saxony as a groundwater monitoring WFS actually contains Berlin data, with the
Berlin Senate administration as publisher. Trust the state geoportal, not the
aggregator.

Most Saxon water entries carry `non_open` with an openness score of 1, meaning
they are map layers rather than downloadable datasets.
