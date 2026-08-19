CarenDMR 0.2.1.71 – CarenDMR vs DroidStar-Referenzpfad

A:
  aktueller CarenDMR-Mikrofon/TX-Pfad
  -> bisheriges 8-kHz-Signal vor AMBE
  -> +2 dB MD380-Eingang
  -> md380_encode_fec
  -> md380_decode_fec
  -> produktiver RX-Pfad

B:
  Mikrofon roh 16 kHz
  -> ausschließlich neutrales Resampling 16 -> 8 kHz
  -> KEIN Mic-Gain aus CarenDMR
  -> KEIN Sprachprozessor
  -> KEIN Audio-Profil/EQ
  -> 0 dB MD380-Eingang
  -> md380_encode_fec
  -> md380_decode_fec
  -> derselbe produktive RX-Pfad

Ziel:
Feststellen, ob die Qualitätsdifferenz zu DroidStar vor dem MD380-Vocoder
durch CarenDMR-Vorverarbeitung/+2-dB-Ansteuerung entsteht.

Zusätzlich:
Alter GUI-Fehler self.replay_button beim Schließen/Selektieren beseitigt.

Test:
  python -m pytest .\tests\test_droidstar_reference_ab_02171.py -q
