# CarenDMR.box – eigenständiger DMR-Client auf dem Raspberry Pi (Konzept, Stand 27.11.2026)

Ziel: ein kleines Gerät ohne Bildschirm, das per WLAN ins Internet geht, sich bei
BrandMeister anmeldet und vollständig ohne PC DMR-Betrieb ermöglicht. Bedienung über
Tasten, PTT und einen Dreh-/Drückschalter direkt an der Box,
alle Rückmeldungen per Sprachausgabe. Verwaltung über eine Web-Oberfläche im
Heimnetz (wie bei der FRITZ!Box).

Umsetzung erst nach „jetzt umsetzen“. Bis dahin werden hier Wünsche gesammelt.

## Entschieden

- **Entwicklungsgerät: Raspberry Pi 4 Model B, 1 GB, mit Lüfter** (bestellt).
  Netzteil 5,1 V / 3 A USB-C (offizielles Netzteil empfohlen).
- **Zielgerät später ggf. Raspberry Pi Zero 2 W** (vorhanden) – nur wenn die
  Codec-Messung (siehe unten) ausreichend Reserve zeigt.
- **Betriebssystem: Raspberry Pi OS Lite, 64 Bit**, ohne Desktop.
- **Codec wie im Desktop-Client:** MD380-Emulation per dynarmic, Firmware wird
  **nicht** ausgeliefert, sondern bei der Einrichtung von der Box selbst
  heruntergeladen (gleiche Quellen und SHA-256 wie in `CLAUDE.md`).
  Grundlage für den ARM64-Build: Branch `feature/android-arm64-prototype`.
- **Der Raspberry Pi übernimmt alles, kein RP2040 in der Box.** Funktionstasten,
  PTT-Leiste, Dreh-/Drückschalter und Vibrationsmodul hängen direkt an den
  GPIO-Pins des Pi. Quittungstöne kommen über den Box-Lautsprecher (kein PAM8302
  nötig). Tasten, Braille und Kappenformen wie im Tastenfeld-Konzept.
- Das RP2040-Tastenfeld (`docs/TASTENFELD_KONZEPT.md`) bleibt ein eigenes Gerät
  für den PC.
- **Verwaltung:** Web-Oberfläche im Heimnetz, kein Bildschirm an der Box.
- **Alles in einem Gehäuse:** Pi, USB-Soundkarte, Lautsprecher, Mikrofon, Tasten,
  PTT, Dreh-/Drückschalter, Vibration. Headset wahlweise per USB oder Bluetooth.
  Ein Netzteil, ein Gerät.
- **Gerätename im Netz: `carendmr-box`**, Web-Verwaltung unter
  `http://carendmr-box.local`.
- **Web-Verwaltung über HTTP** (kein HTTPS) – nur im Heimnetz, Begründung unter
  „Sicherheit“.
- **Umfang: nur Betrieb.** Kein QRZ, kein Logbuch, kein ADIF, kein TG-Monitor,
  kein Audio-Benchmark, kein Audio-Labor, keine Last-Heard-Überwachung.

## Umfang der Box

| Enthalten | Nicht enthalten |
|---|---|
| BrandMeister-Anmeldung (Homebrew/MMDVM) | QRZ-Abfrage, QRZ-Karte |
| Empfang und Senden (PTT), TX-Zeitlimit | Logbuch, QSO-Sync, ADIF-UDP |
| Talkgroup-Favoriten (vorbelegt), Papagei 9990 als Privatruf | TG-Monitor, Monitoring |
| Lautstärke, Mikrofonpegel | Audio-Benchmark, Audio-Coach, Tuner |
| Sprachansagen (Status, Menü, Rufzeichen der Gegenstation) | Qt-Oberflächen |
| Codec-Einrichtung (Download) | |
| Web-Verwaltung, Update, Sicherung | |

Vorbelegte Talkgroups wie im Desktop-Client (`config/favorites.default.json`):
91 World-wide, 9990 Papagei (privat), 262 Deutschland, 2623 Niedersachsen/Bremen.

## Erreichbarkeit der Web-Oberfläche

Entschieden: **`http://carendmr-box.local`** (mDNS über Avahi auf der Box). Das
funktioniert ohne Router-Einstellung unter Windows 10/11, macOS und iOS; Android
im Test prüfen. Eine Adresse wie `carendmr.box` geht im Heimnetz nicht von allein,
weil die Box dort nicht der Namensdienst (DNS) ist.

