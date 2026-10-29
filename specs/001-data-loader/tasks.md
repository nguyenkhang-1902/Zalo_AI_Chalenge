# Tasks: Data Loader & Schema Layer

> REQUIRED SUB-SKILL khi thực thi: `superpowers:subagent-driven-development` (khuyến nghị) hoặc
> `superpowers:executing-plans`. Mỗi task kết thúc bằng bước chạy test thật, không coi "xong" khi
> chưa thấy PASS.

**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

## Global Constraints (áp dụng mọi task)

- Không `business_id`/`question_id` nào trong logic rẽ nhánh (rule 4 cuộc thi) — chỉ dùng trong
  test/golden test.
- Mọi module dưới 250 dòng, 1 trách nhiệm (Điều 5).
- Không phần tử ngẫu nhiên nào trong code (Điều 9) — không `random`, không LLM ở sub-project này.
- Giữ nguyên tiếng Việt có dấu trong tên cột/table (Điều 3) — quote identifier khi ghi SQL.

---

## Phase 1: Setup

### T001 [Setup] Khởi tạo môi trường Python

**Files:**
- Create: `requirements.txt`
- Create: `pytest.ini`
- Create: `src/data_loader/__init__.py`
- Create: `tests/test_setup.py`

- [ ] **Step 1**: Tạo `requirements.txt`

```
duckdb>=1.0
pandas>=2.0
openpyxl>=3.1
pytest>=8.0
```

- [ ] **Step 2**: Tạo venv riêng cho project này (KHÔNG dùng venv của project khác)

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt
```

- [ ] **Step 3**: Tạo `pytest.ini`

```ini
[pytest]
pythonpath = src
```

- [ ] **Step 4**: Tạo `src/data_loader/__init__.py` (file rỗng)

- [ ] **Step 5**: Viết test xác nhận môi trường cài đúng — `tests/test_setup.py`

```python
def test_core_dependencies_importable():
    import duckdb
    import openpyxl
    import pandas

    assert duckdb and openpyxl and pandas
```

- [ ] **Step 6**: Chạy test

Run: `.venv/Scripts/python -m pytest tests/test_setup.py -v`
Expected: PASS

- [ ] **Step 7**: Commit

```bash
git add requirements.txt pytest.ini src/data_loader/__init__.py tests/test_setup.py
git commit -m "chore: scaffold python env for data-loader sub-project"
```

---

## Phase 2: Foundational (các module độc lập — chạy song song được)

### T002 [P] [US1] `models.py` — LoadedTable dùng chung

**Files:**
- Create: `src/data_loader/models.py`

**Interfaces:**
- Produces: `LoadedTable(source_files: list[str], sheet_name: str|None, table_name: str, header_confidence: str, frame: pandas.DataFrame, column_dtypes: dict[str,str])` — mọi module khác dùng class này.

- [ ] **Step 1**: Viết `src/data_loader/models.py`

```python
"""Cấu trúc dữ liệu dùng chung xuyên suốt pipeline data-loader."""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd


@dataclass
class LoadedTable:
    source_files: list[str]
    sheet_name: str | None
    table_name: str
    header_confidence: str  # "high" | "low"
    frame: pd.DataFrame
    column_dtypes: dict = field(default_factory=dict)  # {"col": "numeric"|"date"|"text"|"raw"}
```

- [ ] **Step 2**: Không có test riêng (dataclass thuần, không logic) — để các module sau import và test gián tiếp.

- [ ] **Step 3**: Commit

```bash
git add src/data_loader/models.py
git commit -m "feat(data-loader): add LoadedTable shared dataclass"
```

---

### T003 [P] [US1] `sheet_reader.py` — đọc thô csv/xlsx

**Files:**
- Create: `src/data_loader/sheet_reader.py`
- Test: `tests/data_loader/test_sheet_reader.py`

**Interfaces:**
- Produces: `RawSheet(source_file: str, sheet_name: str|None, rows: list[tuple])`, `read_all_sheets(business_dir: Path) -> list[RawSheet]`

- [ ] **Step 1**: Viết test trước — `tests/data_loader/test_sheet_reader.py`

```python
import csv
from pathlib import Path

import openpyxl

from data_loader.sheet_reader import read_all_sheets


def test_reads_csv_and_xlsx(tmp_path: Path):
    csv_path = tmp_path / "a.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Tên", "Giá"])
        w.writerow(["Cà phê", "20000"])

    xlsx_path = tmp_path / "b.xlsx"
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Sheet1"
    ws.append(["Mã", "Số lượng"])
    ws.append(["SP01", 5])
    wb.create_sheet("Sheet2")
    wb["Sheet2"].append(["X"])
    wb.save(xlsx_path)

    sheets = read_all_sheets(tmp_path)

    assert len(sheets) == 3  # 1 csv + 2 sheet trong xlsx
    csv_sheet = next(s for s in sheets if s.source_file == "a.csv")
    assert csv_sheet.sheet_name is None
    assert csv_sheet.rows == [("Tên", "Giá"), ("Cà phê", "20000")]

    xlsx_sheet1 = next(s for s in sheets if s.source_file == "b.xlsx" and s.sheet_name == "Sheet1")
    assert xlsx_sheet1.rows == [("Mã", "Số lượng"), ("SP01", 5)]
