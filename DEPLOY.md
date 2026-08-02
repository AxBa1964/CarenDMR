# Deployment CarenDMR 0.0.19.4.2

Dieses Dokument ist die verbindliche chronologische Anleitung für Version 0.0.19.4.2. Lokale Zugangsdaten, Datenbanken und externe Vocoder-Plugins dürfen nicht committed oder in das Release-ZIP aufgenommen werden.

## 1. Projektstand prüfen

```powershell
cd C:\Users\abaru\OneDrive\AB_Entwicklung\CarenDMR
git status
git branch --show-current
git pull --ff-only
```

## 2. Dateien unter Windows entsperren

```powershell
Get-ChildItem -Recurse -File | Unblock-File
```

## 3. Virtuelle Umgebung aktivieren

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## 4. Nativen Empfangsdecoder bauen

```powershell
.\native\build_windows.ps1
```

## 5. Native Bridge für DroidStar-kompatible Plugins bauen

```powershell
.\native\build_vocoder_bridge_windows.ps1
```

Die Bridge enthält keinen Codec. Das externe Vocoder-Plugin wird nicht mit CarenDMR ausgeliefert und muss vom Benutzer separat und rechtmäßig bereitgestellt werden.

## 6. Vollständige Tests ausführen

```powershell
python -m unittest discover -s tests -v
```

Erwartet werden 173 erfolgreiche Tests und `OK`.

## 7. Release-Konsistenz prüfen

```powershell
python tools\release_check.py
```

## 8. Anwendung starten

```powershell
python main.py --gui
```

## 9. Empfang und Audio praktisch prüfen

- Mit „Verbinden und empfangen“ verbinden.
- TG91-Empfang, aktuelle Station und QSO-Historie prüfen.
- Im Reiter „Senden – lokaler Audiotest“ Mikrofonaufnahme, Wiedergabe, AGC und Mute prüfen.

## 10. Optionales DroidStar-Plugin offline prüfen

1. Im Reiter „Senden – lokaler Audiotest“ den Bereich „Optionaler AMBE-Encoder“ öffnen.
2. „Plugin auswählen und prüfen“ wählen.
3. Eine separat bereitgestellte, zur Plattform passende DroidStar-Vocoder-Plugin-Datei auswählen.
4. Erfolgsmeldung „AMBE-Encoder bereit: 9 Byte erzeugt“ prüfen.

Die Plugin-Prüfung codiert zunächst nur einen lokalen stummen PCM-Rahmen und sendet nichts. Der anschließende Parrot-Test ist hart auf DMR-ID 9990, Privatruf und Timeslot 2 verriegelt.

## 11. Release-ZIP erzeugen

```powershell
python tools\create_release_zip.py
```

Das ZIP darf insbesondere nicht enthalten:

- `.git`, `.venv` oder Cache-Verzeichnisse,
- `config\*.local.json`,
- externe Vocoder-Plugin-Dateien,
- `data\contacts.db` oder `data\qso_history.db`,
- Audioaufnahmen, Logs oder Paketmitschnitte,
- `*.dll`, `*.so` oder `*.dylib`.

## 12. Git prüfen, committen und pushen

```powershell
git status
git diff --check
git diff
git add -A
git status
git diff --cached --check
git diff --cached
git commit -m "CarenDMR 0.0.19.4.2 Hold-to-Talk und GUI-Bereinigung"
git push origin master
```


## Privaten Parrot-Sprachtest prüfen

1. `python main.py --gui` starten.
2. Im Reiter **Senden** das konfigurierte Plugin erneut prüfen.
3. **5-Sekunden-Privattest an Parrot 9990 starten** wählen.
4. Bestätigen, fünf Sekunden sprechen und das Echo abwarten.
5. Prüfen, dass Ziel 9990, Ruftyp Privatruf und Timeslot 2 unveränderbar angezeigt werden.

## 8. Praktische Funktionsprüfung

```powershell
python main.py --gui
```

- Plugin erneut prüfen.
- TX-Taste drücken und zwei bis fünf Sekunden sprechen.
- TX-Taste loslassen: Die Aufnahme muss sofort enden und gesendet werden.
- Prüfen, dass das Parrot-Echo wiedergegeben und die Sendehistorie ergänzt wird.
- Prüfen, dass beim Loslassen sofort beendet und gesendet wird; das eingestellte TX-Sicherheitslimit greift nur als Notbremse.

---

# Verbindliche Release-Abnahme

Ein Release gilt erst nach vollständiger praktischer Prüfung als freigegeben. Die Liste wird bei neuen Kernfunktionen fortgeschrieben und nicht verkürzt.

