from carendmr.ui_qt.accessibility_formatter import RadioAccessibilityFormatter


def test_radio_formatter_keeps_context_and_spells_pending_tg() -> None:
    formatter = RadioAccessibilityFormatter()
    assert formatter.operation_context(262, 1, "private", "Getrennt") == (
        "Betrieb. Talkgroup 262. Timeslot 1. Rufart Privatruf. Getrennt."
    )
    assert formatter.pending_talkgroup("2622610") == "Neue Talkgroup 2 6 2 2 6 1 0."


def test_history_context_preserves_existing_wording() -> None:
    formatter = RadioAccessibilityFormatter()
    assert formatter.history_context(1) == "QSO-Historie. 1 Station."
    assert formatter.history_context(3) == "QSO-Historie. 3 Stationen."
