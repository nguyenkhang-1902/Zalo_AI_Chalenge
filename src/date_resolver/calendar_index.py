"""Nạp calendar.csv thành chỉ mục tra ngày âm -> ngày dương."""
from __future__ import annotations

import csv
from dataclasses import dataclass, field
from datetime import date

REQUIRED_COLUMNS = ("date", "lunar_day", "lunar_month", "lunar_year", "lunar_leap")


@dataclass
class CalendarIndex:
    lunar_to_solar: dict[tuple[int, int, int], date] = field(default_factory=dict)


def load_calendar(csv_path: str) -> CalendarIndex:
    with open(csv_path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        missing = [col for col in REQUIRED_COLUMNS if col not in fieldnames]
        if missing:
            raise ValueError(f"calendar.csv thiếu cột bắt buộc: {missing}")

        index: dict[tuple[int, int, int], date] = {}
        for row in reader:
            if row["lunar_leap"] == "true":
                continue
            solar_date = date.fromisoformat(row["date"])
            key = (
                int(row["lunar_day"]),
                int(row["lunar_month"]),
                int(row["lunar_year"]),
            )
            index[key] = solar_date

    return CalendarIndex(lunar_to_solar=index)
