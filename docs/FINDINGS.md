# Findings

Preliminary study on the Saxon slice of GEMS-GER: 140 LfULG wells
(`MW_2565` to `MW_2704`), weekly values from 1991-01-07 to 2022-12-26,
233,660 observations. Estimated with well fixed effects and standard errors
clustered by well.

The German working records this summarises are kept as
[`BEFUNDE.md`](BEFUNDE.md) and [`ROBUSTHEIT.md`](ROBUSTHEIT.md). Where they
disagree with this file, this file is current: it carries a correction they
predate.

## The inventory

140 wells survived the GEMS-GER filters out of Saxony's 1,043 quantity
monitoring wells, a survival rate of 13.4 % against 19 % nationally. This is a
thin, selected slice, chosen for completeness and length of record.

The wells are shallow, with a median depth of 6.7 m and 75 of 140 between 5
and 10 m. That is fortunate rather than planned: shallow aquifers respond
quickly to precipitation, which is the signal the study is after.

Saxony carries two regimes. Below 150 m elevation there are 34 wells with a
median recharge of 88 mm per year. Above 300 m there are 33 wells with 96 mm,
but in hydrogeological district 96, the highest at 417 m median elevation,
recharge is the lowest at 66 mm. Crystalline rock with little storage: the
rain arrives and runs off rather than percolating.

**Three gaps worth stating.** Pressure condition is `Unknown` for all 140
wells. Filter position exists for only 16 of 140, and screen length is a
zero placeholder for 124. Those are precisely the variables that govern
whether a well responds quickly or sluggishly, so differences in response time
cannot be traced to well construction here. The data exists at LfULG; it
simply did not reach GEMS-GER.

## What holds

**Recharge is more than proportional to winter precipitation.** The elasticity
is 1.8, and it sits between 1.78 and 1.85 across all four definitions of the
recharge measure that were tested. Concretely, 18 % less winter precipitation
produced 21 % less recharge.

The shape is a threshold rather than a curvature. Fitting
`rise = a + b · P` gives a negative intercept with a zero crossing near 94 mm
of winter precipitation. A quadratic term is slightly negative, so the curve is
mildly concave, and the earlier description of it as "convex" was imprecise.
The threshold value itself is not well identified: a hockey-stick fit puts it
at 155 mm and gives zero for the hill country. **Quote the elasticity, not the
threshold.**

**Recharge has declined, and less winter rain explains it.** The winter rise
fell by 0.266 m over 30 years (p < 0.001), from a decadal median of 0.705 m in
the 2000s to 0.515 m since 2012. Winter precipitation fell 59 mm (p = 0.052)
and winter temperature rose 1.65 K (p = 0.029).

Control for winter precipitation and the trend vanishes entirely: +0.0008 m
per year at p = 0.484. This holds in all four baseline definitions, none of
which shows a significant negative residual trend.

**The intuitive thesis is refuted.** "The same rainfall produces less recharge
today" is not supported for Saxony over this period.

## What was retracted

Three corrections, in the order they were found. Keeping them visible is
cheaper than having a reviewer find them.

### The lowland exception

An earlier reading had the lowland wells showing a genuine weakening of
response per millimetre (−0.046 over 30 years, p = 0.004). Excluding the
extreme year 2014 it is −0.028 at p = 0.069. The exception does not survive,
and neither does the raw trend in response per millimetre, which moves from
p = 0.041 to p = 0.716 without that single year.

### The word "convex"

See above. The relationship is threshold-like with a negative intercept, not
curved. The elasticity is the robust statement.

### The drift — and the unit error behind it

This is the substantive one.

An earlier version of the transfer model reported that a constant-parameter
model calibrated on 1992–2006 systematically overestimates levels from 2007 to
2022, with a residual drift of −0.0022 m per year at p = 0.008, reproduced in
two independent model structures. Three to four centimetres of unexplained
decline over sixteen years.

**That finding was an artefact.** In GEMS-GER the precipitation column is a
weekly sum while the evaporation columns are daily means in mm/day. Summing
`DWD_evapo_p` over a year gives 96 mm, which is impossible for Saxony;
multiplied by seven it gives 674 mm, which is right. The soil bucket was
therefore being fed one seventh of the real evaporative demand, so it
overflowed far too readily, and the fitted storage capacity ran to the edge of
the search grid in the uplands.

With the units corrected:

| | before (wrong units) | after |
|---|---|---|
| NSE median, in sample | 0.416 | 0.640 |
| share above NSE 0.5, in sample | 32.9 % | 83.6 % |
| seasonal amplitude, model / observed | 0.50 | 0.65 |
| fitted soil storage | ran to grid edge, 600 mm | 172 to 239 mm |
| validation bias | −0.039 m, p = 0.013 | +0.009 m, p = 0.689 |
| residual drift | −0.0022 m/a, p = 0.008 | +0.0015 m/a, p = 0.837 |

**There is no detectable drift.** A model with time-invariant parameters
reproduces 2007–2022 without systematic bias. The claim that the system's
transfer function has measurably changed does not survive the correction, and
anything built on it has to be rebuilt.

The empirical findings above are untouched by this, because they use observed
levels and precipitation only. No evaporation column enters them.

## Model performance, stated fairly

The model is a Thornthwaite-type soil store feeding two parallel linear
groundwater reservoirs. Three fitted parameters: storage capacity, a fast
residence time and a slow one, with the two weights and the level obtained by
least squares.

| | NSE median | above 0.5 |
|---|---|---|
| calibrated and scored on 1992–2022 | 0.640 | 83.6 % |
| **calibrated 1992–2006, scored 2007–2022** | **0.547** | **58.6 %** |

The second row is the one to quote. The best benchmark published with
GEMS-GER, a global LSTM with dynamic and static inputs, reaches NSE above 0.5
for 52 % of wells nationally.

So a three-parameter interpretable process model is **comparable to** a deep
learning benchmark here. It is not a like-for-like comparison: different
subset, different split, different evaluation protocol. The honest claim is
that interpretability does not appear to cost much accuracy on this problem,
not that the simple model wins.

Fitted parameters are physically sensible and regionally ordered: soil storage
172 mm in the lowlands, 203 mm in the hill country, 239 mm in the uplands.

## Limitations

1. **Abstraction is absent.** Part of the decline could be pumping rather than
   climate. Without withdrawal data the two cannot be separated, and this is
   the gap the project exists to close.
2. **Amplitude is still underestimated** by about a third, so the model is
   better at the multi-year signal than at the seasonal swing.
3. **The uplands fit worst** (NSE 0.59). A Thornthwaite bucket is a lowland
   concept and does not describe fractured crystalline rock well.
4. **Selection.** The 140 wells are 13.4 % of Saxony's quantity network,
   chosen for long and complete records. They represent that kind of record,
   not necessarily the state.
5. **Definition dependence.** The size of the decline varies by a factor of
   five across the four baseline definitions, from −7.3 % to −40.7 %. Any
   figure quoting the decline must name its definition.

## Reproducing

```bash
pip install -e ".[analysis]"
# Fetch GEMS-GER separately from Zenodo (10.5281/zenodo.15530171)
# and point the DYN constant at its dynamic/ directory.
python analysis/winter_response.py
python analysis/transfer_model.py
```
