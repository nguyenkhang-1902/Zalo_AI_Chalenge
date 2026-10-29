"""Golden test: chạy loader cho TOÀN BỘ train/ thật, kiểm SC-001 (không crash) + SC-003 (<2 phút)."""
import time
from pathlib import Path

from data_loader.build_all import build_all

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_builds_entire_train_dataset_within_time_budget(tmp_path: Path):
    train_dir = PROJECT_ROOT / "train"
    assert train_dir.exists(), "Cần có dữ liệu thật train/ ở gốc repo"

    start = time.monotonic()
    results = build_all(train_dir, tmp_path)
    elapsed = time.monotonic() - start

    assert len(results) == 30
    failed = [biz for biz, status in results.items() if status == "failed"]
    assert failed == [], f"Business thất bại hoàn toàn: {failed}"  # SC-001
    assert elapsed < 120, f"Quá thời gian cho phép: {elapsed:.1f}s"  # SC-003

    assert (tmp_path / "rulebook.md").exists()
    assert (tmp_path / "calendar.csv").exists()
