# CarenDMR 0.1.7.3.5 – Statuslayout und Enter-Regression

## 1. Update installieren und starten

```powershell
cd C:\Users\abaru\OneDrive\AB_Entwicklung\CarenDMR
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python main.py --gui
```

## 2. Automatische Prüfung

```powershell
python -m pytest -q
python tools\release_check.py
```

## 3. Praxistest

1. Im Talkgroup-Feld `262` eingeben. Die Trefferliste muss erscheinen.
2. Ohne Pfeiltaste direkt Enter drücken. Der markierte erste Treffer muss übernommen werden.
3. Erneut `262` eingeben, mit Pfeil runter einen anderen Treffer markieren und Enter drücken. Genau dieser Treffer muss übernommen werden.
4. Prüfen: TG beziehungsweise DMR-ID, Timeslot und Rufart werden gemeinsam übernommen; es entsteht noch keine Verbindung.
5. Escape schließt die Liste und lässt Suchtext sowie Fokus im Talkgroup-Feld.
6. Pfeil runter öffnet die geschlossene Liste wieder; Enter übernimmt anschließend den markierten Treffer.
7. Buttons und Pflicht-Hotkeys prüfen: F5, F6, F7 und Space funktionieren unverändert.
8. Rückfallprüfung: RX/TX, Pegelanzeigen, QSO-Historie und Einstellungen funktionieren unverändert.

## 4. Git-Sicherung

```powershell
git status
git add .
git commit -m "Release 0.1.7.3.5 - Statuslayout und Enter-Regression"
git tag -a v0.1.7.3.5 -m "CarenDMR 0.1.7.3.5"
git push origin feature/0.0.22-ui-redesign
git push origin v0.1.7.3.5
git status
```

---

# CarenDMR 0.1.7.2 – DMR-Kanal V1

## 1. Update installieren und starten

```powershell
cd C:\Users\abaru\OneDrive\AB_Entwicklung\CarenDMR
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python main.py --gui
```

## 2. Automatische Prüfung

```powershell
python -m pytest -q
python tools\release_check.py
```

## 3. Praxistest

1. Auf der Betriebsseite muss der linke obere Bereich `DMR-KANAL` heißen.
2. Das Eingabefeld muss mit `Talkgroup` beschriftet sein und den Platzhalter `Talkgroup eingeben` zeigen.
3. Programmstart: Fokus liegt weiterhin direkt im Talkgroup-Feld.
4. Eine TG manuell eingeben und mit F5 verbinden.
5. F6 und F7 müssen Timeslot und Rufart unverändert umschalten.
6. Nach dem Verbinden muss der Fokus weiterhin auf TX wechseln; nach dem Trennen zurück auf Talkgroup.
7. Parrot mit TG 9990 sowie RX/TX, Pegelanzeigen und QSO-Historie prüfen.
8. In diesem Baustein gibt es bewusst noch keine Suchliste und keine Favoritenverwaltung.

## 4. Git-Sicherung

```powershell
git status
git add .
git commit -m "Release 0.1.7.2 - DMR-Kanal V1"
git tag -a v0.1.7.2 -m "CarenDMR 0.1.7.2"
git push origin feature/0.0.22-ui-redesign
git push origin v0.1.7.2
git status
```

---

# CarenDMR 0.1.7.1 – Betriebsanzeigen V1

## 1. Installation und Start

```powershell
cd C:\Users\abaru\OneDrive\AB_Entwicklung\CarenDMR
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python main.py --gui
```

## 2. Automatische Prüfung

```powershell
python -m pytest -q
python tools\release_check.py
```

## 3. Praxistest

1. Start: oben rechts muss eine graue Anzeige `GETRENNT` mit LED erscheinen; sie darf nicht per Tab erreichbar sein.
2. F5: während Aufbau `VERBINDET`, danach grün `EMPFANG`.
3. Empfang/Parrot: RX-Pegel muss sichtbar reagieren und danach weich auf null fallen.
4. Space: nach Vorlauf und Startton muss die Anzeige rot `SENDEN` zeigen; Sprechen muss das MIC-Meter bewegen.
5. Space erneut: TX sofort beenden, MIC-Meter auf null, nach Rückkehr grün `EMPFANG`.
6. Trennen: Anzeige wieder grau `GETRENNT`, beide Meter null.
7. Einstellungen → Codec / Decoder: Encoder/Decoder, Plugin und Prüfergebnis müssen weiterhin vorhanden sein.
8. Rückfallprüfung: F5, F6, F7, Space, Stumm, AGC, QSO-Historie und Fokusfolge unverändert.

## 4. Git-Sicherung

