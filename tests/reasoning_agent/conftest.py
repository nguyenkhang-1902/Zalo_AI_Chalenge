"""Helper build dữ liệu thật cho test reasoning_agent — build qua chính
data_loader.build_business_db.build_business trên train/ thật, không dùng fixture bịa."""
from __future__ import annotations

import shutil
from pathlib import Path

from data_loader.build_business_db import build_business

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TRAIN_DIR = PROJECT_ROOT / "train"


def build_real_business(dataset_dir: Path, business_id: str, copy_dataset_files: bool = True) -> None:
    """Build thật 1 business từ train/data/<business_id> vào dataset_dir (thường tmp_path của
    test). copy_dataset_files=False khi test không cần rulebook.md/calendar.csv (schema_tools,
    sql_tool) -- chỉ cần=True cho test đụng agent.py (Task 6) hoặc react_loop đầy đủ."""
    if copy_dataset_files:
        for name in ("rulebook.md", "calendar.csv"):
            shutil.copy(TRAIN_DIR / name, dataset_dir / name)
    build_business(TRAIN_DIR / "data" / business_id, dataset_dir)
