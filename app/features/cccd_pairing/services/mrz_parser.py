from __future__ import annotations

import re
from dataclasses import dataclass

from app.services.cccd_qr_parser import CCCD_ID_RE

IDVNM_RE = re.compile(r"IDVNM", re.IGNORECASE)
CHEVRON_RE = re.compile(r"<{3,}")
DIGIT12_RE = re.compile(r"(\d{12})")
CONFUSION = str.maketrans(
    {
        "O": "0",
        "o": "0",
        "I": "1",
        "l": "1",
        "L": "1",
        "B": "8",
        "S": "5",
        "s": "5",
        "Z": "2",
        "z": "2",
    }
)


@dataclass
class MRZResult:
    personal_id: str | None = None
    full_name: str | None = None
    date_of_birth: str | None = None
    raw_mrz: str | None = None
    confidence: float = 0.0
    looks_like_mrz: bool = False


def normalize_mrz_text(text: str | None) -> str:
    if not text:
        return ""
    return re.sub(r"\s+", "", text.upper())


def looks_like_mrz(text: str | None) -> bool:
    if not text:
        return False
    compact = normalize_mrz_text(text)
    if IDVNM_RE.search(compact) and CHEVRON_RE.search(compact):
        return True
    return compact.count("<") >= 8 and bool(DIGIT12_RE.search(compact))


def extract_digit_candidates(text: str | None) -> list[str]:
    compact = normalize_mrz_text(text)
    found = DIGIT12_RE.findall(compact)
    unique: list[str] = []
    for item in found:
        if item not in unique:
            unique.append(item)
    return unique


def apply_ocr_confusion(text: str | None) -> str:
    compact = normalize_mrz_text(text)
    return compact.translate(CONFUSION)


def parse_mrz(text: str | None) -> MRZResult:
    result = MRZResult(raw_mrz=text, looks_like_mrz=looks_like_mrz(text))
    if not text:
        return result
    compact = normalize_mrz_text(text)
    candidates = extract_digit_candidates(compact)
    if not candidates:
        confused = apply_ocr_confusion(compact)
        maybe = DIGIT12_RE.findall(confused)
        if maybe and CCCD_ID_RE.fullmatch(maybe[0]):
            result.personal_id = maybe[0]
            result.confidence = 0.55
            return result
        return result
    result.personal_id = candidates[0]
    result.confidence = 0.9 if result.looks_like_mrz else 0.6
    name_matches = list(re.finditer(r"([A-Z]{2,})<<([A-Z<]+)", compact))
    for name_match in reversed(name_matches):
        surname = name_match.group(1).replace("<", " ").strip()
        if surname in {"VNM", "IDVNM"}:
            continue
        given = name_match.group(2).replace("<", " ").strip()
        full = f"{surname} {given}".strip()
        if full:
            result.full_name = re.sub(r"\s+", " ", full)
            break
    return result