## A. Programmstart und Version

- [ ] `python main.py --gui` startet ohne Fehlermeldung.
- [ ] Fenstertitel und `carendmr/version.py` zeigen `0.0.19.4.2`.
- [ ] Keine Exception erscheint im Terminal oder Ereignisprotokoll.
- [ ] Lokale Konfiguration und Audioeinstellungen werden geladen.

## B. BrandMeister-Verbindung

- [ ] Anmeldung bei BrandMeister erfolgreich.
- [ ] Status zeigt tatsächlich `Verbunden` und `Empfang aktiv`.
- [ ] Trennen und erneutes Verbinden funktioniert.
- [ ] Verbindung bleibt mindestens fünf Minuten stabil.

## C. Normaler Empfang – Pflicht vor jedem Release

- [ ] Tatsächlichen Verkehr im BrandMeister-Dashboard oder mit einem zweiten Empfänger gegenprüfen.
- [ ] TG91-Verkehr auf Timeslot 1 wird verarbeitet.
- [ ] TG91-Verkehr auf Timeslot 2 wird verarbeitet.
- [ ] Sprache ist hörbar.
- [ ] Empfangsstatistik zählt Datagramme und Sprachbursts hoch.
- [ ] Aktuelle Station wird mit DMR-ID und – soweit vorhanden – Kontaktdaten angezeigt.
- [ ] QSO-Historie erhält nach Sprechende einen Eintrag.
- [ ] Lautstärkeregler funktioniert.
- [ ] Mute funktioniert, ohne Netzwerkempfang und Historie anzuhalten.
- [ ] AGC lässt sich ein- und ausschalten.

## D. Encoder und Parrot-Senden

- [ ] Externes DroidStar-Plugin wird geladen.
- [ ] Offline-PCM-zu-AMBE-Test erzeugt 9 Byte.
- [ ] TX gedrückt halten startet die Aufnahme.
- [ ] Loslassen beendet die Aufnahme sofort.
- [ ] Das eingestellte TX-Sicherheitslimit greift nur als Notbremse.
- [ ] Ziel bleibt fest `9990`, Ruftyp `Privatruf`, Timeslot `2`.
- [ ] Parrot-Echo wird empfangen und wiedergegeben.
- [ ] Sendehistorie erhält einen korrekten Eintrag.

## E. Rückkehr zum Empfang – Pflicht nach jedem Parrot-Test

- [ ] War TG91 vor TX aktiv, startet der Empfang nach dem Parrot-Test automatisch neu.
- [ ] TG91-Verkehr ist danach wieder hörbar, ohne manuelles Trennen und Verbinden.
- [ ] Die Empfangsstatistik zählt nach dem Parrot-Test weiter.
- [ ] Auch bei fehlendem Echo oder Parrot-Fehler startet der vorher aktive Empfang wieder.
- [ ] War der Empfang vor TX nicht aktiv, wird er danach nicht ungefragt gestartet.

## F. Daten und Bedienung

- [ ] RadioID-Kontaktdatenbank bleibt vorhanden und nutzbar.
- [ ] QSO-Historie bleibt nach Neustart erhalten.
- [ ] Sendehistorie bleibt nach Neustart erhalten.
- [ ] Alle sichtbaren Schaltflächen haben eine aktuelle Funktion; keine alten Testschaltflächen sind vorhanden.
- [ ] Tastaturbedienung und Fokusreihenfolge funktionieren.

## G. Automatische Prüfung

```powershell
python -m unittest discover -s tests -v
python tools\release_check.py
```

- [ ] Alle Tests erfolgreich.
- [ ] Release-Check erfolgreich.
- [ ] Versionsnummern in README, CHANGELOG, DEPLOY und RELEASE_INFO konsistent.

## H. Release-ZIP

- [ ] ZIP aus dem aktuellen sauberen Projektstand erzeugt.
- [ ] ZIP in ein leeres Verzeichnis entpackt.
- [ ] Tests im frisch entpackten ZIP erfolgreich.
- [ ] Keine `.venv`, Zugangsdaten, lokalen JSON-Dateien, Datenbanken, Plugins, DLLs, SO-/Dylib-Dateien oder Caches enthalten.
- [ ] Anwendung aus dem frisch entpackten Stand gestartet und die Punkte A bis E praktisch geprüft.

**Projektregel:** Eine neue Funktion beginnt erst, wenn alle bestehenden Kernfunktionen diesen Regressionstest bestanden haben.
