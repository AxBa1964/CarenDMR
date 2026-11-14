CarenDMR Audio-Pfad-Regression 0.2.1.70

Ziel:
Die vorhandenen 1_AB.mp3 bis 10_AB.mp3 ersetzen ausschließlich das reale Mikrofon.
Ab dort läuft der produktive CarenDMR-TX-Audiopfad:
Mic-Gain -> StreamingTxSpeechProcessor -> TX-Audio-Tuner/Profil ->
16kHz->8kHz-Sprachband-Filter -> MD380/AMBE -> DMR -> BrandMeister/Parrot.

Auf RX wird ebenfalls der produktive BufferedPcmOutput-Pfad verwendet:
AMBE-Decode -> RX-AGC -> Basisgain -> RX-Lautstärke -> PCM16-Limiter.
Nur das physische Öffnen der Soundkarte wird im Regressionstest ersetzt.

Gemessen werden Peak/RMS dBFS an:
- Referenz-MP3
- Mikrofon roh (virtuell)
- nach Mic-Gain
- nach TX-Sprachaufbereitung/Audioprofil
- direkt vor AMBE
- direkt nach AMBE auf RX
- direkt vor der Soundkarte
Zusätzlich: Echo-Vollständigkeit, Decodefehler und alle bisherigen DMR-Timinglogs.

Start aktuelles Profil:
  python .\tools\audio_path_regression.py

Profil gezielt vergleichen:
  python .\tools\audio_path_regression.py --profile Neutral
  python .\tools\audio_path_regression.py --profile Klar
  python .\tools\audio_path_regression.py --profile DX
  python .\tools\audio_path_regression.py --profile Warm

Ergebnisse:
  logs\audio_path_regression\<Zeitstempel>_<Profil>\results.json
  logs\audio_path_regression\<Zeitstempel>_<Profil>\summary.txt
