from __future__ import annotations

import logging

from PySide6.QtCore import QObject, Signal

from app.features.cccd_pairing.services.matcher import build_pairing_result, draft_batch_from_images
from app.features.cccd_pairing.services.pipeline import pairing_worker_count, run_pass1_parallel

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
            workers = pairing_worker_count(len(self.files))
            self.status_changed.emit(f"Đang phân tích song song ({workers} process)...")
            total = len(self.files)

            def on_image(result, processed, all_count, results):
                self.current_file_changed.emit(result.file_name)
                self.image_processed.emit(result, processed, all_count)
                self.progress_changed.emit(processed, all_count)
                draft = draft_batch_from_images(results, total=all_count)
                self.stats_changed.emit(draft.stats)
                self.batch_ready.emit(draft)
                self.status_changed.emit(f"Đang phân tích: {processed} / {all_count}  •  {workers} process")

            images = run_pass1_parallel(
                self.files,
                should_cancel=lambda: self.cancel_requested,
                on_image=on_image,
                workers=workers,
            )
            cancelled = self.cancel_requested and len(images) < total

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
