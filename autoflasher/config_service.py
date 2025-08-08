# config.py
import os
import platform
import json

JLINK_WINDOWS = "JLink.exe"
JLINK_UNIX = "JLinkExe"
JLINK_DEFAULT_INTERFACE = "SWD"
JLINK_DEFAULT_SPEED = 4000
CONFIG_FILENAME = "config.json"

def get_default_config() -> dict:
    return {
        "jlink_path": JLINK_WINDOWS if platform.system() == "Windows" else JLINK_UNIX,
        "jlink_interface": JLINK_DEFAULT_INTERFACE,
        "jlink_speed": JLINK_DEFAULT_SPEED,
        # Optional user-set defaults:
        "default_folder": "",
        "default_target": "",
        "firmware_root": "firmware",
    }

def load_config(base_dir: str) -> dict:
    """Load config.json from base_dir; merge with defaults."""
    config = get_default_config()
    path = os.path.join(base_dir, CONFIG_FILENAME)
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                file_cfg = json.load(f)
            config.update(file_cfg or {})
        except Exception as e:
            print(f"[config] Warning: failed to load config.json ({e}); using defaults.")
    return config

def save_config(base_dir: str, cfg: dict) -> None:
    """Write config.json to base_dir."""
    path = os.path.join(base_dir, CONFIG_FILENAME)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)
