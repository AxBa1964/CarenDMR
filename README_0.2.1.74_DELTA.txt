CarenDMR 0.2.1.74 – Delta auf 0.2.1.73

TX-Pegel:
- Der bisherige Mic-Gain-Regler ist jetzt wirklich produktiv wirksam.
- 100 % = Faktor 1.0 = unveränderte 9/10-Referenzstrecke.
- Werte unter 100 % schwächen das TX-Mikrofonsignal vor dem neutralen
  16->8-kHz-Resampling ab.
- Keine Verstärkung über 100 %.

Desktop --gui:
- Beschriftung Mic-Gain -> TX-Pegel.
- Regler 0..100 % wirkt direkt auf den produktiven B-TX-Pfad.

Easy --easy:
- Anzeige: RX xx % · TX yy %
- Strg+Plus / Strg+Minus: RX-Lautstärke in 10-%-Schritten, 0..200 %
- Alt+Plus / Alt+Minus: TX-Pegel in 10-%-Schritten, 0..100 %
- Jede Änderung wird gespeichert und per Screenreader angesagt.
- F4 nennt zusätzlich RX- und TX-Pegel.

Gezielter Test:
  python -m pytest .\tests\test_tx_level_easy_02174.py -q
