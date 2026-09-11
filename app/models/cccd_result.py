from __future__ import annotations

from dataclasses import dataclass

SOURCE_QR = "QR"
SOURCE_OCR = "OCR"
SOURCE_NONE = "NONE"

STATUS_CERTAIN = "CERTAIN"
STATUS_NEED_REVIEW = "NEED_REVIEW"
STATUS_UNRECOGNIZED = "UNRECOGNIZED"

STATUS_LABELS = {
    STATUS_CERTAIN: "Chắc chắn",
    STATUS_NEED_REVIEW: "Cần check lại",
    STATUS_UNRECOGNIZED: "Không thể nhận dạng",
}

SOURCE_LABELS = {
    SOURCE_QR: "QR",
    SOURCE_OCR: "OCR",
    SOURCE_NONE: "-",
}


@dataclass
class CCCDResult:
    file_name: str
    file_path: str
    personal_id: str | None = None
    old_id: str | None = None
    full_name: str | None = None
    date_of_birth: str | None = None
    gender: str | None = None
    address: str | None = None
    issue_date: str | None = None
    cancelled_personal_id: str | None = None
    father_name: str | None = None
    mother_name: str | None = None
    source: str = SOURCE_NONE
    status: str = STATUS_UNRECOGNIZED
    note: str | None = None
    raw_qr: str | None = None
    ocr_confidence: float | None = None

    def status_label(self) -> str:
        return STATUS_LABELS.get(self.status, self.status)

    def source_label(self) -> str:
        return SOURCE_LABELS.get(self.source, self.source)

    def display_row(self) -> list[str]:
        return [
            self.file_name,
            self.personal_id or "",
            self.old_id or "",
            self.full_name or "",
            self.date_of_birth or "",
            self.gender or "",
            self.address or "",
            self.issue_date or "",
            self.father_name or "",
            self.mother_name or "",
            self.source_label(),
            self.status_label(),
            self.note or "",
        ]
