"""Barrierefreie HTML-Bausteine der Box-Web-App (ADR-0014).

Schlichtes, semantisches HTML: Überschriften, beschriftete Felder, Fehler als
Text am Anfang, ohne Maus bedienbar, funktioniert ohne JavaScript. Kein
externes CSS oder Skript.
"""
from __future__ import annotations

from html import escape

_STYLE = """
:root{
  color-scheme: light dark;
  --bg:#eef1f5; --card:#ffffff; --text:#1a2230; --muted:#5b6676;
  --accent:#0d7d74; --accent-text:#ffffff; --border:#d4dae2;
  --error-bg:#fdecea; --error-bd:#b3261e; --error-tx:#611a15;
  --ok-bg:#e7f4e4; --ok-bd:#1b7a32; --ok-tx:#14341a;
  --radius:12px; --shadow:0 1px 3px rgba(16,24,40,.09),0 1px 2px rgba(16,24,40,.06);
}
@media (prefers-color-scheme: dark){
  :root{
    --bg:#0f1621; --card:#17202c; --text:#e7edf4; --muted:#9aa7b6;
    --accent:#2bb3a6; --accent-text:#07221f; --border:#2a3745;
    --error-bg:#3b1513; --error-bd:#e06a63; --error-tx:#f8d7d5;
    --ok-bg:#16311a; --ok-bd:#4fae5e; --ok-tx:#d6f0d2;
  }
}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;line-height:1.55;
  margin:0;background:var(--bg);color:var(--text);padding:0 16px 48px}
a{color:var(--accent)}
.topbar{display:flex;align-items:center;gap:10px;max-width:44rem;margin:0 auto;padding:18px 0 10px}
.brand{display:flex;align-items:center;gap:10px;font-weight:700;font-size:1.15rem;color:var(--text)}
.brand svg{width:28px;height:28px;flex:none;color:var(--accent)}
nav{display:flex;flex-wrap:wrap;gap:6px;max-width:44rem;margin:0 auto;
  padding:6px 0 10px;border-bottom:1px solid var(--border)}
nav a{display:inline-block;padding:8px 13px;border-radius:999px;text-decoration:none;
  color:var(--text);background:transparent}
nav a:hover{background:rgba(13,125,116,.12)}
main{max-width:44rem;margin:18px auto 0;background:var(--card);border:1px solid var(--border);
  border-radius:var(--radius);box-shadow:var(--shadow);padding:24px 26px}
h1{font-size:1.6rem;margin:0 0 .4rem}
h2{font-size:1.2rem;margin:1.6rem 0 .25rem;padding-top:1.1rem;border-top:1px solid var(--border)}
h2:first-of-type{border-top:0;padding-top:.25rem}
label{display:block;margin-top:1rem;font-weight:600}
.hint{font-weight:400;color:var(--muted)}
input[type=text],input[type=number],input[type=password],select,textarea{
  width:100%;padding:.6rem .7rem;font-size:1rem;margin-top:.35rem;
  border:1px solid var(--border);border-radius:8px;background:var(--card);color:var(--text)}
textarea{resize:vertical}
input:focus-visible,select:focus-visible,textarea:focus-visible,
button:focus-visible,a:focus-visible{outline:3px solid var(--accent);outline-offset:2px}
button{margin-top:1.25rem;margin-right:.5rem;padding:.65rem 1.25rem;font-size:1rem;font-weight:600;
  color:var(--accent-text);background:var(--accent);border:1px solid transparent;
  border-radius:8px;cursor:pointer}
button:hover{filter:brightness(1.08)}
form{margin-top:.5rem}
dl{margin-top:1rem;display:grid;grid-template-columns:auto 1fr;gap:.4rem 1.25rem}
dt{font-weight:700;color:var(--muted)}
dd{margin:0}
ol,ul{padding-left:1.3rem}
li{margin:.55rem 0}
.error{border:1px solid var(--error-bd);background:var(--error-bg);color:var(--error-tx);
  padding:.75rem 1rem;border-radius:8px;margin-top:1rem}
.ok{border:1px solid var(--ok-bd);background:var(--ok-bg);color:var(--ok-tx);
  padding:.75rem 1rem;border-radius:8px;margin-top:1rem}
@media (max-width:30rem){main{padding:18px 16px}}
""".strip()

