"""Das Zwei-Speicher-Modell auf dem offiziellen GEMS-GER-Split.

Ohmer (KIT) nennt als Protokoll des Benchmarks:
    Training    1991-2007
    Validierung 2008-2012
    Test        2013-2022

Das unterscheidet sich von der bisherigen Auswertung, die auf 1992-2006
kalibriert und auf 2007-2022 bewertet hat. Hier wird das Protokoll
nachgebildet, damit die Zahl vergleichbar wird:

  * die linearen Gewichte werden ausschliesslich auf dem Trainingsfenster
    bestimmt,
  * die Auswahl von C, tau_fast und tau_slow erfolgt nach der Guete auf dem
    Validierungsfenster,
  * berichtet wird die Guete auf dem Testfenster, das in beiden Schritten
    nicht gesehen wurde.

Die Verdunstung wird mit sieben multipliziert, weil die Spalte ein Tagesmittel
und der Niederschlag eine Wochensumme ist. Das entspricht der Korrektur in
GEMS-GER v5. Die ebenfalls in v5 korrigierte Spalte DWD_soil_moist geht in
dieses Modell nicht ein, die Bodenspeicherkapazitaet stammt aus der
Gittersuche.
"""

from __future__ import annotations

import glob
import os

import numpy as np
import pandas as pd
from transfer_model import (
    C_GRID,
    TAU_FAST,
    TAU_SLOW,
    WARMUP_WEEKS,
    reservoir,
    soil_runoff,
)

DYN = os.environ.get("GEMS_GER_DYN", "data/gems-ger/dynamic")
OUT = os.environ.get("WK_OUT", "output")

TRAIN = (1991, 2007)
VALID = (2008, 2012)
TEST = (2013, 2022)


def nse(obs: np.ndarray, sim: np.ndarray) -> float:
    sst = float(((obs - obs.mean()) ** 2).sum())
    if sst <= 0:
        return np.nan
    return 1.0 - float(((obs - sim) ** 2).sum()) / sst


def fit_coefficients(gi: np.ndarray, gj: np.ndarray, y: np.ndarray):
    """Nichtnegative Gewichte plus Niveau, auf dem Trainingsfenster."""
    xi = gi - gi.mean()
    xj = gj - gj.mean()
    yc = y - y.mean()
    a11 = float(xi @ xi)
    a22 = float(xj @ xj)
    a12 = float(xi @ xj)
    b1 = float(xi @ yc)
    b2 = float(xj @ yc)
    A = np.array([[a11, a12], [a12, a22]])
    b = np.array([b1, b2])
    coef = None
    try:
        free = np.linalg.solve(A, b)
        if np.all(free >= 0):
            coef = free
    except np.linalg.LinAlgError:
        pass
    if coef is None:
        cands = []
        for k, (akk, bk) in enumerate(((a11, b1), (a22, b2))):
            if akk > 0:
                c = np.zeros(2)
                c[k] = max(0.0, bk / akk)
                cands.append(c)
        if not cands:
            return None
        coef = max(cands, key=lambda c: 2 * c @ b - c @ A @ c)
    level = float(y.mean() - coef[0] * gi.mean() - coef[1] * gj.mean())
    return float(coef[0]), float(coef[1]), level


def evaluate_well(path: str) -> dict | None:
    d = pd.read_csv(path, parse_dates=["Unnamed: 0"]).rename(
        columns={"Unnamed: 0": "date"}).sort_values("date").reset_index(drop=True)
    year = d["date"].dt.year.to_numpy()
    gwl = d["GWL"].to_numpy(float)

    warm = np.arange(len(d)) >= WARMUP_WEEKS
    m_tr = warm & (year >= TRAIN[0]) & (year <= TRAIN[1])
    m_va = (year >= VALID[0]) & (year <= VALID[1])
    m_te = (year >= TEST[0]) & (year <= TEST[1])
    if m_tr.sum() < 260 or m_va.sum() < 100 or m_te.sum() < 260:
        return None

    runoff = soil_runoff(d["HYRAS_pr"].to_numpy(float),
                         d["DWD_evapo_p"].to_numpy(float) * 7.0,
                         C_GRID)
    taus = np.concatenate([TAU_FAST, TAU_SLOW])
    G = np.stack([reservoir(runoff, t) for t in taus])   # (tau, Zeit, C)
    n_fast = len(TAU_FAST)

    best = {"nse_val": -np.inf}
    for ci in range(len(C_GRID)):
        for i in range(n_fast):
            for j in range(n_fast, len(taus)):
                gi = G[i, :, ci]
                gj = G[j, :, ci]
                fitted = fit_coefficients(gi[m_tr], gj[m_tr], gwl[m_tr])
                if fitted is None:
                    continue
                gf, gs, level = fitted
                sim = level + gf * gi + gs * gj
                v = nse(gwl[m_va], sim[m_va])
                if np.isfinite(v) and v > best["nse_val"]:
                    best = {"nse_val": v,
                            "nse_train": nse(gwl[m_tr], sim[m_tr]),
                            "nse_test": nse(gwl[m_te], sim[m_te]),
                            "C": float(C_GRID[ci]),
                            "tau_fast": float(taus[i]),
                            "tau_slow": float(taus[j])}
    if not np.isfinite(best["nse_val"]):
        return None
    best["MW_ID"] = os.path.basename(path)[:-4]
    return best


def main() -> None:
    rows = []
    for path in sorted(glob.glob(os.path.join(DYN, "MW_*.csv"))):
        r = evaluate_well(path)
        if r is not None:
            rows.append(r)

    res = pd.DataFrame(rows)
    os.makedirs(OUT, exist_ok=True)
    res.to_csv(os.path.join(OUT, "benchmark_split.csv"), index=False)

    print(f"Messstellen ausgewertet: {len(res)}")
    print()
    print("=== Offizielles GEMS-GER-Protokoll ===")
    print("Training 1991-2007, Auswahl auf 2008-2012, Bericht auf 2013-2022")
    for name, col in (("Training", "nse_train"),
                      ("Validierung", "nse_val"),
                      ("Test", "nse_test")):
        s = res[col]
        print(f"  {name:<12} NSE Median {s.median():.3f} | > 0.5: {(s > 0.5).mean() * 100:.1f} % "
              f"| < 0: {(s < 0).mean() * 100:.1f} %")
    print()
    print("Vergleichswerte aus Ohmer et al. 2026, bundesweit, 3.207 Messstellen:")
    print("  Einzelbrunnen-CNN      NSE Median 0.52 | > 0.5: 52 %   | < 0: ~13 %")
    print("  globales LSTM dyn+stat NSE Median 0.50 | > 0.5: ~49 %  | < 0: ~12 %")
    print()
    print(res[["C", "tau_fast", "tau_slow"]].median().round(1).to_string())


if __name__ == "__main__":
    main()
