from carendmr.app_paths import default_data_root, prepare_data_root
from carendmr.tg_monitor.window import run_tg_monitor


if __name__ == "__main__":
    _data_root = default_data_root()
    prepare_data_root(_data_root)
    raise SystemExit(run_tg_monitor(_data_root))
