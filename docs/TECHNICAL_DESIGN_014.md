# CarenDMR 0.0.13 – Verriegeltes Parrot-Testprofil

## Dauerhafte Regel

Automatisierte Übertragungstests dürfen niemals eine öffentliche
Gruppen-Talkgroup verwenden. Es gibt keinen öffentlichen Fallback.

Der einzige zulässige zukünftige Test ist fest definiert als:

- BrandMeister Parrot,
- Ziel-ID 9990,
- Privatruf (`FLCO_USER_USER = 3` und Homebrew-Privatrufbit gesetzt),
- Timeslot 2,
- höchstens 10 Sekunden Übertragung,
- exakt höchstens 15 Sekunden Echo-Beobachtung,
- kein Retry und keine Wiederholungsschleife.

## Paket- und Profilgrenze

`LockedParrotTestProfile` enthält alle Sicherheitswerte unveränderlich.
Die Builder nehmen ausschließlich lokale Quell-/Repeater-/Stream- und
Sequenzwerte an. Ziel, Ruftyp, Timeslot und Zeitgrenzen sind keine
Laufzeitparameter.

`ParrotTestPlan` enthält eine validierte Acht-Paket-Stumm-Fixture und die
festen Zeitwerte, aber absichtlich keine `send`- oder `execute`-Methode.
Nur der getrennte Executor `execute_locked_parrot_once()` darf diesen Plan
nach erneuter Validierung genau einmal ausführen.

Das historische Werkzeug `tools/brandmeister_one_shot.py` schlägt unabhängig
von Argumenten immer vor jeder Netzwerkaktion fehl. Sein früherer
TG91-Sendeloop wurde entfernt.

## Byte-Abnahme

Für Voice-LC-Header, Voice Sync, fünf nummerierte Voice Bursts und Terminator
sind die Homebrew-Flags fest:

`E1 D0 C1 C2 C3 C4 C5 E2`

In jedem Byte ist das Privatrufbit `0x40` gesetzt; das Timeslot-2-Bit `0x80`
bleibt ebenfalls gesetzt. Ziel-ID, Call-Type und Timeslot werden nach
Serialisierung erneut geparst und verglichen. Die acht 33-Byte-Payloads sind
als nicht-personale Referenzvektoren fixiert.

## Einmalige Live-Ausführung

### Lokale hörbare Phasen

Die spätere Live-Ausführung muss die Phasen Start, Übertragung,
Echo-Empfang, Erfolg, sicherer Abbruch und Timeout über eine lokale
`ParrotTestAnnouncer`-Schnittstelle verständlich ansagen. Die Ansagen enthalten
keine IDs, Rufzeichen, Server oder Payloaddaten. Sie können später nur im
barrierefreien Setup ein- oder ausgeschaltet werden; sie bieten keine
Laufzeitsteuerung für Ziel, Route oder Testdauer.

Während der Übertragungsphase sagt CarenDMR ausdrücklich an, dass die derzeit
validierte Fixture stumm ist und keine Sprache sendet. Ausgehende Sprache
existiert erst, wenn ein separater Software-TX-Vocoder oder eine
Mikrofonquelle implementiert, geprüft und freigegeben wurde.

Während der Echo-Phase werden zurückkehrende Parrot-Sprachrahmen über den
bestehenden Software-Empfangsdecoder, Jitterpuffer und das lokale
Standard-Wiedergabegerät ausgegeben. Es entsteht weiterhin keine Aufnahme.

Der getrennte Executor erfüllt folgende Gates:

1. erneute Validierung des unveränderlichen Plans vor jedem Paket,
2. monotone harte 10-s-Abbruchuhr; die aktuelle Stumm-Fixture dauert 0,36 s,
3. genau acht Pakete mit sieben festen 60-ms-Abständen,
4. Ziel 9990, privat und Timeslot 2 byteweise vor jedem Senden geprüft,
5. kein Retry, kein öffentlicher Fallback und keine Wiederholungsschleife,
6. anschließend höchstens 15 Sekunden receive-only Echo-Beobachtung,
7. Echo-Dekodierung über Software-Vocoder, Jitterpuffer und Standardausgabe,
8. Decoder, Audio und Socket werden in jedem Pfad geschlossen.

Die Nutzerfreigabe gilt für genau eine kontrollierte Ausführung nach
vollständiger Test- und lokaler Audio-/Ansageprüfung. Ein Fehler beendet den
Versuch ohne Wiederholung.

## Einmalige praktische Abnahme

Nach 122 erfolgreichen Offline-Tests, nativer Build-/Symbolprüfung und realer
lokaler Ansage-/Audio-Vorprüfung wurde genau eine autorisierte Live-Ausführung
durchgeführt:

- Authentifizierung erfolgreich,
- exakt acht private DMRD-Pakete gesendet,
- Übertragungszeit 0,440 Sekunden,
- sechs Parrot-Echo-Sprachbursts empfangen,
- 18 AMBE-Codewörter ohne Dekodierfehler verarbeitet,
- 2.880 PCM-Samples über die lokale Standardausgabe ausgegeben,
- null ungültige DMRD-Pakete,
- kein Echo-Timeout,
- kein Retry und keine Wiederholung,
- Socket, Decoder und Audiostream geschlossen.

Die ausgehende Fixture war stumm. Die Echoausgabe bestätigt daher Transport,
Rückweg und Audiopfad, aber keine ausgehende Sprachkodierung. Es wurden keine
Sprachinhalte, Identitäten, Payloads oder privaten Verbindungswerte
protokolliert oder gespeichert.
