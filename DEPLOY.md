# Entwicklungs- und Testablauf – CarenDMR 0.2.1.25

Dieser Ablauf gehört ausschließlich zum Offline-Vocodervergleich. Es wird **nicht gefunkt** und die GUI muss nicht gestartet werden.

## 1. Projektordner und Version

```powershell
cd C:\Users\abaru\OneDrive\AB_Entwicklung\CarenDMR
python -c "from carendmr.version import get_version; print(get_version())"
```

Erwartet:

```text
0.2.1.25
```

## 2. Bestehende native Basis prüfen

```powershell
Test-Path .\native\carendmr_mbe.dll
Test-Path .\native\carendmr_vocoder_bridge.dll
```

Beide Ausgaben müssen `True` sein.

## 3. MD380/Dynarmic-Bridge für Windows bauen

Der Build verwendet den festgelegten Upstream-Stand `55c9a2c6d502567380c7dfaf4a2e3cc4dd6d1dd5` und erzeugt lokal `native\carendmr_md380_bridge.dll`.

```powershell
Unblock-File .\native\build_md380_dynarmic_windows.ps1
powershell -ExecutionPolicy Bypass -File .\native\build_md380_dynarmic_windows.ps1
```

Falls der Build wegen fehlender MSYS2-Bausteine stoppt, **nicht improvisieren**. Die vollständige Fehlermeldung aus der Shell weitergeben. Der Build verändert den Live-Funkpfad nicht.

Danach prüfen:

```powershell
Test-Path .\native\carendmr_md380_bridge.dll
```

Erwartet: `True`.

## 4. Offline-A/B-Hörtest starten

Wir verwenden exakt die bereits als 10/10 bewertete Datei:

```powershell
python .\tools\ambe_md380_ab.py "C:\Users\abaru\OneDrive\AB_Entwicklung\CarenDMR\logs\audio_lab\AudioTest_20260807_080745_335\03_vor_ambe_8k.wav"
```

Der Ergebnisordner ist:

```text
C:\Users\abaru\OneDrive\AB_Entwicklung\CarenDMR\logs\audio_lab\AudioTest_20260807_080745_335\ambe_md380_ab
```

Darin liegen:

```text
00_referenz_10von10_vor_ambe_8k.wav
01_encoder_eingang_plus_01dB_8k.wav
02_plugin_A_bisher_loopback_8k.wav
03_md380_DroidStar_loopback_8k.wav
report.json
```

## 5. Hörbewertung

Mit unveränderter Wiedergabelautstärke anhören:

```text
00 = Referenz
01 = Encoder-Eingang +1 dB
02 = bisheriger Windows-Vocoder
03 = MD380/DroidStar-Pfad
```

Benötigt werden nur die Hörnoten für `02` und `03` sowie eine kurze Aussage zu Zischen/Wabern in Sprechpausen und an Wortenden.

Anschließend den kompletten Ordner `ambe_md380_ab` als ZIP bereitstellen.

**Danach stoppen. Kein Parrot-Test und keine Audioeinstellungen verändern.**

## 6. Git erst nach gemeinsamer Freigabe

Git-Commit, Push und Tag werden erst durchgeführt, wenn der A/B-Befund ausgewertet und 0.2.1.25 als sinnvoller Stand bestätigt wurde.


## Wiederholungslauf nach dem Windows-Linkfix

Keine weiteren MSYS2-Pakete installieren.

```powershell
cd C:\Users\abaru\OneDrive\AB_Entwicklung\CarenDMR

powershell -ExecutionPolicy Bypass -File .\native\build_md380_dynarmic_windows.ps1
```

Am Ende muss erscheinen:

```text
MD380-Dynarmic-Bridge erfolgreich gebaut:
```

Danach:

```powershell
python .\tools\ambe_md380_ab.py "C:\Users\abaru\OneDrive\AB_Entwicklung\CarenDMR\logs\audio_lab\AudioTest_20260807_080745_335\03_vor_ambe_8k.wav"
```

Danach den erzeugten Ordner `ambe_md380_ab` anhören und bereitstellen.


## Live-TX-Prüfung 0.2.1.25

Zuerst sicherstellen, dass die bereits gebaute MD380-Bridge vorhanden ist:

```powershell
cd C:\Users\abaru\OneDrive\AB_Entwicklung\CarenDMR
Test-Path .\native\carendmr_md380_bridge.dll
```

Erwartet: `True`.

Danach Anwendung normal starten und zunächst ausschließlich Parrot TG9990, TS2, Privat testen. Der Live-TX verwendet nun MD380/DroidStar; am Mikrofon-, DSP-, Timing- und RX-Pfad wurde für diesen Test nichts verändert.

Bewertung: Lautstärke, Ruhe in Sprechpausen, Wortenden und Gesamtverständlichkeit. Erst nach diesem kontrollierten Parrot-Test wird die verbleibende kleine Unsauberkeit optimiert.


## Direktprüfung 0.2.1.25

Die bereits gebaute Bridge muss vorhanden sein:

```powershell
cd C:\Users\abaru\OneDrive\AB_Entwicklung\CarenDMR
Test-Path .\native\carendmr_md380_bridge.dll
```

Erwartet: `True`.

Danach virtuelle Umgebung aktivieren und CarenDMR normal starten:

```powershell
.\.venv\Scripts\Activate.ps1
python main.py --gui
```

Keine manuelle PATH-Erweiterung nötig.

