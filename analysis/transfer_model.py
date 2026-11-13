"""Transferfunktionsmodell mit zwei parallelen Grundwasserspeichern.

Der Einzelspeicher aus `modell_transferfunktion.py` optimiert die Gesamtkorrelation
und waehlt dafuer eine lange Verweilzeit, die der mehrjaehrigen Schwankung folgt.
Die saisonale Amplitude wird dabei fast vollstaendig weggedaempft -- simulierte
Winteranstiege von 0,07 m gegen beobachtete 0,62 m. Fuer eine Zerlegung des
Neubildungsrueckgangs ist das unbrauchbar.

Abhilfe: zwei Speicher parallel, ein schneller (Wochen) und ein langsamer (Jahre),
gespeist aus demselben Sickerwasser:

    GWL = a + g_fast * G(tau_fast) + g_slow * G(tau_slow)

Das ist die diskrete Entsprechung einer zweigipfligen Impulsantwort und bildet ab,
was hydrologisch passiert: ein Teil des Sickerwassers erreicht den Grundwasserstand
innerhalb von Wochen, ein Teil ueber Jahre. a, g_fast und g_slow sind linear und
werden analytisch bestimmt; C, tau_fast und tau_slow per Gittersuche.
"""

from __future__ import annotations

import glob
import os

import numpy as np
import pandas as pd
from scipy.signal import lfilter

# Paths. Override with environment variables rather than editing this file.
#   GEMS_GER_DYN   directory holding the per-well CSVs from Zenodo
#   WK_INVENTORY   the Saxon inventory CSV produced from the static features
#   WK_OUT         where results are written
DYN = os.environ.get("GEMS_GER_DYN", "data/gems-ger/dynamic")
INVENTAR = os.environ.get("WK_INVENTORY", "data/sachsen_inventar.csv")
OUT = os.environ.get("WK_OUT", "output")

C_GRID = np.unique(np.round(np.geomspace(20, 900, 24)))
TAU_FAST = np.array([1.0, 2.0, 3.0, 4.0, 6.0, 8.0, 12.0])
TAU_SLOW = np.array([20.0, 30.0, 45.0, 70.0, 100.0, 150.0, 220.0, 300.0])
WARMUP_WEEKS = 104


def soil_runoff(precip: np.ndarray, etp: np.ndarray, capacity: np.ndarray) -> np.ndarray:
    storage = capacity * 0.5
    out = np.empty((len(precip), len(capacity)))
    for t in range(len(precip)):
        eta = etp[t] * (storage / capacity)
        tmp = storage + precip[t] - eta
        excess = np.maximum(0.0, tmp - capacity)
        storage = np.clip(tmp - excess, 0.0, capacity)
        out[t] = excess
    return out


def reservoir(runoff: np.ndarray, tau: float) -> np.ndarray:
    return lfilter([1.0], [1.0, -np.exp(-1.0 / tau)], runoff, axis=0)


def fit_well(df: pd.DataFrame, score_slice: slice | None = None) -> dict:
    """Beste Kombination aus C, tau_fast und tau_slow fuer eine Messstelle."""
    precip = df["HYRAS_pr"].to_numpy(float)
    etp = df["DWD_evapo_p"].to_numpy(float) * 7.0   # mm/Tag -> mm/Woche
    gwl = df["GWL"].to_numpy(float)

    runoff = soil_runoff(precip, etp, C_GRID)
    sl = score_slice if score_slice is not None else slice(WARMUP_WEEKS, None)

    taus = np.concatenate([TAU_FAST, TAU_SLOW])
    # G[k] ist die Speicherantwort fuer tau[k], Form (Zeit x Kapazitaeten).
    G = np.stack([reservoir(runoff, t)[sl] for t in taus])

    y = gwl[sl]
    y_c = y - y.mean()
    sst = float((y_c**2).sum())
    n_fast = len(TAU_FAST)

    best = {"nse": -np.inf}
    for ci in range(len(C_GRID)):
        cols = G[:, :, ci]                     # (tau x Zeit)
        cols_c = cols - cols.mean(axis=1, keepdims=True)
        gram = cols_c @ cols_c.T               # (tau x tau)
        rhs = cols_c @ y_c                     # (tau,)

        for i in range(n_fast):
            for j in range(n_fast, len(taus)):
                A = gram[np.ix_([i, j], [i, j])]
                b = rhs[[i, j]]
                # Negative Gewichte waeren physikalisch sinnlos: mehr Sickerwasser
                # darf den Grundwasserstand nicht senken. Statt solche Loesungen zu
                # verwerfen, wird die beste nichtnegative gesucht -- bei zwei
                # Variablen heisst das: freie Loesung, sonst die Raender pruefen.
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
                            v = max(0.0, b[k] / A[k, k])
                            c = np.zeros(2)
                            c[k] = v
                            cands.append(c)
                    if not cands:
                        continue
                    coef = max(cands, key=lambda c: 2 * c @ b - c @ A @ c)
                ssr = sst - float(2 * coef @ b - coef @ A @ coef)
                nse = 1.0 - ssr / sst
                if nse > best["nse"]:
                    best = {"nse": nse, "C": float(C_GRID[ci]),
                            "tau_fast": float(taus[i]), "tau_slow": float(taus[j]),
                            "g_fast": float(coef[0]), "g_slow": float(coef[1])}
    return best


