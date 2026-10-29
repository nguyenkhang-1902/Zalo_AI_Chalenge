"""Golden test: chạy loader trên dữ liệu thật của BTC, không phải fixture giả."""
from pathlib import Path

import duckdb

from data_loader.build_business_db import build_business

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_builds_real_small_business_without_crashing(tmp_path: Path):
    business_dir = PROJECT_ROOT / "train" / "data" / "biz_105"
    assert business_dir.exists(), "Cần có dữ liệu thật train/data/biz_105"

    summary = build_business(business_dir, tmp_path)

    assert len(summary["tables"]) > 0
    db_path = tmp_path / "biz_105.duckdb"
    assert db_path.exists()
    con = duckdb.connect(str(db_path))
    table_names = [r[0] for r in con.execute("SHOW TABLES").fetchall()]
    con.close()
    assert len(table_names) == len(summary["tables"])


def test_merges_monthly_files_for_dev_005(tmp_path: Path):
    business_dir = PROJECT_ROOT / "public_test" / "data" / "dev_005"
    assert business_dir.exists(), "Cần có dữ liệu thật public_test/data/dev_005"

    summary = build_business(business_dir, tmp_path)

    table_names = [t["table_name"] for t in summary["tables"]]
    assert len(table_names) < 24  # 24 file nhưng phải gộp bớt, không ra 24 table rời rạc

    merged = next(t for t in summary["tables"] if len(t["source_files"]) > 1)
    assert len(merged["source_files"]) >= 12  # gộp được phần lớn 17 file BanHang_Thang..


def test_rerun_is_idempotent(tmp_path: Path):
    business_dir = PROJECT_ROOT / "train" / "data" / "biz_105"

    first = build_business(business_dir, tmp_path)
    second = build_business(business_dir, tmp_path)

    assert first == second  # SC-004: chạy lại ra kết quả giống nhau 100%


def test_one_broken_file_does_not_crash_other_tables(tmp_path: Path):
    """Acceptance scenario 5: 1 file hỏng -> business vẫn ra table của file tốt, không crash."""
    business_dir = tmp_path / "biz_broken"
    business_dir.mkdir()
    (business_dir / "good.csv").write_text("A,B\n1,2\n3,4\n", encoding="utf-8")
    # "bad.csv" có dòng số cột không khớp header -> ép pandas raise lỗi khi dựng DataFrame
    (business_dir / "bad.csv").write_text("A,B\n1,2,3\n4,5\n", encoding="utf-8")

    summary = build_business(business_dir, tmp_path / "out")

    table_names = [t["table_name"] for t in summary["tables"]]
    assert "good" in table_names
    assert "bad" not in table_names  # bị bỏ qua, không làm hỏng cả business
