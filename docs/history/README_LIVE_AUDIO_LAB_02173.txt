CarenDMR Live-Audiolabor 0.2.1.73 – Overlay

Ziel
----
Lokaler Qualitäts-/Tuningtest ohne BrandMeister und ohne 9990-Parrot.

Die Strecke ist ab Mikrofon dieselbe produktive CarenDMR-Audiostrecke:
  ausgewähltes Mikrofon
  -> AudioSendService.start_live_capture (derselbe Live-Pfad wie PTT)
  -> Mic-Gain
  -> StreamingTxSpeechProcessor
  -> StreamingTxAudioTuner / aktuelles Profil
  -> SpeechBand-Decimator 16 kHz -> 8 kHz
  -> EncoderService.create_transmit_encoder (MD380-Dynarmic, wenn vorhanden)
  -> 240 ms TX-Lead-In wie im echten Live-TX
  -> NativeMbeReceiveVocoder (derselbe RX-Decoder)
  -> AudioSendService.create_pcm_output
  -> RX-AGC / RX-Lautstärke / RX-Basisgain / Limiter
  -> ausgewählte Soundausgabe

Nicht simuliert wird nur der DMR-Netztransport. DMR-Framing und BrandMeister
verändern die AMBE-Codewörter nicht und gehören daher nicht in die lokale
Audio-Qualitätsmessung.

Bedienung
---------
Programm -> Live-Audiolabor …

1. "Aufnahme starten"
2. sprechen
3. "Aufnahme beenden und anhören"
4. Ergebnis wird lokal AMBE-codiert/decodiert und einmal abgespielt.
5. "Ergebnis nochmal anhören" beliebig oft.
6. "Mikrofon-Original anhören" für direkten A/B-Vergleich.

Das Fenster zeigt den aktuellen und die letzten drei Durchgänge mit:
- Mikrofon / Mic-Gain / Profil
- TX vor AMBE
- Pegel nach Codec
- RX vor Soundkarte
- Codec-Pegeländerung
- Signalähnlichkeit
- Clipping

Zusätzliche Analysewerte in local_audio_lab_result.json:
- RMS/Peak/Crest
- geschätzter Noise Floor
- Spektralzentrum
- Presence-/Low-Band-Anteile
- Residual-SNR nach pegelunabhängiger Signalausrichtung
- korrigierte Decoderbits / Decodefehler

Jeder Lauf bleibt unter logs/audio_lab/... gespeichert; Verlauf zusätzlich:
logs/audio_lab_local/history.json

Installation
------------
ZIP direkt über den CarenDMR-Projektordner entpacken und Dateien ersetzen.

Test:
  python -m pytest .\tests\test_live_audio_lab_02173.py -q

Danach:
  python main.py --gui
