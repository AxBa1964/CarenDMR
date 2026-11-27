"""Barrierefreie HTML-Bausteine der Box-Web-App (ADR-0014).

Schlichtes, semantisches HTML: Überschriften, beschriftete Felder, Fehler als
Text am Anfang, ohne Maus bedienbar, funktioniert ohne JavaScript. Kein
externes CSS oder Skript.
"""
from __future__ import annotations

from html import escape

_STYLE = """
:root { color-scheme: light dark; }
* { box-sizing: border-box; }
body { font-family: system-ui, sans-serif; line-height: 1.5; margin: 0;
       padding: 1rem; max-width: 42rem; margin-inline: auto; }
h1 { font-size: 1.5rem; }
nav a { margin-right: 1rem; }
form { margin-top: 1rem; }
label { display: block; margin-top: 1rem; font-weight: bold; }
input[type=text], input[type=number], input[type=password] {
    width: 100%; padding: 0.5rem; font-size: 1rem; margin-top: 0.25rem; }
.hint { font-weight: normal; color: GrayText; }
button { margin-top: 1.25rem; padding: 0.6rem 1.2rem; font-size: 1rem; }
.error { border: 2px solid #b00020; background: #fdecea; color: #611a15;
         padding: 0.75rem; margin-top: 1rem; }
.ok { border: 2px solid #1b5e20; background: #e7f4e4; color: #14341a;
      padding: 0.75rem; margin-top: 1rem; }
dl { margin-top: 1rem; }
dt { font-weight: bold; margin-top: 0.75rem; }
@media (prefers-color-scheme: dark) {
  .error { background: #3b1513; color: #f8d7d5; }
  .ok { background: #16311a; color: #d6f0d2; }
}
""".strip()


def page(title: str, body: str, *, nav: bool = True) -> str:
    """Rahmen einer Seite. ``title`` erscheint als Titel und als erste H1."""
    navigation = (
        '<nav aria-label="Hauptmenü"><a href="/">Übersicht</a>'
        '<a href="/station">DMR-Station</a>'
        '<a href="/abmelden">Abmelden</a></nav>'
        if nav else ""
    )
    return (
        "<!doctype html>\n"
        '<html lang="de">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"<title>{escape(title)} – CarenDMR-Box</title>\n"
        f"<style>{_STYLE}</style>\n</head>\n<body>\n"
        f"{navigation}\n<main>\n<h1>{escape(title)}</h1>\n{body}\n</main>\n</body>\n</html>\n"
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
