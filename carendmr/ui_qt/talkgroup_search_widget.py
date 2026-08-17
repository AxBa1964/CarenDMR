"""Einzeilige, tastaturbedienbare Talkgroup-Livesuche."""
from __future__ import annotations

from PySide6.QtCore import QEvent, QPoint, Qt, Signal
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QLineEdit,
    QTableWidget,
    QTableWidgetItem,
)

from carendmr.application import TalkgroupSearchService
from carendmr.domain import DmrChannel


class TalkgroupSearchWidget(QLineEdit):
    """QLineEdit mit nicht aktivierendem Popup für DMR-Kanaltreffer.

    Das Suchfeld behält während der gesamten Eingabe den Tastaturfokus. Die
    Trefferliste wird ausschließlich vom Eingabefeld aus mit Pfeiltasten,
    Enter und Escape gesteuert.
    """

    channel_selected = Signal(object)

    def __init__(self, search_service: TalkgroupSearchService, parent=None) -> None:
        super().__init__(parent)
        self.search_service = search_service
        self._results: list[DmrChannel] = []
        self._highlighted_row = -1
        self.popup = QTableWidget(0, 2, None)
        self.popup.setWindowFlags(
            Qt.WindowType.ToolTip
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.popup.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.popup.setObjectName("talkgroupSearchPopup")
        self.popup.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.popup.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.popup.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.popup.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.popup.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.popup.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.popup.verticalHeader().hide()
        self.popup.horizontalHeader().hide()
        self.popup.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.popup.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.popup.cellClicked.connect(self._accept_row)
        self.popup.currentCellChanged.connect(self._remember_current_row)
        self.textEdited.connect(self._refresh_results)

    def _refresh_results(self, text: str) -> None:
        results = self.search_service.search(text, limit=10)
        self._results = list(results)
        self.popup.setRowCount(0)
        for row, channel in enumerate(results):
            self.popup.insertRow(row)
            name_item = QTableWidgetItem(self.search_service.display_name(channel))
            target_item = QTableWidgetItem(self.search_service.format_target(channel))
            name_item.setData(Qt.ItemDataRole.UserRole, channel)
            target_item.setData(Qt.ItemDataRole.UserRole, channel)
            name_item.setToolTip(self.search_service.display_name(channel))
            target_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.popup.setItem(row, 0, name_item)
            self.popup.setItem(row, 1, target_item)
            self.popup.setRowHeight(row, 32)

        if not results:
            self.popup.hide()
            return

        self._select_result_row(0)
        visible_rows = min(len(results), 10)
        popup_width = max(self.width(), 520)
        self.popup.setFixedWidth(popup_width)
        self.popup.setFixedHeight((32 * visible_rows) + 4)
        self.popup.move(self.mapToGlobal(QPoint(0, self.height())))
        self.popup.show()
        self.activateWindow()
        self.setFocus(Qt.FocusReason.OtherFocusReason)


    def _remember_current_row(self, current_row: int, _current_column: int, _previous_row: int, _previous_column: int) -> None:
        if 0 <= current_row < len(self._results):
            self._highlighted_row = current_row

    def _select_result_row(self, row: int) -> None:
        if not self._results:
            self._highlighted_row = -1
            return
        row = max(0, min(row, len(self._results) - 1))
        self._highlighted_row = row
        self.popup.selectRow(row)
        self.popup.setCurrentCell(row, 0)

    def _accept_current_result(self) -> bool:
        if not self.popup.isVisible() or not self._results:
            return False
        row = self._highlighted_row
        if row < 0 or row >= len(self._results):
            row = self.popup.currentRow()
        if row < 0 or row >= len(self._results):
            row = 0
        self._accept_row(row)
        return True

    def event(self, event) -> bool:
        # Return/Enter wird bereits auf der allgemeinen Event-Ebene abgefangen.
        # Dadurch funktioniert die Uebernahme auch dann, wenn Qt das Signal des
        # QLineEdit oder einen Default-Button vor keyPressEvent verarbeitet.
        if event.type() == QEvent.Type.KeyPress and event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if self._accept_current_result():
                event.accept()
                return True
        return super().event(event)

    def _channel_for_row(self, row: int) -> DmrChannel | None:
        # Die Treffer bleiben bewusst in einer Python-Liste. Damit ist die
        # Enter-Uebernahme nicht von der QVariant-Konvertierung der Qt-Zellen
        # abhaengig und funktioniert identisch fuer Maus und Tastatur.
        if row < 0 or row >= len(self._results):
            return None
        return self._results[row]

    def _show_results_for_current_text(self) -> bool:
        """Oeffnet die Trefferliste erneut, sofern Suchtext und Treffer existieren."""
        text = self.text().strip()
        if not text:
            return False
        self._refresh_results(text)
        return self.popup.isVisible() and bool(self._results)

    def _accept_row(self, row: int, _column: int = 0) -> None:
        channel = self._channel_for_row(row)
        if channel is None:
            return
        self.popup.hide()
        self.channel_selected.emit(channel)

    def hide_popup(self) -> None:
        self.popup.hide()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        key = event.key()

        # Pfeil nach unten oeffnet eine zuvor mit Escape geschlossene Liste
        # erneut. Das Suchfeld behaelt dabei den Fokus.
        if key == Qt.Key.Key_Down and not self.popup.isVisible():
            if self._show_results_for_current_text():
                self._select_result_row(0)
                event.accept()
                return

        if self.popup.isVisible() and self._results:
            current = self._highlighted_row
            if current < 0:
                current = self.popup.currentRow()
            if current < 0:
                current = 0
                self._select_result_row(current)
            if key == Qt.Key.Key_Down:
                self._select_result_row(min(current + 1, len(self._results) - 1))
                event.accept()
                return
            if key == Qt.Key.Key_Up:
                self._select_result_row(max(current - 1, 0))
                event.accept()
                return
            if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                self._accept_current_result()
                event.accept()
                return
            if key == Qt.Key.Key_Escape:
                self.popup.hide()
                self.setFocus(Qt.FocusReason.OtherFocusReason)
                event.accept()
                return

        # Alle normalen Zeichen gehen immer an das Eingabefeld. Dadurch kann
        # die Suche trotz sichtbarer Trefferliste fortlaufend verfeinert werden.
        super().keyPressEvent(event)

    def focusOutEvent(self, event) -> None:
        # Das Popup selbst darf den Fokus nicht übernehmen. Bei echtem Wechsel
        # zu einem anderen Bedienelement wird es geschlossen.
        super().focusOutEvent(event)
        if not self.hasFocus():
            self.popup.hide()
