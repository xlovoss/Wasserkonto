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

Scored exactly as the GEMS-GER supplement prescribes: all 521 test weeks from
2013-01-07 to 2022-12-26, imputed values included, and an NSE denominator
built from the **historical 1991–2012 mean** rather than the mean of the test
window. That last detail is not a convention this project chose, and it is not
cosmetic. Test-period levels are lower than the historical mean, so the
denominator is larger and the score higher.

All four rows below are the same 140 Saxon wells, the same weeks, the same
formula.

All figures below use **GEMS-GER v5** and the **revised 20-member benchmark
scores**, which replaced the ones printed in Table 3 of the paper.

| Model on the 140 Saxon wells | NSE median | above 0.5 | RMSE median | Bias median |
|---|---|---|---|---|
| GEMS-GER global LSTM, dyn + static | 0.634 | 77.9 % | 0.298 m | +0.029 m |
| GEMS-GER single-well CNN | 0.629 | 76.4 % | 0.286 m | +0.025 m |
| GEMS-GER global LSTM, dynamic only | 0.612 | 69.3 % | 0.304 m | +0.014 m |
| **This model, three parameters** | **0.549** | **63.6 %** | **0.320 m** | **+0.015 m** |

Per well, the process model beats the single-well CNN on 35.7 % of wells, the
dynamic-only LSTM on 42.9 %, and the dyn+static LSTM on 37.1 %. Median
differences are −0.085, −0.033 and −0.074.

**So the model is behind all three, and the margin against the weakest of them
is small.** Three earlier claims about this number are withdrawn: parity with
the benchmark (wrong split), 0.418 (correct split, wrong denominator), and any
comparison of a Saxon figure against the national medians, which in the revised
scores are 0.518, 0.493 and 0.440. Saxony is an easier subset than Germany as a
whole, which the table above shows directly: all three published models score
far better here than nationally.

### Two supplement updates, and one approximation that did not hold

Two separate corrections landed on this dataset, and they are easy to confuse.

**The data fix (v5).** Evaporation columns were weekly means of daily sums
rather than weekly sums, and `DWD_soil_moist` had been divided by ten a second
time. This project had been multiplying evaporation by seven as a stand-in.
That was close but **not equivalent**: the median NSE moves only from 0.546 to
0.549, yet 65 of the 140 wells shift by more than 0.001 and one by 0.69. The
workaround is gone; `EVAPO_SCALE` is 1.0 and v5 is required.

**The score revision.** The published Table 3 mixed two model runs with
different aggregation orders. The replacement recalculates every metric from
the pointwise median of a 20-member ensemble. On the Saxon wells it moves the
single-well CNN by −0.006 and both LSTMs by about +0.017, enough to reorder
them: the dyn+static LSTM now edges out the CNN here. The supplement also
switched its CSV separator from semicolon to comma, which is why the reader
sniffs it.

### A failure mode the model shares with the benchmark

Marc Ohmer (KIT) reported that the benchmark models struggle with the late
recession limb and overestimate annual minima, and asked whether the process
model does the same. It does, and more plainly than the aggregate bias
suggests.

| | Bias, median over wells |
|---|---|
| all 521 test weeks | +0.017 m |
| observations in the lowest decile | +0.365 m |
| annual minima | +0.279 m |

**Every one of the 140 wells overestimates its annual minima more than its
average.**

With the supplement's `median_predictions.csv.gz` the same diagnostic runs on
the three published models, so this is now measured for all four rather than
measured for one and quoted for the rest.

| Model | bias, all weeks | lowest decile | annual minima | wells where minima are worse than average |
|---|---|---|---|---|
| single-well CNN | +0.025 m | +0.180 m | +0.160 m | 92.1 % |
| global LSTM, dyn + static | +0.029 m | +0.293 m | +0.241 m | 98.6 % |
| global LSTM, dynamic only | +0.014 m | +0.307 m | +0.250 m | 99.3 % |
| three-parameter water balance | +0.017 m | +0.365 m | +0.279 m | 100.0 % |

**All four fail in the same place and in the same direction**, and the
severity tracks overall skill: the strongest model is least affected, the
simplest most. On the 65 wells whose annual minimum drops below the
calibration-period minimum at least once, the error at those minima is +1.08,
+1.51, +1.47 and +1.61 standard deviations respectively — the same order of
magnitude for a convolutional network and for three fitted parameters.

Nearly half the wells, 65 of 140, went below anything seen in 1991–2007 during
the test decade. That is the scale of the regime change the models are being
asked to extrapolate into.

### What drives that error, and what does not

Ohmer's explanation for the neural models is that comparably low levels were
rare or absent in training. For a three-parameter water balance that argument
does not transfer: it learns no value range, it integrates a balance. So the
error was split by two candidate causes.

Each annual minimum in the test window is measured against that well's
**minimum during calibration** (1991–2007), and both the shortfall and the
model error are expressed in units of that well's own standard deviation
during calibration, so that wells with large swings do not dominate.

| Annual minimum falls below the calibration minimum by | n | median error |
|---|---|---|
| it does not | 1197 | 0.56 sd |
| 0 to 0.25 sd | 82 | 1.14 sd |
| 0.25 to 0.5 sd | 56 | 1.40 sd |
| 0.5 to 1 sd | 44 | 1.89 sd |
| more than 1 sd | 21 | 3.23 sd |

Pearson r = +0.63, Spearman +0.52. In metres the medians run from 0.22 m to
2.48 m across the same buckets.

**Length of the recession explains nothing** (r = +0.008). It is not that long
recessions flatten out. It is specifically leaving the range the parameters
were fitted in.

So both model families fail for the same reason, by the same measure, though
the mechanism cannot be the same. A network extrapolates outside its training
distribution; a water balance extrapolates with parameters calibrated to a
regime, and a linear reservoir empties exponentially toward a fixed level that
deep droughts undercut.

**This is testable.** A storage-dependent, non-linear outflow should reduce
the deep-minimum bias while leaving ordinary years untouched. If it does, the
structure is the cause here, and the agreement with the neural models is a
coincidence of symptom rather than of mechanism.

### A note on the standardised overview figure

In Ohmer's figure of all 3,207 wells, z is formed over 1991–2022, so the low
test years are inside the reference mean and shrink the very anomaly the
figure shows. On the 140 Saxon wells the median test-window anomaly is −0.28
standard deviations against the full period, and **−0.42 against 1991–2012
alone**, a factor of 1.5. The same point explains the NSE denominator: the
benchmark references 1991–2012, which is why scores computed that way sit
above scores computed against the test-window mean.

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