```

- [ ] **Step 2**: Chạy test, xác nhận FAIL (chưa có `sheet_reader.py`)

Run: `.venv/Scripts/python -m pytest tests/data_loader/test_sheet_reader.py -v`
Expected: FAIL với `ModuleNotFoundError`

- [ ] **Step 3**: Viết `src/data_loader/sheet_reader.py`

```python
"""Đọc thô mọi sheet/csv trong 1 thư mục business, chưa xử lý header/kiểu dữ liệu."""
from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

import openpyxl


@dataclass
class RawSheet:
    source_file: str
    sheet_name: str | None
    rows: list[tuple]


def _read_csv(path: Path) -> RawSheet:
    with path.open(encoding="utf-8-sig", newline="") as f:
        rows = [tuple(row) for row in csv.reader(f)]
    return RawSheet(source_file=path.name, sheet_name=None, rows=rows)


def _read_xlsx(path: Path) -> list[RawSheet]:
    wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
    sheets = []
    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        rows = list(ws.iter_rows(values_only=True))
        sheets.append(RawSheet(source_file=path.name, sheet_name=sheet_name, rows=rows))
    wb.close()
    return sheets


def read_all_sheets(business_dir: Path) -> list[RawSheet]:
    """Đọc mọi file .csv/.xlsx trong business_dir, trả về danh sách RawSheet (chưa làm sạch)."""
    result: list[RawSheet] = []
    for path in sorted(business_dir.iterdir()):
        if path.suffix.lower() == ".csv":
            result.append(_read_csv(path))
        elif path.suffix.lower() == ".xlsx":
            result.extend(_read_xlsx(path))
    return result
```

- [ ] **Step 4**: Chạy lại test

Run: `.venv/Scripts/python -m pytest tests/data_loader/test_sheet_reader.py -v`
Expected: PASS

- [ ] **Step 5**: Commit

```bash
git add src/data_loader/sheet_reader.py tests/data_loader/test_sheet_reader.py
git commit -m "feat(data-loader): read raw rows from csv/xlsx files"
```

---

### T004 [P] [US1] `readme_parser.py` — parse README.md

**Files:**
- Create: `src/data_loader/readme_parser.py`
- Test: `tests/data_loader/test_readme_parser.py`

**Interfaces:**
- Produces: `ReadmeInfo(raw_text: str, file_columns: list[FileColumns])`, `parse_readme(path: Path) -> ReadmeInfo`, `columns_for(readme: ReadmeInfo, file_name: str, sheet_name: str|None) -> list[str]|None`

- [ ] **Step 1**: Viết test trước — `tests/data_loader/test_readme_parser.py`

```python
from pathlib import Path

from data_loader.readme_parser import columns_for, parse_readme

README_TEXT = """# Dữ liệu biz_129

## File
- `don_hang.csv` (csv)

## Cột trong `don_hang.csv`
- **Hình thức thanh toán**: hình thức thanh toán của đơn
- **Số phiếu**: mã đơn

## Cột trong `BanHang_Thang<tháng>_<năm>.xlsx`, sheet `DonHang_ChiTiet`
- **Mã đơn hàng**: mã đơn
- **Tổng tiền**: thành tiền

## Quy ước
- Dữ liệu có đến hết 14/08/2026.
"""


def test_parses_simple_and_templated_sections(tmp_path: Path):
    readme_path = tmp_path / "README.md"
    readme_path.write_text(README_TEXT, encoding="utf-8")

    info = parse_readme(readme_path)

    assert columns_for(info, "don_hang.csv", None) == ["Hình thức thanh toán", "Số phiếu"]
    assert columns_for(info, "BanHang_Thang01_2025.xlsx", "DonHang_ChiTiet") == [
        "Mã đơn hàng",
        "Tổng tiền",
    ]
    assert columns_for(info, "BanHang_Thang01_2025.xlsx", "SheetKhác") is None
    assert columns_for(info, "khong_ton_tai.csv", None) is None
```

- [ ] **Step 2**: Chạy test, xác nhận FAIL

Run: `.venv/Scripts/python -m pytest tests/data_loader/test_readme_parser.py -v`
Expected: FAIL với `ModuleNotFoundError`

- [ ] **Step 3**: Viết `src/data_loader/readme_parser.py`

```python
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
```

- [ ] **Step 4**: Chạy lại test

Run: `.venv/Scripts/python -m pytest tests/data_loader/test_readme_parser.py -v`
Expected: PASS

- [ ] **Step 5**: Commit

```bash
git add src/data_loader/readme_parser.py tests/data_loader/test_readme_parser.py
git commit -m "feat(data-loader): parse README.md column declarations"
```

---

### T005 [P] [US1] `header_locator.py` — định vị dòng header thật

**Files:**
- Create: `src/data_loader/header_locator.py`
- Test: `tests/data_loader/test_header_locator.py`

**Interfaces:**
- Produces: `HeaderMatch(header_row_index: int, confidence: str)`, `locate_header(rows: list[tuple], expected_columns: list[str]|None, max_scan_rows: int = 15) -> HeaderMatch`

- [ ] **Step 1**: Viết test trước — `tests/data_loader/test_header_locator.py`

```python
from data_loader.header_locator import locate_header


