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