Danach ausschließlich Parrot TG9990 / TS2 / Privat testen und bewerten:
- Rauschen/Wabern in Pausen,
- Lautstärke,
- Wortenden,
- Verständlichkeit.


## Live-Parrot-Test 0.2.1.25

Die vorhandene MD380-Bridge bleibt erhalten:

```powershell
cd C:\Users\abaru\OneDrive\AB_Entwicklung\CarenDMR
Test-Path .\native\carendmr_md380_bridge.dll
```

Erwartet: `True`.

Danach:

```powershell
.\.venv\Scripts\Activate.ps1
python main.py --gui
```

Test ausschließlich mit TG9990 / TS2 / Privat. Drei kurze Sendungen von etwa 8–10 Sekunden durchführen. Keine Audioeinstellungen verändern.

Bewerten:
- kommt der Parrot vollständig zurück,
- bleibt TX nach Sendeende gelb,
- Reihenfolge der Pieptöne,
- Sprachqualität.

Bei weiterem Fehler `logs\tx_rx_timing.log` sichern. Relevant sind insbesondere:
`TX_ENCODER_PUFFER_BEREIT`, `TX_ENCODER_PUFFER_STATISTIK`,
`TX_JITTER_STATISTIK`, `TX_ENCODER_STATISTIK` und Parrot-Endemarken.


## MD380-Pegel-Hörtest 0.2.1.25

Die vorhandene MD380-Bridge muss weiterhin vorhanden sein:

```powershell
cd C:\Users\abaru\OneDrive\AB_Entwicklung\CarenDMR
Test-Path .\native\carendmr_md380_bridge.dll
```

Erwartet: `True`.

Danach den bekannten Referenz-Eingang verwenden:

```powershell
.\.venv\Scripts\Activate.ps1

python .\tools\ambe_md380_level_sweep.py "C:\Users\abaru\OneDrive\AB_Entwicklung\CarenDMR\logs\audio_lab\AudioTest_20260807_080745_335\03_vor_ambe_8k.wav"
```

Erzeugt wird:

```text
...\AudioTest_20260807_080745_335\ambe_md380_level_sweep
```

Hörfolge:

```text
00 = Referenz vor AMBE
01 = -2 dB
02 = -1 dB
03 =  0 dB
04 = +1 dB
05 = +2 dB
06 = +3 dB
```

Bewertung je Datei: Lautstärke, Ruhe in Pausen, Wortenden, Verständlichkeit und Gesamteindruck.


## Live-Parrot-Prüfung 0.2.1.25

```powershell
cd C:\Users\abaru\OneDrive\AB_Entwicklung\CarenDMR
Test-Path .\native\carendmr_md380_bridge.dll
.\.venv\Scripts\Activate.ps1
python main.py --gui
```

`Test-Path` muss `True` liefern.

Danach TG9990 / TS2 / Privat mit drei bis vier kurzen Sendungen testen.
Keine Audioeinstellungen verändern.

Bewerten:
- vollständiger Parrot-Rücklauf,
- Lautstärke,
- Wortenden,
- Pausenruhe,
- Gesamtqualität 1–10.

Der stabile 240-ms-TX-Puffer und die TX/RX-Logik bleiben gegenüber 0.2.1.22 unverändert.


## Kritischer TX→RX-Test 0.2.1.38

```powershell
cd C:\Users\abaru\OneDrive\AB_Entwicklung\CarenDMR
Test-Path .\native\carendmr_md380_bridge.dll
.\.venv\Scripts\Activate.ps1
python main.py --gui
```

`Test-Path` muss `True` liefern.

Dann TG9990 / TS2 / Privat verbinden und mindestens vier kurze Sendungen durchführen.

Erwarteter Ablauf pro Test:

```text
PTT AUS
→ Doppelpiep
→ letzter Voice-Burst + DMR-Terminator
→ TX beendet
→ normaler RX wird sofort neu gestartet
→ Status grün/empfangsbereit
→ Parrot oder andere Station wird über den normalen RX-Pfad empfangen
```

Wichtig: Die RX-Rückkehr darf nicht mehr vom Eintreffen eines Parrot-Echos abhängen. Im Timing-Log darf für den Live-TX nach `TX_TERMINATOR_GESENDET` kein `PARROT_ECHO_WARTE_START` mehr erscheinen.


## Persistente TX/RX-Session prüfen – 0.2.1.38

```powershell
cd C:\Users\abaru\OneDrive\AB_Entwicklung\CarenDMR
Test-Path .\native\carendmr_md380_bridge.dll
.\.venv\Scripts\Activate.ps1
python main.py --gui
```

`Test-Path` muss `True` liefern.

Danach zunächst TG9990 / TS2 / Privat verbinden und vier kurze Parrot-Rufe durchführen.

Im Timing-Log muss der TX/RX-Wechsel ohne erneuten BrandMeister-Login erscheinen. Erwartete Marken sind insbesondere:

```text
RX_SESSION_OFFEN_GEHALTEN
TX_SESSION_WIEDERVERWENDET
TX_SESSION_OFFEN_GEHALTEN
RX_SESSION_WIEDERVERWENDET
RX_ZIELAKTIVIERUNG_UEBERSPRUNGEN
```

Zwischen `TX_TERMINATOR_GESENDET` und erneutem RX dürfen bei unverändertem Funkziel keine neuen Marken `RX_LOGIN_START` oder `RX_ZIELAKTIVIERUNG_START` erscheinen.

