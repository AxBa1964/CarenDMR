# Upstream-Provenienz und Lizenzgrenze

## Projektlizenz

CarenDMR wird als Gesamtwerk unter der GNU General Public License, Version 3
oder später (`GPL-3.0-or-later`), bereitgestellt. Der kanonische Lizenztext
steht in `LICENSE`.

Bei Weitergabe eines Builds müssen insbesondere der korrespondierende
Quellcode, der Lizenztext, die Urheberhinweise und diese Provenienzinformation
mit angeboten beziehungsweise erhalten werden. Diese Dokumentation ist eine
technische Bestandsaufnahme und keine Rechtsberatung.

## Verifizierte Upstream-Basis

Die Datei `carendmr/brandmeister/silent_call.py` ist eine auf Python
übertragene, auf die benötigte Offline-Fixture reduzierte Adaption aus:

- Projekt: DroidStar
- Upstream: <https://github.com/nostar/DroidStar>
- geprüfter Commit: `5368b41d1b832d356a066fafa9992187a72316e1`
- Abruf und Prüfung: 29. Juli 2026

Berücksichtigte Upstream-Dateien und Funktionen:

- `dmr.cpp` / `dmr.h`: DMR-LC-Aufbau, Burst-Komposition, Embedded-LC und EMB;
  Copyright Doug McLain; GPLv3-or-later.
- `DMRDefines.h`: DMR-Synchronmuster, CRC-Masken, Datentypen und festes
  AMBE-Stummmuster; Copyright Jonathan Naylor; GPLv2-or-later.
- `cbptc19696.cpp` / `.h`: BPTC(196,96); Copyright Ian Wraith und Jonathan
  Naylor; GPLv2-or-later.
- `chamming.cpp` / `.h`: Hamming(15,11,3), Hamming(13,9,3) und
  Hamming(16,11,4); Copyright Jonathan Naylor; GPLv2-or-later.
- `cgolay2087.cpp` / `.h`: Golay(20,8,7) für Slot Type; Copyright Jonathan
  Naylor; GPLv2-or-later.
- `crs129.cpp` / `.h`: Reed-Solomon(12,9); Copyright Jonathan Naylor;
  GPLv2-or-later.
- `CRCenc.cpp` / `.h`: 5-Bit-LC-Prüfsumme; Copyright Jonathan Naylor und Andy
  Uribe; GPLv2-or-later.

Die GPLv2-or-later-Bestandteile dürfen unter GPLv3 weitergegeben werden. Der
GPLv3-or-later-DMR-Ablauf und das Gesamtwerk werden deshalb einheitlich als
GPLv3-or-later lizenziert.

## Bewusst nicht übernommen

Für die Stummruf-Fixture wurden Qt/UI, Audioaufnahme oder -wiedergabe,
AMBE-Geräte- und Software-Vocoder, Netzwerktransport, BrandMeister-Anmeldung,
Modemsteuerung, Timer, PTT/Keying sowie alle anderen Digitalfunkarten nicht
übernommen.

Der übernommene AMBE-Inhalt ist ausschließlich das feste 33-Byte-Stummmuster
aus `DMRDefines.h`. CarenDMR enthält damit keinen allgemeinen AMBE-Encoder.

## Änderungen gegenüber Upstream

- C++ wurde idiomatisch und speichersicher nach Python übertragen.
- Der Funktionsumfang wurde auf TG91, Timeslot 2, Gruppenruf, Color Code 1 und
  genau eine sechs Bursts lange Stumm-Fixture begrenzt.
- Es gibt keine Sendeschnittstelle und keine Netzwerkabhängigkeit.
- Öffentliche Eingaben werden durch das bestehende unveränderliche
  `DmrdPacket`-Modell geprüft.
- Alle acht 33-Byte-Payloads wurden mit Dummy-IDs bytegenau gegen einen
  separat kompilierten C++-Referenzgenerator aus den oben genannten
  Upstream-Komponenten verglichen.

## Empfangsdecoder ab 0.0.11

Für den rein empfangsseitigen AMBE+2-Decoder wurden aus demselben geprüften
DroidStar-Commit zusätzlich isoliert:

- `mbe/ambe3600x2450.c` und zugehörige Konstanten: AMBE 2450/1150
  Fehlerkorrektur, Parameterdekodierung und Frame-Verarbeitung;
- `mbe/ecc.c` und Konstanten: Golay-/Hamming-Fehlerkorrektur;
- `mbe/mbelib.c`, `mbelib.h` und Konstanten: Parameterspeicher und
  Sprachsynthese;
