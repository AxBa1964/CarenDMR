# CarenDMR 0.1.2.1 – Design-System-Fix

## 1. Installation

ZIP vollständig über den Projektordner entpacken. Lokale Konfigurationen, Plugins und Datenbanken nicht löschen.

```powershell
cd C:\Users\abaru\OneDrive\AB_Entwicklung\CarenDMR
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python main.py --gui
```

## 2. Prüfung

1. Einstellungen über `Strg+,` öffnen; in der Konsole darf kein Traceback erscheinen.
2. Mit Tab auf Haupt- und Einstellungsreiter gehen. Der gelbe Rahmen liegt nur um den vollständigen Reiter, nicht zusätzlich um den Text.
3. Betrieb prüfen: Statusanzeige ist klar nicht klickbar, Verbinden/Trennen klar als Button erkennbar. Beide Elemente sind rechts bündig und gleich breit.
4. F5, F6, F7, Space, Empfang und Parrot unverändert prüfen.
