# CarenDMR.box – eigenständiger DMR-Client auf dem Raspberry Pi (Konzept, Stand 27.11.2026)

Ziel: ein kleines Gerät ohne Bildschirm, das per WLAN ins Internet geht, sich bei
BrandMeister anmeldet und vollständig ohne PC DMR-Betrieb ermöglicht. Bedienung über
das Bedien-Tastenfeld (`docs/TASTENFELD_KONZEPT.md`) und einen Dreh-/Drückschalter,
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
- **Bedienung an der Box:** Tastenfeld (RP2040, USB-CDC, Protokoll aus dem
  Tastenfeld-Konzept) plus Dreh-/Drückschalter direkt an GPIO.
- **Verwaltung:** Web-Oberfläche im Heimnetz, kein Bildschirm an der Box.
- **Ein Gehäuse für alles:** Pi, Tasten, Dreh-/Drückschalter, Lautsprecher und
  Mikrofon. Headset wahlweise per USB oder Bluetooth.
- **Gerätename im Netz: `carendmr-box`.**
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
- Manuell erreichbar über eine Tastenkombination am Tastenfeld (z. B. lang drücken
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
- **Tastenfeld:** PTT, Funktionstasten wie im Tastenfeld-Konzept.
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
| USB-Soundkarte mit Mikrofoneingang, im Gehäuse | Pi 4 hat keinen Mikrofoneingang |
| Lautsprecher + kleiner Verstärker, im Gehäuse | Empfang und Ansagen |
| Mikrofon (Elektret), im Gehäuse | Senden |
| Dreh-/Drückschalter (Encoder mit Taster) | Menü, an GPIO |
| Taster (Gateron Brown wie im Tastenfeld-Konzept), PTT-Leiste | an GPIO oder RP2040 (offen) |
| Vibrationsmodul 5 V | Quittung, an GPIO |
| Headset (optional) | USB oder Bluetooth |

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
  - Eingabe: `KeypadService` (Tastenfeld, USB-CDC) und Encoder (GPIO).
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
- Tasten direkt an die GPIO-Pins des Pi (einfacher, kein RP2040 nötig) oder das
  RP2040-Tastenfeld per USB im Gehäuse (gleiche Firmware wie für den PC)?
- Gehäuse (3D-Druck, Bambu Lab H2S): Maße nach Lieferung von Pi, Lüfter,
  Lautsprecher und Soundkarte.
- Soll die Web-Verwaltung später auch Gegenstationen anzeigen (aktuell: nein,
  kein Monitoring)?
