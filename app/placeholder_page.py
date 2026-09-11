from __future__ import annotations

from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget


class PlaceholderPage(QWidget):
    def __init__(self, title: str, description: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("page")

        badge = QLabel("Đang phát triển")
        badge.setObjectName("soonBadge")

        title_label = QLabel(title)
        title_label.setObjectName("placeholderTitle")

        description_label = QLabel(description)
        description_label.setObjectName("placeholderText")
        description_label.setWordWrap(True)

        hint = QLabel("Đầu mục đã được bố trí trên menu. Thư viện hỗ trợ đã được chuẩn bị trong môi trường dự án.")
        hint.setObjectName("hintText")
        hint.setWordWrap(True)

        card_layout = QVBoxLayout()
        card_layout.setContentsMargins(32, 32, 32, 32)
        card_layout.setSpacing(10)
        card_layout.addWidget(badge)
        card_layout.addWidget(title_label)
        card_layout.addWidget(description_label)
        card_layout.addSpacing(8)
        card_layout.addWidget(hint)
        card_layout.addStretch()

        card = QFrame()
        card.setObjectName("card")
        card.setLayout(card_layout)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.addWidget(card)
