# Robustheitsprüfung der Befunde zur sächsischen Grundwasserneubildung

Geprüft wurden die drei offenen Punkte aus `BEFUNDE.md`: das Extremjahr 2014,
die Abhängigkeit von der Baseline-Definition und der Ersatz des Anstiegsmaßes
durch ein prozessbasiertes Transferfunktionsmodell.

**Ergebnis in einem Satz:** Die Überproportionalität hält allen Prüfungen stand,
der Befund „keine Abschwächung je Millimeter" wird sogar deutlich stärker – aber
die quantitative Zerlegung des Rückgangs scheitert am Modell, und ein kleiner,
systematischer Rest bleibt unerklärt.

---

## 1. Das Extremjahr 2014

2014 war mit 156 mm Winterniederschlag das trockenste Jahr der Reihe und dominierte
die unterste Niederschlagsklasse (108 von 200 Messstellen-Jahren).

Die Kurvenform überlebt seinen Ausschluss. Der unterste Stützpunkt steigt von 0,061
auf 0,128 m je 100 mm, die Monotonie bleibt vollständig erhalten:

| Winterniederschlag | alle Jahre | ohne 2014 |
|---|---|---|
| < 180 mm | 0,061 | 0,128 |
| 180–220 mm | 0,164 | 0,169 |
| 220–260 mm | 0,203 | 0,204 |
| 260–300 mm | 0,230 | 0,231 |
| 300–340 mm | 0,261 | 0,261 |
| > 340 mm | 0,274 | 0,274 |

Die Monotonie gilt auch getrennt nach Regime (Tiefland 0,045 → 0,261;
Hügelland 0,080 → 0,281; Bergland 0,152 → 0,267).

**Zwei Korrekturen am bisherigen Stand:**

Der rohe Trend der Reaktion je Millimeter war allein von 2014 getragen. Ohne dieses
Jahr: −0,004 über 30 Jahre bei p = 0,716 statt −0,025 bei p = 0,041. Es gibt damit
schon ohne jede Kontrollgröße keinen Hinweis auf eine Abschwächung.

Der Tiefland-Befund hält der Prüfung nicht stand. Mit 2014 war er signifikant
(−0,046, p = 0,004), ohne 2014 nicht mehr (−0,028, p = 0,069). Die Aussage
„im Tiefland überlebt die Hypothese" ist zurückzunehmen.

---

## 2. Die Form des Zusammenhangs: Elastizität statt Konvexität

Die bisherige Formulierung war unpräzise. Ein quadratischer Term in
`Anstieg ~ P + P²` ist **negativ** (−0,074, p = 0,043), die Kurve ist also leicht
konkav, nicht konvex. Die Überproportionalität entsteht nicht durch Krümmung,
sondern durch einen **Achsenabschnitt**:

    Anstieg [m] = −0,444 + 0,00472 · P [mm]     (ohne 2014)

Der Nulldurchgang liegt bei rund **94 mm Winterniederschlag** – darunter erreicht
rechnerisch nichts mehr den Grundwasserspiegel. Das ist der Schwellenwert, den der
Bodenspeicher setzt.

Die robuste Kennzahl ist die **Elastizität**: ein Prozent mehr Winterniederschlag
bringt etwa **1,8 Prozent mehr Neubildung**.

Ein explizit gefittetes Hockeystick-Modell `Anstieg = b · max(0, P − P₀)` liefert
P₀ = 155 mm und 0,472 m je 100 mm darüber, aber mit instabilen Werten je Regime
(Hügelland: P₀ = 0). Der Schwellenwert selbst ist also **nicht belastbar bestimmt**;
die Elastizität ist es.

---

## 3. Vier Baseline-Definitionen

| Definition | Rückgang Dekade 1 → 3 | Elastizität | Trend roh (30 J.) | Trend mit Regen kontrolliert |
|---|---|---|---|---|
| A – November-Basis, Peak Dez–Mai | −20,8 % | 1,78 | −0,266 (p < 0,001) | +0,024 (p = 0,484) |
| B – Minimum Okt–Dez als Basis | −16,0 % | 1,85 | −0,213 (p < 0,001) | +0,057 (p = 0,056) |
| C – Halbjahresdifferenz Apr–Okt | −40,7 % | 1,85 | −0,357 (p < 0,001) | −0,076 (p = 0,062) |
| D – Jahresamplitude max − min | −7,3 % | 1,07 | −0,136 (p < 0,001) | +0,105 (p = 0,001) |

**Was robust ist:** Der Rückgang der Neubildung ist in allen vier Definitionen
hochsignifikant. Und in keiner einzigen bleibt nach Kontrolle des Niederschlags ein
signifikant negativer Trend übrig. Der Kernbefund steht damit auf vier unabhängigen
Messkonstruktionen.

**Was nicht robust ist:** Die *Höhe* des Rückgangs schwankt um den Faktor fünf,
von −7,3 % bis −40,7 %. Jede Zahl, die den Rückgang beziffert, muss ihre Definition
mitnennen.

Die Jahresamplitude (D) fällt mit einer Elastizität von 1,07 aus der Reihe. Das ist
plausibel: Sie enthält den sommerlichen Tiefststand, der von der Verdunstung bestimmt
wird und nicht vom Niederschlag. Die Überproportionalität ist also eine Eigenschaft
der *Neubildung*, nicht der Grundwasserdynamik insgesamt.

Definition C deutet als einzige einen negativen Rest an (−0,076, p = 0,062). Knapp
außerhalb der Signifikanz, aber erwähnenswert.

