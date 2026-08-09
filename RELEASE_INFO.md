# CarenDMR 0.2.1.55 – Satellitenumschaltung

Die MapTiler-Satellitenansicht verwendet nun die für Leaflet dokumentierte 512-px-HiDPI-Variante `@2x.jpg`.

Beim Umschalten wird die jeweils andere Basiskarte explizit entfernt. Eine kleine Anzeige oben links nennt die tatsächlich aktive Basiskarte: **Karte** oder **Satellit**.

Falls MapTiler eine Kachel nicht liefert, erscheint in der Shell eine Diagnose mit der konkreten Tile-URL. Ein HTTP-403 deutet auf einen fehlenden, ungültigen oder eingeschränkten MapTiler-Key hin.
