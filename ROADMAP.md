# Stand 0.1.1

Aktueller stabiler Qt-Funktionsstand: 0.0.28.3.

Aktueller stabiler Entwicklungsstand: **0.0.19.4** – Hold-to-Talk und bereinigte Sendeoberfläche.

# Roadmap

Die Roadmap beschreibt Produktmeilensteine, keine festen Termine. Jeder
Meilenstein muss automatisiert getestet, dokumentiert und nach den
[Accessibility-Anforderungen](docs/ACCESSIBILITY_REQUIREMENTS.md) praktisch
abgenommen werden.

## Abgeschlossen

### 0.0.17 – Dauerempfang und QSO-Historie

- periodischer BrandMeister-Heartbeat im Live-Empfang
- unbegrenzter GUI-Empfang bis zur Benutzeraktion
- lokaler, eigener Reiter für abgeschlossene Sprechdurchgänge

### Fundament und BrandMeister

- Projekt-, Test- und Release-Grundlage
- Audio-Geräteerkennung und lokaler Selbsttest
- BrandMeister-Login, Heartbeat und Diagnose
- eigene kompatible Software- und Package-Kennung

### DMR-Empfang

- striktes DMRD-Paketmodell
- AMBE+2-Empfangsgrenze und nativer mbelib-Decoder
- Jitterpuffer und PCM-Wiedergabe
- bestätigter TG91-Live-Empfang auf Timeslot 2

### 0.0.14 und 0.0.14.1 – Read-only-Hauptfenster

- getrennte Anzeige von BrandMeister, Empfang und Audio
- Verbinden und Trennen ohne PTT
- zugängliches Ereignisprotokoll
- vollständige Tastaturbedienung der Kernaktionen

### 0.0.15 – Aktuelle Station

- DMR-ID, Talkgroup und Timeslot des aktuellen Sprechers
- Sprechbeginn, Sprecherwechsel und Sprechende
- laufende Sprechdauer
- gemeinsame Application-Schicht für GUI und Konsole

## Nächste Meilensteine

### 0.0.16 – Zugängliche Einrichtung

- getrennter Bereich „Einrichtung und Verbindung“
- Audio-Ein- und Ausgabegeräte
- BrandMeister-Konfiguration ohne Offenlegung von Geheimnissen
- Speichern und Verbindungstest als getrennte Aktionen

### 0.0.17 – Nutzbarer Empfang

- lokale Rufzeichen- und Kontaktauflösung aus einer rechtlich geklärten Quelle
- robuste Wiederverbindung und verständliche Diagnose
- subjektive Sprachverständlichkeit mit der Nutzerin abnehmen

### 0.0.18 – Kontrollierte PTT

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

## Aktueller Zwischenstand 0.0.19.1

- optionale DroidStar-Vocoder-Plugin-Integration
- lokaler PCM-zu-AMBE-Test ohne Funkübertragung
- nächster Schritt: hart verriegelter privater Parrot-Sprachtest
