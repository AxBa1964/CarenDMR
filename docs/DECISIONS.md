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

## ADR-0014 – VoiceOver ist verbindliche UI-Abnahmebedingung

**Status:** beschlossen
**Version:** 0.0.9

Jede zukünftige CarenDMR-Bedienoberfläche muss vollständig per Tastatur und
mit macOS VoiceOver bedienbar sein. Semantische Beschriftung, vorhersehbare
Fokusreihenfolge, nicht ausschließlich visuelle Zustandsdarstellung,
priorisierte Live-Ankündigungen, eine kompakte Zustandszusammenfassung, ein
zugängliches textuelles Ereignisprotokoll sowie verständliche Fehler und
nächste Aktionen sind verpflichtend.

**Grund:** CarenDMR ist nach einer blinden Person benannt und wird für eine
blinde Nutzerin entwickelt. Barrierefreiheit bestimmt deshalb Architektur,
Informationsmodell und Abnahme von Beginn der UI-Entwicklung an. Eine spätere
Nachrüstung würde zentrale Entscheidungen zu Fokus, Semantik und
Statuskommunikation zu spät korrigieren.

Die vollständigen Abnahmekriterien sind in
`docs/ACCESSIBILITY_REQUIREMENTS.md` festgehalten.

## ADR-0015 – Persönliche Verbindungseinstellungen sind vom Betrieb getrennt

**Status:** beschlossen
**Version:** 0.0.9

Rufzeichen, DMR-ID, BrandMeister-Zugangsdaten, Security-/Hotspot-Passwort,
Serverauswahl und verwandte persönliche Verbindungseinstellungen werden in
einem separaten, klar benannten und vollständig zugänglichen
Einrichtungs-/Konfigurationsbereich verwaltet. Sie erscheinen nicht als
dauerhafte Inhalte der normalen Betriebsansicht.

Geheimnisse bleiben maskiert. Speichern und Verbindungstest sind getrennte
Aktionen und melden Erfolg, Fehler sowie den Speicherzustand in einfacher,
VoiceOver-tauglicher Sprache.

**Grund:** Die Trennung reduziert Komplexität im täglichen Betrieb, schützt
sensible Daten vor versehentlicher Anzeige oder Ansage und ermöglicht eine
vorhersehbare Fokus- und Navigationsstruktur.

## ADR-0016 – Software-Vocoder bleibt empfangsseitig und austauschbar

**Status:** beschlossen
**Version:** 0.0.11

DMR-Empfangsaudio nutzt eine kleine zustandsbehaftete `ReceiveVocoder`-
Schnittstelle. Die erste Implementierung kapselt ausschließlich den
ISC/mbelib-basierten AMBE-2450/1150-Decoderpfad aus DroidStar.

MD380-Firmware, Codec2, Encode-/PTT-Funktionen und Audio-Wiedergabe gehören
nicht zu dieser Grenze. Ein Sprachstrom besitzt eine eigene Decoderinstanz.

**Grund:** CarenDMR muss ohne USB-Vocoder empfangen können, soll aber
Protokoll, Codec und Wiedergabe getrennt prüfen können. Die austauschbare
Grenze hält einen USB- oder anderen rechtlich freigegebenen Decoder später
möglich und verhindert, dass Empfangsdekodierung versehentlich eine
Sendefähigkeit einführt.

## ADR-0017 – Automatisierte Sendetests nur als verriegelter Parrot-Privatruf

**Status:** beschlossen
**Version:** 0.0.13

Automatisierte Sendetests verwenden niemals öffentliche Gruppen-Talkgroups.
Der einzige zulässige Testpfad ist BrandMeister Parrot als Privatruf an 9990
auf Timeslot 2. Die Sendezeit ist hart auf höchstens 10 Sekunden begrenzt,
die anschließende Echo-Beobachtung auf höchstens 15 Sekunden. Ziel, Ruftyp,
Timeslot und Zeiten dürfen nicht zur Laufzeit konfigurierbar sein. Es gibt
keinen Retry, keine Wiederholung und keinen öffentlichen Fallback.

**Grund:** Automatisierte Diagnosen dürfen unbeteiligte Funkteilnehmer nicht
belasten. Ein privater Echo-Dienst bietet eine klar begrenzte technische
Abnahmefläche und lässt sich vollständig fail-closed verriegeln.

## ADR-0018 – Gemeinsamer Startpunkt für alle Oberflächen

**Status:** beschlossen
**Version:** 0.2.1.84 / 0.2.1.87

Funkkern und Desktop-Zusatzdienste werden ausschließlich in
`carendmr/bootstrap.py` erzeugt und verdrahtet (`build_radio_core`,
`build_desktop_services`). Oberflächen erhalten fertige Objekte.

**Grund:** Vorher bauten Hauptfenster und Easy-Oberfläche den Funkkern jeweils
selbst. Doppelte Verdrahtung kann unbemerkt auseinanderlaufen; ein einziger
Startpunkt hält den Funkpfad in allen Oberflächen identisch und ist
Voraussetzung für weitere Oberflächen (Hardwarebedienung, Android).

## ADR-0019 – Ein Bedienpfad über den OperatingController

**Status:** beschlossen
**Version:** 0.2.1.85 / 0.2.1.86

Jede Oberfläche verbindet, trennt und sendet über den `OperatingController`.
Dessen `RadioStateMachine` ist die einzige Quelle für den Bedienzustand.
Oberflächen starten für den Funkablauf keine eigenen Threads.

**Grund:** Das Hauptfenster führte zuvor eine eigene Zustandsmaschine und eigene
Threads parallel zum Controller der Easy-Oberfläche. Ein gemeinsamer Pfad
verhindert abweichendes Verhalten bei TX, Trennen und Zielwechsel.

## ADR-0020 – Tkinter-Oberfläche entfernt

**Status:** beschlossen
**Version:** 0.2.1.87

Die Tkinter-Oberfläche (`carendmr/ui`, Startoption `--gui-tk`) wurde entfernt.
Qt-Hauptfenster und Easy-Oberfläche sind die unterstützten Oberflächen.

**Grund:** Die Qt-Oberfläche hat den Funktionsumfang vollständig übernommen;
die Tk-Rückfallebene wurde nicht mehr gepflegt und band rund 2.500 Zeilen Code
sowie eigene Tests.