def test_finds_header_after_junk_rows_using_readme_columns():
    rows = [
        ("BẢNG KÊ PHIẾU GIAO HÀNG", None, None),
        ("Kỳ báo cáo: toàn bộ", None, None),
        (None, None, None),
        ("Ngày giao hàng", "Mã đơn hàng", "Số lượng giao"),
        ("02/02/2025", "ORD000002", 1),
    ]
    expected_columns = ["Ngày giao hàng", "Mã đơn hàng", "Số lượng giao"]

    match = locate_header(rows, expected_columns)

    assert match.header_row_index == 3
    assert match.confidence == "high"


def test_falls_back_to_heuristic_when_no_readme_columns():
    rows = [
        ("Tên", "Giá"),
        ("Cà phê", 20000),
    ]

    match = locate_header(rows, expected_columns=None)

    assert match.header_row_index == 0
    assert match.confidence == "low"
```

- [ ] **Step 2**: Chạy test, xác nhận FAIL

Run: `.venv/Scripts/python -m pytest tests/data_loader/test_header_locator.py -v`
Expected: FAIL với `ModuleNotFoundError`

- [ ] **Step 3**: Viết `src/data_loader/header_locator.py`

```python
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
```

- [ ] **Step 4**: Chạy lại test

Run: `.venv/Scripts/python -m pytest tests/data_loader/test_header_locator.py -v`
Expected: PASS

- [ ] **Step 5**: Commit

```bash
git add src/data_loader/header_locator.py tests/data_loader/test_header_locator.py
git commit -m "feat(data-loader): locate real header row using readme hints"
```

---

### T006 [P] [US1] `value_cleaner.py` — làm sạch số/ngày/số lượng-đơn vị

**Files:**
- Create: `src/data_loader/value_cleaner.py`
- Test: `tests/data_loader/test_value_cleaner.py`

**Interfaces:**
- Produces: `clean_numeric_column(values: list) -> tuple[list, str]`, `split_quantity_unit(values: list) -> tuple[list, list] | None`, `parse_vn_date_column(values: list) -> tuple[list, str]`

- [ ] **Step 1**: Viết test trước — `tests/data_loader/test_value_cleaner.py`

```python
from data_loader.value_cleaner import (
    clean_numeric_column,
    parse_vn_date_column,
    split_quantity_unit,
)


def test_clean_numeric_column_handles_thousand_separator_mixed_with_plain_number():
    values = [42000, "51,000", "45000", None]

    cleaned, dtype = clean_numeric_column(values)

    assert dtype == "numeric"
    assert cleaned == [42000.0, 51000.0, 45000.0, None]


def test_clean_numeric_column_falls_back_to_raw_when_mostly_non_numeric():
    values = ["Đã hoàn thành", "Đã huỷ", "Đang giao"]

    cleaned, dtype = clean_numeric_column(values)

    assert dtype == "raw"
    assert cleaned == values


def test_split_quantity_unit_extracts_number_and_unit_when_majority_match():
    values = ["1 kg", "2 cái", 5, None]

    result = split_quantity_unit(values)

    assert result is not None
    numbers, units = result
    assert numbers == [1.0, 2.0, 5.0, None]
    assert units == ["kg", "cái", None, None]


def test_split_quantity_unit_returns_none_when_pattern_is_rare():
    values = [1, 2, 3, "1 kg"]

    assert split_quantity_unit(values) is None


def test_parse_vn_date_column_converts_to_iso():
    values = ["01/04/2025", "31/05/2025", None]

    cleaned, dtype = parse_vn_date_column(values)

    assert dtype == "date"
    assert cleaned == ["2025-04-01", "2025-05-31", None]
```

- [ ] **Step 2**: Chạy test, xác nhận FAIL

Run: `.venv/Scripts/python -m pytest tests/data_loader/test_value_cleaner.py -v`
Expected: FAIL với `ModuleNotFoundError`

- [ ] **Step 3**: Viết `src/data_loader/value_cleaner.py`

```python
"""Rule thuần làm sạch giá trị cột: số có dấu phẩy ngăn nghìn, số lượng kèm đơn vị, ngày VN."""
from __future__ import annotations

import re
from datetime import date, datetime