_BRAND_ICON = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
    'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">'
    '<circle cx="12" cy="14" r="3"></circle>'
    '<path d="M7.8 9.8a6 6 0 0 1 8.4 0"></path>'
    '<path d="M5 7a9 9 0 0 1 14 0"></path></svg>'
)


def page(title: str, body: str, *, nav: bool = True) -> str:
    """Rahmen einer Seite. ``title`` erscheint als Titel und als erste H1."""
    header = f'<header class="topbar"><span class="brand">{_BRAND_ICON}CarenDMR-Box</span></header>'
    navigation = (
        '<nav aria-label="Hauptmenü"><a href="/">Übersicht</a>'
        '<a href="/station">DMR-Station</a>'
        '<a href="/talkgroups">Talkgroups</a>'
        '<a href="/audio">Audio</a>'
        '<a href="/fm">FM-Funknetz</a>'
        '<a href="/einrichtung">Einrichtung</a>'
        '<a href="/system">System</a>'
        '<a href="/abmelden">Abmelden</a></nav>'
        if nav else ""
    )
    return (
        "<!doctype html>\n"
        '<html lang="de">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"<title>{escape(title)} – CarenDMR-Box</title>\n"
        f"<style>{_STYLE}</style>\n</head>\n<body>\n"
        f"{header}\n{navigation}\n<main>\n<h1>{escape(title)}</h1>\n{body}\n</main>\n</body>\n</html>\n"
    )


def error_box(message: str) -> str:
    if not message:
        return ""
    return f'<p class="error" role="alert">{escape(message)}</p>'


def ok_box(message: str) -> str:
    if not message:
        return ""
    return f'<p class="ok" role="status">{escape(message)}</p>'


def _field(
    name: str, label: str, value: str = "", *, kind: str = "text",
    hint: str = "", required: bool = False, inputmode: str = "",
) -> str:
    attrs = f'type="{kind}" id="{name}" name="{escape(name)}" value="{escape(value)}"'
    if required:
        attrs += " required"
    if inputmode:
        attrs += f' inputmode="{inputmode}"'
    if kind == "password":
        attrs += ' autocomplete="new-password"'
    hint_html = f' <span class="hint">{escape(hint)}</span>' if hint else ""
    return (
        f'<label for="{name}">{escape(label)}{hint_html}</label>\n'
        f"<input {attrs}>"
    )


def login_page(csrf: str, error: str = "", *, first_time: bool = False) -> str:
    if first_time:
        intro = (
            "<p>Beim ersten Start legen Sie das Verwaltungskennwort fest. "
            "Damit schützen Sie die Einstellungen der Box.</p>"
        )
        button, title = "Kennwort festlegen", "Erststart"
        extra = _field("password2", "Kennwort wiederholen", kind="password", required=True)
    else:
        intro = "<p>Bitte mit dem Verwaltungskennwort anmelden.</p>"
        button, title = "Anmelden", "Anmelden"
        extra = ""
    body = (
        error_box(error) + intro
        + '<form method="post" action="/anmelden">\n'
        + f'<input type="hidden" name="csrf" value="{escape(csrf)}">\n'
        + f'<input type="hidden" name="first_time" value="{"1" if first_time else "0"}">\n'
        + _field("password", "Verwaltungskennwort", kind="password", required=True)
        + ("\n" + extra if extra else "")
        + f'\n<button type="submit">{button}</button>\n</form>'
    )
    return page(title, body, nav=False)


def overview_page(items: list[tuple[str, str]], *, message: str = "") -> str:
    rows = "\n".join(
        f"<dt>{escape(label)}</dt><dd>{escape(value)}</dd>" for label, value in items
    )
    body = ok_box(message) + f"<dl>\n{rows}\n</dl>"
    return page("Übersicht", body)


