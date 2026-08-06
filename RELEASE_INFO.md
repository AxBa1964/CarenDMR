# CarenDMR 0.2.0 – Eigene Modulation vergleichen

Dieser Release verbindet die TG-Referenzdatenbank mit dem geführten Parrot-Audiotest.

## Messprinzip

Die eigene Modulation wird aus `04_codec_loopback_8k.wav` analysiert. Damit wird das eigene Signal nach AMBE-Encoding und lokalem AMBE-Decoding mit empfangenen Benchmark-Stationen nach deren AMBE-Decoding verglichen. Ein direkter Vergleich von Rohmikrofon und DMR-Empfang wird vermieden.

## Bedienung

Im Reiter **Audio-Benchmark** startet **Eigene Modulation testen** den bestehenden passiven Audio-Assistenten und bereitet TG 9990, TS2 und Privatruf vor. Nach dem vollständigen Parrot-Test erscheint der Vergleich automatisch.

## Sicherheit

Empfehlungen werden nur angezeigt. Mic-Gain, Tuner und PTT-Vorlauf werden in dieser Version nicht automatisch verändert.
