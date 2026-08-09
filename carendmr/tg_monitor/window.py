"""Eigenständige Qt-Oberfläche für den CarenDMR-TG-Monitor."""
from __future__ import annotations

import json
import queue
import sys
import time
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import (
    QApplication, QComboBox, QHBoxLayout, QLabel, QLineEdit, QMainWindow,
    QMessageBox, QPushButton, QSpinBox, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
    QHeaderView, QAbstractItemView,
)

from carendmr.domain import DmrChannel
from carendmr.ipc.channel_control import send_channel_to_carendmr
from carendmr.tg_monitor.activity_service import TalkgroupActivity, TalkgroupActivityService
from carendmr.tg_monitor.instance_control import acquire_tg_monitor_instance
from carendmr.ui_qt.window_geometry import WindowGeometryManager
from carendmr.ui_qt.theme import apply_theme
from carendmr.version import __version__


class TGMonitorWindow(QMainWindow):
    def __init__(self, project_root: Path) -> None:
        super().__init__()
        self.project_root = Path(project_root)
        self.setWindowTitle(f"CarenDMR TG-Monitor {__version__}")
        self.resize(900, 520)
        self._window_geometry = WindowGeometryManager(self.project_root, self)

        self._updates: queue.Queue[tuple[str, object]] = queue.Queue()
        self._activities: dict[int, TalkgroupActivity] = {}
        self._tg_names = self._load_talkgroup_names()
        self._settings_path = self.project_root / "config" / "tg_monitor.local.json"
        settings = self._load_settings()
        self._monitored = set(settings.get("talkgroups", []))
        if not self._monitored:
            self._monitored = self._default_talkgroups()
        self._transfer_timeslot = int(settings.get("timeslot", 2))
        if self._transfer_timeslot not in {1, 2}:
            self._transfer_timeslot = 2
        self._minimum_duration_seconds = int(settings.get("minimum_duration_seconds", 3))
        self._minimum_duration_seconds = max(0, min(60, self._minimum_duration_seconds))

        self._log_path = self.project_root / "logs" / "tg_monitor.log"
        self._service = TalkgroupActivityService(
            self._monitored,
            on_activity=lambda item: self._updates.put(("activity", item)),
            on_status=lambda message: self._updates.put(("status", message)),
            log_path=self._log_path,
        )

        central = QWidget()
        layout = QVBoxLayout(central)

        intro = QLabel(
            "Beobachtet ausgewählte BrandMeister-Talkgroups unabhängig vom CarenDMR-Funkbetrieb. "
            "Ein markierter Eintrag kann an ein laufendes CarenDMR übergeben werden."
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)

        controls = QHBoxLayout()
        controls.addWidget(QLabel("Talkgroups:"))
        self.tg_edit = QLineEdit(", ".join(str(v) for v in sorted(self._monitored)))
        self.tg_edit.setAccessibleName("Zu überwachende Talkgroups")
        self.tg_edit.setToolTip("Mehrere Talkgroups durch Komma oder Leerzeichen trennen, z. B. 91, 262, 263")
        controls.addWidget(self.tg_edit, 1)

        self.apply_button = QPushButton("Überwachung übernehmen")
        self.apply_button.clicked.connect(self._apply_monitored)
        controls.addWidget(self.apply_button)

        controls.addWidget(QLabel("Übergabe:"))
        self.ts_combo = QComboBox()
        self.ts_combo.addItems(["TS1", "TS2"])
        self.ts_combo.setCurrentIndex(self._transfer_timeslot - 1)
        self.ts_combo.currentIndexChanged.connect(self._save_settings)
        controls.addWidget(self.ts_combo)

        controls.addWidget(QLabel("Mindestdauer:"))
        self.minimum_duration_spin = QSpinBox()
        self.minimum_duration_spin.setRange(0, 60)
        self.minimum_duration_spin.setSuffix(" s")
        self.minimum_duration_spin.setValue(self._minimum_duration_seconds)
        self.minimum_duration_spin.setAccessibleName("Mindestsprechdauer in Sekunden")
        self.minimum_duration_spin.setToolTip(
            "Durchgänge unter dieser Dauer werden ausgeblendet. 0 deaktiviert den Filter."
        )
        self.minimum_duration_spin.valueChanged.connect(self._minimum_duration_changed)
        controls.addWidget(self.minimum_duration_spin)
        layout.addLayout(controls)

        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(
            ["TG", "Name", "Status", "Station", "Name", "Dauer", "Letzte Aktivität"]
        )
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.doubleClicked.connect(self._send_selected)
        layout.addWidget(self.table, 1)

        actions = QHBoxLayout()
        self.status_label = QLabel(f"Bereit · Diagnose: {self._log_path}")
        self.status_label.setToolTip(str(self._log_path))
        self.status_label.setObjectName("secondaryText")
        actions.addWidget(self.status_label, 1)
        self.send_button = QPushButton("In CarenDMR übernehmen")
        self.send_button.clicked.connect(self._send_selected)
        actions.addWidget(self.send_button)
        layout.addLayout(actions)

        self.setCentralWidget(central)
        self._rebuild_rows()

        self._timer = QTimer(self)
        self._timer.setInterval(500)
        self._timer.timeout.connect(self._poll)
        self._timer.start()
        self._service.start()

    def _default_talkgroups(self) -> set[int]:
        path = self.project_root / "config" / "favorites.local.json"
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            rows = data.get("favorites", data) if isinstance(data, dict) else data
            values = []
            for row in rows if isinstance(rows, list) else []:
                target = int(row.get("target", 0))
                if target > 0 and target not in values:
                    values.append(target)
            if values:
                return set(values[:10])
        except Exception:
            pass
        return {91, 262}

    def _load_talkgroup_names(self) -> dict[int, str]:
        path = self.project_root / "config" / "talkgroups.json"
        try:
            rows = json.loads(path.read_text(encoding="utf-8"))
            return {
                int(row["target"]): str(row.get("name", "")).strip()
                for row in rows if isinstance(row, dict) and int(row.get("target", 0)) > 0
            }
        except Exception:
            return {}

    def _load_settings(self) -> dict:
        try:
            data = json.loads(self._settings_path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _save_settings(self) -> None:
        self._transfer_timeslot = self.ts_combo.currentIndex() + 1
        self._settings_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "talkgroups": sorted(self._monitored),
            "timeslot": self._transfer_timeslot,
            "minimum_duration_seconds": self._minimum_duration_seconds,
        }
        self._settings_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    @staticmethod
    def _parse_talkgroups(text: str) -> set[int]:
        normalized = text.replace(";", ",").replace(" ", ",")
        values: set[int] = set()
        for part in normalized.split(","):
            part = part.strip()
            if not part:
                continue
            value = int(part)
            if value <= 0:
                raise ValueError(f"Ungültige Talkgroup: {part}")
            values.add(value)
        if not values:
            raise ValueError("Mindestens eine Talkgroup angeben.")
        if len(values) > 50:
            raise ValueError("Maximal 50 Talkgroups gleichzeitig überwachen.")
        return values

    def _minimum_duration_changed(self, value: int) -> None:
        self._minimum_duration_seconds = max(0, min(60, int(value)))
        self._save_settings()
        self._refresh_all_rows()
        self.status_label.setText(
            f"Mindestsprechdauer: {self._minimum_duration_seconds} s · Diagnose: {self._log_path}"
        )

    def _apply_monitored(self) -> None:
        try:
            values = self._parse_talkgroups(self.tg_edit.text())
        except ValueError as error:
            QMessageBox.warning(self, "TG-Monitor", str(error))
            return
        self._monitored = values
        self._service.set_monitored_talkgroups(values)
        self._save_settings()
        self._rebuild_rows()
        self.status_label.setText(f"{len(values)} Talkgroups werden überwacht.")

    def _rebuild_rows(self) -> None:
        selected = self._selected_target()
        self.table.setRowCount(0)
        for target in sorted(self._monitored):
            row = self.table.rowCount()
            self.table.insertRow(row)
            name = self._tg_names.get(target, "")
            values = [str(target), name, "ruhig", "", "", "", ""]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                if col == 0:
                    item.setData(Qt.ItemDataRole.UserRole, target)
                self.table.setItem(row, col, item)
        self._refresh_all_rows()
        if selected in self._monitored:
            for row in range(self.table.rowCount()):
                if self._target_at(row) == selected:
                    self.table.selectRow(row)
                    break

    def _target_at(self, row: int) -> int | None:
        item = self.table.item(row, 0)
        if item is None:
            return None
        try:
            return int(item.data(Qt.ItemDataRole.UserRole) or item.text())
        except (TypeError, ValueError):
            return None

    def _selected_target(self) -> int | None:
        row = self.table.currentRow()
        return self._target_at(row) if row >= 0 else None

    def _refresh_all_rows(self) -> None:
        now = int(time.time())
        for row in range(self.table.rowCount()):
            target = self._target_at(row)
            activity = self._activities.get(target or 0)
            if activity is None:
                continue
            name = activity.talkgroup_name or self._tg_names.get(activity.target, "")
            duration = max(0, (now if activity.active else activity.stopped_at) - activity.started_at)
            if duration < self._minimum_duration_seconds:
                self.table.item(row, 1).setText(name)
                self.table.item(row, 2).setText("ruhig")
                self.table.item(row, 3).setText("")
                self.table.item(row, 4).setText("")
                self.table.item(row, 5).setText("")
                self.table.item(row, 6).setText("")
                continue
            self.table.item(row, 1).setText(name)
            self.table.item(row, 2).setText("AKTIV" if activity.active else "ruhig")
            self.table.item(row, 3).setText(activity.callsign or str(activity.source_id or ""))
            self.table.item(row, 4).setText(activity.source_name)
            self.table.item(row, 5).setText(f"{duration} s")
            stamp = activity.started_at if activity.active else activity.stopped_at or activity.started_at
            self.table.item(row, 6).setText(
                datetime.fromtimestamp(stamp).strftime("%H:%M:%S") if stamp > 0 else ""
            )

    def _poll(self) -> None:
        while True:
            try:
                kind, value = self._updates.get_nowait()
            except queue.Empty:
                break
            if kind == "activity":
                activity = value
                self._activities[activity.target] = activity
            elif kind == "status":
                self.status_label.setText(str(value))
        self._refresh_all_rows()

    def _send_selected(self, *_args) -> None:
        target = self._selected_target()
        if target is None:
            QMessageBox.information(self, "TG-Monitor", "Bitte zuerst eine Talkgroup markieren.")
            return
        name = self._tg_names.get(target, "")
        activity = self._activities.get(target)
        if activity is not None and activity.talkgroup_name:
            name = activity.talkgroup_name
        channel = DmrChannel(target, self.ts_combo.currentIndex() + 1, "group", name=name)
        ok, message = send_channel_to_carendmr(channel)
        self.status_label.setText(message)
        if not ok:
            QMessageBox.warning(self, "TG-Monitor", message)

    def closeEvent(self, event) -> None:
        self._service.stop()
        self._save_settings()
        event.accept()


def run_tg_monitor(project_root: Path) -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    apply_theme(app)

    instance_server = acquire_tg_monitor_instance()
    if instance_server is None:
        QMessageBox.information(
            None,
            "CarenDMR TG-Monitor",
            "Der TG-Monitor läuft bereits.",
        )
        return 0

    window = TGMonitorWindow(project_root)
    # Referenz am Fenster halten, damit der lokale Einzelinstanz-Server bis
    # zum Schließen des Monitors bestehen bleibt.
    window._instance_server = instance_server
    window._window_geometry.register("tg_monitor", window)

    def handle_instance_command() -> None:
        while instance_server.hasPendingConnections():
            socket = instance_server.nextPendingConnection()
            if socket is None:
                return
            socket.waitForReadyRead(150)
            command = bytes(socket.readAll()).decode("utf-8", errors="ignore").strip().lower()
            if command == "activate":
                if window.isMinimized():
                    window.showNormal()
                else:
                    window.show()
                window.raise_()
                window.activateWindow()
            elif command == "close":
                window.close()
            socket.disconnectFromServer()

    instance_server.newConnection.connect(handle_instance_command)
    window.show()
    return int(app.exec())
