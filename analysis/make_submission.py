"""Erzeugt die Codabench-Einreichung fuer den GEMS-GER Community Benchmark.

Ausgabe ist ein Verzeichnis mit

    predictions.csv   ID, Date, prediction fuer jede ausgewaehlte Messstelle
                      und alle 521 Testwochen von 2013-01-07 bis 2022-12-26
    model.json        Modelldokumentation
    submission.zip    beides gepackt

Der Aufbau von predictions.csv folgt dem Layout der veroeffentlichten Datei
median_predictions.csv, also Sortierung nach numerischer MW_ID und darin nach
Datum, Datumsformat YYYY-MM-DD, volle float64-Genauigkeit.

**Vor dem Hochladen den Spaltennamen gegen das Starting Kit pruefen.** Das Kit
liegt auf der Codabench-Seite und war von hier nicht lesbar. Falls dort eine
andere Bezeichnung als `prediction` verlangt wird, genuegt --column.

Zur Kontrolle werden die Scores mit der Funktion aus evaluation.py des
GEMS-GER-Repositorys berechnet, also mit dem Code der Benchmark-Autoren und
nicht mit einer eigenen Nachbildung.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import zipfile
from datetime import date

import numpy as np
import pandas as pd
from benchmark_compare import evaluate_well_sim

TEST_DATES = pd.date_range("2013-01-07", "2022-12-26", freq="W-MON")


def official_score(observed: np.ndarray, simulated: np.ndarray, historical_mean: float) -> dict:
    """Identisch zu score() in scripts/models/evaluation.py des GEMS-GER-Repos."""
    error = simulated - observed
    denominator = float(np.sum((observed - historical_mean) ** 2))
    return {
        "NSE": 1 - float(np.sum(error ** 2)) / denominator if denominator > 0 else np.nan,
        "R2": float(np.corrcoef(observed, simulated)[0, 1] ** 2)
        if observed.std() > 0 and simulated.std() > 0 else np.nan,
        "RMSE": float(np.sqrt(np.mean(error ** 2))),
        "Bias": float(np.mean(error)),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dynamic", default=os.environ.get("GEMS_GER_DYN", "data/gems-ger/dynamic"))
    ap.add_argument("--output", default=os.path.join(os.environ.get("WK_OUT", "output"), "submission"))
    ap.add_argument("--column", default="prediction",
                    help="Spaltenname der Vorhersage, laut Starting Kit")
    args = ap.parse_args()
    os.makedirs(args.output, exist_ok=True)

    blocks, scores = [], []
    for path in sorted(glob.glob(os.path.join(args.dynamic, "MW_*.csv")),
                       key=lambda p: int(os.path.basename(p)[3:-4])):
        got = evaluate_well_sim(path)
        if got is None:
            continue
        d, sim = got
        ident = os.path.basename(path)[:-4]
        idx = pd.DatetimeIndex(d["date"])
        if not TEST_DATES.isin(idx).all():
            raise SystemExit(f"{ident}: Testwochen fehlen in den Eingangsdaten")
        pos = idx.get_indexer(TEST_DATES)

        pred = np.asarray(sim)[pos].astype(np.float64)
        obs = d["GWL"].to_numpy(float)[pos]
        hist_mean = float(d.loc[idx < pd.Timestamp("2013-01-01"), "GWL"].mean())
        if not np.isfinite(pred).all():
            raise SystemExit(f"{ident}: nichtfinite Vorhersagen")

        blocks.append(pd.DataFrame({"ID": ident,
                                    "Date": TEST_DATES.strftime("%Y-%m-%d"),
                                    args.column: pred}))
        scores.append({"ID": ident, **official_score(obs, pred, hist_mean)})

    preds = pd.concat(blocks, ignore_index=True)
    csv_path = os.path.join(args.output, "predictions.csv")
    preds.to_csv(csv_path, index=False, float_format="%.17g", lineterminator="\n")

    sc = pd.DataFrame(scores)
    sc.to_csv(os.path.join(args.output, "self_scores.csv"), index=False)

    meta = {
        "name": "Wasserkonto two-reservoir water balance",
        "version": "1.0",
        "submitted": date.today().isoformat(),
        "authors": ["Leon Maximilian Brade"],
        "affiliation": "Hochschule Bielefeld, Campus Guetersloh",
        "model_type": "conceptual rainfall-groundwater transfer model, not machine learning",
        "description": (
            "Thornthwaite-type soil moisture store feeding two parallel linear "
            "groundwater reservoirs. Three fitted parameters per well: soil storage "
            "capacity and two residence times. The two reservoir weights and the "
            "reference level are obtained by non-negative least squares."
        ),
        "inputs_used": ["HYRAS_pr", "DWD_evapo_p"],
        "inputs_not_used": [
            "past groundwater levels as a model input",
            "static site features",
            "all other dynamic columns",
        ],
        "preprocessing": (
            "DWD_evapo_p is multiplied by 7. The column is a daily mean in mm/day "
            "while precipitation is a weekly sum; this is the scaling corrected in "
            "GEMS-GER v5."
        ),
        "training_period": "1991-01-07 to 2007-12-31, first 104 weeks used as warm-up only",
        "validation_period": "2008-01-07 to 2012-12-31, used to select the three parameters",
        "test_period": "2013-01-07 to 2022-12-26, never used for fitting or selection",
        "ensemble_members": 1,
        "deterministic": True,
        "parameters_median_over_wells": {
            "soil_storage_capacity_mm": 203.0,
            "fast_residence_time_weeks": 2.0,
            "slow_residence_time_weeks": 70.0,
        },
        "runtime": "about three minutes for 140 wells on one CPU core, no GPU",
        "code": "https://github.com/xlovoss/Wasserkonto",
        "license": "MIT",
        "notes": (
            "Submitted as an interpretable reference point rather than as a competitive "
            "model. Known weakness: annual minima are overestimated, and the error grows "
            "with how far the minimum falls below the calibration-period minimum."
        ),
    }
    with open(os.path.join(args.output, "model.json"), "w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=2, ensure_ascii=False)
        fh.write("\n")

    zip_path = os.path.join(args.output, "submission.zip")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(csv_path, "predictions.csv")
        z.write(os.path.join(args.output, "model.json"), "model.json")

    print(f"Messstellen           {sc.shape[0]}")
    print(f"Zeilen in predictions {len(preds)}  (erwartet {sc.shape[0] * 521})")
    print(f"Spalten               {list(preds.columns)}")
    print()
    print("Eigene Kontrolle mit der Score-Funktion aus evaluation.py:")
    for metric in ("NSE", "R2", "RMSE", "Bias"):
        s = sc[metric]
        print(f"  {metric:<5} min {s.min():+.3f}  Median {s.median():+.3f}  max {s.max():+.3f}")
    print(f"  NSE ueber 0,5 bei {(sc.NSE > 0.5).mean() * 100:.1f} % der Messstellen")
    print()
    print(f"Fertig: {zip_path}")


if __name__ == "__main__":
    main()
