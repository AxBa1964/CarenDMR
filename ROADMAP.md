# Roadmap

Die Roadmap beschreibt Produktmeilensteine, keine festen Termine. Jeder
Meilenstein muss automatisiert getestet, dokumentiert und nach den
[Accessibility-Anforderungen](docs/ACCESSIBILITY_REQUIREMENTS.md) praktisch
abgenommen werden.

## Abgeschlossen

### Fundament und BrandMeister

- Projekt-, Test- und Release-Grundlage
- Audio-Geräteerkennung und lokaler Selbsttest
- BrandMeister-Login, Heartbeat und Diagnose
- eigene kompatible Software- und Package-Kennung

### DMR-Empfang

- striktes DMRD-Paketmodell
- Empfangsereignisse ohne Sprachpayload
- AMBE+2-Empfangsgrenze und nativer mbelib-Decoder
- Jitterpuffer und begrenzte PCM-Wiedergabe
- bestätigter TG91-Live-Empfang

### Sendesicherheit

- öffentliche automatisierte Gruppenruf-Tests dauerhaft deaktiviert
- privates Parrot-Profil auf 9990, Timeslot 2 und feste Zeitgrenzen verriegelt
- einmaliger stummer Parrot-Test erfolgreich abgeschlossen

## Nächste Meilensteine

### 0.0.14.1 – Read-only VoiceOver-Grundfenster

- Verbindungsstatus, TG91, Timeslot 2 und Audiozustand
- aktuelle Aktivität und zugängliches Ereignisprotokoll
- Verbinden/Trennen ohne PTT
- stabile Fokusreihenfolge und priorisierte Ankündigungen
- praktische Abnahme mit VoiceOver

### 0.0.15 – Zugängliche Einrichtung

- getrennter Bereich „Einrichtung und Verbindung“
- Audio-Ein- und Ausgabegeräte
- BrandMeister-Konfiguration ohne Offenlegung von Geheimnissen
- Speichern und Verbindungstest als getrennte Aktionen

### 0.0.16 – Nutzbarer Empfang

- laufende QSOs verständlich darstellen
- DMR-ID, Rufzeichen und Talkgroup ansagen, soweit zuverlässig vorhanden
- robuste Wiederverbindung und verständliche Diagnose
- subjektive Sprachverständlichkeit mit der Nutzerin abnehmen

### 0.0.17 – Kontrollierte PTT

- Mikrofon-PCM und rechtlich geklärte Encoderstrategie
- eindeutig bedienbare PTT mit akustischer Sende-/Empfangsrückmeldung
- harte Zeit- und Zielschutzregeln
- ausschließlich private, kontrollierte Tests vor Freigabe

## Vor Version 1.0

- vollständige Kernabläufe mit VoiceOver und NVDA testen
- Windows- und macOS-Paketierung reproduzierbar machen
- Datenschutz-, Codec-/Patent- und Vertriebsfragen klären
- Installations-, Diagnose- und Notfallanleitungen mit Nutzerinnen testen

## Nicht geplant

- andere digitale Betriebsarten
- Hotspot- oder Repeaterbetrieb
- automatisierte Aussendungen auf öffentlichen Talkgroups
- eine komplexe, visuell dominierte Mehrprotokoll-Oberfläche
