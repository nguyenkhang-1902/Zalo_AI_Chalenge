"""Tự định vị dòng header thật trong 1 sheet thô, dựa vào tên cột khai báo ở README (nếu có)."""
from __future__ import annotations

from dataclasses import dataclass

_MATCH_THRESHOLD = 0.6


@dataclass
class HeaderMatch:
    header_row_index: int
    confidence: str  # "high" | "low"


def _normalize(cell) -> str:
    return str(cell).strip().lower() if cell is not None else ""


def locate_header(
    rows: list[tuple], expected_columns: list[str] | None, max_scan_rows: int = 15
) -> HeaderMatch:
    if not rows:
        return HeaderMatch(header_row_index=0, confidence="low")

    if expected_columns:
        expected_norm = {_normalize(c) for c in expected_columns}
        best_index, best_score = 0, -1.0
        for i, row in enumerate(rows[:max_scan_rows]):
            row_norm = {_normalize(c) for c in row if c is not None}
            score = len(row_norm & expected_norm) / len(expected_norm)
            if score > best_score:
                best_index, best_score = i, score
        if best_score >= _MATCH_THRESHOLD:
            return HeaderMatch(header_row_index=best_index, confidence="high")

    # Fallback: dòng đầu tiên mà mọi cell không rỗng đều là chuỗi (không phải số/None)
    for i, row in enumerate(rows[:max_scan_rows]):
        non_empty = [c for c in row if c is not None and str(c).strip() != ""]
        if non_empty and all(isinstance(c, str) for c in non_empty):
            return HeaderMatch(header_row_index=i, confidence="low")

    return HeaderMatch(header_row_index=0, confidence="low")
