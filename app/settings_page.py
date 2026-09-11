from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.tools_page import _make_file_table, _set_table_text

LIBRARY_CHECKS = (
    ("openpyxl", "Đọc / tạo file Excel .xlsx"),
    ("PIL", "Xử lý ảnh (Pillow)"),
    ("qrcode", "Tạo mã QR"),
    ("cv2", "Tìm và đọc QR trong ảnh (OpenCV)"),
    ("rapidocr_onnxruntime", "OCR ảnh / căn cước"),
)


class SettingsPage(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("page")

        title = QLabel("Cài đặt & môi trường")
        title.setObjectName("pageTitle")

        subtitle = QLabel(
            "Kiểm tra các thư viện đã chuẩn bị cho OCR, Excel và QR. "
            "Chưa tải model OCR cho đến khi bấm kiểm tra."
        )
        subtitle.setObjectName("pageSubtitle")
        subtitle.setWordWrap(True)

        check_button = QPushButton("Kiểm tra thư viện")
        check_button.setObjectName("primaryButton")
        check_button.setCursor(Qt.CursorShape.PointingHandCursor)
        check_button.clicked.connect(self._check_libraries)

        self.table = _make_file_table(["Thư viện", "Mục đích", "Trạng thái"])
        self.status = QLabel("Chưa kiểm tra")
        self.status.setObjectName("hintText")

        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(24, 24, 24, 24)
        card_layout.setSpacing(12)
        card_layout.addWidget(title)
        card_layout.addWidget(subtitle)

        buttons = QHBoxLayout()
        buttons.addWidget(check_button)
        buttons.addStretch()
        card_layout.addLayout(buttons)
        card_layout.addWidget(self.table, 1)
        card_layout.addWidget(self.status)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.addWidget(card)

        self._fill_rows("Chưa kiểm tra")

    def _fill_rows(self, status: str) -> None:
        self.table.setRowCount(len(LIBRARY_CHECKS))
        for row, (name, purpose) in enumerate(LIBRARY_CHECKS):
            _set_table_text(self.table, row, 0, name)
            _set_table_text(self.table, row, 1, purpose)
            _set_table_text(self.table, row, 2, status)
        self.table.resizeRowsToContents()

    def _check_libraries(self) -> None:
        ready = 0
        self.table.setRowCount(len(LIBRARY_CHECKS))
        for row, (name, purpose) in enumerate(LIBRARY_CHECKS):
            try:
                self._import_library(name)
                state = "Sẵn sàng"
                ready += 1
            except Exception as error:
                state = f"Thiếu: {error.__class__.__name__}"
            _set_table_text(self.table, row, 0, name)
            _set_table_text(self.table, row, 1, purpose)
            _set_table_text(self.table, row, 2, state)
        self.table.resizeRowsToContents()
        self.status.setText(f"{ready}/{len(LIBRARY_CHECKS)} thư viện sẵn sàng")

    def _import_library(self, name: str) -> None:
        if name == "rapidocr_onnxruntime":
            try:
                __import__("rapidocr_onnxruntime")
            except ImportError:
                __import__("rapidocr")
            return
        __import__(name)
