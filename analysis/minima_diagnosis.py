"""Warum das Prozessmodell die Jahrestiefstaende ueberschaetzt.

Marc Ohmers Erklaerung fuer die Benchmarkmodelle lautet, dass vergleichbar
niedrige Werte im Training selten oder gar nicht vorkamen. Fuer ein
datengetriebenes Modell ist das zwingend: es hat diesen Bereich nie gesehen.

Fuer ein konzeptionelles Modell mit drei Parametern gilt dieses Argument so
nicht. Es lernt keinen Wertebereich, sondern extrapoliert eine Bilanz. Wenn es
die Minima trotzdem ueberschaetzt, muss die Ursache eine andere sein, und die
naheliegende Kandidatin ist die Struktur: ein linearer Speicher entleert sich
exponentiell mit fester Zeitkonstante und kann eine lange, tiefe Rezession
nicht nachbilden.

Dieses Skript trennt die beiden Erklaerungen, soweit es mit den Daten geht:

1. Waechst der Fehler an den Minima mit der Tiefe unterhalb des im Training
   beobachteten Minimums? Dann ist es der Bereich.
2. Waechst er mit der Dauer der Rezession, unabhaengig von der Tiefe? Dann ist
   es die Struktur.

Ausserdem wird geprueft, wie stark die Standardisierung ueber 1991 bis 2022
die Absenkung im Testfenster verkleinert, verglichen mit einer
Standardisierung allein ueber 1991 bis 2012.
"""

from __future__ import annotations

import glob
import os

import numpy as np
import pandas as pd
from benchmark_compare import evaluate_well_sim

DYN = os.environ.get("GEMS_GER_DYN", "data/gems-ger/dynamic")
OUT = os.environ.get("WK_OUT", "output")

TEST_FROM = pd.Timestamp("2013-01-07")
TEST_TO = pd.Timestamp("2022-12-26")


def main() -> None:
    rows, zrows = [], []
    for path in sorted(glob.glob(os.path.join(DYN, "MW_*.csv"))):
        got = evaluate_well_sim(path)
        if got is None:
            continue
        d, sim = got
        date = d["date"]
        year = date.dt.year.to_numpy()
        gwl = d["GWL"].to_numpy(float)
        m_te = ((date >= TEST_FROM) & (date <= TEST_TO)).to_numpy()
        m_tr = (year >= 1991) & (year <= 2007)
        m_hist = year <= 2012

        # Standardisierung: ganzer Zeitraum gegen nur Historie.
        z_all = (gwl[m_te].mean() - gwl.mean()) / gwl.std(ddof=0)
        z_hist = (gwl[m_te].mean() - gwl[m_hist].mean()) / gwl[m_hist].std(ddof=0)
        zrows.append({"z_1991_2022": z_all, "z_1991_2012": z_hist})

        train_min = float(gwl[m_tr].min())
        te_year = year[m_te]
        obs_te, sim_te = gwl[m_te], sim[m_te]
        for y in np.unique(te_year):
            k = te_year == y
            i = int(np.argmin(obs_te[k]))
            obs_min = float(obs_te[k][i])
            # Dauer der Rezession: Wochen seit dem letzten Jahreshoechststand.
            weeks_falling = int(k.sum() - np.argmax(obs_te[k]) - (k.sum() - i))
            rows.append({
                "year": int(y),
                "resid_at_min": float(sim_te[k][i] - obs_min),
                "below_train_min": train_min - obs_min,   # > 0 = tiefer als je im Training
                "recession_weeks": max(weeks_falling, 0),
            })

    m = pd.DataFrame(rows)
    z = pd.DataFrame(zrows)
    os.makedirs(OUT, exist_ok=True)
    m.to_csv(os.path.join(OUT, "minima_diagnosis.csv"), index=False)

    print("=== Standardisierung ===")
    print(f"  Mittleres z im Testfenster, Bezug 1991-2022: {z.z_1991_2022.median():+.3f}")
    print(f"  Mittleres z im Testfenster, Bezug 1991-2012: {z.z_1991_2012.median():+.3f}")
    print(f"  Die Absenkung erscheint um Faktor "
          f"{z.z_1991_2012.median() / z.z_1991_2022.median():.2f} groesser, "
          f"wenn nur die Historie den Bezug bildet.")
    print()

    print("=== Fehler an den Jahresminima, nach Tiefe unterhalb des Trainingsminimums ===")
    m["bucket"] = pd.cut(m.below_train_min, [-np.inf, 0, 0.25, 0.5, 1.0, np.inf],
                         labels=["ueber Trainingsmin.", "0 bis 0,25 m",
                                 "0,25 bis 0,5 m", "0,5 bis 1 m", "ueber 1 m tiefer"])
    g = m.groupby("bucket", observed=True).agg(
        n=("resid_at_min", "size"), median_fehler=("resid_at_min", "median"))
    print(g.round(3).to_string())
    print()

    sub = m.dropna(subset=["below_train_min", "resid_at_min"])
    print(f"  Korrelation Fehler gegen Tiefe unter Trainingsminimum: "
          f"{np.corrcoef(sub.below_train_min, sub.resid_at_min)[0, 1]:+.3f}")
    print(f"  Korrelation Fehler gegen Dauer der Rezession:          "
          f"{np.corrcoef(sub.recession_weeks, sub.resid_at_min)[0, 1]:+.3f}")
    print()

    print("=== Fehler je Testjahr ===")
    per_year = m.groupby("year").agg(
        median_fehler=("resid_at_min", "median"),
        anteil_unter_trainingsmin=("below_train_min", lambda s: (s > 0).mean() * 100))
    print(per_year.round(3).to_string())


if __name__ == "__main__":
    main()
