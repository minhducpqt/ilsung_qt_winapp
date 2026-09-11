from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QThread
from PySide6.QtGui import QColor, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.config import APP_NAME
from app.models.cccd_result import (
    STATUS_CERTAIN,
    STATUS_NEED_REVIEW,
    STATUS_UNRECOGNIZED,
    CCCDResult,
)
from app.services.excel_exporter import export_cccd_results
from app.workers.cccd_batch_worker import CCCDBatchWorker

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
TABLE_HEADERS = [
    "STT",
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


def list_image_files(folder: Path) -> list[Path]:
    files = [
        path
        for path in folder.iterdir()
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
    ]
    files.sort(key=lambda item: item.name.casefold())
    return files


class ImagePreviewDialog(QDialog):
    def __init__(self, result: CCCDResult, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(result.file_name)
        self.resize(720, 560)

        image_label = QLabel()
        image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pixmap = QPixmap(result.file_path)
        if not pixmap.isNull():
            image_label.setPixmap(
                pixmap.scaled(680, 360, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            )
        else:
            image_label.setText("Không mở được ảnh")

        info = QLabel(
            f"{result.file_name}\n"
            f"Số CCCD: {result.personal_id or '-'}\n"
            f"Họ và tên: {result.full_name or '-'}\n"
            f"Nguồn: {result.source_label()}  |  Kết quả: {result.status_label()}\n"
            f"{result.note or ''}"
        )
        info.setWordWrap(True)
        info.setObjectName("placeholderText")

        layout = QVBoxLayout(self)
        layout.addWidget(image_label, 1)
        layout.addWidget(info)


class CCCDBatchPage(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("page")
        self.folder: Path | None = None
        self.image_files: list[Path] = []
        self.results: list[CCCDResult] = []
        self._thread: QThread | None = None
        self._worker: CCCDBatchWorker | None = None

        title = QLabel("Đọc CCCD hàng loạt")
        title.setObjectName("pageTitle")
        subtitle = QLabel("Ưu tiên đọc QR trên ảnh căn cước. Không có QR hợp lệ thì OCR offline. Cập nhật từng ảnh.")
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
        self.stop_button = QPushButton("Dừng")
        self.export_button = QPushButton("Xuất Excel")
        self.start_button.setObjectName("primaryButton")
        self.stop_button.setObjectName("dangerButton")
        self.choose_button.setObjectName("secondaryButton")
        self.export_button.setObjectName("secondaryButton")
        self.stop_button.setEnabled(False)
        self.export_button.setEnabled(False)
        for button in (self.choose_button, self.start_button, self.stop_button, self.export_button):
            button.setCursor(Qt.CursorShape.PointingHandCursor)

        self.choose_button.clicked.connect(self._choose_folder)
        self.start_button.clicked.connect(self._start)
        self.stop_button.clicked.connect(self._stop)
        self.export_button.clicked.connect(self._export)

        self.progress = QProgressBar()
        self.progress.setMinimum(0)
        self.progress.setMaximum(1)
        self.progress.setValue(0)
        self.progress_label = QLabel("0 / 0 - 0%")
        self.progress_label.setObjectName("hintText")
        self.status_label = QLabel("Sẵn sàng")
        self.status_label.setObjectName("hintText")

        self.table = QTableWidget(0, len(TABLE_HEADERS))
        self.table.setObjectName("fileTable")
        self.table.setHorizontalHeaderLabels(TABLE_HEADERS)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setWordWrap(False)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setStretchLastSection(True)
        self.table.cellDoubleClicked.connect(self._preview_row)

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
        buttons.addWidget(self.stop_button)
        buttons.addWidget(self.export_button)
        buttons.addStretch()

        progress_row = QHBoxLayout()
        progress_row.addWidget(self.progress, 1)
        progress_row.addWidget(self.progress_label)

        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 20, 20, 20)
        card_layout.setSpacing(10)
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

    def _choose_folder(self) -> None:
        selected = QFileDialog.getExistingDirectory(self, "Chọn thư mục ảnh CCCD", str(Path.home()))
        if not selected:
            return
        if self.results:
            confirm = QMessageBox.question(
                self,
                APP_NAME,
                "Chọn thư mục mới sẽ xóa bảng kết quả hiện tại. Tiếp tục?",
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
        self._reset_results()
        self.total_label.setText(f"Tổng ảnh: {len(files)}")
        self.status_label.setText("Sẵn sàng")

    def _reset_results(self) -> None:
        self.results = []
        self.table.setRowCount(0)
        self.processed_label.setText("Đã xử lý: 0")
        self.certain_label.setText("Chắc chắn: 0")
        self.review_label.setText("Cần check lại: 0")
        self.unrecognized_label.setText("Không thể nhận dạng: 0")
        self.progress.setMaximum(max(len(self.image_files), 1))
        self.progress.setValue(0)
        self._set_progress_text(0, len(self.image_files))
        self.export_button.setEnabled(False)

    def _set_progress_text(self, processed: int, total: int) -> None:
        percent = int(processed * 100 / total) if total else 0
        self.progress_label.setText(f"{processed} / {total} - {percent}%")

    def _set_running(self, running: bool) -> None:
        self.choose_button.setEnabled(not running)
        self.start_button.setEnabled(not running)
        self.stop_button.setEnabled(running)
        self.export_button.setEnabled(bool(self.results))

    def _start(self) -> None:
        if self._thread is not None:
            return
        if not self.image_files:
            QMessageBox.information(self, APP_NAME, "Hãy chọn thư mục chứa ảnh trước.")
            return
        self._reset_results()
        self.total_label.setText(f"Tổng ảnh: {len(self.image_files)}")
        self.progress.setMaximum(len(self.image_files))
        self._set_running(True)

        self._thread = QThread(self)
        self._worker = CCCDBatchWorker([str(path) for path in self.image_files])
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.result_ready.connect(self._on_result)
        self._worker.progress_changed.connect(self._on_progress)
        self._worker.current_file_changed.connect(self._on_current_file)
        self._worker.stats_changed.connect(self._on_stats)
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
        self.results.append(result)
        row = self.table.rowCount()
        self.table.insertRow(row)
        values = [str(row + 1), *result.display_row()]
        color = STATUS_COLORS.get(result.status)
        for column, value in enumerate(values):
            item = QTableWidgetItem(value)
            if column == 0:
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if color is not None and column == 12:
                item.setBackground(color)
            self.table.setItem(row, column, item)
        self.table.scrollToBottom()
        self.export_button.setEnabled(True)

    def _on_progress(self, processed: int, total: int) -> None:
        self.progress.setMaximum(max(total, 1))
        self.progress.setValue(processed)
        self._set_progress_text(processed, total)

    def _on_current_file(self, filename: str) -> None:
        if "OCR" in (self.status_label.text() or ""):
            return
        self.status_label.setText(f"Đang xử lý: {filename}")

    def _on_stats(self, processed: int, certain: int, review: int, unrecognized: int) -> None:
        self.processed_label.setText(f"Đã xử lý: {processed}")
        self.certain_label.setText(f"Chắc chắn: {certain}")
        self.review_label.setText(f"Cần check lại: {review}")
        self.unrecognized_label.setText(f"Không thể nhận dạng: {unrecognized}")

    def _on_finished(self, cancelled: bool) -> None:
        self._set_running(False)
        total = len(self.image_files)
        processed = len(self.results)
        if cancelled:
            self.status_label.setText(f"Đã dừng ở {processed}/{total} ảnh")
        else:
            self.status_label.setText(f"Hoàn thành {processed}/{total} ảnh")
            QMessageBox.information(self, APP_NAME, f"Đã xử lý xong {processed} ảnh")

    def _preview_row(self, row: int, _column: int) -> None:
        if 0 <= row < len(self.results):
            ImagePreviewDialog(self.results[row], self).exec()

    def _export(self) -> None:
        if not self.results:
            QMessageBox.information(self, APP_NAME, "Chưa có kết quả để xuất.")
            return
        default = str(Path.home() / "ket_qua_cccd.xlsx")
        selected, _ = QFileDialog.getSaveFileName(
            self,
            "Xuất Excel",
            default,
            "Excel (*.xlsx)",
        )
        if not selected:
            return
        path = Path(selected)
        if path.suffix.lower() != ".xlsx":
            path = path.with_suffix(".xlsx")
        try:
            export_cccd_results(path, self.results)
        except OSError as error:
            QMessageBox.warning(self, APP_NAME, f"Không xuất được Excel.\n{error}")
            return
        QMessageBox.information(self, APP_NAME, f"Đã xuất:\n{path}")
