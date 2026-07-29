# CarenDMR 0.0.11 – Empfangsseitiger Software-Vocoder

## Ziel und Grenze

Dieser Meilenstein wandelt validierte DMR-AMBE+2-Codewörter in PCM um. Er ist
ausschließlich empfangsseitig. Er enthält keine Audio-Wiedergabe, keinen
Encoder, keine Mikrofonverarbeitung, kein PTT und keinen Netzwerkversand.

## Datenfluss

1. Das vorhandene `DmrdPacket` validiert das 55-Byte-Homebrew-Datagramm.
2. Nur `VOICE_SYNC` und `VOICE` werden als Audio akzeptiert.
3. Die 33-Byte-DMR-Nutzlast wird nach der DroidStar-Anordnung in drei
   9-Byte-AMBE-Codewörter zerlegt; die mittleren Sync-/EMB-Bits werden
   ausgelassen.
4. Ein zustandsbehafteter `ReceiveVocoder` dekodiert jedes Codewort in
   160 Mono-Samples, signed 16 bit, 8 kHz, entsprechend 20 ms.
5. `PcmFrame` transportiert ausschließlich Samples und die vom Decoder
   gemeldete Anzahl korrigierter Bitfehler.

Die drei Codewörter eines DMR-Bursts ergeben zusammen 480 Samples oder 60 ms.
Ein Decoderobjekt gehört genau zu einem laufenden Sprachstrom; seine
Prädiktionsparameter dürfen nicht zwischen Streams vermischt werden.

## Native Grenze

`native/carendmr_mbe.c` stellt nur drei C-Symbole bereit:

- Decoder anlegen,
- ein 9-Byte-Codewort dekodieren,
- Decoder freigeben.

Die Bibliothek wird mit `make -C native check` gebaut. Der Check kompiliert
mit strikten Warnungen und lehnt unerwartete Encoder-Symbole ab. Das erzeugte
`.dylib`/`.so` bleibt ein ignoriertes lokales Build-Artefakt.

Der Python-Adapter lädt die Bibliothek über `ctypes`. Fehlende Bibliothek,
falsche Eingabelänge und Benutzung nach dem Schließen führen zu klaren,
stabilen Ausnahmen ohne Pfad- oder Loaderdetails in der Nutzermeldung.

## Verifikation und Aussagegrenze

Der feste, nicht-personale DroidStar/MMDVM-AMBE-Stummvektor wird dreimal
dekodiert. Geprüft werden:

- exakt drei identische 9-Byte-Codewörter aus einem Voice-Sync-Burst,
- exakt 480 PCM-Samples,
- null gemeldete korrigierte Fehler,
- ein bytegenauer SHA-256-Goldenwert der PCM-Ausgabe,
- Wertebereich signed 16 bit,
- deterministisches Fehlerverhalten und wiederholbares Schließen.

Der Vektor beweist Datenpfad, Zustandsführung und Reproduzierbarkeit. Er
beweist ausdrücklich noch keine Verständlichkeit realer Sprache. Dafür ist
später eine kontrollierte, private Live-Aufnahme ohne Wiedergabe gegen
Referenzsoftware oder USB-Hardware zu vergleichen.

## Nächster getrennt freizugebender Schritt

Der nächste funktionale Schritt ist ein begrenzter Receive-only-Capture, der
AMBE-Codewörter durch diesen Decoder führt und PCM ausschließlich in einem
privaten lokalen Testartefakt sammelt. Audio-Wiedergabe folgt erst nach
bestätigter Sprachverständlichkeit und eigener Accessibility-/Geräteprüfung.
