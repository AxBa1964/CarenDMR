from pathlib import Path

from carendmr.tg_monitor.window import run_tg_monitor


if __name__ == "__main__":
    raise SystemExit(run_tg_monitor(Path(__file__).resolve().parent))
