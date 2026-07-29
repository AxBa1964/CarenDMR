"""Permanently disabled legacy public-talkgroup transmission tool."""

from __future__ import annotations


class OneShotSafetyError(RuntimeError):
    """The obsolete public-group test is forbidden by project policy."""


def execute_one_shot(*_args: object, **_kwargs: object) -> None:
    raise OneShotSafetyError(
        "Öffentliche Talkgroups dürfen nicht für automatisierte Sendetests "
        "verwendet werden. Es wurde nichts gesendet."
    )


def main() -> int:
    print("GESPERRT: Der frühere TG91-Sendetest ist dauerhaft deaktiviert.")
    print("Automatisierte Sendetests dürfen nur das verriegelte private")
    print("BrandMeister-Parrot-Profil 9990 auf Timeslot 2 verwenden.")
    print("Es wurde nichts gesendet.")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
