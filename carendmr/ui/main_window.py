"""Kleines barrierefreies Read-only-Hauptfenster für CarenDMR."""

from __future__ import annotations

import queue
import tkinter as tk
from pathlib import Path
from threading import Thread
from tkinter import messagebox, ttk

from carendmr.application import AudioSendService, EventService, ReceiveService
from carendmr.audio import AudioDirection
from carendmr.domain import ApplicationEvent, ApplicationState, ConnectionState, EventLevel
from carendmr.version import __version__


class MainWindow:
    """Native Tk-Steuerelemente mit stabiler Fokusreihenfolge und Textlabels."""

    def __init__(self, project_root: Path) -> None:
        self.project_root = Path(project_root)
        self.root = tk.Tk()
        self.root.title(f"CarenDMR {__version__}")
        self.root.minsize(620, 480)

        self.events = EventService()
        self.receive_service = ReceiveService(self.project_root, events=self.events)
        self.audio_send_service = AudioSendService(
            self.project_root,
            mute_receive=self.receive_service.mute_audio_output,
            unmute_receive=self.receive_service.unmute_audio_output,
        )
        self._updates: queue.SimpleQueue[tuple[str, object]] = queue.SimpleQueue()

        self.brandmeister_var = tk.StringVar(value="Getrennt")
        self.receive_var = tk.StringVar(value="Inaktiv")
        self.server_var = tk.StringVar(value="Nicht verbunden")
        self.talkgroup_var = tk.StringVar(value="91")
        self.timeslot_var = tk.StringVar(value="2")
        self.audio_var = tk.StringVar(value="Inaktiv")
        self.statistics_var = tk.StringVar(value="Noch keine Empfangsdaten")
        self.current_callsign_var = tk.StringVar(value="Nicht bekannt")
        self.current_name_var = tk.StringVar(value="Nicht bekannt")
        self.current_location_var = tk.StringVar(value="Nicht bekannt")
        self.current_country_var = tk.StringVar(value="Nicht bekannt")
        self.current_dmr_id_var = tk.StringVar(value="Kein aktiver Sprecher")
        self.current_target_var = tk.StringVar(value="Talkgroup 91, Timeslot 2")
        self.current_duration_var = tk.StringVar(value="0 Sekunden")
        self.contacts_var = tk.StringVar(value=self._contacts_status_text())
        self.microphone_var = tk.StringVar(value="Noch nicht geprüft")
        self.microphone_status_var = tk.StringVar(value="Mikrofon noch nicht geprüft")
        self.microphone_level_var = tk.DoubleVar(value=0.0)
        self.microphone_gain_var = tk.DoubleVar(value=float(self.audio_send_service.gain_percent))
        self.microphone_gain_text_var = tk.StringVar(value=f"{self.audio_send_service.gain_percent} %")
        self.output_volume_var = tk.DoubleVar(value=float(self.audio_send_service.output_volume_percent))
        self.output_volume_text_var = tk.StringVar(value=f"{self.audio_send_service.output_volume_percent} %")
        self.output_muted_var = tk.BooleanVar(value=self.audio_send_service.user_muted)
        self.output_agc_var = tk.BooleanVar(value=self.audio_send_service.agc_enabled)
        self.output_level_var = tk.DoubleVar(value=0.0)
        self.output_status_var = tk.StringVar(value="AGC EIN; Ausgabe 100 %; Stumm AUS")
        self._settings_save_after_id: str | None = None
        self.receive_service.set_output_volume_percent(self.audio_send_service.output_volume_percent)
        self.receive_service.set_user_muted(self.audio_send_service.user_muted)
        self.receive_service.set_agc_enabled(self.audio_send_service.agc_enabled)
        self.receive_service.set_output_level_callback(
            lambda level: self._updates.put(("output_level", level))
        )
        self._update_output_status()
        self.microphone_diagnostics_var = tk.StringVar(
            value="16.000 Hz, Mono, PCM; keine Funkübertragung"
        )
        self._microphone_by_label: dict[str, object] = {}

        self._build()
        self.receive_service.state_store.subscribe(
            lambda state: self._updates.put(("state", state))
        )
        self.events.subscribe(lambda event: self._updates.put(("event", event)))
        self.root.protocol("WM_DELETE_WINDOW", self._close)
        self.root.bind("<Escape>", lambda _event: self._close())
        self.root.bind("<Control-q>", lambda _event: self._close())
        self.root.bind("<Control-r>", lambda _event: self._start())
        self.root.bind("<Control-t>", lambda _event: self._stop())
        self.root.bind("<Control-m>", lambda _event: self._toggle_output_mute())
        self.root.after(100, self._process_updates)
        self.connect_button.focus_set()

    def _build(self) -> None:
        outer = ttk.Frame(self.root, padding=12)
        outer.grid(row=0, column=0, sticky="nsew")
        self.root.rowconfigure(0, weight=1)
        self.root.columnconfigure(0, weight=1)
        outer.rowconfigure(1, weight=1)
        outer.columnconfigure(0, weight=1)

        heading = ttk.Label(outer, text="CarenDMR", font=("TkDefaultFont", 16, "bold"))
        heading.grid(row=0, column=0, sticky="w", pady=(0, 8))

        self.notebook = ttk.Notebook(outer, takefocus=True)
        self.notebook.grid(row=1, column=0, sticky="nsew")
        reception = ttk.Frame(self.notebook, padding=12)
        history = ttk.Frame(self.notebook, padding=12)
        transmit = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(reception, text="Empfang")
        self.notebook.add(history, text="QSO-Historie")
        self.notebook.add(transmit, text="Senden – lokaler Audiotest")
        self._build_reception_tab(reception)
        self._build_history_tab(history)
        self._build_transmit_tab(transmit)

    def _build_reception_tab(self, outer: ttk.Frame) -> None:
        outer.columnconfigure(1, weight=1)
        outer.rowconfigure(11, weight=1)
        fields = (
            ("BrandMeister", self.brandmeister_var),
            ("Empfang", self.receive_var),
            ("Server", self.server_var),
            ("Talkgroup", self.talkgroup_var),
            ("Timeslot", self.timeslot_var),
            ("Audioausgabe", self.audio_var),
        )
        for row, (label, variable) in enumerate(fields):
            ttk.Label(outer, text=f"{label}:").grid(row=row, column=0, sticky="nw", padx=(0, 12), pady=3)
            ttk.Label(outer, textvariable=variable, takefocus=True).grid(row=row, column=1, sticky="nw", pady=3)

        current_frame = ttk.LabelFrame(outer, text="Aktuelle Station", padding=10)
        current_frame.grid(row=6, column=0, columnspan=2, sticky="ew", pady=(10, 4))
        current_frame.columnconfigure(1, weight=1)
        current_fields = (
            ("Rufzeichen", self.current_callsign_var),
            ("Name", self.current_name_var),
            ("Ort/Region", self.current_location_var),
            ("Land", self.current_country_var),
            ("DMR-ID", self.current_dmr_id_var),
            ("Ziel", self.current_target_var),
            ("Sprechdauer", self.current_duration_var),
        )
        for row, (label, variable) in enumerate(current_fields):
            ttk.Label(current_frame, text=f"{label}:").grid(row=row, column=0, sticky="nw", padx=(0, 12), pady=2)
            ttk.Label(current_frame, textvariable=variable, takefocus=True).grid(row=row, column=1, sticky="nw", pady=2)

        contacts_frame = ttk.LabelFrame(outer, text="Kontaktdatenbank", padding=10)
        contacts_frame.grid(row=7, column=0, columnspan=2, sticky="ew", pady=(6, 4))
        contacts_frame.columnconfigure(0, weight=1)
        ttk.Label(contacts_frame, textvariable=self.contacts_var, wraplength=440, takefocus=True).grid(row=0, column=0, sticky="w", padx=(0, 12))
        self.contacts_button = ttk.Button(contacts_frame, text="Kontaktdaten aktualisieren", command=self._update_contacts)
        self.contacts_button.grid(row=0, column=1, sticky="e")

        ttk.Label(outer, text="Empfangsstatistik:").grid(row=8, column=0, sticky="nw", padx=(0, 12), pady=(8, 3))
        ttk.Label(outer, textvariable=self.statistics_var, wraplength=460, takefocus=True).grid(row=8, column=1, sticky="nw", pady=(8, 3))

        ttk.Label(outer, text="Ereignisprotokoll:").grid(row=9, column=0, columnspan=2, sticky="w", pady=(12, 4))
        log_frame = ttk.Frame(outer)
        log_frame.grid(row=10, column=0, columnspan=2, sticky="nsew")
        log_frame.rowconfigure(0, weight=1)
        log_frame.columnconfigure(0, weight=1)
        self.event_log = tk.Listbox(log_frame, activestyle="dotbox", exportselection=False, selectmode=tk.BROWSE, takefocus=True)
        scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.event_log.yview)
        self.event_log.configure(yscrollcommand=scrollbar.set)
        self.event_log.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        buttons = ttk.Frame(outer)
        buttons.grid(row=11, column=0, columnspan=2, sticky="ew", pady=(12, 0))
        self.connect_button = ttk.Button(buttons, text="Verbinden und empfangen", command=self._start)
        self.disconnect_button = ttk.Button(buttons, text="Trennen", command=self._stop, state="disabled")
        self.exit_button = ttk.Button(buttons, text="Beenden", command=self._close)
        self.connect_button.grid(row=0, column=0, padx=(0, 8))
        self.disconnect_button.grid(row=0, column=1, padx=(0, 8))
        self.exit_button.grid(row=0, column=2)
        ttk.Label(outer, text="Tastenkürzel: Strg+R verbinden, Strg+T trennen, Esc oder Strg+Q beenden.", wraplength=560).grid(row=12, column=0, columnspan=2, sticky="w", pady=(10, 0))

    def _build_transmit_tab(self, frame: ttk.Frame) -> None:
        frame.columnconfigure(1, weight=1)
        ttk.Label(
            frame,
            text="Lokaler Mikrofontest – es werden keine DMR-Daten gesendet.",
            wraplength=560,
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 12))

        ttk.Label(frame, text="Mikrofon:").grid(row=1, column=0, sticky="w", padx=(0, 12), pady=4)
        self.microphone_combo = ttk.Combobox(
            frame,
            textvariable=self.microphone_var,
            state="readonly",
            takefocus=True,
        )
        self.microphone_combo.grid(row=1, column=1, sticky="ew", pady=4)
        self.microphone_combo.bind("<<ComboboxSelected>>", self._select_microphone)

        ttk.Button(frame, text="Mikrofone neu einlesen", command=self._scan_microphones).grid(
            row=2, column=1, sticky="w", pady=(2, 10)
        )
        ttk.Label(frame, text="Pegel:").grid(row=3, column=0, sticky="w", padx=(0, 12), pady=4)
        self.microphone_level = ttk.Progressbar(
            frame,
            variable=self.microphone_level_var,
            maximum=100,
            mode="determinate",
            takefocus=True,
        )
        self.microphone_level.grid(row=3, column=1, sticky="ew", pady=4)

        ttk.Label(frame, text="Mikrofonverstärkung:").grid(row=4, column=0, sticky="w", padx=(0, 12), pady=4)
        gain_frame = ttk.Frame(frame)
        gain_frame.grid(row=4, column=1, sticky="ew", pady=4)
        gain_frame.columnconfigure(0, weight=1)
        self.microphone_gain_scale = ttk.Scale(
            gain_frame, from_=25, to=200, variable=self.microphone_gain_var,
            command=self._on_microphone_gain_changed, takefocus=True,
        )
        self.microphone_gain_scale.grid(row=0, column=0, sticky="ew")
        ttk.Label(gain_frame, textvariable=self.microphone_gain_text_var, width=7, takefocus=True).grid(row=0, column=1, padx=(10, 0))

        ttk.Label(frame, text="Ausgabelautstärke:").grid(row=5, column=0, sticky="w", padx=(0, 12), pady=4)
        volume_frame = ttk.Frame(frame)
        volume_frame.grid(row=5, column=1, sticky="ew", pady=4)
        volume_frame.columnconfigure(0, weight=1)
        ttk.Scale(
            volume_frame, from_=0, to=400, variable=self.output_volume_var,
            command=self._on_output_volume_changed, takefocus=True,
        ).grid(row=0, column=0, sticky="ew")
        ttk.Label(volume_frame, textvariable=self.output_volume_text_var, width=7, takefocus=True).grid(row=0, column=1, padx=(10, 0))

        ttk.Label(frame, text="Audioausgabe:").grid(row=6, column=0, sticky="w", padx=(0, 12), pady=4)
        output_flags = ttk.Frame(frame)
        output_flags.grid(row=6, column=1, sticky="w", pady=4)
        ttk.Checkbutton(
            output_flags, text="Stumm (Strg+M)", variable=self.output_muted_var,
            command=self._on_output_mute_changed, takefocus=True,
        ).grid(row=0, column=0, padx=(0, 14))
        ttk.Checkbutton(
            output_flags, text="Lautstärke automatisch anpassen (AGC)",
            variable=self.output_agc_var, command=self._on_output_agc_changed,
            takefocus=True,
        ).grid(row=0, column=1)

        ttk.Label(frame, text="DMR-Ausgangspegel:").grid(row=7, column=0, sticky="w", padx=(0, 12), pady=4)
        ttk.Progressbar(
            frame, variable=self.output_level_var, maximum=100,
            mode="determinate", takefocus=True,
        ).grid(row=7, column=1, sticky="ew", pady=4)

        ttk.Label(frame, text="Audiostatus:").grid(row=8, column=0, sticky="nw", padx=(0, 12), pady=4)
        ttk.Label(frame, textvariable=self.output_status_var, wraplength=480, takefocus=True).grid(row=8, column=1, sticky="w", pady=4)
        ttk.Label(frame, text="Status:").grid(row=9, column=0, sticky="nw", padx=(0, 12), pady=4)
        ttk.Label(frame, textvariable=self.microphone_status_var, wraplength=480, takefocus=True).grid(row=9, column=1, sticky="w", pady=4)
        ttk.Label(frame, text="Format:").grid(row=10, column=0, sticky="nw", padx=(0, 12), pady=4)
        ttk.Label(frame, textvariable=self.microphone_diagnostics_var, wraplength=480, takefocus=True).grid(row=10, column=1, sticky="w", pady=4)

        controls = ttk.Frame(frame)
        controls.grid(row=11, column=0, columnspan=2, sticky="w", pady=(14, 0))
        self.record_button = ttk.Button(controls, text="5 Sekunden Testaufnahme", command=self._record_microphone_test)
        self.play_button = ttk.Button(controls, text="Testaufnahme wiedergeben", command=self._play_microphone_test, state="disabled")
        self.loopback_button = ttk.Button(controls, text="4 Sekunden Loopback", command=self._run_audio_loopback)
        self.record_button.grid(row=0, column=0, padx=(0, 8))
        self.play_button.grid(row=0, column=1, padx=(0, 8))
        self.loopback_button.grid(row=0, column=2)
        ttk.Label(
            frame,
            text=("Version 0.0.18 enthält bewusst keine PTT, keinen AMBE-Encoder "
                  "und keine Netzwerk-Sendefunktion."),
            wraplength=560,
        ).grid(row=12, column=0, columnspan=2, sticky="w", pady=(16, 0))
        self.root.after(0, self._scan_microphones)

    def _build_history_tab(self, frame: ttk.Frame) -> None:
        frame.rowconfigure(1, weight=1)
        frame.columnconfigure(0, weight=1)
        controls = ttk.Frame(frame)
        controls.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        ttk.Label(controls, text="Abgeschlossene empfangene Sprechdurchgänge").grid(row=0, column=0, sticky="w")
        ttk.Button(controls, text="Aktualisieren", command=self._refresh_history).grid(row=0, column=1, padx=(12, 0))
        columns = ("time", "callsign", "name", "country", "dmr_id", "target", "duration")
        self.history_tree = ttk.Treeview(frame, columns=columns, show="headings", takefocus=True)
        headings = {
            "time": "Zeit", "callsign": "Rufzeichen", "name": "Name",
            "country": "Land", "dmr_id": "DMR-ID", "target": "Ziel",
            "duration": "Dauer",
        }
        widths = {"time": 145, "callsign": 90, "name": 150, "country": 110, "dmr_id": 90, "target": 90, "duration": 70}
        for column in columns:
            self.history_tree.heading(column, text=headings[column])
            self.history_tree.column(column, width=widths[column], anchor="w")
        scroll = ttk.Scrollbar(frame, orient="vertical", command=self.history_tree.yview)
        self.history_tree.configure(yscrollcommand=scroll.set)
        self.history_tree.grid(row=1, column=0, sticky="nsew")
        scroll.grid(row=1, column=1, sticky="ns")
        self._refresh_history()

    def _refresh_history(self) -> None:
        if not hasattr(self, "history_tree"):
            return
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)
        for entry in self.receive_service.history.list_recent():
            try:
                from datetime import datetime
                timestamp = datetime.fromisoformat(entry.ended_at).astimezone().strftime("%d.%m.%Y %H:%M:%S")
            except ValueError:
                timestamp = entry.ended_at
            target = f"TG{entry.talkgroup}/TS{entry.timeslot}"
            self.history_tree.insert("", tk.END, values=(
                timestamp, entry.callsign or "Unbekannt", entry.name, entry.country,
                entry.source_id, target, f"{entry.duration_seconds:.0f} s",
            ))

    def _contacts_status_text(self) -> str:
        info = self.receive_service.contacts.info()
        if info.record_count == 0:
            return "Noch nicht installiert. Quelle: RadioID.net"
        return (
            f"Quelle: {info.source}; Datensätze: {info.record_count:,}; "
            f"Stand: {info.updated_at}"
        ).replace(",", ".")

    def _update_contacts(self) -> None:
        self.contacts_button.configure(state="disabled")
        self.contacts_var.set("RadioID-Kontaktdaten werden heruntergeladen und importiert …")
        self.events.publish("Aktualisierung der RadioID-Kontaktdaten gestartet.")

        def worker() -> None:
            try:
                count, updated_at = self.receive_service.contacts.update()
                self._updates.put(("contacts_updated", (count, updated_at)))
            except Exception as error:
                self._updates.put(("contacts_error", error))

        Thread(target=worker, name="CarenDMR-Contacts", daemon=True).start()

    def _scan_microphones(self) -> None:
        try:
            devices = self.audio_send_service.microphones()
            self._microphone_by_label = {
                device.display_name(AudioDirection.INPUT): device for device in devices
            }
            labels = list(self._microphone_by_label)
            self.microphone_combo.configure(values=labels)
            selected = self.audio_send_service.selected_input
            if selected is not None:
                label = selected.display_name(AudioDirection.INPUT)
                self.microphone_var.set(label)
                self.microphone_status_var.set(f"Mikrofon bereit: {selected.name}")
            elif labels:
                self.microphone_var.set(labels[0])
            else:
                self.microphone_var.set("Kein Mikrofon gefunden")
                self.microphone_status_var.set("Kein Mikrofon verfügbar")
        except Exception as error:
            self.microphone_status_var.set(f"Mikrofonprüfung fehlgeschlagen: {error}")

    def _select_microphone(self, _event: object | None = None) -> None:
        device = self._microphone_by_label.get(self.microphone_var.get())
        if device is None:
            return
        try:
            selected = self.audio_send_service.select_microphone(device.stable_key)
            self.microphone_status_var.set(f"Mikrofon ausgewählt: {selected.name}")
        except Exception as error:
            self.microphone_status_var.set(f"Mikrofon konnte nicht gewählt werden: {error}")

    def _on_microphone_gain_changed(self, value: str) -> None:
        gain = int(round(float(value)))
        self.microphone_gain_text_var.set(f"{gain} %")
        try:
            self.audio_send_service.set_gain_percent(gain)
            self._schedule_audio_settings_save()
        except Exception as error:
            self.microphone_status_var.set(f"Mikrofonverstärkung ist ungültig: {error}")

    def _on_output_volume_changed(self, value: str) -> None:
        volume = int(round(float(value)))
        self.output_volume_text_var.set(f"{volume} %")
        self.audio_send_service.set_output_volume_percent(volume)
        self.receive_service.set_output_volume_percent(volume)
        self._update_output_status()
        self._schedule_audio_settings_save()

    def _on_output_mute_changed(self) -> None:
        muted = bool(self.output_muted_var.get())
        self.audio_send_service.set_user_muted(muted)
        self.receive_service.set_user_muted(muted)
        self._update_output_status()
        self._schedule_audio_settings_save()

    def _on_output_agc_changed(self) -> None:
        enabled = bool(self.output_agc_var.get())
        self.audio_send_service.set_agc_enabled(enabled)
        self.receive_service.set_agc_enabled(enabled)
        self._update_output_status()
        self._schedule_audio_settings_save()

    def _update_output_status(self) -> None:
        self.output_status_var.set(
            f"AGC {'EIN' if self.output_agc_var.get() else 'AUS'}; "
            f"Ausgabe {int(round(self.output_volume_var.get()))} %; "
            f"Stumm {'EIN' if self.output_muted_var.get() else 'AUS'}"
        )

    def _toggle_output_mute(self) -> None:
        self.output_muted_var.set(not self.output_muted_var.get())
        self._on_output_mute_changed()

    def _schedule_audio_settings_save(self) -> None:
        if self._settings_save_after_id is not None:
            self.root.after_cancel(self._settings_save_after_id)
        self._settings_save_after_id = self.root.after(600, self._save_audio_settings)

    def _save_audio_settings(self) -> None:
        self._settings_save_after_id = None
        try:
            self.audio_send_service.save_settings()
        except Exception as error:
            self.microphone_status_var.set(f"Audioeinstellungen konnten nicht gespeichert werden: {error}")

    def _set_audio_buttons(self, enabled: bool) -> None:
        state = "normal" if enabled else "disabled"
        self.record_button.configure(state=state)
        self.loopback_button.configure(state=state)
        if not enabled:
            self.play_button.configure(state="disabled")

    def _record_microphone_test(self) -> None:
        self._set_audio_buttons(False)
        self.microphone_level_var.set(0.0)
        self.microphone_status_var.set("Testaufnahme läuft für 5 Sekunden …")

        def worker() -> None:
            try:
                diagnostics = self.audio_send_service.record_test(
                    duration_seconds=5.0,
                    level_callback=lambda level: self._updates.put(("mic_level", level)),
                )
                self._updates.put(("mic_recorded", diagnostics))
            except Exception as error:
                self._updates.put(("mic_error", error))

        Thread(target=worker, name="CarenDMR-Microphone-Test", daemon=True).start()

    def _play_microphone_test(self) -> None:
        self._set_audio_buttons(False)
        self.microphone_status_var.set("Testaufnahme wird lokal wiedergegeben …")

        def worker() -> None:
            try:
                self.audio_send_service.play_test()
                self._updates.put(("mic_played", None))
            except Exception as error:
                self._updates.put(("mic_error", error))

        Thread(target=worker, name="CarenDMR-Microphone-Playback", daemon=True).start()

    def _run_audio_loopback(self) -> None:
        self._set_audio_buttons(False)
        self.microphone_status_var.set("Loopback-Test läuft für 4 Sekunden …")

        def worker() -> None:
            try:
                self.audio_send_service.run_loopback(duration_seconds=4.0)
                self._updates.put(("mic_loopback", None))
            except Exception as error:
                self._updates.put(("mic_error", error))

        Thread(target=worker, name="CarenDMR-Audio-Loopback", daemon=True).start()

    def _start(self) -> None:
        if self.receive_service.start():
            self.connect_button.configure(state="disabled")
            self.disconnect_button.configure(state="normal")
        else:
            self.events.publish("Der Empfang läuft bereits.")

    def _stop(self) -> None:
        self.receive_service.stop()

    def _close(self) -> None:
        if self._settings_save_after_id is not None:
            self.root.after_cancel(self._settings_save_after_id)
            self._settings_save_after_id = None
        try:
            self.audio_send_service.save_settings()
        except Exception:
            pass
        if self.receive_service.is_running:
            self.receive_service.stop()
            if not self.receive_service.wait(3.0):
                messagebox.showwarning(
                    "CarenDMR",
                    "Der Empfang wird noch beendet. Bitte das Fenster gleich erneut schließen.",
                    parent=self.root,
                )
                return
        self.root.destroy()

    def _process_updates(self) -> None:
        try:
            while True:
                kind, value = self._updates.get_nowait()
                if kind == "state":
                    self._apply_state(value)  # type: ignore[arg-type]
                elif kind == "event":
                    self._append_event(value)  # type: ignore[arg-type]
                    if "Sprechdurchgang von" in value.message:
                        self._refresh_history()
                elif kind == "mic_level":
                    self.microphone_level_var.set(float(value))
                elif kind == "output_level":
                    self.output_level_var.set(float(value))
                elif kind == "mic_recorded":
                    diagnostics = value
                    self.microphone_status_var.set(
                        f"Testaufnahme abgeschlossen. Spitzenpegel {diagnostics.peak_percent:.0f} Prozent."
                    )
                    self.microphone_diagnostics_var.set(
                        f"{diagnostics.sample_rate:,} Hz, Mono, PCM; "
                        f"{diagnostics.captured_samples:,} Samples; "
                        f"{diagnostics.captured_samples / diagnostics.sample_rate:.2f} Sekunden; "
                        f"{diagnostics.device_name}."
                    .replace(",", "."))
                    self._set_audio_buttons(True)
                    self.play_button.configure(state="normal")
                elif kind == "mic_played":
                    self.microphone_status_var.set("Testaufnahme wurde vollständig wiedergegeben.")
                    self._set_audio_buttons(True)
                    self.play_button.configure(state="normal")
                elif kind == "mic_loopback":
                    self.microphone_status_var.set("Loopback-Test abgeschlossen.")
                    self._set_audio_buttons(True)
                    if self.audio_send_service.has_recording:
                        self.play_button.configure(state="normal")
                elif kind == "mic_error":
                    self.microphone_status_var.set(f"Audio-Test fehlgeschlagen: {value}")
                    self._set_audio_buttons(True)
                    if self.audio_send_service.has_recording:
                        self.play_button.configure(state="normal")
                elif kind == "contacts_updated":
                    count, updated_at = value  # type: ignore[misc]
                    self.contacts_var.set(
                        f"Quelle: RadioID.net; Datensätze: {count:,}; Stand: {updated_at}".replace(",", ".")
                    )
                    self.contacts_button.configure(state="normal")
                    self.events.publish(f"Kontaktdatenbank aktualisiert: {count} Datensätze.")
                elif kind == "contacts_error":
                    self.contacts_button.configure(state="normal")
                    self.contacts_var.set(self._contacts_status_text())
                    self.events.publish(
                        f"Kontaktdaten konnten nicht aktualisiert werden: {value}",
                        EventLevel.ERROR,
                    )
        except queue.Empty:
            pass
        if self.root.winfo_exists():
            self.root.after(100, self._process_updates)

    def _apply_state(self, state: ApplicationState) -> None:
        if state.connection is ConnectionState.CONNECTING:
            brandmeister_text = "Verbindung wird hergestellt"
        elif state.brandmeister_connected:
            brandmeister_text = "Verbunden"
        elif state.connection is ConnectionState.ERROR:
            brandmeister_text = "Fehler"
        else:
            brandmeister_text = "Getrennt"
        self.brandmeister_var.set(brandmeister_text)
        self.receive_var.set("Aktiv" if state.receive_active else "Inaktiv")
        self.server_var.set(state.server)
        self.audio_var.set("Aktiv" if state.audio_active else "Inaktiv")
        call = state.current_call
        if call is None:
            self.current_callsign_var.set("Nicht bekannt")
            self.current_name_var.set("Nicht bekannt")
            self.current_location_var.set("Nicht bekannt")
            self.current_country_var.set("Nicht bekannt")
            self.current_dmr_id_var.set("Kein aktiver Sprecher")
            self.current_target_var.set(
                f"Talkgroup {state.talkgroup}, Timeslot {state.timeslot}"
            )
            self.current_duration_var.set("0 Sekunden")
        else:
            contact = call.contact
            self.current_callsign_var.set(contact.callsign if contact else "Nicht gefunden")
            self.current_name_var.set(
                contact.display_name if contact and contact.display_name else "Nicht angegeben"
            )
            location = " / ".join(
                part for part in ((contact.city if contact else ""), (contact.state if contact else "")) if part
            )
            self.current_location_var.set(location or "Nicht angegeben")
            self.current_country_var.set(
                contact.country if contact and contact.country else "Nicht angegeben"
            )
            self.current_dmr_id_var.set(str(call.source_id))
            self.current_target_var.set(
                f"Talkgroup {call.talkgroup}, Timeslot {call.timeslot}"
            )
            self.current_duration_var.set(f"{call.elapsed_seconds:.0f} Sekunden")
        stats = state.statistics
        self.statistics_var.set(
            f"Laufzeit {stats.elapsed_seconds:.0f} Sekunden; "
            f"Datagramme {stats.datagrams}; Sprachbursts {stats.voice_bursts}; "
            f"Dekodierfehler {stats.decode_errors}; verdeckte Bursts {stats.concealed_bursts}."
        )
        running = state.connection in {
            ConnectionState.CONNECTING,
            ConnectionState.CONNECTED,
            ConnectionState.RECEIVING,
            ConnectionState.STOPPING,
        }
        self.connect_button.configure(state="disabled" if running else "normal")
        self.disconnect_button.configure(state="normal" if running else "disabled")

    def _append_event(self, event: ApplicationEvent) -> None:
        self.event_log.insert(tk.END, event.display_text)
        self.event_log.see(tk.END)

    def run(self) -> int:
        self.events.publish("CarenDMR ist bereit. Der Empfang ist noch nicht verbunden.")
        self.root.mainloop()
        return 0


def run_gui(project_root: Path) -> int:
    return MainWindow(project_root).run()