def station_page(
    values: dict, csrf: str, *, error: str = "", message: str = "", password_set: bool = False
) -> str:
    pw_hint = "gesetzt – leer lassen, um es zu behalten" if password_set else "noch nicht gesetzt"
    body = (
        error_box(error) + ok_box(message)
        + '<form method="post" action="/station">\n'
        + f'<input type="hidden" name="csrf" value="{escape(csrf)}">\n'
        + _field("callsign", "Rufzeichen", str(values.get("callsign", "")), required=True)
        + "\n" + _field("dmr_id", "DMR-ID", str(values.get("dmr_id", "") or ""),
                        kind="number", required=True, inputmode="numeric")
        + "\n" + _field("password", "Hotspot-Passwort (BrandMeister)", kind="password", hint=pw_hint)
        + "\n" + _field("location", "Standort (Locator)", str(values.get("location", "")),
                        hint="z. B. JO52")
        + "\n" + _field("host", "Server", str(values.get("host", "")))
        + "\n" + _field("port", "Port", str(values.get("port", "")),
                        kind="number", inputmode="numeric")
        + '\n<button type="submit" name="aktion" value="speichern">Speichern</button>\n'
        + '<button type="submit" name="aktion" value="test">Verbindung testen</button>\n'
        + "</form>"
    )
    return page("DMR-Station", body)


def _hidden(csrf: str, network: str) -> str:
    return (
        f'<input type="hidden" name="csrf" value="{escape(csrf)}">'
        f'<input type="hidden" name="netz" value="{escape(network)}">'
    )


def favorites_page(
    network: str, favorites, hotlist, csrf: str, *, error: str = "", message: str = ""
) -> str:
    net_label = "DMR" if network == "dmr" else "FM-Funknetz"
    other = "fm" if network == "dmr" else "dmr"
    other_label = "FM-Funknetz" if network == "dmr" else "DMR"
    is_dmr = network == "dmr"

    switch = (
        f'<p>Netz: <strong>{escape(net_label)}</strong> · '
        f'<a href="/talkgroups?netz={other}">zu {escape(other_label)} wechseln</a></p>'
    )

    # Hotliste 1–4
    slot_options = "".join(
        f'<option value="{i}">{escape(fav.label())}</option>'
        for i, fav in enumerate(favorites)
    )
    slot_rows = []
    for slot in range(1, 5):
        current = hotlist[slot - 1] if slot - 1 < len(hotlist) else None
        belegt = current.label() if current else "frei"
        assign = (
            f'<form method="post" action="/talkgroups" style="display:inline">'
            f'{_hidden(csrf, network)}'
            f'<input type="hidden" name="slot" value="{slot}">'
            f'<label for="fav{slot}">Favorit für Platz {slot}</label>'
            f'<select id="fav{slot}" name="favorite">{slot_options}</select> '
            f'<button type="submit" name="aktion" value="assign">auf Platz {slot}</button>'
            f'</form>'
        ) if favorites else "<p class=\"hint\">Erst Favoriten anlegen.</p>"
        clear = (
            f'<form method="post" action="/talkgroups" style="display:inline">'
            f'{_hidden(csrf, network)}'
            f'<input type="hidden" name="slot" value="{slot}">'
            f'<button type="submit" name="aktion" value="clear_slot">Platz {slot} leeren</button>'
            f'</form>'
        ) if current else ""
        slot_rows.append(f"<li>Platz {slot}: <strong>{escape(belegt)}</strong><br>{assign} {clear}</li>")
    hotlist_html = "<h2>Hotliste (Tasten 1–4)</h2>\n<ul>\n" + "\n".join(slot_rows) + "\n</ul>"

    # Favoritenliste
    rows = []
    for index, fav in enumerate(favorites):
        buttons = (
            f'<form method="post" action="/talkgroups" style="display:inline">{_hidden(csrf, network)}'
            f'<input type="hidden" name="index" value="{index}">'
            f'<button type="submit" name="aktion" value="up">nach oben</button>'
            f'<button type="submit" name="aktion" value="down">nach unten</button>'
            f'<button type="submit" name="aktion" value="remove">entfernen</button></form>'
        )
        detail = f" · TS{fav.timeslot} · {'privat' if fav.call_type=='private' else 'Gruppe'}" if is_dmr else ""
        rows.append(f"<li>{escape(fav.label())}{detail}<br>{buttons}</li>")
    list_html = (
        "<h2>Favoritenliste</h2>\n<ol>\n" + "\n".join(rows) + "\n</ol>"
        if favorites else "<h2>Favoritenliste</h2>\n<p class=\"hint\">Noch keine Favoriten.</p>"
    )

    # Hinzufügen
    dmr_fields = (
        '<label for="timeslot">Zeitschlitz</label>'
        '<select id="timeslot" name="timeslot"><option value="2">2</option><option value="1">1</option></select>'
        '<label for="call_type">Rufart</label>'
        '<select id="call_type" name="call_type">'
        '<option value="group">Gruppe</option><option value="private">privat</option></select>'
    ) if is_dmr else ""
    add_html = (
        "<h2>Favorit hinzufügen</h2>\n"
        f'<form method="post" action="/talkgroups">{_hidden(csrf, network)}'
        + _field("name", "Name", hint="z. B. Deutschland")
        + "\n" + _field("talkgroup", "Talkgroup", kind="number", required=True, inputmode="numeric")
        + "\n" + dmr_fields
        + '\n<button type="submit" name="aktion" value="add">Hinzufügen</button></form>'
    )

    # Import/Export
    io_html = (
        "<h2>Sichern und laden</h2>\n"
        f'<p><a href="/talkgroups?netz={network}&export=1">Favoriten als Datei speichern (Export)</a></p>\n'
        f'<form method="post" action="/talkgroups">{_hidden(csrf, network)}'
        '<label for="import_text">Favoriten einfügen (JSON)</label>'
        '<textarea id="import_text" name="import_text" rows="5" style="width:100%"></textarea>'
        '<label><input type="checkbox" name="replace" value="1"> bestehende Liste ersetzen</label>'
        '<button type="submit" name="aktion" value="import">Laden</button></form>'
    )

    body = error_box(error) + ok_box(message) + switch + hotlist_html + list_html + add_html + io_html
    return page(f"Talkgroups {net_label}", body)


