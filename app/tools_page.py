from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QMessageBox,
    QProgressDialog,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.config import APP_NAME
from app.file_ops import copy_renamed_files, is_same_or_inside, preview_renames, scan_files


def _format_size(size: int) -> str:
    value = float(size)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            if unit == "B":
                return f"{int(value)} {unit}"
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{size} B"


def _make_file_table(headers: list[str]) -> QTableWidget:
    table = QTableWidget(0, len(headers))
    table.setObjectName("fileTable")
    table.setHorizontalHeaderLabels(headers)
    table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
    table.setAlternatingRowColors(True)
    table.setShowGrid(True)
    table.verticalHeader().setVisible(False)
    table.setWordWrap(False)
    header = table.horizontalHeader()
    header.setHighlightSections(False)
    header.setStretchLastSection(False)
    header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
    if len(headers) > 1:
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
    return table


def _set_table_text(table: QTableWidget, row: int, column: int, text: str, align=None) -> None:
    item = QTableWidgetItem(text)
    if align is not None:
        item.setTextAlignment(align)
    table.setItem(row, column, item)


class ToolsPage(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("page")
        self.source_dir: Path | None = None
        self.dest_dir: Path | None = None
        self.scanned_files: list[Path] = []

        title = QLabel("Đổi tên và copy file")
        title.setObjectName("pageTitle")

        subtitle = QLabel(
            "Quét toàn bộ file trong folder nguồn, đổi tên lần lượt F00001, F00002... rồi copy sang folder đích."
        )
        subtitle.setObjectName("pageSubtitle")
        subtitle.setWordWrap(True)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self._build_source_panel())
        splitter.addWidget(self._build_dest_panel())
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        splitter.setChildrenCollapsible(False)

        copy_button = QPushButton("Copy và đổi tên sang folder đích")
        copy_button.setObjectName("primaryButton")
        copy_button.setCursor(Qt.CursorShape.PointingHandCursor)
        copy_button.clicked.connect(self._copy_renamed)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(splitter, 1)
        layout.addWidget(copy_button, alignment=Qt.AlignmentFlag.AlignLeft)

    def _build_source_panel(self) -> QFrame:
        card = QFrame()
        card.setObjectName("card")

        heading = QLabel("Folder nguồn")
        heading.setObjectName("sectionTitle")

        choose_button = QPushButton("Chọn folder nguồn")
        choose_button.setObjectName("secondaryButton")
        choose_button.setCursor(Qt.CursorShape.PointingHandCursor)
        choose_button.clicked.connect(self._choose_source)

        rescan_button = QPushButton("Quét lại")
        rescan_button.setObjectName("secondaryButton")
        rescan_button.setCursor(Qt.CursorShape.PointingHandCursor)
        rescan_button.clicked.connect(self._rescan_source)

        self.source_path_label = QLabel("Chưa chọn folder nguồn")
        self.source_path_label.setObjectName("pathLabel")
        self.source_path_label.setWordWrap(True)

        self.source_table = _make_file_table(["STT", "Tên file", "Thư mục con", "Tên mới", "Dung lượng"])

        self.scan_status = QLabel("Chưa quét file")
        self.scan_status.setObjectName("hintText")

        buttons = QHBoxLayout()
        buttons.setContentsMargins(0, 0, 0, 0)
        buttons.setSpacing(8)
        buttons.addWidget(choose_button)
        buttons.addWidget(rescan_button)
        buttons.addStretch()

        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)
        layout.addWidget(heading)
        layout.addLayout(buttons)
        layout.addWidget(self.source_path_label)
        layout.addWidget(self.source_table, 1)
        layout.addWidget(self.scan_status)
        return card

    def _build_dest_panel(self) -> QFrame:
        card = QFrame()
        card.setObjectName("card")

        heading = QLabel("Folder đích")
        heading.setObjectName("sectionTitle")

        choose_button = QPushButton("Chọn folder đích")
        choose_button.setObjectName("secondaryButton")
        choose_button.setCursor(Qt.CursorShape.PointingHandCursor)
        choose_button.clicked.connect(self._choose_destination)

        create_button = QPushButton("Tạo folder")
        create_button.setObjectName("secondaryButton")
        create_button.setCursor(Qt.CursorShape.PointingHandCursor)
        create_button.clicked.connect(self._create_folder)

        self.dest_path_label = QLabel("Chưa chọn folder đích")
        self.dest_path_label.setObjectName("pathLabel")
        self.dest_path_label.setWordWrap(True)

        self.dest_table = _make_file_table(["STT", "Tên file", "Thư mục con", "Dung lượng"])

        self.dest_status = QLabel("Chưa chọn folder đích")
        self.dest_status.setObjectName("hintText")

        buttons = QHBoxLayout()
        buttons.setContentsMargins(0, 0, 0, 0)
        buttons.setSpacing(8)
        buttons.addWidget(choose_button)
        buttons.addWidget(create_button)
        buttons.addStretch()

        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)
        layout.addWidget(heading)
        layout.addLayout(buttons)
        layout.addWidget(self.dest_path_label)
        layout.addWidget(self.dest_table, 1)
        layout.addWidget(self.dest_status)
        return card

    def _choose_source(self) -> None:
        selected = QFileDialog.getExistingDirectory(self, "Chọn folder nguồn", str(Path.home()))
        if not selected:
            return
        self.source_dir = Path(selected)
        self.source_path_label.setText(str(self.source_dir))
        self._rescan_source()

    def _rescan_source(self) -> None:
        if self.source_dir is None:
            QMessageBox.information(self, APP_NAME, "Hãy chọn folder nguồn trước.")
            return
        try:
            self.scanned_files = scan_files(self.source_dir)
        except OSError as error:
            QMessageBox.warning(self, APP_NAME, f"Không quét được folder nguồn.\n{error}")
            return

        self.source_table.setRowCount(len(self.scanned_files))
        for row, (original, new_name) in enumerate(preview_renames(self.scanned_files)):
            relative = original.relative_to(self.source_dir)
            folder = str(relative.parent) if relative.parent != Path(".") else "—"
            _set_table_text(self.source_table, row, 0, str(row + 1), Qt.AlignmentFlag.AlignCenter)
            _set_table_text(self.source_table, row, 1, original.name)
            _set_table_text(self.source_table, row, 2, folder)
            _set_table_text(self.source_table, row, 3, new_name)
            _set_table_text(
                self.source_table,
                row,
                4,
                _format_size(original.stat().st_size),
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
            )
        self.source_table.resizeRowsToContents()
        self.scan_status.setText(f"Đã quét {len(self.scanned_files)} file")

    def _choose_destination(self) -> None:
        start = str(self.dest_dir or Path.home())
        selected = QFileDialog.getExistingDirectory(self, "Chọn folder đích", start)
        if not selected:
            return
        self._set_destination(Path(selected))

    def _create_folder(self) -> None:
        start = str(self.dest_dir or Path.home())
        parent_selected = QFileDialog.getExistingDirectory(self, "Chọn nơi tạo folder mới", start)
        if not parent_selected:
            return
        parent = Path(parent_selected)
        name, accepted = QInputDialog.getText(self, "Tạo folder", f"Tên folder mới trong:\n{parent}")
        if not accepted:
            return
        folder_name = name.strip()
        if not folder_name or any(sep in folder_name for sep in ("/", "\\")):
            QMessageBox.warning(self, APP_NAME, "Tên folder không hợp lệ.")
            return
        target = parent / folder_name
        try:
            target.mkdir(parents=False, exist_ok=False)
        except OSError as error:
            QMessageBox.warning(self, APP_NAME, f"Không tạo được folder.\n{error}")
            return
        self._set_destination(target)
        QMessageBox.information(self, APP_NAME, f"Đã tạo và chọn folder đích:\n{target}")

    def _set_destination(self, target: Path) -> None:
        self.dest_dir = target
        self.dest_path_label.setText(f"Folder đích: {target}")
        self._refresh_dest_files()

    def _refresh_dest_files(self) -> None:
        if self.dest_dir is None:
            self.dest_table.setRowCount(0)
            self.dest_status.setText("Chưa chọn folder đích")
            return
        try:
            files = scan_files(self.dest_dir)
        except OSError as error:
            self.dest_table.setRowCount(0)
            self.dest_status.setText(f"Không đọc được folder đích: {error}")
            return

        self.dest_table.setRowCount(len(files))
        for row, path in enumerate(files):
            relative = path.relative_to(self.dest_dir)
            folder = str(relative.parent) if relative.parent != Path(".") else "—"
            _set_table_text(self.dest_table, row, 0, str(row + 1), Qt.AlignmentFlag.AlignCenter)
            _set_table_text(self.dest_table, row, 1, path.name)
            _set_table_text(self.dest_table, row, 2, folder)
            _set_table_text(
                self.dest_table,
                row,
                3,
                _format_size(path.stat().st_size),
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
            )
        self.dest_table.resizeRowsToContents()
        self.dest_status.setText(f"Folder đích đang có {len(files)} file")

    def _copy_renamed(self) -> None:
        if self.source_dir is None:
            QMessageBox.information(self, APP_NAME, "Hãy chọn folder nguồn.")
            return
        if self.dest_dir is None:
            QMessageBox.information(self, APP_NAME, "Hãy chọn hoặc tạo folder đích.")
            return
        if not self.scanned_files:
            self._rescan_source()
        if not self.scanned_files:
            QMessageBox.information(self, APP_NAME, "Folder nguồn không có file để copy.")
            return

        source = self.source_dir.resolve()
        dest = self.dest_dir.resolve()
        if dest == source or is_same_or_inside(dest, source):
            QMessageBox.warning(
                self,
                APP_NAME,
                "Folder đích không được trùng hoặc nằm trong folder nguồn.",
            )
            return

        confirm = QMessageBox.question(
            self,
            APP_NAME,
            (
                f"Copy {len(self.scanned_files)} file từ:\n{source}\n\n"
                f"sang:\n{dest}\n\n"
                "Tên mới: F00001, F00002, ..."
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        progress = QProgressDialog("Đang copy file...", "Hủy", 0, len(self.scanned_files), self)
        progress.setWindowTitle(APP_NAME)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)

        def on_progress(value: int) -> None:
            progress.setValue(value)
            QApplication.processEvents()

        try:
            copied = copy_renamed_files(
                self.scanned_files,
                dest,
                progress=on_progress,
                should_cancel=progress.wasCanceled,
            )
        except OSError as error:
            progress.close()
            self._refresh_dest_files()
            QMessageBox.warning(self, APP_NAME, f"Copy thất bại.\n{error}")
            return
        progress.close()

        self._refresh_dest_files()

        if progress.wasCanceled():
            QMessageBox.information(
                self,
                APP_NAME,
                f"Đã dừng. Copy được {len(copied)}/{len(self.scanned_files)} file sang:\n{dest}",
            )
            return

        QMessageBox.information(
            self,
            APP_NAME,
            f"Đã copy {len(copied)} file sang:\n{dest}",
        )