Prüfen:
- TX wird nach PTT-Aus schnell beendet,
- Empfang setzt sofort wieder ein,
- Parrot kommt vollständig zurück,
- mehrere TX/RX-Wechsel funktionieren ohne Neuverbinden,
- erst ein tatsächlicher TG-/TS-/Rufart-Wechsel erzeugt eine neue BrandMeister-Anmeldung.


## Parrot-RX-Filter prüfen – 0.2.1.38

TG9990 / TS2 / Privat verbinden und vier kurze Parrot-Rufe durchführen.

Erwartung:
- TX wird bei BrandMeister als `2632198 -> 9990` sichtbar.
- Parrot-RX kommt als `9990 -> 2632198`.
- Diagnose meldet für diese Pakete `FILTER AKZEPTIERT`.
- Nach PTT-Aus kein Logout/Login; dieselbe BrandMeister-Session bleibt aktiv.
- Antwort vollständig hörbar.

TG91 ist für diesen Test keine Voraussetzung. Ein zuvor verbliebener dynamischer TG91-Zustand kann im BrandMeister-Dashboard mit `Drop dynamic groups` entfernt werden.


## Audio Coach und Fensterposition prüfen – 0.2.1.38

```powershell
cd C:\Users\abaru\OneDrive\AB_Entwicklung\CarenDMR
python -c "from carendmr.version import get_version; print(get_version())"
python -m pytest tests
python main.py --gui
```

Erwartete Version: `0.2.1.38`.

### Test A – Audio Coach

1. TG9990 / TS2 / Privat verbinden.
2. Einen normalen Parrot-Ruf durchführen und die Qualität merken.
3. Audio Coach öffnen und `Eigene Modulation testen` starten.
4. Genau einen Coach-Parrot-Ruf durchführen.
5. Danach ohne Programmneustart erneut einen normalen Parrot-Ruf durchführen.

Erwartung:
- Coach und normaler PTT verwenden dieselbe Live-TX-Audiokette.
- Beim Start des Coach wird das Mikrofon nicht separat vorab geöffnet.
- Im Timing-Log steht `AUDIO_TEST_BEREIT Passiv; kein separater Mikrofon-Vorlauf`.
- Nach dem Coach darf die normale Parrot-Qualität nicht schlechter werden.

### Test B – Fensterposition

1. Hauptfenster an eine gut erkennbare Position verschieben und Größe ändern.
2. CarenDMR normal schließen.
3. CarenDMR erneut starten.

Erwartung:
- Position und Größe werden wiederhergestellt.
- Die Datei `config\window.local.json` wird angelegt.
- Nach einem Monitorwechsel darf das Fenster nicht unsichtbar außerhalb aller Bildschirme starten.


## Audio Coach / RX-AGC prüfen – 0.2.1.38

1. Prüfen, dass in der Oberfläche `AGC aktiv` ausgeschaltet ist.
2. TG9990 / TS2 / Privat verbinden.
3. Einen normalen Parrot-Ruf durchführen.
4. Audio Coach starten und genau einen Modulationstest durchführen.
5. Auf die vollständige Parrot-Antwort warten.
6. Danach erneut einen normalen Parrot-Ruf durchführen.

Erwartung:
- Kein hörbares automatisches Hochregeln am Satzanfang, wenn AGC ausgeschaltet ist.
- Audio Coach meldet nicht mehr `Keine vollständige Parrot-Antwort empfangen`.
- Im Timing-Log erscheinen `AUDIO_TEST_WARTET_AUF_PARROT` und danach `AUDIO_TEST_PARROT_GESPEICHERT`.
- Im Audio-Testordner liegt eine Datei `rx_*_parrot_nach_ambe_8k.wav`.
- `analysis.json` enthält `extra.echo_received = true`.


## Tuner/Audio-Coach prüfen – 0.2.1.38

1. CarenDMR starten und DMR Audio-Tuner aufklappen.
2. Prüfen: `Parrot vorbereiten` und `Audio-Assistent` sowie deren Statuszeile sind entfernt.
3. Prüfen: `Zurücksetzen` ist weiterhin vorhanden.
4. Im Audio Coach `Eigene Modulation testen` durchführen.
5. Bei einer Empfehlung auf die Formulierung achten.

Erwartung bei bereits eingestellten Tiefen `-2 dB` und erneuter Bass-Empfehlung `-2`:
`Tiefen → -4 dB (aktuell -2 dB, weitere Änderung -2)`

Damit ist eindeutig, dass die Empfehlung eine weitere Korrektur meint und nicht erneut den bereits aktiven Wert `-2 dB`.


## Vollständiges Audio-Coach-Parrot-Echo prüfen – 0.2.1.38

1. TG9990 / TS2 / Privat verbinden.
2. Im Audio Coach `Eigene Modulation testen` starten.
3. Referenztext vollständig sprechen und TX beenden.
4. Die komplette Parrot-Wiedergabe abwarten.

Erwartung:
- Der Coach darf während laufender Parrot-Wiedergabe noch kein Endergebnis anzeigen.
- Kurze frühe Terminatoren erscheinen ggf. nur im Timing-Log als `AUDIO_TEST_PARROT_TERMINATOR_IGNORIERT`.
- `AUDIO_TEST_PARROT_GESPEICHERT` erscheint erst nahe dem echten Ende der Parrot-Wiedergabe.
- Die gespeicherte RX-WAV hat ungefähr die Länge der TX-Aufnahme.
- Erst danach startet die Audioanalyse und der Coach zeigt das Ergebnis.


