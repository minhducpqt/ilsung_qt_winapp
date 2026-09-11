from pathlib import Path

from app.models.cccd_result import SOURCE_QR, STATUS_CERTAIN, CCCDResult
from app.services.cccd_draft_store import draft_path_for_folder, load_cccd_draft, save_cccd_draft


def test_draft_roundtrip_keeps_edited_fields(tmp_path: Path):
    folder = tmp_path / "cccd"
    folder.mkdir()
    result = CCCDResult(
        file_name="a.jpg",
        file_path=str(folder / "a.jpg"),
        personal_id="001234567890",
        full_name="Nguyễn Văn Test",
        source=SOURCE_QR,
        status=STATUS_CERTAIN,
        manual_edit=True,
        note="đã sửa địa chỉ",
    )
    path = save_cccd_draft(folder, [result], root=tmp_path / "drafts")
    assert path.exists()
    loaded = load_cccd_draft(folder, root=tmp_path / "drafts")
    assert len(loaded) == 1
    assert loaded[0].personal_id == "001234567890"
    assert loaded[0].full_name == "Nguyễn Văn Test"
    assert loaded[0].manual_edit is True
    assert loaded[0].note == "đã sửa địa chỉ"


def test_empty_results_are_not_saved(tmp_path: Path):
    folder = tmp_path / "cccd"
    folder.mkdir()
    empty = CCCDResult(file_name="blank.jpg", file_path=str(folder / "blank.jpg"))
    save_cccd_draft(folder, [empty], root=tmp_path / "drafts")
    assert load_cccd_draft(folder, root=tmp_path / "drafts") == []


def test_same_folder_reuses_draft_file(tmp_path: Path):
    folder = tmp_path / "cccd"
    folder.mkdir()
    first = draft_path_for_folder(folder, root=tmp_path / "drafts")
    second = draft_path_for_folder(folder, root=tmp_path / "drafts")
    assert first == second


def test_missing_draft_returns_empty(tmp_path: Path):
    folder = tmp_path / "missing"
    folder.mkdir()
    assert load_cccd_draft(folder, root=tmp_path / "drafts") == []
