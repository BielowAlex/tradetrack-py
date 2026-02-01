import json
import sys
from pathlib import Path
from typing import Optional


def get_base_dir() -> Path:
    """Папка з exe (при збірці PyInstaller) або папка bridge (при запуску з Python)."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent


CONFIG_PATH = get_base_dir() / "config.json"
STATE_PATH = get_base_dir() / "state.json"


def save_config(config_dict: dict) -> None:
    """Зберегти конфіг (викликається після отримання з фронту)."""
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config_dict, f, indent=2)


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(
            f"Config not found: {CONFIG_PATH}\n"
            "Run the app and connect from the web app (bridge section)."
        )
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _load_state() -> dict:
    if not STATE_PATH.exists():
        return {}
    try:
        with open(STATE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, KeyError):
        return {}


def _save_state(data: dict) -> None:
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def load_last_sync() -> Optional[str]:
    return _load_state().get("last_sync_at")


def save_last_sync(iso_datetime: str) -> None:
    data = _load_state()
    data["last_sync_at"] = iso_datetime
    _save_state(data)


def has_saved_language() -> bool:
    """Чи збережено вибір мови (наступні запуски не питають)."""
    return "language" in _load_state()


def get_language() -> str:
    """Повертає поточну мову: 'uk' або 'en'. За замовчуванням 'uk'."""
    return _load_state().get("language", "uk") or "uk"


def save_language(lang: str) -> None:
    """Зберігає вибрану мову в state.json."""
    data = _load_state()
    data["language"] = lang if lang in ("uk", "en") else "uk"
    _save_state(data)