## Betriebsmaske / Audio-Tuner / zuletzt gehört prüfen – 0.2.1.38

```powershell
cd C:\Users\abaru\OneDrive\AB_Entwicklung\CarenDMR
python -c "from carendmr.version import get_version; print(get_version())"
python -m pytest tests
python main.py --gui
```

Erwartete Version: `0.2.1.38`.

### Betriebsmaske
- Kein großer zusätzlicher CarenDMR-Kopfblock mehr im Tab `Betrieb`.
- `Audio-Tuner…` öffnet ein eigenes Fenster.
- Öffnen und Schließen des Audio-Tuners verändert die Geometrie der Betriebsmaske nicht.
- TX und Betriebsinformationen bleiben an ihrer Position.

### Zuletzt gehört
- Unter `Aktuelle Station` erscheint `ZULETZT GEHÖRT`.
- Es werden maximal drei zuletzt abgeschlossene Empfangsstationen aus der QSO-Historie gezeigt.
- Zeile enthält Uhrzeit, Rufzeichen/DMR-ID, optional Name/Land sowie TG/TS.
- Die Liste löst noch keinen Privatruf aus.


## UI-Prüfung – 0.2.1.38

```powershell
cd C:\Users\abaru\OneDrive\AB_Entwicklung\CarenDMR
python -c "from carendmr.version import get_version; print(get_version())"
python -m pytest tests
python main.py --gui
```

Erwartete Version: `0.2.1.38`.

### Betrieb
- Beim ersten Start nach 0.2.1.33 wird ein altes übergroßes Fenster einmalig auf ca. 980 × 720 normalisiert.
- Danach werden Position und Größe wieder normal gespeichert.
- Unter TX befindet sich kein großer leerer Bereich mehr.
- `Betriebsinformationen` schließen direkt an die beiden Hauptkarten an.
- Beschriftung und Wert sind bei `Aktuelle Station` optisch klar unterscheidbar.

### Zuletzt gehört
- Echte Tabelle mit Kopfzeile: `Zeit | Rufzeichen | Name | Land | Ziel`.
- Maximal drei unterschiedliche zuletzt gehörte Stationen.
- Keine Ruf-/Klickfunktion in dieser Version.

### Audio-Tuner
- `Audio-Tuner…` öffnet weiterhin ein eigenes Fenster.
- Profil und Zurücksetzen stehen sauber in einer Zeile.
- Alle sieben Regler stehen gleichmäßig untereinander.
- Werte befinden sich rechts in klaren Wertefeldern.
- Keine großen leeren Abstände zwischen Überschrift, Profil und Reglern.


## Schnellwahl / RX-Liste / TX prüfen – 0.2.1.38

```powershell
cd C:\Users\abaru\OneDrive\AB_Entwicklung\CarenDMR
python -c "from carendmr.version import get_version; print(get_version())"
python -m pytest tests
python main.py --gui
```

Erwartete Version: `0.2.1.38`.

- Oberhalb der Talkgroup-Eingabe erscheinen maximal drei Schnellwahlknöpfe aus den ersten drei Favoriten.
- Getrennt: Schnellwahl anklicken → TG/TS/Rufart werden übernommen → Verbindung wird aufgebaut.
- Verbunden: Schnellwahl anklicken → aktuelle Verbindung wird beendet → neuer Favorit vollständig übernommen → Verbindung wird neu aufgebaut.
- Nach Ende einer empfangenen Station muss sie unmittelbar in `Zuletzt gehört` erscheinen.
- TX reicht nahezu bis an den linken und rechten Rand der Bedienkarte.


## Favoriten-Sortierung / TX prüfen – 0.2.1.38

- Talkgroups öffnen, alle Filter zurücksetzen.
- Einen Favoriten mit gedrückter linker Maustaste innerhalb des Favoritenblocks nach oben/unten ziehen.
- Favoriten müssen nach dem Loslassen weiterhin geschlossen oben stehen und die neue Reihenfolge behalten.
- Zurück zu Betrieb: die ersten drei Favoriten müssen in derselben Reihenfolge als Schnellwahl erscheinen.
- Nicht-Favoriten dürfen nicht per Drag&Drop sortiert werden.
- TX muss sichtbar deutlich höher sein als in 0.2.1.36 und die freie Fläche nach unten ausnutzen.
- Während TX erscheint die Sendedauer direkt im TX-Button.


## Favoriten-Drop und TG-Suchranking prüfen – 0.2.1.38

- Im Talkgroups-Reiter ohne Filter einen Favoriten über einen anderen ziehen.
- Nach dem Loslassen müssen alle Favoriten sofort sichtbar bleiben; die verdrängte Zeile muss direkt nach unten rutschen.
- Reihenfolge muss nach Tabwechsel/Neustart erhalten bleiben.
- In der Suche `262` eingeben.
- Erwartung: TG `262` steht als exakter Treffer ganz oben.
- Danach folgen passende Präfix-TGs wie 2621, 2622, 2623 usw.; Favoritenstatus darf einen schlechteren Treffer nicht vor TG 262 schieben.
- Ohne Suchtext stehen Favoriten weiterhin immer oben.


## Regression 0.2.1.39 – RX-Pegel und TX-Anzeige

