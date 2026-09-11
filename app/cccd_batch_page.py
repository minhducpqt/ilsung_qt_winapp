from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSize, Qt, QThread, QTimer, Signal
from PySide6.QtGui import QColor, QMouseEvent, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QButtonGroup,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QStyle,
    QStyledItemDelegate,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.config import APP_NAME
from app.models.cccd_result import (
    SOURCE_MANUAL,
    SOURCE_NONE,
    STATUS_CERTAIN,
    STATUS_LABELS,
    STATUS_NEED_REVIEW,
    STATUS_UNRECOGNIZED,
    CCCDResult,
)
from app.services.cccd_draft_store import load_cccd_draft, save_cccd_draft
from app.services.excel_exporter import export_cccd_results
from app.workers.cccd_batch_worker import CCCDBatchWorker

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
MODE_IMAGE = "image"
MODE_NAME = "name"
THUMB_W = 220
THUMB_H = 132
ROW_H_IMAGE = 144
ROW_H_SHEET = 28
COL_STT = 0
COL_IMAGE = 1
COL_NAME = 2
COL_SOURCE = 12
COL_STATUS = 13
COL_NOTE = 14
COL_GENDER = 7
EDITABLE_COLUMNS = {3, 4, 5, 6, 7, 8, 9, 10, 11, 13, 14}
FIELD_BY_COLUMN = {
    3: "personal_id",
    4: "old_id",
    5: "full_name",
    6: "date_of_birth",
    7: "gender",
    8: "address",
    9: "issue_date",
    10: "father_name",
    11: "mother_name",
    14: "note",
}
COLUMN_WIDTHS = {
    0: 48,
    1: 240,
    2: 168,
    3: 128,
    4: 118,
    5: 180,
    6: 100,
    7: 88,
    8: 260,
    9: 100,
    10: 150,
    11: 150,
    12: 78,
    13: 128,
    14: 180,
}
TABLE_HEADERS = [
    "STT",
    "Ảnh",
    "Tên ảnh",
    "Số CCCD",
    "Số CMND cũ",
    "Họ và tên",
    "Ngày sinh",
    "Giới tính",
    "Nơi cư trú",
    "Ngày cấp",
    "Họ tên cha",
    "Họ tên mẹ",
    "Nguồn",
    "Kết quả",
    "Ghi chú",
]
STATUS_COLORS = {
    STATUS_CERTAIN: QColor(220, 252, 231),
    STATUS_NEED_REVIEW: QColor(254, 243, 199),
    STATUS_UNRECOGNIZED: QColor(254, 226, 226),
}
STATUS_BY_LABEL = {label: key for key, label in STATUS_LABELS.items()}
GENDER_CHOICES = ["", "Nam", "Nữ"]
LOCKED_BG = QColor(243, 244, 246)


def list_image_files(folder: Path) -> list[Path]:
    files = [
        path
        for path in folder.iterdir()
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
    ]
    files.sort(key=lambda item: item.name.casefold())
    return files


def _clean_text(value: str | None) -> str | None:
    text = (value or "").strip()
    return text or None


