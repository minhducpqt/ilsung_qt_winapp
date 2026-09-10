from __future__ import annotations

import sys
from pathlib import Path

APP_NAME = "QT Windows App"
APP_VERSION = "1.0.0"
WINDOW_TITLE = "QT Windows App"
WINDOW_WIDTH = 1100
WINDOW_HEIGHT = 700
WINDOW_MIN_WIDTH = 800
WINDOW_MIN_HEIGHT = 500


def app_base_dir() -> Path:
    """Project root when running from source; bundle root after PyInstaller."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent.parent


def resource_path(*parts: str) -> Path:
    """Resolve files in app/resources for both source and frozen builds."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        base = Path(sys._MEIPASS) / "app" / "resources"
    else:
        base = Path(__file__).resolve().parent / "resources"
    return base.joinpath(*parts)
