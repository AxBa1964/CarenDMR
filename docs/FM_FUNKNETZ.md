# FM-Funknetz in CarenDMR

Stand 0.2.1.95: **anmelden und empfangen** im FM-Funknetz (SvxLink-Reflektor,
Protokoll 2.0). Es wird **nichts gesendet**. Konzept und Regeln des
Netzbetreibers: `docs/CARENDMR_BOX_KONZEPT.md`, Abschnitt „FM-Funknetz zusätzlich“.

## Technik

- Code: `carendmr/svxreflector/` (Qt-frei) – `protocol.py` (Nachrichten),
  `client.py` (TCP/UDP, Anmeldung, Heartbeats), `opus.py` (libopus per ctypes),
  `config.py`, `listen.py` (Konsolen-Empfang).
- Anmeldung: Challenge/Response mit HMAC-SHA1; der Key geht nie über das Netz.
- Sprache: Opus, 16 kHz, 20-ms-Rahmen; verlorene Pakete werden verschleiert.
- Heartbeats: TCP alle 10 s, UDP alle 15 s (Werte aus SvxLink).
- Quellen: SvxLink `src/svxlink/reflector/ReflectorMsg.h` (GPLv2+), Latry
  `android/ReflectorClientProtocol.cpp` (GPLv3); in Python neu umgesetzt.

## Einrichten (Windows)

1. Opus installieren (einmalig, MSYS2 UCRT64 ist schon für die Codec-Bridge da):

   ```powershell
   cd C:\ABDevelop\CarenDMR
   $env:MSYSTEM="UCRT64"; C:\msys64\usr\bin\bash.exe -lc "pacman -S --needed --noconfirm mingw-w64-ucrt-x86_64-opus"
   ```

   CarenDMR findet `libopus-0.dll` in `C:\msys64\ucrt64\bin` oder im Ordner `native`.

2. Zugang eintragen:

   ```powershell
   cd C:\ABDevelop\CarenDMR
   Copy-Item config\fm_funknetz.example.json config\fm_funknetz.local.json
   notepad config\fm_funknetz.local.json
   ```

   `callsign`: `DK7EE-APP` (PC-Client), `auth_key`: Key vom Netzbetreiber.
   Die Datei ist gitignored und wird nie eingecheckt.

## Einrichten (Raspberry Pi / Linux)

```bash
sudo apt install -y libopus0
```

Für die Box gilt `callsign` `DK7EE-TRX`.

## Empfangen

```powershell
cd C:\ABDevelop\CarenDMR
.\.venv\Scripts\python.exe main.py --fm-listen
```

- Vorgabe ist TG 20 („Testarea“). Andere Talkgroup: `--tg 9990`.
- Begrenzte Dauer: `--duration 300` (1–3600 s). Ende sonst mit Strg+C.
- Ausgabe: Anmeldung, „DB0XYZ spricht (Talkgroup 20)“, „… fertig nach 4,2 Sekunden“,
  am Ende eine Zusammenfassung.

Typische Meldungen:

| Meldung | Bedeutung |
|---|---|
| `fm_funknetz.local.json fehlt` | Schritt 2 noch nicht erledigt |
| `Opus fehlt` | Schritt 1 noch nicht erledigt |
| `Server meldet: Access denied` | Rufzeichen oder Key falsch, oder noch nicht freigeschaltet (bis 60 min) |
| `Der Server verlangt Protokoll 3.x` | Reflektor nimmt Protokoll 2.0 nicht an – dann Zertifikat nötig |
| `nicht erreichbar` | Server, Port (5308) oder Internetverbindung prüfen |

## Noch nicht enthalten

- Senden (PTT) – erst nach erfolgreichem Empfangstest; erste Aussendung über
  Papagei TG 9990/9998, Tests nur in TG 20.
- Einbindung in Hauptfenster, Easy und Box; Favoriten für FM.
- `libopus-0.dll` im Windows-Setup mitliefern.
