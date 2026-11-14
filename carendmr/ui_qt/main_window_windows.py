"""Menü, Zusatzfenster (Einstellungen, Audio-Werkzeuge, TG-Monitor) und Fenstergeometrie.

Teil von ``MainWindow`` (siehe main_window.py). Die Methoden wurden ab
0.2.1.87 unverändert aus dem Hauptfenster hierher verschoben.
"""
from __future__ import annotations

import base64
import json
import subprocess
import sys
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import QApplication, QMessageBox
from pathlib import Path
from carendmr.tg_monitor.instance_control import is_tg_monitor_running, send_tg_monitor_command
from carendmr.ui_qt.audio_tool_windows import AudioBenchmarkWindow, AudioCoachWindow, AudioLabWindow
from carendmr.ui_qt.settings_dialog import SettingsDialog


class MainWindowWindowsMixin:
    """Mixin für ``MainWindow``; setzt dessen Attribute voraus."""

    def _build_menu(self) -> None:
        """Ergänzt nur den Zugang zum separaten Einstellungsfenster."""
        program_menu = self.menuBar().addMenu("Programm")
        settings_action = QAction("Einstellungen …", self)
        settings_action.setShortcut(QKeySequence("Ctrl+,"))
        settings_action.triggered.connect(self._open_settings)
        program_menu.addAction(settings_action)
        program_menu.addSeparator()
        benchmark_action = QAction("Audio-Benchmark …", self)
        benchmark_action.triggered.connect(self._open_audio_benchmark)
        program_menu.addAction(benchmark_action)
        coach_action = QAction("Audio Coach …", self)
        coach_action.triggered.connect(self._open_audio_coach)
        program_menu.addAction(coach_action)
        lab_action = QAction("Live-Audiolabor …", self)
        lab_action.triggered.connect(self._open_audio_lab)
        program_menu.addAction(lab_action)
        program_menu.addSeparator()
        tg_monitor_action = QAction("TG-Monitor starten", self)
        tg_monitor_action.triggered.connect(self._start_tg_monitor)
        program_menu.addAction(tg_monitor_action)

        self.window_menu = self.menuBar().addMenu("Fenster")
        self.window_menu.aboutToShow.connect(self._rebuild_window_menu)

    def _rebuild_window_menu(self) -> None:
        self.window_menu.clear()

        main_action = QAction("CarenDMR – Hauptfenster", self)
        main_action.triggered.connect(lambda: self._bring_window_to_front(self))
        self.window_menu.addAction(main_action)

        labels = {
            "settings": "Einstellungen",
            "audio_benchmark": "Audio-Benchmark",
            "audio_coach": "Audio Coach",
            "audio_lab": "Live-Audiolabor",
            "audio_tuner": "Audio-Tuner",
            "qrz_station": (
                self._qrz_window.windowTitle()
                if self._qrz_window is not None
                else "QRZ.com – Station"
            ),
        }
        for key, widget in self.window_geometry.visible_windows():
            label = labels.get(key, widget.windowTitle() or key)
            action = QAction(label, self)
            action.triggered.connect(
                lambda _checked=False, target=widget: self._bring_window_to_front(target)
            )
            self.window_menu.addAction(action)

        if is_tg_monitor_running():
            monitor_action = QAction("TG-Monitor", self)
            monitor_action.triggered.connect(
                lambda: send_tg_monitor_command("activate")
            )
            self.window_menu.addAction(monitor_action)

        self.window_menu.addSeparator()

        front_action = QAction("Alle Fenster nach vorne", self)
        front_action.triggered.connect(self._bring_all_windows_to_front)
        self.window_menu.addAction(front_action)

        close_action = QAction("Alle Zusatzfenster schließen", self)
        close_action.triggered.connect(self._close_all_auxiliary_windows)
        self.window_menu.addAction(close_action)

        self.window_menu.addSeparator()
        reset_action = QAction("Fensterpositionen zurücksetzen", self)
        reset_action.triggered.connect(self._reset_window_positions)
        self.window_menu.addAction(reset_action)

    def _bring_window_to_front(self, widget) -> None:
        if widget is None:
            return
        if widget.isMinimized():
            widget.showNormal()
        else:
            widget.show()
        widget.raise_()
        widget.activateWindow()

    def _bring_all_windows_to_front(self) -> None:
        self._bring_window_to_front(self)
        self.window_geometry.bring_all_to_front()
        if is_tg_monitor_running():
            send_tg_monitor_command("activate")

    def _close_all_auxiliary_windows(self) -> None:
        self.window_geometry.close_all()
        if is_tg_monitor_running():
            send_tg_monitor_command("close")
        self.statusBar().showMessage("Alle Zusatzfenster wurden geschlossen.", 5000)

    def _reset_window_positions(self) -> None:
        self._close_all_auxiliary_windows()
        self.window_geometry.reset_saved()
        path = self._window_state_path()
        try:
            path.unlink()
        except FileNotFoundError:
            pass
        except OSError:
            pass

        self.showNormal()
        self.resize(980, 720)
        app = QApplication.instance()
        screens = list(app.screens()) if app is not None else []
        if screens:
            area = screens[0].availableGeometry()
            self.move(area.center() - self.rect().center())
        self.statusBar().showMessage(
            "Fensterpositionen wurden zurückgesetzt. Zusatzfenster öffnen wieder an Standardpositionen.",
            7000,
        )

    def _start_tg_monitor(self) -> None:
        """Startet den eigenständigen TG-Monitor höchstens einmal."""
        if is_tg_monitor_running():
            self.statusBar().showMessage("Der TG-Monitor läuft bereits.", 5000)
            QMessageBox.information(self, "CarenDMR", "Der TG-Monitor läuft bereits.")
            return

        script = self.project_root / "tg_monitor.py"
        if not script.is_file():
            QMessageBox.warning(self, "CarenDMR", f"TG-Monitor wurde nicht gefunden:\n{script}")
            return

        try:
            subprocess.Popen(
                [sys.executable, str(script)],
                cwd=str(self.project_root),
            )
        except OSError as error:
            QMessageBox.critical(self, "CarenDMR", f"TG-Monitor konnte nicht gestartet werden:\n\n{error}")
            return

        self.statusBar().showMessage("TG-Monitor wurde als eigenes Programm gestartet.", 5000)

    def _open_audio_benchmark(self) -> None:
        if self._audio_benchmark_window is None:
            self._audio_benchmark_window = AudioBenchmarkWindow(
                self.audio_benchmark_service,
                current_target=lambda: (
                    self._selected_talkgroup_for_benchmark(),
                    self._selected_timeslot,
                ),
                reconnect_request=self._benchmark_reconnect,
                parent=self,
            )
            self.window_geometry.register("audio_benchmark", self._audio_benchmark_window)
        self._audio_benchmark_window.show()
        self._audio_benchmark_window.raise_()
        self._audio_benchmark_window.activateWindow()

    def _open_audio_coach(self) -> None:
        if self._audio_coach_window is None:
            self._audio_coach_window = AudioCoachWindow(
                self.audio_benchmark_service,
                start_modulation_test=self._start_audio_tuner_assistant,
                cancel_modulation_test=self._cancel_audio_tuner_assistant,
                parent=self,
            )
            self.window_geometry.register("audio_coach", self._audio_coach_window)
        self._audio_coach_window.show()
        self._audio_coach_window.raise_()
        self._audio_coach_window.activateWindow()

    def _open_audio_lab(self) -> None:
        if self._audio_lab_window is None:
            self._audio_lab_window = AudioLabWindow(
                self.local_audio_lab_service,
                parent=self,
            )
            self.window_geometry.register("audio_lab", self._audio_lab_window)
        self._audio_lab_window.show()
        self._audio_lab_window.raise_()
        self._audio_lab_window.activateWindow()

    def _open_settings(self) -> None:
        if self._settings_dialog is not None and self._settings_dialog.isVisible():
            self._settings_dialog.raise_()
            self._settings_dialog.activateWindow()
            return
        dialog = SettingsDialog(
            self.project_root, self.audio_send_service, self.receive_service, self,
            station_settings=self.station_settings,
        )
        dialog.settings_applied.connect(self._settings_applied)
        dialog.finished.connect(lambda _result: setattr(self, "_settings_dialog", None))
        self._settings_dialog = dialog
        self.window_geometry.register("settings", dialog)
        dialog.show()

    def _settings_applied(self) -> None:
        self.preferences = self.preferences_store.load()
        self._selected_timeslot = self.preferences.timeslot
        self._selected_call_type = self.preferences.call_type
        self._reload_hotkeys()
        self._sync_radio_controls()
        self._sync_operation_audio_controls()

    def _window_state_path(self) -> Path:
        return self.project_root / "config" / "window.local.json"

    def _restore_window_geometry(self) -> None:
        """Stellt Position/Größe wieder her, aber niemals unsichtbar off-screen."""
        path = self._window_state_path()
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            encoded = str(payload.get("geometry", "")).strip()
            if not encoded:
                return
            raw = base64.b64decode(encoded.encode("ascii"))
            layout_version = int(payload.get("layout_version", 1) or 1)
            if not self.restoreGeometry(raw):
                return
            # 0.2.1.34 hat eine deutlich kompaktere Maske. Alte, für das vorherige
            # gestreckte Layout gespeicherte Größen werden einmalig normalisiert;
            # Position und alle künftig gespeicherten Größen bleiben erhalten.
            if layout_version < 2 and not self.isMaximized():
                self.resize(980, 720)
            app = QApplication.instance()
            screens = list(app.screens()) if app is not None else []
            frame = self.frameGeometry()
            visible = any(screen.availableGeometry().intersects(frame) for screen in screens)
            if not visible and screens:
                area = screens[0].availableGeometry()
                self.resize(min(self.width(), area.width()), min(self.height(), area.height()))
                self.move(area.center() - self.rect().center())
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            return

    def _save_window_geometry(self) -> None:
        path = self._window_state_path()
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "geometry": base64.b64encode(bytes(self.saveGeometry())).decode("ascii"),
                "maximized": bool(self.isMaximized()),
                "layout_version": 2,
            }
            path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        except OSError:
            pass
