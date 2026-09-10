from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.config import APP_NAME, APP_VERSION, WINDOW_HEIGHT, WINDOW_MIN_HEIGHT, WINDOW_MIN_WIDTH, WINDOW_TITLE, WINDOW_WIDTH


class HomePage(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("page")

        title = QLabel(APP_NAME)
        title.setObjectName("pageTitle")

        subtitle = QLabel("Python + PySide6")
        subtitle.setObjectName("pageSubtitle")

        status_dot = QLabel("●")
        status_dot.setObjectName("statusText")

        status_text = QLabel("Ứng dụng đang hoạt động")
        status_text.setObjectName("statusText")

        status_row = QHBoxLayout()
        status_row.setContentsMargins(0, 0, 0, 0)
        status_row.setSpacing(8)
        status_row.addWidget(status_dot)
        status_row.addWidget(status_text)
        status_row.addStretch()

        check_button = QPushButton("Kiểm tra")
        check_button.setObjectName("primaryButton")
        check_button.setCursor(Qt.CursorShape.PointingHandCursor)
        check_button.clicked.connect(self._on_check)

        card_layout = QVBoxLayout()
        card_layout.setContentsMargins(32, 32, 32, 32)
        card_layout.setSpacing(12)
        card_layout.addWidget(title)
        card_layout.addWidget(subtitle)
        card_layout.addSpacing(8)
        card_layout.addLayout(status_row)
        card_layout.addSpacing(12)
        card_layout.addWidget(check_button, alignment=Qt.AlignmentFlag.AlignLeft)
        card_layout.addStretch()

        card = QFrame()
        card.setObjectName("card")
        card.setLayout(card_layout)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(0)
        layout.addWidget(card)

    def _on_check(self) -> None:
        QMessageBox.information(
            self,
            APP_NAME,
            "Ứng dụng hoạt động bình thường",
        )


class PlaceholderPage(QWidget):
    def __init__(self, title: str, description: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("page")

        title_label = QLabel(title)
        title_label.setObjectName("placeholderTitle")

        description_label = QLabel(description)
        description_label.setObjectName("placeholderText")
        description_label.setWordWrap(True)

        card_layout = QVBoxLayout()
        card_layout.setContentsMargins(32, 32, 32, 32)
        card_layout.setSpacing(10)
        card_layout.addWidget(title_label)
        card_layout.addWidget(description_label)
        card_layout.addStretch()

        card = QFrame()
        card.setObjectName("card")
        card.setLayout(card_layout)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.addWidget(card)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(WINDOW_TITLE)
        self.resize(WINDOW_WIDTH, WINDOW_HEIGHT)
        self.setMinimumSize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)

        central = QWidget()
        central.setObjectName("centralWidget")
        self.setCentralWidget(central)

        self.stack = QStackedWidget()
        self.stack.setObjectName("contentArea")
        self.stack.addWidget(HomePage())
        self.stack.addWidget(
            PlaceholderPage("Công cụ", "Trang công cụ sẽ được bổ sung ở các phiên bản sau.")
        )
        self.stack.addWidget(
            PlaceholderPage("Cài đặt", "Trang cài đặt sẽ được bổ sung ở các phiên bản sau.")
        )

        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._build_sidebar())
        root.addWidget(self.stack, 1)

    def _build_sidebar(self) -> QWidget:
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(220)

        brand = QLabel(APP_NAME)
        brand.setObjectName("brandTitle")

        brand_sub = QLabel("Desktop App")
        brand_sub.setObjectName("brandSubtitle")

        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)
        self.nav_group.idClicked.connect(self.stack.setCurrentIndex)

        nav_layout = QVBoxLayout()
        nav_layout.setContentsMargins(0, 0, 0, 0)
        nav_layout.setSpacing(6)

        for index, label in enumerate(("Trang chủ", "Công cụ", "Cài đặt")):
            button = QPushButton(label)
            button.setObjectName("navButton")
            button.setCheckable(True)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setChecked(index == 0)
            self.nav_group.addButton(button, index)
            nav_layout.addWidget(button)

        footer = QLabel(f"v{APP_VERSION}")
        footer.setObjectName("sidebarFooter")

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(16, 24, 16, 16)
        layout.setSpacing(4)
        layout.addWidget(brand)
        layout.addWidget(brand_sub)
        layout.addSpacing(20)
        layout.addLayout(nav_layout)
        layout.addStretch()
        layout.addWidget(footer)
        return sidebar
