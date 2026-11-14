CarenDMR 0.2.1.69 – MD380-Decoder-A/B-Test

A = produktiver MD380 encode_fec -> bisheriger mbelib RX-Decoder
B = derselbe produktive MD380 encode_fec -> MD380 decode_fec wie DroidStar

Beide Decoder erhalten byte-identische 9-Byte-AMBE-Frames. Danach laufen A und
B jeweils durch denselben produktiven RX-Ausgabepfad.

Im Live-Audiolabor:
  A hören – mbelib
  B hören – MD380
  Original anhören

Dateien:
  05A_md380_encode_mbelib_decode_8k.wav
  05B_md380_encode_md380_decode_8k.wav
  06A_mbelib_rx_<rate>hz.wav
  06B_md380_rx_<rate>hz.wav

Test:
  python -m pytest .\tests\test_md380_decoder_ab_02169.py -q
