# CarenDMR.box – Raspberry Pi einrichten und Codec messen

Stand 0.2.1.93. Ziel dieses Schritts: Auf dem Raspberry Pi 4 läuft der
Sprach-Codec, und die Messung zeigt, wie viel Reserve bleibt. Konzept:
`docs/CARENDMR_BOX_KONZEPT.md`.

## 1. SD-Karte vorbereiten (am PC)

- Raspberry Pi Imager installieren (raspberrypi.com/software).
- Betriebssystem: **Raspberry Pi OS Lite (64-bit)**.
- In den Anpassungen des Imagers setzen: Gerätename `carendmr-box`, Benutzer
  und Kennwort, WLAN, **SSH einschalten**. Wo diese Einstellungen stehen,
  hängt von der Imager-Version ab.
- Karte in den Pi, Netzteil anschließen, etwa zwei Minuten warten.

## 2. Vom PC aus anmelden

```powershell
cd C:\ABDevelop\CarenDMR
ssh <benutzer>@carendmr-box.local
```

Alle weiteren Befehle laufen auf dem Pi.

## 3. Pakete und Quellcode

```bash
sudo apt update
sudo apt install -y git cmake ninja-build g++ libboost-dev python3-venv alsa-utils libopus0
git clone https://github.com/AxBa1964/CarenDMR.git
cd CarenDMR
python3 -m venv .venv
.venv/bin/pip install -r requirements-box.txt
```

Später aktualisieren: `cd ~/CarenDMR && git pull`.

## 4. Codec-Bridge bauen

```bash
cd ~/CarenDMR
./native/build_md380_dynarmic_linux.sh
```

Dauert auf dem Pi 4 etwa 20–40 Minuten (zwei Compiler gleichzeitig, damit 1 GB
RAM reicht; Lüfter läuft). Ergebnis: `native/libcarendmr_md380_bridge.so`.

## 5. Firmware laden und messen

```bash
cd ~/CarenDMR
.venv/bin/python main.py --codec-benchmark --setup-codec
```

`--setup-codec` lädt beim ersten Mal die MD380-Firmware (md380.org) und das
RAM-Abbild (md380tools) und prüft beide per SHA-256 – derselbe Weg wie
„Sprach-Codec einrichten“ unter Windows. Danach genügt:

```bash
.venv/bin/python main.py --codec-benchmark
```

Optionen: `--frames 3000` (60 s statt 30 s), `--wav datei.wav` (eigenes
Testsignal, 8000 Hz, mono, 16 Bit).

Bewertung (Kodieren + Dekodieren, 99-%-Wert, Anteil am 20-ms-Rahmen):

| Anteil | Bewertung |
|---|---|
| bis 25 % | gut – genug Reserve |
| bis 50 % | knapp – unter Last prüfen |
| darüber | zu langsam |

Bitte die komplette Ausgabe zurückmelden; sie kommt ins Konzept.

## 6. Soundkarte und Mikrofon prüfen

UGREEN-Soundkarte einstecken, Kapsel an die rote Buchse, Kopfhörer oder
Verstärker an die grüne.

```bash
lsusb
arecord -l
aplay -l
arecord -D plughw:CARD=Device,DEV=0 -f S16_LE -r 8000 -c 1 -d 5 probe.wav
aplay -D plughw:CARD=Device,DEV=0 probe.wav
```

Der Kartenname (`Device`) steht in der Ausgabe von `arecord -l`; weicht er ab,
den dort genannten Namen einsetzen. Die Aufnahme `probe.wav` (8 kHz, mono)
taugt auch als Testsignal für `--wav`.
