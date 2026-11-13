# Befunde: Winterliche Grundwasserneubildung in Sachsen, 1992–2022

Datengrundlage: GEMS-GER (Ohmer et al., ESSD 18, 77–95, 2026), Teilmenge Sachsen.
140 Messstellen des LfULG (`MW_2565` bis `MW_2704`), Wochenwerte 1991-01-07 bis 2022-12-26,
233.660 Zeilen. Auswertbar nach Filterung: 4.340 Messstellen-Jahre.

## Methode

Grundwasserneubildung findet in Mitteleuropa überwiegend im hydrologischen Winterhalbjahr
statt. Je Messstelle und hydrologischem Jahr (1. November bis 31. Oktober) wurde gebildet:

- **Winterniederschlag**: Summe `HYRAS_pr` November bis April
- **Winteranstieg**: Höchststand `GWL` (Dezember bis Mai) minus Ausgangsniveau
  (Mittel der ersten beiden Novemberwochen)
- **Reaktion**: Anstieg je 100 mm Winterniederschlag

Ausgeschlossen: Messstellen-Jahre mit weniger als 24 Winterwochen, mit weniger als
100 mm Winterniederschlag oder mit mehr als 25 % imputierten Werten.

Alle Trendschätzungen mit Messstellen-Fixeffekten (Within-Schätzer) und nach Messstelle
geclusterten Standardfehlern, damit Unterschiede *zwischen* Messstellen die
Zeitentwicklung nicht überlagern.

## Hauptbefund

**Die Neubildung ist deutlich zurückgegangen – aber nicht, weil der Grundwasserkörper
schwächer auf Niederschlag reagiert. Sondern weil die Winter trockener wurden und die
Reaktion nichtlinear ist.**

| Zeitraum | Winterregen (Median) | Anstieg (Median) | Reaktion je 100 mm |
|---|---|---|---|
| 1992–2001 | 283 mm | 0,650 m | 0,225 |
| 2002–2011 | 292 mm | 0,705 m | 0,241 |
| 2012–2022 | 244 mm | 0,515 m | 0,208 |

Trends über 30 Jahre, Within-Schätzer:

- **Winteranstieg: −0,266 m** (p < 0,001)
- Winterniederschlag: −59 mm (p = 0,052)
- Wintertemperatur: +1,65 K (p = 0,029)
- Reaktion je 100 mm: −0,025 (p = 0,041)

**Entscheidend:** Wird der Winterniederschlag kontrolliert, verschwindet der Trend des
Anstiegs vollständig (+0,0008 m pro Jahr, p = 0,484). Auch der Trend der Reaktion
überlebt die Kontrolle nicht und dreht das Vorzeichen (+0,0009 pro Jahr, p = 0,171).

Die ursprüngliche Hypothese – gleicher Regen, weniger Wirkung – lässt sich für Sachsen
in diesem Zeitraum **nicht bestätigen**.

## Der eigentliche Mechanismus: Konvexität

Die Reaktion hängt stark vom Niederschlagsniveau selbst ab:

| Winterniederschlag | n | Reaktion (m je 100 mm) | Anstieg (m) |
|---|---|---|---|
| < 180 mm | 200 | 0,061 | 0,10 |
| 180–220 mm | 573 | 0,164 | 0,33 |
| 220–260 mm | 1.053 | 0,203 | 0,50 |
| 260–300 mm | 1.005 | 0,230 | 0,64 |
| 300–340 mm | 741 | 0,261 | 0,83 |
| > 340 mm | 768 | 0,274 | 1,08 |

In nassen Wintern ist die Ausbeute je Millimeter rund **4,5-mal höher** als in trockenen.
Der Bodenspeicher nimmt sich seinen Anteil zuerst; erst der Überschuss versickert.

Praktische Folge: 17 % weniger Winterniederschlag erzeugten 27 % weniger Neubildung.
Jede Planung, die Niederschlag und verfügbares Grundwasser linear verknüpft,
überschätzt das Dargebot in trockenen Jahren systematisch.

## Regionale Differenzierung

| Regime | n | Reaktion über 30 J. | Anstieg über 30 J. |
|---|---|---|---|
| Tiefland (< 150 m) | 1.054 | **−0,046 (p = 0,004)** | −0,228 m (p < 0,001) |
| Hügelland (150–300 m) | 2.263 | −0,006 (p = 0,738) | −0,239 m (p < 0,001) |
| Bergland (≥ 300 m) | 1.023 | −0,045 (p = 0,159) | −0,364 m (p < 0,001) |

Der absolute Anstieg sinkt überall signifikant. Eine echte Abschwächung der Reaktion
je Millimeter zeigt sich **nur im Tiefland** – dort überlebt die ursprüngliche Hypothese
und verdient eine genauere Prüfung.

## Einschränkungen

1. **Geringe erklärte Varianz.** Das Within-R² liegt bei 0,056. Jahr und Kontrollgrößen
   erklären nur einen kleinen Teil der Streuung; der Rest ist Standort- und
   Jahresrauschen. Die Trendaussagen sind belastbar, die Modellgüte ist es nicht.
2. **Die Bodenfeuchte-Kontrolle ist methodisch unsauber.** Der Koeffizient ist negativ
   (−0,016, p < 0,001), was kontraintuitiv wirkt. Vermutlich ein Artefakt der
   Baseline-Definition: Ein nasser Oktober hat den Wasserstand bereits gehoben, womit
   für den Winteranstieg weniger Spielraum bleibt. Das ist kein Gegenbeleg zur
   Speicherhypothese, sondern eine Schwäche der Spezifikation.
3. **Entnahme ist nicht berücksichtigt.** Ein Teil des sinkenden Anstiegs könnte auf
   Förderung statt auf Klima zurückgehen. Ohne Entnahmedaten nicht trennbar.
4. **Definitionsabhängigkeit.** Novemberbasis und Dezember-bis-Mai-Höchststand sind eine
   von mehreren vertretbaren Festlegungen. Gegenprobe mit Summenlinien oder einem
   Transferfunktionsmodell steht aus.
5. **Ausreißer 2014.** Mit 156 mm Winterniederschlag und einer Reaktion von 0,036 das
   Extremjahr der Reihe. Robustheitsprüfung ohne dieses Jahr steht aus.
6. **Selektionseffekt.** Die 140 Messstellen sind 13,4 % des sächsischen Mengenmessnetzes,
   ausgewählt nach Vollständigkeit. Sie repräsentieren lange, lückenarme Reihen,
   nicht notwendig das Land.

## Hinweis zu den Rohdaten

`GWL_flag` ist invers zur naheliegenden Lesart: 98,8 % der Werte stehen auf `True`,
1,2 % auf `False`. Da das Paper einen Imputationsanteil von durchschnittlich 1,05 %
angibt, markiert `False` die imputierten Werte und `True` die gemessenen.

## Dateien

- `analyse_winterreaktion.py` – Auswertungsskript, von `dynamic/` ausgehend reproduzierbar
- `sachsen_inventar.csv` – die 140 Messstellen mit Koordinaten und Standortmerkmalen
- `sachsen_winterreaktion.csv` – 4.340 Messstellen-Jahre mit allen abgeleiteten Größen
