from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QDir, Qt
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFileSystemModel,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QProgressDialog,
    QPushButton,
    QSplitter,
    QTreeView,
    QVBoxLayout,
    QWidget,
)

from app.config import APP_NAME
from app.file_ops import copy_renamed_files, is_same_or_inside, preview_renames, scan_files


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

        self.file_list = QListWidget()
        self.file_list.setObjectName("fileList")

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
        layout.addWidget(self.file_list, 1)
        layout.addWidget(self.scan_status)
        return card

    def _build_dest_panel(self) -> QFrame:
        card = QFrame()
        card.setObjectName("card")

        heading = QLabel("Cây thư mục máy tính")
        heading.setObjectName("sectionTitle")

        create_button = QPushButton("Tạo folder")
        create_button.setObjectName("secondaryButton")
        create_button.setCursor(Qt.CursorShape.PointingHandCursor)
        create_button.clicked.connect(self._create_folder)

        delete_button = QPushButton("Xóa folder")
        delete_button.setObjectName("dangerButton")
        delete_button.setCursor(Qt.CursorShape.PointingHandCursor)
        delete_button.clicked.connect(self._delete_folder)

        new_dest_button = QPushButton("Tạo folder đích mới")
        new_dest_button.setObjectName("secondaryButton")
        new_dest_button.setCursor(Qt.CursorShape.PointingHandCursor)
        new_dest_button.clicked.connect(self._create_destination_folder)

        set_dest_button = QPushButton("Chọn làm folder đích")
        set_dest_button.setObjectName("secondaryButton")
        set_dest_button.setCursor(Qt.CursorShape.PointingHandCursor)
        set_dest_button.clicked.connect(self._set_selected_as_destination)

        self.fs_model = QFileSystemModel(self)
        self.fs_model.setFilter(QDir.Filter.AllDirs | QDir.Filter.NoDotAndDotDot)
        root_path = QDir.rootPath()
        self.fs_model.setRootPath(root_path)

        self.tree = QTreeView()
        self.tree.setObjectName("folderTree")
        self.tree.setModel(self.fs_model)
        self.tree.setRootIndex(self.fs_model.index(root_path))
        self.tree.setHeaderHidden(True)
        self.tree.setAnimated(True)
        for column in range(1, self.fs_model.columnCount()):
            self.tree.hideColumn(column)

        home_index = self.fs_model.index(str(Path.home()))
        if home_index.isValid():
            self.tree.setCurrentIndex(home_index)
            self.tree.scrollTo(home_index)

        self.dest_path_label = QLabel("Chưa chọn folder đích")
        self.dest_path_label.setObjectName("pathLabel")
        self.dest_path_label.setWordWrap(True)

        buttons = QHBoxLayout()
        buttons.setContentsMargins(0, 0, 0, 0)
        buttons.setSpacing(8)
        buttons.addWidget(create_button)
        buttons.addWidget(delete_button)
        buttons.addStretch()

        dest_buttons = QHBoxLayout()
        dest_buttons.setContentsMargins(0, 0, 0, 0)
        dest_buttons.setSpacing(8)
        dest_buttons.addWidget(new_dest_button)
        dest_buttons.addWidget(set_dest_button)
        dest_buttons.addStretch()

        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)
        layout.addWidget(heading)
        layout.addLayout(buttons)
        layout.addWidget(self.tree, 1)
        layout.addLayout(dest_buttons)
        layout.addWidget(self.dest_path_label)
        return card

    def _selected_tree_dir(self) -> Path | None:
        index = self.tree.currentIndex()
        if not index.isValid():
            return None
        path = Path(self.fs_model.filePath(index))
        return path if path.is_dir() else None

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

        self.file_list.clear()
        for original, new_name in preview_renames(self.scanned_files):
            relative = original.relative_to(self.source_dir)
            item = QListWidgetItem(f"{relative}  →  {new_name}")
            self.file_list.addItem(item)
        self.scan_status.setText(f"Đã quét {len(self.scanned_files)} file")

    def _create_folder(self) -> None:
        parent = self._selected_tree_dir() or Path.home()
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
        self._focus_tree_path(target)

    def _create_destination_folder(self) -> None:
        parent = self._selected_tree_dir() or Path.home()
        name, accepted = QInputDialog.getText(
            self,
            "Tạo folder đích mới",
            f"Tên folder đích trong:\n{parent}",
        )
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
            QMessageBox.warning(self, APP_NAME, f"Không tạo được folder đích.\n{error}")
            return
        self._set_destination(target)
        self._focus_tree_path(target)

    def _delete_folder(self) -> None:
        target = self._selected_tree_dir()
        if target is None:
            QMessageBox.information(self, APP_NAME, "Hãy chọn folder cần xóa.")
            return
        if target.resolve() in {Path.home().resolve(), Path(QDir.rootPath()).resolve()}:
            QMessageBox.warning(self, APP_NAME, "Không xóa folder hệ thống này.")
            return
        if self.source_dir and target.resolve() == self.source_dir.resolve():
            QMessageBox.warning(self, APP_NAME, "Không xóa folder nguồn đang chọn.")
            return

        confirm = QMessageBox.question(
            self,
            APP_NAME,
            f"Xóa folder này và toàn bộ nội dung?\n{target}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        if not QDir(str(target)).removeRecursively():
            QMessageBox.warning(self, APP_NAME, f"Không xóa được folder.\n{target}")
            return
        if self.dest_dir and self.dest_dir.resolve() == target.resolve():
            self.dest_dir = None
            self.dest_path_label.setText("Chưa chọn folder đích")

    def _set_selected_as_destination(self) -> None:
        target = self._selected_tree_dir()
        if target is None:
            QMessageBox.information(self, APP_NAME, "Hãy chọn một folder trên cây thư mục.")
            return
        self._set_destination(target)

    def _set_destination(self, target: Path) -> None:
        self.dest_dir = target
        self.dest_path_label.setText(f"Folder đích: {target}")

    def _focus_tree_path(self, path: Path) -> None:
        index = self.fs_model.index(str(path))
        if index.isValid():
            self.tree.setCurrentIndex(index)
            self.tree.scrollTo(index)

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
            QMessageBox.warning(self, APP_NAME, f"Copy thất bại.\n{error}")
            return
        progress.close()

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