def audio_page(
    inputs, outputs, current_input, current_output, volume: int, gain: int, csrf: str,
    *, error: str = "", message: str = "", devices_available: bool = True,
) -> str:
    def options(choices, selected) -> str:
        return "".join(
            f'<option value="{escape(c.key)}"{" selected" if c.key == selected else ""}>'
            f"{escape(c.label)}</option>"
            for c in choices
        )

    if devices_available and (inputs or outputs):
        devices = (
            '<form method="post" action="/audio">'
            + f'<input type="hidden" name="csrf" value="{escape(csrf)}">'
            + '<label for="input">Mikrofon</label>'
            + f'<select id="input" name="input">{options(inputs, current_input)}</select>'
            + '<label for="output">Lautsprecher</label>'
            + f'<select id="output" name="output">{options(outputs, current_output)}</select>'
            + '<button type="submit" name="aktion" value="save_devices">Geräte speichern</button>'
            + '<button type="submit" name="aktion" value="test">Probeton</button></form>'
        )
    else:
        devices = (
            '<p class="hint">Keine Audiogeräte gefunden. Die Geräteauswahl steht erst '
            "zur Verfügung, wenn eine USB-Soundkarte angeschlossen ist (auf dem Pi).</p>"
        )

    volume_form = (
        "<h2>Lautstärke und Mikrofon</h2>\n"
        f'<form method="post" action="/audio">'
        f'<input type="hidden" name="csrf" value="{escape(csrf)}">'
        + _field("volume", "Empfangslautstärke (Prozent)", str(volume), kind="number",
                 inputmode="numeric", hint="0–400")
        + "\n" + _field("gain", "Mikrofonpegel (Prozent)", str(gain), kind="number",
                        inputmode="numeric", hint="0–400")
        + '\n<button type="submit" name="aktion" value="save_levels">Speichern</button></form>'
    )

    body = (
        error_box(error) + ok_box(message)
        + "<h2>Geräte</h2>\n" + devices + "\n" + volume_form
    )
    return page("Audio", body)