Im **Einrichtungsmodus** spannt die Box ihr eigenes WLAN „CarenDMR-Box“ auf und ist
dort selbst Namensdienst; jede Adresse führt auf die Einrichtungsseite (Captive
Portal, öffnet sich auf dem Handy meist von selbst).

Zusätzlich sagt die Box ihre Adresse auf Tastendruck an
(„CarenDMR ist erreichbar unter carendmr minus box Punkt local, IP 192.168.178.42“).

## Einrichtungsmodus (Erststart / kein WLAN bekannt)

- Box startet ohne bekanntes WLAN → eigenes WLAN „CarenDMR-Box“ mit Kennwort
  (Kennwort steht auf dem Gehäuse, auch in Braille) → Ansage „Einrichtungsmodus“.
- Einrichtungsseite: Heim-WLAN wählen und Kennwort eingeben → Box verbindet sich
  und sagt die neue Adresse an.
- Manuell erreichbar über eine Tastenkombination an der Box (z. B. lang drücken
  beim Einschalten), falls das WLAN gewechselt werden muss.
- Rückfall ohne Handy: USB-Stick mit `carendmr-box.local.json` (WLAN, Station);
  die Box liest ihn beim Einstecken ein und bestätigt per Ansage.

## Seiten der Web-Verwaltung

1. **Übersicht** – Verbindungsstatus (WLAN, BrandMeister), aktuelle Talkgroup,
   Version, Codec eingerichtet ja/nein.
2. **Station** – Rufzeichen, DMR-ID, Hotspot-Kennwort BrandMeister, Server
   (Vorgabe `master2.bm262.de`, Port 62031), Verbindungstest.
3. **WLAN** – Netzwerke suchen, verbinden, gespeicherte Netze verwalten.
4. **Sprach-Codec** – Firmware herunterladen bzw. eigene Dateien hochladen,
   Prüfung per SHA-256 (gleiche Logik wie `codec_setup_service.py`).
5. **Audio** – Ausgabe- und Eingabegerät, Lautstärke, Mikrofonpegel, Testton,
   Mikrofontest (Aufnahme und Wiedergabe), TX-Zeitlimit.
6. **Talkgroups** – Favoritenliste (vorbelegt), hinzufügen, entfernen, sortieren,
   Name für die Ansage; 9990 automatisch Privatruf (`channel_rules.py`).
7. **Bedienung** – Tastenbelegung (kurz/lang), Ansagegeschwindigkeit, Stimme,
   Ansage-Lautstärke.
8. **System** – Update suchen und installieren, Neustart, Herunterfahren,
   Einstellungen sichern/wiederherstellen (ohne Kennwörter), Protokoll für die
   Fehlersuche herunterladen, Verwaltungskennwort ändern.

Barrierefreiheit (ADR-0014 gilt auch hier): schlichtes, semantisches HTML,
jedes Feld mit Beschriftung, Überschriften-Struktur, Fehlermeldungen als Text am
Feld, ohne Maus bedienbar, getestet mit NVDA, VoiceOver und TalkBack. Seiten
funktionieren auch ohne JavaScript.

## Sicherheit

- Verwaltungskennwort wird bei der Einrichtung festgelegt; ohne Anmeldung nur die
  Übersicht (oder gar nichts) sichtbar.
- Kennwörter (BrandMeister, WLAN, Verwaltung) sind **nur schreibbar**: Die Seite
  zeigt nie ein gespeichertes Kennwort an, nur „gesetzt“.
- Zugangsdaten liegen auf der Box in `*.local.json`, Rechte nur für den
  CarenDMR-Dienst.
- Web-Oberfläche nur im lokalen Netz, keine Portfreigabe nötig.
- **HTTP im Heimnetz (entschieden).** HTTPS bräuchte ein selbst signiertes
  Zertifikat; die Browser-Warnungen sind für Blinde schwer zu bestätigen. Das WLAN
  selbst ist per WPA2/WPA3 verschlüsselt. Restrisiko: Ein anderes Gerät im selben
  Heimnetz könnte Eingaben mitlesen – vertretbar, weil Kennwörter nur selten
  eingegeben werden und nie angezeigt werden. Keine Portfreigabe ins Internet.
- Im Einrichtungsmodus ist das Box-WLAN „CarenDMR-Box“ mit Kennwort geschützt.
- Sicherungsdatei enthält keine Kennwörter.

## Bedienung an der Box

