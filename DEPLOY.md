# CarenDMR 0.0.28.3 – Qt-Einstellungen Bedienkorrekturen

## 1. Installation

ZIP vollständig über den Projektordner entpacken. Lokale Konfigurationen, Plugins und Datenbanken nicht löschen.

```powershell
cd C:\Users\abaru\OneDrive\AB_Entwicklung\CarenDMR
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python main.py --gui
```

## 2. Betrieb prüfen

1. Fenster ohne Vollbild öffnen; alle Bedienelemente müssen erreichbar sein.
2. F5/F6/F7, Empfang und Parrot unverändert prüfen.
3. Mic-Gain und RX-Lautstärke im Betrieb prüfen; RX endet bei 100 %.
4. Stumm und AGC prüfen.

## 3. Datenbanken prüfen

1. Einstellungen > Datenbanken öffnen.
2. Kontaktdaten aktualisieren.
3. Währenddessen muss direkt in der RadioID-Kachel „Kontaktdaten werden aktualisiert …“ stehen.
4. Abschluss oder Fehler muss ebenfalls dort erscheinen.

## 4. Codec prüfen

1. Einstellungen > Codec / Decoder öffnen.
2. Ein vorhandenes `plugins/vocoder_plugin.winnt.x86_64` muss automatisch erkannt werden.
3. Bei manueller Zuordnung muss die Datei auch ohne `.dll` sichtbar sein.
