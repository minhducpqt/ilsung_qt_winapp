from __future__ import annotations

import re
from dataclasses import dataclass

from app.services.cccd_qr_parser import CCCD_ID_RE, OLD_ID_RE, normalize_qr_date
from app.services.vietnamese_names import looks_like_vietnamese_name, normalize_person_name, pick_vietnamese_name

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


@dataclass
class OCRItem:
    text: str
    confidence: float | None = None


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


def _looks_like_name(text: str) -> bool:
    return looks_like_vietnamese_name(text) or (
        len(text.strip()) >= 4
        and not any(ch.isdigit() for ch in text)
        and len(text.split()) >= 2
    )


def _normalize_gender(text: str) -> str | None:
    value = _norm(text)
    if value in {"nam", "male"}:
        return "Nam"
    if value in {"nữ", "nu", "female"}:
        return "Nữ"
    if "nam" in value and "nữ" not in value and "nu" not in value:
        return "Nam"
    if "nữ" in value or re.search(r"\bnu\b", value) or "female" in value:
        return "Nữ"
    return None


def _is_labelish(text: str) -> bool:
    lowered = _norm(text)
    if lowered in {"full name", "date of birth", "dob", "sex", "gender", "no", "place of residence", "residence"}:
        return True
    if lowered.startswith("/ ") or lowered.startswith("no:"):
        return True
    return False


def _after_label(lines: list[str], labels: tuple[str, ...]) -> str | None:
    for index, line in enumerate(lines):
        lowered = _norm(line)
        for label in labels:
            if label in lowered:
                match = re.search(re.escape(label), lowered)
                if match:
                    original_after = line[match.end() :].strip(" :.-/")
                    original_after = re.sub(
                        r"^(full name|date of birth|dob|sex|gender|place of residence|residence)\s*:?\s*",
                        "",
                        original_after,
                        flags=re.IGNORECASE,
                    ).strip(" :.-/")
                    if original_after and not _is_labelish(original_after):
                        return original_after.strip()
                if index + 1 < len(lines):
                    nxt = lines[index + 1].strip()
                    if nxt and not _is_labelish(nxt):
                        return nxt
    return None


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
        result.full_name = normalize_person_name(name)
    if not result.full_name:
        result.full_name = pick_vietnamese_name(lines)

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

    address = _after_label(lines, ADDRESS_LABELS)
    if address and len(address) >= 6 and not CCCD_ID_RE.fullmatch(address):
        result.address = address

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
