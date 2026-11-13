# Analysis

The preliminary study, as it was actually run. These two scripts produce the
numbers in [`../docs/FINDINGS.md`](../docs/FINDINGS.md). They are kept here so
the findings can be checked rather than believed.

They read GEMS-GER, which is not part of this repository and is not
redistributed here. Download it separately from Zenodo, DOI
`10.5281/zenodo.15530171`.

## Running

```bash
pip install -e ".[analysis]"

export GEMS_GER_DYN="/path/to/GEMS-GER_data/dynamic"
export WK_INVENTORY="data/sachsen_inventar.csv"
export WK_OUT="output"

python analysis/winter_response.py
python analysis/transfer_model.py
```

`WK_INVENTORY` points at the Saxon subset of
`static_features_MW_1toMW_3207.csv`, filtered to the 140 wells whose operator
is LfULG. Both scripts need around 2 GB of memory and run in a few minutes on
a laptop.

## What each one does

**`winter_response.py`** builds one row per well and hydrological year with
the winter precipitation sum, the rise from the autumn minimum to the spring
maximum, and the response in metres per millimetre. It then estimates the
elasticity and the residual time trend with well fixed effects and standard
errors clustered by well. This is where the headline result comes from, that
recharge responds more than proportionally to winter precipitation with an
elasticity of 1.8.

**`transfer_model.py`** calibrates a Thornthwaite-type soil store feeding two
parallel linear groundwater reservoirs, per well, by grid search over the
storage capacity and the two residence times, with the weights and the
reference level from non-negative least squares. It scores Nash-Sutcliffe
efficiency both in sample and in a split-sample test calibrated on 1992 to
2006 and scored on 2007 to 2022.

## One thing to be careful about

In GEMS-GER the precipitation column is a weekly sum while the evaporation
columns are daily means in mm per day. They have to be put on the same scale
before they enter a water balance. `transfer_model.py` multiplies evaporation
by seven for exactly this reason, and the line is commented so it does not
look like a stray constant.

Getting this wrong costs more than accuracy. It produced an apparent
systematic drift in the earlier version of this model that disappeared once
the units were fixed. The retraction is documented in
[`../docs/FINDINGS.md`](../docs/FINDINGS.md).