_NUMERIC_RE = re.compile(r"^-?\d[\d,]*\.?\d*$")
_QTY_UNIT_RE = re.compile(r"^(\d+(?:\.\d+)?)\s*(\D+)$")
_DATE_FORMATS = ("%d/%m/%Y", "%Y-%m-%d")
_RAW_RATIO_THRESHOLD = 0.9
_QTY_UNIT_MATCH_THRESHOLD = 0.5


def _to_number(value) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text:
        return None
    if _NUMERIC_RE.match(text):
        return float(text.replace(",", ""))
    return None


def clean_numeric_column(values: list) -> tuple[list, str]:
    non_null = [v for v in values if v is not None and str(v).strip() != ""]
    if not non_null:
        return list(values), "raw"
    parsed = [_to_number(v) for v in non_null]
    ok_ratio = sum(p is not None for p in parsed) / len(non_null)
    if ok_ratio < _RAW_RATIO_THRESHOLD:
        return list(values), "raw"
    return [_to_number(v) for v in values], "numeric"


def split_quantity_unit(values: list) -> tuple[list, list] | None:
    non_null = [v for v in values if v is not None and str(v).strip() != ""]
    if not non_null:
        return None
    matched = sum(
        1
        for v in non_null
        if not isinstance(v, (int, float)) and _QTY_UNIT_RE.match(str(v).strip())
    )
    if matched / len(non_null) < _QTY_UNIT_MATCH_THRESHOLD:
        return None

    numbers, units = [], []
    for v in values:
        if v is None or str(v).strip() == "":
            numbers.append(None)
            units.append(None)
        elif isinstance(v, (int, float)):
            numbers.append(float(v))
            units.append(None)
        else:
            m = _QTY_UNIT_RE.match(str(v).strip())
            if m:
                numbers.append(float(m.group(1)))
                units.append(m.group(2).strip())
            else:
                numbers.append(None)
                units.append(None)
    return numbers, units


def parse_vn_date_column(values: list) -> tuple[list, str]:
    non_null = [v for v in values if v is not None and str(v).strip() != ""]
    if not non_null:
        return list(values), "raw"

    def _parse_one(v) -> date | None:
        if isinstance(v, datetime):
            return v.date()
        if isinstance(v, date):
            return v
        text = str(v).strip()
        for fmt in _DATE_FORMATS:
            try:
                return datetime.strptime(text, fmt).date()
            except ValueError:
                continue
        return None

    parsed = [_parse_one(v) for v in non_null]
    ok_ratio = sum(p is not None for p in parsed) / len(non_null)
    if ok_ratio < _RAW_RATIO_THRESHOLD:
        return list(values), "raw"

    result = []
    for v in values:
        if v is None or str(v).strip() == "":
            result.append(None)
        else:
            parsed_v = _parse_one(v)
            result.append(parsed_v.isoformat() if parsed_v else None)
    return result, "date"
```

- [ ] **Step 4**: Chạy lại test

Run: `.venv/Scripts/python -m pytest tests/data_loader/test_value_cleaner.py -v`
Expected: PASS (5 test)

- [ ] **Step 5**: Commit

```bash
git add src/data_loader/value_cleaner.py tests/data_loader/test_value_cleaner.py
git commit -m "feat(data-loader): generic numeric/date/quantity-unit cleaning rules"
```

---

### T007 [P] [US1] `schema_grouping.py` — FR-011: gộp file cùng schema chia theo kỳ

**Files:**
- Create: `src/data_loader/schema_grouping.py`
- Test: `tests/data_loader/test_schema_grouping.py`

**Interfaces:**
- Consumes: `LoadedTable` (từ `models.py`, Task T002)
- Produces: `group_same_schema_files(tables: list[LoadedTable]) -> list[LoadedTable]`

⚠️ **Quan trọng**: chỉ gộp khi phần đuôi tên file (sau tiền tố chung) là **số** (kiểu `_Thang01_2025`,
`_T1_2025`...) — KHÔNG gộp chỉ vì 2 file cùng schema + cùng tiền tố chữ (vd `DanhSachKhachA.csv` và
`DanhSachNhaCungCap.csv` đều bắt đầu `DanhSach` nhưng là 2 bảng khác nhau). Xem test thứ 2 bên dưới.

- [ ] **Step 1**: Viết test trước — `tests/data_loader/test_schema_grouping.py`

```python
import pandas as pd

from data_loader.models import LoadedTable
from data_loader.schema_grouping import group_same_schema_files


def _table(source_file: str, data: dict) -> LoadedTable:
    return LoadedTable(
        source_files=[source_file],
        sheet_name=None,
        table_name=source_file.rsplit(".", 1)[0],
        header_confidence="high",
        frame=pd.DataFrame(data),
    )


