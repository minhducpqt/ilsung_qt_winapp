from __future__ import annotations

import re
import unicodedata

# Họ phổ biến ở Việt Nam — dùng để nhận diện và chuẩn hoá.
COMMON_SURNAMES = [
    "Nguyễn", "Trần", "Lê", "Phạm", "Hoàng", "Huỳnh", "Phan", "Vũ", "Võ",
    "Đặng", "Bùi", "Đỗ", "Hồ", "Ngô", "Dương", "Lý", "Đinh", "Trịnh",
    "Lương", "Đoàn", "Đào", "Mai", "Cao", "Lâm", "Tạ", "Thái", "Vương",
    "Tô", "Lưu", "Tăng", "Châu", "Hà", "Quách", "Kiều", "Tống", "La",
    "Lại", "Trương", "Chu", "Triệu", "Tôn", "Đàm", "Hứa", "Thiều", "Vi",
    "Mạc", "Từ", "Ông", "Thạch", "Nông", "Giàng", "Lò", "Cầm", "Bạch",
    "Đinh", "Hà", "Kim", "Tăng", "Ung", "Diệp", "Nhữ", "Phùng", "Quang",
]

COMMON_NAME_WORDS = [
    "Văn", "Thị", "Đức", "Minh", "Hoàng", "Hữu", "Công", "Xuân", "Thanh",
    "Quang", "Anh", "Ngọc", "Hồng", "Thu", "Kim", "Gia", "Bảo", "Khánh",
    "Tuấn", "Hùng", "Dũng", "Cường", "Hải", "Sơn", "Long", "Nam", "Việt",
    "Hương", "Hạnh", "Lan", "Linh", "Trang", "Thảo", "Phương", "Nga",
    "Yến", "Hà", "Hiếu", "Hòa", "Thành", "Thắng", "Tùng", "Tú", "Trinh",
    "Bình", "Giang", "Uyên", "Quỳnh", "My", "Vy", "Chi", "Trâm", "Ngân",
    "Đạt", "Phúc", "Lộc", "Tâm", "Tín", "Trung", "Kiên", "Mạnh", "Khôi",
    "Khang", "Phát", "Tài", "Lợi", "Nhi", "Ngọc", "Ánh", "Diễm", "Kiều",
    "Duyên", "Hiền", "Hoa", "Mai", "Đào", "Quế", "Trúc", "Vân",
    "Đức", "Duy", "Khải", "Nguyên", "Phong", "Quân", "Vinh", "Vỹ",
    "Huyền", "Nhung", "Oanh", "Quyên", "Thư", "Tiên", "Tuyết", "Xuân",
]


def fold_vi(text: str) -> str:
    """Lowercase and strip Vietnamese diacritics for matching."""
    decomposed = unicodedata.normalize("NFD", text.lower().strip())
    stripped = "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")
    return stripped.replace("đ", "d").replace("Đ", "d")


def _build_index() -> dict[str, str]:
    index: dict[str, str] = {}
    for word in COMMON_SURNAMES + COMMON_NAME_WORDS:
        key = fold_vi(word)
        index.setdefault(key, word)
    return index


_NAME_INDEX = _build_index()
_SURNAME_FOLDED = {fold_vi(name) for name in COMMON_SURNAMES}

_HEADER_HINTS = (
    "cong hoa", "xa hoi", "viet nam", "can cuoc", "cong dan", "socialist",
    "identity", "full name", "date of birth", "ho chieu", "nationality",
)


def looks_like_vietnamese_name(text: str) -> bool:
    cleaned = re.sub(r"[^0-9A-Za-zÀ-ỹĐđ\s]", " ", text)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if len(cleaned) < 4 or any(ch.isdigit() for ch in cleaned):
        return False
    folded = fold_vi(cleaned)
    if any(hint in folded for hint in _HEADER_HINTS):
        return False
    words = cleaned.split()
    if not (2 <= len(words) <= 6):
        return False
    return fold_vi(words[0]) in _SURNAME_FOLDED


def normalize_person_name(text: str | None) -> str | None:
    """Map OCR/QR name words onto common Vietnamese names when possible."""
    if not text:
        return None
    cleaned = re.sub(r"[^0-9A-Za-zÀ-ỹĐđ\s'\-]", " ", text)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if not cleaned or any(ch.isdigit() for ch in cleaned):
        return None

    words = cleaned.split()
    if not (1 <= len(words) <= 6):
        return cleaned.title() if len(words) >= 2 else None

    normalized: list[str] = []
    for word in words:
        canonical = _NAME_INDEX.get(fold_vi(word))
        if canonical:
            normalized.append(canonical)
        else:
            normalized.append(word[:1].upper() + word[1:].lower())
    return " ".join(normalized)


def pick_vietnamese_name(lines: list[str]) -> str | None:
    """Choose the most likely personal name line from OCR text."""
    candidates: list[str] = []
    for line in lines:
        if looks_like_vietnamese_name(line):
            normalized = normalize_person_name(line)
            if normalized:
                candidates.append(normalized)
    if not candidates:
        return None
    candidates.sort(key=lambda item: (item.split()[0] in COMMON_SURNAMES, len(item.split())), reverse=True)
    return candidates[0]
