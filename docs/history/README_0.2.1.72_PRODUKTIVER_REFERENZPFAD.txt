CarenDMR 0.2.1.72 – DroidStar-Referenzpfad produktiv

Auf Basis des A/B-Hörtests wird B jetzt der normale TX-Pfad.

Produktiver TX:
  Mikrofon roh
  -> 16 kHz mono
  -> ausschließlich neutrales Anti-Alias-Resampling auf 8 kHz
  -> KEIN digitaler CarenDMR-Mic-Gain
  -> KEINE Sprachaufbereitung
  -> KEIN Audio-Tuner/EQ/Kompressor/Limiter
  -> MD380 encode_fec mit 0 dB Eingangsgain
  -> DMR

Produktiver RX bleibt:
  MD380 decode_fec
  -> RX 100 % = Faktor 1.0
  -> Soundkarte

Das Live-Audiolabor behält den alten CarenDMR-Pfad als A und den neuen
produktiven Referenzpfad als B für weitere Vergleiche.

Hinweis:
Die bisherigen TX-Profil-/Mic-Gain-Einstellungen bleiben vorerst gespeichert,
werden im neuen Referenz-TX aber bewusst nicht angewendet. So bleibt die
A/B-Entscheidung unverfälscht; gezielte Klangoptionen können später einzeln
gegen diese saubere Baseline wieder zugeschaltet werden.

Test:
  python -m pytest .\tests\test_productive_droidstar_reference_02172.py -q

Danach:
  python main.py --gui
