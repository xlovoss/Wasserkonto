"""Winterliche Grundwasserneubildung in Sachsen: Reagiert derselbe Regen heute schwaecher?

Idee: In Mitteleuropa findet die Grundwasserneubildung ueberwiegend im hydrologischen
Winterhalbjahr statt (November bis April), weil im Sommer die Verdunstung den Niederschlag
weitgehend aufzehrt. Pro Messstelle und hydrologischem Jahr laesst sich daher eine
Reaktionskennzahl bilden:

    Reaktion = (Winter-Anstieg des Grundwasserstands) / (Winter-Niederschlag) * 100

in Metern Anstieg je 100 mm Niederschlag. Faellt diese Kennzahl ueber die Jahrzehnte,
erzeugt dieselbe Regenmenge weniger Neubildung.

Kontrollgroesse ist die Bodenfeuchte Ende Oktober: Ist der Bodenspeicher vor dem Winter
leer, muss er erst gefuellt werden, bevor Wasser versickert. Erklaert die Vorfeuchte den
Trend, liegt es am leergelaufenen Speicher; bleibt der Trend bestehen, wirkt etwas anderes.
"""

from __future__ import annotations

import glob
import os

import numpy as np
import pandas as pd

# Paths. Override with environment variables rather than editing this file.
#   GEMS_GER_DYN   directory holding the per-well CSVs from Zenodo
#   WK_INVENTORY   the Saxon inventory CSV produced from the static features
#   WK_OUT         where results are written
DYN = os.environ.get("GEMS_GER_DYN", "data/gems-ger/dynamic")
INVENTAR = os.environ.get("WK_INVENTORY", "data/sachsen_inventar.csv")
OUT = os.environ.get("WK_OUT", "output")

# Hydrologisches Winterhalbjahr und Monate, in denen der Jahreshoechststand faellt.
WINTER_MONTHS = {11, 12, 1, 2, 3, 4}
PEAK_MONTHS = {12, 1, 2, 3, 4, 5}

# Mindestabdeckung, damit ein Messstellen-Jahr ausgewertet wird.
MIN_WINTER_WEEKS = 24   # von ~26 Wochen November bis April
MIN_PRECIP_MM = 100.0   # Jahre mit extrem wenig Winterregen sind numerisch instabil


def hydro_year(ts: pd.Timestamp) -> int:
    """Das hydrologische Jahr beginnt am 1. November und wird nach seinem Ende benannt."""
    return ts.year + 1 if ts.month >= 11 else ts.year


def load_dynamic() -> pd.DataFrame:
    frames = []
    for path in sorted(glob.glob(os.path.join(DYN, "MW_*.csv"))):
        mw = os.path.basename(path)[:-4]
        d = pd.read_csv(path, parse_dates=["Unnamed: 0"]).rename(
            columns={"Unnamed: 0": "date"}
        )
        d["MW_ID"] = mw
        frames.append(d)
    df = pd.concat(frames, ignore_index=True)
    df["hy"] = df["date"].map(hydro_year)
    df["month"] = df["date"].dt.month
    return df


def winter_response(df: pd.DataFrame) -> pd.DataFrame:
    """Eine Zeile je Messstelle und hydrologischem Jahr."""
    rows = []
    for (mw, hy), g in df.groupby(["MW_ID", "hy"], sort=True):
        win = g[g["month"].isin(WINTER_MONTHS)]
        if len(win) < MIN_WINTER_WEEKS:
            continue

        precip = win["HYRAS_pr"].sum()
        if precip < MIN_PRECIP_MM:
            continue

        # Ausgangsniveau: erste beiden Novemberwochen. Hoechststand: Dezember bis Mai.
        start = g[g["month"] == 11].sort_values("date")["GWL"].head(2)
        peak = g[g["month"].isin(PEAK_MONTHS)]["GWL"]
        if start.empty or peak.empty:
            continue

        rise = peak.max() - start.mean()

        # Vorfeuchte des Bodens: Oktober des VORHERIGEN Kalenderjahres gehoert noch
        # zum vorangehenden hydrologischen Jahr, daher separat gesucht.
        pre = df[(df["MW_ID"] == mw) & (df["date"].dt.year == hy - 1) & (df["month"] == 10)]
        soil_pre = pre["DWD_soil_moist"].mean() if len(pre) else np.nan

        rows.append(
            {
                "MW_ID": mw,
                "hy": hy,
                "precip_winter_mm": precip,
                "rise_m": rise,
                "response_m_per_100mm": rise / precip * 100.0,
                "soil_moist_oct": soil_pre,
                "temp_winter_mean": win["HYRAS_tas"].mean(),
                "evapo_winter_mm": win["DWD_evapo_r"].sum(),
                "imputed_share": 1.0 - win["GWL_flag"].mean(),
            }
        )
    return pd.DataFrame(rows)


def main() -> None:
    inv = pd.read_csv(INVENTAR)
    inv["regime"] = np.where(
        inv["Elevation"] < 150, "Tiefland (<150 m)",
        np.where(inv["Elevation"] >= 300, "Bergland (>=300 m)", "Huegelland (150-300 m)"),
    )

    df = load_dynamic()
    resp = winter_response(df).merge(
        inv[["MW_ID", "regime", "Elevation", "Depth", "AquiferMed", "GWN1000_GR"]],
        on="MW_ID", how="left",
    )

    # Vollstaendige hydrologische Jahre: 1992 bis 2022.
    resp = resp[(resp["hy"] >= 1992) & (resp["hy"] <= 2022)]
    # Messstellen-Jahre, die ueberwiegend auf imputierten Werten beruhen, fliegen raus.
    resp = resp[resp["imputed_share"] < 0.25]

    os.makedirs(OUT, exist_ok=True)
    resp.to_csv(os.path.join(OUT, "winter_response.csv"), index=False)

    print(f"Auswertbare Messstellen-Jahre: {len(resp)}  "
          f"({resp.MW_ID.nunique()} Messstellen, {resp.hy.nunique()} Jahre)")
    print()

    print("=== Median je Dekade ===")
    dec = pd.cut(resp["hy"], [1991, 2001, 2011, 2022],
                 labels=["1992-2001", "2002-2011", "2012-2022"])
    agg = resp.groupby(dec, observed=True).agg(
        n=("response_m_per_100mm", "size"),
        winterregen_mm=("precip_winter_mm", "median"),
        anstieg_m=("rise_m", "median"),
        reaktion=("response_m_per_100mm", "median"),
        bodenfeuchte_okt=("soil_moist_oct", "median"),
        wintertemp=("temp_winter_mean", "median"),
    ).round(3)
    print(agg.to_string())
    print()

    print("=== Median je Dekade und Regime ===")
    agg2 = resp.groupby([dec, "regime"], observed=True).agg(
        n=("response_m_per_100mm", "size"),
        winterregen_mm=("precip_winter_mm", "median"),
        reaktion=("response_m_per_100mm", "median"),
    ).round(3)
    print(agg2.to_string())
    print()

    print("=== Jahresmediane (Reaktion in m je 100 mm) ===")
    per_year = resp.groupby("hy").agg(
        n=("response_m_per_100mm", "size"),
        reaktion=("response_m_per_100mm", "median"),
        winterregen=("precip_winter_mm", "median"),
        bodenfeuchte_okt=("soil_moist_oct", "median"),
    ).round(3)
    print(per_year.to_string())


if __name__ == "__main__":
    main()