```powershell
git status
git add .
git commit -m "Release 0.1.7.1 - Betriebsanzeigen V1"
git tag -a v0.1.7.1 -m "CarenDMR 0.1.7.1"
git push origin feature/0.0.22-ui-redesign
git push origin v0.1.7.1
git status
```

---

# CarenDMR 0.1.6.8 – TS/RA Keyboard Workflow Final

- Timeslot und Rufart bleiben sichtbar und per Maus bedienbar.
- Beide Statusgruppen sind aus der Tab-Reihenfolge entfernt.
- Tastaturbedienung erfolgt ausschließlich über die konfigurierten Hotkeys.
- Hotkey-Hinweise werden dynamisch aus dem Eingabemanager angezeigt.
- F6/F7 beziehungsweise die individuell belegten Tasten erzeugen genau eine kurze Fachansage.
- Verbinden, PTT, Timeslot und Rufart sind Pflicht-Hotkeys und können nicht gelöscht werden.

## Test

```powershell
python main.py --gui
```

Die Anwendung muss ohne `AttributeError: audio_service` starten. Danach Verbindung, TX-Startton und TX-Endtöne prüfen.

---

# CarenDMR 0.1.6.6 – Field-Test Audio & Accessibility Final

## Gezielter Praxistest

1. `python main.py --gui` starten. Der Fokus muss direkt in „Neue Talkgroup“ stehen.
2. Mit Tab Timeslot und Rufart prüfen. Erwartet werden kurze Namen wie „Timeslot 2, Schaltfläche“ und „Privatruf, Schaltfläche“.
3. F6 und F7 prüfen. Es darf keine doppelte zusätzliche Ansage folgen.
4. Unter **Einstellungen → Diagnose** die PTT-Vorlaufzeit einstellen und übernehmen.
5. Verbinden und Space drücken. Erst Vorlauf, dann ein heller Beep, danach tatsächlicher TX. Erst nach dem Beep sprechen.
6. Space zum Beenden drücken. TX muss sofort enden; danach müssen zwei kurze Beeps folgen.
7. Parrot-Antwort prüfen. Start-Beep und End-Beeps dürfen nicht im gesendeten Sprachsignal enthalten sein.


## 1. Installation

ZIP vollständig über den Projektordner entpacken. Lokale Konfigurationen, Plugins und Datenbanken nicht löschen.

```powershell
cd C:\Users\abaru\OneDrive\AB_Entwicklung\CarenDMR
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python main.py --gui
```

## 2. Segment-Schalter und Tab-Reihenfolge

1. Programm starten und auf Betrieb bleiben.
2. Neue Talkgroup eingeben oder das Feld leer lassen.
3. Mit Tab weitergehen. Reihenfolge muss sein:
   - Neue Talkgroup
   - aktuell gewählter Timeslot
   - aktuell gewählte Rufart
   - Verbinden
4. F6 muss zwischen TS1 und TS2 wechseln.
5. F7 muss zwischen Gruppe und Privat wechseln.
6. Screenreader prüfen: Es soll `Timeslot 1/2 … Schaltfläche` beziehungsweise `Gruppenruf/Privatruf … Schaltfläche` gesprochen werden, nicht `Kontrollkästchen`.

## 3. TX/RX, Vorlauf und Signalton

1. TG 9990, TS2, Privat verbinden.
2. TX/RX-Schaltfläche muss unterhalb von Stumm/AGC an derselben Position bleiben.
3. Gewünschten PTT-Vorlauf unter `Einstellungen → Diagnose → Accessibility-Test` einstellen und übernehmen.
4. TX drücken:
   - Screenreader kann die kurze Schaltflächenmeldung beenden.
   - Nach dem eingestellten Vorlauf ertönt lokal ein kurzer Piepton.
   - Erst danach beginnt die tatsächliche Sendung.
5. Während echter TX-Zeit erscheint unter dem Button `0`, danach `1`, `2`, `3` …
6. Die Zahl darf nicht vorgelesen werden.
7. RX drücken beziehungsweise Space erneut betätigen:
   - Sendung endet.
   - Zahl verschwindet.
   - Button bleibt an derselben Position.
8. Nächste Sendung muss wieder bei `0` beginnen.
9. Parrot-Antwort vollständig prüfen; der Startton darf nicht mitgesendet werden.

## 4. Rückfallprüfung

- F5 verbindet und trennt.
- F6/F7 ändern den Funkparameter vor der Verbindung.
- QSO-Historie und Einstellungen öffnen.
- Audio, Stumm, AGC und Parrot funktionieren.
- Programm während RX sauber schließen.
