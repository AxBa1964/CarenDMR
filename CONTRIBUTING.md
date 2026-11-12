# Stand 0.1.1

# Zu CarenDMR beitragen

Danke für das Interesse an CarenDMR. Beiträge müssen das enge Projektziel
respektieren: ein zuverlässiger, barrierefreier BrandMeister-DMR-Client.

## Vor einer Änderung

1. Issue oder geplanten Meilenstein prüfen.
2. Sicherstellen, dass die Änderung ausschließlich DMR/BrandMeister betrifft.
3. Auswirkungen auf Tastatur, VoiceOver/NVDA, Audio und Sendesicherheit
   beschreiben.
4. Bei Codec-, Protokoll- oder Upstream-Code Lizenz und Provenienz klären.

## Entwicklungsumgebung

Die Installationsanleitungen liegen in:

- [INSTALL_MACOS.md](INSTALL_MACOS.md)
- [INSTALL_WINDOWS.md](INSTALL_WINDOWS.md)
- [INSTALL_LINUX.md](INSTALL_LINUX.md)

Tests:

```text
python -m pytest tests
```

Nativer Empfangsdecoder:

```text
make -C native check
```

## Git-Workflow

1. Vom aktuellen `master` einen kurzen Branch anlegen.
2. Nur zusammengehörige Änderungen umsetzen.
3. Tests und Dokumentation gemeinsam mit dem Code aktualisieren.
4. Vor dem Commit `git status` und den vollständigen Diff prüfen.
5. Einen knappen, sachlichen Commit erstellen.
6. Einen Draft Pull Request gegen `master` öffnen.

Lokale Konfigurationen, Logs, ZIP-Dateien, virtuelle Umgebungen und native
Build-Artefakte dürfen nicht committed werden.

## Qualitätsregeln

- Keine neue Funktion ohne passende automatisierte Tests.
- Keine Information ausschließlich visuell darstellen.
- Fehler erklären Ursache, Auswirkung und nächste Handlung.
- Geheimnisse niemals loggen, ansagen oder in Testdaten einbauen.
- Netzwerkparser und öffentliche Eingaben strikt validieren.
- Sendefunktionen standardmäßig verweigern, solange Ziel, Ruftyp und Grenzen
  nicht beweisbar sicher sind.
- Keine automatische Aussendung auf öffentlichen Talkgroups.

Die vollständige Definition of Done für Bedienoberflächen steht in
[ACCESSIBILITY_REQUIREMENTS.md](docs/ACCESSIBILITY_REQUIREMENTS.md).

## Sprache und Stil

- Python-Code soll klein, typisiert, testbar und ohne unnötige Abhängigkeiten
  bleiben.
- Benutzertexte sind verständlich und vermeiden Protokolljargon.
- Dokumentation wird auf Deutsch gepflegt; englische Fachbegriffe sind dort
  erlaubt, wo sie im Protokoll oder Quellcode feststehen.
- Bestehende Architekturentscheidungen in `docs/DECISIONS.md` nicht
  stillschweigend umgehen.

## Lizenz

Mit einem Beitrag erklärst du dich damit einverstanden, ihn unter
GPL-3.0-or-later bereitzustellen. Fremdcode darf nur mit kompatibler Lizenz,
erhaltenen Hinweisen und dokumentierter Herkunft aufgenommen werden.
