# CarenDMR 0.0.6 – Netzwerkgrundlage

## Ziel

Version 0.0.6 schafft eine kleine, testbare UDP-Basis. Sie meldet sich noch
nicht bei BrandMeister an und überträgt keine Funk- oder Zugangsdaten.

## Komponenten

### NetworkConfig

Enthält:

- Servername
- UDP-Port
- Empfangszeitlimit
- Heartbeat-Intervall

Die produktive lokale Datei heißt:

```text
config/network.local.json
```

Sie wird nicht automatisch aus dem Beispiel erzeugt, damit niemals
versehentlich ein falscher Server kontaktiert wird.

### DNS-Auflösung

`resolve_udp_endpoint()` löst den Servernamen auf. IPv4 wird derzeit bevorzugt,
IPv6 bleibt grundsätzlich unterstützt.

### UdpTransport

Der Transport kapselt:

- Socket öffnen
- Zielendpunkt verbinden
- Bytes senden
- Bytes mit Zeitlimit empfangen
- Socket sicher schließen

Ein UDP-`connect()` baut keine dauerhafte Verbindung wie TCP auf. Er legt nur
den Zielendpunkt des lokalen Sockets fest. Ob der entfernte Server tatsächlich
antwortet, kann erst anhand eines gültigen Protokollpakets festgestellt werden.

### HeartbeatController

Der HeartbeatController ist absichtlich protokollneutral. Er entscheidet
deterministisch, wann ein Heartbeat fällig ist, erzeugt aber keine
BrandMeister-Nachricht.

Dadurch kann die Zeitlogik vollständig ohne echte Wartezeiten getestet werden.

### NetworkDiagnostics

Die Diagnose prüft in 0.0.6:

1. Konfiguration
2. DNS-Auflösung
3. Öffnen des lokalen UDP-Kanals

Sie behauptet ausdrücklich noch nicht, dass BrandMeister erreichbar oder die
Anmeldung erfolgreich ist.

## Sicherheitsgrenze

0.0.6 sendet beim Diagnosewerkzeug keine Pakete und benötigt noch keine
Anmeldedaten.

## Nicht enthalten

- BrandMeister-Anmeldepakete
- Passwort oder Kennwort-Hash
- Authentifizierungsantworten
- Protokoll-Heartbeat
- DMRD-Daten
- Audioübertragung
- Wiederverbindung
