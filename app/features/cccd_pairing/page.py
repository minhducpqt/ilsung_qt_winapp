from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QThread
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.config import APP_NAME
from app.features.cccd_pairing.models import (
    MANUAL_MATCH,
    CCCDPairImageResult,
    CCCDPersonPairRecord,
    PairingBatchResult,
    PairingStats,
)
from app.features.cccd_pairing.services.excel_exporter import export_pairing_xlsx
from app.features.cccd_pairing.services.html_exporter import export_pairing_html
from app.features.cccd_pairing.services.matcher import manual_pair
from app.features.cccd_pairing.worker import CCCDPairingWorker

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
COL_ACTION = 0
COL_STT = 1
EDITABLE_COLUMNS = {2, 3, 4, 5, 6, 7, 8, 9, 10, 15}
FIELD_BY_COLUMN = {
    2: "personal_id",
    3: "old_id",
    4: "full_name",
    5: "date_of_birth",
    6: "gender",
    7: "address",
    8: "issue_date",
    9: "father_name",
    10: "mother_name",
    15: "note",
}
TABLE_HEADERS = [
    "Xem",
    "STT",
    "Số CCCD",
    "Số CMND cũ",
    "Họ và tên",
    "Ngày sinh",
    "Giới tính",
    "Địa chỉ",
    "Ngày cấp",
    "Họ tên cha",
    "Họ tên mẹ",
    "File mặt trước",
    "File mặt sau",
    "Trạng thái nhận dạng",
    "Trạng thái ghép",
    "Ghi chú",
]


def list_image_files(folder: Path) -> list[Path]:
    files = [path for path in folder.iterdir() if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS]
    files.sort(key=lambda item: item.name.casefold())
    return files


