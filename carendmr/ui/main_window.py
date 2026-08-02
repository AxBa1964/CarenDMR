"""Kleines barrierefreies Read-only-Hauptfenster für CarenDMR."""

from __future__ import annotations

import queue
import tkinter as tk
from pathlib import Path
from threading import Event, Thread
from time import monotonic
from tkinter import filedialog, messagebox, ttk

from carendmr.application import AudioSendService, EncoderService, EventService, ParrotTestService, ReceiveService
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
        self.encoder_service = EncoderService(self.project_root)
        self.audio_send_service = AudioSendService(
            self.project_root,
            mute_receive=self.receive_service.mute_audio_output,
            unmute_receive=self.receive_service.unmute_audio_output,
        )
        self.parrot_test_service = ParrotTestService(
            self.project_root, audio_service=self.audio_send_service,
            encoder_service=self.encoder_service,
        )
        self._updates: queue.SimpleQueue[tuple[str, object]] = queue.SimpleQueue()
        self._tx_stop_event: Event | None = None
        self._tx_started_at: float | None = None
        self._tx_active = False
        self._tx_recording = False
        self._tx_pointer_grabbed = False

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
        configured_plugin = self.encoder_service.configured_plugin_path
        self.encoder_plugin_var = tk.StringVar(
            value=str(configured_plugin) if configured_plugin else "Noch kein Plugin ausgewählt"
        )
        self.encoder_status_var = tk.StringVar(
            value="AMBE-Encoder nicht geprüft; Senden ist weiterhin gesperrt."
        )
        self.parrot_status_var = tk.StringVar(
            value="Bereit für einen privaten Test, sobald Encoder und Mikrofon geprüft sind."
        )
        self.transmit_optimizer_var = tk.BooleanVar(value=True)
        self.tx_safety_limit_var = tk.IntVar(
            value=self.audio_send_service.tx_safety_limit_seconds
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
        transmit_history = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(reception, text="Empfang")
        self.notebook.add(history, text="QSO-Historie")
        self.notebook.add(transmit, text="Senden")
        self.notebook.add(transmit_history, text="Sendehistorie")
        self._build_reception_tab(reception)
        self._build_history_tab(history)
        self._build_transmit_tab(transmit)
        self._build_transmit_history_tab(transmit_history)

    def _build_reception_tab(self, outer: ttk.Frame) -> None:
        outer.columnconfigure(1, weight=1)
        outer.rowconfigure(11, weight=1)
        fields = (
            ("BrandMeister", self.brandmeister_var),
            ("Empfang", self.receive_var),
            ("Server", self.server_var),
        )
        for row, (label, variable) in enumerate(fields):
            ttk.Label(outer, text=f"{label}:").grid(row=row, column=0, sticky="nw", padx=(0, 12), pady=3)
            ttk.Label(outer, textvariable=variable, takefocus=True).grid(row=row, column=1, sticky="nw", pady=3)

        ttk.Label(outer, text="Talkgroup:").grid(row=3, column=0, sticky="nw", padx=(0, 12), pady=3)
        self.talkgroup_entry = ttk.Entry(outer, textvariable=self.talkgroup_var, width=12, takefocus=True)
        self.talkgroup_entry.grid(row=3, column=1, sticky="w", pady=3)
        ttk.Label(outer, text="Timeslot:").grid(row=4, column=0, sticky="nw", padx=(0, 12), pady=3)
        self.timeslot_combo = ttk.Combobox(
            outer, textvariable=self.timeslot_var, values=("1", "2"),
            state="readonly", width=4, takefocus=True,
        )
        self.timeslot_combo.grid(row=4, column=1, sticky="w", pady=3)
        ttk.Label(outer, text="Audioausgabe:").grid(row=5, column=0, sticky="nw", padx=(0, 12), pady=3)
        ttk.Label(outer, textvariable=self.audio_var, takefocus=True).grid(row=5, column=1, sticky="nw", pady=3)

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
            text="Senden und Audioeinstellungen für den sicheren Parrot-Privatruf.",
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

        encoder_frame = ttk.LabelFrame(frame, text="Optionaler AMBE-Encoder", padding=10)
        encoder_frame.grid(row=11, column=0, columnspan=2, sticky="ew", pady=(16, 0))
        encoder_frame.columnconfigure(1, weight=1)
        ttk.Label(encoder_frame, text="DroidStar-Plugin:").grid(row=0, column=0, sticky="nw", padx=(0, 12), pady=3)
        ttk.Label(encoder_frame, textvariable=self.encoder_plugin_var, wraplength=430, takefocus=True).grid(row=0, column=1, sticky="w", pady=3)
        ttk.Label(encoder_frame, text="Status:").grid(row=1, column=0, sticky="nw", padx=(0, 12), pady=3)
        ttk.Label(encoder_frame, textvariable=self.encoder_status_var, wraplength=430, takefocus=True).grid(row=1, column=1, sticky="w", pady=3)
        encoder_controls = ttk.Frame(encoder_frame)
        encoder_controls.grid(row=2, column=0, columnspan=2, sticky="w", pady=(8, 0))
        self.encoder_select_button = ttk.Button(encoder_controls, text="Plugin auswählen und prüfen", command=self._select_encoder_plugin)
        self.encoder_verify_button = ttk.Button(encoder_controls, text="Konfiguriertes Plugin erneut prüfen", command=self._verify_encoder_plugin)
        self.encoder_select_button.grid(row=0, column=0, padx=(0, 8))
        self.encoder_verify_button.grid(row=0, column=1)

        parrot_frame = ttk.LabelFrame(frame, text="BrandMeister-Parrot – sicherer Sprachtest", padding=10)
        parrot_frame.grid(row=12, column=0, columnspan=2, sticky="ew", pady=(16, 0))
        parrot_frame.columnconfigure(1, weight=1)
        for row, (label, value) in enumerate((
            ("Ziel", "9990"), ("Ruftyp", "Privatruf"),
            ("Timeslot", "2"), ("Bedienung", "TX gedrückt halten; Loslassen sendet"),
        )):
            ttk.Label(parrot_frame, text=f"{label}:").grid(row=row, column=0, sticky="nw", padx=(0, 12), pady=2)
            ttk.Label(parrot_frame, text=value, takefocus=True).grid(row=row, column=1, sticky="nw", pady=2)
        ttk.Label(parrot_frame, text="TX-Sicherheitslimit:").grid(row=4, column=0, sticky="nw", padx=(0, 12), pady=2)
        limit_frame = ttk.Frame(parrot_frame)
        limit_frame.grid(row=4, column=1, sticky="w", pady=2)
        self.tx_safety_limit_spinbox = ttk.Spinbox(
            limit_frame, from_=5, to=180, increment=5, width=6,
            textvariable=self.tx_safety_limit_var, command=self._on_tx_safety_limit_changed,
            takefocus=True,
        )
        self.tx_safety_limit_spinbox.grid(row=0, column=0, padx=(0, 6))
        self.tx_safety_limit_spinbox.bind("<FocusOut>", self._on_tx_safety_limit_changed)
        self.tx_safety_limit_spinbox.bind("<Return>", self._on_tx_safety_limit_changed)
        ttk.Label(limit_frame, text="Sekunden (5–180)").grid(row=0, column=1)
        ttk.Label(parrot_frame, text="Status:").grid(row=5, column=0, sticky="nw", padx=(0, 12), pady=4)
        ttk.Label(parrot_frame, textvariable=self.parrot_status_var, wraplength=430, takefocus=True).grid(row=5, column=1, sticky="w", pady=4)
        ttk.Checkbutton(
            parrot_frame, text="Sprache optimieren (Hochpass, Kompressor, Limiter)",
            variable=self.transmit_optimizer_var, takefocus=True,
        ).grid(row=6, column=0, columnspan=2, sticky="w", pady=(4, 4))
        self.parrot_button = ttk.Button(
            parrot_frame, text="TX gedrückt halten – Loslassen sendet",
            state="disabled", takefocus=True,
        )
        self.parrot_button.grid(row=7, column=0, columnspan=2, sticky="w", pady=(8, 0))
        self.parrot_button.bind("<ButtonPress-1>", self._start_hold_to_talk)
        self.parrot_button.bind("<ButtonRelease-1>", self._release_hold_to_talk)
        self.parrot_button.bind("<KeyPress-space>", self._start_hold_to_talk)
        self.parrot_button.bind("<KeyRelease-space>", self._release_hold_to_talk)
        # Fallback auf Fensterebene: Das Loslassen wird auch erkannt, wenn
        # der Mauszeiger die TX-Schaltfläche während des Drückens verlässt.
        self.root.bind("<ButtonRelease-1>", self._release_hold_to_talk, add="+")

        ttk.Label(
            frame,
            text=("Version 0.0.19.4 sendet ausschließlich einen fest verriegelten "
                  "Privatruf an 9990 auf Timeslot 2. Es gibt keine freie Zielwahl."),
            wraplength=560,
        ).grid(row=13, column=0, columnspan=2, sticky="w", pady=(16, 0))
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

    def _build_transmit_history_tab(self, frame: ttk.Frame) -> None:
        frame.rowconfigure(1, weight=1)
        frame.columnconfigure(0, weight=1)
        controls = ttk.Frame(frame)
        controls.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        ttk.Label(controls, text="Abgeschlossene private Parrot-Sendetests").grid(row=0, column=0, sticky="w")
        ttk.Button(controls, text="Aktualisieren", command=self._refresh_transmit_history).grid(row=0, column=1, padx=(12, 0))
        columns = ("time", "target", "type", "duration", "echo", "limit", "optimizer")
        self.transmit_history_tree = ttk.Treeview(frame, columns=columns, show="headings", takefocus=True)
        headings = {"time":"Zeit", "target":"Ziel", "type":"Ruftyp", "duration":"Dauer", "echo":"Echo", "limit":"Limit", "optimizer":"Optimierer"}
        widths = {"time":155, "target":90, "type":90, "duration":80, "echo":70, "limit":80, "optimizer":90}
        for column in columns:
            self.transmit_history_tree.heading(column, text=headings[column])
            self.transmit_history_tree.column(column, width=widths[column], anchor="w")
        scroll = ttk.Scrollbar(frame, orient="vertical", command=self.transmit_history_tree.yview)
        self.transmit_history_tree.configure(yscrollcommand=scroll.set)
        self.transmit_history_tree.grid(row=1, column=0, sticky="nsew")
        scroll.grid(row=1, column=1, sticky="ns")
        self._refresh_transmit_history()

    def _refresh_transmit_history(self) -> None:
        if not hasattr(self, "transmit_history_tree"):
            return
        for item in self.transmit_history_tree.get_children():
            self.transmit_history_tree.delete(item)
        from datetime import datetime
        for entry in self.parrot_test_service.history.list_recent():
            try:
                timestamp = datetime.fromisoformat(entry.started_at).astimezone().strftime("%d.%m.%Y %H:%M:%S")
            except ValueError:
                timestamp = entry.started_at
            self.transmit_history_tree.insert("", tk.END, values=(
                timestamp, f"{entry.destination_id}/TS{entry.timeslot}", entry.call_type,
                f"{entry.duration_seconds:.1f} s", "Ja" if entry.echo_received else "Nein",
                "Ja" if entry.safety_limit_reached else "Nein",
                "Ein" if entry.optimizer_enabled else "Aus",
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


    def _on_tx_safety_limit_changed(self, _event: object | None = None) -> None:
        try:
            limit = self.audio_send_service.set_tx_safety_limit_seconds(
                self.tx_safety_limit_var.get()
            )
            self.tx_safety_limit_var.set(limit)
            self._schedule_audio_settings_save()
        except Exception as error:
            self.tx_safety_limit_var.set(
                self.audio_send_service.tx_safety_limit_seconds
            )
            self.parrot_status_var.set(f"TX-Sicherheitslimit ist ungültig: {error}")

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

    def _set_encoder_buttons(self, enabled: bool) -> None:
        state = "normal" if enabled else "disabled"
        self.encoder_select_button.configure(state=state)
        self.encoder_verify_button.configure(state=state)

    def _select_encoder_plugin(self) -> None:
        selected = filedialog.askopenfilename(
            parent=self.root,
            title="DroidStar-kompatibles Vocoder-Plugin auswählen",
            filetypes=(("Vocoder-Plugin", "*"), ("Alle Dateien", "*.*")),
        )
        if not selected:
            return
        self.encoder_plugin_var.set(selected)
        self._verify_encoder_path(Path(selected), save=True)

    def _verify_encoder_plugin(self) -> None:
        plugin_path = self.encoder_service.configured_plugin_path
        if plugin_path is None:
            self.encoder_status_var.set("Es ist noch kein Plugin ausgewählt.")
            return
        self.encoder_plugin_var.set(str(plugin_path))
        self._verify_encoder_path(plugin_path, save=False)

    def _verify_encoder_path(self, plugin_path: Path, *, save: bool) -> None:
        self._set_encoder_buttons(False)
        self.encoder_status_var.set(
            "Plugin wird lokal geladen und mit einem stummen PCM-Testframe geprüft …"
        )

        def worker() -> None:
            try:
                if save:
                    result = self.encoder_service.configure_and_verify(plugin_path)
                else:
                    result = self.encoder_service.verify_configured()
                self._updates.put(("encoder_verified", result))
            except Exception as error:
                self._updates.put(("encoder_error", error))

        Thread(target=worker, name="CarenDMR-Encoder-Test", daemon=True).start()

    def _start_hold_to_talk(self, event=None) -> str:
        if self._tx_active or str(self.parrot_button.cget("state")) == "disabled":
            return "break"
        if self.receive_service.is_running:
            self.receive_service.stop()
            self.receive_service.wait(3.0)
        self._tx_active = True
        self._tx_recording = True
        self._tx_stop_event = Event()
        self._tx_started_at = monotonic()
        if event is not None and getattr(event, "num", None) == 1:
            try:
                self.parrot_button.grab_set()
                self._tx_pointer_grabbed = True
            except tk.TclError:
                self._tx_pointer_grabbed = False
        self.parrot_button.configure(text="TX läuft – zum Senden loslassen")
        limit = self.audio_send_service.tx_safety_limit_seconds
        self.parrot_status_var.set(f"TX-Aufnahme läuft: 0,0 / {limit} Sekunden.")
        self._update_tx_timer()
        stop_event = self._tx_stop_event
        optimize = bool(self.transmit_optimizer_var.get())

        def worker() -> None:
            try:
                result = self.parrot_test_service.run_hold_to_talk(
                    stop_event,
                    level_callback=lambda level: self._updates.put(("mic_level", level)),
                    optimize=optimize,
                )
                self._updates.put(("parrot_result", result))
            except Exception as error:
                self._updates.put(("parrot_error", error))

        Thread(target=worker, name="CarenDMR-Hold-To-Talk-Parrot", daemon=True).start()
        return "break"

    def _release_hold_to_talk(self, _event=None) -> str:
        if not self._tx_active or self._tx_stop_event is None:
            return "break"
        if self._tx_pointer_grabbed:
            try:
                self.parrot_button.grab_release()
            except tk.TclError:
                pass
            self._tx_pointer_grabbed = False
        if not self._tx_stop_event.is_set():
            self._tx_recording = False
            self.parrot_button.configure(text="Kodierung und Senden läuft …", state="disabled")
            self.parrot_status_var.set(
                "TX losgelassen. Aufnahme beendet; Sprache wird codiert und privat an 9990 gesendet …"
            )
            self._tx_stop_event.set()
        return "break"

    def _release_tx_pointer_grab(self) -> None:
        if not self._tx_pointer_grabbed:
            return
        try:
            self.parrot_button.grab_release()
        except tk.TclError:
            pass
        self._tx_pointer_grabbed = False

    def _update_tx_timer(self) -> None:
        if not self._tx_active or not self._tx_recording or self._tx_started_at is None:
            return
        limit = float(self.audio_send_service.tx_safety_limit_seconds)
        elapsed = min(limit, monotonic() - self._tx_started_at)
        if elapsed >= limit and self._tx_stop_event is not None:
            self._tx_recording = False
            self._tx_stop_event.set()
            self._release_tx_pointer_grab()
            self.parrot_button.configure(text="Sicherheitslimit erreicht – Senden läuft", state="disabled")
            self.parrot_status_var.set(
                f"{int(limit)}-Sekunden-Sicherheitslimit erreicht. "
                "Aufnahme beendet; Aussendung läuft …"
            )
            return
        self.parrot_status_var.set(
            f"TX-Aufnahme läuft: {elapsed:.1f} / {int(limit)} Sekunden. "
            "Zum Senden loslassen."
        )
        self.root.after(100, self._update_tx_timer)

    def _start(self) -> None:
        try:
            talkgroup = int(self.talkgroup_var.get().strip())
            timeslot = int(self.timeslot_var.get().strip())
            self.receive_service.set_receive_target(talkgroup, timeslot)
        except (TypeError, ValueError, RuntimeError) as error:
            messagebox.showerror("CarenDMR", str(error), parent=self.root)
            self.talkgroup_entry.focus_set()
            return
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
                elif kind == "encoder_verified":
                    diagnostics = value
                    self.encoder_plugin_var.set(diagnostics.plugin_path)
                    self.encoder_status_var.set(
                        f"AMBE-Encoder bereit: {diagnostics.encoded_bytes} Byte erzeugt. "
                        f"{diagnostics.message}"
                    )
                    self._set_encoder_buttons(True)
                    self.parrot_button.configure(state="normal")
                elif kind == "parrot_result":
                    result, duration, safety_limit_reached = value
                    self._tx_active = False
                    self._tx_recording = False
                    self._tx_stop_event = None
                    self._tx_started_at = None
                    self._release_tx_pointer_grab()
                    suffix = " Sicherheitslimit erreicht." if safety_limit_reached else ""
                    if result.echo_received:
                        self.parrot_status_var.set(
                            f"Parrot-Echo erfolgreich. {duration:.1f} Sekunden TX; "
                            f"{result.echo_voice_bursts} Echobursts empfangen.{suffix}"
                        )
                    else:
                        self.parrot_status_var.set(
                            f"{duration:.1f} Sekunden privat gesendet, aber kein Echo empfangen.{suffix}"
                        )
                    self.parrot_button.configure(state="normal", text="TX gedrückt halten – Loslassen sendet")
                    self._refresh_transmit_history()
                elif kind == "parrot_error":
                    self._tx_active = False
                    self._tx_recording = False
                    self._tx_stop_event = None
                    self._tx_started_at = None
                    self._release_tx_pointer_grab()
                    self.parrot_status_var.set(f"Parrot-Test sicher abgebrochen: {value}")
                    self.parrot_button.configure(state="normal", text="TX gedrückt halten – Loslassen sendet")
                elif kind == "encoder_error":
                    self.encoder_status_var.set(f"Encoderprüfung fehlgeschlagen: {value}")
                    self._set_encoder_buttons(True)
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
        self.talkgroup_entry.configure(state="disabled" if running else "normal")
        self.timeslot_combo.configure(state="disabled" if running else "readonly")

    def _append_event(self, event: ApplicationEvent) -> None:
        self.event_log.insert(tk.END, event.display_text)
        self.event_log.see(tk.END)

    def run(self) -> int:
        self.events.publish("CarenDMR ist bereit. Der Empfang ist noch nicht verbunden.")
        self.root.mainloop()
        return 0


def run_gui(project_root: Path) -> int:
    return MainWindow(project_root).run()
