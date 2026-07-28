# DEPLOY – CarenDMR 0.0.4

Diese Anleitung vollständig und in der angegebenen Reihenfolge ausführen.

Projektpfad:

```text
C:\Users\abaru\OneDrive\AB_Entwicklung\CarenDMR
```

## 1. In das Projekt wechseln

```powershell
cd C:\Users\abaru\OneDrive\AB_Entwicklung\CarenDMR
```

## 2. Sauberen Ausgangszustand prüfen

```powershell
git status
```

Vor dem Einspielen muss erscheinen:

```text
nothing to commit, working tree clean
```

Falls dort bereits andere Änderungen stehen, das Update nicht darüberkopieren.

## 3. Update entpacken

`CarenDMR_0.0.4_Update.zip` entpacken und den enthaltenen Ordnerinhalt direkt
über das vorhandene Projekt kopieren.

Dabei vorhandene Dateien ersetzen lassen.

Wichtig: Nicht den Ordner `CarenDMR_0.0.4_Update` als zusätzlichen Unterordner
in das Projekt kopieren. Im Projekt müssen danach beispielsweise diese Pfade
existieren:

```text
CarenDMR\carendmr\core\events.py
CarenDMR\carendmr\accessibility\speech.py
CarenDMR\docs\TECHNICAL_DESIGN.md
```

## 4. Änderungen kontrollieren

```powershell
git status
```

Erwartet werden geänderte Dokumentations- und Versionsdateien sowie neue
Dateien unter:

```text
carendmr\core
carendmr\accessibility
tests
docs
```

Dieser nicht saubere Arbeitsbaum ist jetzt korrekt, weil das Update noch nicht
committed wurde.

## 5. Alle Tests ausführen

```powershell
python -m unittest discover -s tests -v
```

Alle Tests müssen mit `OK` enden. Die genaue Testanzahl kann höher sein als in
diesem Update, weil die Tests der Vorversionen erhalten bleiben.

Bei einem Fehler nicht committen.

## 6. Anwendung starten

```powershell
python main.py
```

Die Anwendung muss weiterhin normal starten und Version `0.0.4` melden.
Danach das Programm regulär beenden.

## 7. Optionaler Core-Selbsttest

```powershell
python -c "from carendmr.core import EventBus, StatusManager, AppStatus; from carendmr.accessibility import SpeechManager, ConsoleSpeechOutput; b=EventBus(); s=SpeechManager(b, ConsoleSpeechOutput()); m=StatusManager(b); s.start(); m.set_status(AppStatus.READY)"
```

Erwartete Ausgabe:

```text
CarenDMR ist bereit.
```

## 8. Release-ZIP erzeugen

```powershell
python tools\create_release_zip.py
```

Erwartet wird:

```text
release\CarenDMR_0.0.4.zip
```

## 9. Änderungen für den Commit vormerken

```powershell
git add .
git status
```

Alle Dateien der Version 0.0.4 müssen jetzt unter `Changes to be committed`
stehen.

Kontrollieren, dass weder Logdateien noch ein fremdes ZIP im Projektstamm
vorgemerkt sind. Das Release-ZIP im ausgeschlossenen Release-Ordner darf nicht
im Commit erscheinen.

## 10. Commit erstellen

```powershell
git commit -m "CarenDMR 0.0.4 Core und technisches Design"
```

## 11. Abschluss prüfen

```powershell
git status
```

Erwartet:

```text
nothing to commit, working tree clean
```

## Ergebnis

Version 0.0.4 ist abgeschlossen. Die nächste Version 0.0.5 darf anschließend
die echte Audio-Geräteerkennung auf Basis von `sounddevice` implementieren.