def fm_page(values: dict, csrf: str, *, error: str = "", message: str = "", key_set: bool = False) -> str:
    key_hint = "gesetzt – leer lassen, um ihn zu behalten" if key_set else "noch nicht gesetzt"
    body = (
        error_box(error) + ok_box(message)
        + '<p>Zugang zum FM-Funknetz (SvxLink-Reflektor). Für die Box gilt das '
        + 'Rufzeichen <strong>DK7EE-TRX</strong>.</p>'
        + '<form method="post" action="/fm">'
        + f'<input type="hidden" name="csrf" value="{escape(csrf)}">'
        + _field("callsign", "Rufzeichen", str(values.get("callsign", "")), required=True,
                 hint="z. B. DK7EE-TRX")
        + "\n" + _field("auth_key", "Key", kind="password", hint=key_hint)
        + "\n" + _field("software_name", "Software-Kennung", str(values.get("software_name", "")),
                        hint="Vorgabe CarenFM")
        + "\n" + _field("host", "Server", str(values.get("host", "")))
        + "\n" + _field("port", "Port", str(values.get("port", "")), kind="number", inputmode="numeric")
        + "\n" + _field("talkgroup", "Start-Talkgroup", str(values.get("talkgroup", "")),
                        kind="number", inputmode="numeric", hint="z. B. 20 (Testarea)")
        + '\n<button type="submit" name="aktion" value="speichern">Speichern</button>'
        + '<button type="submit" name="aktion" value="test">Verbindung testen</button></form>'
    )
    return page("FM-Funknetz", body)


def system_page(csrf: str, *, error: str = "", message: str = "") -> str:
    body = (
        error_box(error) + ok_box(message)
        + "<h2>Verwaltungskennwort ändern</h2>\n"
        + f'<form method="post" action="/system"><input type="hidden" name="csrf" value="{escape(csrf)}">'
        + _field("old", "Aktuelles Kennwort", kind="password", required=True)
        + "\n" + _field("new1", "Neues Kennwort", kind="password", required=True)
        + "\n" + _field("new2", "Neues Kennwort wiederholen", kind="password", required=True)
        + '\n<button type="submit" name="aktion" value="change_password">Kennwort ändern</button></form>'
        + "\n<h2>Sicherung</h2>\n"
        + '<p><a href="/system?backup=1">Einstellungen als Datei speichern</a> '
        + '(Favoriten, Station, FM und Audio – ohne Kennwörter und Key).</p>'
        + "\n<h2>Box</h2>\n"
        + f'<form method="post" action="/system" style="display:inline"><input type="hidden" name="csrf" value="{escape(csrf)}">'
        + '<button type="submit" name="aktion" value="reboot">Box neu starten</button></form>\n'
        + f'<form method="post" action="/system" style="display:inline"><input type="hidden" name="csrf" value="{escape(csrf)}">'
        + '<button type="submit" name="aktion" value="shutdown">Box herunterfahren</button></form>'
        + '\n<p class="hint">Neustart und Herunterfahren wirken nur auf der Box (Raspberry Pi).</p>'
    )
    return page("System", body)


def assistant_page(steps: list[tuple[str, str, bool]]) -> str:
    """steps: (Titel, Link, erledigt)."""
    total = len(steps)
    done = sum(1 for _, _, ok in steps if ok)
    items = []
    for number, (title, link, ok) in enumerate(steps, start=1):
        status = "erledigt" if ok else "offen"
        items.append(
            f'<li>Schritt {number} von {total}: <a href="{escape(link)}">{escape(title)}</a> '
            f"– <strong>{status}</strong></li>"
        )
    body = (
        f"<p>Diese Liste führt durch die Einrichtung. {done} von {total} Schritten erledigt. "
        "Sie können jederzeit aufhören und später hier weitermachen.</p>\n"
        + "<ol>\n" + "\n".join(items) + "\n</ol>\n"
        + '<p><a href="/">Zur Übersicht (abbrechen)</a></p>'
    )
    return page("Einrichtung", body)
