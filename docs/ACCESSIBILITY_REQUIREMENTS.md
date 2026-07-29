# Verbindliche Anforderungen an die barrierefreie Bedienoberfläche

**Status:** verbindliche Produktanforderung
**Primäre Abnahmeplattform:** macOS mit VoiceOver
**Gültigkeit:** für jede zukünftige CarenDMR-Bedienoberfläche

## 1. Produktgrundsatz

CarenDMR ist nach einer blinden Person benannt und wird für eine blinde
Nutzerin entwickelt. Vollständige Bedienbarkeit mit VoiceOver ist deshalb
kein Zusatzmerkmal und keine spätere Optimierung, sondern eine
Abnahmebedingung für jede Benutzeroberfläche.

Eine Funktion gilt erst als fertig, wenn sie ohne Maus, ohne Sehen des
Bildschirms und ohne Interpretation rein visueller Hinweise verständlich,
bedienbar und überprüfbar ist.

## 2. Semantik und Tastaturbedienung

- Jedes interaktive Element muss vollständig per Tastatur erreichbar und
  bedienbar sein.
- Jedes Element benötigt eine eindeutige semantische Rolle, einen kurzen
  zugänglichen Namen und, falls nötig, eine verständliche Beschreibung.
- Beschriftungen müssen Zweck und Wirkung erklären; technische Abkürzungen
  allein reichen nicht aus.
- Zustände wie ausgewählt, gedrückt, deaktiviert, verbunden oder sendend
  müssen dem Accessibility-Framework semantisch gemeldet werden.
- Tastenkürzel ergänzen die normale Fokusbedienung, ersetzen sie aber nicht.
- Die Fokusreihenfolge muss stabil, logisch und vorhersehbar sein.
- Nach Aktionen, Dialogen und Fehlern muss der Fokus an einer sinnvollen,
  dokumentierten Stelle verbleiben oder dorthin zurückkehren.

## 3. Informationen dürfen nicht nur visuell sein

Keine relevante Information darf ausschließlich durch Farbe, Position,
Animation, Symbolform, Pegelanzeige oder Wellenform vermittelt werden.

Insbesondere benötigen:

- Verbindungszustände,
- Empfang und Senden,
- aktive Talkgroup und Timeslot,
- Audioaktivität,
- Fehler, Warnungen und deaktivierte Funktionen

immer eine gleichwertige textliche und für VoiceOver zugängliche Darstellung.

Eine spätere Wellenform oder Farbanzeige darf nur eine zusätzliche visuelle
Darstellung sein. Sie ist niemals die einzige Quelle für Inhalt oder Zustand.

## 4. Aktueller Zustand

Die Oberfläche muss eine kompakte, jederzeit gezielt erreichbare
Zustandszusammenfassung anbieten. In stabiler Reihenfolge beschreibt sie:

1. Verbindung: getrennt, verbindet, verbunden oder Fehler,
2. aktive Talkgroup und Timeslot,
3. Betriebsart: bereit, empfängt oder sendet,
4. aktuelle Aktivität, beispielsweise wer oder welche Gruppe gerade
   empfangen wird, soweit diese Information zuverlässig vorliegt.

Beispielstruktur:

```text
Verbunden. Talkgroup 91, Timeslot 2. Empfang. Aktuell Sprachaktivität.
```

Fehlende oder unbekannte Werte werden ausdrücklich als unbekannt bezeichnet
und nicht stillschweigend ausgelassen.

## 5. Live-Ankündigungen

Wichtige Zustandsänderungen müssen über geeignete Live-Regionen beziehungsweise
native Accessibility-Benachrichtigungen angekündigt werden:

- Verbindung hergestellt oder getrennt,
- Empfang beginnt oder endet,
- Senden beginnt oder endet,
- aktive Talkgroup oder Timeslot ändert sich,
- ein Fehler verhindert die gewünschte Aktion.

Ankündigungen müssen kurz, eindeutig und priorisiert sein. Identische
Wiederholungen, laufende Paketmeldungen und schnell wechselnde technische
Zwischenzustände werden zusammengefasst oder unterdrückt, damit VoiceOver
nicht übermäßig spricht und wichtige Meldungen nicht verdrängt werden.

Die gezielt abrufbare Zustandszusammenfassung bleibt von Live-Ankündigungen
getrennt: Sie liefert auf Wunsch den vollständigen aktuellen Kontext, ohne
jede Einzeländerung ungefragt vorzulesen.

## 6. Zugängliches Gesprächs- und Ereignisprotokoll

Die Oberfläche benötigt ein textuelles, per Tastatur und VoiceOver lesbares
Gesprächs-/Ereignisprotokoll.

Jeder Eintrag enthält, soweit sinnvoll:

- verständliche Zeitangabe,
- Ereignisart,
- Talkgroup und Timeslot,
- Empfangs- oder Senderichtung,
- kurze Aktivitäts- oder Statusbeschreibung.

Das Protokoll:

- verwendet echte Text- und Listen-Semantik,
- besitzt eine vorhersehbare Lesereihenfolge,
- kann ohne Maus durchsucht und durchlaufen werden,
- verschiebt den aktuellen Fokus nicht automatisch,
- kündigt neue Einträge nicht ungefiltert vollständig an,
- enthält keine Passwörter, Zugangsdaten oder unnötigen Paket-Rohdaten.

## 7. Fehler und nächste Schritte

Fehlermeldungen müssen nicht-visuell vollständig verständlich sein und drei
Fragen beantworten:

