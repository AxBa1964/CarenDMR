"""Kleines barrierefreies Read-only-Hauptfenster für CarenDMR."""

from __future__ import annotations

import queue
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

from carendmr.application import EventService, ReceiveService
from carendmr.domain import ApplicationEvent, ApplicationState, ConnectionState
from carendmr.version import __version__


class MainWindow:
    """Native Tk-Steuerelemente mit stabiler Fokusreihenfolge und Textlabels."""

    def __init__(self, project_root: Path) -> None:
        self.root = tk.Tk()
        self.root.title(f"CarenDMR {__version__}")
        self.root.minsize(620, 480)

        self.events = EventService()
        self.receive_service = ReceiveService(project_root, events=self.events)
        self._updates: queue.SimpleQueue[tuple[str, object]] = queue.SimpleQueue()

        self.brandmeister_var = tk.StringVar(value="Getrennt")
        self.receive_var = tk.StringVar(value="Inaktiv")
        self.server_var = tk.StringVar(value="Nicht verbunden")
        self.talkgroup_var = tk.StringVar(value="91")
        self.timeslot_var = tk.StringVar(value="2")
        self.audio_var = tk.StringVar(value="Inaktiv")
        self.statistics_var = tk.StringVar(value="Noch keine Empfangsdaten")

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
        self.root.after(100, self._process_updates)
        self.connect_button.focus_set()

    def _build(self) -> None:
        outer = ttk.Frame(self.root, padding=16)
        outer.grid(row=0, column=0, sticky="nsew")
        self.root.rowconfigure(0, weight=1)
        self.root.columnconfigure(0, weight=1)
        outer.columnconfigure(1, weight=1)
        outer.rowconfigure(9, weight=1)

        heading = ttk.Label(outer, text="CarenDMR – Empfang", font=("TkDefaultFont", 16, "bold"))
        heading.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 12))

        fields = (
            ("BrandMeister", self.brandmeister_var),
            ("Empfang", self.receive_var),
            ("Server", self.server_var),
            ("Talkgroup", self.talkgroup_var),
            ("Timeslot", self.timeslot_var),
            ("Audioausgabe", self.audio_var),
        )
        for row, (label, variable) in enumerate(fields, start=1):
            ttk.Label(outer, text=f"{label}:").grid(row=row, column=0, sticky="nw", padx=(0, 12), pady=3)
            value = ttk.Label(outer, textvariable=variable, takefocus=True)
            value.grid(row=row, column=1, sticky="nw", pady=3)

        ttk.Label(outer, text="Empfangsstatistik:").grid(row=7, column=0, sticky="nw", padx=(0, 12), pady=(8, 3))
        ttk.Label(outer, textvariable=self.statistics_var, wraplength=460, takefocus=True).grid(
            row=7, column=1, sticky="nw", pady=(8, 3)
        )

        ttk.Label(outer, text="Ereignisprotokoll:").grid(row=8, column=0, columnspan=2, sticky="w", pady=(12, 4))
        log_frame = ttk.Frame(outer)
        log_frame.grid(row=9, column=0, columnspan=2, sticky="nsew")
        log_frame.rowconfigure(0, weight=1)
        log_frame.columnconfigure(0, weight=1)
        self.event_log = tk.Listbox(
            log_frame,
            activestyle="dotbox",
            exportselection=False,
            selectmode=tk.BROWSE,
            takefocus=True,
        )
        scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.event_log.yview)
        self.event_log.configure(yscrollcommand=scrollbar.set)
        self.event_log.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        buttons = ttk.Frame(outer)
        buttons.grid(row=10, column=0, columnspan=2, sticky="ew", pady=(12, 0))
        self.connect_button = ttk.Button(buttons, text="Verbinden und empfangen", command=self._start)
        self.disconnect_button = ttk.Button(buttons, text="Trennen", command=self._stop, state="disabled")
        self.exit_button = ttk.Button(buttons, text="Beenden", command=self._close)
        self.connect_button.grid(row=0, column=0, padx=(0, 8))
        self.disconnect_button.grid(row=0, column=1, padx=(0, 8))
        self.exit_button.grid(row=0, column=2)

        ttk.Label(
            outer,
            text="Tastenkürzel: Strg+R verbinden, Strg+T trennen, Esc oder Strg+Q beenden.",
            wraplength=560,
        ).grid(row=11, column=0, columnspan=2, sticky="w", pady=(10, 0))

    def _start(self) -> None:
        if self.receive_service.start():
            self.connect_button.configure(state="disabled")
            self.disconnect_button.configure(state="normal")
        else:
            self.events.publish("Der Empfang läuft bereits.")

    def _stop(self) -> None:
        self.receive_service.stop()

    def _close(self) -> None:
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
                else:
                    self._append_event(value)  # type: ignore[arg-type]
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