1. CarenDMR starten und mit BrandMeister verbinden.
2. RX-Lautstärke auf 100 % setzen, AGC zunächst ausschalten und eine bekannte Station bzw. Parrot empfangen. Gültige PCM16-Pegel werden durch CarenDMR nicht zusätzlich komprimiert.
3. AGC einschalten und erneut empfangen. Verstärkte Spitzen bleiben auf den PCM16-Bereich begrenzt.
4. TX starten. Die Laufzeit muss ausschließlich im großen TX-Button als `TX   <n> s` erscheinen. Unter dem TX-Button darf kein separates `0`-/Zeit-Label mehr vorhanden sein.
5. TX beenden und prüfen, dass RX unmittelbar wieder aktiv ist.


## Regression 0.2.1.40 – eigenständiger TG-Monitor

1. Virtuelle Umgebung aktivieren und `python -m pip install -r requirements.txt` ausführen. Neu ist `python-socketio[client]`.
2. CarenDMR normal mit `python main.py --gui` starten und verbinden.
3. In einer zweiten Shell mit derselben virtuellen Umgebung `python tg_monitor.py` starten.
4. Im TG-Monitor mehrere Talkgroups durch Komma eingeben, z. B. `91, 262, 263`, und **Überwachung übernehmen** wählen.
5. Prüfen, dass der Status **Mit BrandMeister Last Heard verbunden.** erscheint und Aktivität nur für die ausgewählten TGs in der Tabelle aktualisiert wird.
6. Eine TG markieren und **In CarenDMR übernehmen** ausführen. Bei bestehender Verbindung muss CarenDMR sauber trennen, TG/TS setzen und wieder verbinden.
7. Während eines laufenden TX erneut eine TG-Übergabe versuchen. CarenDMR muss den Wechsel ablehnen; TX darf nicht beeinflusst werden.
8. CarenDMR schließen und im TG-Monitor erneut **In CarenDMR übernehmen** wählen. Der Monitor muss melden, dass CarenDMR nicht erreichbar ist; der TG-Monitor selbst läuft weiter.
9. TG-Monitor schließen und neu starten. Überwachte TGs und Übergabe-Timeslot müssen wiederhergestellt werden.


## Diagnose 0.2.1.41 – TG-Monitor Last Heard

1. CarenDMR und den TG-Monitor wie gewohnt starten.
2. Im TG-Monitor mindestens eine sicher aktive Talkgroup überwachen, vorzugsweise `91`.
3. 30 bis 60 Sekunden warten, während auf der TG tatsächlich gesprochen wird.
4. Danach `logs/tg_monitor.log` öffnen bzw. für die Fehleranalyse bereitstellen.
5. Im Log müssen mindestens Verbindungszeilen wie `START`, `VERBINDUNG wird aufgebaut` und `VERBUNDEN Socket.IO` erscheinen.
6. Für eingehende BrandMeister-Ereignisse stehen Zeilen `MQTT RAW=...`.
7. Direkt danach zeigt `PARSE ... FILTER=TREFFER` oder `FILTER=IGNORIERT`, wie CarenDMR das Ereignis interpretiert hat.
8. Falls keine `MQTT RAW`-Zeilen entstehen, liegt das Problem vor dem Parser im Last-Heard-Datenweg. Falls RAW-Zeilen vorhanden sind, aber `PARSE VERWORFEN` erscheint, ist das tatsächliche Payload-Format maßgeblich für den nächsten Fix.


## Regression 0.2.1.42 – BrandMeister Last-Heard Subscription

1. CarenDMR wie gewohnt starten.
2. TG-Monitor mit `python tg_monitor.py` in einer zweiten Shell starten.
3. Eine sicher aktive Talkgroup überwachen, vorzugsweise `91`.
4. In `logs/tg_monitor.log` müssen nach `VERBUNDEN Socket.IO` die Zeile `SUBSCRIBE join=everything` und anschließend `MQTT RAW=...`-Einträge erscheinen.
5. Für überwachte TGs muss `FILTER=TREFFER` erscheinen und die Tabellenzeile aktualisiert werden.
6. Eine markierte TG an CarenDMR übergeben und prüfen, dass der bestehende Ablauf Trennen → TG/TS setzen → Verbinden funktioniert.
7. Während TX muss eine externe Kanalübergabe weiterhin abgewiesen werden.


## Regression 0.2.1.43 – TX-Sicherheitslimit und TG-Mindestdauer

1. CarenDMR mit einer vorhandenen `config/audio_send.local.json` starten, die `tx_safety_limit_seconds: 60` enthält. Der wirksame Wert muss auf 300 Sekunden migriert werden.
2. Einen längeren TX von deutlich über 60 Sekunden durchführen. CarenDMR darf den TX nicht mehr bei 60 Sekunden beenden.
3. Die 5-Minuten-Sicherheitsgrenze bleibt bestehen; ein versehentliches Dauersenden wird spätestens nach 300 Sekunden beendet.
4. TG-Monitor starten. `Mindestdauer` muss standardmäßig auf `3 s` stehen.
5. Ein Ereignis unter 3 Sekunden darf keine Stations-/Daueranzeige erzeugen.
6. Ein laufender oder abgeschlossener Durchgang ab 3 Sekunden muss normal angezeigt werden.
7. Mindestdauer ändern, TG-Monitor neu starten und prüfen, dass der Wert aus `config/tg_monitor.local.json` wiederhergestellt wird.


