from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.config import (
    APP_VERSION,
    COMPANY_SHORT,
    MENU_GROUPS,
    WINDOW_HEIGHT,
    WINDOW_MIN_HEIGHT,
    WINDOW_MIN_WIDTH,
    WINDOW_TITLE,
    WINDOW_WIDTH,
)
from app.cccd_batch_page import CCCDBatchPage
from app.home_page import HomePage
from app.placeholder_page import PlaceholderPage
from app.settings_page import SettingsPage
from app.tools_page import ToolsPage

PLACEHOLDER_COPY = {
    "sort_files": (
        "Sắp xếp file theo ngày",
        "Sẽ hỗ trợ xếp file hành chính theo ngày tạo hoặc ngày sửa, tiện lưu chứng từ theo lô.",
    ),
    "file_to_excel": (
        "Xuất danh sách file ra Excel",
        "Sẽ xuất bảng tên file, dung lượng, đường dẫn từ một folder ra file .xlsx.",
    ),
    "qr_find": (
        "Tìm QR trong ảnh",
        "Sẽ dò vị trí mã QR trong một tấm ảnh chụp và đọc nội dung mã.",
    ),
    "excel_io": (
        "Đọc / tạo file Excel",
        "Sẽ đọc và tạo file .xlsx phục vụ danh sách nhân sự, biên bản, báo cáo hành chính.",
    ),
    "excel_merge": (
        "Gộp nhiều sheet",
        "Sẽ gộp dữ liệu từ nhiều sheet hoặc nhiều file Excel thành một bảng làm việc.",
    ),
    "qr_create": (
        "Tạo mã QR",
        "Sẽ tạo ảnh QR từ văn bản, link nội bộ hoặc mã chứng từ.",
    ),
    "qr_read": (
        "Đọc mã QR từ ảnh",
        "Sẽ đọc nội dung từ một ảnh QR rõ nét hoặc ảnh chụp có chứa QR.",
    ),
}


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(WINDOW_TITLE)
        self.resize(WINDOW_WIDTH, WINDOW_HEIGHT)
        self.setMinimumSize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)
        self._page_ids: list[str] = []

        central = QWidget()
        central.setObjectName("centralWidget")
        self.setCentralWidget(central)

        self.stack = QStackedWidget()
        self.stack.setObjectName("contentArea")
        self._build_pages()

        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._build_sidebar())
        root.addWidget(self.stack, 1)

    def _build_pages(self) -> None:
        for _group, items in MENU_GROUPS:
            for page_id, _label, _status in items:
                self._page_ids.append(page_id)
                self.stack.addWidget(self._create_page(page_id))

    def _create_page(self, page_id: str) -> QWidget:
        if page_id == "home":
            return HomePage(on_open_page=self._open_page)
        if page_id == "rename_copy":
            return ToolsPage()
        if page_id == "ocr_cccd":
            return CCCDBatchPage()
        if page_id == "settings":
            return SettingsPage()
        title, description = PLACEHOLDER_COPY[page_id]
        return PlaceholderPage(title, description)

    def _open_page(self, page_id: str) -> None:
        index = self._page_ids.index(page_id)
        self.stack.setCurrentIndex(index)
        button = self.nav_group.button(index)
        if button is not None:
            button.setChecked(True)

    def _build_sidebar(self) -> QWidget:
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(252)

        brand = QLabel(COMPANY_SHORT)
        brand.setObjectName("brandTitle")

        brand_sub = QLabel("Công cụ hành chính")
        brand_sub.setObjectName("brandSubtitle")

        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)
        self.nav_group.idClicked.connect(self.stack.setCurrentIndex)

        nav_host = QWidget()
        nav_layout = QVBoxLayout(nav_host)
        nav_layout.setContentsMargins(0, 0, 0, 0)
        nav_layout.setSpacing(4)

        index = 0
        for group_title, items in MENU_GROUPS:
            group_label = QLabel(group_title.upper())
            group_label.setObjectName("navGroupLabel")
            nav_layout.addSpacing(10)
            nav_layout.addWidget(group_label)
            for page_id, label, status in items:
                button = QPushButton(label)
                button.setObjectName("navButtonSoon" if status == "soon" else "navButton")
                button.setCheckable(True)
                button.setCursor(Qt.CursorShape.PointingHandCursor)
                button.setChecked(index == 0)
                self.nav_group.addButton(button, index)
                nav_layout.addWidget(button)
                index += 1

        nav_layout.addStretch()

        scroll = QScrollArea()
        scroll.setObjectName("sidebarScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidget(nav_host)

        footer = QLabel(f"v{APP_VERSION}")
        footer.setObjectName("sidebarFooter")


        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(14, 20, 14, 14)
        layout.setSpacing(4)
        layout.addWidget(brand)
        layout.addWidget(brand_sub)
        layout.addSpacing(8)
        layout.addWidget(scroll, 1)
        layout.addWidget(footer)
        return sidebar

    def closeEvent(self, event) -> None:
        if "ocr_cccd" in self._page_ids:
            page = self.stack.widget(self._page_ids.index("ocr_cccd"))
            flush = getattr(page, "flush_autosave", None)
            if callable(flush):
                flush()
            stop = getattr(page, "_stop", None)
            thread = getattr(page, "_thread", None)
            if callable(stop):
                stop()
            if thread is not None:
                thread.wait(5000)
        event.accept()
