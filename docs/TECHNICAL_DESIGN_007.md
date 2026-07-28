# CarenDMR 0.0.7 – BrandMeister-Login

## Referenz

Die Implementierung folgt dem in DroidStar verwendeten DMR-Master-Handshake.

## Ablauf

1. Client sendet `RPTL` plus DMR-/ESSID als vier Byte, Big Endian.
2. Master antwortet mit `RPTACK` plus vier Byte Challenge.
3. Client bildet SHA-256 aus `Challenge + UTF-8-Passwort`.
4. Client sendet `RPTK` plus DMR-/ESSID plus 32 Byte Hash.
5. Master bestätigt mit `RPTACK`.
6. Client sendet ein 302 Byte großes `RPTC`-Stationsdatenpaket.
7. Master bestätigt mit `RPTACK`.
8. Status wird auf verbunden gesetzt.
9. Client sendet `RPTPING` plus ID.
10. Master antwortet mit `MSTPONG` plus ID.
11. Beim Beenden sendet der Client `RPTCL` plus ID.

`MSTNAK` wird in jeder Anmeldephase als Ablehnung behandelt.

## Passwort

Verwendet wird nicht das normale BrandMeister-Webseitenkennwort, sondern das in
BrandMeister SelfCare gesetzte **Hotspot Security Password**.

Die produktive Datei heißt:

```text
config/brandmeister.local.json
```

Sie muss von Git ausgeschlossen bleiben.

## Sicherheitsgrenzen

- Passwort wird nie auf dem Bildschirm ausgegeben.
- Tests benutzen ausschließlich fiktive Daten und fiktive IP-Adressen.
- Das Diagnosewerkzeug führt genau einen Login, optional einen Ping und danach
  eine ordentliche Abmeldung durch.
- Noch keine Sprach- oder DMRD-Datenübertragung.
- Noch kein dauerhafter Hintergrundbetrieb.
