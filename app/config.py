from __future__ import annotations

import sys
from pathlib import Path

APP_NAME = "ILSungTech Tools"
APP_VERSION = "1.0.0"
WINDOW_TITLE = "ILSungTech Tools"
WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 740
WINDOW_MIN_WIDTH = 960
WINDOW_MIN_HEIGHT = 560


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
