CarenDMR Audio-Gesamtregression 0.2.1.72

Standardstart:
  python .\tools\audio_path_regression.py

Ohne weitere Parameter werden automatisch vier komplette 10er-Läufe ausgeführt:
  Neutral -> Klar -> DX -> Warm

Damit entstehen 40 Sendefälle. Zwischen den Sendefällen gilt weiterhin die
konfigurierte Pause (Standard 3 s).

Gesamtauswertung:
  logs\audio_path_regression\<Zeitstempel>_all\profile_comparison.txt
  logs\audio_path_regression\<Zeitstempel>_all\profile_comparison.json
  logs\audio_path_regression\<Zeitstempel>_all\results_all_profiles.json

Einzelprofil bleibt möglich:
  python .\tools\audio_path_regression.py --profile Neutral

Aktuelle GUI-/Konfigurationseinstellung:
  python .\tools\audio_path_regression.py --profile current

Die 0.2.1.71-Korrektur der TX-Pegelinstrumentierung ist enthalten.
