from __future__ import annotations

import re
from dataclasses import dataclass, fields

from app.services.vietnamese_names import normalize_person_name

CCCD_ID_RE = re.compile(r"^\d{12}$")
OLD_ID_RE = re.compile(r"^\d{8,12}$")
DATE_COMPACT_RE = re.compile(r"^(\d{2})(\d{2})(\d{4})$")


@dataclass
class ParsedCCCDQR:
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
    schema: str | None = None
    raw_qr: str | None = None
    certain: bool = False


def is_cccd_id(value: str | None) -> bool:
    return bool(value and CCCD_ID_RE.fullmatch(value.strip()))


def normalize_qr_date(value: str | None) -> str | None:
    if not value:
        return None
    text = value.strip()
    compact = re.sub(r"\D", "", text)
    match = DATE_COMPACT_RE.fullmatch(compact)
    if not match:
        return None
    day, month, year = int(match.group(1)), int(match.group(2)), int(match.group(3))
    if not (1 <= day <= 31 and 1 <= month <= 12 and 1900 <= year <= 2100):
        return None
    return f"{day:02d}/{month:02d}/{year}"


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    text = value.strip()
    return text or None


def _normalize_gender(value: str | None) -> str | None:
    if not value:
        return None
    text = value.strip().lower()
    mapping = {
        "nam": "Nam",
        "male": "Nam",
        "nữ": "Nữ",
        "nu": "Nữ",
        "female": "Nữ",
    }
    return mapping.get(text)


def _old_id(value: str | None) -> str | None:
    text = _clean(value)
    if not text:
        return None
    digits = re.sub(r"\D", "", text)
    if OLD_ID_RE.fullmatch(digits) and not CCCD_ID_RE.fullmatch(digits):
        return digits
    return None


def _normalize_qr_payload(raw: str) -> str:
    text = raw.strip().lstrip("\ufeff").replace("\x00", "").replace("\r", "")
    match = re.search(r"(?<!\d)(\d{12}\|.*)$", text, flags=re.DOTALL)
    if match:
        return match.group(1).strip()
    match = re.search(r"(?<!\d)(\d{12})(?!\d)", text)
    if match and "|" not in text:
        return match.group(1)
    return text.strip()


def parse_cccd_qr(raw: str | None) -> ParsedCCCDQR | None:
    """Parse CCCD QR. Core 7 fields are the usual payload; anything after is optional."""
    if raw is None:
        return None
    payload = _normalize_qr_payload(raw)
    if not payload:
        return None

    result = ParsedCCCDQR(raw_qr=payload)

    if CCCD_ID_RE.fullmatch(payload):
        result.personal_id = payload
        result.schema = "id_only"
        result.certain = True
        return result

    if "|" not in payload:
        return None

    parts = [part.strip() for part in payload.split("|")]
    if not parts or not CCCD_ID_RE.fullmatch(parts[0]):
        return None

    result.personal_id = parts[0]
    result.old_id = _old_id(parts[1]) if len(parts) > 1 else None
    result.full_name = normalize_person_name(_clean(parts[2])) if len(parts) > 2 else None
    result.date_of_birth = normalize_qr_date(parts[3]) if len(parts) > 3 else None
    result.gender = _normalize_gender(parts[4]) if len(parts) > 4 else None
    result.address = _clean(parts[5]) if len(parts) > 5 else None
    result.issue_date = normalize_qr_date(parts[6]) if len(parts) > 6 else None

    extras = parts[7:]
    remaining: list[str] = []
    for extra in extras:
        extra = extra.strip()
        if not extra:
            continue
        if is_cccd_id(extra) and not result.cancelled_personal_id:
            result.cancelled_personal_id = extra
            continue
        if normalize_qr_date(extra) and result.issue_date:
            continue
        remaining.append(extra)

    if remaining:
        result.father_name = normalize_person_name(remaining[0])
    if len(remaining) >= 2:
        result.mother_name = normalize_person_name(remaining[1])

    if result.father_name or result.mother_name:
        result.schema = "adult_plus_optional"
    elif len(parts) >= 7:
        result.schema = "adult_v1"
    else:
        result.schema = "adult_partial"

    # QR CCCD is the strongest source: accept once the 12-digit ID and pipe schema are present.
    result.certain = True
    return result


def parsed_to_fields(parsed: ParsedCCCDQR) -> dict[str, str | None]:
    data = {}
    for item in fields(ParsedCCCDQR):
        if item.name in {"schema", "raw_qr", "certain"}:
            continue
        data[item.name] = getattr(parsed, item.name)
    return data
