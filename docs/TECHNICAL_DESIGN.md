# CarenDMR – Technisches Design

**Stand:** Version 0.0.4  
**Zweck:** Verbindliche technische Leitplanken für die nächsten Releases.

## 1. Zielbild

CarenDMR wird kein allgemeiner Multimode-Client. Das Programm soll eine kleine,
zuverlässige und barrierefreie Bedienoberfläche für BrandMeister-DMR werden.

Die Architektur trennt deshalb konsequent:

1. Anwendungszustand
2. barrierefreie Rückmeldungen
3. Audio
4. BrandMeister-Netzwerk
5. DMR-Rahmen
6. Vocoder
7. spätere Bedienoberfläche

Keine dieser Schichten darf technische Details einer anderen Schicht ungeprüft
nach außen weiterreichen.

## 2. Core

### EventBus

Version 0.0.4 führt einen kleinen synchronen EventBus ein. Synchron bedeutet:
Ein Ereignis wird unmittelbar an alle registrierten Empfänger verteilt.

Diese einfache Form ist absichtlich gewählt:

- leicht verständlich
- deterministisch testbar
- keine versteckten Threads
- keine zusätzliche Bibliothek
- ausreichend für den heutigen Projektstand

Audio- und Netzwerk-Threads werden später nur an ihren technischen Grenzen
eingeführt. Der zentrale Anwendungszustand bleibt davon getrennt.

### StatusManager

Der StatusManager ist die einzige Stelle, die den übergeordneten Zustand der
Anwendung verwaltet. Komponenten sollen nicht selbstständig beliebige Texte
ausgeben.

Vorgesehene Zustände:

- STARTING
- READY
- CONNECTING
- CONNECTED
- DISCONNECTED
- RECEIVING
- TRANSMITTING
- ERROR

Eine echte Änderung erzeugt ein `StatusChangedEvent`. Wiederholungen desselben
Zustands werden standardmäßig unterdrückt, damit Screenreader und spätere
Sprachausgabe nicht unnötig wiederholen.

## 3. Barrierefreiheit und Sprachausgabe

Technische Zustände werden zunächst in verständliche deutsche Texte übersetzt.
Die Ausgabe erfolgt in 0.0.4 ausschließlich auf der Konsole.

Wichtig: Die Konsolenausgabe ist kein Provisorium im Sinne einer Sackgasse.
Sie implementiert bereits dieselbe Schnittstelle, die später von nativer
Sprachausgabe verwendet wird.

Geplante Plattformadapter:

- Windows: native SAPI-Anbindung
- macOS: native Systemsprachausgabe
- Testbetrieb: aufzeichnende oder stumme Ausgabe
- Fallback: Konsole

Eine konkrete TTS-Bibliothek wird erst ausgewählt, nachdem sie auf aktuellen
Windows- und macOS-Systemen praktisch geprüft wurde. `pyttsx3` wird in 0.0.4
nicht als feste Abhängigkeit übernommen, weil die öffentlich dokumentierten
Testangaben zu den Plattformtreibern deutlich veraltet sind.

## 4. Audioentscheidung

Für Version 0.0.5 ist `sounddevice` als bevorzugte Python-Bibliothek vorgesehen.

Begründung:

- Windows, macOS und Linux werden unterstützt
- basiert auf PortAudio
- kann Geräte abfragen
- kann aufnehmen und wiedergeben
- unterstützt Callback-Streams für spätere niedrige Latenz
- klare Trennung zwischen Geräteerkennung und Audiostream

Version 0.0.4 installiert `sounddevice` noch nicht. Erst 0.0.5 bringt die
Abhängigkeit und einen AudioManager mit echten Gerätetests ein.

Alternativen:

### PyAudio

Technisch grundsätzlich geeignet, bringt aber häufig mehr Installations- und
Build-Aufwand mit. Kein Vorteil für den ersten CarenDMR-Audiopfad.

### soundcard

Interessant für bestimmte Plattformfunktionen, aber für den geplanten
PortAudio-basierten, plattformübergreifenden Pfad derzeit nicht erste Wahl.

### miniaudio

Schlank und attraktiv für Wiedergabe und Dateiformate. Für die geplante
Geräteerkennung und bidirektionale Echtzeitkommunikation ist `sounddevice`
zunächst direkter passend.

## 5. Konfiguration

JSON bleibt das Konfigurationsformat. Geheimnisse wie das BrandMeister-
Hotspot-Passwort dürfen später nicht in Beispielkonfigurationen, Git oder
Release-ZIPs landen.

Geräte werden nicht nur über eine laufende Nummer gespeichert. Laufende
Audioindizes können sich nach Neustarts ändern. Die spätere Auswahl soll daher
mindestens Gerätename, Host-API und Kanalrichtung berücksichtigen und bei
Abweichungen verständlich auf das Standardgerät zurückfallen.

## 6. Logging

CarenDMR verwendet weiterhin das Python-Modul `logging`.

Regeln:

- technische Details ins Log
- verständliche Meldungen an die Accessibility-Schicht
- Passwörter niemals loggen
- Audiopakete nicht standardmäßig einzeln loggen
- Fehler enthalten Kontext, aber keine Zugangsdaten

## 7. Tests

`unittest` bleibt das Testframework. Externe Hardware und Audio müssen in Tests
über Schnittstellen ersetzt werden können.

Version 0.0.4 testet:

- Ereignisverteilung
- Abmeldung von Ereignissen
- Zustandswechsel
- Unterdrückung unnötiger Wiederholungen
- Übersetzung technischer Zustände
- Entkopplung der Ausgabeschicht

## 8. Noch nicht Bestandteil von 0.0.4

- Audio-Geräte erkennen
- Mikrofonaufnahme
- Lautsprecherwiedergabe
- echte Text-to-Speech-Ausgabe
- BrandMeister-Anmeldung
- UDP-Kommunikation
- DMRD-Rahmen
- AMBE-Vocoder
- grafische Oberfläche
- globale Tastatursteuerung

## 9. Nächster Schritt

Version 0.0.5 implementiert ausschließlich die Audio-Grundlage:

1. `sounddevice` als dokumentierte Abhängigkeit
2. Eingabe- und Ausgabegeräte erkennen
3. Standardgeräte kennzeichnen
4. verständliche Geräteliste
5. Auswahl sicher speichern
6. lokaler Aufnahme-/Wiedergabetest
7. automatisierte Tests ohne echte Hardware