- **Dreh-/Drückschalter:** Drehen = nächster Menüpunkt, jeder Punkt wird sofort mit
  Position angesagt („Talkgruppe Deutschland, 3 von 5“). Kurz drücken = auswählen,
  lang drücken = zurück. Im Betrieb: Drehen = Talkgroup wechseln oder Lautstärke
  (Belegung mit Caren abstimmen).
- **Tasten an der Box:** PTT, Funktionstasten wie im Tastenfeld-Konzept; kurzer
  Vibrationsimpuls bei jedem Tastendruck, Quittung (hoch = OK, tiefer Doppelton +
  lange Vibration = Fehler) über Box-Lautsprecher und Vibrationsmodul.
- **„Wo bin ich?“-Taste:** sagt Menü, Punkt, Talkgroup und Verbindungszustand an.
- **Ansagen beim Einschalten:** „CarenDMR startet“ → „WLAN verbunden“ →
  „BrandMeister angemeldet, Talkgruppe Deutschland“. Fehler werden klar benannt
  („Kein WLAN – Einrichtungsmodus aktiv“).
- **Sprachausgabe:** Feste Texte (Menüpunkte, Statusmeldungen) als vorab erzeugte
  WAV-Dateien in guter Stimme; nur veränderliche Texte (Rufzeichen, Namen) live
  über espeak-ng bzw. Piper (auf dem Pi 4 ausreichend schnell).
- **Herunterfahren:** lange Tastenkombination → Ansage „Box fährt herunter“, damit
  die SD-Karte nicht beschädigt wird.

## Hardware (Entwicklung)

| Teil | Zweck |
|---|---|
| Raspberry Pi 4 B, 1 GB, mit Lüfter | bestellt |
| Netzteil 5,1 V / 3 A, USB-C | Stromversorgung |
| microSD 16–32 GB (Markenkarte, A1) | System |
| USB-Soundkarte UGREEN USB Sound Adapter (Amazon B016CU2PEU, getrennte Buchsen Kopfhörer/Mikrofon, Raspberry Pi genannt); Alternative Delock 63926 (Amazon B07GVL4BHC, C-Media CM6533) | Ein- und Ausgabe; Pi 4 hat keinen Mikrofoneingang |
| Verstärker PAM8302 (vorhanden/bestellt, 5 V, mono) | an den Kopfhörerausgang der Soundkarte |
| Lautsprecher Zuahaly 3 W / 8 Ω (vorhanden/bestellt) | Empfang, Ansagen, Quittungstöne |
| Erste Tests: BerryBase „USB Mini Mikrofon“ (Art. 125147) | Mikrofon direkt per USB, ohne Löten |
| Endausbau: Elektret-Kapsel 6 mm mit Anschlussdrähten (z. B. Amazon B00OK619WS, 3 Stück) + Kabel mit 3,5-mm-Stecker | im Gehäuse, an den Mikrofoneingang der Soundkarte; keine MAX9814/MAX4466-Module (Linepegel) |
| Taster Gateron Brown (5–6 Funktionstasten) | an GPIO (Pull-up, gegen GND) |
| PTT-Leiste (2 Taster parallel) | ein GPIO |
| Dreh-/Drückschalter (Encoder mit Taster) | Menü, drei GPIO |
| Vibrationsmodul DAOKAI 5 V | Quittung, ein GPIO |
| Headset (optional) | USB oder Bluetooth |

### Audio-Verkabelung

- Soundkarte steckt per kurzem USB-Kabel (oder Winkeladapter) am Pi im Gehäuse.
- Kopfhörerausgang → PAM8302 (A+ an Signal, A− an Masse) → Lautsprecher.
  PAM8302 an 5 V des Pi, SD-Pin an GPIO (stumm, wenn nichts ausgegeben wird).
  Lautstärke per Trimmpoti grob begrenzen, fein in der Software.
- Mikrofonkapsel an den Mikrofoneingang (die Soundkarte liefert die
  Speisespannung für Elektret). Kapsel vorne hinter Lochgitter, in Gummi gelagert,
  mit Abstand zu Lüfter und Lautsprecher.
- Nicht den analogen 3,5-mm-Ausgang des Pi 4 nutzen (rauscht).
- Keine Handy-Mikrofone mit 4-poligem Stecker (CTIA/TRRS) an den 3-poligen
  Mikrofoneingang der Soundkarte – Pinbelegung passt nicht.
- Nach dem Anstecken prüfen: `lsusb` und `arecord -l` zeigen die Soundkarte.
- Zu prüfen: Brummen/Pfeifen durch gemeinsame 5-V-Versorgung (Klasse-D-Verstärker
  und USB-Soundkarte). Abhilfe bei Bedarf: Ferrit, kurzes geschirmtes Kabel,
  Masse sternförmig.
