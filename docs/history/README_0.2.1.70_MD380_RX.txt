CarenDMR 0.2.1.70 – produktiver MD380-RX

Änderungen:
- produktiver BrandMeister-RX dekodiert DMR-AMBE+2 jetzt mit
  MD380 md380_decode_fec statt mbelib
- Live-Audiolabor B verwendet exakt denselben produktiven MD380-RX-Decoder
- RX 100 % = Faktor 1.0
- feste +12.04-dB/x4-RX-Kompensation entfernt
- zulässige PCM16-Samples werden bei RX 100 %, AGC aus unverändert ausgegeben
- Clipping-Schutz greift nur bei echtem Überlauf

A bleibt im Audiolabor als mbelib-Vergleich erhalten.

Test:
  python -m pytest .\tests\test_md380_productive_rx_02170.py -q

Danach:
  python main.py --gui
