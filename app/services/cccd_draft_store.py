from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path

from app.config import user_data_dir
from app.models.cccd_result import CCCDResult

DRAFT_VERSION = 1


def drafts_dir() -> Path:
    path = user_data_dir() / "cccd_drafts"
    path.mkdir(parents=True, exist_ok=True)
    return path


def draft_path_for_folder(folder: str | Path, root: Path | None = None) -> Path:
    resolved = str(Path(folder).expanduser().resolve())
    digest = hashlib.sha1(resolved.encode("utf-8")).hexdigest()[:16]
    base = Path(root) if root is not None else drafts_dir()
    base.mkdir(parents=True, exist_ok=True)
    return base / f"{digest}.json"


def save_cccd_draft(folder: str | Path, results: list[CCCDResult], root: Path | None = None) -> Path:
    destination = draft_path_for_folder(folder, root=root)
    payload = {
        "version": DRAFT_VERSION,
        "folder": str(Path(folder).expanduser().resolve()),
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "results": [result.to_dict() for result in results if result.has_data() or result.manual_edit],
    }
    destination.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return destination


def load_cccd_draft(folder: str | Path, root: Path | None = None) -> list[CCCDResult]:
    path = draft_path_for_folder(folder, root=root)
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    rows = payload.get("results") if isinstance(payload, dict) else None
    if not isinstance(rows, list):
        return []
    results: list[CCCDResult] = []
    for row in rows:
        if isinstance(row, dict):
            results.append(CCCDResult.from_dict(row))
    return results