1. Was ist fehlgeschlagen?
2. Welche Auswirkung hat das?
3. Was kann die Nutzerin als Nächstes tun?

Der Fehlertext darf sich nicht nur auf Farbe, Position, Symbol oder
Protokollcode beziehen. Die zugehörige Aktion, beispielsweise
„Erneut verbinden“, „Audioausgabe auswählen“ oder „Dialog schließen“, muss
eindeutig beschriftet und per Tastatur erreichbar sein.

## 8. Getrennter Bereich „Einrichtung und Verbindung“

Persönliche Identitäts- und Verbindungsdaten gehören in einen separaten,
eindeutig benannten Bereich „Einrichtung und Verbindung“ beziehungsweise
„Konfiguration“. Sie dürfen nicht die normale Betriebsansicht überladen.

Dieser Bereich umfasst insbesondere:

- Rufzeichen,
- DMR-ID,
- BrandMeister-Zugangsdaten beziehungsweise Security-/Hotspot-Passwort,
- Serverauswahl,
- weitere persönliche Stations- und Verbindungseinstellungen.

Für diesen Bereich gelten zusätzlich:

- Alle Felder, Gruppen, Hinweise und Aktionen besitzen eindeutige semantische
  Namen und sind vollständig per Tastatur und VoiceOver bedienbar.
- Geheimnisse werden maskiert und niemals ungefragt vorgelesen, in
  Statusmeldungen wiederholt oder in das Ereignisprotokoll geschrieben.
- Eine bewusste Aktion zum Anzeigen eines Geheimnisses darf nur mit klarer
  Beschriftung, eindeutigem Zustand und vorheriger Sicherheitswarnung
  vorgesehen werden.
- „Speichern“ und „Verbindung testen“ sind getrennte, eindeutig benannte
  Aktionen; ein Test darf nicht stillschweigend andere Werte speichern.
- Nach Speichern oder Testen wird das Ergebnis in einfacher Sprache
  beschrieben: erfolgreich, noch nicht gespeichert, ungültige Eingabe oder
  Verbindung fehlgeschlagen.
- Fehlermeldungen nennen das betroffene Feld oder den Verbindungsschritt,
  verraten aber niemals den geheimen Inhalt.
- Beim Verlassen mit ungespeicherten Änderungen erfolgt eine verständliche,
  per Tastatur bedienbare Entscheidung zum Speichern, Verwerfen oder
  Zurückkehren.

Die normale Betriebsansicht zeigt nur den für den Betrieb erforderlichen
Verbindungszustand. Sie zeigt keine Passwörter und wiederholt Rufzeichen,
DMR-ID, Server oder persönliche Stationsdaten nicht dauerhaft.

## 9. Abnahme

Jeder UI-Meilenstein wird mindestens mit folgenden Prüfungen abgenommen:

- vollständiger Ablauf nur mit Tastatur,
- vollständiger Ablauf mit aktiviertem VoiceOver und ausgeschaltetem
  Bildschirm beziehungsweise ohne visuelle Orientierung,
- Kontrolle von Rollen, Namen, Zuständen und Fokusreihenfolge,
- Prüfung der Zustandszusammenfassung,
- Prüfung wichtiger und unterdrückter Live-Ankündigungen,
- Lesen und Navigieren des Ereignisprotokolls,
- Fehlerablauf einschließlich verständlicher nächster Aktion.

Automatisierte Tests sollen Zustandsformatierung, Fokusregeln und
Ankündigungsunterdrückung absichern. Die praktische VoiceOver-Prüfung bleibt
zusätzlich verpflichtend.

## 10. Empfohlener erster UI-Meilenstein

Der erste UI-Meilenstein soll ein nicht-sendendes, nur lesendes
VoiceOver-Grundfenster sein:

- semantisch benannter Verbindungsstatus,
- kompakte Zustandszusammenfassung mit TG91 und Timeslot 2,
- klarer Bereich „Aktuelle Aktivität“,
- textuelles Ereignisprotokoll,
- genau eine sicher bedienbare Aktion zum Verbinden beziehungsweise Trennen,
- definierte Fokusreihenfolge und wenige priorisierte Live-Ankündigungen.

PTT, Audioübertragung, Wellenformen, visuelle Pegel und komplexe Einstellungen
bleiben aus diesem ersten UI-Meilenstein ausgeschlossen. So kann die
Accessibility-Architektur mit VoiceOver praktisch abgenommen werden, bevor
zeitkritische Sendefunktionen hinzukommen.

Der getrennte Bereich „Einrichtung und Verbindung“ folgt als eigener
UI-Meilenstein nach dem read-only Grundfenster. Dadurch werden normaler
Betrieb und sensible Konfiguration von Beginn an strukturell getrennt.

## 11. Zugängliche Testphasen

Ein zukünftiger verriegelter BrandMeister-Parrot-Test kündigt lokal und
verständlich Start, stumme Übertragungsphase, Echo-Empfang, Erfolg, sicheren
Abbruch und Timeout an. Die Ansagen vermeiden persönliche Daten und unnötige
technische Details. Zurückkehrendes Echo wird über die normale lokale
Audioausgabe hörbar.

Das Ein-/Ausschalten dieser Ansagen gehört in den zugänglichen Setup-Bereich,
nicht in die normale Betriebsansicht. Es darf Ziel, Route, Timeslot oder
Zeitgrenzen des verriegelten Tests nicht verändern.
