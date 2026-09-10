from __future__ import annotations

import shutil
from collections.abc import Callable
from pathlib import Path

SKIP_NAMES = {".ds_store", "thumbs.db", "desktop.ini"}


def scan_files(source: Path) -> list[Path]:
    """Return every file under source, sorted, skipping junk/hidden names."""
    if not source.is_dir():
        raise NotADirectoryError(str(source))

    files: list[Path] = []
    for path in source.rglob("*"):
        if not path.is_file():
            continue
        if path.name.startswith("."):
            continue
        if path.name.lower() in SKIP_NAMES:
            continue
        files.append(path)
    files.sort(key=lambda item: str(item).casefold())
    return files


def renamed_filename(index: int, original: Path) -> str:
    return f"F{index:05d}{original.suffix}"


def preview_renames(files: list[Path]) -> list[tuple[Path, str]]:
    return [(path, renamed_filename(index, path)) for index, path in enumerate(files, start=1)]


def copy_renamed_files(
    files: list[Path],
    destination: Path,
    progress: Callable[[int], None] | None = None,
    should_cancel: Callable[[], bool] | None = None,
) -> list[Path]:
    """Copy files into destination as F00001, F00002, ... Keep extensions."""
    destination.mkdir(parents=True, exist_ok=True)
    copied: list[Path] = []
    for index, source in enumerate(files, start=1):
        if should_cancel and should_cancel():
            break
        target = destination / renamed_filename(index, source)
        shutil.copy2(source, target)
        copied.append(target)
        if progress:
            progress(index)
    return copied


def is_same_or_inside(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False