## Regression 0.2.1.44 – TG-Monitor Integration

1. CarenDMR starten und im Menü `Programm` den Eintrag **TG-Monitor starten** wählen.
2. Der TG-Monitor muss als eigenes Fenster/Programm erscheinen, während CarenDMR weiterläuft.
3. Den Menüpunkt erneut wählen. Es darf keine zweite Monitorinstanz entstehen; CarenDMR muss `Der TG-Monitor läuft bereits.` melden.
4. Im Monitor eine TG markieren und **In CarenDMR übernehmen** wählen. CarenDMR muss den Kanal wie bisher übernehmen.
5. Wenn CarenDMR den Kanal erfolgreich übernimmt, darf der Monitor nicht mehr fälschlich `Kanal konnte nicht an CarenDMR gesendet werden.` anzeigen.
6. TG-Monitor separat über `python tg_monitor.py` ein zweites Mal starten. Auch dieser Versuch muss als bereits laufende Instanz erkannt werden.
7. Monitor schließen und anschließend erneut aus CarenDMR starten. Der Start muss wieder möglich sein.


## Regression 0.2.1.45 – RX-Anfang und unerwarteter RX-Abbruch

1. CarenDMR starten. Im Betrieb muss **AGC aktiv** zunächst ausgeschaltet sein. In `logs/tx_rx_timing.log` muss `RX_AGC_DIAGNOSE Beim Programmstart ausgeschaltet` erscheinen.
2. Eine aktive Talkgroup wie TG91 mindestens mehrere Durchgänge hören. Prüfen, ob die ersten 1–2 Sekunden jetzt sofort mit normaler Lautstärke hörbar sind.
3. Falls gewünscht AGC während der Sitzung manuell einschalten und denselben Höreindruck direkt vergleichen.
4. Ein längeres QSO beobachten. Wenn der Empfang unerwartet abbricht, CarenDMR nicht sofort neu starten, sondern `logs/tx_rx_timing.log` sichern.
5. Direkt vor einem intern ausgelösten Ende muss jetzt `RX_STOP_ANGEFORDERT` stehen. Bei Stopps über den ConnectionManager steht zusätzlich `RX_STOP_QUELLE`, z. B. `ConnectionManager.disconnect` oder `ConnectionManager.connect Zielwechsel`.
6. CarenDMR normal schließen und prüfen, ob die bisherige Shell-Warnung `QFont::setPointSize: Point size <= 0 (-1)` nicht mehr erscheint.
7. TX, Parrot, normaler RX, TG-Wechsel und TG-Monitor kurz regressiv prüfen.


## Regression 0.2.1.46 – QRZ.com Stationsinformation

1. `config/qrz.example.json` nach `config/qrz.local.json` kopieren.
2. In `config/qrz.local.json` QRZ-Benutzername, QRZ-Passwort und eigenes Rufzeichen eintragen. Die Datei ist lokal und darf nicht committed werden.
3. CarenDMR starten und eine Station mit bekanntem QRZ.com-Profil empfangen.
4. Nach erfolgreichem Hintergrund-Lookup muss im Bereich **Aktuelle Station** der Button **QRZ.com** erscheinen. Bei nicht vorhandenem Rufzeichen darf der Button nicht erscheinen.
5. **QRZ.com** öffnen. Das Fenster muss nicht-modal sein; CarenDMR muss weiter bedienbar bleiben.
6. Falls QRZ.com ein Hauptbild liefert, muss dieses links im Fenster erscheinen. Fehlt das Bild oder ist es nicht erreichbar, muss das Fenster trotzdem funktionieren.
7. Prüfen: Rufzeichen, Name, Ort, Region, Land, Locator und Koordinaten werden aus dem QRZ-Datensatz angezeigt.
8. Die Weltkarte muss Gegenstation und – sofern QRZ für das eigene Rufzeichen Koordinaten liefert – die eigene Station markieren.
9. **Details** wählen: Karte zoomt auf die Umgebung der Gegenstation. **Weltkarte** stellt die Gesamtansicht wieder her.
10. **QRZ.com öffnen** muss die öffentliche QRZ-Seite des Rufzeichens im Browser öffnen.
11. `config/qrz.local.json` darf weder in Git noch in der Release-ZIP enthalten sein.
12. RX/TX, Parrot, TG-Wechsel und TG-Monitor regressiv prüfen.


## Regression 0.2.1.47 – Fenstermanagement

1. CarenDMR auf einem Mehrmonitor-System starten.
2. QRZ.com-Fenster öffnen, auf einen anderen Monitor verschieben, Größe ändern und schließen. Ein anderes QRZ-Rufzeichen öffnen: Das QRZ-Fenster muss wieder an der zuletzt gespeicherten Position erscheinen.
3. Einstellungen, Audio-Benchmark, Audio Coach und Audio-Tuner jeweils verschieben, schließen und erneut öffnen. Position und Größe müssen pro Fenstertyp wiederhergestellt werden.
4. TG-Monitor starten, auf einen gewünschten Monitor verschieben, schließen und erneut starten. Position und Größe müssen erhalten bleiben.
5. Menü **Fenster** öffnen. Es muss das Hauptfenster, alle aktuell sichtbaren Zusatzfenster und – falls aktiv – den TG-Monitor anzeigen.
6. Einen Fenstereintrag wählen. Das gewählte Fenster muss auf seinem bisherigen Monitor nach vorne kommen.
7. **Alle Fenster nach vorne** wählen. Alle offenen CarenDMR-Fenster einschließlich TG-Monitor müssen sichtbar nach vorne kommen, ohne auf einen gemeinsamen Monitor verschoben zu werden.
8. **Alle Zusatzfenster schließen** wählen. Hauptfenster bleibt geöffnet; Zusatzfenster und TG-Monitor werden geschlossen.
9. **Fensterpositionen zurücksetzen** wählen und Zusatzfenster erneut öffnen. Sie müssen wieder an ihren Standardpositionen erscheinen.
10. Optional einen gespeicherten Monitor entfernen/abschalten. Beim nächsten Öffnen darf kein Fenster dauerhaft außerhalb der verbleibenden sichtbaren Bildschirme liegen.
11. RX/TX, Parrot, TG-Wechsel, TG-Monitor-Kanalübergabe und QRZ-Lookup regressiv prüfen.


