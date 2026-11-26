"""Barrierefreier Dialog „Nach Updates suchen“.

Prüft nur auf Anfrage (beim Öffnen) im Hintergrund und sagt das Ergebnis an.
Bei einer neuen Version öffnen zwei Knöpfe den Download bzw. die
Projektseite im Browser; installiert wird nichts automatisch.
"""
from __future__ import annotations

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from carendmr.application.update_check_service import (
    UpdateCheckService,
    UpdateResult,
    UpdateState,
)
from carendmr.ui_qt.accessibility import announce
from carendmr.ui_qt.first_run_dialogs import _Background


class UpdateDialog(QDialog):
    def __init__(self, service: UpdateCheckService | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._service = service or UpdateCheckService()
        self._result: UpdateResult | None = None
        self._background = _Background(self)
        self.setWindowTitle("CarenDMR – Nach Updates suchen")
        self.setAccessibleName("Nach Updates suchen")
        self.setModal(True)

        layout = QVBoxLayout(self)
        self.status_label = QLabel("Es wird nach Updates gesucht. Bitte warten.")
        self.status_label.setWordWrap(True)
        self.status_label.setAccessibleName("Ergebnis der Update-Prüfung")
        layout.addWidget(self.status_label)

        buttons = QDialogButtonBox()
        self.download_button = buttons.addButton("&Download öffnen", QDialogButtonBox.ButtonRole.ActionRole)
        self.page_button = buttons.addButton("&Projektseite öffnen", QDialogButtonBox.ButtonRole.ActionRole)
        self.close_button = buttons.addButton("&Schließen", QDialogButtonBox.ButtonRole.RejectRole)
        self.download_button.clicked.connect(lambda: self._open(self._result.download if self._result else ""))
        self.page_button.clicked.connect(lambda: self._open(self._result.page if self._result else ""))
        self.close_button.clicked.connect(self.reject)
        self.download_button.setVisible(False)
        self.page_button.setVisible(False)
        layout.addWidget(buttons)
        self.close_button.setFocus()

        self._background.start(
            lambda _progress: self._service.check(),
            on_done=self._show_result,
            on_error=lambda error: self._show_result(
                UpdateResult(UpdateState.ERROR, f"Die Update-Prüfung ist fehlgeschlagen: {error}", self._service.current)
            ),
            name="CarenDMR-Update-Pruefung",
        )

    def _show_result(self, result: UpdateResult) -> None:
        self._result = result
        self.status_label.setText(result.message)
        announce(self.status_label, result.message)
        available = result.state is UpdateState.AVAILABLE
        self.download_button.setVisible(available and bool(result.download))
        self.page_button.setVisible(bool(result.page) and result.state is not UpdateState.ERROR)
        if available and result.download:
            self.download_button.setFocus()
        else:
            self.close_button.setFocus()

    def _open(self, url: str) -> None:
        if url.lower().startswith("https://"):
            QDesktopServices.openUrl(QUrl(url))

    def reject(self) -> None:
        # Schließen ist jederzeit erlaubt; ein laufender Abruf endet im Hintergrund.
        super().reject()
