"""Vergleich gegen die GEMS-GER-Benchmarkmodelle, nach deren eigener Score-Definition.

Das Supplement `model_performance/README.md` legt die Auswertung exakt fest, und
sie weicht in einem Punkt von der ueblichen Konvention ab:

    NSE = 1 - sum((pred - obs)^2) / sum((obs - mean_1991_2012)^2)

Der Nenner verwendet also den historischen Mittelwert aus 1991 bis 2012 und
nicht den Mittelwert des Testfensters. Weil die Grundwasserstaende im
Testfenster im Mittel tiefer liegen, ist der Nenner dadurch groesser und der
NSE hoeher. Ein mit der ueblichen Definition gerechneter Wert ist gegen die
veroeffentlichten Zahlen nicht vergleichbar.

Weiter gilt laut Supplement: alle 521 Testwochen von 2013-01-07 bis 2022-12-26,
imputierte Werte eingeschlossen, GWL_flag ist kein Filter.

Zusaetzlich beantwortet dieses Skript die Frage von Marc Ohmer, ob das
Prozessmodell dieselbe Schwaeche zeigt wie die Benchmarkmodelle, naemlich eine
Ueberschaetzung der spaeten Rezession und der jaehrlichen Tiefstaende.
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
PERF = os.environ.get("GEMS_GER_PERF", "data/gems-ger/model_performance")
OUT = os.environ.get("WK_OUT", "output")

TEST_FROM = pd.Timestamp("2013-01-07")
TEST_TO = pd.Timestamp("2022-12-26")
HIST_TO = 2012          # historischer Mittelwert aus 1991 bis 2012
TRAIN = (1991, 2007)
VALID = (2008, 2012)


def fit_coefficients(gi: np.ndarray, gj: np.ndarray, y: np.ndarray):
    xi, xj, yc = gi - gi.mean(), gj - gj.mean(), y - y.mean()
    A = np.array([[float(xi @ xi), float(xi @ xj)],
                  [float(xi @ xj), float(xj @ xj)]])
    b = np.array([float(xi @ yc), float(xj @ yc)])
    coef = None
    try:
        free = np.linalg.solve(A, b)
        if np.all(free >= 0):
            coef = free
    except np.linalg.LinAlgError:
        pass
    if coef is None:
        cands = []
        for k in (0, 1):
            if A[k, k] > 0:
                c = np.zeros(2)
                c[k] = max(0.0, b[k] / A[k, k])
                cands.append(c)
        if not cands:
            return None
        coef = max(cands, key=lambda c: 2 * c @ b - c @ A @ c)
    return float(coef[0]), float(coef[1]), float(y.mean() - coef[0] * gi.mean() - coef[1] * gj.mean())


def evaluate_well(path: str, sim_only: bool = False):
    d = pd.read_csv(path, parse_dates=["Unnamed: 0"]).rename(
        columns={"Unnamed: 0": "date"}).sort_values("date").reset_index(drop=True)
    year = d["date"].dt.year.to_numpy()
    gwl = d["GWL"].to_numpy(float)

    warm = np.arange(len(d)) >= WARMUP_WEEKS
    m_tr = warm & (year >= TRAIN[0]) & (year <= TRAIN[1])
    m_va = (year >= VALID[0]) & (year <= VALID[1])
    m_te = ((d["date"] >= TEST_FROM) & (d["date"] <= TEST_TO)).to_numpy()
    m_hist = year <= HIST_TO
    if m_tr.sum() < 260 or m_va.sum() < 100 or m_te.sum() < 500:
        return None

    runoff = soil_runoff(d["HYRAS_pr"].to_numpy(float),
                         d["DWD_evapo_p"].to_numpy(float) * 7.0, C_GRID)
    taus = np.concatenate([TAU_FAST, TAU_SLOW])
    G = np.stack([reservoir(runoff, t) for t in taus])
    n_fast = len(TAU_FAST)

    # Modellauswahl auf dem Validierungsfenster, mit uebliche NSE-Konvention.
    y_va = gwl[m_va]
    sst_va = float(((y_va - y_va.mean()) ** 2).sum())
    best = None
    best_v = -np.inf
    for ci in range(len(C_GRID)):
        for i in range(n_fast):
            for j in range(n_fast, len(taus)):
                gi, gj = G[i, :, ci], G[j, :, ci]
                fitted = fit_coefficients(gi[m_tr], gj[m_tr], gwl[m_tr])
                if fitted is None:
                    continue
                gf, gs, level = fitted
                sim = level + gf * gi + gs * gj
                v = 1.0 - float(((y_va - sim[m_va]) ** 2).sum()) / sst_va if sst_va > 0 else -np.inf
                if v > best_v:
                    best_v, best = v, (sim, float(C_GRID[ci]), float(taus[i]), float(taus[j]))
    if best is None:
        return None
    if sim_only:
        return d, best[0]
    sim, cap, tf, ts = best

    obs_te, sim_te = gwl[m_te], sim[m_te]
    hist_mean = float(gwl[m_hist].mean())
    denom = float(((obs_te - hist_mean) ** 2).sum())
    resid = sim_te - obs_te

    # Tiefstaende: unterstes Dezil der Beobachtungen und die Jahresminima.
    q10 = np.quantile(obs_te, 0.10)
    low = obs_te <= q10
    te_year = d.loc[m_te, "date"].dt.year.to_numpy()
    mins = [resid[te_year == y][np.argmin(obs_te[te_year == y])]
            for y in np.unique(te_year) if (te_year == y).sum() > 0]

    return {
        "ID": os.path.basename(path)[:-4],
        "nse_official": 1.0 - float((resid ** 2).sum()) / denom if denom > 0 else np.nan,
        "nse_classic": 1.0 - float((resid ** 2).sum())
                       / float(((obs_te - obs_te.mean()) ** 2).sum()),
        "rmse": float(np.sqrt((resid ** 2).mean())),
        "bias": float(resid.mean()),
        "bias_low_decile": float(resid[low].mean()),
        "bias_annual_minima": float(np.mean(mins)),
        "nse_val": best_v, "C": cap, "tau_fast": tf, "tau_slow": ts,
    }


def main() -> None:
    rows = [r for r in (evaluate_well(p)
                        for p in sorted(glob.glob(os.path.join(DYN, "MW_*.csv"))))
            if r is not None]
    mine = pd.DataFrame(rows)
    os.makedirs(OUT, exist_ok=True)
    mine.to_csv(os.path.join(OUT, "benchmark_compare.csv"), index=False)

    bench = {}
    for name, fn in (("single", "model_performance_single.csv"),
                     ("dynonly", "model_performance_global_dynonly.csv"),
                     ("dynstat", "model_performance_global_dynstat.csv")):
        b = pd.read_csv(os.path.join(PERF, fn), sep=";")
        bench[name] = b[b["ID"].isin(mine["ID"])].set_index("ID")

    print(f"Messstellen: {len(mine)}  (von {len(bench['single'])} im Benchmark gefunden)")
    print()
    print("=== Testfenster 2013-2022, Score-Definition des Supplements ===")
    print(f"{'Modell':<22}{'NSE Median':>12}{'> 0.5':>9}{'< 0':>8}{'RMSE Med':>11}{'Bias Med':>11}")
    for name, b in bench.items():
        print(f"{'GEMS-GER ' + name:<22}{b.NSE.median():>12.3f}{(b.NSE > 0.5).mean() * 100:>8.1f}%"
              f"{(b.NSE < 0).mean() * 100:>7.1f}%{b.RMSE.median():>11.3f}{b.Bias.median():>+11.3f}")
    print(f"{'Prozessmodell (3 P.)':<22}{mine.nse_official.median():>12.3f}"
          f"{(mine.nse_official > 0.5).mean() * 100:>8.1f}%{(mine.nse_official < 0).mean() * 100:>7.1f}%"
          f"{mine.rmse.median():>11.3f}{mine.bias.median():>+11.3f}")
    print()
    print(f"Zum Vergleich, uebliche NSE-Konvention (Mittelwert des Testfensters): "
          f"Median {mine.nse_classic.median():.3f}, "
          f"> 0.5 bei {(mine.nse_classic > 0.5).mean() * 100:.1f} %")
    print()

    print("=== Paarweise, dieselben Messstellen ===")
    for name, b in bench.items():
        j = mine.set_index("ID").join(b[["NSE", "Bias"]], how="inner", rsuffix="_b")
        d = j.nse_official - j.NSE
        print(f"  gegen {name:<9} besser bei {(d > 0).mean() * 100:5.1f} % der Messstellen, "
              f"Mediandifferenz {d.median():+.3f}")
    print()

    print("=== Tiefstaende: ueberschaetzt das Prozessmodell sie auch? ===")
    print("(positiv heisst Modell ueber Beobachtung)")
    print(f"  Bias ueber alle Testwochen        Median {mine.bias.median():+.3f} m")
    print(f"  Bias im untersten Dezil           Median {mine.bias_low_decile.median():+.3f} m")
    print(f"  Bias an den Jahresminima          Median {mine.bias_annual_minima.median():+.3f} m")
    share = (mine.bias_annual_minima > mine.bias).mean() * 100
    print(f"  Minima staerker ueberschaetzt als der Durchschnitt: {share:.1f} % der Messstellen")
    print()
    print("Benchmark-Bias je Modell (alle Testwochen, Median): "
          + ", ".join(f"{n} {b.Bias.median():+.3f}" for n, b in bench.items()))


def evaluate_well_sim(path: str):
    """Nur die angepasste Simulation, fuer weitergehende Diagnosen."""
    return evaluate_well(path, sim_only=True)


if __name__ == "__main__":
    main()
