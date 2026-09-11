from __future__ import annotations

import re
from dataclasses import dataclass

from app.services.cccd_qr_parser import CCCD_ID_RE, OLD_ID_RE, normalize_qr_date
from app.services.vietnamese_names import fold_vi, looks_like_vietnamese_name, normalize_person_name, pick_vietnamese_name
from app.services.vietnamese_provinces import contains_province

CCCD_IN_TEXT_RE = re.compile(r"\b(\d{12})\b")
OLD_IN_TEXT_RE = re.compile(r"\b(\d{9})\b")
DATE_SEP_RE = re.compile(r"\b(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})\b")
DATE_COMPACT_IN_TEXT_RE = re.compile(r"\b(\d{8})\b")

NAME_LABELS = (
    "họ, chữ đệm và tên khai sinh",
    "họ và tên",
    "ho va ten",
    "full name",
)
DOB_LABELS = ("ngày sinh", "ngay sinh", "date of birth", "dob")
GENDER_LABELS = ("giới tính", "gioi tinh", "sex", "gender")
ADDRESS_LABELS = (
    "nơi thường trú",
    "noi thuong tru",
    "nơi cư trú",
    "noi cu tru",
    "place of residence",
    "residence",
)
ISSUE_LABELS = ("ngày cấp", "ngay cap", "date of issue", "date of issuance")
FATHER_LABELS = ("họ tên cha", "ho ten cha", "cha:", "father")
MOTHER_LABELS = ("họ tên mẹ", "ho ten me", "mẹ:", "me:", "mother")
OLD_ID_LABELS = ("cmnd", "số cũ", "so cu", "old id", "identity card")

# Chữ chỉ dẫn in trên CCCD — không phải nội dung khai thác.
_GUIDE_PHRASES = (
    "họ, chữ đệm và tên khai sinh",
    "ho, chu dem va ten khai sinh",
    "họ chữ đệm và tên khai sinh",
    "date of issuance",
    "place of residence",
    "place of origin",
    "date of expiry",
    "date of birth",
    "date of issue",
    "nơi thường trú",
    "noi thuong tru",
    "nơi cư trú",
    "noi cu tru",
    "có giá trị đến",
    "co gia tri den",
    "số định danh cá nhân",
    "so dinh danh ca nhan",
    "quốc tịch",
    "quoc tich",
    "nationality",
    "quê quán",
    "que quan",
    "họ và tên",
    "ho va ten",
    "full name",
    "ngày sinh",
    "ngay sinh",
    "giới tính",
    "gioi tinh",
    "ngày cấp",
    "ngay cap",
    "identity card",
    "residence",
    "gender",
    "origin",
    "expiry",
    "dob",
    "sex",
    "số / no",
    "so / no",
    "số/no",
    "so/no",
)
_GUIDE_RE = re.compile(
    "|".join(re.escape(phrase) for phrase in sorted(_GUIDE_PHRASES, key=len, reverse=True)),
    flags=re.IGNORECASE,
)
_LABEL_CRUMBS = {"full", "name", "sex", "gender", "dob", "id", "i", "of", "the"}


@dataclass
class OCRItem:
    text: str
    confidence: float | None = None
    box: object | None = None


@dataclass
class ParsedCCCDOCR:
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
    ocr_confidence: float | None = None


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def _strip_guide_text(text: str) -> str:
    cleaned = _GUIDE_RE.sub(" ", text)
    cleaned = re.sub(r"[:/\\|]+", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" :.-")
    words = [word for word in cleaned.split() if fold_vi(word) not in _LABEL_CRUMBS]
    return " ".join(words)


def _is_labelish(text: str) -> bool:
    stripped = _strip_guide_text(text)
    folded = fold_vi(stripped)
    if folded in {"nam", "nu", "male", "female"}:
        return False
    if len(stripped) <= 2:
        return True
    if folded in {"full name", "date of birth", "place of residence", "nationality", "viet nam", "vietnam"}:
        return True
    return False


def _looks_like_name(text: str) -> bool:
    stripped = _strip_guide_text(text)
    if not stripped or _is_labelish(stripped):
        return False
    if looks_like_vietnamese_name(stripped) or looks_like_vietnamese_name(text):
        return True
    words = stripped.split()
    if any(fold_vi(word) in _LABEL_CRUMBS for word in words):
        return False
    return len(stripped) >= 4 and not any(ch.isdigit() for ch in stripped) and 2 <= len(words) <= 6


def _normalize_gender(text: str) -> str | None:
    value = _norm(_strip_guide_text(text) or text)
    tokens = value.split()
    if value in {"nam", "male"} or tokens == ["nam"]:
        return "Nam"
    if value in {"nữ", "nu", "female"}:
        return "Nữ"
    if len(tokens) <= 2 and "nam" in tokens and "nữ" not in value and "nu" not in tokens:
        return "Nam"
    if len(tokens) <= 2 and ("nữ" in value or "nu" in tokens or "female" in tokens):
        return "Nữ"
    return None


def _value_after_labels(line: str, labels: tuple[str, ...]) -> str | None:
    lowered = _norm(line)
    remainder = None
    for label in labels:
        match = re.search(re.escape(label), lowered)
        if not match:
            continue
        after = _strip_guide_text(line[match.end() :])
        if after and not _is_labelish(after):
            remainder = after
    if remainder:
        return remainder
    whole = _strip_guide_text(line)
    if whole and not _is_labelish(whole) and not any(label in lowered for label in labels if len(label) <= 3):
        # Line may be "Họ và tên / Full name: NGUYEN VAN A"
        if any(label in lowered for label in labels):
            return whole
    return None


