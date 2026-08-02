"""Kleines barrierefreies Read-only-Hauptfenster für CarenDMR."""

from __future__ import annotations

import queue
import tkinter as tk
from pathlib import Path
from threading import Event, Thread
from time import monotonic
from tkinter import filedialog, messagebox, ttk

from carendmr.application import AudioSendService, ConnectionManager, EncoderService, EventService, ParrotTestService, ReceiveService
from carendmr.audio import AudioDirection
from carendmr.domain import ApplicationEvent, ApplicationState, ConnectionState, EventLevel
from carendmr.version import __version__


class MainWindow:
    """Native Tk-Steuerelemente mit stabiler Fokusreihenfolge und Textlabels."""

    def __init__(self, project_root: Path) -> None:
        self.project_root = Path(project_root)
        self.root = tk.Tk()
        self.root.title(f"CarenDMR {__version__}")
        self.root.minsize(760, 650)

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
        self.connection_manager = ConnectionManager(
            self.receive_service, self.parrot_test_service, events=self.events
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
        self.call_type_var = tk.StringVar(value="Gruppe")
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
        # Für den Funkbetrieb gilt ein festes Sicherheitslimit von 60 Sekunden.
        self.audio_send_service.set_tx_safety_limit_seconds(60)
        self.tx_safety_limit_var = tk.IntVar(value=60)
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
        self.root.bind("<Control-u>", lambda _event: self._switch_receive_target())
        self.root.bind("<Control-m>", lambda _event: self._toggle_output_mute())
        self.root.bind("<Control-p>", lambda _event: self._toggle_transmit())
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
        operation = ttk.Frame(self.notebook, padding=12)
        history = ttk.Frame(self.notebook, padding=12)
        settings = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(operation, text="Betrieb")
        self.notebook.add(history, text="QSO-Historie")
        self.notebook.add(settings, text="Einstellungen")
        self._build_operation_tab(operation)
        self._build_history_tab(history)
        self._build_settings_tab(settings)
        self.root.after(0, self._initialize_once)

    def _build_operation_tab(self, outer: ttk.Frame) -> None:
        """Gemeinsame Funkgeräteansicht für Empfang und PTT."""
        outer.columnconfigure(0, weight=1)
        outer.rowconfigure(5, weight=1)

        status = ttk.LabelFrame(outer, text="Verbindung und Kanal", padding=10)
        status.grid(row=0, column=0, sticky="ew")
        status.columnconfigure(5, weight=1)
        ttk.Label(status, text="BrandMeister:").grid(row=0, column=0, sticky="w", padx=(0, 6))
        ttk.Label(status, textvariable=self.brandmeister_var).grid(row=0, column=1, sticky="w", padx=(0, 18))
        ttk.Label(status, text="Empfang:").grid(row=0, column=2, sticky="w", padx=(0, 6))
        ttk.Label(status, textvariable=self.receive_var).grid(row=0, column=3, sticky="w")
        ttk.Label(status, text="Server:").grid(row=1, column=0, sticky="w", padx=(0, 6), pady=(6, 0))
        ttk.Label(status, textvariable=self.server_var).grid(row=1, column=1, columnspan=5, sticky="w", pady=(6, 0))

        self.connect_button = ttk.Button(status, text="CONNECT", command=self._toggle_connection, width=13)
        self.connect_button.grid(row=0, column=4, rowspan=2, padx=(18, 0), sticky="e")

        ttk.Label(status, text="Talkgroup:").grid(row=2, column=0, sticky="w", padx=(0, 6), pady=(8, 0))
        self.talkgroup_entry = ttk.Entry(status, textvariable=self.talkgroup_var, width=10, takefocus=True)
        self.talkgroup_entry.grid(row=2, column=1, sticky="w", pady=(8, 0))
        ttk.Label(status, text="Timeslot:").grid(row=2, column=2, sticky="w", padx=(10, 6), pady=(8, 0))
        self.timeslot_combo = ttk.Combobox(status, textvariable=self.timeslot_var, values=("1", "2"), state="readonly", width=4, takefocus=True)
        self.timeslot_combo.grid(row=2, column=3, sticky="w", pady=(8, 0))
        ttk.Label(status, text="Rufart:").grid(row=2, column=4, sticky="w", padx=(12, 6), pady=(8, 0))
        self.call_type_combo = ttk.Combobox(status, textvariable=self.call_type_var, values=("Gruppe", "Privat"), state="readonly", width=8, takefocus=True)
        self.call_type_combo.grid(row=2, column=5, sticky="w", pady=(8, 0))
        self.switch_button = ttk.Button(status, text="Kanal umschalten", command=self._switch_receive_target, state="disabled")
        self.switch_button.grid(row=3, column=0, columnspan=2, pady=(8, 0), sticky="w")

        current_frame = ttk.LabelFrame(outer, text="Aktuelle Station", padding=10)
        current_frame.grid(row=1, column=0, sticky="ew", pady=(8, 0))
        current_frame.columnconfigure(1, weight=1)
        current_frame.columnconfigure(3, weight=1)
        current_fields = (
            ("Rufzeichen", self.current_callsign_var), ("Name", self.current_name_var),
            ("Ort/Region", self.current_location_var), ("Land", self.current_country_var),
            ("DMR-ID", self.current_dmr_id_var), ("Ziel", self.current_target_var),
            ("Sprechdauer", self.current_duration_var),
        )
        for index, (label, variable) in enumerate(current_fields):
            row, pair = divmod(index, 2)
            col = pair * 2
            ttk.Label(current_frame, text=f"{label}:").grid(row=row, column=col, sticky="nw", padx=(0, 8), pady=2)
            ttk.Label(current_frame, textvariable=variable, takefocus=True).grid(row=row, column=col + 1, sticky="nw", padx=(0, 18), pady=2)
        ttk.Label(current_frame, text="Kontaktstatus:").grid(row=4, column=0, sticky="nw", padx=(0, 8), pady=2)
        self.worked_status_var = tk.StringVar(value="Nur gehört – noch kein bestätigtes QSO")
        ttk.Label(current_frame, textvariable=self.worked_status_var).grid(row=4, column=1, columnspan=3, sticky="w", pady=2)

        radio = ttk.LabelFrame(outer, text="Funkbetrieb", padding=10)
        radio.grid(row=2, column=0, sticky="ew", pady=(8, 0))
        radio.columnconfigure(0, weight=1)
        radio.columnconfigure(1, weight=1)
        ttk.Label(radio, text="RX-Pegel").grid(row=0, column=0, sticky="w")
        ttk.Progressbar(radio, variable=self.output_level_var, maximum=100).grid(row=1, column=0, sticky="ew", padx=(0, 12))
        ttk.Label(radio, text="Mikrofonpegel").grid(row=0, column=1, sticky="w")
        self.microphone_level = ttk.Progressbar(radio, variable=self.microphone_level_var, maximum=100)
        self.microphone_level.grid(row=1, column=1, sticky="ew")
        self.parrot_button = tk.Button(
            radio, text="TX AUS", command=self._toggle_transmit,
            font=("TkDefaultFont", 15, "bold"), width=18, height=3,
            bg="#2f6fbd", fg="white", activebackground="#245892",
            disabledforeground="#dddddd", state="disabled", takefocus=True,
        )
        self.parrot_button.grid(row=2, column=0, columnspan=2, pady=(12, 6))
        self.operation_mute_check = ttk.Checkbutton(
            radio, text="Stumm (Strg+M)", variable=self.output_muted_var,
            command=self._on_output_mute_changed, takefocus=True,
        )
        self.operation_mute_check.grid(row=3, column=0, columnspan=2, pady=(4, 0))

        ttk.Label(outer, text="Empfangsstatistik:").grid(row=3, column=0, sticky="w", pady=(8, 2))
        ttk.Label(outer, textvariable=self.statistics_var, wraplength=690).grid(row=4, column=0, sticky="w")
        log_frame = ttk.LabelFrame(outer, text="Ereignisprotokoll", padding=6)
        log_frame.grid(row=5, column=0, sticky="nsew", pady=(8, 0))
        log_frame.rowconfigure(0, weight=1); log_frame.columnconfigure(0, weight=1)
        self.event_log = tk.Listbox(log_frame, activestyle="dotbox", exportselection=False, takefocus=True)
        scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.event_log.yview)
        self.event_log.configure(yscrollcommand=scrollbar.set)
        self.event_log.grid(row=0, column=0, sticky="nsew"); scrollbar.grid(row=0, column=1, sticky="ns")

        buttons = ttk.Frame(outer)
        buttons.grid(row=6, column=0, sticky="ew", pady=(10, 0))
        self.exit_button = ttk.Button(buttons, text="Beenden", command=self._close)
        self.exit_button.grid(row=0, column=0)

    def _build_settings_tab(self, frame: ttk.Frame) -> None:
        """Technische Inbetriebnahme- und Audioeinstellungen."""
        frame.columnconfigure(1, weight=1)
        ttk.Label(frame, text="Audio und einmalige Inbetriebnahme", font=("TkDefaultFont", 12, "bold")).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 10))
        ttk.Label(frame, text="Mikrofon:").grid(row=1, column=0, sticky="w", padx=(0, 12), pady=4)
        self.microphone_combo = ttk.Combobox(frame, textvariable=self.microphone_var, state="readonly", takefocus=True)
        self.microphone_combo.grid(row=1, column=1, sticky="ew", pady=4); self.microphone_combo.bind("<<ComboboxSelected>>", self._select_microphone)
        ttk.Button(frame, text="Mikrofone neu einlesen", command=self._scan_microphones).grid(row=2, column=1, sticky="w", pady=(2, 8))
        ttk.Label(frame, text="Mikrofonstatus:").grid(row=3, column=0, sticky="nw", padx=(0, 12), pady=4)
        ttk.Label(frame, textvariable=self.microphone_status_var, wraplength=520).grid(row=3, column=1, sticky="w", pady=4)
        ttk.Label(frame, text="Mikrofonverstärkung:").grid(row=4, column=0, sticky="w", padx=(0, 12), pady=4)
        gain_frame = ttk.Frame(frame); gain_frame.grid(row=4, column=1, sticky="ew"); gain_frame.columnconfigure(0, weight=1)
        self.microphone_gain_scale = ttk.Scale(gain_frame, from_=25, to=200, variable=self.microphone_gain_var, command=self._on_microphone_gain_changed)
        self.microphone_gain_scale.grid(row=0, column=0, sticky="ew"); ttk.Label(gain_frame, textvariable=self.microphone_gain_text_var, width=7).grid(row=0, column=1, padx=(8, 0))
        ttk.Label(frame, text="Ausgabelautstärke:").grid(row=5, column=0, sticky="w", padx=(0, 12), pady=4)
        vol = ttk.Frame(frame); vol.grid(row=5, column=1, sticky="ew"); vol.columnconfigure(0, weight=1)
        ttk.Scale(vol, from_=0, to=400, variable=self.output_volume_var, command=self._on_output_volume_changed).grid(row=0, column=0, sticky="ew")
        ttk.Label(vol, textvariable=self.output_volume_text_var, width=7).grid(row=0, column=1, padx=(8, 0))
        flags = ttk.Frame(frame); flags.grid(row=6, column=1, sticky="w", pady=4)
        ttk.Checkbutton(flags, text="AGC", variable=self.output_agc_var, command=self._on_output_agc_changed).grid(row=0, column=0)
        ttk.Checkbutton(frame, text="Sprache optimieren (Hochpass, Kompressor, Limiter)", variable=self.transmit_optimizer_var).grid(row=7, column=1, sticky="w", pady=4)

        encoder_frame = ttk.LabelFrame(frame, text="AMBE-Encoder – einmalige Zuordnung", padding=10)
        encoder_frame.grid(row=8, column=0, columnspan=2, sticky="ew", pady=(14, 0)); encoder_frame.columnconfigure(1, weight=1)
        ttk.Label(encoder_frame, text="Plugin:").grid(row=0, column=0, sticky="nw", padx=(0, 10), pady=3)
        ttk.Label(encoder_frame, textvariable=self.encoder_plugin_var, wraplength=500).grid(row=0, column=1, sticky="w", pady=3)
        ttk.Label(encoder_frame, text="Status:").grid(row=1, column=0, sticky="nw", padx=(0, 10), pady=3)
        ttk.Label(encoder_frame, textvariable=self.encoder_status_var, wraplength=500).grid(row=1, column=1, sticky="w", pady=3)
        controls = ttk.Frame(encoder_frame); controls.grid(row=2, column=0, columnspan=2, sticky="w", pady=(8, 0))
        self.encoder_select_button = ttk.Button(controls, text="Plugin zuordnen", command=self._select_encoder_plugin)
        self.encoder_verify_button = ttk.Button(controls, text="Erneut prüfen", command=self._verify_encoder_plugin)
        self.encoder_select_button.grid(row=0, column=0, padx=(0, 8)); self.encoder_verify_button.grid(row=0, column=1)
        ttk.Label(encoder_frame, text="Beim Programmstart wird das gespeicherte Plugin automatisch geladen und geprüft. Nur bei einem Fehler ist ein Eingriff erforderlich.", wraplength=600).grid(row=3, column=0, columnspan=2, sticky="w", pady=(8, 0))

        contacts = ttk.LabelFrame(frame, text="Kontaktdatenbank", padding=10)
        contacts.grid(row=9, column=0, columnspan=2, sticky="ew", pady=(14, 0)); contacts.columnconfigure(0, weight=1)
        ttk.Label(contacts, textvariable=self.contacts_var, wraplength=500).grid(row=0, column=0, sticky="w")
        self.contacts_button = ttk.Button(contacts, text="Kontaktdaten aktualisieren", command=self._update_contacts)
        self.contacts_button.grid(row=0, column=1, padx=(12, 0))
        ttk.Label(frame, text="TX-Sicherheitslimit: fest 60 Sekunden", font=("TkDefaultFont", 10, "bold")).grid(row=10, column=0, columnspan=2, sticky="w", pady=(14, 0))

    def _initialize_once(self) -> None:
        """Lädt Mikrofon und Encoder automatisch; im Erfolgsfall bleibt es still."""
        self._scan_microphones()
        plugin_path = self.encoder_service.configured_plugin_path
        if plugin_path is None:
            self.encoder_status_var.set("Noch kein Encoder zugeordnet. Empfang ist möglich; Senden bleibt gesperrt.")
            return
        self.encoder_plugin_var.set(str(plugin_path))
        self._verify_encoder_path(plugin_path, save=False)

    def _toggle_transmit(self) -> None:
        if self._tx_active:
            self._release_hold_to_talk()
        else:
            self._start_hold_to_talk()

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
        target_controls = ttk.Frame(outer)
        target_controls.grid(row=4, column=1, sticky="w", pady=3)
        self.timeslot_combo = ttk.Combobox(
            target_controls, textvariable=self.timeslot_var, values=("1", "2"),
            state="readonly", width=4, takefocus=True,
        )
        self.timeslot_combo.grid(row=0, column=0, sticky="w")
        self.switch_button = ttk.Button(
            target_controls,
            text="TG / Timeslot umschalten",
            command=self._switch_receive_target,
            state="disabled",
            takefocus=True,
        )
        self.switch_button.grid(row=0, column=1, padx=(12, 0))
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
        ttk.Label(outer, text="Tastenkürzel: Strg+R verbinden, Strg+U TG/TS umschalten, Strg+T trennen, Esc oder Strg+Q beenden.", wraplength=560).grid(row=12, column=0, columnspan=2, sticky="w", pady=(10, 0))

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
            text=("Der Sendebereich sendet ausschließlich einen fest verriegelten "
                  "Privatruf an 9990 auf Timeslot 2. Es gibt keine freie Zielwahl."),
            wraplength=560,
        ).grid(row=13, column=0, columnspan=2, sticky="w", pady=(16, 0))

    def _build_history_tab(self, frame: ttk.Frame) -> None:
        frame.rowconfigure(1, weight=1)
        frame.columnconfigure(0, weight=1)
        controls = ttk.Frame(frame)
        controls.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        ttk.Label(controls, text="Abgeschlossene empfangene Sprechdurchgänge").grid(row=0, column=0, sticky="w")
        ttk.Button(controls, text="Aktualisieren", command=self._refresh_history).grid(row=0, column=1, padx=(12, 0))
        columns = ("time", "callsign", "name", "country", "dmr_id", "target", "duration", "worked")
        self.history_tree = ttk.Treeview(frame, columns=columns, show="headings", takefocus=True)
        headings = {
            "time": "Zeit", "callsign": "Rufzeichen", "name": "Name",
            "country": "Land", "dmr_id": "DMR-ID", "target": "Ziel",
            "duration": "Dauer", "worked": "QSO",
        }
        widths = {"time": 145, "callsign": 90, "name": 150, "country": 110, "dmr_id": 90, "target": 90, "duration": 70, "worked": 105}
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
                entry.source_id, target, f"{entry.duration_seconds:.0f} s", "Nur gehört",
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
        self.parrot_button.configure(text="TX EIN", bg="#c62828", activebackground="#9d1f1f")
        limit = self.audio_send_service.tx_safety_limit_seconds
        self.parrot_status_var.set(f"SENDEN: 0,0 / {limit} Sekunden. Erneut TX drücken zum Beenden.")
        self._update_tx_timer()
        stop_event = self._tx_stop_event
        optimize = bool(self.transmit_optimizer_var.get())

        def worker() -> None:
            try:
                result = self.connection_manager.run_parrot_hold_to_talk(
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
            self.parrot_button.configure(text="TX AUS", state="disabled", bg="#2f6fbd")
            if hasattr(self, "events"):
                self.events.publish("TX beendet; Aussendung wird abgeschlossen.")
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
            self.parrot_button.configure(text="TX LIMIT ERREICHT", state="disabled", bg="#b26a00")
            self.events.publish(f"TX nach {int(limit)} Sekunden automatisch beendet.", EventLevel.WARNING)
            return
        # Der laufende TX-Zustand wird ausschließlich über die große rote Taste angezeigt.
        self.root.after(100, self._update_tx_timer)

    def _toggle_connection(self) -> None:
        if self.receive_service.is_running:
            self._stop()
        else:
            self._start()

    def _start(self) -> None:
        try:
            talkgroup = int(self.talkgroup_var.get().strip())
            timeslot = int(self.timeslot_var.get().strip())
        except (TypeError, ValueError, RuntimeError) as error:
            messagebox.showerror("CarenDMR", str(error), parent=self.root)
            self.talkgroup_entry.focus_set()
            return
        call_type = "private" if self.call_type_var.get() == "Privat" else "group"
        if self.connection_manager.connect(talkgroup, timeslot, call_type):
            self.connect_button.configure(text="DISCONNECT")
        else:
            self.events.publish("Der Empfang läuft bereits.")

    def _switch_receive_target(self) -> None:
        try:
            talkgroup = int(self.talkgroup_var.get().strip())
            timeslot = int(self.timeslot_var.get().strip())
        except (TypeError, ValueError) as error:
            messagebox.showerror("CarenDMR", str(error), parent=self.root)
            self.talkgroup_entry.focus_set()
            return
        if not self.receive_service.is_running:
            self._start()
            return
        try:
            call_type = "private" if self.call_type_var.get() == "Privat" else "group"
            started = self.connection_manager.switch_receive_target(talkgroup, timeslot, call_type)
        except (TypeError, ValueError, RuntimeError) as error:
            messagebox.showerror("CarenDMR", str(error), parent=self.root)
            self.talkgroup_entry.focus_set()
            return
        if not started:
            self.events.publish("Ein TG-/TS-Wechsel läuft bereits.")
            return
        self.switch_button.configure(state="disabled")

    def _stop(self) -> None:
        self.connection_manager.disconnect()

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
                    self.parrot_button.configure(state="normal", text="TX AUS", bg="#2f6fbd")
                elif kind == "parrot_result":
                    result, duration, safety_limit_reached = value
                    self._tx_active = False
                    self._tx_recording = False
                    self._tx_stop_event = None
                    self._tx_started_at = None
                    self._release_tx_pointer_grab()
                    suffix = " Sicherheitslimit erreicht." if safety_limit_reached else ""
                    if result.echo_received:
                        self.events.publish(
                            f"Parrot-Echo erfolgreich: {duration:.1f} Sekunden TX, "
                            f"{result.echo_voice_bursts} Echobursts empfangen.{suffix}"
                        )
                    else:
                        self.events.publish(
                            f"{duration:.1f} Sekunden privat gesendet, aber kein Echo empfangen.{suffix}",
                            EventLevel.WARNING,
                        )
                    self.parrot_button.configure(state="normal", text="TX AUS", bg="#2f6fbd", activebackground="#245892")
                    self._refresh_transmit_history()
                elif kind == "parrot_error":
                    self._tx_active = False
                    self._tx_recording = False
                    self._tx_stop_event = None
                    self._tx_started_at = None
                    self._release_tx_pointer_grab()
                    self.events.publish(f"Parrot-Test sicher abgebrochen: {value}", EventLevel.ERROR)
                    self.parrot_button.configure(state="normal", text="TX AUS", bg="#2f6fbd", activebackground="#245892")
                elif kind == "encoder_error":
                    self.encoder_status_var.set(f"Encoder konnte nicht geladen werden: {value}")
                    self._set_encoder_buttons(True)
                    self.parrot_button.configure(state="disabled", text="TX NICHT VERFÜGBAR", bg="#777777")
                    messagebox.showerror(
                        "AMBE-Encoder",
                        "Der gespeicherte AMBE-Encoder konnte nicht geladen werden. "
                        "Empfang bleibt möglich; Senden ist deaktiviert. "
                        "Bitte prüfen Sie die Zuordnung unter Einstellungen.\n\n" + str(value),
                        parent=self.root,
                    )
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
        self.connect_button.configure(
            text="DISCONNECT" if running else "CONNECT",
            state="disabled" if state.connection in {ConnectionState.CONNECTING, ConnectionState.STOPPING} else "normal",
        )
        self.switch_button.configure(
            state="normal" if running and state.connection is not ConnectionState.STOPPING else "disabled"
        )
        self.talkgroup_entry.configure(state="normal")
        self.timeslot_combo.configure(state="readonly")
        self.call_type_combo.configure(state="readonly")

    def _append_event(self, event: ApplicationEvent) -> None:
        self.event_log.insert(tk.END, event.display_text)
        self.event_log.see(tk.END)

    def run(self) -> int:
        self.events.publish("CarenDMR ist bereit. Der Empfang ist noch nicht verbunden.")
        self.root.mainloop()
        return 0


def run_gui(project_root: Path) -> int:
    return MainWindow(project_root).run()
