from __future__ import annotations

from dataclasses import dataclass, field

SIDE_FRONT = "FRONT"
SIDE_BACK = "BACK"
SIDE_UNKNOWN = "UNKNOWN"

SOURCE_QR = "QR"
SOURCE_MRZ_EXACT = "MRZ_EXACT"
SOURCE_MRZ = "MRZ"
SOURCE_OCR = "OCR"
SOURCE_NONE = "NONE"

STATUS_CERTAIN = "CERTAIN"
STATUS_NEED_REVIEW = "NEED_REVIEW"
STATUS_UNRECOGNIZED = "UNRECOGNIZED"

MATCH_CERTAIN = "MATCH_CERTAIN"
FRONT_ONLY = "FRONT_ONLY"
NEED_REVIEW = "NEED_REVIEW"
MANUAL_MATCH = "MANUAL_MATCH"
DUPLICATE = "DUPLICATE"

STATUS_LABELS = {
    STATUS_CERTAIN: "Chắc chắn",
    STATUS_NEED_REVIEW: "Cần check lại",
    STATUS_UNRECOGNIZED: "Không thể nhận dạng",
}

MATCH_LABELS = {
    MATCH_CERTAIN: "Đã ghép",
    FRONT_ONLY: "Chỉ mặt trước",
    NEED_REVIEW: "Cần check lại",
    MANUAL_MATCH: "Ghép thủ công",
    DUPLICATE: "Duplicate",
}

SIDE_LABELS = {
    SIDE_FRONT: "Mặt trước",
    SIDE_BACK: "Mặt sau",
    SIDE_UNKNOWN: "Không xác định",
}


@dataclass
class CCCDPairImageResult:
    file_name: str
    file_path: str
    side: str = SIDE_UNKNOWN
    side_confidence: float = 0.0
    personal_id: str | None = None
    source: str = SOURCE_NONE
    recognition_status: str = STATUS_UNRECOGNIZED
    crop_path: str | None = None
    crop_confidence: float = 0.0
    qr_raw: str | None = None
    mrz_raw: str | None = None
    ocr_text: str | None = None
    suggested_id: str | None = None
    note: str | None = None
    old_id: str | None = None
    full_name: str | None = None
    date_of_birth: str | None = None
    gender: str | None = None
    address: str | None = None
    issue_date: str | None = None
    father_name: str | None = None
    mother_name: str | None = None


@dataclass
class CCCDPersonPairRecord:
    personal_id: str | None = None
    old_id: str | None = None
    full_name: str | None = None
    date_of_birth: str | None = None
    gender: str | None = None
    address: str | None = None
    issue_date: str | None = None
    father_name: str | None = None
    mother_name: str | None = None
    front_file_name: str | None = None
    front_file_path: str | None = None
    front_crop: str | None = None
    back_file_name: str | None = None
    back_file_path: str | None = None
    back_crop: str | None = None
    front_recognition_status: str = STATUS_UNRECOGNIZED
    back_recognition_status: str = STATUS_UNRECOGNIZED
    match_status: str = FRONT_ONLY
    note: str | None = None
    user_edited: bool = False

    def recognition_label(self) -> str:
        if self.front_recognition_status == STATUS_CERTAIN:
            return STATUS_LABELS[STATUS_CERTAIN]
        if self.front_recognition_status == STATUS_NEED_REVIEW or self.match_status == NEED_REVIEW:
            return STATUS_LABELS[STATUS_NEED_REVIEW]
        return STATUS_LABELS.get(self.front_recognition_status, STATUS_LABELS[STATUS_UNRECOGNIZED])

    def match_label(self) -> str:
        return MATCH_LABELS.get(self.match_status, self.match_status)

    def display_row(self) -> list[str]:
        return [
            self.personal_id or "",
            self.old_id or "",
            self.full_name or "",
            self.date_of_birth or "",
            self.gender or "",
            self.address or "",
            self.issue_date or "",
            self.father_name or "",
            self.mother_name or "",
            self.front_file_name or "",
            self.back_file_name or "",
            self.recognition_label(),
            self.match_label(),
            self.note or "",
        ]


@dataclass
class PairingStats:
    total: int = 0
    processed: int = 0
    front: int = 0
    back: int = 0
    unknown: int = 0
    paired: int = 0
    front_only: int = 0
    orphan_back: int = 0
    duplicate: int = 0


@dataclass
class PairingBatchResult:
    images: list[CCCDPairImageResult] = field(default_factory=list)
    persons: list[CCCDPersonPairRecord] = field(default_factory=list)
    orphan_backs: list[CCCDPairImageResult] = field(default_factory=list)
    unknowns: list[CCCDPairImageResult] = field(default_factory=list)
    stats: PairingStats = field(default_factory=PairingStats)
