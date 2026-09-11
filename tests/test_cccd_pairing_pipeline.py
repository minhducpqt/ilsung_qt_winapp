import pickle

from app.features.cccd_pairing.models import SIDE_UNKNOWN
from app.features.cccd_pairing.services.pipeline import (
    _analyze_one,
    pairing_worker_count,
    run_pass1_parallel,
)


def test_worker_count_stays_in_range():
    assert pairing_worker_count(0) == 1
    assert pairing_worker_count(1) == 1
    assert 2 <= pairing_worker_count(20) <= 6


def test_analyze_function_is_picklable():
    pickle.dumps(_analyze_one)


def test_parallel_one_worker_analyzes_missing_file(tmp_path):
    missing = tmp_path / "no_such.jpg"
    results = []

    def on_image(result, processed, total, collected):
        results.append(result)

    batch = run_pass1_parallel([str(missing)], workers=1, on_image=on_image)
    assert len(batch) == 1
    assert batch[0].side == SIDE_UNKNOWN
    assert batch[0].file_name == "no_such.jpg"
    assert results == batch
