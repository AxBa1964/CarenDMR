"""Qt-Verwaltung des gemeinsamen Talkgroup-Verzeichnisses."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView, QCheckBox, QComboBox, QDialog, QFileDialog,
    QFormLayout, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton,
    QSpinBox, QTableWidget, QTableWidgetItem, QTextEdit, QVBoxLayout, QWidget,
)

from carendmr.application import FavoriteService, TalkgroupCatalogService, TalkgroupSearchService
from carendmr.domain import DmrChannel, FavoriteChannel


class FavoriteEditDialog(QDialog):
    def __init__(self, channel: DmrChannel, favorite: FavoriteChannel | None = None, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("DMR-Kanal bearbeiten")
        self.setMinimumWidth(430)
        layout = QVBoxLayout(self)
        form = QFormLayout()
        default_name = favorite.default_name if favorite else channel.name
        custom_name = favorite.custom_name if favorite else default_name
        note = favorite.note if favorite else ""
        self.favorite_check = QCheckBox("Als Favorit markieren")
        self.favorite_check.setChecked(favorite is not None)
        self.name_edit = QLineEdit(custom_name)
        self.default_label = QLabel(default_name or "–")
        self.target_label = QLabel(str(channel.target))
        self.timeslot = QSpinBox(); self.timeslot.setRange(1, 2); self.timeslot.setValue(favorite.timeslot if favorite else channel.timeslot)
        self.call_type = QComboBox(); self.call_type.addItem("Gruppe", "group"); self.call_type.addItem("Privat", "private")
        self.call_type.setCurrentIndex(0 if (favorite.call_type if favorite else channel.call_type) == "group" else 1)
        self.note_edit = QTextEdit(note); self.note_edit.setMaximumHeight(110)
        self.note_edit.setPlaceholderText("Zum Beispiel: Rundspruch Dienstag 08:00")
        form.addRow("Favorit", self.favorite_check)
        for label, widget in (("Eigener Name", self.name_edit), ("Standardname", self.default_label), ("Talkgroup / DMR-ID", self.target_label), ("Timeslot", self.timeslot), ("Rufart", self.call_type), ("Notiz", self.note_edit)):
            form.addRow(label, widget)
        layout.addLayout(form)
        buttons = QHBoxLayout(); buttons.addStretch(1)
        save = QPushButton("Speichern"); cancel = QPushButton("Abbrechen")
        save.setMinimumWidth(90); cancel.setMinimumWidth(90)
        save.clicked.connect(self.accept); cancel.clicked.connect(self.reject)
        buttons.addWidget(save); buttons.addWidget(cancel); layout.addLayout(buttons)
        self._channel = channel; self._default_name = default_name

    @property
    def mark_as_favorite(self) -> bool:
        return self.favorite_check.isChecked()

    def favorite(self, position: int = 0) -> FavoriteChannel:
        return FavoriteChannel(self._channel.target, self.timeslot.value(), str(self.call_type.currentData()), self._default_name, self.name_edit.text().strip(), self.note_edit.toPlainText().strip(), position).normalized()


class FavoritesWidget(QWidget):
    """Zeigt alle Talkgroups; Favoriten sind lediglich mit einem Stern markiert."""
    channel_requested = Signal(object)
    changed = Signal()

    def __init__(self, service: FavoriteService, search_service: TalkgroupSearchService, catalog_service: TalkgroupCatalogService, parent=None) -> None:
        super().__init__(parent)
        self.service = service; self.search_service = search_service; self.catalog_service = catalog_service
        root = QVBoxLayout(self)
        title = QLabel("TALKGROUPS"); title.setObjectName("sectionTitle"); root.addWidget(title)
        filters = QHBoxLayout()
        self.filter_edit = QLineEdit(); self.filter_edit.setPlaceholderText("Talkgroup nach Nummer oder Name filtern")
        self.country_filter = QComboBox(); self.country_filter.addItem("Alle Länder", "")
        self.language_filter = QComboBox(); self.language_filter.addItem("Alle Sprachen", "")
        filters.addWidget(self.filter_edit, 1); filters.addWidget(self.country_filter); filters.addWidget(self.language_filter)
        root.addLayout(filters)
        self.filter_edit.textChanged.connect(self.refresh)
        self.country_filter.currentIndexChanged.connect(self.refresh); self.language_filter.currentIndexChanged.connect(self.refresh)
        self.table = QTableWidget(0, 9, self)
        self.table.setHorizontalHeaderLabels(["★", "Eigener Name", "Standardname", "TG", "TS", "R", "Land", "Sprache", "Notiz"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows); self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers); self.table.verticalHeader().hide(); self.table.horizontalHeader().setStretchLastSection(True)
        self.table.itemDoubleClicked.connect(lambda *_: self.use_selected()); self.table.itemClicked.connect(self._item_clicked)
        root.addWidget(self.table, 1)
        buttons = QHBoxLayout()
        for text, callback in (("Bearbeiten", self.edit_selected), ("Favorit setzen", self.set_favorite), ("Favorit entfernen", self.remove_favorite), ("BrandMeister aktualisieren", self.update_brandmeister), ("Importieren", self.import_favorites), ("Exportieren", self.export_favorites), ("Übernehmen", self.use_selected)):
            b=QPushButton(text); b.setMinimumWidth(0); b.setMaximumWidth(b.sizeHint().width()+18); b.clicked.connect(callback); buttons.addWidget(b)
        buttons.addStretch(1); root.addLayout(buttons); self._populate_metadata_filters(); self.refresh()

    def _populate_metadata_filters(self) -> None:
        countries = sorted({c.country for c in self.search_service.channels if c.country})
        languages = sorted({part.strip() for c in self.search_service.channels for part in c.language.split("/") if part.strip()})
        for value in countries: self.country_filter.addItem(value, value)
        for value in languages: self.language_filter.addItem(value, value)

    def _visible_channels(self):
        query=self.filter_edit.text().strip().casefold()
        channels=list(self.search_service.channels)
        if query:
            channels=[c for c in channels if query in str(c.target) or query in c.name.casefold() or query in c.country.casefold() or query in c.language.casefold()]
        country=str(self.country_filter.currentData() or "")
        language=str(self.language_filter.currentData() or "")
        if country: channels=[c for c in channels if c.country == country]
        if language: channels=[c for c in channels if language in c.language.split("/")]
        favorites={(f.target,f.timeslot,f.call_type):f for f in self.service.favorites}
        channels.sort(key=lambda c: (0 if (c.target,c.timeslot,c.call_type) in favorites else 1, favorites.get((c.target,c.timeslot,c.call_type)).position if (c.target,c.timeslot,c.call_type) in favorites else 999999, c.target))
        return channels

    def refresh(self, *_args) -> None:
        current=self.table.currentRow(); self.table.setRowCount(0)
        for row, channel in enumerate(self._visible_channels()):
            fav=self.service.find(channel.target, channel.timeslot, channel.call_type)
            values=["★" if fav else "☆", fav.custom_name if fav else "", fav.default_name if fav else channel.name, str(channel.target), str(fav.timeslot if fav else channel.timeslot), fav.call_type_short if fav else ("G" if channel.call_type=="group" else "P"), channel.country, channel.language, self._note_preview(fav.note if fav else "")]
            self.table.insertRow(row)
            for col,value in enumerate(values):
                item=QTableWidgetItem(value); item.setData(Qt.ItemDataRole.UserRole, channel)
                if col==8 and fav: item.setToolTip(fav.note)
                if col in {0,3,4,5}: item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(row,col,item)
        if self.table.rowCount(): self.table.selectRow(max(0,min(current,self.table.rowCount()-1)))
        self.table.resizeColumnsToContents()

    @staticmethod
    def _note_preview(note: str, length: int=40) -> str:
        compact=" ".join(str(note).split()); return compact if len(compact)<=length else compact[:length-1].rstrip()+"…"

    def _selected_channel(self) -> DmrChannel | None:
        row=self.table.currentRow(); item=self.table.item(row,0) if row>=0 else None; value=item.data(Qt.ItemDataRole.UserRole) if item else None
        return value if isinstance(value,DmrChannel) else None

    def _item_clicked(self, item: QTableWidgetItem) -> None:
        if item.column()!=0: return
        channel=self._selected_channel()
        if not channel: return
        fav=self.service.find(channel.target,channel.timeslot,channel.call_type)
        if fav: self.service.remove(fav)
        else:
            dialog=FavoriteEditDialog(channel,parent=self); dialog.favorite_check.setChecked(True)
            if dialog.exec()!=QDialog.DialogCode.Accepted or not dialog.mark_as_favorite: return
            self.service.add(dialog.favorite())
        self.search_service.set_favorites(self.service.favorites); self.refresh(); self.changed.emit()

    def add_channel(self, channel: DmrChannel) -> bool:
        existing=self.service.find(channel.target,channel.timeslot,channel.call_type)
        dialog=FavoriteEditDialog(channel,existing,self)
        if dialog.exec()!=QDialog.DialogCode.Accepted: return False
        if dialog.mark_as_favorite:
            if existing: self.service.update(existing,dialog.favorite(existing.position))
            else: self.service.add(dialog.favorite())
        elif existing:
            self.service.remove(existing)
        self.search_service.set_favorites(self.service.favorites); self.refresh(); self.changed.emit(); return True

    def edit_selected(self) -> None:
        channel=self._selected_channel()
        if channel: self.add_channel(channel)

    def set_favorite(self) -> None:
        channel=self._selected_channel()
        if not channel: return
        existing=self.service.find(channel.target,channel.timeslot,channel.call_type)
        if existing: return
        dialog=FavoriteEditDialog(channel,None,self); dialog.favorite_check.setChecked(True)
        if dialog.exec()!=QDialog.DialogCode.Accepted or not dialog.mark_as_favorite: return
        self.service.add(dialog.favorite()); self.search_service.set_favorites(self.service.favorites); self.refresh(); self.changed.emit()

    def remove_favorite(self) -> None:
        channel=self._selected_channel()
        if not channel: return
        fav=self.service.find(channel.target,channel.timeslot,channel.call_type)
        if fav: self.service.remove(fav); self.search_service.set_favorites(self.service.favorites); self.refresh(); self.changed.emit()

    def use_selected(self) -> None:
        channel=self._selected_channel()
        if channel:
            fav=self.service.find(channel.target,channel.timeslot,channel.call_type)
            self.channel_requested.emit(fav.to_dmr_channel() if fav else channel)

    def update_brandmeister(self) -> None:
        try: count=self.catalog_service.update_from_brandmeister()
        except Exception as exc: QMessageBox.warning(self,"Aktualisierung fehlgeschlagen",str(exc)); return
        self.search_service.reload(); self.search_service.set_favorites(self.service.favorites)
        country=self.country_filter.currentData(); language=self.language_filter.currentData()
        self.country_filter.blockSignals(True); self.language_filter.blockSignals(True)
        self.country_filter.clear(); self.country_filter.addItem("Alle Länder", "")
        self.language_filter.clear(); self.language_filter.addItem("Alle Sprachen", "")
        self._populate_metadata_filters()
        self.country_filter.blockSignals(False); self.language_filter.blockSignals(False)
        self.refresh(); self.changed.emit()
        QMessageBox.information(self,"BrandMeister",f"{count} Talkgroups wurden geladen.")

    def import_favorites(self) -> None:
        filename,_=QFileDialog.getOpenFileName(self,"Favoriten importieren","","Favoriten (*.json *.csv)")
        if not filename:return
        try: count=self.service.import_csv(Path(filename)) if filename.lower().endswith('.csv') else self.service.import_json(Path(filename))
        except Exception as exc: QMessageBox.warning(self,"Import fehlgeschlagen",str(exc)); return
        self.search_service.set_favorites(self.service.favorites); self.refresh(); self.changed.emit(); QMessageBox.information(self,"Import",f"{count} Favoriten importiert.")

    def export_favorites(self) -> None:
        filename,selected=QFileDialog.getSaveFileName(self,"Favoriten exportieren","CarenDMR_Favoriten.json","JSON (*.json);;CSV (*.csv)")
        if not filename:return
        try:
            if filename.lower().endswith('.csv') or selected.startswith('CSV'):
                if not filename.lower().endswith('.csv'): filename += '.csv'
                self.service.export_csv(Path(filename))
            else:
                if not filename.lower().endswith('.json'): filename += '.json'
                self.service.export_json(Path(filename))
        except Exception as exc: QMessageBox.warning(self,"Export fehlgeschlagen",str(exc)); return
        QMessageBox.information(self,"Export","Favoriten wurden exportiert.")

    def keyPressEvent(self,event) -> None:
        if event.key() in (Qt.Key.Key_Return,Qt.Key.Key_Enter): self.use_selected(); event.accept(); return
        super().keyPressEvent(event)