- ausschließlich die vier 36 Einträge langen DMR-Bit-Mapping-Tabellen aus
  `mbe/mbevocoder.cpp`.

Diese Dateien tragen die ISC-Erlaubnis und ihre vorhandenen Hinweise bleiben
im Quellbaum erhalten. Die CarenDMR-C-ABI-Hülle ist GPLv3-or-later. Die
ISC-Lizenz ist mit GPLv3 vereinbar; bei Weitergabe bleiben dennoch beide
Hinweissätze erhalten.

Nicht übernommen wurden die Encode-Methoden von `MBEVocoder`, der
IMBE-Encoder, MD380-Firmware oder -Emulation, Codec2, USB-Vocoder-Code,
Qt-/Audio-Code sowie Netzwerk- und Sendefunktionen.

Die urheberrechtliche Lizenzkompatibilität beantwortet nicht selbstständig
Fragen zu Patenten oder proprietären Codec-Rechten. Vor öffentlicher
Verteilung eines Software-AMBE-Decoders ist deshalb eine gesonderte Prüfung
für die vorgesehenen Länder und Vertriebswege erforderlich. Die lokale
technische Validierung trifft keine rechtliche Freigabeentscheidung.

## MD380-Emulation ab 0.2.1.x (Stand 0.2.1.88)

Der Abschnitt oben beschreibt den Stand von 0.0.11. Seit der 0.2.1-Reihe nutzt
CarenDMR für Senden und Empfangen zusätzlich die MD380-Emulation:

- Upstream: <https://github.com/dbehnke/md380_vocoder_dynarmic>, festgelegter
  Commit `55c9a2c6d502567380c7dfaf4a2e3cc4dd6d1dd5`, gebaut über
  `native/build_md380_dynarmic_windows.ps1` und die CarenDMR-Hülle
  `native/md380_dynarmic_bridge.cpp` (GPLv3-or-later).
- Die Emulation führt den AMBE+2-Codec aus der Firmware des Funkgeräts
  Tytera MD380 aus. Die Firmware selbst stammt von Tytera; ihre Lizenz ist
  unbekannt, vergleichbare Projekte (md380tools, greyfoxsolid/vocoder,
  VoxDMR) liefern sie deshalb nicht mit.
- Die bisherige Bridge-DLL (`native/carendmr_md380_bridge.dll`, alte Bauart)
  enthält die Firmware fest eingebaut.

Festlegung ab 0.2.1.88:

- Öffentliche Builds enthalten **keine** MD380-Firmware. Der Nutzer stellt
  `D002.032.bin` und `d02032-core.img` selbst bereit („Sprach-Codec
  einrichten“); CarenDMR lädt sie zur Laufzeit.
- `packaging/build_release.ps1` verweigert einen öffentlichen Build mit der
  alten Bridge.
- Ab 0.2.1.89 lädt die Bridge die Firmware zur Laufzeit (Export
  `carendmr_md380_init_files`); `native/md380_dynarmic_build/CMakeLists.txt`
  übersetzt nur `md380_vocoder.cpp` aus dem Upstream (GPL-2.0-or-later,
  Doug McLain AD8DP, basierend auf md380tools).
- Bezug für den Nutzer: `TYT-Tytera-MD-380-FW-v232.zip` von md380.org
  (SHA-256 der Update-Datei `e1a1a11a…09f43` wie in
  `md380_vocoder_dynarmic/firmware/download.sh`) und `cores/d02032-core.img`
  aus md380tools (SHA-256 `d4039818…19f66`, identisch mit der Kopie in
  md380_vocoder_dynarmic). Das RAM-Abbild stammt aus einem laufenden MD380
  und wird wie die Firmware nicht mit CarenDMR verteilt.
- `carendmr/vocoder/md380_firmware.py` enthält das Auspackverfahren und den
  XOR-Schlüssel aus md380tools `md380_fw.py` (Travis Goodspeed KK4VCZ u. a.;
  Lizenz laut README „licensed in exchange for two liters of India Pale
  Ale“). Der Schlüssel ist keine Firmware, sondern das Verfahren, um die
  verschlüsselte Update-Datei zu lesen.
- Offen: alte DLL mit eingebauter Firmware aus dem Repository und ggf. der
  Git-Historie entfernen.

Patente: DVSI vergibt Lizenzen für AMBE+2. Ob für die Nutzung des
emulierten Codecs Patentrechte berührt sind, ist nicht geprüft; die
Verantwortung liegt wie bei DroidStar und VoxDMR beim Nutzer. Diese
Dokumentation ist keine Rechtsberatung.
