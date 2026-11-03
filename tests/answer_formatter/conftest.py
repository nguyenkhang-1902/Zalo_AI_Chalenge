"""Helper build dữ liệu thật cho test answer_formatter — build qua chính
data_loader.build_business_db.build_business trên train/ thật, không dùng fixture bịa."""
from __future__ import annotations

import shutil
from pathlib import Path

from data_loader.build_business_db import build_business

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TRAIN_DIR = PROJECT_ROOT / "train"


def build_real_dataset(dataset_dir: Path, business_ids: set[str]) -> None:
    for name in ("rulebook.md", "calendar.csv"):
        shutil.copy(TRAIN_DIR / name, dataset_dir / name)
    for business_id in business_ids:
        build_business(TRAIN_DIR / "data" / business_id, dataset_dir)
