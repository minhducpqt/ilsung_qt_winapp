from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import QObject, Signal

from app.features.cccd_pairing.services.matcher import build_pairing_result
from app.features.cccd_pairing.services.pipeline import run_pass1
from app.services.cccd_ocr_reader import load_ocr_engine

logger = logging.getLogger(__name__)


class CCCDPairingWorker(QObject):
    image_processed = Signal(object, int, int)
    progress_changed = Signal(int, int)
    current_file_changed = Signal(str)
    stats_changed = Signal(object)
    status_changed = Signal(str)
    batch_ready = Signal(object)
    finished = Signal(bool)

    def __init__(self, files: list[str], parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.files = [str(path) for path in files]
        self.cancel_requested = False

    def request_cancel(self) -> None:
        self.cancel_requested = True

    def run(self) -> None:
        cancelled = False
        images = []
        try:
            self.status_changed.emit("Đang khởi tạo OCR...")
            engine = load_ocr_engine()
            total = len(self.files)

            def on_image(result, processed, all_count):
                self.current_file_changed.emit(result.file_name)
                self.image_processed.emit(result, processed, all_count)
                self.progress_changed.emit(processed, all_count)
                paired = build_pairing_result(images)
                paired.stats.total = all_count
                paired.stats.processed = processed
                self.stats_changed.emit(paired.stats)
                self.batch_ready.emit(paired)
                self.status_changed.emit(f"Đang phân tích: {processed} / {all_count}")

            def should_cancel():
                return self.cancel_requested

            for path in self.files:
                if self.cancel_requested:
                    cancelled = True
                    break
                name = Path(path).name
                self.current_file_changed.emit(name)
                self.status_changed.emit(f"Đang xử lý: {name}")
                batch = run_pass1([path], engine=engine, should_cancel=should_cancel)
                if not batch:
                    continue
                images.extend(batch)
                on_image(batch[0], len(images), total)

            self.status_changed.emit("Đang ghép mặt trước / mặt sau...")
            result = build_pairing_result(images)
            result.stats.total = total
            result.stats.processed = len(images)
            self.stats_changed.emit(result.stats)
            self.batch_ready.emit(result)
        except Exception as error:
            logger.info("pairing worker failed")
            self.status_changed.emit(f"Lỗi: {error.__class__.__name__}")
        finally:
            if cancelled:
                self.status_changed.emit(f"Đã dừng ở {len(images)}/{len(self.files)} ảnh")
            elif self.files:
                self.status_changed.emit(f"Hoàn thành {len(images)}/{len(self.files)} ảnh")
            self.finished.emit(cancelled)
