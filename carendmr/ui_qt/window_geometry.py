"""Zentrale Positions-/Größenverwaltung für CarenDMR-Zusatzfenster."""
from __future__ import annotations

import base64
import json
from pathlib import Path

from PySide6.QtCore import QEvent, QObject
from PySide6.QtWidgets import QApplication, QWidget


class WindowGeometryManager(QObject):
    def __init__(self, project_root: Path, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.project_root = Path(project_root)
        self.path = self.project_root / "config" / "windows.local.json"
        self._widgets: dict[str, QWidget] = {}
        self._keys_by_widget: dict[int, str] = {}

    def _load(self) -> dict:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except (OSError, json.JSONDecodeError, TypeError):
            return {}

    def _save_data(self, data: dict) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        except OSError:
            pass

    def register(self, key: str, widget: QWidget) -> QWidget:
        normalized = str(key).strip()
        if not normalized:
            raise ValueError("Fensterschlüssel darf nicht leer sein.")
        self._widgets[normalized] = widget
        self._keys_by_widget[id(widget)] = normalized
        widget.installEventFilter(self)
        self.restore(normalized, widget)
        return widget

    def unregister(self, widget: QWidget) -> None:
        key = self._keys_by_widget.pop(id(widget), None)
        if key and self._widgets.get(key) is widget:
            self._widgets.pop(key, None)
        try:
            widget.removeEventFilter(self)
        except RuntimeError:
            pass

    def eventFilter(self, watched, event):  # noqa: N802
        if event.type() == QEvent.Type.Close:
            key = self._keys_by_widget.get(id(watched))
            if key and isinstance(watched, QWidget):
                self.save(key, watched)
        elif event.type() == QEvent.Type.Destroy:
            if isinstance(watched, QWidget):
                self.unregister(watched)
        return super().eventFilter(watched, event)

    def save(self, key: str, widget: QWidget) -> None:
        data = self._load()
        data[str(key)] = {
            "geometry": base64.b64encode(bytes(widget.saveGeometry())).decode("ascii"),
        }
        self._save_data(data)

    def restore(self, key: str, widget: QWidget) -> bool:
        data = self._load()
        entry = data.get(str(key), {})
        encoded = str(entry.get("geometry", "")).strip() if isinstance(entry, dict) else ""
        if not encoded:
            return False
        try:
            raw = base64.b64decode(encoded.encode("ascii"))
        except (ValueError, TypeError):
            return False
        if not widget.restoreGeometry(raw):
            return False
        self.ensure_visible(widget)
        return True

    @staticmethod
    def ensure_visible(widget: QWidget) -> None:
        app = QApplication.instance()
        screens = list(app.screens()) if app is not None else []
        if not screens:
            return
        frame = widget.frameGeometry()
        if any(screen.availableGeometry().intersects(frame) for screen in screens):
            return
        area = screens[0].availableGeometry()
        widget.resize(min(widget.width(), area.width()), min(widget.height(), area.height()))
        widget.move(area.center() - widget.rect().center())

    def visible_windows(self) -> list[tuple[str, QWidget]]:
        result = []
        for key, widget in list(self._widgets.items()):
            try:
                if widget.isVisible():
                    result.append((key, widget))
            except RuntimeError:
                self._widgets.pop(key, None)
        return result

    def bring_to_front(self, widget: QWidget) -> None:
        if widget.isMinimized():
            widget.showNormal()
        else:
            widget.show()
        widget.raise_()
        widget.activateWindow()

    def bring_all_to_front(self) -> None:
        for _key, widget in self.visible_windows():
            self.bring_to_front(widget)

    def close_all(self) -> None:
        for _key, widget in list(self.visible_windows()):
            widget.close()

    def reset_saved(self) -> None:
        try:
            self.path.unlink()
        except FileNotFoundError:
            pass
        except OSError:
            pass
