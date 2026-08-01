"""HTTPS-Download des offiziellen RadioID-Nutzerexports."""

from __future__ import annotations

from pathlib import Path
from typing import Callable
from urllib.request import Request, urlopen

from carendmr.version import __version__

RADIOID_USER_CSV_URL = "https://radioid.net/static/user.csv"
MAX_DOWNLOAD_BYTES = 100 * 1024 * 1024


class RadioIdDownloader:
    def __init__(self, opener: Callable[..., object] = urlopen) -> None:
        self._opener = opener

    def download(self, target: Path, *, url: str = RADIOID_USER_CSV_URL) -> Path:
        target = Path(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        request = Request(url, headers={"User-Agent": f"CarenDMR/{__version__} (Amateur Radio Client)"})
        temporary = target.with_suffix(target.suffix + ".part")
        temporary.unlink(missing_ok=True)
        total = 0
        try:
            with self._opener(request, timeout=30) as response, temporary.open("wb") as output:
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > MAX_DOWNLOAD_BYTES:
                        raise ValueError("Der RadioID-Download überschreitet die zulässige Größe.")
                    output.write(chunk)
            if total == 0:
                raise ValueError("RadioID lieferte eine leere Datei.")
            temporary.replace(target)
            return target
        except Exception:
            temporary.unlink(missing_ok=True)
            raise