- Alternative: Audio-Aufsteckplatine mit WM8960 (Mikrofone und Verstärker an Bord,
  z. B. Waveshare WM8960 Audio HAT) – kompakter, aber Treiber muss bei
  Kernel-Updates passen. Zunächst USB-Soundkarte.

### Audio-Wege

- **Eingebaut:** Lautsprecher und Mikrofon im Gehäuse. Beim Senden ist der
  Lautsprecher stumm (Halbduplex), daher keine Rückkopplung.
- **USB-Headset:** wird beim Einstecken erkannt und automatisch genutzt, Ansage
  „Headset verbunden“; beim Abziehen zurück auf eingebaut.
- **Bluetooth-Headset:** Kopplung über die Web-Verwaltung (Seite Audio) oder per
  Menü am Drehschalter. Freisprechprofil (HFP) mit 8 bzw. 16 kHz reicht, weil DMR
  ohnehin nur 8 kHz überträgt. Zu testen: zusätzliche Verzögerung, und dass
  Bluetooth und WLAN auf dem Pi 4 denselben Funkchip teilen – WLAN möglichst auf
  5 GHz.
- **Geräusche im Gehäuse:** Lüfter nur temperaturgesteuert, Mikrofon entkoppelt
  und weit weg vom Lüfter montieren; beim Mikrofontest prüfen.

## Software-Aufbau

- Neue Oberfläche `carendmr/box/` neben `ui_qt/`, **ohne Qt**:
  - Box-Dienst (systemd), startet über `bootstrap.py` / `build_radio_core()` und
    bedient den Funk nur über den `OperatingController`.
  - Eingabe: `KeypadService` mit austauschbarer Quelle – GPIO an der Box,
    USB-CDC beim RP2040-Tastenfeld am PC. Beide liefern dieselben Tastenereignisse
    (`KEY n DOWN/UP/LONG`, Encoder), die Bedienlogik ist für beide gleich.
  - Ausgabe: Linux-Variante von `SpeechOutput` (`accessibility/speech.py`).
  - Web-Verwaltung: kleiner HTTP-Server im selben Prozess oder als eigener Dienst;
    ändert Einstellungen nur über die bestehenden Application-Services
    (`station_settings_service`, `favorite_service`, `codec_setup_service`,
    `audio_setup_service` …).
- Abhängigkeiten auf der Box abspecken: kein PySide6, matplotlib, librosa.
  Zu prüfen: `ipc/channel_control.py` nutzt QtNetwork; `scipy` wird in
  Audio-Diensten für Resampling/Filter verwendet.
- Kein eigener UDPProvider auf der Box: direkt zu master2, Port 62031.
- Updates: zunächst per Web-Seite (Paket von dk7ee.de, Prüfung per SHA-256);
  später ggf. fertiges SD-Karten-Abbild zum Download.

## Messplan Codec (vor weiterer Hardware)

1. Bridge für Linux ARM64 bauen (Grundlage Android-ARM64-Build).
2. Test-WAV kodieren und dekodieren, Zeit pro 20-ms-Sprachrahmen messen,
   getrennt für Kodieren und Dekodieren, mit CPU-Last und Temperatur.
3. Erst Pi 4, dann Zero 2 W. Ziel: deutlich unter 20 ms pro Rahmen mit Reserve
   für Netzwerk, Audio und Sprachausgabe.

## Offen

- Web-Technik: nur Python-Standardbibliothek oder kleines Framework.
- Belegung Dreh-/Drückschalter und Tastenfeld im Betrieb (mit Caren testen).
- Pi-Modell für die fertige Box: Pi 4 (bestellt, 85 × 56 mm), Pi 3 A+
  (65 × 56 mm) oder Zero 2 W (65 × 30 mm) – nach der Codec-Messung.
- Gehäuse (3D-Druck, Bambu Lab H2S): vorhandenes Tastenfeld-Gehäuse erweitern oder
  neu konstruieren; Maße nach Lieferung von Pi, Lüfter, Lautsprecher und
  Soundkarte. Lüfter weit weg vom Mikrofon.
- GPIO-Belegung festlegen (Pins für Lüfter und ggf. späteres I2S-Audio freihalten).
- Soll die Web-Verwaltung später auch Gegenstationen anzeigen (aktuell: nein,
  kein Monitoring)?
