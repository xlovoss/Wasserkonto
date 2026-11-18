"""Der Minima-Fehler fuer alle vier Modelle, mit derselben Messvorschrift.

Bisher war die Aussage halb gemessen und halb zitiert: fuer das Prozessmodell
gerechnet, fuer die Benchmarkmodelle aus Marc Ohmers Mail uebernommen. Mit der
Datei median_predictions.csv.gz aus dem Supplement laesst sich fuer alle drei
veroeffentlichten Modelle dasselbe rechnen.

Gemessen wird je Messstelle im Testfenster 2013 bis 2022:

    Bias ueber alle 521 Wochen
    Bias im untersten Dezil der Beobachtungen
    Bias an den Jahresminima
    Fehler an den Minima nach Tiefe unterhalb des Kalibrierminimums,
      normiert auf die Standardabweichung der Messstelle 1991 bis 2007

Positiv heisst, das Modell liegt ueber der Beobachtung.

Die Korrekturen in GEMS-GER v5 betreffen DWD_evapo_* und DWD_soil_moist. Die
Spalte GWL ist unveraendert, deshalb gelten Beobachtungen, Minima und
historische Mittelwerte unabhaengig von der Fassung.
"""

from __future__ import annotations

import argparse
import glob
import os

import numpy as np
import pandas as pd

MODELS = {"single_median": "single", "dynonly_median": "dynonly", "dynstat_median": "dynstat"}
TEST_FROM = pd.Timestamp("2013-01-07")
TEST_TO = pd.Timestamp("2022-12-26")


def diagnose(obs: np.ndarray, sim: np.ndarray, years: np.ndarray,
             train_min: float, train_sd: float) -> dict:
    resid = sim - obs
    q10 = np.quantile(obs, 0.10)
    mins, depths = [], []
    for y in np.unique(years):
        k = years == y
        i = int(np.argmin(obs[k]))
        mins.append(resid[k][i])
        depths.append((train_min - obs[k][i]) / train_sd)
    return {
        "bias_all": float(resid.mean()),
        "bias_low_decile": float(resid[obs <= q10].mean()),
        "bias_minima": float(np.mean(mins)),
        "minima_worse_than_mean": bool(np.mean(mins) > resid.mean()),
        "deep_minima_error_sd": float(np.mean([m / train_sd for m, dd in zip(mins, depths) if dd > 0]))
        if any(dd > 0 for dd in depths) else np.nan,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dynamic", default=os.environ.get("GEMS_GER_DYN", "data/gems-ger/dynamic"))
    ap.add_argument("--predictions", required=True, help="median_predictions.csv.gz")
    ap.add_argument("--mine", default=None, help="eigene predictions.csv, optional")
    ap.add_argument("--output", default=os.environ.get("WK_OUT", "output"))
    args = ap.parse_args()

    wells = {os.path.basename(p)[:-4]: p
             for p in glob.glob(os.path.join(args.dynamic, "MW_*.csv"))}
    print(f"Messstellen mit Beobachtungen vor Ort: {len(wells)}")

    obs_store = {}
    for ident, path in wells.items():
        d = pd.read_csv(path, parse_dates=[0], index_col=0)
        te = (d.index >= TEST_FROM) & (d.index <= TEST_TO)
        tr = (d.index.year >= 1991) & (d.index.year <= 2007)
        g = d["GWL"].to_numpy(float)
        obs_store[ident] = {
            "dates": d.index[te], "obs": g[te], "years": d.index[te].year.to_numpy(),
            "train_min": float(g[tr].min()), "train_sd": float(g[tr].std(ddof=0)),
        }

    rows = []
    reader = pd.read_csv(args.predictions, chunksize=521 * 200)
    carry = pd.DataFrame()
    for chunk in reader:
        chunk = pd.concat([carry, chunk], ignore_index=True)
        complete = chunk.ID.map(chunk.ID.value_counts()) == 521
        carry = chunk[~complete]
        for ident, block in chunk[complete].groupby("ID", sort=False):
            if ident not in obs_store:
                continue
            o = obs_store[ident]
            if len(block) != len(o["obs"]):
                continue
            for column, name in MODELS.items():
                rows.append({"ID": ident, "model": name,
                             **diagnose(o["obs"], block[column].to_numpy(float),
                                        o["years"], o["train_min"], o["train_sd"])})

    if args.mine and os.path.exists(args.mine):
        mine = pd.read_csv(args.mine)
        for ident, block in mine.groupby("ID", sort=False):
            if ident not in obs_store:
                continue
            o = obs_store[ident]
            rows.append({"ID": ident, "model": "prozessmodell",
                         **diagnose(o["obs"], block.iloc[:, 2].to_numpy(float),
                                    o["years"], o["train_min"], o["train_sd"])})

    res = pd.DataFrame(rows)
    os.makedirs(args.output, exist_ok=True)
    res.to_csv(os.path.join(args.output, "minima_all_models.csv"), index=False)

    order = ["single", "dynstat", "dynonly", "prozessmodell"]
    present = [m for m in order if m in set(res.model)]
    print(f"Messstellen je Modell: {res.groupby('model').size().to_dict()}")
    print()
    print(f"{'Modell':<16}{'Bias alle':>11}{'unt. Dezil':>12}{'Jahresminima':>14}"
          f"{'Minima schlechter':>19}")
    for m in present:
        s = res[res.model == m]
        print(f"{m:<16}{s.bias_all.median():>+11.3f}{s.bias_low_decile.median():>+12.3f}"
              f"{s.bias_minima.median():>+14.3f}{s.minima_worse_than_mean.mean() * 100:>18.1f}%")
    print()
    print("Fehler an Minima unterhalb des Kalibrierminimums, in Standardabweichungen:")
    for m in present:
        s = res[res.model == m].deep_minima_error_sd.dropna()
        if len(s):
            print(f"  {m:<16} Median {s.median():+.2f} sd   (n = {len(s)} Messstellen)")


if __name__ == "__main__":
    main()
