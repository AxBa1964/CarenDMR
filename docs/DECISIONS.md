# CarenDMR – Architekturentscheidungen

## ADR-001: Eigenständiges Projekt

**Entscheidung:** CarenDMR bleibt vollständig von SmartHomeLab und
CarenPDFText getrennt.

**Begründung:** Die Projekte haben unterschiedliche Nutzer, Laufzeiten,
Abhängigkeiten, Sicherheitsanforderungen und Entwicklungsziele.

## ADR-002: Nur BrandMeister-DMR

**Entscheidung:** CarenDMR unterstützt ausschließlich DMR über
BrandMeister.

**Begründung:** Weitere digitale Betriebsarten erhöhen Komplexität und
erschweren die barrierefreie Bedienung, ohne Carens konkreten Anwendungsfall
zu verbessern.

## ADR-003: DroidStar nur als technische Referenz

**Entscheidung:** CarenDMR übernimmt DroidStar nicht als eingebettetes
Gesamtprogramm und kopiert keine Qt-Oberfläche.

**Begründung:** DroidStar ist eine Mehrprotokoll-Anwendung. CarenDMR benötigt
nur einen kleinen Teil der Architektur. Die relevanten Abläufe werden sauber
neu implementiert.

## ADR-004: Keine allgemeine Mode-Basisklasse

**Entscheidung:** Es wird keine generische Abstraktion für DMR, D-Star, YSF,
P25 oder andere Modi gebaut.

**Begründung:** Eine solche Abstraktion hätte für CarenDMR keinen praktischen
Nutzen und würde das Projekt unnötig vergrößern.

## ADR-005: Netzwerk, DMR-Rahmen, Vocoder und Audio trennen

**Entscheidung:** Diese vier Bereiche erhalten getrennte Schnittstellen.

**Begründung:** Der Vocoder kann sich aus technischen oder rechtlichen
Gründen ändern. Audio- und Netzwerklogik müssen unabhängig testbar bleiben.

## ADR-006: Barrierefreiheit ist Kernfunktion

**Entscheidung:** Sprachausgabe, Tastaturbedienung und verständliche
Statusmeldungen werden nicht nachträglich ergänzt, sondern gehören zur
Grundarchitektur.

**Begründung:** Caren ist die Hauptnutzerin. Eine rein visuelle Oberfläche
würde das Projektziel verfehlen.

## ADR-007: Erst Audio, dann Netzwerk

**Entscheidung:** Vor der BrandMeister-Anbindung werden Mikrofon,
Lautsprecher und lokale Audioverarbeitung geprüft.

**Begründung:** Audiofehler und Netzwerkfehler müssen getrennt diagnostiziert
werden können.

## ADR-008: Keine inoffizielle Vocoder-Datei im Repository

**Entscheidung:** Vocoder-Binärdateien werden nicht in Git oder in normale
Release-ZIPs aufgenommen.

**Begründung:** Herkunft, Lizenz und Plattformabhängigkeit müssen separat
behandelt werden.
