# Architekturentscheidungen

Dieses Dokument ergänzt die in Version 0.0.3 begonnenen Entscheidungen.

## ADR-0008 – Core vor Audio und Netzwerk

**Status:** beschlossen  
**Version:** 0.0.4

CarenDMR erhält vor Audio und Netzwerk eine kleine, unabhängige Kernschicht aus
EventBus und StatusManager.

**Grund:** Spätere Komponenten dürfen nicht direkt voneinander abhängig werden.
Audiofehler, Netzwerkzustände und Bedienaktionen sollen denselben
nachvollziehbaren Kommunikationsweg verwenden.

## ADR-0009 – EventBus bleibt zunächst synchron

**Status:** beschlossen  
**Version:** 0.0.4

Der EventBus arbeitet zunächst synchron und ohne Threads.

**Grund:** Einfachheit, reproduzierbare Tests und leichte Fehlersuche. Threads
werden erst an den Grenzen von Audio und UDP eingeführt.

## ADR-0010 – Verständliche Meldungen sind eigene Fachlogik

**Status:** beschlossen  
**Version:** 0.0.4

Technische Zustände und deutschsprachige Rückmeldungen werden getrennt.

**Grund:** Ein Netzwerkmodul darf nicht entscheiden, was Caren hört.
Formulierungen, Wiederholungen und Prioritäten gehören zur
Accessibility-Schicht.

## ADR-0011 – Keine feste TTS-Abhängigkeit in 0.0.4

**Status:** beschlossen  
**Version:** 0.0.4

Die erste Speech-Ausgabe nutzt die Konsole hinter einer austauschbaren
Schnittstelle.

**Grund:** Native Windows- und macOS-Ausgabe soll praktisch geprüft werden,
bevor eine Bibliothek zur dauerhaften Projektabhängigkeit wird. Die verfügbaren
öffentlichen pyttsx3-Unterlagen nennen überwiegend sehr alte getestete
Betriebssystemversionen.

## ADR-0012 – sounddevice ist bevorzugte Audio-Basis

**Status:** vorgesehen für 0.0.5  
**Version:** 0.0.4

Für Audio-Geräte, Aufnahme und Wiedergabe wird `sounddevice` bevorzugt.

**Grund:** Plattformunterstützung für Windows und macOS, PortAudio-Basis,
Geräteabfrage sowie Callback-Streams für spätere Echtzeitanforderungen.

Die endgültige Freigabe erfolgt erst nach dem praktischen Gerätetest in 0.0.5.

## ADR-0013 – Keine vorgezogene BrandMeister-Funktion

**Status:** beschlossen  
**Version:** 0.0.4

Version 0.0.4 enthält weder UDP noch Login-Simulationen.

**Grund:** Jede Version soll eine kleine, vollständig prüfbare Verantwortung
haben. Netzwerkcode würde die Abnahme des Core unnötig vermischen.