## Regression 0.2.1.48 – DMR-Kanal und QRZ-Button

1. CarenDMR starten und den Bereich **DMR-Kanal** prüfen. Aktuelle TG, Name und `TSx · Gruppe/Privat` müssen links kompakt sichtbar sein.
2. Die ersten drei Favoriten müssen weiterhin als Schnellwahlbuttons erscheinen.
3. Die Combobox **Alle Favoriten …** öffnen. Sie darf ausschließlich gespeicherte Favoriten enthalten.
4. Einen Favoriten bei getrennter Verbindung auswählen. TG, Timeslot und Rufart müssen vollständig übernommen und die Verbindung aufgebaut werden.
5. Einen anderen Favoriten bei bestehender Verbindung auswählen. Der vorhandene Ablauf Trennen → Kanal vollständig setzen → Wiederverbinden muss unverändert funktionieren.
6. Während TX müssen Schnellwahl und Favoritenauswahl weiterhin abgewiesen werden.
7. Favoritenreihenfolge im Talkgroup-Reiter verändern. Danach müssen sowohl die drei Schnellwahlbuttons als auch die Favoriten-Combobox aktualisiert sein.
8. Eine Station ohne QRZ-Treffer empfangen und anschließend eine Station mit QRZ-Treffer. Beim Erscheinen des QRZ.com-Buttons darf sich der Bereich **Aktuelle Station** weder in Höhe noch Position verschieben.
9. QRZ.com-Button muss kompakter als zuvor erscheinen und das Stationsfenster weiterhin öffnen.
10. RX/TX, Parrot, TG-Wechsel, TG-Monitor und Fenstermanagement regressiv prüfen.


## Regression 0.2.1.49 – QRZ Stationskarte

1. CarenDMR starten und zwischen einer Station ohne QRZ-Treffer und einer Station mit QRZ-Treffer wechseln. Der QRZ-Button darf keinen schwarzen Platzhalter hinterlassen und das Stationslayout darf beim Ein-/Ausblenden nicht springen.
2. QRZ.com-Fenster öffnen. Das Profilbild muss deutlich größer als zuvor erscheinen; Beschriftungen und Werte müssen kompakt nebeneinander stehen.
3. LoTW/eQSL mit QRZ-Wert `0` muss als `Nein`, mit `1` als `Ja` erscheinen.
4. Sind für eigene Station und Gegenstation QRZ-Koordinaten vorhanden, müssen Entfernung in km und Peilrichtung in Grad angezeigt werden.
5. Die Karte muss innerhalb des QRZ-Fensters laden. OSM-Attribution muss sichtbar bleiben.
6. Karte mit Mausrad zoomen und mit gedrückter Maustaste verschieben.
7. **Welt** wählen: eigene Station und Gegenstation müssen gemeinsam sichtbar werden, soweit beide Koordinaten vorhanden sind.
8. **Details** wählen: Karte muss auf die Gegenstation zoomen und deren Popup öffnen.
9. **HAM Grid** aus- und wieder einschalten. Die Maidenhead-Gitterebene muss entsprechend verschwinden/erscheinen.
10. Verbindungslinie zwischen eigener Station und Gegenstation prüfen.
11. **Satellit** bleibt in dieser Version deaktiviert; es darf kein undokumentierter/deprecated Gratis-Endpunkt verwendet werden.
12. RX/TX, QRZ-Lookup, TG-Monitor, Fensterpositionen und Favoriten regressiv prüfen.


## Regression 0.2.1.50 – QRZ Karten-Sizing

1. QRZ.com-Fenster mit einer weit entfernten Gegenstation öffnen.
2. In **Welt** muss die Karte den gesamten verfügbaren Kartenbereich ausfüllen. Es dürfen keine großen schwarzen Flächen und keine Browser-Scrollbalken sichtbar sein.
3. **Details** wählen. Auch die Detailansicht muss den Kartenbereich vollständig füllen.
4. QRZ-Fenster mehrfach größer und kleiner ziehen. Die Karte muss sich jeweils neu an die verfügbare Größe anpassen.
5. Danach erneut **Welt** und **Details** wählen. Marker, Route und HAM Grid müssen korrekt weiterarbeiten.
6. Mausrad-Zoom und Verschieben mit der Maus prüfen.
7. QRZ-Profilbild, Stationsdetails, Entfernung/Richtung und QRZ-Browserbutton regressiv prüfen.
8. RX/TX, TG-Monitor und Fenstermanagement kurz regressiv prüfen.


