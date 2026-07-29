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

Nicht übernommen wurden Qt/UI, Audioaufnahme oder -wiedergabe, AMBE-Geräte- und
Software-Vocoder, Netzwerktransport, BrandMeister-Anmeldung, Modemsteuerung,
Timer, PTT/Keying sowie alle anderen Digitalfunkarten.

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
