from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import QObject, Signal

from app.models.cccd_result import (
    STATUS_CERTAIN,
    STATUS_NEED_REVIEW,
    STATUS_UNRECOGNIZED,
    CCCDResult,
)
from app.services.cccd_processor import CCCDProcessor

logger = logging.getLogger(__name__)


class CCCDBatchWorker(QObject):
    result_ready = Signal(object)
    progress_changed = Signal(int, int)
    current_file_changed = Signal(str)
    stats_changed = Signal(int, int, int, int)
    status_changed = Signal(str)
    finished = Signal(bool)
    error = Signal(str)

    def __init__(self, files: list[str], parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.files = [str(path) for path in files]
        self.cancel_requested = False

    def request_cancel(self) -> None:
        self.cancel_requested = True

    def run(self) -> None:
        total = len(self.files)
        processed = 0
        certain = 0
        review = 0
        unrecognized = 0
        cancelled = False

        try:
            self.status_changed.emit("Đang khởi tạo OCR...")
            processor = CCCDProcessor()
            processor.ensure_ocr_ready()

            for file_path in self.files:
                if self.cancel_requested:
                    cancelled = True
                    break

                name = Path(file_path).name
                self.current_file_changed.emit(name)
                self.status_changed.emit(f"Đang xử lý: {name}")

                try:
                    result = processor.process_image(
                        file_path,
                        status=self.status_changed.emit,
                    )
                except Exception as error:
                    logger.info("RESULT UNRECOGNIZED")
                    result = CCCDResult(
                        file_name=name,
                        file_path=file_path,
                        note=f"Không đọc được file ảnh",
                    )
                    self.error.emit(str(error.__class__.__name__))

                processed += 1
                if result.status == STATUS_CERTAIN:
                    certain += 1
                elif result.status == STATUS_NEED_REVIEW:
                    review += 1
                else:
                    unrecognized += 1

                self.result_ready.emit(result)
                self.progress_changed.emit(processed, total)
                self.stats_changed.emit(processed, certain, review, unrecognized)
        except Exception as error:
            self.error.emit(str(error))
        finally:
            if cancelled:
                self.status_changed.emit(f"Đã dừng ở {processed}/{total} ảnh")
            elif total:
                self.status_changed.emit(f"Hoàn thành {processed}/{total} ảnh")
            self.finished.emit(cancelled)