## Regression 0.2.1.51 – Leaflet Start/Shutdown

1. CarenDMR aus einer Shell mit `python main.py --gui` starten.
2. QRZ.com-Fenster für eine Station mit Koordinaten öffnen.
3. In der Shell darf **kein** `Failed to find a valid digest in the integrity attribute` für `leaflet.css` erscheinen.
4. In der Shell darf **kein** `ReferenceError: syncMapSize is not defined` erscheinen – weder beim Öffnen noch beim Größenändern oder Schließen.
5. **Welt**, **Details** und **HAM Grid** betätigen; Karte muss weiter funktionieren.
6. QRZ-Fenster mehrfach größer/kleiner ziehen und schließen.
7. CarenDMR vollständig beenden. Die beiden genannten JavaScript-Fehler dürfen auch beim Beenden nicht erscheinen.
8. RX/TX, TG-Monitor und Fensterverwaltung kurz regressiv prüfen.


## Regression 0.2.1.52 – Leaflet Bounds-Initialisierung

1. CarenDMR aus einer Shell mit `python main.py --gui` starten.
2. QRZ.com-Fenster einer Station mit Koordinaten öffnen.
3. In der Shell darf beim Öffnen **kein** `Cannot read properties of undefined (reading 'min')` erscheinen.
4. Karte muss direkt vollständig sichtbar sein.
5. **Welt**, **Details** und **HAM Grid** testen.
6. QRZ-Fenster mehrfach vergrößern/verkleinern; dabei dürfen keine JavaScript-Bounds-Fehler erscheinen.
7. QRZ-Fenster und CarenDMR schließen; auch dabei dürfen keine `js:`-Fehler erscheinen.
8. Profilbild, QRZ-Details, Entfernung/Richtung und Browserbutton regressiv prüfen.


## Regression 0.2.1.53 – QRZ Flaggen-Pins

1. QRZ-Fenster einer Station mit bekannten Koordinaten öffnen.
2. Eigener Standort und Gegenstation müssen als zwei deutlich erkennbare Flaggen-Pins erscheinen und jeweils permanent mit dem Rufzeichen beschriftet sein.
3. **Welt** wählen: beide Flaggen-Pins und die Verbindungslinie müssen gemeinsam sichtbar sein.
4. **Details** wählen: Karte zoomt auf die Gegenstation; deren Flaggen-Pin bleibt sichtbar und das Popup öffnet sich.
5. Jeweils auf beide Pins klicken. Popup muss Rolle, Rufzeichen, Name, Locator/Land und Koordinaten zeigen, soweit die QRZ-Daten vorhanden sind.
6. HAM Grid ein-/ausschalten sowie Mausrad-Zoom und Verschieben prüfen.
7. Shell auf JavaScript-Fehler kontrollieren.


## Regression 0.2.1.54 – Satellit und HAM Grid

1. In `config/qrz.local.json` optional `maptiler_api_key` mit einem gültigen MapTiler-Key ergänzen.
2. QRZ-Fenster öffnen. Mit gültigem Key muss **Satellit** aktiv sein; ohne Key bleibt der Button deaktiviert und der Tooltip weist auf `config/qrz.local.json` hin.
3. **Satellit** drücken. Die Basiskarte muss auf MapTiler Satellite wechseln; Buttontext wird **Karte**.
4. **Karte** drücken. OpenStreetMap muss wieder sichtbar sein.
5. Flaggen-Pins, Rufzeichen, Verbindungslinie und Entfernung/Richtung müssen auf beiden Basiskarten erhalten bleiben.
6. **HAM Grid** in Weltansicht ein-/ausschalten. Die gelben Maidenhead-Felder und Feldnamen müssen deutlich sichtbar verschwinden bzw. erscheinen.
7. Weiter hineinzoomen. Bei höherem Zoom müssen feinere 4-stellige Squares erscheinen; ab Zoom 7 auch deren Bezeichnungen.
8. HAM Grid auch über der Satellitenansicht ein-/ausschalten.
9. **Welt**, **Details**, Mausrad-Zoom und Verschieben auf beiden Basiskarten prüfen.
10. Shell auf JavaScript-Fehler kontrollieren.
11. `qrz.local.json` darf weiterhin weder in Git noch in der Release-ZIP enthalten sein.


## Regression 0.2.1.55 – Satellitenumschaltung

1. Gültigen `maptiler_api_key` in `config/qrz.local.json` eintragen und CarenDMR neu starten.
2. QRZ-Fenster öffnen. Links oben in der Karte muss zunächst **Karte** stehen.
3. **Satellit** drücken. Die Basiskarte muss sichtbar auf Luft-/Satellitenbild wechseln und die Kartenquellenanzeige muss **Satellit** zeigen.
4. Der Button heißt danach **Karte**. Erneut drücken: OSM erscheint wieder und Quellenanzeige zeigt **Karte**.
5. HAM Grid, beide Flaggen-Pins und Verbindungslinie müssen auf beiden Basiskarten sichtbar bleiben.
6. Falls Satellit nicht geladen wird, Shell prüfen: `CarenDMR MapTiler satellite tile failed <URL>` zeigt eine fehlgeschlagene Tile-Anforderung. Bei 403 den MapTiler-Key bzw. dessen Restrictions prüfen.
7. Welt/Details, Mausrad-Zoom und Fenstergrößenänderung regressiv prüfen.
