# CarenDMR 0.0.13.1 – Project Foundation

## Zweck

Dieser Meilenstein vereinheitlicht Projekt-, Installations- und
Entwicklungsdokumentation. Er ändert keine DMR-, Netzwerk-, Audio- oder
Sendefunktion.

## Enthalten

- README als zentraler, barrierefrei formulierter Projekteinstieg
- Roadmap mit abgeschlossenen und nächsten Produktmeilensteinen
- Beitrags- und Sicherheitsregeln
- getrennte Installationsanleitungen für macOS, Windows und Linux
- aktueller Architekturüberblick bis einschließlich Empfangsdecoder,
  Jitterpuffer und verriegeltem Parrot-Test
- reproduzierbarer Release- und Pull-Request-Ablauf
- konsistente Verknüpfung von Lizenz, Provenienz, Accessibility,
  BrandMeister-Kompatibilität und Änderungsverlauf

## Unveränderter Funktionsstand

- bestätigter BrandMeister-Login
- strikter DMRD-Empfang
- nativer, nur empfangender AMBE+2/mbelib-Decoder
- begrenzte PCM-Wiedergabe und TG91-Live-Empfang
- verriegeltes privates Parrot-Profil
- keine allgemeine PTT- oder Encoderoberfläche

## Validierung

- vollständige Python-Testreihe
- nativer macOS-Build mit Symbolprüfung
- Versions- und Linkkonsistenz der Projektdokumentation
- Kontrolle, dass keine lokale Konfiguration oder Build-Artefakte im Diff
  enthalten sind

Die verbindliche Versionsquelle bleibt `carendmr/version.py`.
