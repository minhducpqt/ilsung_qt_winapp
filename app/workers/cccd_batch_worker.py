from __future__ import annotations

import logging
from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, wait
from multiprocessing import get_context
from pathlib import Path

from PySide6.QtCore import QObject, Signal

from app.models.cccd_result import (
    STATUS_CERTAIN,
    STATUS_NEED_REVIEW,
    STATUS_UNRECOGNIZED,
    CCCDResult,
)
from app.services.cccd_processor import (
    CCCDProcessor,
    analyze_image_path,
    batch_worker_count,
    init_batch_process_engine,
)

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
        workers = batch_worker_count(total)

        try:
            if workers <= 1:
                processed, certain, review, unrecognized, cancelled = self._run_sequential(total)
            else:
                processed, certain, review, unrecognized, cancelled = self._run_parallel(total, workers)
        except Exception as error:
            self.error.emit(str(error))
        finally:
            if cancelled:
                self.status_changed.emit(f"Đã dừng ở {processed}/{total} ảnh")
            elif total:
                self.status_changed.emit(f"Hoàn thành {processed}/{total} ảnh")
            self.finished.emit(cancelled)

    def _emit_result(self, result: CCCDResult, processed: int, total: int, certain: int, review: int, unrecognized: int) -> None:
        self.current_file_changed.emit(result.file_name)
        self.result_ready.emit(result)
        self.progress_changed.emit(processed, total)
        self.stats_changed.emit(processed, certain, review, unrecognized)

    def _count_status(self, result: CCCDResult, certain: int, review: int, unrecognized: int) -> tuple[int, int, int]:
        if result.status == STATUS_CERTAIN:
            return certain + 1, review, unrecognized
        if result.status == STATUS_NEED_REVIEW:
            return certain, review + 1, unrecognized
        return certain, review, unrecognized + 1

    def _failed_result(self, file_path: str) -> CCCDResult:
        return CCCDResult(
            file_name=Path(file_path).name,
            file_path=file_path,
            note="Không đọc được file ảnh",
        )

    def _run_sequential(self, total: int) -> tuple[int, int, int, int, bool]:
        processed = certain = review = unrecognized = 0
        self.status_changed.emit("Đang khởi tạo OCR...")
        processor = CCCDProcessor()
        processor.ensure_ocr_ready()
        for file_path in self.files:
            if self.cancel_requested:
                return processed, certain, review, unrecognized, True
            name = Path(file_path).name
            self.current_file_changed.emit(name)
            self.status_changed.emit(f"Đang xử lý: {name}")
            try:
                result = processor.process_image(file_path, status=self.status_changed.emit)
            except Exception as error:
                logger.info("RESULT UNRECOGNIZED")
                result = self._failed_result(file_path)
                self.error.emit(str(error.__class__.__name__))
            processed += 1
            certain, review, unrecognized = self._count_status(result, certain, review, unrecognized)
            self._emit_result(result, processed, total, certain, review, unrecognized)
        return processed, certain, review, unrecognized, False

    def _run_parallel(self, total: int, workers: int) -> tuple[int, int, int, int, bool]:
        processed = certain = review = unrecognized = 0
        self.status_changed.emit(f"Đang phân tích song song ({workers} process)...")
        try:
            ctx = get_context("spawn")
            with ProcessPoolExecutor(
                max_workers=workers,
                mp_context=ctx,
                initializer=init_batch_process_engine,
            ) as pool:
                pending = {pool.submit(analyze_image_path, path): path for path in self.files}
                while pending:
                    if self.cancel_requested:
                        for future in pending:
                            future.cancel()
                        running = [future for future in pending if not future.cancelled()]
                        if running:
                            wait(running)
                        for future, path in list(pending.items()):
                            pending.pop(future)
                            if future.cancelled():
                                continue
                            result = self._future_result(future, path)
                            processed += 1
                            certain, review, unrecognized = self._count_status(result, certain, review, unrecognized)
                            self._emit_result(result, processed, total, certain, review, unrecognized)
                            self.status_changed.emit(f"Đang phân tích: {processed} / {total}  •  {workers} process")
                        return processed, certain, review, unrecognized, True
                    done, _still = wait(list(pending), timeout=0.25, return_when=FIRST_COMPLETED)
                    for future in done:
                        path = pending.pop(future)
                        if future.cancelled():
                            continue
                        result = self._future_result(future, path)
                        processed += 1
                        certain, review, unrecognized = self._count_status(result, certain, review, unrecognized)
                        self._emit_result(result, processed, total, certain, review, unrecognized)
                        self.status_changed.emit(f"Đang phân tích: {processed} / {total}  •  {workers} process")
        except Exception:
            logger.info("cccd batch pool fallback sequential")
            return self._run_sequential(total)
        return processed, certain, review, unrecognized, False

    def _future_result(self, future, path: str) -> CCCDResult:
        try:
            return future.result()
        except Exception as error:
            logger.info("RESULT UNRECOGNIZED")
            self.error.emit(str(error.__class__.__name__))
            return self._failed_result(path)
