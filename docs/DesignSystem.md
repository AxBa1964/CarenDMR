# CarenDMR Design System V1

## Ziel

Jedes Element muss auf den ersten Blick erkennen lassen, ob es Information anzeigt, eine Eingabe erwartet, eine Auswahl verändert oder eine Aktion auslöst. Das Designsystem beschreibt deshalb Bedeutung und Verhalten – nicht nur Farben.

## Elementklassen

### Information

Reine Status- und Anzeigeflächen. Sie besitzen keinen Hover-Effekt, keinen Hand-Mauszeiger und keinen Tastaturfokus.

Beispiele: Verbindungsstatus, aktuelle Station, Systeminformationen.

### Eingabe

Helle, klar umrandete Felder mit sichtbarem Cursor. Im gesperrten Zustand werden sie dunkelgrau und zeigen keinen editierbaren Eindruck.

Beispiel: Talkgroup.

### Auswahl

Direkte Wahlschalter mit klar getrenntem aktivem, inaktivem und gesperrtem Zustand.

Beispiele: Timeslot, Rufart.

### Aktion

Erhabene Schaltflächen mit Hover-, Fokus- und gedrücktem Zustand. Grün steht für eine normale Aktion, Rot für eine kritische oder beendende Aktion.

Beispiele: CONNECT, DISCONNECT, PTT.

## Fokus

Der Tastaturfokus wird in allen Tk-Bedienelementen mit einem vier Pixel starken, kontrastreichen Cyan-Rahmen angezeigt. Der Ruhezustand besitzt nur einen dünnen Rahmen.

## Farben

Farben sind semantisch:

- Dunkel: Information
- Hell: Eingabe
- Blau: Auswahl
- Grün: normale Aktion oder erfolgreicher Status
- Rot: kritische Aktion oder Fehler
- Grau: gesperrt

## Entwicklungsregel

Neue UI-Elemente dürfen keine eigenen zufälligen Farben, Rahmen oder Hover-Zustände definieren. Sie verwenden die Konstanten und Hilfsfunktionen aus `carendmr/ui/design_system.py`.
