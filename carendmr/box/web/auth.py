"""Verwaltungskennwort und Sitzungen der Box-Web-App.

Das Kennwort wird nur als PBKDF2-Hash in ``config/box_admin.local.json``
gespeichert (gitignored), nie im Klartext. Sitzungen leben im Speicher.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import time
from pathlib import Path

ADMIN_FILE = "box_admin.local.json"
_ITERATIONS = 200_000
_SALT_BYTES = 16
MIN_PASSWORD_LENGTH = 6
SESSION_TTL_SECONDS = 3600.0


class AdminAuth:
    """Setzt, prüft und speichert das Verwaltungskennwort."""

    def __init__(self, project_root: Path) -> None:
        self._path = Path(project_root) / "config" / ADMIN_FILE

    def is_configured(self) -> bool:
        return self._path.is_file()

    def set_password(self, password: str) -> None:
        if len(password) < MIN_PASSWORD_LENGTH:
            raise ValueError(
                f"Das Verwaltungskennwort muss mindestens {MIN_PASSWORD_LENGTH} Zeichen haben."
            )
        salt = os.urandom(_SALT_BYTES)
        digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _ITERATIONS)
        record = {
            "algorithm": "pbkdf2_sha256",
            "iterations": _ITERATIONS,
            "salt": salt.hex(),
            "hash": digest.hex(),
        }
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._path.with_suffix(".tmp")
        tmp.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
        tmp.replace(self._path)

    def verify(self, password: str) -> bool:
        if not self._path.is_file():
            return False
        try:
            record = json.loads(self._path.read_text(encoding="utf-8"))
            salt = bytes.fromhex(record["salt"])
            expected = bytes.fromhex(record["hash"])
            iterations = int(record.get("iterations", _ITERATIONS))
        except (OSError, ValueError, KeyError, json.JSONDecodeError):
            return False
        digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
        return hmac.compare_digest(digest, expected)


class SessionStore:
    """Sitzungs-Token im Speicher; jedes trägt ein CSRF-Token."""

    def __init__(self, *, ttl_seconds: float = SESSION_TTL_SECONDS, clock=time.monotonic) -> None:
        self._ttl = ttl_seconds
        self._clock = clock
        self._sessions: dict[str, dict] = {}

    def create(self) -> str:
        token = secrets.token_urlsafe(32)
        self._sessions[token] = {
            "created": self._clock(),
            "csrf": secrets.token_urlsafe(16),
        }
        return token

    def is_valid(self, token: str | None) -> bool:
        return self._get(token) is not None

    def csrf_token(self, token: str | None) -> str | None:
        session = self._get(token)
        return session["csrf"] if session else None

    def check_csrf(self, token: str | None, csrf: str | None) -> bool:
        expected = self.csrf_token(token)
        return bool(expected) and bool(csrf) and hmac.compare_digest(expected, csrf)

    def destroy(self, token: str | None) -> None:
        if token:
            self._sessions.pop(token, None)

    def _get(self, token: str | None) -> dict | None:
        if not token:
            return None
        session = self._sessions.get(token)
        if session is None:
            return None
        if self._clock() - session["created"] > self._ttl:
            self._sessions.pop(token, None)
            return None
        return session
