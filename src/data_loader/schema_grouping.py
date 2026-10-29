"""Phát hiện và hợp nhất các file cùng schema bị chia theo kỳ/tháng (FR-011)."""
from __future__ import annotations

import os
import re
from collections import defaultdict

import pandas as pd

from data_loader.models import LoadedTable

_MIN_COMMON_PREFIX_LEN = 3
_PERIOD_SUFFIX_RE = re.compile(r"^[_\-]*\d")


def _schema_signature(table: LoadedTable) -> tuple:
    return tuple(sorted(table.frame.columns))


def _is_period_series(stems: list[str], prefix: str) -> bool:
    if len(prefix) < _MIN_COMMON_PREFIX_LEN:
        return False
    return all(_PERIOD_SUFFIX_RE.match(stem[len(prefix):]) for stem in stems)


def group_same_schema_files(tables: list[LoadedTable]) -> list[LoadedTable]:
    """Gộp các LoadedTable cùng schema + đuôi tên file là số (chuỗi theo kỳ) thành 1 table UNION.
    Table không cùng nhóm thì giữ nguyên. Trả về list mới, không sửa input."""
    by_signature: dict[tuple, list[LoadedTable]] = defaultdict(list)
    for t in tables:
        by_signature[_schema_signature(t)].append(t)

    result: list[LoadedTable] = []
    for group in by_signature.values():
        if len(group) == 1:
            result.append(group[0])
            continue

        stems = [os.path.splitext(f)[0] for t in group for f in t.source_files]
        prefix = os.path.commonprefix(stems)
        if not _is_period_series(stems, prefix):
            result.extend(group)
            continue

        table_name = re.sub(r"[_\-\d]+$", "", prefix) or "data"
        result.append(
            LoadedTable(
                source_files=[f for t in group for f in t.source_files],
                sheet_name=group[0].sheet_name,
                table_name=table_name,
                header_confidence="low" if any(t.header_confidence == "low" for t in group) else "high",
                frame=pd.concat([t.frame for t in group], ignore_index=True),
            )
        )
    return result