def test_groups_monthly_files_with_same_schema_and_numeric_suffix():
    jan = _table("BanHang_Thang01_2025.xlsx", {"Mã đơn": ["A1"], "Tổng tiền": [1000]})
    feb = _table("BanHang_Thang02_2025.xlsx", {"Mã đơn": ["B1"], "Tổng tiền": [2000]})
    danh_muc = _table("DanhMuc.xlsx", {"Mã hàng": ["SP1"], "Tên": ["Cà phê"]})

    result = group_same_schema_files([jan, feb, danh_muc])

    assert len(result) == 2
    merged = next(t for t in result if len(t.source_files) == 2)
    assert set(merged.source_files) == {"BanHang_Thang01_2025.xlsx", "BanHang_Thang02_2025.xlsx"}
    assert len(merged.frame) == 2
    assert merged.table_name.startswith("BanHang")
    standalone = next(t for t in result if len(t.source_files) == 1)
    assert standalone.table_name == "DanhMuc"


def test_does_not_group_same_schema_with_unrelated_text_suffix():
    a = _table("DanhSachKhachA.csv", {"Tên": ["X"], "SDT": ["0900"]})
    b = _table("DanhSachNhaCungCap.csv", {"Tên": ["Y"], "SDT": ["0911"]})

    result = group_same_schema_files([a, b])

    assert len(result) == 2  # đuôi tên không phải số -> không gộp nhầm
```

- [ ] **Step 2**: Chạy test, xác nhận FAIL

Run: `.venv/Scripts/python -m pytest tests/data_loader/test_schema_grouping.py -v`
Expected: FAIL với `ModuleNotFoundError`

- [ ] **Step 3**: Viết `src/data_loader/schema_grouping.py`

```python
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
```

- [ ] **Step 4**: Chạy lại test

Run: `.venv/Scripts/python -m pytest tests/data_loader/test_schema_grouping.py -v`
Expected: PASS (2 test)

- [ ] **Step 5**: Commit

```bash
git add src/data_loader/schema_grouping.py tests/data_loader/test_schema_grouping.py
git commit -m "feat(data-loader): union same-schema files split by period (FR-011)"
```

---

### T008 [P] [US1] `schema_summary.py` — sinh JSON tóm tắt schema

**Files:**
- Create: `src/data_loader/schema_summary.py`
- Test: `tests/data_loader/test_schema_summary.py`

**Interfaces:**
- Consumes: `LoadedTable` (từ `models.py`)
- Produces: `summarize_business(business_id: str, tables: list[LoadedTable], readme_raw: str) -> dict`

- [ ] **Step 1**: Viết test trước — `tests/data_loader/test_schema_summary.py`

```python
import pandas as pd

from data_loader.models import LoadedTable
from data_loader.schema_summary import summarize_business


def test_summarize_business_reports_dtype_and_samples():
    table = LoadedTable(
        source_files=["a.csv"],
        sheet_name=None,
        table_name="a",
        header_confidence="high",
        frame=pd.DataFrame({"Tổng tiền": [1000.0, 2000.0, None]}),
        column_dtypes={"Tổng tiền": "numeric"},
    )

    summary = summarize_business("biz_test", [table], readme_raw="# readme")

    assert summary["business_id"] == "biz_test"
    assert summary["readme"] == "# readme"
    col = summary["tables"][0]["columns"][0]
    assert col["name"] == "Tổng tiền"
    assert col["dtype"] == "numeric"
    assert col["n_null"] == 1
    assert col["n_rows"] == 3
    assert col["sample_values"] == [1000.0, 2000.0]
```

- [ ] **Step 2**: Chạy test, xác nhận FAIL

Run: `.venv/Scripts/python -m pytest tests/data_loader/test_schema_summary.py -v`
Expected: FAIL với `ModuleNotFoundError`

- [ ] **Step 3**: Viết `src/data_loader/schema_summary.py`

```python
"""Sinh bản tóm tắt schema (cột/kiểu/mẫu) cho mỗi table, để sub-project sau dùng xây prompt."""
from __future__ import annotations

from data_loader.models import LoadedTable

_SAMPLE_SIZE = 5


def summarize_table(table: LoadedTable) -> dict:
    frame = table.frame
    columns = []
    for col in frame.columns:
        series = frame[col]
        non_null = series.dropna()
        columns.append(
            {
                "name": col,
                "dtype": table.column_dtypes.get(col, "text"),
                "n_null": int(series.isna().sum()),
                "n_rows": int(len(series)),
                "sample_values": non_null.head(_SAMPLE_SIZE).tolist(),
            }
        )
    return {
        "table_name": table.table_name,
        "source_files": table.source_files,
        "header_confidence": table.header_confidence,
        "columns": columns,
    }


def summarize_business(business_id: str, tables: list[LoadedTable], readme_raw: str) -> dict:
    return {
        "business_id": business_id,
        "readme": readme_raw,
        "tables": [summarize_table(t) for t in tables],
    }