def _next_content(lines: list[str], start: int, limit: int = 3) -> tuple[str, int] | None:
    end = min(start + 1 + limit, len(lines))
    for index in range(start + 1, end):
        raw = lines[index].strip()
        cleaned = _strip_guide_text(raw)
        if cleaned and not _is_labelish(raw) and not _is_labelish(cleaned):
            return cleaned, index
    return None


def _find_labeled(lines: list[str], labels: tuple[str, ...]) -> tuple[str, int] | None:
    for index, line in enumerate(lines):
        lowered = _norm(line)
        if not any(label in lowered for label in labels):
            continue
        same_line = _value_after_labels(line, labels)
        if same_line:
            return same_line, index
        following = _next_content(lines, index)
        if following:
            return following
    return None


def _after_label(lines: list[str], labels: tuple[str, ...]) -> str | None:
    found = _find_labeled(lines, labels)
    return found[0] if found else None


def _parse_address(lines: list[str]) -> str | None:
    found = _find_labeled(lines, ADDRESS_LABELS)
    if not found:
        return None
    address, index = found
    if len(address) < 6 or CCCD_ID_RE.fullmatch(address):
        return None
    if index + 1 < len(lines):
        nxt_raw = lines[index + 1].strip()
        nxt = _strip_guide_text(nxt_raw)
        if (
            nxt
            and not _is_labelish(nxt_raw)
            and contains_province(nxt)
            and fold_vi(nxt) not in fold_vi(address)
        ):
            address = f"{address.rstrip(',; ')}, {nxt}"
    return address


def _collect_dates(lines: list[str], blob: str) -> list[str]:
    found: list[str] = []
    for text in [*lines, blob]:
        for match in DATE_SEP_RE.finditer(text):
            day, month, year = int(match.group(1)), int(match.group(2)), int(match.group(3))
            if 1 <= day <= 31 and 1 <= month <= 12 and 1900 <= year <= 2100:
                value = f"{day:02d}/{month:02d}/{year}"
                if value not in found:
                    found.append(value)
        for match in DATE_COMPACT_IN_TEXT_RE.finditer(text):
            value = normalize_qr_date(match.group(1))
            if value and value not in found:
                found.append(value)
    found.sort(key=lambda item: int(item.split("/")[-1]))
    return found


def _first_date(text: str) -> str | None:
    match = DATE_SEP_RE.search(text)
    if match:
        day, month, year = int(match.group(1)), int(match.group(2)), int(match.group(3))
        if 1 <= day <= 31 and 1 <= month <= 12 and 1900 <= year <= 2100:
            return f"{day:02d}/{month:02d}/{year}"
    compact = DATE_COMPACT_IN_TEXT_RE.search(text)
    if compact:
        return normalize_qr_date(compact.group(1))
    return None


def parse_cccd_ocr(items: list[OCRItem] | list[str], full_text: str | None = None) -> ParsedCCCDOCR:
    lines: list[str] = []
    confidences: list[float] = []
    for item in items:
        if isinstance(item, OCRItem):
            if item.text.strip():
                lines.append(item.text.strip())
                if item.confidence is not None:
                    confidences.append(item.confidence)
        else:
            text = str(item).strip()
            if text:
                lines.append(text)

    blob = full_text if full_text is not None else "\n".join(lines)
    result = ParsedCCCDOCR()
    if confidences:
        result.ocr_confidence = sum(confidences) / len(confidences)

    ids = CCCD_IN_TEXT_RE.findall(blob)
    if ids:
        result.personal_id = ids[0]
        if len(ids) > 1:
            result.cancelled_personal_id = ids[1]

    old_near_label = _after_label(lines, OLD_ID_LABELS)
    if old_near_label and OLD_ID_RE.fullmatch(re.sub(r"\D", "", old_near_label)[:9] if old_near_label else ""):
        digits = re.sub(r"\D", "", old_near_label)
        if OLD_ID_RE.fullmatch(digits):
            result.old_id = digits
    if not result.old_id:
        for match in OLD_IN_TEXT_RE.findall(blob):
            if match != (result.personal_id or "")[:9]:
                result.old_id = match
                break

    name = _after_label(lines, NAME_LABELS)
    if name and _looks_like_name(name):
        result.full_name = normalize_person_name(_strip_guide_text(name) or name)
    if not result.full_name:
        result.full_name = pick_vietnamese_name([line for line in lines if not _is_labelish(line)])

    dates = _collect_dates(lines, blob)
    dob_line = _after_label(lines, DOB_LABELS)
    result.date_of_birth = _first_date(dob_line) if dob_line else None
    if not result.date_of_birth and dates:
        result.date_of_birth = dates[0]

    gender_line = _after_label(lines, GENDER_LABELS)
    if gender_line:
        result.gender = _normalize_gender(gender_line)
    if not result.gender:
        for line in lines:
            gender = _normalize_gender(line)
            if gender and _norm(line) in {"nam", "nữ", "nu", "male", "female"}:
                result.gender = gender
                break

    result.address = _parse_address(lines)

    issue_line = _after_label(lines, ISSUE_LABELS)
    if issue_line:
        result.issue_date = _first_date(issue_line)
    if not result.issue_date and len(dates) >= 2:
        result.issue_date = dates[-1]

    father = _after_label(lines, FATHER_LABELS)
    if father and _looks_like_name(father):
        result.father_name = normalize_person_name(father)
    mother = _after_label(lines, MOTHER_LABELS)
    if mother and _looks_like_name(mother):
        result.mother_name = normalize_person_name(mother)

    return result