class PairPreviewDialog(QDialog):
    def __init__(self, person: CCCDPersonPairRecord, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(person.personal_id or person.front_file_name or "Xem CCCD")
        self.resize(920, 560)
        layout = QVBoxLayout(self)
        info = QLabel(f"{person.full_name or '-'}  •  {person.match_label()}")
        info.setObjectName("hintText")
        images = QHBoxLayout()
        images.addWidget(self._side("Mặt trước", person.front_crop or person.front_file_path, person.front_file_name), 1)
        images.addWidget(self._side("Mặt sau", person.back_crop or person.back_file_path, person.back_file_name), 1)
        layout.addWidget(info)
        layout.addLayout(images, 1)

    def _side(self, title: str, path: str | None, filename: str | None) -> QFrame:
        frame = QFrame()
        box = QVBoxLayout(frame)
        caption = QLabel(f"{title}\n{filename or 'Không có ảnh mặt sau' if 'sau' in title.lower() else 'Không có ảnh'}")
        caption.setWordWrap(True)
        image = QLabel()
        image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if path and Path(path).exists():
            pixmap = QPixmap(path)
            if not pixmap.isNull():
                image.setPixmap(pixmap.scaled(420, 280, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            else:
                image.setText("Không mở được ảnh")
        else:
            image.setText("Không có ảnh mặt sau" if "sau" in title.lower() else "Không có ảnh")
        box.addWidget(caption)
        box.addWidget(image, 1)
        return frame


class OrphanBackDialog(QDialog):
    def __init__(
        self,
        orphans: list[CCCDPairImageResult],
        persons: list[CCCDPersonPairRecord],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Mặt sau chưa ghép")
        self.resize(720, 480)
        self.orphans = orphans
        self.persons = persons
        self.paired: tuple[CCCDPersonPairRecord, CCCDPairImageResult] | None = None

        self.back_list = QListWidget()
        for item in orphans:
            row = QListWidgetItem(f"{item.file_name}  •  {item.personal_id or 'chưa có số'}  •  {item.suggested_id or ''}")
            row.setData(Qt.ItemDataRole.UserRole, item)
            self.back_list.addItem(row)
        self.person_list = QListWidget()
        for person in persons:
            row = QListWidgetItem(f"{person.personal_id or '-'}  •  {person.full_name or person.front_file_name}")
            row.setData(Qt.ItemDataRole.UserRole, person)
            self.person_list.addItem(row)

        self.preview = QLabel("Chọn một mặt sau để xem")
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview.setMinimumHeight(180)
        self.back_list.currentItemChanged.connect(self._show_back)

        pair_button = QPushButton("Ghép thủ công")
        pair_button.setObjectName("primaryButton")
        pair_button.clicked.connect(self._pair)
        close_button = QPushButton("Đóng")
        close_button.setObjectName("secondaryButton")
        close_button.clicked.connect(self.reject)

        lists = QHBoxLayout()
        left = QVBoxLayout()
        left.addWidget(QLabel("Mặt sau chưa ghép"))
        left.addWidget(self.back_list, 1)
        right = QVBoxLayout()
        right.addWidget(QLabel("Hồ sơ mặt trước"))
        right.addWidget(self.person_list, 1)
        lists.addLayout(left, 1)
        lists.addLayout(right, 1)

        buttons = QHBoxLayout()
        buttons.addWidget(pair_button)
        buttons.addWidget(close_button)
        buttons.addStretch()

        layout = QVBoxLayout(self)
        layout.addLayout(lists, 1)
        layout.addWidget(self.preview)
        layout.addLayout(buttons)

    def _show_back(self, current: QListWidgetItem | None, _previous=None) -> None:
        if current is None:
            return
        item = current.data(Qt.ItemDataRole.UserRole)
        path = item.crop_path or item.file_path
        pixmap = QPixmap(path)
        if pixmap.isNull():
            self.preview.setText(item.note or item.file_name)
            return
        self.preview.setPixmap(pixmap.scaled(360, 200, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))

    def _pair(self) -> None:
        back_item = self.back_list.currentItem()
        person_item = self.person_list.currentItem()
        if back_item is None or person_item is None:
            QMessageBox.information(self, APP_NAME, "Hãy chọn một mặt sau và một hồ sơ mặt trước.")
            return
        self.paired = (person_item.data(Qt.ItemDataRole.UserRole), back_item.data(Qt.ItemDataRole.UserRole))
        self.accept()


class CCCDPairingPage(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("page")
        self.folder: Path | None = None
        self.image_files: list[Path] = []
        self.batch = PairingBatchResult()
        self._suspend_table = False
        self._thread: QThread | None = None
        self._worker: CCCDPairingWorker | None = None

        title = QLabel("Ghép CCCD 2 mặt")
        title.setObjectName("pageTitle")
        subtitle = QLabel(
            "Nhận diện mặt trước/mặt sau, ghép theo số CCCD 12 số, sửa trên bảng, xuất Excel (dữ liệu) và HTML (in A4)."
        )
        subtitle.setObjectName("pageSubtitle")
        subtitle.setWordWrap(True)

        self.folder_label = QLabel("Chưa chọn thư mục")
        self.folder_label.setObjectName("pathLabel")
        self.folder_label.setWordWrap(True)

        self.stat_labels = {
            "total": QLabel("Tổng ảnh: 0"),
            "processed": QLabel("Đã xử lý: 0"),
            "front": QLabel("Mặt trước: 0"),
            "back": QLabel("Mặt sau: 0"),
            "unknown": QLabel("Không xác định: 0"),
            "paired": QLabel("Đã ghép: 0"),
            "front_only": QLabel("Chỉ mặt trước: 0"),
            "orphan": QLabel("Mặt sau chưa ghép: 0"),
            "duplicate": QLabel("Duplicate: 0"),
        }
        for label in self.stat_labels.values():
            label.setObjectName("statLabel")

        self.choose_button = QPushButton("Chọn thư mục")
        self.start_button = QPushButton("Phân tích")
        self.stop_button = QPushButton("Dừng")
        self.export_xlsx_button = QPushButton("Xuất Excel")
        self.export_html_button = QPushButton("Xuất HTML")
        self.orphan_button = QPushButton("Mặt sau chưa ghép")
        self.start_button.setObjectName("primaryButton")
        self.stop_button.setObjectName("dangerButton")
        for button in (self.choose_button, self.export_xlsx_button, self.export_html_button, self.orphan_button):
            button.setObjectName("secondaryButton")
        self.stop_button.setEnabled(False)
        self.export_xlsx_button.setEnabled(False)
        self.export_html_button.setEnabled(False)
        self.orphan_button.setEnabled(False)
        for button in (
            self.choose_button,
            self.start_button,
            self.stop_button,
            self.export_xlsx_button,
            self.export_html_button,
            self.orphan_button,
        ):
            button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.choose_button.clicked.connect(self._choose_folder)
        self.start_button.clicked.connect(self._start)
        self.stop_button.clicked.connect(self._stop)
        self.export_xlsx_button.clicked.connect(self._export_xlsx)
        self.export_html_button.clicked.connect(self._export_html)
        self.orphan_button.clicked.connect(self._open_orphans)

        self.progress = QProgressBar()
        self.progress.setValue(0)
        self.progress_label = QLabel("0 / 0 - 0%")
        self.progress_label.setObjectName("hintText")
        self.status_label = QLabel("Sẵn sàng. Chọn thư mục ảnh CCCD mặt trước/mặt sau.")
        self.status_label.setObjectName("hintText")

        self.table = QTableWidget(0, len(TABLE_HEADERS))
        self.table.setObjectName("resultSheet")
        self.table.setHorizontalHeaderLabels(TABLE_HEADERS)
        self.table.setEditTriggers(
            QAbstractItemView.EditTrigger.DoubleClicked
            | QAbstractItemView.EditTrigger.SelectedClicked
            | QAbstractItemView.EditTrigger.EditKeyPressed
            | QAbstractItemView.EditTrigger.AnyKeyPressed
        )
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectItems)
        self.table.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(32)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(True)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setStretchLastSection(True)
        header.setSectionResizeMode(COL_ACTION, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(COL_ACTION, 64)
        self.table.setColumnWidth(4, 180)
        self.table.setColumnWidth(7, 240)
        self.table.itemChanged.connect(self._on_item_changed)

        stats = QHBoxLayout()
        for label in self.stat_labels.values():
            stats.addWidget(label)
        stats.addStretch()
        buttons = QHBoxLayout()
        for button in (
            self.choose_button,
            self.start_button,
            self.stop_button,
            self.export_xlsx_button,
            self.export_html_button,
            self.orphan_button,
        ):
            buttons.addWidget(button)
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

    def _choose_folder(self) -> None:
        selected = QFileDialog.getExistingDirectory(self, "Chọn thư mục ảnh CCCD", str(Path.home()))
        if not selected:
            return
        folder = Path(selected)
        files = list_image_files(folder)
        if not files:
            QMessageBox.information(self, APP_NAME, "Thư mục không có ảnh .jpg, .jpeg, .png, .bmp hoặc .webp.")
            return
        self.folder = folder
        self.image_files = files
        self.folder_label.setText(str(folder))
        self.batch = PairingBatchResult()
        self.table.setRowCount(0)
        self._set_stats(PairingStats(total=len(files)))
        self.progress.setMaximum(len(files))
        self.progress.setValue(0)
        self.progress_label.setText(f"0 / {len(files)} - 0%")
        self.status_label.setText(f"Đã tải {len(files)} ảnh. Bấm Phân tích.")
        self.export_xlsx_button.setEnabled(False)
        self.export_html_button.setEnabled(False)
        self.orphan_button.setEnabled(False)

    def _set_running(self, running: bool) -> None:
        self.choose_button.setEnabled(not running)
        self.start_button.setEnabled(not running)
        self.stop_button.setEnabled(running)
        has_rows = bool(self.batch.persons)
        self.export_xlsx_button.setEnabled(has_rows and not running)
        self.export_html_button.setEnabled(has_rows and not running)
        self.orphan_button.setEnabled(bool(self.batch.orphan_backs) and not running)

    def _start(self) -> None:
        if self._thread is not None:
            return
        if not self.image_files:
            QMessageBox.information(self, APP_NAME, "Hãy chọn thư mục chứa ảnh trước.")
            return
        self.batch = PairingBatchResult()
        self.table.setRowCount(0)
        self.progress.setMaximum(len(self.image_files))
        self.progress.setValue(0)
        self._set_running(True)
        self._thread = QThread(self)
        self._worker = CCCDPairingWorker([str(path) for path in self.image_files])
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.progress_changed.connect(self._on_progress)
        self._worker.current_file_changed.connect(lambda name: self.status_label.setText(f"Đang xử lý: {name}"))
        self._worker.stats_changed.connect(self._set_stats)
        self._worker.status_changed.connect(self.status_label.setText)
        self._worker.batch_ready.connect(self._on_batch)
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

    def _on_progress(self, processed: int, total: int) -> None:
        self.progress.setMaximum(max(total, 1))
        self.progress.setValue(processed)
        percent = int(processed * 100 / total) if total else 0
        self.progress_label.setText(f"{processed} / {total} - {percent}%")

    def _set_stats(self, stats: object) -> None:
        if not isinstance(stats, PairingStats):
            return
        mapping = {
            "total": f"Tổng ảnh: {stats.total}",
            "processed": f"Đã xử lý: {stats.processed}",
            "front": f"Mặt trước: {stats.front}",
            "back": f"Mặt sau: {stats.back}",
            "unknown": f"Không xác định: {stats.unknown}",
            "paired": f"Đã ghép: {stats.paired}",
            "front_only": f"Chỉ mặt trước: {stats.front_only}",
            "orphan": f"Mặt sau chưa ghép: {stats.orphan_back}",
            "duplicate": f"Duplicate: {stats.duplicate}",
        }
        for key, text in mapping.items():
            self.stat_labels[key].setText(text)

    def _on_batch(self, batch: object) -> None:
        if not isinstance(batch, PairingBatchResult):
            return
        self._merge_user_edits(batch)
        self.batch = batch
        self._reload_table()
        running = self._thread is not None
        self.export_xlsx_button.setEnabled(bool(batch.persons) and not running)
        self.export_html_button.setEnabled(bool(batch.persons) and not running)
        self.orphan_button.setEnabled(bool(batch.orphan_backs) and not running)

    def _merge_user_edits(self, incoming: PairingBatchResult) -> None:
        previous = {
            person.front_file_path: person
            for person in self.batch.persons
            if person.user_edited and person.front_file_path
        }
        if not previous:
            return
        for person in incoming.persons:
            old = previous.get(person.front_file_path or "")
            if old is None:
                continue
            for field in FIELD_BY_COLUMN.values():
                setattr(person, field, getattr(old, field))
            person.user_edited = True
            if old.match_status == MANUAL_MATCH:
                person.back_file_name = old.back_file_name
                person.back_file_path = old.back_file_path
                person.back_crop = old.back_crop
                person.back_recognition_status = old.back_recognition_status
                person.match_status = old.match_status
                person.note = old.note

    def _reload_table(self) -> None:
        v_pos = self.table.verticalScrollBar().value()
        h_pos = self.table.horizontalScrollBar().value()
        self._suspend_table = True
        self.table.setRowCount(len(self.batch.persons))
        for row, person in enumerate(self.batch.persons):
            self.table.setCellWidget(row, COL_ACTION, self._preview_button(row))
            self._set_cell(row, COL_STT, str(row + 1), editable=False)
            for offset, value in enumerate(person.display_row(), start=2):
                self._set_cell(row, offset, value, editable=offset in EDITABLE_COLUMNS)
        self._suspend_table = False
        self.table.verticalScrollBar().setValue(v_pos)
        self.table.horizontalScrollBar().setValue(h_pos)

    def _preview_button(self, row: int) -> QWidget:
        button = QPushButton("Xem")
        button.setObjectName("iconButton")
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setFixedSize(52, 24)
        button.clicked.connect(lambda _checked=False, index=row: self._preview_row(index))
        host = QWidget()
        box = QHBoxLayout(host)
        box.setContentsMargins(4, 2, 4, 2)
        box.setAlignment(Qt.AlignmentFlag.AlignCenter)
        box.addWidget(button)
        return host

    def _set_cell(self, row: int, column: int, text: str, editable: bool) -> None:
        item = QTableWidgetItem(text)
        flags = Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
        if editable:
            flags |= Qt.ItemFlag.ItemIsEditable
        item.setFlags(flags)
        self.table.setItem(row, column, item)

    def _on_item_changed(self, item: QTableWidgetItem) -> None:
        if self._suspend_table:
            return
        row, column = item.row(), item.column()
        if column not in FIELD_BY_COLUMN or not (0 <= row < len(self.batch.persons)):
            return
        person = self.batch.persons[row]
        value = item.text().strip() or None
        setattr(person, FIELD_BY_COLUMN[column], value)
        person.user_edited = True

    def _preview_row(self, row: int) -> None:
        if 0 <= row < len(self.batch.persons):
            PairPreviewDialog(self.batch.persons[row], self).exec()

    def _open_orphans(self) -> None:
        if not self.batch.orphan_backs:
            QMessageBox.information(self, APP_NAME, "Không còn mặt sau chưa ghép.")
            return
        dialog = OrphanBackDialog(self.batch.orphan_backs, self.batch.persons, self)
        if dialog.exec() != QDialog.DialogCode.Accepted or dialog.paired is None:
            return
        person, back = dialog.paired
        manual_pair(person, back)
        self.batch.orphan_backs = [item for item in self.batch.orphan_backs if item is not back]
        self.batch.stats.orphan_back = len(self.batch.orphan_backs)
        self.batch.stats.paired = sum(1 for item in self.batch.persons if item.back_file_name)
        self._set_stats(self.batch.stats)
        self._reload_table()
        self.orphan_button.setEnabled(bool(self.batch.orphan_backs))

    def _on_finished(self, cancelled: bool) -> None:
        self._set_running(False)
        total = len(self.image_files)
        processed = self.batch.stats.processed
        if cancelled:
            self.status_label.setText(f"Đã dừng ở {processed}/{total} ảnh. Kết quả đã làm vẫn giữ.")
        else:
            self.status_label.setText(f"Hoàn thành {processed}/{total} ảnh. Có thể sửa bảng, xuất Excel hoặc HTML.")
            QMessageBox.information(self, APP_NAME, f"Đã xử lý xong {processed} ảnh, {len(self.batch.persons)} hồ sơ.")

    def _export_xlsx(self) -> None:
        if not self.batch.persons:
            QMessageBox.information(self, APP_NAME, "Chưa có hồ sơ để xuất.")
            return
        default = str(Path.home() / "ket_qua_cccd_2_mat.xlsx")
        selected, _ = QFileDialog.getSaveFileName(self, "Xuất Excel", default, "Excel (*.xlsx)")
        if not selected:
            return
        path = Path(selected)
        if path.suffix.lower() != ".xlsx":
            path = path.with_suffix(".xlsx")
        try:
            export_pairing_xlsx(path, self.batch.persons)
        except OSError as error:
            QMessageBox.warning(self, APP_NAME, f"Không xuất được Excel.\n{error}")
            return
        QMessageBox.information(self, APP_NAME, f"Đã xuất dữ liệu:\n{path}")

    def _export_html(self) -> None:
        if not self.batch.persons:
            QMessageBox.information(self, APP_NAME, "Chưa có hồ sơ để xuất.")
            return
        default = str(Path.home() / "in_cccd_2_mat.html")
        selected, _ = QFileDialog.getSaveFileName(self, "Xuất HTML in CCCD", default, "HTML (*.html)")
        if not selected:
            return
        path = Path(selected)
        if path.suffix.lower() != ".html":
            path = path.with_suffix(".html")
        try:
            export_pairing_html(path, self.batch.persons)
        except OSError as error:
            QMessageBox.warning(self, APP_NAME, f"Không xuất được HTML.\n{error}")
            return
        QMessageBox.information(self, APP_NAME, f"Đã xuất bản in A4:\n{path}")