```

- [ ] **Step 4**: Chạy lại test

Run: `.venv/Scripts/python -m pytest tests/data_loader/test_schema_summary.py -v`
Expected: PASS

- [ ] **Step 5**: Commit

```bash
git add src/data_loader/schema_summary.py tests/data_loader/test_schema_summary.py
git commit -m "feat(data-loader): build per-business schema summary json"
```

---

### T009 [P] [US1] `duckdb_writer.py` — ghi DuckDB

**Files:**
- Create: `src/data_loader/duckdb_writer.py`
- Test: `tests/data_loader/test_duckdb_writer.py`

**Interfaces:**
- Consumes: `LoadedTable` (từ `models.py`)
- Produces: `write_tables(db_path: Path, tables: list[LoadedTable]) -> None`

- [ ] **Step 1**: Viết test trước — `tests/data_loader/test_duckdb_writer.py`

```python
from pathlib import Path

import duckdb
import pandas as pd

from data_loader.duckdb_writer import write_tables
from data_loader.models import LoadedTable


def test_writes_and_overwrites_tables_idempotently(tmp_path: Path):
    db_path = tmp_path / "biz.duckdb"
    table = LoadedTable(
        source_files=["a.csv"],
        sheet_name=None,
        table_name="Khách hàng",
        header_confidence="high",
        frame=pd.DataFrame({"Tên": ["An", "Bình"]}),
    )

    write_tables(db_path, [table])
    write_tables(db_path, [table])  # chạy lại -> không được nhân đôi dòng

    con = duckdb.connect(str(db_path))
    rows = con.execute('SELECT "Tên" FROM "Khách hàng" ORDER BY "Tên"').fetchall()
    con.close()

    assert rows == [("An",), ("Bình",)]
```

- [ ] **Step 2**: Chạy test, xác nhận FAIL

Run: `.venv/Scripts/python -m pytest tests/data_loader/test_duckdb_writer.py -v`
Expected: FAIL với `ModuleNotFoundError`

- [ ] **Step 3**: Viết `src/data_loader/duckdb_writer.py`

```python
"""Ghi các LoadedTable đã làm sạch vào 1 file DuckDB (ghi đè sạch mỗi lần chạy)."""
from __future__ import annotations

from pathlib import Path

import duckdb

from data_loader.models import LoadedTable


def _quote_ident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def write_tables(db_path: Path, tables: list[LoadedTable]) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()
    con = duckdb.connect(str(db_path))
    try:
        for table in tables:
            con.register("tmp_df", table.frame)
            con.execute(f"CREATE TABLE {_quote_ident(table.table_name)} AS SELECT * FROM tmp_df")
            con.unregister("tmp_df")
    finally:
        con.close()
```

- [ ] **Step 4**: Chạy lại test

Run: `.venv/Scripts/python -m pytest tests/data_loader/test_duckdb_writer.py -v`
Expected: PASS

- [ ] **Step 5**: Commit

```bash
git add src/data_loader/duckdb_writer.py tests/data_loader/test_duckdb_writer.py
git commit -m "feat(data-loader): write cleaned tables to duckdb, overwrite on rerun"
```

---

## Phase 3: Integration (phụ thuộc toàn bộ Phase 2 — không chạy song song)

### T010 [US1] `build_business_db.py` — orchestrator 1 business + golden test trên dữ liệu thật

**Files:**
- Create: `src/data_loader/build_business_db.py`
- Test: `tests/data_loader/test_build_business_db_golden.py`

**Interfaces:**
- Consumes: mọi module T002-T009 (`models`, `sheet_reader`, `readme_parser`, `header_locator`, `value_cleaner`, `schema_grouping`, `schema_summary`, `duckdb_writer`)
- Produces: `build_business(business_dir: Path, out_dir: Path) -> dict` (trả schema summary dict, đồng thời ghi `{out_dir}/{business_id}.duckdb` + `{out_dir}/{business_id}.schema.json`)

⚠️ Đây là **golden test chạy trên dữ liệu thật** của BTC (`train/data/biz_105`,
`public_test/data/dev_005`) — cần thư mục `train/` và `public_test/` đã có ở gốc repo (đã có từ
lúc brainstorm, xem `TIEN_DO.md`). Không dùng fixture giả cho bước này vì mục tiêu là xác nhận
pipeline chạy đúng trên dữ liệu thật, không phải chỉ đúng với input lý tưởng tự tạo.

- [ ] **Step 1**: Viết test trước — `tests/data_loader/test_build_business_db_golden.py`

```python
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
    assert len(merged["source_files"]) >= 12  # gộp được phần lớn 17 file BanHang_Thang..


def test_rerun_is_idempotent(tmp_path: Path):
    business_dir = PROJECT_ROOT / "train" / "data" / "biz_105"

    first = build_business(business_dir, tmp_path)
    second = build_business(business_dir, tmp_path)

    assert first == second  # SC-004: chạy lại ra kết quả giống nhau 100%