class ComboDelegate(QStyledItemDelegate):
    def __init__(self, items: list[str], editable: bool = False, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._items = items
        self._editable = editable

    def createEditor(self, parent, _option, _index) -> QComboBox:
        combo = QComboBox(parent)
        combo.addItems(self._items)
        combo.setEditable(self._editable)
        combo.setFrame(False)
        return combo

    def setEditorData(self, editor: QComboBox, index) -> None:  # type: ignore[override]
        text = str(index.data() or "")
        found = editor.findText(text)
        if found >= 0:
            editor.setCurrentIndex(found)
        elif editor.isEditable():
            editor.setCurrentText(text)

    def setModelData(self, editor: QComboBox, model, index) -> None:  # type: ignore[override]
        model.setData(index, editor.currentText(), Qt.ItemDataRole.EditRole)


class ClickableThumb(QLabel):
    clicked = Signal()
    double_clicked = Signal()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.double_clicked.emit()
        super().mouseDoubleClickEvent(event)


class ImagePreviewDialog(QDialog):
    def __init__(self, result: CCCDResult, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(result.file_name)
        self.resize(900, 680)
        image_label = QLabel()
        image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pixmap = QPixmap(result.file_path)
        if pixmap.isNull():
            image_label.setText("Không mở được ảnh")
        else:
            image_label.setPixmap(
                pixmap.scaled(
                    860,
                    620,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
        layout = QVBoxLayout(self)
        layout.addWidget(image_label, 1)


class ResultSheet(QTableWidget):
    """Spreadsheet-like grid: click a cell and type, Tab/Enter move like Excel."""

    def keyPressEvent(self, event) -> None:
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if self.state() != QAbstractItemView.State.EditingState:
                row, column = self.currentRow(), self.currentColumn()
                if row + 1 < self.rowCount():
                    self.setCurrentCell(row + 1, column)
                event.accept()
                return
        super().keyPressEvent(event)


class CCCDBatchPage(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("page")
        self.folder: Path | None = None
        self.image_files: list[Path] = []
        self.results: list[CCCDResult] = []
        self._result_by_path: dict[str, CCCDResult] = {}
        self._user_touched: set[str] = set()
        self._mode = MODE_IMAGE
        self._thumb_index = 0
        self._suspend_table = False
        self._thread: QThread | None = None
        self._worker: CCCDBatchWorker | None = None
        self._autosave_timer = QTimer(self)
        self._autosave_timer.setSingleShot(True)
        self._autosave_timer.setInterval(700)
        self._autosave_timer.timeout.connect(self.flush_autosave)

        title = QLabel("Đọc CCCD hàng loạt")
        title.setObjectName("pageTitle")
        subtitle = QLabel(
            "Bảng kết quả giống Excel: bấm vào ô và sửa trực tiếp. Ảnh nằm trên từng dòng. Bản nháp tự lưu tạm."
        )
        subtitle.setObjectName("pageSubtitle")
        subtitle.setWordWrap(True)

        self.folder_label = QLabel("Chưa chọn thư mục")
        self.folder_label.setObjectName("pathLabel")
        self.folder_label.setWordWrap(True)

        self.total_label = QLabel("Tổng ảnh: 0")
        self.processed_label = QLabel("Đã xử lý: 0")
        self.certain_label = QLabel("Chắc chắn: 0")
        self.review_label = QLabel("Cần check lại: 0")
        self.unrecognized_label = QLabel("Không thể nhận dạng: 0")
        for label in (
            self.total_label,
            self.processed_label,
            self.certain_label,
            self.review_label,
            self.unrecognized_label,
        ):
            label.setObjectName("statLabel")

        self.choose_button = QPushButton("Chọn thư mục")
        self.start_button = QPushButton("Bắt đầu phân tích")
        self.rerun_button = QPushButton()
        self.stop_button = QPushButton("Dừng")
        self.export_button = QPushButton("Xuất Excel")
        self.image_mode_button = QPushButton("Hiện ảnh")
        self.name_mode_button = QPushButton("Chỉ tên file")
        self.start_button.setObjectName("primaryButton")
        self.rerun_button.setObjectName("iconButton")
        self.rerun_button.setToolTip("Phân tích lại toàn bộ")
        self.rerun_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_BrowserReload))
        self.rerun_button.setIconSize(QSize(16, 16))
        self.rerun_button.setFixedSize(36, 36)
        self.stop_button.setObjectName("dangerButton")
        for button in (
            self.choose_button,
            self.export_button,
            self.image_mode_button,
            self.name_mode_button,
        ):
            button.setObjectName("secondaryButton")
        self.stop_button.setEnabled(False)
        self.rerun_button.setEnabled(False)
        self.export_button.setEnabled(False)
        self.image_mode_button.setCheckable(True)
        self.name_mode_button.setCheckable(True)
        self.image_mode_button.setChecked(True)
        self.mode_group = QButtonGroup(self)
        self.mode_group.setExclusive(True)
        self.mode_group.addButton(self.image_mode_button)
        self.mode_group.addButton(self.name_mode_button)
        for button in (
            self.choose_button,
            self.start_button,
            self.rerun_button,
            self.stop_button,
            self.export_button,
            self.image_mode_button,
            self.name_mode_button,
        ):
            button.setCursor(Qt.CursorShape.PointingHandCursor)

        self.choose_button.clicked.connect(self._choose_folder)
        self.start_button.clicked.connect(self._start)
        self.rerun_button.clicked.connect(self._force_start)
        self.stop_button.clicked.connect(self._stop)
        self.export_button.clicked.connect(self._export)
        self.image_mode_button.clicked.connect(lambda: self._set_mode(MODE_IMAGE))
        self.name_mode_button.clicked.connect(lambda: self._set_mode(MODE_NAME))

        self.progress = QProgressBar()
        self.progress.setMinimum(0)
        self.progress.setMaximum(1)
        self.progress.setValue(0)
        self.progress_label = QLabel("0 / 0 - 0%")
        self.progress_label.setObjectName("hintText")
        self.status_label = QLabel("Sẵn sàng. Chọn thư mục, rồi sửa ngay trên bảng.")
        self.status_label.setObjectName("hintText")

        self.table = ResultSheet(0, len(TABLE_HEADERS))
        self.table.setObjectName("resultSheet")
        self.table.setHorizontalHeaderLabels(TABLE_HEADERS)
        self.table.setEditTriggers(
            QAbstractItemView.EditTrigger.DoubleClicked
            | QAbstractItemView.EditTrigger.SelectedClicked
            | QAbstractItemView.EditTrigger.EditKeyPressed
            | QAbstractItemView.EditTrigger.AnyKeyPressed
        )
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectItems)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(True)
        self.table.setTabKeyNavigation(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setWordWrap(False)
        self.table.setCornerButtonEnabled(False)
        header = self.table.horizontalHeader()
        header.setHighlightSections(False)
        header.setSectionsClickable(False)
        header.setStretchLastSection(True)
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        for column, width in COLUMN_WIDTHS.items():
            self.table.setColumnWidth(column, width)
        header.setSectionResizeMode(COL_IMAGE, QHeaderView.ResizeMode.Fixed)
        self.table.setItemDelegateForColumn(COL_GENDER, ComboDelegate(GENDER_CHOICES, editable=True, parent=self.table))
        self.table.setItemDelegateForColumn(
            COL_STATUS, ComboDelegate(list(STATUS_LABELS.values()), editable=False, parent=self.table)
        )
        self.table.itemChanged.connect(self._on_item_changed)
        self.table.cellDoubleClicked.connect(self._on_cell_double_clicked)

        stats = QHBoxLayout()
        for label in (
            self.total_label,
            self.processed_label,
            self.certain_label,
            self.review_label,
            self.unrecognized_label,
        ):
            stats.addWidget(label)
        stats.addStretch()

        buttons = QHBoxLayout()
        buttons.addWidget(self.choose_button)
        buttons.addWidget(self.start_button)
        buttons.addWidget(self.rerun_button)
        buttons.addWidget(self.stop_button)
        buttons.addWidget(self.export_button)
        buttons.addWidget(self.image_mode_button)
        buttons.addWidget(self.name_mode_button)
        buttons.addStretch()

        progress_row = QHBoxLayout()
        progress_row.addWidget(self.progress, 1)
        progress_row.addWidget(self.progress_label)

        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 16, 20, 16)
        card_layout.setSpacing(8)
        card_layout.addWidget(title)
        card_layout.addWidget(subtitle)
        card_layout.addWidget(self.folder_label)
        card_layout.addLayout(stats)
        card_layout.addLayout(buttons)
        card_layout.addLayout(progress_row)
        card_layout.addWidget(self.status_label)
        card_layout.addWidget(self.table, 1)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.addWidget(card)
        self._apply_mode()

    def _set_mode(self, mode: str) -> None:
        self._mode = mode
        self.image_mode_button.setChecked(mode == MODE_IMAGE)
        self.name_mode_button.setChecked(mode == MODE_NAME)
        self._apply_mode()
        if mode == MODE_IMAGE and self.image_files:
            self._thumb_index = 0
            QTimer.singleShot(0, self._load_thumbs_batch)

    def _apply_mode(self) -> None:
        if self._mode == MODE_IMAGE:
            self.table.showColumn(COL_IMAGE)
            self.table.setColumnWidth(COL_IMAGE, COLUMN_WIDTHS[COL_IMAGE])
            for row in range(self.table.rowCount()):
                self.table.setRowHeight(row, ROW_H_IMAGE)
        else:
            self.table.hideColumn(COL_IMAGE)
            for row in range(self.table.rowCount()):
                self.table.setRowHeight(row, ROW_H_SHEET)

    def _choose_folder(self) -> None:
        selected = QFileDialog.getExistingDirectory(self, "Chọn thư mục ảnh CCCD", str(Path.home()))
        if not selected:
            return
        if self.folder is not None and (self.results or self._result_by_path):
            self.flush_autosave()
            confirm = QMessageBox.question(
                self,
                APP_NAME,
                "Đổi thư mục sẽ chuyển sang dữ liệu của thư mục mới. Bản lưu tạm thư mục hiện tại đã được giữ lại. Tiếp tục?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if confirm != QMessageBox.StandardButton.Yes:
                return
        folder = Path(selected)
        files = list_image_files(folder)
        if not files:
            QMessageBox.information(self, APP_NAME, "Thư mục không có ảnh .jpg, .jpeg, .png, .bmp hoặc .webp.")
            return
        self.folder = folder
        self.image_files = files
        self.folder_label.setText(str(folder))
        self._reset_run_state(clear_rows=True)
        self._fill_preview_rows()
        restored = self._restore_draft()
        self.total_label.setText(f"Tổng ảnh: {len(files)}")
        self.rerun_button.setEnabled(True)
        if restored:
            self.status_label.setText(f"Đã tải {len(files)} ảnh và khôi phục {restored} dòng từ bản lưu tạm. Sửa trực tiếp trên bảng.")
        else:
            self.status_label.setText(f"Đã tải {len(files)} ảnh. Bấm ô để sửa, hoặc bắt đầu phân tích.")
        if self.table.rowCount():
            self.table.setCurrentCell(0, 3)

    def _reset_run_state(self, clear_rows: bool = False) -> None:
        self.results = []
        self._result_by_path = {}
        self._user_touched = set()
        self.processed_label.setText("Đã xử lý: 0")
        self.certain_label.setText("Chắc chắn: 0")
        self.review_label.setText("Cần check lại: 0")
        self.unrecognized_label.setText("Không thể nhận dạng: 0")
        self.progress.setMaximum(max(len(self.image_files), 1))
        self.progress.setValue(0)
        self._set_progress_text(0, len(self.image_files))
        self.export_button.setEnabled(False)
        if clear_rows:
            self.table.setRowCount(0)
            self._thumb_index = 0

    def _fill_preview_rows(self) -> None:
        self._suspend_table = True
        self.table.setRowCount(len(self.image_files))
        for row, path in enumerate(self.image_files):
            self._set_cell(row, COL_STT, str(row + 1), center=True)
            self._set_cell(row, COL_NAME, path.name)
            for column in range(3, self.table.columnCount()):
                self._set_cell(row, column, "")
        self._suspend_table = False
        self._apply_mode()
        self._thumb_index = 0
        QTimer.singleShot(0, self._load_thumbs_batch)

    def _restore_draft(self) -> int:
        if self.folder is None:
            return 0
        draft_rows = load_cccd_draft(self.folder)
        if not draft_rows:
            return 0
        by_name = {item.file_name: item for item in draft_rows}
        restored = 0
        for path in self.image_files:
            match = by_name.get(path.name)
            if match is None or not match.has_data():
                continue
            match.file_path = str(path)
            match.file_name = path.name
            self._result_by_path[str(path)] = match
            self._user_touched.add(str(path))
            self._apply_result_to_row(path, match)
            restored += 1
        self._sync_results()
        self._refresh_stats()
        self.export_button.setEnabled(bool(self._result_by_path))
        return restored

    def _load_thumbs_batch(self) -> None:
        if self._mode != MODE_IMAGE or not self.image_files:
            return
        end = min(self._thumb_index + 8, len(self.image_files))
        for row in range(self._thumb_index, end):
            if self.table.cellWidget(row, COL_IMAGE) is None:
                self.table.setCellWidget(row, COL_IMAGE, self._thumb_widget(row, self.image_files[row]))
            self.table.setRowHeight(row, ROW_H_IMAGE)
        self._thumb_index = end
        if end < len(self.image_files):
            QTimer.singleShot(0, self._load_thumbs_batch)

    def _thumb_widget(self, row: int, path: Path) -> ClickableThumb:
        label = ClickableThumb()
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setFixedSize(THUMB_W + 8, THUMB_H + 8)
        label.clicked.connect(lambda: self.table.setCurrentCell(row, 3))
        label.double_clicked.connect(lambda: self._zoom_row(row))
        pixmap = QPixmap(str(path))
        if pixmap.isNull():
            label.setText("—")
            return label
        label.setPixmap(
            pixmap.scaled(
                THUMB_W,
                THUMB_H,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )
        return label

    def _set_cell(self, row: int, column: int, text: str, center: bool = False, color: QColor | None = None) -> None:
        item = self.table.item(row, column)
        if item is None:
            item = QTableWidgetItem(text)
            self.table.setItem(row, column, item)
        else:
            item.setText(text)
        flags = Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
        if column in EDITABLE_COLUMNS:
            flags |= Qt.ItemFlag.ItemIsEditable
        item.setFlags(flags)
        if center or column in {COL_STT, COL_GENDER, COL_SOURCE, COL_STATUS}:
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
        else:
            item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        if color is not None:
            item.setBackground(color)
        elif column in {COL_STT, COL_NAME, COL_SOURCE}:
            item.setBackground(LOCKED_BG)
        elif column != COL_STATUS:
            item.setBackground(QColor(255, 255, 255))

    def _set_progress_text(self, processed: int, total: int) -> None:
        percent = int(processed * 100 / total) if total else 0
        self.progress_label.setText(f"{processed} / {total} - {percent}%")

    def _set_running(self, running: bool) -> None:
        self.choose_button.setEnabled(not running)
        self.start_button.setEnabled(not running)
        self.rerun_button.setEnabled(not running and bool(self.image_files))
        self.stop_button.setEnabled(running)
        self.export_button.setEnabled(self._has_exportable())

    def _has_exportable(self) -> bool:
        return any(result.has_data() for result in self._result_by_path.values())

    def _pending_files(self) -> list[Path]:
        return [path for path in self.image_files if str(path) not in self._user_touched]

    def _force_start(self) -> None:
        self._start(force=True)

    def _start(self, force: bool = False) -> None:
        if self._thread is not None:
            return
        if not self.image_files:
            QMessageBox.information(self, APP_NAME, "Hãy chọn thư mục chứa ảnh trước.")
            return
        if force:
            confirm = QMessageBox.question(
                self,
                APP_NAME,
                "Phân tích lại toàn bộ sẽ ghi đè mọi dòng, kể cả đã sửa tay. Tiếp tục?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if confirm != QMessageBox.StandardButton.Yes:
                return
            self._user_touched.clear()
            pending = list(self.image_files)
        else:
            pending = self._pending_files()
            if not pending:
                QMessageBox.information(
                    self,
                    APP_NAME,
                    "Mọi dòng đã có dữ liệu sửa tay hoặc bản lưu tạm. Dùng nút làm mới để phân tích lại toàn bộ.",
                )
                return
            if self._user_touched:
                confirm = QMessageBox.question(
                    self,
                    APP_NAME,
                    "Phân tích sẽ chạy các ảnh chưa sửa tay. Dòng đã chỉnh trên bảng được giữ nguyên.",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.Yes,
                )
                if confirm != QMessageBox.StandardButton.Yes:
                    return
        self.total_label.setText(f"Tổng ảnh: {len(self.image_files)}")
        self.progress.setMaximum(len(pending))
        self.progress.setValue(0)
        self._set_progress_text(0, len(pending))
        self._set_running(True)

        self._thread = QThread(self)
        self._worker = CCCDBatchWorker([str(path) for path in pending])
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.result_ready.connect(self._on_result)
        self._worker.progress_changed.connect(self._on_progress)
        self._worker.current_file_changed.connect(self._on_current_file)
        self._worker.stats_changed.connect(lambda *_args: self._refresh_stats())
        self._worker.status_changed.connect(self.status_label.setText)
        self._worker.finished.connect(self._on_finished)
        self._worker.finished.connect(self._thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._clear_thread)
        self._thread.start()

    def _stop(self) -> None:
        if self._worker is not None:
            self._worker.request_cancel()
            self.status_label.setText("Đang dừng sau ảnh hiện tại...")

    def _clear_thread(self) -> None:
        self._thread = None
        self._worker = None

    def _on_result(self, result: object) -> None:
        if not isinstance(result, CCCDResult):
            return
        if result.file_path in self._user_touched:
            self._schedule_autosave()
            return
        self._result_by_path[result.file_path] = result
        self._sync_results()
        self._apply_result_to_row(Path(result.file_path), result)
        self.export_button.setEnabled(True)
        self._schedule_autosave()

    def _apply_result_to_row(self, path: Path, result: CCCDResult) -> None:
        row = self._row_for_path(str(path))
        if row is None:
            return
        self._suspend_table = True
        values = result.display_row()
        color = STATUS_COLORS.get(result.status)
        self._set_cell(row, COL_NAME, values[0])
        for offset, value in enumerate(values[1:], start=3):
            self._set_cell(row, offset, value, color=color if offset == COL_STATUS else None)
        self._suspend_table = False

    def _row_for_path(self, file_path: str) -> int | None:
        return next((index for index, path in enumerate(self.image_files) if str(path) == file_path), None)

    def _sync_results(self) -> None:
        self.results = [
            self._result_by_path[str(path)]
            for path in self.image_files
            if str(path) in self._result_by_path
        ]

    def _ensure_result(self, path: Path) -> CCCDResult:
        key = str(path)
        result = self._result_by_path.get(key)
        if result is None:
            result = CCCDResult(file_name=path.name, file_path=key)
            self._result_by_path[key] = result
        return result

    def _on_item_changed(self, item: QTableWidgetItem) -> None:
        if self._suspend_table:
            return
        row, column = item.row(), item.column()
        if not (0 <= row < len(self.image_files)):
            return
        if column not in FIELD_BY_COLUMN and column != COL_STATUS:
            return
        path = self.image_files[row]
        result = self._ensure_result(path)
        text = _clean_text(item.text())
        if column == COL_STATUS:
            result.status = STATUS_BY_LABEL.get(item.text().strip(), result.status)
        else:
            setattr(result, FIELD_BY_COLUMN[column], text)
        if result.source == SOURCE_NONE and result.has_data():
            result.source = SOURCE_MANUAL
        if result.status == STATUS_UNRECOGNIZED and result.personal_id:
            result.status = STATUS_NEED_REVIEW
        result.manual_edit = True
        self._user_touched.add(str(path))
        self._suspend_table = True
        self._set_cell(row, COL_SOURCE, result.source_label())
        self._set_cell(row, COL_STATUS, result.status_label(), color=STATUS_COLORS.get(result.status))
        self._suspend_table = False
        self._sync_results()
        self._refresh_stats()
        self.export_button.setEnabled(True)
        self._schedule_autosave()

    def _on_cell_double_clicked(self, row: int, column: int) -> None:
        if column == COL_IMAGE:
            self._zoom_row(row)

    def _zoom_row(self, row: int) -> None:
        if not (0 <= row < len(self.image_files)):
            return
        path = self.image_files[row]
        ImagePreviewDialog(self._ensure_result(path), self).exec()

    def _on_progress(self, processed: int, total: int) -> None:
        self.progress.setMaximum(max(total, 1))
        self.progress.setValue(processed)
        self._set_progress_text(processed, total)

    def _on_current_file(self, filename: str) -> None:
        if "OCR" in (self.status_label.text() or ""):
            return
        self.status_label.setText(f"Đang xử lý: {filename}")

    def _refresh_stats(self) -> None:
        certain = review = unrecognized = processed = 0
        for path in self.image_files:
            result = self._result_by_path.get(str(path))
            if result is None or not result.has_data():
                continue
            processed += 1
            if result.status == STATUS_CERTAIN:
                certain += 1
            elif result.status == STATUS_NEED_REVIEW:
                review += 1
            else:
                unrecognized += 1
        self.processed_label.setText(f"Đã xử lý: {processed}")
        self.certain_label.setText(f"Chắc chắn: {certain}")
        self.review_label.setText(f"Cần check lại: {review}")
        self.unrecognized_label.setText(f"Không thể nhận dạng: {unrecognized}")

    def _on_finished(self, cancelled: bool) -> None:
        self._set_running(False)
        self._refresh_stats()
        self.flush_autosave()
        total = len(self.image_files)
        processed = len([item for item in self._result_by_path.values() if item.has_data()])
        if cancelled:
            self.status_label.setText(f"Đã dừng ở {processed}/{total} ảnh. Sửa trên bảng — bản nháp đã lưu tạm.")
        else:
            self.status_label.setText(f"Hoàn thành {processed}/{total} ảnh. Bấm vào ô để sửa, bản nháp tự lưu.")
            QMessageBox.information(self, APP_NAME, f"Đã xử lý xong {processed} ảnh")

    def _schedule_autosave(self) -> None:
        self.status_label.setText("Đang lưu tạm...")
        self._autosave_timer.start()

    def flush_autosave(self) -> None:
        self._autosave_timer.stop()
        if self.folder is None:
            return
        self._sync_results()
        if not self.results:
            return
        try:
            save_cccd_draft(self.folder, self.results)
        except OSError as error:
            self.status_label.setText(f"Không lưu tạm được: {error}")
            return
        self.status_label.setText("Đã lưu tạm. Tiếp tục sửa trên bảng hoặc xuất Excel.")

    def _export(self) -> None:
        self.flush_autosave()
        results = [
            self._result_by_path[str(path)]
            for path in self.image_files
            if str(path) in self._result_by_path and self._result_by_path[str(path)].has_data()
        ]
        if not results:
            QMessageBox.information(self, APP_NAME, "Chưa có kết quả để xuất.")
            return
        default = str(Path.home() / "ket_qua_cccd.xlsx")
        selected, _ = QFileDialog.getSaveFileName(self, "Xuất Excel", default, "Excel (*.xlsx)")
        if not selected:
            return
        path = Path(selected)
        if path.suffix.lower() != ".xlsx":
            path = path.with_suffix(".xlsx")
        try:
            export_cccd_results(path, results)
        except OSError as error:
            QMessageBox.warning(self, APP_NAME, f"Không xuất được Excel.\n{error}")
            return
        QMessageBox.information(self, APP_NAME, f"Đã xuất:\n{path}")
