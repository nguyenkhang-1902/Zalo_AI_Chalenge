"""Chạy loader cho toàn bộ business trong 1 dataset (train/ hoặc public_test/),
copy kèm rulebook.md + calendar.csv (FR-013) vào cùng chỗ output."""
from __future__ import annotations

import argparse
import logging
import shutil
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

from data_loader.build_business_db import build_business

logger = logging.getLogger(__name__)


def _build_one(business_dir: Path, out_dir: Path) -> tuple[str, str]:
    """Build 1 business trong process con, tự bắt exception ở đây (process con không dùng
    chung logger/traceback với process cha nên trả status đơn giản thay vì raise lại)."""
    business_id = business_dir.name
    try:
        build_business(business_dir, out_dir)
        return business_id, "ok"
    except Exception:
        logger.error("Business %s thất bại hoàn toàn", business_id, exc_info=True)
        return business_id, "failed"


def build_all(dataset_dir: Path, out_dir: Path) -> dict[str, str]:
    """Chạy build_business song song theo process cho mỗi business (độc lập, mỗi business ghi
    file .duckdb/.schema.json riêng tên) để kịp ngân sách SC-003 (<2 phút cho 30 business thật) —
    chạy tuần tự mất ~400s trên máy này."""
    out_dir.mkdir(parents=True, exist_ok=True)

    for shared_file in ("rulebook.md", "calendar.csv"):
        src = dataset_dir / shared_file
        if src.exists():
            shutil.copy(src, out_dir / shared_file)

    business_dirs = [d for d in sorted((dataset_dir / "data").iterdir()) if d.is_dir()]

    results: dict[str, str] = {}
    start = time.monotonic()
    with ProcessPoolExecutor() as pool:
        futures = [pool.submit(_build_one, business_dir, out_dir) for business_dir in business_dirs]
        for future in as_completed(futures):
            business_id, status = future.result()
            results[business_id] = status
    logger.info("Xong %d business trong %.1fs", len(results), time.monotonic() - start)
    return results


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset-dir", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    build_all(args.dataset_dir, args.out)


if __name__ == "__main__":
    main()