def test_one_broken_file_does_not_crash_other_tables(tmp_path: Path):
    """Acceptance scenario 5: 1 file hỏng -> business vẫn ra table của file tốt, không crash."""
    business_dir = tmp_path / "biz_broken"
    business_dir.mkdir()
    (business_dir / "good.csv").write_text("A,B\n1,2\n3,4\n", encoding="utf-8")
    # "bad.csv" có dòng số cột không khớp header -> ép pandas raise lỗi khi dựng DataFrame
    (business_dir / "bad.csv").write_text("A,B\n1,2,3\n4,5\n", encoding="utf-8")

    summary = build_business(business_dir, tmp_path / "out")

    table_names = [t["table_name"] for t in summary["tables"]]
    assert "good" in table_names
    assert "bad" not in table_names  # bị bỏ qua, không làm hỏng cả business
```

- [ ] **Step 2**: Chạy test, xác nhận FAIL

Run: `.venv/Scripts/python -m pytest tests/data_loader/test_build_business_db_golden.py -v`
Expected: FAIL với `ModuleNotFoundError`

- [ ] **Step 3**: Viết `src/data_loader/build_business_db.py`

```python
"""Orchestrator: README -> header locate -> clean -> group -> DuckDB + schema summary, 1 business."""
from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

import pandas as pd

from data_loader.duckdb_writer import write_tables
from data_loader.header_locator import locate_header
from data_loader.models import LoadedTable
from data_loader.readme_parser import ReadmeInfo, columns_for, parse_readme
from data_loader.schema_grouping import group_same_schema_files
from data_loader.schema_summary import summarize_business
from data_loader.sheet_reader import RawSheet, read_all_sheets
from data_loader.value_cleaner import (
    clean_numeric_column,
    parse_vn_date_column,
    split_quantity_unit,
)

logger = logging.getLogger(__name__)


def _clean_sheet_to_table(raw_sheet: RawSheet, expected_columns: list[str] | None) -> LoadedTable | None:
    match = locate_header(raw_sheet.rows, expected_columns)
    header_row = raw_sheet.rows[match.header_row_index]
    data_rows = raw_sheet.rows[match.header_row_index + 1 :]
    if not data_rows:
        return None

    header = [str(c).strip() if c is not None else f"col_{i}" for i, c in enumerate(header_row)]
    frame = pd.DataFrame(data_rows, columns=header)
    column_dtypes: dict[str, str] = {}

    for col in list(frame.columns):
        values = frame[col].tolist()

        split = split_quantity_unit(values)
        if split is not None:
            numbers, units = split
            frame[col] = numbers
            frame[f"{col} (đơn vị)"] = units
            column_dtypes[col] = "numeric"
            column_dtypes[f"{col} (đơn vị)"] = "text"
            continue

        cleaned, dtype = clean_numeric_column(values)
        if dtype == "numeric":
            frame[col] = cleaned
            column_dtypes[col] = "numeric"
            continue

        cleaned, dtype = parse_vn_date_column(values)
        if dtype == "date":
            frame[col] = cleaned
            column_dtypes[col] = "date"
        else:
            column_dtypes[col] = "raw"

    table_name = raw_sheet.source_file.rsplit(".", 1)[0]
    if raw_sheet.sheet_name:
        table_name = f"{table_name}__{raw_sheet.sheet_name}"

    return LoadedTable(
        source_files=[raw_sheet.source_file],
        sheet_name=raw_sheet.sheet_name,
        table_name=table_name,
        header_confidence=match.confidence,
        frame=frame,
        column_dtypes=column_dtypes,
    )


