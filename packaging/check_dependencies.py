"""Prüft, ob im gebauten Programmordner alle DLL-Abhängigkeiten vorhanden sind.

Aufruf (durch build_release.ps1):
    python packaging/check_dependencies.py <Programmordner> <objdump.exe>

Untersucht alle .dll/.pyd/.exe mit ``objdump -p`` und meldet importierte
DLLs, die weder im Programmordner liegen noch zu Windows gehören. Grund:
Der Bauplan lässt nicht benötigte Qt-Teile weg; fehlt dadurch doch etwas,
soll der Build sofort scheitern statt erst beim Nutzer.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

# Diese Namen stammen aus Windows selbst und liegen nie im Programmordner.
_SYSTEM_PREFIXES = ("api-ms-win-", "ext-ms-")
_SYSTEM_NAMES = {
    "kernel32.dll", "user32.dll", "gdi32.dll", "advapi32.dll", "shell32.dll",
    "ole32.dll", "oleaut32.dll", "ws2_32.dll", "winmm.dll", "version.dll",
    "comdlg32.dll", "comctl32.dll", "imm32.dll", "uxtheme.dll", "dwmapi.dll",
    "crypt32.dll", "bcrypt.dll", "ncrypt.dll", "secur32.dll", "netapi32.dll",
    "userenv.dll", "iphlpapi.dll", "dnsapi.dll", "setupapi.dll", "shlwapi.dll",
    "d3d11.dll", "d3d12.dll", "d3d9.dll", "dxgi.dll", "d3dcompiler_47.dll",
    "opengl32.dll", "dwrite.dll", "d2d1.dll", "mpr.dll", "wtsapi32.dll",
    "authz.dll", "rpcrt4.dll", "msvcrt.dll", "ntdll.dll", "powrprof.dll",
    "winhttp.dll", "wininet.dll", "winspool.drv", "hid.dll", "dbghelp.dll",
    "mf.dll", "mfplat.dll", "mfreadwrite.dll", "propsys.dll", "wevtapi.dll",
    "normaliz.dll", "urlmon.dll", "credui.dll", "psapi.dll", "msimg32.dll",
    "usp10.dll", "gdiplus.dll", "dcomp.dll", "mfuuid.dll", "avrt.dll",
    "ksuser.dll", "dsound.dll", "cfgmgr32.dll", "shcore.dll", "wldap32.dll",
    "dhcpcsvc.dll", "fwpuclnt.dll", "mscms.dll", "esent.dll", "wsock32.dll",
    "sspicli.dll", "wintrust.dll", "cryptui.dll", "pdh.dll", "xinput1_4.dll",
    "comsupp.dll", "oleacc.dll", "uiautomationcore.dll", "dbgeng.dll",
    "bluetoothapis.dll", "wlanapi.dll", "dwmcore.dll", "msdmo.dll",
    "dxva2.dll", "evr.dll", "mfcore.dll", "ninput.dll", "hhctrl.ocx",
    "windowscodecs.dll", "wtsapi32.dll", "cryptnet.dll", "wer.dll",
    "devobj.dll", "msacm32.dll", "secur32.dll", "wsnmp32.dll",
}
_DLL_NAME = re.compile(r"DLL Name:\s*(\S+)", re.IGNORECASE)


def _is_system(name: str) -> bool:
    lower = name.lower()
    return lower.startswith(_SYSTEM_PREFIXES) or lower in _SYSTEM_NAMES


def check(root: Path, objdump: Path) -> list[tuple[str, str]]:
    binaries = [
        path for path in root.rglob("*")
        if path.is_file() and path.suffix.lower() in {".dll", ".pyd", ".exe"}
    ]
    present = {path.name.lower() for path in binaries}
    missing: list[tuple[str, str]] = []
    for path in binaries:
        result = subprocess.run(
            [str(objdump), "-p", str(path)], capture_output=True, text=True, errors="replace"
        )
        for name in _DLL_NAME.findall(result.stdout):
            if name.lower() in present or _is_system(name):
                continue
            missing.append((str(path.relative_to(root)), name))
    return missing


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(__doc__)
        return 2
    root, objdump = Path(argv[1]), Path(argv[2])
    if not objdump.is_file():
        print(f"objdump nicht gefunden ({objdump}); Abhängigkeitsprüfung übersprungen.")
        return 0
    missing = check(root, objdump)
    # Nur echte Lücken bei Qt, Python und mitgelieferten Bibliotheken zählen;
    # unbekannte Windows-Systembibliotheken werden nur aufgelistet.
    serious = [
        (owner, name) for owner, name in missing
        if name.lower().startswith(("qt6", "pyside6", "shiboken6", "python", "lib", "carendmr"))
    ]
    others = sorted({name for _owner, name in missing} - {name for _o, name in serious})
    if others:
        print("Hinweis: nicht gefundene, vermutlich Windows-eigene DLLs: " + ", ".join(others))
    if serious:
        print("FEHLER: Im Programmordner fehlen benötigte DLLs:")
        for owner, name in sorted(set(serious)):
            print(f"  {name}  (gebraucht von {owner})")
        return 1
    print("Abhängigkeitsprüfung: alle Qt-, Python- und Bibliotheks-DLLs vorhanden.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
