"""Helper build dữ liệu thật cho test distill — dùng lại data train/ thật qua
data_loader.build_business_db.build_business (giống tests/reasoning_agent/conftest.py)."""
from __future__ import annotations

import shutil
from pathlib import Path

from data_loader.build_business_db import build_business

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TRAIN_DIR = PROJECT_ROOT / "train"


def build_real_business(dataset_dir: Path, business_id: str, copy_dataset_files: bool = True) -> None:
    if copy_dataset_files:
        for name in ("rulebook.md", "calendar.csv"):
            shutil.copy(TRAIN_DIR / name, dataset_dir / name)
    build_business(TRAIN_DIR / "data" / business_id, dataset_dir)
