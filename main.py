from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from app.config import APP_NAME, APP_VERSION
from app.main_window import MainWindow
from app.styles import APP_STYLESHEET


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setStyleSheet(APP_STYLESHEET)

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
