"""Phát hiện và hợp nhất các file cùng schema bị chia theo kỳ/tháng (FR-011)."""
from __future__ import annotations

import os
import re
from collections import defaultdict

import pandas as pd

from data_loader.models import LoadedTable

_MIN_COMMON_PREFIX_LEN = 3
_PERIOD_SUFFIX_RE = re.compile(r"^[_\-]*\d")

_SHEET_PERIOD_RE = re.compile(
    r"^(?:t\d{1,2}[_\-]\d{4}"              # T01_2025, T02-2025, T7-2025 (không đệm số 0)
    r"|\d{1,2}\.\d{4}"                      # 04.2025
    r"|th[aá]ng\s*\d{1,2}[\s\-]\d{4})$",    # Thang 02 2025 / Tháng 01-2025
    re.IGNORECASE,
)


def _is_period_sheet_name(name: str | None) -> bool:
    return name is not None and bool(_SHEET_PERIOD_RE.match(name.strip()))


def _schema_signature(table: LoadedTable) -> tuple:
    return tuple(sorted(table.frame.columns))


def _is_period_series(stems: list[str], prefix: str) -> bool:
    if len(prefix) < _MIN_COMMON_PREFIX_LEN:
        return False
    return all(_PERIOD_SUFFIX_RE.match(stem[len(prefix):]) for stem in stems)


def _merge_group(group: list[LoadedTable], stem_prefix: str) -> LoadedTable:
    table_name = re.sub(r"[_\-\d]+$", "", stem_prefix) or "data"
    merged_dtypes: dict = {}
    for t in group:
        merged_dtypes.update(t.column_dtypes)
    return LoadedTable(
        source_files=[f for t in group for f in t.source_files],
        sheet_name=group[0].sheet_name,
        table_name=table_name,
        header_confidence="low" if any(t.header_confidence == "low" for t in group) else "high",
        frame=pd.concat([t.frame for t in group], ignore_index=True),
        column_dtypes=merged_dtypes,
    )


def group_same_schema_files(tables: list[LoadedTable]) -> list[LoadedTable]:
    """Gộp các LoadedTable cùng schema thành 1 table UNION khi chia theo kỳ/tháng, theo 1 trong 2
    tín hiệu: (a) hậu tố tên FILE là số liên tiếp (hành vi gốc, FR-011), hoặc (b) tên SHEET của
    CÙNG 1 file khớp pattern kỳ (vd "T01_2025".."T02_2025" trong 1 file duy nhất -- FR-011 mở
    rộng cho sheet). Sheet không khớp pattern kỳ (vd dev_014 "Ghi tắt") giữ riêng, không bị kéo
    vào nhóm gộp dù cùng schema. Table không cùng nhóm thì giữ nguyên. Trả về list mới, không sửa
    input."""
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
        if _is_period_series(stems, prefix):
            result.append(_merge_group(group, prefix))
            continue

        period_members = [t for t in group if _is_period_sheet_name(t.sheet_name)]
        other_members = [t for t in group if not _is_period_sheet_name(t.sheet_name)]
        if len(period_members) >= 2:
            result.append(_merge_group(period_members, prefix))
            result.extend(other_members)
        else:
            result.extend(group)

    return result
