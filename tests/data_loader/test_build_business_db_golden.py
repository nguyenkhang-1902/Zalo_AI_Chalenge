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
    # Gộp raw trước khi clean (FR-011) phải ra đúng cả 17 file BanHang_Thang.., không chỉ "đa số":
    # một regression lùi về gộp 13-16 file phải FAIL test này, không được lọt qua im lặng.
    assert len(merged["source_files"]) == 17


def test_merges_period_sheets_within_a_single_file_for_biz_102(tmp_path: Path):
    """Finding #5: biz_102/DonHang_ChiTiet.xlsx chia 18 sheet theo tháng (T01_2025..T06_2026)
    trong CÙNG 1 file -- phải gộp thành 1 table, không ra 18 table rời rạc."""
    business_dir = PROJECT_ROOT / "train" / "data" / "biz_102"
    assert business_dir.exists(), "Cần có dữ liệu thật train/data/biz_102"

    summary = build_business(business_dir, tmp_path)

    don_hang_tables = [t for t in summary["tables"] if t["table_name"].startswith("DonHang_ChiTiet")]
    assert len(don_hang_tables) == 1, f"Phải gộp thành 1 table, hiện ra: {don_hang_tables}"
    assert len(don_hang_tables[0]["source_files"]) == 18


def test_merges_period_sheets_across_two_files_for_biz_105(tmp_path: Path):
    """Finding #5(b): biz_105 có 2 file (SoBanHang_1.xlsx 12 sheet + SoBanHang_2026.xlsx 5 sheet)
    cùng khai cột giống nhau trong README -- phải gộp XUYÊN FILE thành 1 table duy nhất."""
    business_dir = PROJECT_ROOT / "train" / "data" / "biz_105"
    assert business_dir.exists(), "Cần có dữ liệu thật train/data/biz_105"

    summary = build_business(business_dir, tmp_path)

    so_ban_hang_tables = [t for t in summary["tables"] if t["table_name"].startswith("SoBanHang")]
    assert len(so_ban_hang_tables) == 1, f"Phải gộp thành 1 table, hiện ra: {so_ban_hang_tables}"
    assert len(so_ban_hang_tables[0]["source_files"]) == 17  # 12 sheet file 1 + 5 sheet file 2


def test_merges_period_sheets_for_dev_014_without_readme_and_excludes_stray_sheet(tmp_path: Path):
    """Finding #5(c): dev_014 (1 trong 7 business README văn xuôi, không có cột khai báo) --
    phải gộp ở tầng post-clean (không cần README), và sheet "Ghi tắt" không khớp pattern kỳ phải
    đứng riêng, không bị kéo vào nhóm gộp."""
    business_dir = PROJECT_ROOT / "public_test" / "data" / "dev_014"
    assert business_dir.exists(), "Cần có dữ liệu thật public_test/data/dev_014"

    summary = build_business(business_dir, tmp_path)

    so_ban_hang_tables = [
        t for t in summary["tables"] if t["table_name"].startswith("SoBanHang") and len(t["source_files"]) > 1
    ]
    assert len(so_ban_hang_tables) == 1, f"Phải có đúng 1 table gộp theo kỳ, hiện ra: {summary['tables']}"


def test_rerun_is_idempotent(tmp_path: Path):
    business_dir = PROJECT_ROOT / "train" / "data" / "biz_105"

    first = build_business(business_dir, tmp_path)
    second = build_business(business_dir, tmp_path)

    assert first == second  # SC-004: chạy lại ra kết quả giống nhau 100%


def test_rerun_is_idempotent_for_raw_grouped_business(tmp_path: Path):
    """SC-004 cho đường gộp raw-period-series mới (dev_005 thực sự đi qua
    _group_raw_period_series/_clean_raw_group_to_table; biz_105 không, vì các sheet của nó có
    tên khác nhau từng tháng -> không tạo raw group nào)."""
    business_dir = PROJECT_ROOT / "public_test" / "data" / "dev_005"

    first = build_business(business_dir, tmp_path)
    second = build_business(business_dir, tmp_path)

    assert first == second


def test_one_broken_file_does_not_crash_other_tables(tmp_path: Path):
    """Acceptance scenario 5: 1 file hỏng -> business vẫn ra table của file tốt, không crash."""
    business_dir = tmp_path / "biz_broken"
    business_dir.mkdir()
    (business_dir / "good.csv").write_text("A,B\n1,2\n3,4\n", encoding="utf-8")
    # "bad.csv" chứa byte không phải UTF-8 hợp lệ (0xFF không bao giờ hợp lệ trong UTF-8) -> lỗi
    # ngay khi đọc, bị read_all_sheets bỏ qua tại tầng đọc file (độc lập với fix Finding #8 ở
    # tầng dựng DataFrame -- không còn dùng lệch-số-cột để giả lập file hỏng nữa, vì sau fix đó
    # không còn làm file hỏng theo cách đó).
    (business_dir / "bad.csv").write_bytes(b"A,B\n\xff\xfe,2\n")

    summary = build_business(business_dir, tmp_path / "out")

    table_names = [t["table_name"] for t in summary["tables"]]
    assert "good" in table_names
    assert "bad" not in table_names  # bị bỏ qua, không làm hỏng cả business