def build_business(business_dir: Path, out_dir: Path) -> dict:
    business_id = business_dir.name
    readme_path = business_dir / "README.md"
    readme: ReadmeInfo | None = parse_readme(readme_path) if readme_path.exists() else None

    tables: list[LoadedTable] = []
    for raw_sheet in read_all_sheets(business_dir):
        expected = (
            columns_for(readme, raw_sheet.source_file, raw_sheet.sheet_name) if readme else None
        )
        try:
            table = _clean_sheet_to_table(raw_sheet, expected)
            if table is not None:
                tables.append(table)
        except Exception:
            logger.warning(
                "Bỏ qua %s (sheet=%s) của %s do lỗi parse",
                raw_sheet.source_file,
                raw_sheet.sheet_name,
                business_id,
                exc_info=True,
            )

    tables = group_same_schema_files(tables)

    out_dir.mkdir(parents=True, exist_ok=True)
    write_tables(out_dir / f"{business_id}.duckdb", tables)

    readme_raw = readme.raw_text if readme else ""
    summary = summarize_business(business_id, tables, readme_raw)
    (out_dir / f"{business_id}.schema.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--biz-dir", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    build_business(args.biz_dir, args.out)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4**: Chạy lại test

Run: `.venv/Scripts/python -m pytest tests/data_loader/test_build_business_db_golden.py -v`
Expected: PASS (4 test). Nếu `test_merges_monthly_files_for_dev_005` fail vì số file gộp được
ít hơn 12 — kiểm tra lại README `dev_005` có đúng 17 file `BanHang_Thang..` cùng cột hay README
đã đổi (dataset có thể cập nhật).

- [ ] **Step 5**: Commit

```bash
git add src/data_loader/build_business_db.py tests/data_loader/test_build_business_db_golden.py
git commit -m "feat(data-loader): wire full pipeline for a single business, verify on real data"
```

---

### T011 [US1] `build_all.py` — batch runner toàn dataset + golden test SC-001/SC-003

**Files:**
- Create: `src/data_loader/build_all.py`
- Test: `tests/data_loader/test_build_all_golden.py`

**Interfaces:**
- Consumes: `build_business` (từ T010)
- Produces: `build_all(dataset_dir: Path, out_dir: Path) -> dict[str, str]` (map `business_id -> "ok"|"failed"`)

🎯 **Checkpoint của sub-project 001-data-loader**: sau task này, chạy
`python -m data_loader.build_all --dataset-dir train --out build_output` phải ra `.duckdb` +
`.schema.json` cho cả 30 business, không business nào "failed", dưới 2 phút — đúng SC-001/SC-003
của spec.

- [ ] **Step 1**: Viết test trước — `tests/data_loader/test_build_all_golden.py`

```python
"""Golden test: chạy loader cho TOÀN BỘ train/ thật, kiểm SC-001 (không crash) + SC-003 (<2 phút)."""
import time
from pathlib import Path

from data_loader.build_all import build_all

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_builds_entire_train_dataset_within_time_budget(tmp_path: Path):
    train_dir = PROJECT_ROOT / "train"
    assert train_dir.exists(), "Cần có dữ liệu thật train/ ở gốc repo"

    start = time.monotonic()
    results = build_all(train_dir, tmp_path)
    elapsed = time.monotonic() - start

    assert len(results) == 30
    failed = [biz for biz, status in results.items() if status == "failed"]
    assert failed == [], f"Business thất bại hoàn toàn: {failed}"  # SC-001
    assert elapsed < 120, f"Quá thời gian cho phép: {elapsed:.1f}s"  # SC-003

    assert (tmp_path / "rulebook.md").exists()
    assert (tmp_path / "calendar.csv").exists()
```

- [ ] **Step 2**: Chạy test, xác nhận FAIL

Run: `.venv/Scripts/python -m pytest tests/data_loader/test_build_all_golden.py -v`
Expected: FAIL với `ModuleNotFoundError`

- [ ] **Step 3**: Viết `src/data_loader/build_all.py`

```python
"""Chạy loader cho toàn bộ business trong 1 dataset (train/ hoặc public_test/),
copy kèm rulebook.md + calendar.csv (FR-013) vào cùng chỗ output."""
from __future__ import annotations

import argparse
import logging
import shutil
import time
from pathlib import Path

from data_loader.build_business_db import build_business

logger = logging.getLogger(__name__)


def build_all(dataset_dir: Path, out_dir: Path) -> dict[str, str]:
    out_dir.mkdir(parents=True, exist_ok=True)

    for shared_file in ("rulebook.md", "calendar.csv"):
        src = dataset_dir / shared_file
        if src.exists():
            shutil.copy(src, out_dir / shared_file)

    results: dict[str, str] = {}
    start = time.monotonic()
    for business_dir in sorted((dataset_dir / "data").iterdir()):
        if not business_dir.is_dir():
            continue
        try:
            build_business(business_dir, out_dir)
            results[business_dir.name] = "ok"
        except Exception:
            logger.error("Business %s thất bại hoàn toàn", business_dir.name, exc_info=True)
            results[business_dir.name] = "failed"
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
```

- [ ] **Step 4**: Chạy lại test

Run: `.venv/Scripts/python -m pytest tests/data_loader/test_build_all_golden.py -v`
Expected: PASS

- [ ] **Step 5**: Chạy toàn bộ test suite của sub-project để xác nhận không có gì vỡ

Run: `.venv/Scripts/python -m pytest tests/ -v`
Expected: tất cả PASS (19 test: 1 setup + 1 sheet_reader + 1 readme_parser + 2 header_locator +
5 value_cleaner + 2 schema_grouping + 1 schema_summary + 1 duckdb_writer + 4 build_business_db +
1 build_all)

- [ ] **Step 6**: Commit

```bash
git add src/data_loader/build_all.py tests/data_loader/test_build_all_golden.py
git commit -m "feat(data-loader): batch-build whole dataset, copy rulebook/calendar passthrough"
```

---

## 🟡 Polish / Để sau (không chặn checkpoint trên)

- [ ] T012 `[P]` **(SHOULD-012, deferred)** Phát hiện khoá liên kết khả dĩ giữa table khác schema
  (so độ phủ giá trị giữa các cột) — chỉ làm nếu còn thời gian trước 16/11. Không có task chi
  tiết ở đây theo đúng tinh thần YAGNI; brainstorm riêng khi tới lúc.
- [ ] T013 Chạy thử `build_all` trên `public_test/` (14 business) — không có success-criteria số
  cứng (spec chỉ yêu cầu `train/`), nhưng nên chạy 1 lần thủ công để soát thêm edge case trước khi
  sang `002-date-calendar-resolver`.