def simulate(df: pd.DataFrame, p: dict) -> np.ndarray:
    runoff = soil_runoff(df["HYRAS_pr"].to_numpy(float),
                         df["DWD_evapo_p"].to_numpy(float) * 7.0,
                         np.array([p["C"]]))
    fast = reservoir(runoff, p["tau_fast"])[:, 0]
    slow = reservoir(runoff, p["tau_slow"])[:, 0]
    sim = p["g_fast"] * fast + p["g_slow"] * slow
    gwl = df["GWL"].to_numpy(float)
    # Niveau so legen, dass Modell und Beobachtung dasselbe Mittel haben.
    return sim + (gwl[WARMUP_WEEKS:].mean() - sim[WARMUP_WEEKS:].mean())


def load_well(path: str) -> pd.DataFrame:
    d = pd.read_csv(path, parse_dates=["Unnamed: 0"]).rename(
        columns={"Unnamed: 0": "date"}).sort_values("date").reset_index(drop=True)
    d["year"] = d["date"].dt.year
    d["month"] = d["date"].dt.month
    d["hy"] = np.where(d["month"] >= 11, d["year"] + 1, d["year"])
    return d


def main() -> None:
    inv = pd.read_csv(INVENTAR)
    inv["regime"] = np.where(inv["Elevation"] < 150, "Tiefland",
                     np.where(inv["Elevation"] >= 300, "Bergland", "Huegelland"))
    regime = dict(zip(inv["MW_ID"], inv["regime"]))

    rows = []
    for path in sorted(glob.glob(os.path.join(DYN, "MW_*.csv"))):
        mw = os.path.basename(path)[:-4]
        g = load_well(path)
        p = fit_well(g)
        sim = simulate(g, p)
        g["GWL_sim"] = sim

        obs_amp = g.groupby("hy")["GWL"].agg(lambda s: s.max() - s.min()).median()
        sim_amp = g.groupby("hy")["GWL_sim"].agg(lambda s: s.max() - s.min()).median()

        # Split-Sample fuer die Parameterstabilitaet.
        cal_mask = g["year"] <= 2006
        p_cal = fit_well(g[cal_mask].reset_index(drop=True))
        sim_cal = simulate(g, p_cal)
        val = g["year"] >= 2007
        resid = g.loc[val, "GWL"].to_numpy() - sim_cal[val.to_numpy()]
        # Niveauversatz der Kalibrierperiode abziehen, damit nur die Drift zaehlt.
        base = (g.loc[cal_mask & (g.index >= WARMUP_WEEKS), "GWL"].to_numpy()
                - sim_cal[(cal_mask & (g.index >= WARMUP_WEEKS)).to_numpy()]).mean()
        resid = resid - base
        drift = float(np.polyfit(g.loc[val, "year"].to_numpy(float), resid, 1)[0])

        rows.append({"MW_ID": mw, "regime": regime.get(mw), **p,
                     "amp_obs": float(obs_amp), "amp_sim": float(sim_amp),
                     "amp_ratio": float(sim_amp / obs_amp) if obs_amp else np.nan,
                     "bias_val_m": float(resid.mean()),
                     "drift_val_m_per_year": drift})

    res = pd.DataFrame(rows)
    os.makedirs(OUT, exist_ok=True)
    res.to_csv(os.path.join(OUT, "transfer_model_parameters.csv"), index=False)

    print("=== Guete Zwei-Speicher-Modell ===")
    print(f"NSE Median {res.nse.median():.3f} | > 0.5: {(res.nse>0.5).mean()*100:.1f} % "
          f"| > 0.65: {(res.nse>0.65).mean()*100:.1f} %")
    print(f"Amplitudenverhaeltnis Modell/Beobachtung: Median {res.amp_ratio.median():.2f} "
          f"({res.amp_ratio.quantile(.25):.2f}-{res.amp_ratio.quantile(.75):.2f})")
    print()
    print(res.groupby("regime")[["C", "tau_fast", "tau_slow", "nse", "amp_ratio"]]
          .median().round(2).to_string())
    print()
    from scipy import stats
    tb = stats.ttest_1samp(res.bias_val_m.dropna(), 0.0)
    td = stats.ttest_1samp(res.drift_val_m_per_year.dropna(), 0.0)
    print("=== Split-Sample 1992-2006 kalibriert, 2007-2022 validiert ===")
    print(f"Bias Median {res.bias_val_m.median():+.3f} m  (t={tb.statistic:.2f}, p={tb.pvalue:.4f})")
    print(f"Drift Median {res.drift_val_m_per_year.median():+.4f} m/Jahr "
          f"(t={td.statistic:.2f}, p={td.pvalue:.4f})")


if __name__ == "__main__":
    main()
