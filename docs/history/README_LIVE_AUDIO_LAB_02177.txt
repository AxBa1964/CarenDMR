CarenDMR Live-Audiolabor 0.2.1.77 – RX-Zeitachsenfix

Ursache des verlangsamten 06-Mitschnitts:
BufferedPcmOutput bekommt 8-kHz-PCM vom Decoder, resampelt es aber in write()
auf die native Ausgaberate des Soundgeräts (bei Jabra typischerweise 48 kHz).
Der processed_tap arbeitet daher ebenfalls mit dieser nativen Rate.

Der bisherige Laborcode speicherte diese 48-kHz-Samples fälschlich mit einem
8-kHz-WAV-Header. Folge: ungefähr 6-fache Laufzeit und stark verlangsamte
Sprache.

Korrektur:
- native Ausgaberate aus dem produktiven BufferedPcmOutput übernehmen
- 06-WAV mit genau dieser Rate speichern
- RX-Metrik als rx_before_soundcard_native kennzeichnen
- tatsächliche Codec- und RX-Ausgabedauer im Ergebnis-JSON speichern
- bestehende Historie bleibt im Widget rückwärtskompatibel lesbar

Der produktive Audio-/DMR-Signalweg wurde nicht verändert.

Prüfung:
  python -m pytest .\tests\test_live_audio_lab_02177.py -q

Danach:
  python main.py --gui
