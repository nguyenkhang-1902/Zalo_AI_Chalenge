"""Golden test: chạy loader cho TOÀN BỘ train/ + public_test/ thật, kiểm SC-001 (không crash, mỗi
business >=1 table) + SC-003 (<2 phút cho train/)."""
import time
from pathlib import Path

from data_loader.build_all import build_all

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _assert_every_business_ok(results: dict[str, str]) -> None:
    not_ok = {biz: status for biz, status in results.items() if status != "ok"}
    # "empty" = chạy xong nhưng 0 table (vd biz_123/dev_006 chỉ có pos.sqlite) -- cũng là lỗi SC-001
    assert not_ok == {}, f"Business không ra được table hợp lệ: {not_ok}"


def test_builds_entire_train_dataset_within_time_budget(tmp_path: Path):
    train_dir = PROJECT_ROOT / "train"
    assert train_dir.exists(), "Cần có dữ liệu thật train/ ở gốc repo"

    start = time.monotonic()
    results = build_all(train_dir, tmp_path)
    elapsed = time.monotonic() - start

    assert len(results) == 30
    _assert_every_business_ok(results)  # SC-001
    assert elapsed < 120, f"Quá thời gian cho phép: {elapsed:.1f}s"  # SC-003

    assert (tmp_path / "rulebook.md").exists()
    assert (tmp_path / "calendar.csv").exists()


def test_builds_entire_public_test_dataset(tmp_path: Path):
    public_dir = PROJECT_ROOT / "public_test"
    assert public_dir.exists(), "Cần có dữ liệu thật public_test/ ở gốc repo"

    results = build_all(public_dir, tmp_path)

    assert len(results) == 14
    _assert_every_business_ok(results)
