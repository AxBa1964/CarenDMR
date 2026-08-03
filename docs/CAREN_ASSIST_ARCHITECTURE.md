# Caren Assist – Architekturgrundlage

## Verbindliche Produktregel

Jede betriebsrelevante Funktion und Information besitzt zwei unabhängige Ausgabekanäle:

1. visuell über GUI, Display oder Protokoll,
2. sprachlich über Caren Assist beziehungsweise TTS.

Die Ausgaben müssen nicht inhaltlich identisch sein. Die visuelle Ausgabe darf Details, Tabellen oder Karten zeigen. Die sprachliche Ausgabe muss den Nutzer sicher durch den täglichen Funkbetrieb führen.

## Ziel für blinde OM/YL

Nach abgeschlossener Grundeinrichtung muss der tägliche Betrieb ohne sehende Hilfe möglich sein: Einschalten, Verbindungsaufbau, Talkgroupwahl, Timeslot und Rufart, Senden, Empfangen, QSO-Bestätigung, Zustandsabfrage, verständliche Fehlerbehandlung und sicheres Ausschalten.

## Informationsmanager

Der Informationsmanager ist unabhängig von GUI, DMR-Netzwerk und TTS. Eine Meldung enthält:

- stabilen Ereigniscode,
- kurzen visuellen Text,
- ausführlichen Sprachtext,
- Kategorie,
- Priorität,
- technischen Schweregrad,
- optionalen Handlungshinweis,
- Kennzeichen, ob sie gesprochen werden darf.

Visuelle und sprachliche Empfänger abonnieren getrennte Kanäle. Eine deaktivierte Sprachausgabe darf die visuelle Meldung nicht unterdrücken.

## Fehlerführung

Fehlertexte sollen beantworten:

1. Was ist passiert?
2. Welche Funktion ist betroffen?
3. Was funktioniert weiterhin?
4. Was kann der Nutzer jetzt tun?

Beispiel: „Kein Mikrofon erkannt. Senden ist nicht möglich. Empfang bleibt aktiv. Prüfe die Mikrofonverbindung.“

## Abgrenzung

Der DMR-Kern kennt weder GUI noch TTS. Er oder die Anwendungsschicht erzeugt fachliche Ereignisse. Die Ausgabekanäle entscheiden über Darstellung und Sprachausgabe.
