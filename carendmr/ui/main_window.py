"""Kleines barrierefreies Read-only-Hauptfenster für CarenDMR."""

from __future__ import annotations

import json
import queue
import tkinter as tk
from pathlib import Path
from threading import Event, Thread
from time import monotonic
from tkinter import filedialog, messagebox, ttk

from carendmr.application import AudioSendService, ConnectionManager, EncoderService, EventService, ParrotTestService, ReceiveService
from carendmr.audio import AudioDirection
from carendmr.domain import (
    ApplicationEvent, ApplicationState, ConnectionState, EventLevel,
    InformationCategory, InformationPriority,
)
from carendmr.diagnostics import initialize as initialize_diagnostics, set_enabled as set_diagnostics_enabled
from carendmr.diagnostics.tx_rx_timing import initialize as initialize_tx_rx_timing
from carendmr.version import __version__


class MainWindow:
    """Native Tk-Steuerelemente mit stabiler Fokusreihenfolge und Textlabels."""

    def __init__(self, project_root: Path) -> None:
        self.project_root = Path(project_root)
        self.root = tk.Tk()
        self.root.title(f"CarenDMR {__version__}")
        self.root.geometry("1380x840")
        self.root.minsize(1180, 720)

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
        self.colors = {
            "background": "#0b1220", "card": "#111c2e", "card_alt": "#18263a",
            "text": "#f4f7fb", "muted": "#8fa3bb", "blue": "#2f80ed",
            "blue_dark": "#1f65c1", "green": "#38d996", "green_dark": "#167a55",
            "cyan": "#55d7ff", "yellow": "#f2c94c", "red": "#d94141",
        }
        self.diagnostics_enabled_var = tk.BooleanVar(value=initialize_diagnostics(self.project_root))
        self.audio_debug_wav_enabled_var = tk.BooleanVar(value=self.audio_send_service.audio_debug_wav_enabled)
        initialize_tx_rx_timing(self.project_root)
        self.system_mode_var = tk.StringVar(value="DMR TS2")
        self.system_network_var = tk.StringVar(value="BrandMeister")
        self.system_codec_var = tk.StringVar(value="AMBE+2")
        self.system_speaker_var = tk.StringVar(value="OK")
        self.system_microphone_var = tk.StringVar(value="OK")
        self.history_search_var = tk.StringVar(value="")
        self.history_summary_var = tk.StringVar(value="Noch keine Historieneinträge")
        self.history_selection_var = tk.StringVar(value="Keine Station ausgewählt")
        self.history_qso_button_var = tk.StringVar(value="QSO bestätigen")
        self._selected_history_source_id: int | None = None
        self._history_rows: dict[str, object] = {}
        self._worked_status_source_id: int | None = None
        self._worked_status_value = False
        self._pages: dict[str, tk.Widget] = {}
        self._nav_buttons: dict[str, tk.Button] = {}

        self._configure_theme()
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
        self.root.bind("<F1>", lambda _event: self._show_help())
        self.root.bind("<F2>", lambda _event: self._switch_receive_target())
        self.root.bind("<F3>", lambda _event: self._toggle_transmit())
        self.root.bind("<F4>", lambda _event: self._toggle_output_mute())
        self.root.after(100, self._process_updates)
        self.connect_button.focus_set()

    def _configure_theme(self) -> None:
        """Zentrales dunkles Designsystem für die neue CarenDMR-Oberfläche."""
        self.root.configure(bg=self.colors["background"])
        self.root.minsize(1180, 720)
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("App.TFrame", background=self.colors["background"])
        style.configure("TNotebook", background=self.colors["background"], borderwidth=0)
        style.configure("TNotebook.Tab", background=self.colors["card"], foreground=self.colors["muted"],
                        padding=(18, 9), font=("Segoe UI", 10, "bold"))
        style.map("TNotebook.Tab", background=[("selected", self.colors["blue"])],
                  foreground=[("selected", "white")])
        style.configure("Dark.TCombobox", fieldbackground=self.colors["card_alt"],
                        background=self.colors["card_alt"], foreground=self.colors["text"],
                        arrowcolor=self.colors["text"], borderwidth=0, padding=5)
        style.map("Dark.TCombobox", fieldbackground=[("readonly", self.colors["card_alt"])],
                  foreground=[("readonly", self.colors["text"])])
        style.configure("Switch.TCheckbutton", background=self.colors["card"], foreground=self.colors["text"],
                        font=("Segoe UI", 10, "bold"), padding=4)
        style.map("Switch.TCheckbutton", background=[("active", self.colors["card"])])
        style.configure("RX.Horizontal.TProgressbar", troughcolor=self.colors["card_alt"],
                        background=self.colors["blue"], borderwidth=0, thickness=10)
        style.configure("MIC.Horizontal.TProgressbar", troughcolor=self.colors["card_alt"],
                        background=self.colors["green"], borderwidth=0, thickness=10)

    def _build(self) -> None:
        outer = tk.Frame(self.root, bg=self.colors["background"], padx=20, pady=14)
        outer.grid(row=0, column=0, sticky="nsew")
        self.root.rowconfigure(0, weight=1)
        self.root.columnconfigure(0, weight=1)
        outer.rowconfigure(1, weight=1)
        outer.columnconfigure(0, weight=1)

        header = tk.Frame(outer, bg=self.colors["background"], height=82)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        header.grid_propagate(False)
        header.columnconfigure(0, weight=1)
        brand = tk.Frame(header, bg=self.colors["background"])
        brand.grid(row=0, column=0, sticky="w")
        tk.Label(brand, text="CarenDMR", bg=self.colors["background"], fg=self.colors["text"],
                 font=("Segoe UI", 28, "bold")).pack(side="left")
        tk.Label(brand, text="DIGITAL RADIO CONSOLE", bg=self.colors["background"], fg=self.colors["cyan"],
                 font=("Segoe UI", 11, "bold")).pack(side="left", padx=(18, 0), pady=(12, 0))

        nav = tk.Frame(header, bg=self.colors["background"])
        nav.grid(row=0, column=1, sticky="e")
        for column, (key, caption) in enumerate((("operation", "◉  BETRIEB"), ("history", "◷  QSO-HISTORIE"), ("settings", "⚙  EINSTELLUNGEN"))):
            button = tk.Button(nav, text=caption, command=lambda page=key: self._show_page(page),
                               width=20, height=2, relief="flat", bd=0, cursor="hand2",
                               font=("Segoe UI", 11, "bold"))
            button.grid(row=0, column=column, padx=(0 if column == 0 else 10, 0), sticky="e")
            self._nav_buttons[key] = button

        page_host = tk.Frame(outer, bg=self.colors["background"])
        page_host.grid(row=1, column=0, sticky="nsew")
        page_host.rowconfigure(0, weight=1)
        page_host.columnconfigure(0, weight=1)
        operation = ttk.Frame(page_host, padding=0, style="App.TFrame")
        history = ttk.Frame(page_host, padding=12, style="App.TFrame")
        settings = ttk.Frame(page_host, padding=12, style="App.TFrame")
        for key, page in (("operation", operation), ("history", history), ("settings", settings)):
            page.grid(row=0, column=0, sticky="nsew")
            self._pages[key] = page

        self._build_operation_tab(operation)
        self._build_history_tab(history)
        self._build_settings_tab(settings)
        self._show_page("operation", announce=False)
        self.root.after(0, self._initialize_once)

    def _show_page(self, page_name: str, *, announce: bool = True) -> None:
        page = self._pages.get(page_name)
        if page is None:
            return
        page.tkraise()
        for key, button in self._nav_buttons.items():
            active = key == page_name
            button.configure(
                bg=self.colors["blue"] if active else self.colors["card"],
                fg="white" if active else self.colors["muted"],
                activebackground=self.colors["blue_dark"] if active else self.colors["card_alt"],
                activeforeground="white",
                font=("Segoe UI", 13 if active else 10, "bold"),
            )
        if announce and hasattr(self, "events"):
            labels = {"operation": "Betrieb", "history": "QSO-Historie", "settings": "Einstellungen"}
            label = labels.get(page_name, page_name)
            self.events.publish(
                f"Bereich {label} geöffnet.",
                code=f"navigation.{page_name}",
                long_text=f"Du befindest dich im Bereich {label}.",
                category=InformationCategory.OPERATION,
                priority=InformationPriority.LOW,
            )

    def _show_help(self) -> None:
        messagebox.showinfo(
            "CarenDMR Tastenkürzel",
            "F1 Hilfe\nF2 TG wechseln\nF3 TX EIN/AUS\nF4 Stumm\n\nWeitere Tastenkürzel werden später frei definierbar.",
            parent=self.root,
        )

    def _build_operation_tab(self, outer: ttk.Frame) -> None:
        """Freigegebene Funkgeräteansicht mit festen, nicht springenden Bereichen."""
        bg, card, card_alt = self.colors["background"], self.colors["card"], self.colors["card_alt"]
        text, muted = self.colors["text"], self.colors["muted"]
        blue, green, red = self.colors["blue"], self.colors["green"], self.colors["red"]
        outer.configure(style="App.TFrame")
        for col, weight in enumerate((36, 36, 28)):
            outer.columnconfigure(col, weight=weight, uniform="main")
        outer.rowconfigure(1, weight=1)
        outer.rowconfigure(2, weight=1)

        # Feste Verbindungs- und TG-Leiste
        channel = tk.Frame(outer, bg=card, padx=14, pady=12, height=132)
        channel.grid(row=0, column=0, columnspan=3, sticky="ew", pady=(0, 12))
        channel.grid_propagate(False)
        for col, minsize in enumerate((310, 150, 130, 170, 210, 210)):
            channel.columnconfigure(col, minsize=minsize, weight=1 if col in (1, 2, 3) else 0)

        self.connection_card = tk.Frame(channel, bg="#128241", width=300, height=102, padx=18, pady=12)
        self.connection_card.grid(row=0, column=0, rowspan=2, sticky="nsew", padx=(0, 16))
        self.connection_card.grid_propagate(False)
        self.connection_title = tk.Label(self.connection_card, textvariable=self.brandmeister_var, bg="#128241", fg="white",
                                         anchor="w", width=18, font=("Segoe UI", 20, "bold"))
        self.connection_title.grid(row=0, column=0, sticky="w")
        self.connection_server = tk.Label(self.connection_card, textvariable=self.server_var, bg="#128241", fg="white",
                                          anchor="w", width=30, font=("Segoe UI", 10))
        self.connection_server.grid(row=1, column=0, sticky="w", pady=(10, 0))

        def heading(label: str, col: int) -> None:
            tk.Label(channel, text=label, bg=card, fg=self.colors["cyan"], anchor="w",
                     font=("Segoe UI", 9, "bold")).grid(row=0, column=col, sticky="w", padx=8)
        heading("TALKGROUP", 1); heading("TIMESLOT", 2); heading("RUFART", 3)
        self.talkgroup_entry = tk.Entry(channel, textvariable=self.talkgroup_var, width=8, justify="center",
                                        bg=card_alt, fg=text, insertbackground=text, relief="flat",
                                        font=("Segoe UI", 22, "bold"))
        self.talkgroup_entry.grid(row=1, column=1, sticky="nsew", padx=8, ipady=6)
        self.timeslot_combo = ttk.Combobox(channel, textvariable=self.timeslot_var, values=("1", "2"), state="readonly",
                                           width=5, justify="center", takefocus=True, style="Dark.TCombobox",
                                           font=("Segoe UI", 18, "bold"))
        self.timeslot_combo.grid(row=1, column=2, sticky="nsew", padx=8)
        self.call_type_combo = ttk.Combobox(channel, textvariable=self.call_type_var, values=("Gruppe", "Privat"), state="readonly",
                                            width=10, justify="center", takefocus=True, style="Dark.TCombobox",
                                            font=("Segoe UI", 13, "bold"))
        self.call_type_combo.grid(row=1, column=3, sticky="nsew", padx=8)
        self.switch_button = tk.Button(channel, text="TG wechseln", command=self._switch_receive_target,
                                       bg=blue, fg="white", activebackground=self.colors["blue_dark"], activeforeground="white",
                                       relief="flat", bd=0, font=("Segoe UI", 12, "bold"), state="disabled")
        self.switch_button.grid(row=0, column=4, rowspan=2, sticky="nsew", padx=10)
        self.connect_button = tk.Button(channel, text="CONNECT", command=self._toggle_connection,
                                        bg=self.colors["green_dark"], fg="white", activeforeground="white",
                                        relief="flat", bd=0, font=("Segoe UI", 13, "bold"))
        self.connect_button.grid(row=0, column=5, rowspan=2, sticky="nsew", padx=(10, 0))

        # Aktuelle Station – alle Inhalte bleiben in festen Rasterzellen
        station = tk.Frame(outer, bg=card, padx=20, pady=16, width=460, height=360)
        station.grid(row=1, column=0, sticky="nsew", padx=(0, 6), pady=(0, 12))
        station.grid_propagate(False); station.columnconfigure(0, weight=1)
        tk.Label(station, text="AKTUELLE STATION", bg=card, fg=self.colors["cyan"], anchor="w",
                 font=("Segoe UI", 10, "bold")).grid(row=0, column=0, sticky="ew")
        tk.Label(station, textvariable=self.current_callsign_var, bg=card, fg=text, anchor="w", width=14,
                 font=("Segoe UI", 32, "bold")).grid(row=1, column=0, sticky="ew", pady=(18, 0))
        tk.Label(station, textvariable=self.current_name_var, bg=card, fg=self.colors["cyan"], anchor="w", width=28,
                 font=("Segoe UI", 16)).grid(row=2, column=0, sticky="ew", pady=(2, 0))
        details = tk.Frame(station, bg=card); details.grid(row=3, column=0, sticky="ew", pady=(18, 0)); details.columnconfigure(0, weight=1)
        tk.Label(details, textvariable=self.current_location_var, bg=card, fg=muted, anchor="w", width=24,
                 font=("Segoe UI", 10)).grid(row=0, column=0, sticky="w")
        tk.Label(details, textvariable=self.current_country_var, bg=card, fg=muted, anchor="e", width=20,
                 font=("Segoe UI", 10)).grid(row=0, column=1, sticky="e")
        meta = tk.Frame(station, bg=card); meta.grid(row=4, column=0, sticky="ew", pady=(18, 0)); meta.columnconfigure(0, weight=1)
        tk.Label(meta, textvariable=self.current_dmr_id_var, bg=card, fg=muted, anchor="w", width=18,
                 font=("Segoe UI", 10)).grid(row=0, column=0, sticky="w")
        tk.Label(meta, textvariable=self.current_target_var, bg=card, fg=muted, anchor="e", width=30,
                 font=("Segoe UI", 10)).grid(row=0, column=1, sticky="e")
        bottom = tk.Frame(station, bg=card); bottom.grid(row=5, column=0, sticky="sew", pady=(28, 0)); bottom.columnconfigure(0, weight=1)
        self.worked_status_var = tk.StringVar(value="● Noch kein bestätigtes QSO")
        tk.Label(bottom, textvariable=self.worked_status_var, bg=card_alt, fg=self.colors["yellow"], anchor="w",
                 font=("Segoe UI", 10, "bold"), padx=10, pady=7, width=25).grid(row=0, column=0, sticky="w")
        tk.Label(bottom, textvariable=self.current_duration_var, bg=card, fg=self.colors["yellow"], anchor="e", width=12,
                 font=("Consolas", 18, "bold")).grid(row=0, column=1, sticky="e")

        # Funksteuerung
        radio = tk.Frame(outer, bg=card, padx=20, pady=16, width=460, height=360)
        radio.grid(row=1, column=1, sticky="nsew", padx=6, pady=(0, 12))
        radio.grid_propagate(False); radio.columnconfigure(0, weight=1)
        tk.Label(radio, text="FUNKSTEUERUNG", bg=card, fg=self.colors["cyan"], anchor="w",
                 font=("Segoe UI", 10, "bold")).grid(row=0, column=0, sticky="ew")
        self.parrot_button = tk.Button(radio, text="TX AUS\nZum Senden drücken", command=self._toggle_transmit,
                                       font=("Segoe UI", 18, "bold"), bg="#1769d2", fg="white",
                                       activebackground="#0f54ad", activeforeground="white", relief="flat", bd=0,
                                       disabledforeground="#d7d7d7", state="disabled", cursor="hand2")
        self.parrot_button.grid(row=1, column=0, sticky="nsew", pady=(16, 12), ipady=24)
        self.operation_mute_check = ttk.Checkbutton(radio, text="Stumm (Strg+M)", variable=self.output_muted_var,
                                                    command=self._on_output_mute_changed, takefocus=True,
                                                    style="Switch.TCheckbutton")
        self.operation_mute_check.grid(row=2, column=0, sticky="w", pady=(0, 10))
        tk.Label(radio, text="RX-PEGEL", bg=card, fg=text, font=("Segoe UI", 9, "bold")).grid(row=3, column=0, sticky="w")
        ttk.Progressbar(radio, variable=self.output_level_var, maximum=100, style="RX.Horizontal.TProgressbar").grid(row=4, column=0, sticky="ew", pady=(4, 10))
        tk.Label(radio, text="MIC-PEGEL", bg=card, fg=text, font=("Segoe UI", 9, "bold")).grid(row=5, column=0, sticky="w")
        self.microphone_level = ttk.Progressbar(radio, variable=self.microphone_level_var, maximum=100, style="MIC.Horizontal.TProgressbar")
        self.microphone_level.grid(row=6, column=0, sticky="ew", pady=(4, 0))

        # Systeminformation
        system = tk.Frame(outer, bg=card, padx=20, pady=16, width=340, height=360)
        system.grid(row=1, column=2, sticky="nsew", padx=(6, 0), pady=(0, 12))
        system.grid_propagate(False); system.columnconfigure(1, weight=1)
        tk.Label(system, text="SYSTEM INFO", bg=card, fg=self.colors["cyan"], anchor="w",
                 font=("Segoe UI", 10, "bold")).grid(row=0, column=0, columnspan=2, sticky="ew")
        entries=(("Modus", self.system_mode_var), ("Netzwerk", self.system_network_var), ("Codec", self.system_codec_var),
                 ("Lautsprecher", self.system_speaker_var), ("Mikrofon", self.system_microphone_var))
        for row,(label,var) in enumerate(entries, start=1):
            tk.Label(system, text=label, bg=card, fg=muted, anchor="w", font=("Segoe UI", 10)).grid(row=row, column=0, sticky="w", pady=(18 if row==1 else 12,0))
            tk.Label(system, textvariable=var, bg=card, fg=text, anchor="e", font=("Segoe UI", 10)).grid(row=row, column=1, sticky="e", pady=(18 if row==1 else 12,0))
        self.diagnostics_status_label = tk.Label(system, text="DIAGNOSE AUS", bg=card_alt, fg=self.colors["blue"],
                                                 font=("Segoe UI", 10, "bold"), padx=14, pady=12)
        self.diagnostics_status_label.grid(row=7, column=0, columnspan=2, sticky="sew", pady=(28,0))

        # Ereignisbereich
        events = tk.Frame(outer, bg=card, padx=16, pady=12, height=210)
        events.grid(row=2, column=0, columnspan=3, sticky="nsew")
        events.grid_propagate(False); events.rowconfigure(1, weight=1); events.columnconfigure(0, weight=1)
        header = tk.Frame(events, bg=card); header.grid(row=0, column=0, sticky="ew", pady=(0,8)); header.columnconfigure(0, weight=1)
        tk.Label(header, text="EREIGNISSE", bg=card, fg=self.colors["cyan"], font=("Segoe UI", 10, "bold")).grid(row=0,column=0,sticky="w")
        tk.Label(header, textvariable=self.statistics_var, bg=card, fg=muted, anchor="e", font=("Segoe UI", 9)).grid(row=0,column=1,sticky="e")
        self.event_log = tk.Listbox(events, activestyle="none", exportselection=False, takefocus=True,
                                    bg=card_alt, fg=text, selectbackground=blue, selectforeground="white",
                                    relief="flat", borderwidth=0, highlightthickness=0, font=("Consolas", 10))
        scrollbar=ttk.Scrollbar(events, orient="vertical", command=self.event_log.yview)
        self.event_log.configure(yscrollcommand=scrollbar.set)
        self.event_log.grid(row=1,column=0,sticky="nsew"); scrollbar.grid(row=1,column=1,sticky="ns")

        footer = tk.Frame(outer, bg=bg, height=34); footer.grid(row=3,column=0,columnspan=3,sticky="ew",pady=(8,0)); footer.grid_propagate(False); footer.columnconfigure(1,weight=1)
        tk.Label(footer, text="F1 Hilfe   |   F2 TG wechseln   |   F3 Sprechen (TX)   |   F4 Stumm", bg=bg, fg=muted, font=("Segoe UI",9)).grid(row=0,column=0,sticky="w")
        tk.Label(footer, text=f"Version {__version__}   |   ● System OK", bg=bg, fg=green, font=("Segoe UI",9,"bold")).grid(row=0,column=1,sticky="e")
        self.exit_button=tk.Button(footer,text="Beenden",command=self._close,bg=card_alt,fg=text,activebackground=card,activeforeground=text,relief="flat",padx=12,pady=3)
        self.exit_button.grid(row=0,column=2,padx=(14,0),sticky="e")

    def _build_settings_tab(self, frame: ttk.Frame) -> None:
        """Kompakte Einstellungen mit linker Kategorienavigation und festen Karten."""
        bg, card, card_alt = self.colors["background"], self.colors["card"], self.colors["card_alt"]
        text, muted = self.colors["text"], self.colors["muted"]
        blue, green, yellow = self.colors["blue"], self.colors["green"], self.colors["yellow"]

        frame.configure(style="App.TFrame")
        frame.columnconfigure(1, weight=1)
        frame.rowconfigure(1, weight=1)

        # Kopfzeile und Suche
        heading = tk.Frame(frame, bg=bg, height=76)
        heading.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 12))
        heading.grid_propagate(False)
        heading.columnconfigure(0, weight=1)
        heading.rowconfigure(0, minsize=38)
        heading.rowconfigure(1, minsize=24)
        tk.Label(heading, text="Einstellungen", bg=bg, fg=text,
                 font=("Segoe UI", 22, "bold")).grid(row=0, column=0, sticky="sw")
        tk.Label(heading, text="Änderungen werden sofort gespeichert", bg=bg, fg=muted,
                 font=("Segoe UI", 9)).grid(row=1, column=0, sticky="nw", pady=(2, 0))
        self.settings_search_var = tk.StringVar()
        search = tk.Entry(heading, textvariable=self.settings_search_var, width=34,
                          bg=card_alt, fg=text, insertbackground=text, relief="flat",
                          font=("Segoe UI", 10))
        search.grid(row=0, column=1, rowspan=2, sticky="e", ipady=8)
        search.insert(0, "Einstellungen durchsuchen …")
        search.bind("<FocusIn>", lambda _e: search.delete(0, tk.END) if search.get().startswith("Einstellungen") else None)
        search.bind("<Return>", self._search_settings)

        # Linke Navigation
        sidebar = tk.Frame(frame, bg=card, width=220, padx=10, pady=12)
        sidebar.grid(row=1, column=0, sticky="nsw", padx=(0, 12))
        sidebar.grid_propagate(False)
        content = tk.Frame(frame, bg=bg)
        content.grid(row=1, column=1, sticky="nsew")
        content.rowconfigure(0, weight=1)
        content.columnconfigure(0, weight=1, minsize=720)
        content.columnconfigure(1, weight=0, minsize=280)

        self._settings_pages = {}
        self._settings_nav_buttons = {}
        sections = (
            ("audio", "Audio"),
            ("network", "Netzwerk"),
            ("data", "Daten"),
            ("operation", "Bedienung"),
            ("diagnostics", "Diagnose"),
            ("extensions", "Erweiterungen"),
        )
        for row, (key, caption) in enumerate(sections):
            button = tk.Button(sidebar, text=caption, anchor="w", width=20,
                               command=lambda section=key: self._show_settings_section(section),
                               bg=card, fg=muted, activebackground=card_alt,
                               activeforeground=text, relief="flat", bd=0,
                               padx=14, pady=10, cursor="hand2",
                               font=("Segoe UI", 10, "bold"))
            button.grid(row=row, column=0, sticky="ew", pady=2)
            self._settings_nav_buttons[key] = button
            page = tk.Frame(content, bg=bg)
            page.grid(row=0, column=0, sticky="nsew")
            page.columnconfigure(0, weight=1, uniform="settings")
            page.columnconfigure(1, weight=1, uniform="settings")
            self._settings_pages[key] = page

        def card_box(parent: tk.Widget, title: str, subtitle: str = "", row: int = 0, column: int = 0,
                     columnspan: int = 1, height: int = 220) -> tk.Frame:
            box = tk.Frame(parent, bg=card, padx=18, pady=15, height=height)
            box.grid(row=row, column=column, columnspan=columnspan, sticky="nsew",
                     padx=(0, 8) if column == 0 else (8, 0), pady=(0, 14))
            box.grid_propagate(False)
            box.columnconfigure(0, weight=1)
            tk.Label(box, text=title, bg=card, fg=self.colors["cyan"],
                     font=("Segoe UI", 13, "bold")).grid(row=0, column=0, sticky="w")
            if subtitle:
                tk.Label(box, text=subtitle, bg=card, fg=muted,
                         font=("Segoe UI", 9), wraplength=520, justify="left").grid(row=1, column=0, sticky="w", pady=(2, 10))
            return box

        def field_label(parent: tk.Widget, text_value: str, row: int) -> None:
            tk.Label(parent, text=text_value, bg=card, fg=muted,
                     font=("Segoe UI", 9, "bold")).grid(row=row, column=0, sticky="w", pady=(5, 2))

        # Audio
        audio = self._settings_pages["audio"]
        audio.rowconfigure(0, weight=1); audio.rowconfigure(1, weight=1)
        mic = card_box(audio, "Mikrofon", "Eingabegerät und Sendepegel", 0, 0, height=260)
        field_label(mic, "Gerät", 2)
        self.microphone_combo = ttk.Combobox(mic, textvariable=self.microphone_var, state="readonly",
                                             takefocus=True, style="Dark.TCombobox")
        self.microphone_combo.grid(row=3, column=0, sticky="ew")
        self.microphone_combo.bind("<<ComboboxSelected>>", self._select_microphone)
        tk.Button(mic, text="Neu einlesen", command=self._scan_microphones,
                  bg=card_alt, fg=text, activebackground=blue, activeforeground="white",
                  relief="flat", padx=12, pady=6).grid(row=4, column=0, sticky="w", pady=(8, 4))
        tk.Label(mic, textvariable=self.microphone_status_var, bg=card, fg=muted,
                 wraplength=470, justify="left", font=("Segoe UI", 9)).grid(row=5, column=0, sticky="w")
        field_label(mic, "Mikrofonverstärkung", 6)
        gain = tk.Frame(mic, bg=card); gain.grid(row=7, column=0, sticky="ew"); gain.columnconfigure(0, weight=1)
        self.microphone_gain_scale = ttk.Scale(gain, from_=25, to=200, variable=self.microphone_gain_var,
                                               command=self._on_microphone_gain_changed)
        self.microphone_gain_scale.grid(row=0, column=0, sticky="ew")
        tk.Label(gain, textvariable=self.microphone_gain_text_var, bg=card, fg=text, width=7).grid(row=0, column=1, padx=(8, 0))

        output = card_box(audio, "Wiedergabe", "Lautsprecher und Empfangslautstärke", 0, 1, height=260)
        field_label(output, "Ausgabelautstärke", 2)
        volume = tk.Frame(output, bg=card); volume.grid(row=3, column=0, sticky="ew"); volume.columnconfigure(0, weight=1)
        ttk.Scale(volume, from_=0, to=400, variable=self.output_volume_var,
                  command=self._on_output_volume_changed).grid(row=0, column=0, sticky="ew")
        tk.Label(volume, textvariable=self.output_volume_text_var, bg=card, fg=text, width=7).grid(row=0, column=1, padx=(8, 0))
        ttk.Checkbutton(output, text="Automatische Lautstärkeanpassung (AGC)", variable=self.output_agc_var,
                        command=self._on_output_agc_changed, style="Switch.TCheckbutton").grid(row=4, column=0, sticky="w", pady=(10, 2))
        ttk.Checkbutton(output, text="Sprache für TX optimieren", variable=self.transmit_optimizer_var,
                        style="Switch.TCheckbutton").grid(row=5, column=0, sticky="w", pady=2)
        tk.Label(output, textvariable=self.output_status_var, bg=card, fg=muted,
                 font=("Segoe UI", 9), wraplength=470).grid(row=6, column=0, sticky="w", pady=(10, 0))

        codec = card_box(audio, "AMBE-Codec", "Automatische Prüfung beim Programmstart", 1, 0, columnspan=2, height=190)
        codec.columnconfigure(0, weight=1); codec.columnconfigure(1, weight=0)
        tk.Label(codec, textvariable=self.encoder_status_var, bg=card, fg=green,
                 font=("Segoe UI", 10, "bold"), wraplength=720, justify="left").grid(row=2, column=0, sticky="w", pady=(4, 2))
        tk.Label(codec, textvariable=self.encoder_plugin_var, bg=card, fg=muted,
                 font=("Consolas", 8), wraplength=720, justify="left").grid(row=3, column=0, sticky="w")
        codec_controls = tk.Frame(codec, bg=card)
        codec_controls.grid(row=2, column=1, rowspan=2, sticky="e", padx=(16, 0))
        self.encoder_select_button = tk.Button(codec_controls, text="Plugin zuordnen", command=self._select_encoder_plugin,
                                               bg=card_alt, fg=text, activebackground=blue, activeforeground="white",
                                               relief="flat", padx=12, pady=7)
        self.encoder_verify_button = tk.Button(codec_controls, text="Erneut prüfen", command=self._verify_encoder_plugin,
                                               bg=blue, fg="white", activebackground=self.colors["blue_dark"],
                                               activeforeground="white", relief="flat", padx=12, pady=7)
        self.encoder_select_button.grid(row=0, column=0, padx=(0, 8)); self.encoder_verify_button.grid(row=0, column=1)

        # Netzwerk
        network = self._settings_pages["network"]
        connection = card_box(network, "BrandMeister", "Aktive Verbindung und lokales Profil", 0, 0, columnspan=2, height=230)
        profile = self._load_brandmeister_profile_summary()
        rows = (("Server", profile["server"]), ("Rufzeichen", profile["callsign"]),
                ("DMR-ID", profile["dmr_id"]), ("Port", profile["port"]))
        for idx, (label_text, value_text) in enumerate(rows, start=2):
            tk.Label(connection, text=label_text, bg=card, fg=muted,
                     font=("Segoe UI", 9, "bold"), width=14, anchor="w").grid(row=idx, column=0, sticky="w", pady=3)
            tk.Label(connection, text=value_text, bg=card, fg=text,
                     font=("Segoe UI", 10), anchor="w").grid(row=idx, column=1, sticky="w", pady=3)
        tk.Label(connection, text="Zugangsdaten werden weiterhin ausschließlich in brandmeister.local.json verwaltet.",
                 bg=card, fg=yellow, font=("Segoe UI", 9), wraplength=680,
                 justify="left").grid(row=6, column=0, columnspan=2, sticky="w", pady=(10, 0))

        # Daten
        data_page = self._settings_pages["data"]
        contacts = card_box(data_page, "RadioID-Kontaktdaten", "Namen, Rufzeichen und Länderzuordnung", 0, 0, height=225)
        tk.Label(contacts, textvariable=self.contacts_var, bg=card, fg=text,
                 wraplength=470, justify="left", font=("Segoe UI", 10)).grid(row=2, column=0, sticky="w", pady=(4, 14))
        self.contacts_button = tk.Button(contacts, text="Kontaktdaten aktualisieren", command=self._update_contacts,
                                         bg=blue, fg="white", activebackground=self.colors["blue_dark"],
                                         activeforeground="white", relief="flat", padx=14, pady=8)
        self.contacts_button.grid(row=3, column=0, sticky="w")
        qso = card_box(data_page, "QSO-Datenbank", "Historie und spätere Logbuchübergabe", 0, 1, height=225)
        tk.Label(qso, text="QSO-Historie wird lokal in SQLite gespeichert.", bg=card, fg=text,
                 font=("Segoe UI", 10), wraplength=470, justify="left").grid(row=2, column=0, sticky="w", pady=(4, 10))
        tk.Label(qso, text="Sicherung, Wiederherstellung und UDP-Logbuch folgen in einer späteren Ausbaustufe.",
                 bg=card, fg=muted, font=("Segoe UI", 9), wraplength=470,
                 justify="left").grid(row=3, column=0, sticky="w")

        # Bedienung
        operation = self._settings_pages["operation"]
        shortcuts = card_box(operation, "Tastenkürzel", "Zentrale Bedienung ohne Maus", 0, 0, columnspan=2, height=285)
        shortcut_rows = (("F1", "Hilfe"), ("F2", "TG wechseln"), ("F3", "TX EIN / AUS"),
                         ("F4", "Stumm"), ("Strg+Q", "Beenden"), ("Strg+U", "TG wechseln"))
        for idx, (key_text, action_text) in enumerate(shortcut_rows, start=2):
            tk.Label(shortcuts, text=key_text, bg=card_alt, fg=self.colors["cyan"],
                     width=12, padx=8, pady=4, font=("Consolas", 10, "bold")).grid(row=idx, column=0, sticky="w", pady=2)
            tk.Label(shortcuts, text=action_text, bg=card, fg=text,
                     font=("Segoe UI", 10)).grid(row=idx, column=1, sticky="w", padx=(12, 0))
        tk.Label(shortcuts, text="Frei definierbare Zuordnungen werden mit dem ShortcutManager ergänzt.",
                 bg=card, fg=yellow, font=("Segoe UI", 9)).grid(row=8, column=0, columnspan=2, sticky="w", pady=(10, 0))

        # Diagnose
        diagnostics = self._settings_pages["diagnostics"]
        diag_card = card_box(diagnostics, "Diagnosemodus", "Ausführliche Ausgaben und Audioaufzeichnungen für gezielte Fehlersuche", 0, 0, columnspan=2, height=315)
        ttk.Checkbutton(diag_card, text="Diagnosemodus aktiv (ausführliche PowerShell-Ausgaben)", variable=self.diagnostics_enabled_var,
                        command=self._on_diagnostics_changed, style="Switch.TCheckbutton").grid(row=2, column=0, sticky="w", pady=(8, 6))
        tk.Label(diag_card, text="Im Normalbetrieb ausgeschaltet. Die Änderung wirkt sofort und wird lokal gespeichert.",
                 bg=card, fg=muted, font=("Segoe UI", 9), wraplength=720,
                 justify="left").grid(row=3, column=0, sticky="w")
        tk.Label(diag_card, text="PowerShell bleibt dadurch ruhig; Empfang, Decoder und Audio arbeiten unverändert weiter.",
                 bg=card, fg=text, font=("Segoe UI", 10), wraplength=720,
                 justify="left").grid(row=4, column=0, sticky="w", pady=(12, 0))
        ttk.Checkbutton(diag_card, text="WAV-Audiodiagnose aktiv (TX roh, vor AMBE und Parrot-RX)",
                        variable=self.audio_debug_wav_enabled_var, command=self._on_audio_debug_wav_changed,
                        style="Switch.TCheckbutton").grid(row=5, column=0, sticky="w", pady=(20, 6))
        tk.Label(diag_card, text="Nur bei gezielter Fehlersuche einschalten. Dateien werden unter logs\\audio_debug gespeichert.",
                 bg=card, fg=muted, font=("Segoe UI", 9), wraplength=720,
                 justify="left").grid(row=6, column=0, sticky="w")

        # Erweiterungen
        extensions = self._settings_pages["extensions"]
        ext = card_box(extensions, "Erweiterungen", "Reservierter Platz für kommende Module", 0, 0, columnspan=2, height=270)
        future = ("UDP-Logbuch", "APRS", "Stream Deck / Fußtaster", "Plugins")
        for idx, name in enumerate(future, start=2):
            tile = tk.Frame(ext, bg=card_alt, padx=14, pady=10, width=240, height=58)
            tile.grid(row=idx // 2, column=idx % 2, sticky="ew", padx=(0, 8) if idx % 2 == 0 else (8, 0), pady=6)
            tile.grid_propagate(False)
            tk.Label(tile, text=name, bg=card_alt, fg=text,
                     font=("Segoe UI", 10, "bold")).pack(anchor="w")
            tk.Label(tile, text="Später", bg=card_alt, fg=muted,
                     font=("Segoe UI", 8)).pack(anchor="w")
        ext.columnconfigure(0, weight=1); ext.columnconfigure(1, weight=1)

        self._show_settings_section("audio")

    def _show_settings_section(self, section: str) -> None:
        page = getattr(self, "_settings_pages", {}).get(section)
        if page is None:
            return
        page.tkraise()
        for key, button in getattr(self, "_settings_nav_buttons", {}).items():
            active = key == section
            button.configure(
                bg=self.colors["blue"] if active else self.colors["card"],
                fg="white" if active else self.colors["muted"],
                activebackground=self.colors["blue_dark"] if active else self.colors["card_alt"],
                activeforeground="white",
            )

    def _search_settings(self, _event: object | None = None) -> None:
        term = self.settings_search_var.get().strip().lower()
        mapping = {
            "mikrofon": "audio", "lautsprecher": "audio", "audio": "audio", "ambe": "audio", "codec": "audio",
            "server": "network", "brandmeister": "network", "rufzeichen": "network", "dmr": "network",
            "datenbank": "data", "kontakt": "data", "qso": "data", "logbuch": "data",
            "taste": "operation", "shortcut": "operation", "bedienung": "operation",
            "diagnose": "diagnostics", "debug": "diagnostics", "log": "diagnostics",
            "plugin": "extensions", "aprs": "extensions", "udp": "extensions", "stream": "extensions",
        }
        for keyword, section in mapping.items():
            if keyword in term:
                self._show_settings_section(section)
                return
        self.events.publish(f"Keine passende Einstellung für '{term}' gefunden.")

    def _load_brandmeister_profile_summary(self) -> dict[str, str]:
        path = self.project_root / "config" / "brandmeister.local.json"
        result = {"server": "Nicht konfiguriert", "callsign": "—", "dmr_id": "—", "port": "62031"}
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return result
        result["server"] = str(data.get("host", result["server"]))
        result["callsign"] = str(data.get("callsign", result["callsign"]))
        result["dmr_id"] = str(data.get("dmr_id", result["dmr_id"]))
        result["port"] = str(data.get("port", result["port"]))
        return result

    def _on_diagnostics_changed(self) -> None:
        enabled = bool(self.diagnostics_enabled_var.get())
        set_diagnostics_enabled(enabled)
        state = "eingeschaltet" if enabled else "ausgeschaltet"
        self.events.publish(f"Diagnosemodus {state}.")
        if hasattr(self, "diagnostics_status_label"):
            self.diagnostics_status_label.configure(text="DIAGNOSE EIN" if enabled else "DIAGNOSE AUS", fg=self.colors["yellow"] if enabled else self.colors["blue"])

    def _on_audio_debug_wav_changed(self) -> None:
        enabled = bool(self.audio_debug_wav_enabled_var.get())
        self.audio_send_service.set_audio_debug_wav_enabled(enabled)
        self.audio_send_service.save_settings()
        state = "eingeschaltet" if enabled else "ausgeschaltet"
        self.events.publish(f"WAV-Audiodiagnose {state}.")

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
        """Moderne Stationshistorie mit manuell bestätigtem QSO-Status."""
        bg, card, card_alt = self.colors["background"], self.colors["card"], self.colors["card_alt"]
        text, muted, cyan = self.colors["text"], self.colors["muted"], self.colors["cyan"]
        frame.configure(style="App.TFrame")
        frame.rowconfigure(1, weight=1)
        frame.columnconfigure(0, weight=1)

        header = tk.Frame(frame, bg=bg, height=84)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        header.grid_propagate(False)
        header.columnconfigure(0, weight=1)
        title = tk.Frame(header, bg=bg)
        title.grid(row=0, column=0, sticky="w")
        tk.Label(title, text="QSO-HISTORIE", bg=bg, fg=text,
                 font=("Segoe UI", 22, "bold")).pack(anchor="w")
        tk.Label(title, text="Gehörte Stationen und bestätigte Funkkontakte",
                 bg=bg, fg=muted, font=("Segoe UI", 10)).pack(anchor="w", pady=(2, 0))

        search = tk.Frame(header, bg=bg)
        search.grid(row=0, column=1, sticky="e")
        tk.Label(search, text="SUCHE", bg=bg, fg=cyan,
                 font=("Segoe UI", 9, "bold")).grid(row=0, column=0, sticky="w")
        entry = tk.Entry(search, textvariable=self.history_search_var, width=28,
                         bg=card_alt, fg=text, insertbackground=text, relief="flat",
                         font=("Segoe UI", 11))
        entry.grid(row=1, column=0, ipady=7, padx=(0, 8))
        entry.bind("<KeyRelease>", lambda _event: self._refresh_history())
        tk.Button(search, text="Aktualisieren", command=self._refresh_history,
                  bg=self.colors["blue"], fg="white", activebackground=self.colors["blue_dark"],
                  activeforeground="white", relief="flat", bd=0, padx=16, pady=7,
                  font=("Segoe UI", 10, "bold")).grid(row=1, column=1)

        content = tk.Frame(frame, bg=bg)
        content.grid(row=1, column=0, sticky="nsew")
        content.rowconfigure(0, weight=1)
        content.columnconfigure(0, weight=1)

        table_card = tk.Frame(content, bg=card, padx=14, pady=12)
        table_card.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        table_card.rowconfigure(2, weight=1)
        table_card.columnconfigure(0, weight=1)
        tk.Label(table_card, text="STATIONEN", bg=card, fg=cyan,
                 font=("Segoe UI", 10, "bold")).grid(row=0, column=0, sticky="w")
        tk.Label(table_card, textvariable=self.history_summary_var, bg=card, fg=muted,
                 font=("Segoe UI", 9)).grid(row=0, column=1, sticky="e")

        columns = ("last", "callsign", "name", "country", "target", "heard", "duration", "worked")
        style = ttk.Style(self.root)
        style.configure("History.Treeview", background=card_alt, fieldbackground=card_alt,
                        foreground=text, rowheight=30, borderwidth=0,
                        font=("Segoe UI", 10))
        style.configure("History.Treeview.Heading", background=card, foreground=cyan,
                        relief="flat", font=("Segoe UI", 9, "bold"))
        style.map("History.Treeview", background=[("selected", self.colors["blue_dark"])],
                  foreground=[("selected", "white")])
        table_area = ttk.Frame(table_card, style="App.TFrame")
        table_area.grid(row=2, column=0, columnspan=2, sticky="nsew", pady=(10, 0))
        table_area.rowconfigure(0, weight=1)
        table_area.columnconfigure(0, weight=1)
        self.history_tree = ttk.Treeview(table_area, columns=columns, show="headings",
                                         takefocus=True, style="History.Treeview")
        headings = {
            "last": "Zuletzt gehört", "callsign": "Rufzeichen", "name": "Name",
            "country": "Land", "target": "Letztes Ziel", "heard": "Durchgänge",
            "duration": "Gesamtdauer", "worked": "QSO",
        }
        widths = {"last": 120, "callsign": 90, "name": 115, "country": 95,
                  "target": 90, "heard": 78, "duration": 88, "worked": 96}
        for column in columns:
            self.history_tree.heading(column, text=headings[column])
            self.history_tree.column(column, width=widths[column], minwidth=58, anchor="w", stretch=False)
        scroll = ttk.Scrollbar(table_area, orient="vertical", command=self.history_tree.yview)
        self.history_tree.configure(yscrollcommand=scroll.set)
        self.history_tree.grid(row=0, column=0, sticky="nsew")
        scroll.grid(row=0, column=1, sticky="ns")
        self.history_tree.bind("<<TreeviewSelect>>", self._on_history_selected)
        self.history_tree.bind("<Configure>", self._resize_history_columns)
        self.history_tree.bind("<Double-1>", lambda _event: self._toggle_history_worked())

        detail = tk.Frame(content, bg=card, padx=18, pady=16, width=280)
        detail.grid(row=0, column=1, sticky="ns", padx=(8, 0))
        detail.grid_propagate(False)
        detail.columnconfigure(0, weight=1)
        tk.Label(detail, text="QSO-STATUS", bg=card, fg=cyan,
                 font=("Segoe UI", 10, "bold")).grid(row=0, column=0, sticky="w")
        tk.Label(detail, textvariable=self.history_selection_var, bg=card, fg=text,
                 justify="left", anchor="nw", wraplength=235,
                 font=("Segoe UI", 12)).grid(row=1, column=0, sticky="new", pady=(18, 20))
        self.history_qso_button = tk.Button(
            detail, textvariable=self.history_qso_button_var,
            command=self._toggle_history_worked, state="disabled",
            bg=self.colors["green_dark"], fg="white", activebackground=self.colors["green"],
            activeforeground="white", disabledforeground=muted, relief="flat", bd=0,
            padx=16, pady=12, font=("Segoe UI", 11, "bold"),
        )
        self.history_qso_button.grid(row=2, column=0, sticky="ew")
        tk.Label(detail,
                 text="Ein bestätigtes QSO bedeutet: Mit dieser Station wurde tatsächlich gesprochen. "
                      "Diese Kennzeichnung bildet später die Grundlage für einen Logbucheintrag.",
                 bg=card, fg=muted, justify="left", wraplength=235,
                 font=("Segoe UI", 9)).grid(row=3, column=0, sticky="sw", pady=(20, 0))
        self._refresh_history()

    def _resize_history_columns(self, event: object | None = None) -> None:
        """Passt alle Historientabellenspalten an die tatsächlich verfügbare Breite an."""
        if not hasattr(self, "history_tree"):
            return
        width = getattr(event, "width", 0) if event is not None else self.history_tree.winfo_width()
        available = max(1, int(width) - 2)
        proportions = {
            "last": 0.16, "callsign": 0.12, "name": 0.15, "country": 0.13,
            "target": 0.12, "heard": 0.09, "duration": 0.11, "worked": 0.12,
        }
        used = 0
        columns = tuple(proportions)
        for column in columns[:-1]:
            column_width = max(58, int(available * proportions[column]))
            self.history_tree.column(column, width=column_width, stretch=False)
            used += column_width
        self.history_tree.column(columns[-1], width=max(58, available - used), stretch=True)

    def _refresh_history(self) -> None:
        if not hasattr(self, "history_tree"):
            return
        selected_source = self._selected_history_source_id
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)
        self._history_rows.clear()
        summaries = self.receive_service.history.list_station_summaries(self.history_search_var.get())
        worked_count = sum(1 for item in summaries if item.worked)
        self.history_summary_var.set(
            f"{len(summaries)} Stationen  ·  {worked_count} bestätigte QSOs"
        )
        restore_iid = ""
        from datetime import datetime
        for summary in summaries:
            try:
                timestamp = datetime.fromisoformat(summary.last_heard_at).astimezone().strftime("%d.%m.%Y %H:%M")
            except ValueError:
                timestamp = summary.last_heard_at
            target = f"TG {summary.last_talkgroup} / TS{summary.last_timeslot}"
            iid = f"station-{summary.source_id}"
            self._history_rows[iid] = summary
            self.history_tree.insert("", tk.END, iid=iid, values=(
                timestamp, summary.callsign or "Unbekannt", summary.name,
                summary.country, target, summary.heard_count,
                self._format_history_duration(summary.total_duration_seconds),
                "✓ Gesprochen" if summary.worked else "Nur gehört",
            ))
            if summary.source_id == selected_source:
                restore_iid = iid
        if restore_iid:
            self.history_tree.selection_set(restore_iid)
            self.history_tree.focus(restore_iid)
            self.history_tree.see(restore_iid)
            self._on_history_selected()
        elif not summaries:
            self._selected_history_source_id = None
            self.history_selection_var.set("Keine Station ausgewählt")
            self.history_qso_button_var.set("QSO bestätigen")
            self.history_qso_button.configure(state="disabled")

    @staticmethod
    def _format_history_duration(seconds: float) -> str:
        total = max(0, int(round(seconds)))
        minutes, remaining = divmod(total, 60)
        if minutes:
            return f"{minutes} min {remaining:02d} s"
        return f"{remaining} s"

    def _on_history_selected(self, _event: object | None = None) -> None:
        selection = self.history_tree.selection()
        if not selection:
            return
        summary = self._history_rows.get(selection[0])
        if summary is None:
            return
        self._selected_history_source_id = summary.source_id
        location = " / ".join(part for part in (summary.city, summary.state, summary.country) if part)
        status = "QSO bestätigt" if summary.worked else "Bisher nur gehört"
        self.history_selection_var.set(
            f"{summary.callsign or 'Unbekannt'}\n"
            f"{summary.name or 'Name nicht vorhanden'}\n\n"
            f"DMR-ID {summary.source_id}\n"
            f"{location or 'Ort nicht vorhanden'}\n\n"
            f"{summary.heard_count} Sprechdurchgänge\n"
            f"{self._format_history_duration(summary.total_duration_seconds)} Gesamtdauer\n\n"
            f"{status}"
        )
        self.history_qso_button_var.set("QSO zurücknehmen" if summary.worked else "QSO bestätigen")
        self.history_qso_button.configure(
            state="normal",
            bg=self.colors["red"] if summary.worked else self.colors["green_dark"],
        )

    def _toggle_history_worked(self) -> None:
        selection = self.history_tree.selection() if hasattr(self, "history_tree") else ()
        if not selection:
            return
        summary = self._history_rows.get(selection[0])
        if summary is None:
            return
        new_state = not summary.worked
        self.receive_service.history.set_worked(summary.source_id, new_state)
        if self._worked_status_source_id == summary.source_id:
            self._worked_status_value = new_state
            self.worked_status_var.set(
                "✓ Bereits gesprochen" if new_state else "● Noch kein bestätigtes QSO"
            )
        action = "als gesprochen bestätigt" if new_state else "auf nur gehört zurückgesetzt"
        self.events.publish(f"{summary.callsign or summary.source_id} wurde {action}.")
        self._refresh_history()

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
        self.parrot_button.configure(text="TX EIN\nZum Beenden erneut drücken", bg="#c62828", activebackground="#9d1f1f")
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
            self.parrot_button.configure(text="TX AUS\nZum Senden drücken", state="disabled", bg="#1769d2")
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
                    self.parrot_button.configure(state="normal", text="TX AUS\nZum Senden drücken", bg="#1769d2")
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
                    self.parrot_button.configure(state="normal", text="TX AUS\nZum Senden drücken", bg="#1769d2", activebackground="#0f54ad")
                    self._refresh_transmit_history()
                elif kind == "parrot_error":
                    self._tx_active = False
                    self._tx_recording = False
                    self._tx_stop_event = None
                    self._tx_started_at = None
                    self._release_tx_pointer_grab()
                    self.events.publish(f"Parrot-Test sicher abgebrochen: {value}", EventLevel.ERROR)
                    self.parrot_button.configure(state="normal", text="TX AUS\nZum Senden drücken", bg="#1769d2", activebackground="#0f54ad")
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
        self.brandmeister_var.set(brandmeister_text.upper())
        self.receive_var.set("Aktiv" if state.receive_active else "Inaktiv")
        if state.connection is ConnectionState.CONNECTING:
            connection_color = "#9a6a00"
        elif state.brandmeister_connected:
            connection_color = "#128241"
        elif state.connection is ConnectionState.ERROR:
            connection_color = self.colors["red"]
        else:
            connection_color = self.colors["card_alt"]
        if hasattr(self, "connection_card"):
            self.connection_card.configure(bg=connection_color)
            self.connection_title.configure(bg=connection_color)
            self.connection_server.configure(bg=connection_color)
        self.system_mode_var.set(f"DMR TS{state.timeslot}")
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
            self._worked_status_source_id = None
            self._worked_status_value = False
            self.worked_status_var.set("● Noch kein bestätigtes QSO")
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
            if self._worked_status_source_id != call.source_id:
                self._worked_status_source_id = call.source_id
                self._worked_status_value = self.receive_service.history.is_worked(call.source_id)
            self.worked_status_var.set(
                "✓ Bereits gesprochen" if self._worked_status_value else "● Noch kein bestätigtes QSO"
            )
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
            bg=self.colors["red"] if running else self.colors["green_dark"],
            activebackground="#a52d2d" if running else "#116a49",
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
        self.events.publish(
            "CarenDMR ist bereit. Der Empfang ist noch nicht verbunden.",
            code="system.ready",
            long_text="CarenDMR ist bereit. Der Empfang ist noch nicht verbunden.",
            category=InformationCategory.SYSTEM,
            priority=InformationPriority.HIGH,
        )
        self.root.mainloop()
        return 0


def run_gui(project_root: Path) -> int:
    return MainWindow(project_root).run()
