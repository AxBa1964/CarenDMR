"""Funktionale Qt-Portierung der QSO-Historie."""
from __future__ import annotations

from datetime import datetime
from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from carendmr.application import QsoHistoryService
from carendmr.domain import QsoHistorySummary


class HistoryTable(QTableWidget):
    """Tabelle mit stabilem Dialog-Tabverhalten.

    Pfeiltasten bleiben vollständig bei Qt. Tab und Shift+Tab setzen den Fokus
    direkt auf ausdrücklich hinterlegte Nachbar-Widgets. Dadurch entsteht keine
    rekursive keyPressEvent-/focusNextPrevChild-Kette.
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.tab_forward_target: QWidget | None = None
        self.tab_backward_target: QWidget | None = None

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() in (Qt.Key.Key_Tab, Qt.Key.Key_Backtab):
            backwards = event.key() == Qt.Key.Key_Backtab or bool(
                event.modifiers() & Qt.KeyboardModifier.ShiftModifier
            )
            target = self.tab_backward_target if backwards else self.tab_forward_target
            if target is not None and target.isEnabled():
                target.setFocus(Qt.FocusReason.BacktabFocusReason if backwards else Qt.FocusReason.TabFocusReason)
                event.accept()
                return
        super().keyPressEvent(event)


class QsoHistoryWidget(QWidget):
    def __init__(
        self,
        service: QsoHistoryService,
        status_callback: Callable[[str], None] | None = None,
        worked_changed_callback: Callable[[int, bool], None] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.service = service
        self.status_callback = status_callback or (lambda _message: None)
        self.worked_changed_callback = worked_changed_callback or (lambda _source_id, _worked: None)
        self._rows: list[QsoHistorySummary] = []
        self._selected_source_id: int | None = None
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        controls = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Rufzeichen, Name, DMR-ID, Ort oder Talkgroup")
        self.search_edit.textChanged.connect(self.refresh)
        self.refresh_button = QPushButton("Aktualisieren")
        self.refresh_button.clicked.connect(self.refresh)
        self.summary_label = QLabel("Noch keine Historieneinträge")
        controls.addWidget(QLabel("Suche:"))
        controls.addWidget(self.search_edit, 1)
        controls.addWidget(self.refresh_button)
        controls.addWidget(self.summary_label)
        root.addLayout(controls)

        content = QHBoxLayout()
        self.table = HistoryTable(0, 8, self)
        self.table.setHorizontalHeaderLabels(
            (
                "Zuletzt gehört",
                "Rufzeichen",
                "Name",
                "Land",
                "Letztes Ziel",
                "Durchgänge",
                "Gesamtdauer",
                "QSO",
            )
        )
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.itemSelectionChanged.connect(self._selection_changed)
        self.table.itemDoubleClicked.connect(lambda _item: self.toggle_worked())
        content.addWidget(self.table, 3)

        detail_box = QGroupBox("QSO-Details")
        detail_form = QFormLayout(detail_box)
        self.callsign_label = QLabel("Keine Station ausgewählt")
        self.name_label = QLabel("–")
        self.dmr_id_label = QLabel("–")
        self.location_label = QLabel("–")
        self.last_target_label = QLabel("–")
        self.count_label = QLabel("–")
        self.duration_label = QLabel("–")
        self.worked_label = QLabel("–")
        for label in (
            self.callsign_label,
            self.name_label,
            self.location_label,
            self.last_target_label,
            self.worked_label,
        ):
            label.setWordWrap(True)
        detail_form.addRow("Rufzeichen:", self.callsign_label)
        detail_form.addRow("Name:", self.name_label)
        detail_form.addRow("DMR-ID:", self.dmr_id_label)
        detail_form.addRow("Ort:", self.location_label)
        detail_form.addRow("Letztes Ziel:", self.last_target_label)
        detail_form.addRow("Sprechdurchgänge:", self.count_label)
        detail_form.addRow("Gesamtdauer:", self.duration_label)
        detail_form.addRow("Status:", self.worked_label)
        self.worked_button = QPushButton("QSO bestätigen")
        self.worked_button.setEnabled(False)
        self.worked_button.clicked.connect(self.toggle_worked)
        detail_form.addRow(self.worked_button)
        content.addWidget(detail_box, 1)
        root.addLayout(content, 1)

        QWidget.setTabOrder(self.search_edit, self.refresh_button)
        QWidget.setTabOrder(self.refresh_button, self.table)
        QWidget.setTabOrder(self.table, self.worked_button)
        self.table.tab_backward_target = self.refresh_button
        self.table.tab_forward_target = self.worked_button

    @staticmethod
    def _format_timestamp(value: str) -> str:
        try:
            return datetime.fromisoformat(value).astimezone().strftime("%d.%m.%Y %H:%M")
        except (ValueError, TypeError):
            return value

    @staticmethod
    def _format_duration(seconds: float) -> str:
        total = max(0, int(round(seconds)))
        hours, rest = divmod(total, 3600)
        minutes, remaining = divmod(rest, 60)
        if hours:
            return f"{hours} h {minutes:02d} min {remaining:02d} s"
        if minutes:
            return f"{minutes} min {remaining:02d} s"
        return f"{remaining} s"

    def refresh(self, *_args: object) -> None:
        selected_source = self._selected_source_id
        self._rows = list(self.service.list_station_summaries(self.search_edit.text()))
        self.table.setRowCount(len(self._rows))
        restore_row = -1
        for row, summary in enumerate(self._rows):
            values = (
                self._format_timestamp(summary.last_heard_at),
                summary.callsign or "Unbekannt",
                summary.name or "",
                summary.country or "",
                f"TG {summary.last_talkgroup} / TS{summary.last_timeslot}",
                str(summary.heard_count),
                self._format_duration(summary.total_duration_seconds),
                "Gesprochen" if summary.worked else "Nur gehört",
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setData(Qt.ItemDataRole.UserRole, summary.source_id)
                self.table.setItem(row, column, item)
            if summary.source_id == selected_source:
                restore_row = row
        self.table.resizeColumnsToContents()
        worked_count = sum(1 for item in self._rows if item.worked)
        self.summary_label.setText(
            f"{len(self._rows)} Stationen · {worked_count} bestätigte QSOs"
        )
        if restore_row >= 0:
            self.table.selectRow(restore_row)
        elif self._rows:
            self.table.selectRow(0)
        else:
            self._selected_source_id = None
            self._show_summary(None)

    def _selection_changed(self) -> None:
        row = self.table.currentRow()
        summary = self._rows[row] if 0 <= row < len(self._rows) else None
        self._selected_source_id = summary.source_id if summary else None
        self._show_summary(summary)

    def _show_summary(self, summary: QsoHistorySummary | None) -> None:
        if summary is None:
            self.callsign_label.setText("Keine Station ausgewählt")
            for label in (
                self.name_label,
                self.dmr_id_label,
                self.location_label,
                self.last_target_label,
                self.count_label,
                self.duration_label,
                self.worked_label,
            ):
                label.setText("–")
            self.worked_button.setText("QSO bestätigen")
            self.worked_button.setEnabled(False)
            return
        location = " / ".join(
            part for part in (summary.city, summary.state, summary.country) if part
        )
        self.callsign_label.setText(summary.callsign or "Unbekannt")
        self.name_label.setText(summary.name or "Name nicht vorhanden")
        self.dmr_id_label.setText(str(summary.source_id))
        self.location_label.setText(location or "Ort nicht vorhanden")
        self.last_target_label.setText(
            f"TG {summary.last_talkgroup}, Timeslot {summary.last_timeslot}"
        )
        self.count_label.setText(str(summary.heard_count))
        self.duration_label.setText(self._format_duration(summary.total_duration_seconds))
        self.worked_label.setText("QSO bestätigt" if summary.worked else "Bisher nur gehört")
        self.worked_button.setText("QSO zurücknehmen" if summary.worked else "QSO bestätigen")
        self.worked_button.setEnabled(True)

    def toggle_worked(self) -> None:
        row = self.table.currentRow()
        if not (0 <= row < len(self._rows)):
            return
        summary = self._rows[row]
        new_state = not summary.worked
        self.service.set_worked(summary.source_id, new_state)
        self.worked_changed_callback(summary.source_id, new_state)
        action = "als gesprochen bestätigt" if new_state else "auf nur gehört zurückgesetzt"
        self.status_callback(f"{summary.callsign or summary.source_id} wurde {action}.")
        self.refresh()
