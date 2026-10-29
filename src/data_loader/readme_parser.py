"""Parse README.md của 1 business -> danh sách cột khai báo cho từng file/sheet."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

_SECTION_HEADER_RE = re.compile(
    r"^##\s*Cột trong\s*`([^`]+)`(?:,\s*sheet\s*`([^`]+)`)?\s*$", re.MULTILINE
)
_BULLET_RE = re.compile(r"^-\s*\*\*(.+?)\*\*\s*:", re.MULTILINE)


@dataclass
class FileColumns:
    file_name: str
    sheet_name: str | None
    columns: list[str] = field(default_factory=list)


@dataclass
class ReadmeInfo:
    raw_text: str
    file_columns: list[FileColumns]


def _template_to_regex(template: str) -> re.Pattern:
    """Đổi tên file dạng mẫu trong README (vd 'BanHang_Thang<tháng>_<năm>.xlsx') thành regex."""
    parts = re.split(r"(<[^>]+>)", template)
    pattern = "".join(
        ".+?" if p.startswith("<") and p.endswith(">") else re.escape(p) for p in parts
    )
    return re.compile("^" + pattern + "$")


def parse_readme(readme_path: Path) -> ReadmeInfo:
    text = readme_path.read_text(encoding="utf-8")
    headers = list(_SECTION_HEADER_RE.finditer(text))
    file_columns: list[FileColumns] = []
    for i, m in enumerate(headers):
        file_name, sheet_name = m.group(1), m.group(2)
        start = m.end()
        end = headers[i + 1].start() if i + 1 < len(headers) else len(text)
        section_text = text[start:end]
        columns = _BULLET_RE.findall(section_text)
        file_columns.append(FileColumns(file_name=file_name, sheet_name=sheet_name, columns=columns))
    return ReadmeInfo(raw_text=text, file_columns=file_columns)


def columns_for(readme: ReadmeInfo, file_name: str, sheet_name: str | None) -> list[str] | None:
    """Tìm danh sách cột khai báo khớp đúng file (và sheet nếu có). Trả None nếu không có."""
    for fc in readme.file_columns:
        is_match = fc.file_name == file_name or _template_to_regex(fc.file_name).match(file_name)
        if not is_match:
            continue
        if fc.sheet_name is None or fc.sheet_name == sheet_name:
            return fc.columns
    return None