---

## 4. Transferfunktionsmodell

Aufbau: Bodenspeicher mit Kapazität C, dessen Verdunstung proportional zur Füllung
zehrt und der erst bei Überlauf Sickerwasser abgibt, gekoppelt an lineare
Grundwasserspeicher. Die Nichtlinearität entsteht hier aus der Modellstruktur und
wird nicht aus den Daten gefittet.

Zwei Varianten: ein Speicher (`modell_transferfunktion.py`) und zwei parallele
Speicher, schnell und langsam (`modell_zwei_speicher.py`).

### Güte

| | NSE Median | Anteil NSE > 0,5 | Amplitude Modell/Beobachtung |
|---|---|---|---|
| Ein Speicher | 0,417 | 33,6 % | ~0,11 |
| Zwei Speicher | 0,416 | 32,9 % | 0,50 |

Zum Vergleich: Das beste Benchmark-Modell in GEMS-GER, ein global trainiertes LSTM
mit dynamischen und statischen Eingaben, erreicht national NSE > 0,5 für 52 % der
Messstellen. Ein Dreiparametermodell kommt also auf etwa zwei Drittel der Trefferquote
eines tiefen neuronalen Netzes – bei vollständiger Interpretierbarkeit. Das ist für
sich genommen ein verwertbares Argument zur Erklärbarkeitsfrage.

### Kalibrierte Parameter

| Regime | C [mm] | τ schnell [Wo] | τ langsam [Wo] | NSE |
|---|---|---|---|---|
| Tiefland | 143 | 1 | 58 | 0,48 |
| Hügelland | 171 | 1 | 45 | 0,41 |
| Bergland | 502 | 1 | 45 | 0,35 |

Im Bergland läuft C an den Rand des Suchgitters (600 mm). Der Bodenspeicher ist dort
nicht identifiziert – das Thornthwaite-Konzept passt nicht auf klüftiges Festgestein.
Entsprechend ist die Güte dort am schlechtesten.

### Parameterstabilität: der einzige Hinweis auf echte Veränderung

Kalibrierung auf 1992–2006, Validierung auf 2007–2022. Ein Modell mit konstanten
Parametern **überschätzt** die Grundwasserstände der Validierperiode systematisch:

| | Bias | Residuendrift |
|---|---|---|
| Ein Speicher | −0,027 m (p = 0,037) | −0,0027 m/Jahr (p = 0,012) |
| Zwei Speicher | −0,039 m (p = 0,013) | −0,0022 m/Jahr (p = 0,008) |

Beide Modellvarianten zeigen denselben Befund: Über die 16 Validierungsjahre
summiert sich eine unerklärte Absenkung von etwa **3 bis 4 Zentimetern**.

Das ist klein gegenüber dem beobachteten Rückgang des Winteranstiegs von 0,14 bis
0,27 m, aber es ist systematisch und in zwei unabhängigen Modellstrukturen
reproduzierbar. **Drei Erklärungen sind damit nicht unterscheidbar:** tatsächlich
verändertes Systemverhalten, Grundwasserentnahme, oder strukturelle Modellfehler.

### Was nicht funktioniert hat

Die geplante Zerlegung des Rückgangs in einen vom Klimaantrieb erklärten und einen
unerklärten Anteil ist gescheitert. Das Modell unterschätzt die saisonale Amplitude
um die Hälfte, und der simulierte Winteranstieg sinkt im letzten Jahrzehnt auf einen
Median von 0,025 m – praktisch Rauschen. Relative Rückgänge gegen diesen Nenner
ergeben −70 % gegen beobachtete −23 %, also „300 % erklärt". Die Zahl ist ein
Artefakt und wird nicht berichtet.

Verwertbar bleibt der qualitative Vergleich: Das Modell erzeugt aus reiner
Prozessstruktur eine Elastizität von **2,53** gegen beobachtete **1,76**. Es bestätigt
den Mechanismus unabhängig von der empirischen Anpassung, überzeichnet ihn aber.

---

## Stand der Hypothesen

| Hypothese | Status |
|---|---|
| Die Neubildung ist zurückgegangen | **bestätigt**, in vier Definitionen, p < 0,001 |
| Der Rückgang geht überwiegend auf weniger Winterniederschlag zurück | **bestätigt**, Trend verschwindet unter Kontrolle in allen vier Definitionen |
| Neubildung reagiert überproportional auf Niederschlag | **bestätigt**, Elastizität 1,8, prüfungsfest gegen Ausreißer und Definitionen |
| Es gibt einen Schwellenwert | **plausibel**, Lage aber nicht belastbar (94 bis 155 mm) |
| Der Grundwasserkörper reagiert je Millimeter schwächer als früher | **nicht bestätigt**; der Hinweis darauf lag an einem einzigen Extremjahr |
| ... im Tiefland doch | **zurückgenommen** (p = 0,069 ohne 2014) |
| Es bleibt ein unerklärter Rest | **ja, klein**: 3–4 cm über 16 Jahre, in zwei Modellen, Ursache offen |

## Dateien

- `modell_transferfunktion.py` – Einspeicher-Modell, Kalibrierung und Split-Sample
- `modell_zwei_speicher.py` – Zwei-Speicher-Variante
- `zerlegung2.py` – gescheiterte Zerlegung, dokumentiert zur Nachvollziehbarkeit
- `sachsen_modell2_parameter.csv` – kalibrierte Parameter je Messstelle
- `sachsen_baselines.csv` – vier Anstiegsmaße je Messstelle und Jahr
