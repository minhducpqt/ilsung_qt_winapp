from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.config import APP_NAME, COMPANY_NAME


class HomePage(QWidget):
    def __init__(self, on_open_first_tool: Callable[[], None] | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("page")
        self._on_open_first_tool = on_open_first_tool

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(16)
        layout.addWidget(self._build_hero())
        layout.addWidget(self._build_feature_grid())
        layout.addStretch()

    def _build_hero(self) -> QFrame:
        hero = QFrame()
        hero.setObjectName("heroCard")

        eyebrow = QLabel(COMPANY_NAME)
        eyebrow.setObjectName("heroEyebrow")

        title = QLabel("Bộ công cụ hỗ trợ nhân viên hành chính")
        title.setObjectName("heroTitle")
        title.setWordWrap(True)

        body = QLabel(
            "Tiện ích hỗ trợ công việc do CÔNG TY CỔ PHẦN IL-SUNG TECH nghiên cứu phát triển. "
            "Giúp nhân viên hành chính xử lý file, số hóa giấy tờ, Excel và mã QR ngay trên máy tính, chạy offline."
        )
        body.setObjectName("heroBody")
        body.setWordWrap(True)

        status = QLabel("●  Ứng dụng đang hoạt động")
        status.setObjectName("heroStatus")

        open_button = QPushButton("Mở công cụ đầu tiên")
        open_button.setObjectName("heroPrimaryButton")
        open_button.setCursor(Qt.CursorShape.PointingHandCursor)
        open_button.clicked.connect(self._open_first_tool)

        check_button = QPushButton("Kiểm tra")
        check_button.setObjectName("heroGhostButton")
        check_button.setCursor(Qt.CursorShape.PointingHandCursor)
        check_button.clicked.connect(self._on_check)

        buttons = QHBoxLayout()
        buttons.setContentsMargins(0, 0, 0, 0)
        buttons.setSpacing(10)
        buttons.addWidget(open_button)
        buttons.addWidget(check_button)
        buttons.addStretch()

        inner = QVBoxLayout(hero)
        inner.setContentsMargins(36, 32, 36, 32)
        inner.setSpacing(12)
        inner.addWidget(eyebrow)
        inner.addWidget(title)
        inner.addWidget(body)
        inner.addSpacing(8)
        inner.addWidget(status)
        inner.addSpacing(8)
        inner.addLayout(buttons)
        return hero

    def _build_feature_grid(self) -> QWidget:
        wrap = QWidget()
        grid = QGridLayout(wrap)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(12)

        cards = (
            ("Sẵn sàng", "Đổi tên & copy file", "Quét folder nguồn, đặt tên F00001, F00002... rồi copy sang folder đích."),
            ("Sẵn sàng", "Đọc CCCD hàng loạt", "Ưu tiên QR, không có QR hợp lệ thì OCR offline và xuất Excel."),
            ("Sắp triển khai", "Excel & báo cáo", "Đọc và tạo file .xlsx phục vụ thống kê, danh sách, biên bản."),
            ("Sắp triển khai", "QR trong ảnh", "Tạo QR, đọc QR và tìm vị trí mã QR trong một tấm ảnh."),
        )
        for index, (badge, title, text) in enumerate(cards):
            grid.addWidget(self._feature_card(badge, title, text), index // 2, index % 2)
        return wrap

    def _feature_card(self, badge: str, title: str, text: str) -> QFrame:
        card = QFrame()
        card.setObjectName("featureCard")

        badge_label = QLabel(badge)
        badge_label.setObjectName("readyBadge" if badge == "Sẵn sàng" else "soonBadge")

        title_label = QLabel(title)
        title_label.setObjectName("featureTitle")

        text_label = QLabel(text)
        text_label.setObjectName("featureText")
        text_label.setWordWrap(True)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(8)
        layout.addWidget(badge_label, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(title_label)
        layout.addWidget(text_label)
        layout.addStretch()
        return card

    def _open_first_tool(self) -> None:
        if self._on_open_first_tool:
            self._on_open_first_tool()

    def _on_check(self) -> None:
        QMessageBox.information(
            self,
            APP_NAME,
            "Ứng dụng hoạt động bình thường.\nBộ công cụ IL-SUNG TECH sẵn sàng hỗ trợ công việc hành chính.",
        )
