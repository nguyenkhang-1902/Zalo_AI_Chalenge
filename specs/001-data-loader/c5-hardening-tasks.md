# C5 Hardening — 001-data-loader Tasks

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans. Plan: `specs/001-data-loader/c5-hardening-plan.md`
> (đọc cả Global Constraints + bảng 8 Finding trước khi bắt đầu).

---

### Task 1: T001 `value_cleaner.py` — giữ giờ trong ngày + trả object date/datetime thật (Finding #1+#2)

**Files:**
- Modify: `src/data_loader/value_cleaner.py:124-154` (`parse_vn_date_column`)
- Modify: `src/data_loader/build_business_db.py:80-85` (`_apply_value_cleaning`'s dispatch cho
  dtype trả về từ `parse_vn_date_column`)
- Test: `tests/data_loader/test_value_cleaner.py`
- Test: `tests/data_loader/test_build_business_db.py` (dtype dispatch không đổi hành vi cột
  date-only đã có test)

**Interfaces:**
- Consumes: không có (hàm thuần, không phụ thuộc task khác).
- Produces: `parse_vn_date_column(values: list) -> tuple[list, str]` — **THAY ĐỔI HỢP ĐỒNG**:
  dtype trả về là `"date"` (giữ nguyên, cho cột chỉ có ngày) HOẶC **`"datetime"` (MỚI)** khi cột
  có ít nhất 1 giá trị mang giờ/phút/giây thật khác 0; giá trị trong list trả về là object
  `datetime.date`/`datetime.datetime` THẬT (không còn `.isoformat()` string). `build_business_db.py`'s
  `_apply_value_cleaning` phải nhận biết CẢ 2 dtype này (Task 4/5 không đụng vùng code này, an toàn).

- [ ] **Step 1: Đọc lại 2 test hiện có sẽ bị ảnh hưởng, để biết chính xác assert cần đổi**

Đọc `tests/data_loader/test_value_cleaner.py` dòng 84-90 (`test_parse_vn_date_column_converts_to_iso`)
và `tests/data_loader/test_build_business_db.py` dòng 13-29
(`test_value_cleaning_treats_pandas_nan_and_nat_as_missing`). Dòng 84-90 SẼ phải sửa (assert cũ
check ra string ISO, không còn đúng sau fix). Dòng 13-29 KHÔNG cần sửa gì (cột "Ngày" trong test đó
toàn giá trị `datetime(2025,1,2)`/`datetime(2025,1,3)` không có giờ thật (00:00:00) — sau fix vẫn
phải ra dtype `"date"` với giá trị là `date` object, test hiện tại chỉ check `dtypes["Ngày"] == "date"`
và không có `"NaT"` trong list — cả 2 vẫn đúng sau fix, không đổi).

- [ ] **Step 2: Viết test mới thất bại cho hành vi giữ giờ + trả object thật**

Thêm vào `tests/data_loader/test_value_cleaner.py` (cuối file), import thêm `date, datetime` từ
`datetime` ở đầu file:

```python
from datetime import date, datetime
```

```python
def test_parse_vn_date_column_returns_real_date_objects_not_iso_strings():
    values = ["01/04/2025", "31/05/2025", None]

    cleaned, dtype = parse_vn_date_column(values)

    assert dtype == "date"
    assert cleaned == [date(2025, 4, 1), date(2025, 5, 31), None]


def test_parse_vn_date_column_keeps_real_time_of_day_from_datetime_objects():
    # Dữ liệu thật train/data/biz_105/SoBanHang_1.xlsx, sheet "Thang 02 2025": openpyxl tự parse
    # cell Excel có giờ thành datetime.datetime object thật (không phải text) -- bug gốc là
    # _parse_one gọi .date() bỏ mất giờ của CHÍNH object này, không phải thiếu format text.
    values = [
        datetime(2025, 2, 1, 6, 0, 25),
        datetime(2025, 2, 1, 6, 46, 58),
        None,
    ]

    cleaned, dtype = parse_vn_date_column(values)

    assert dtype == "datetime"
    assert cleaned == [datetime(2025, 2, 1, 6, 0, 25), datetime(2025, 2, 1, 6, 46, 58), None]


def test_parse_vn_date_column_upgrades_whole_column_to_datetime_when_any_value_has_time():
    # 1 giá trị có giờ thật đủ để NÂNG CẢ CỘT thành "datetime" -- các giá trị chỉ có ngày (00:00:00)
    # trong CÙNG cột phải lên datetime lúc nửa đêm để cột đồng nhất 1 kiểu (DuckDB infer TIMESTAMP
    # cho cả cột, không lẫn DATE/TIMESTAMP giữa các dòng).
    values = [datetime(2025, 2, 1, 0, 0, 0), datetime(2025, 2, 1, 6, 0, 25)]

    cleaned, dtype = parse_vn_date_column(values)

    assert dtype == "datetime"
    assert cleaned == [datetime(2025, 2, 1, 0, 0, 0), datetime(2025, 2, 1, 6, 0, 25)]
```

Sửa test cũ `test_parse_vn_date_column_converts_to_iso` (đổi tên luôn cho đúng hành vi mới) từ:

```python
def test_parse_vn_date_column_converts_to_iso():
    values = ["01/04/2025", "31/05/2025", None]

    cleaned, dtype = parse_vn_date_column(values)

    assert dtype == "date"
    assert cleaned == ["2025-04-01", "2025-05-31", None]
```

thành (xoá hẳn, vì `test_parse_vn_date_column_returns_real_date_objects_not_iso_strings` ở Step 2
đã thay thế đúng vị trí và đúng input) — xoá function `test_parse_vn_date_column_converts_to_iso`
khỏi file.

- [ ] **Step 3: Chạy test, xác nhận các test MỚI fail (test cũ của cột date-only vẫn pass)**

Run: `.venv/Scripts/python.exe -m pytest tests/data_loader/test_value_cleaner.py -v`
Expected: `test_parse_vn_date_column_returns_real_date_objects_not_iso_strings`,
`test_parse_vn_date_column_keeps_real_time_of_day_from_datetime_objects`,
`test_parse_vn_date_column_upgrades_whole_column_to_datetime_when_any_value_has_time` FAIL.
Các test khác trong file PASS.

- [ ] **Step 4: Sửa `parse_vn_date_column`**

Trong `src/data_loader/value_cleaner.py`, thay toàn bộ hàm `parse_vn_date_column` (dòng 124-154)
bằng:

```python
def parse_vn_date_column(values: list) -> tuple[list, str]:
    non_null = [v for v in values if v is not None and str(v).strip() != ""]
    if not non_null:
        return list(values), "raw"

    def _parse_one(v) -> date | datetime | None:
        if isinstance(v, datetime):
            return v
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

    # 1 giá trị có giờ/phút/giây thật (khác 00:00:00) đủ để nâng CẢ CỘT lên "datetime" -- giữ
    # đồng nhất 1 kiểu dữ liệu cho cả cột thay vì lẫn date/datetime từng dòng.
    has_time = any(
        isinstance(p, datetime) and (p.hour or p.minute or p.second) for p in parsed if p is not None
    )

    result = []
    for v in values:
        if v is None or str(v).strip() == "":
            result.append(None)
            continue
        parsed_v = _parse_one(v)
        if parsed_v is None:
            result.append(None)
        elif has_time:
            result.append(
                parsed_v if isinstance(parsed_v, datetime) else datetime(parsed_v.year, parsed_v.month, parsed_v.day)
            )
        else:
            result.append(parsed_v.date() if isinstance(parsed_v, datetime) else parsed_v)
    return result, "datetime" if has_time else "date"
```

- [ ] **Step 5: Sửa dispatch trong `build_business_db.py`'s `_apply_value_cleaning`**

Trong `src/data_loader/build_business_db.py`, đổi đoạn (dòng 80-85):

```python
        cleaned, dtype = parse_vn_date_column(values)
        if dtype == "date":
            frame[col] = cleaned
            column_dtypes[col] = "date"
        else:
            column_dtypes[col] = "raw"
```

thành:

```python
        cleaned, dtype = parse_vn_date_column(values)
        if dtype in ("date", "datetime"):
            frame[col] = cleaned
            column_dtypes[col] = dtype
        else:
            column_dtypes[col] = "raw"
```

- [ ] **Step 6: Chạy lại test, xác nhận PASS**

Run: `.venv/Scripts/python.exe -m pytest tests/data_loader/test_value_cleaner.py tests/data_loader/test_build_business_db.py -v`
Expected: toàn bộ PASS, không còn fail nào.

- [ ] **Step 7: Verify thực nghiệm DuckDB suy đúng kiểu DATE/TIMESTAMP (không phải VARCHAR)**

Thêm vào `tests/data_loader/test_duckdb_writer.py` (cuối file):

```python
from datetime import date, datetime


def test_date_and_datetime_columns_get_native_duckdb_types_not_varchar(tmp_path: Path):
    """Finding #2: parse_vn_date_column trả object date/datetime thật (không phải isoformat string)
    -- DuckDB phải suy ra DATE/TIMESTAMP thật để EXTRACT()/date function dùng được, không VARCHAR."""
    db_path = tmp_path / "biz.duckdb"
    table = LoadedTable(
        source_files=["a.csv"],
        sheet_name=None,
        table_name="DonHang",
        header_confidence="high",
        frame=pd.DataFrame(
            {
                "Ngày": [date(2025, 1, 2), None, date(2025, 1, 3)],
                "Giờ vào": [datetime(2025, 1, 2, 6, 30, 0), None, datetime(2025, 1, 3, 0, 0, 0)],
            }
        ),
    )

    write_tables(db_path, [table])

    con = duckdb.connect(str(db_path))
    types = dict(
        con.execute(
            "SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'DonHang'"
        ).fetchall()
    )
    con.close()
    assert types["Ngày"] == "DATE"
    assert types["Giờ vào"] == "TIMESTAMP"
```

Run: `.venv/Scripts/python.exe -m pytest tests/data_loader/test_duckdb_writer.py -v`
Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add src/data_loader/value_cleaner.py src/data_loader/build_business_db.py tests/data_loader/test_value_cleaner.py tests/data_loader/test_build_business_db.py tests/data_loader/test_duckdb_writer.py
git commit -m "fix(data-loader): keep real time-of-day and native date/datetime objects (C5 #1, #2)"
```

---

### Task 2: T002 `value_cleaner.py` — giữ số điện thoại/MST bắt đầu bằng 0 dạng text (Finding #6)

**Files:**
- Modify: `src/data_loader/value_cleaner.py:29-37` (`clean_numeric_column`)
- Test: `tests/data_loader/test_value_cleaner.py`

**Interfaces:**
- Consumes: không có.
- Produces: `clean_numeric_column(values: list) -> tuple[list, str]` — hợp đồng KHÔNG đổi (vẫn trả
  `("numeric", ...)` hoặc `("raw", ...)`), chỉ THÊM 1 điều kiện mới khiến cột ID-dạng-số-có-0-đầu
  rơi về `"raw"` sớm hơn.

- [ ] **Step 1: Viết test mới thất bại, dùng đúng dữ liệu thật**

Thêm vào `tests/data_loader/test_value_cleaner.py`:

```python
def test_clean_numeric_column_keeps_leading_zero_phone_numbers_as_text():
    # Dữ liệu thật train/data/biz_108/DanhSachKhachHang.xlsx, cột "Điện thoại" -- hiện bị ép
    # thành float (933201672.0), mất số 0 đầu.
    values = ["0933201672", "0919331756", "0975706068", "0707409323", "0900683501"]

    cleaned, dtype = clean_numeric_column(values)

    assert dtype == "raw"
    assert cleaned == values


def test_clean_numeric_column_still_converts_plain_quantities_with_a_single_zero():
    # "0" (số lượng 0) lẫn với số thường không có số 0 đầu -- KHÔNG được bị coi là leading-zero
    # code, vẫn phải ép numeric như trước.
    values = ["0", "150", "42"]

    cleaned, dtype = clean_numeric_column(values)

    assert dtype == "numeric"
    assert cleaned == [0.0, 150.0, 42.0]
```

- [ ] **Step 2: Chạy test, xác nhận fail**

Run: `.venv/Scripts/python.exe -m pytest tests/data_loader/test_value_cleaner.py::test_clean_numeric_column_keeps_leading_zero_phone_numbers_as_text -v`
Expected: FAIL (hiện ra `dtype == "numeric"`, mất số 0).

- [ ] **Step 3: Sửa `clean_numeric_column`**

Trong `src/data_loader/value_cleaner.py`, thêm hàm mới ngay TRƯỚC `clean_numeric_column` (dòng 29):

```python
def _looks_like_leading_zero_code(non_null: list) -> bool:
    """SĐT/MST VN quy ước giữ số 0 đầu (vd "0933201672") -- không ai viết số lượng/tiền có số 0
    đệm đầu, nên tỉ lệ cao giá trị dạng text bắt đầu bằng "0" (độ dài > 1) là tín hiệu đủ mạnh để
    coi cả cột là mã định danh, không ép numeric."""
    texts = [str(v).strip() for v in non_null if not isinstance(v, (int, float))]
    if not texts:
        return False
    zero_prefixed = sum(1 for t in texts if t.startswith("0") and len(t) > 1)
    return zero_prefixed / len(texts) >= _RAW_RATIO_THRESHOLD
```

Sửa `clean_numeric_column` (dòng 29-37 hiện tại) từ:

```python
def clean_numeric_column(values: list) -> tuple[list, str]:
    non_null = [v for v in values if v is not None and str(v).strip() != ""]
    if not non_null:
        return list(values), "raw"
    parsed = [_to_number(v) for v in non_null]
    ok_ratio = sum(p is not None for p in parsed) / len(non_null)
    if ok_ratio < _RAW_RATIO_THRESHOLD:
        return list(values), "raw"
    return [_to_number(v) for v in values], "numeric"
```

thành:

```python
def clean_numeric_column(values: list) -> tuple[list, str]:
    non_null = [v for v in values if v is not None and str(v).strip() != ""]
    if not non_null:
        return list(values), "raw"
    if _looks_like_leading_zero_code(non_null):
        return list(values), "raw"
    parsed = [_to_number(v) for v in non_null]
    ok_ratio = sum(p is not None for p in parsed) / len(non_null)
    if ok_ratio < _RAW_RATIO_THRESHOLD:
        return list(values), "raw"
    return [_to_number(v) for v in values], "numeric"
```

- [ ] **Step 4: Chạy lại test, xác nhận PASS**

Run: `.venv/Scripts/python.exe -m pytest tests/data_loader/test_value_cleaner.py -v`
Expected: toàn bộ PASS (bao gồm `test_clean_numeric_column_handles_thousand_separator_mixed_with_plain_number`
đã có từ trước — `[42000, "51,000", "45000", None]` không có giá trị nào bắt đầu bằng "0" nên
không bị ảnh hưởng).

- [ ] **Step 5: Commit**

```bash
git add src/data_loader/value_cleaner.py tests/data_loader/test_value_cleaner.py
git commit -m "fix(data-loader): keep leading-zero phone/tax-id columns as text (C5 #6)"
```

---

### Task 3: T003 `header_locator.py` — bỏ qua dòng caption báo cáo trong fallback (Finding #3)

**Files:**
- Modify: `src/data_loader/header_locator.py:36-42`
- Test: `tests/data_loader/test_header_locator.py`

**Interfaces:**
- Consumes: không có.
- Produces: `locate_header(...)` — hợp đồng không đổi, chỉ cải thiện ĐỘ CHÍNH XÁC của nhánh
  fallback (khi không có `expected_columns` tốt để so khớp).

- [ ] **Step 1: Viết test mới thất bại, dùng đúng dữ liệu thật**

Thêm vào `tests/data_loader/test_header_locator.py`:

```python
def test_skips_real_caption_rows_before_header_when_no_readme_columns():
    # Dữ liệu thật train/data/biz_118/Bảng kê phiếu giao hàng.xlsx: 2 dòng caption phía trên
    # header, mỗi dòng chỉ có 1 cell -- fallback (không có expected_columns) từng chọn nhầm dòng
    # caption đầu tiên làm header vì "mọi cell không rỗng đều string" cũng đúng với dòng caption.
    rows = [
        ("BẢNG KÊ PHIẾU GIAO HÀNG",),
        ("Kỳ báo cáo: toàn bộ",),
        (),
        (
            "Ngày giao hàng", "Mã đơn hàng", "Lần giao", "Tên hàng hóa", "Đơn vị tính",
            "Số lượng giao", "Biển số xe", "Người giao hàng",
        ),
        ("02/02/2025", "ORD000002", 1, "Kẽm buộc 1mm", "kg", 1, "51C-327.66", "Ông Hương"),
    ]

    match = locate_header(rows, expected_columns=None)

    assert match.header_row_index == 3
    assert match.confidence == "low"


def test_falls_back_to_first_candidate_when_every_row_looks_like_a_caption():
    # Pathological case: nếu MỌI dòng string-only đều giống caption, phải vẫn trả về dòng ĐẦU
    # TIÊN trong số đó (không về index 0 cứng hoặc rơi hết), giữ an toàn như hành vi gốc.
    rows = [("TIÊU ĐỀ MỘT",), ("TIÊU ĐỀ HAI",)]

    match = locate_header(rows, expected_columns=None)

    assert match.header_row_index == 0
    assert match.confidence == "low"
```

- [ ] **Step 2: Chạy test, xác nhận test đầu tiên fail**

Run: `.venv/Scripts/python.exe -m pytest tests/data_loader/test_header_locator.py -v`
Expected: `test_skips_real_caption_rows_before_header_when_no_readme_columns` FAIL
(trả về `header_row_index == 0` thay vì `3`). Test thứ 2 đã PASS từ code gốc (tình cờ, vì rơi về
default `index=0` cuối hàm) — không sao, vẫn phải giữ đúng sau khi sửa (Step 3 đảm bảo điều này).

- [ ] **Step 3: Sửa fallback trong `locate_header`**

Trong `src/data_loader/header_locator.py`, thay đoạn (dòng 36-42):

```python
    # Fallback: dòng đầu tiên mà mọi cell không rỗng đều là chuỗi (không phải số/None)
    for i, row in enumerate(rows[:max_scan_rows]):
        non_empty = [c for c in row if c is not None and str(c).strip() != ""]
        if non_empty and all(isinstance(c, str) for c in non_empty):
            return HeaderMatch(header_row_index=i, confidence="low")

    return HeaderMatch(header_row_index=0, confidence="low")
```

thành:

```python
    # Fallback: dòng đầu tiên mà mọi cell không rỗng đều là chuỗi, ƯU TIÊN bỏ qua dòng giống
    # caption báo cáo (1 cell, dạng "TIÊU ĐỀ HOA" hoặc "Nhãn: giá trị") -- caption như vậy phổ
    # biến ở đầu file xlsx thật (vd biz_118/"Bảng kê phiếu giao hàng.xlsx") và dễ bị nhận lầm là
    # header khi sheet chỉ có 1-vài cell có dữ liệu ở các dòng caption đó. Nếu MỌI dòng ứng viên
    # đều giống caption (pathological), rơi về dòng ứng viên ĐẦU TIÊN để giữ an toàn như trước.
    candidates: list[int] = []
    for i, row in enumerate(rows[:max_scan_rows]):
        non_empty = [c for c in row if c is not None and str(c).strip() != ""]
        if non_empty and all(isinstance(c, str) for c in non_empty):
            candidates.append(i)
            if not _looks_like_caption(non_empty):
                return HeaderMatch(header_row_index=i, confidence="low")

    if candidates:
        return HeaderMatch(header_row_index=candidates[0], confidence="low")

    return HeaderMatch(header_row_index=0, confidence="low")
```

Thêm hàm `_looks_like_caption` ngay TRƯỚC `locate_header` (sau `_normalize`, dòng 17):

```python
def _looks_like_caption(non_empty_cells: list) -> bool:
    if len(non_empty_cells) != 1:
        return False
    text = str(non_empty_cells[0]).strip()
    return text.isupper() or ":" in text
```

- [ ] **Step 4: Chạy lại test, xác nhận PASS**

Run: `.venv/Scripts/python.exe -m pytest tests/data_loader/test_header_locator.py -v`
Expected: toàn bộ PASS (bao gồm `test_falls_back_to_heuristic_when_no_readme_columns` đã có từ
trước — `("Tên","Giá")` có 2 cell nên `_looks_like_caption` luôn `False`, không đổi hành vi).

- [ ] **Step 5: Commit**

```bash
git add src/data_loader/header_locator.py tests/data_loader/test_header_locator.py
git commit -m "fix(data-loader): skip report-caption rows in header-locator fallback (C5 #3)"
```

---

### Task 4: T004 `build_business_db.py` — dedupe tên cột casefold (Finding #7)

**Files:**
- Modify: `src/data_loader/build_business_db.py:31-43` (`_build_header`)
- Test: `tests/data_loader/test_build_business_db.py`

**Interfaces:**
- Consumes: không có.
- Produces: `_build_header(header_row: tuple) -> list[str]` — hợp đồng không đổi.

- [ ] **Step 1: Viết test mới thất bại**

Trong `tests/data_loader/test_build_business_db.py`, đổi import dòng 9 từ:

```python
from data_loader.build_business_db import _apply_value_cleaning, _dedupe_table_names, build_business
```

thành:

```python
from data_loader.build_business_db import (
    _apply_value_cleaning,
    _build_header,
    _dedupe_table_names,
    build_business,
)
```

Thêm vào cuối file:

```python
def test_build_header_dedupes_case_insensitively():
    # DuckDB không phân biệt hoa/thường tên cột (giống _dedupe_table_names đã làm cho table) --
    # "Ten" và "ten" phải bị coi là trùng.
    header = _build_header(("Ten", "ten", "Ghi chú", "Ghi chú"))

    assert header == ["Ten", "ten_2", "Ghi chú", "Ghi chú_2"]


def test_build_header_avoids_colliding_with_an_existing_original_name():
    # Tên sinh ra để dedupe ("Ten_2") không được đụng 1 tên gốc đã có sẵn trong header.
    header = _build_header(("Ten", "Ten", "Ten_2"))

    assert header == ["Ten", "Ten_2", "Ten_2_2"]
    assert len({h.casefold() for h in header}) == 3
```

- [ ] **Step 2: Chạy test, xác nhận fail**

Run: `.venv/Scripts/python.exe -m pytest tests/data_loader/test_build_business_db.py::test_build_header_dedupes_case_insensitively tests/data_loader/test_build_business_db.py::test_build_header_avoids_colliding_with_an_existing_original_name -v`
Expected: cả 2 FAIL (`ten` hiện không bị coi là trùng `Ten`; `Ten_2` sinh ra đụng tên gốc không bị phát hiện).

- [ ] **Step 3: Sửa `_build_header`**

Trong `src/data_loader/build_business_db.py`, thay toàn bộ hàm `_build_header` (dòng 31-43) bằng:

```python
def _build_header(header_row: tuple) -> list[str]:
    """Tên cột từ dòng header thô, đổi tên None -> col_i và chống trùng tên (vd 'Ghi chú' x2,
    hoặc 'Ten'/'ten' lệch hoa-thường -- DuckDB không phân biệt hoa/thường tên cột kể cả khi quote,
    nên phải casefold khi so trùng, giống _dedupe_table_names đã làm cho tên table). Tên sinh ra để
    dedupe cũng được kiểm trong CÙNG 1 set, để không đụng 1 tên gốc đã có sẵn trong header."""
    seen: set[str] = set()
    header: list[str] = []
    for i, c in enumerate(header_row):
        name = str(c).strip() if c is not None else f"col_{i}"
        base, n = name, 1
        while name.casefold() in seen:
            n += 1
            name = f"{base}_{n}"
        seen.add(name.casefold())
        header.append(name)
    return header
```

- [ ] **Step 4: Chạy lại test, xác nhận PASS**

Run: `.venv/Scripts/python.exe -m pytest tests/data_loader/test_build_business_db.py -v`
Expected: toàn bộ PASS.

- [ ] **Step 5: Commit**

```bash
git add src/data_loader/build_business_db.py tests/data_loader/test_build_business_db.py
git commit -m "fix(data-loader): casefold column-name dedupe, check against original names too (C5 #7)"
```

---

### Task 5: T005 `build_business_db.py` — pad/truncate row về đúng độ dài header trước khi dựng DataFrame (Finding #8)

**Files:**
- Modify: `src/data_loader/build_business_db.py:89-111` (`_clean_sheet_to_table`),
  `src/data_loader/build_business_db.py:152-192` (`_clean_raw_group_to_table`)
- Test: `tests/data_loader/test_build_business_db.py`

**Interfaces:**
- Consumes: không có.
- Produces: `_align_row_length(rows: list[tuple], length: int) -> list[tuple]` (hàm nội bộ mới,
  dùng ở cả `_clean_sheet_to_table` và `_clean_raw_group_to_table`).

**⚠️ Lưu ý quan trọng — sửa 1 test hiện có:** `test_one_broken_file_does_not_crash_other_tables`
(cuối `tests/data_loader/test_build_business_db.py`) hiện dùng file CSV có SỐ CỘT LỆCH header
("A,B" + dòng "1,2,3") để giả lập "file hỏng". Sau fix này, lệch-độ-dài-dòng không còn khiến
pandas raise lỗi nữa (được pad/truncate êm, đúng ý Finding #8) — nên file đó sẽ KHÔNG còn hỏng,
làm test FAIL sai mục đích nếu không sửa fixture. Phải đổi fixture sang 1 nguyên nhân hỏng file
KHÁC — byte không phải UTF-8 hợp lệ (lỗi ngay ở tầng đọc file, trước khi tới `_clean_sheet_to_table`
hoàn toàn) — đã verify thực nghiệm `0xFF` luôn raise `UnicodeDecodeError` khi đọc với `utf-8-sig`.

- [ ] **Step 1: Sửa fixture của test đã có (TRƯỚC khi sửa code, để tránh test đó sai mục đích)**

Trong `tests/data_loader/test_build_business_db.py`, sửa `test_one_broken_file_does_not_crash_other_tables`
từ:

```python
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

thành:

```python
def test_one_broken_file_does_not_crash_other_tables(tmp_path: Path):
    """Acceptance scenario 5: 1 file hỏng -> business vẫn ra table của file tốt, không crash."""
    business_dir = tmp_path / "biz_broken"
    business_dir.mkdir()
    (business_dir / "good.csv").write_text("A,B\n1,2\n3,4\n", encoding="utf-8")
    # "bad.csv" chứa byte không phải UTF-8 hợp lệ (0xFF không bao giờ hợp lệ trong UTF-8) -> lỗi
    # ngay khi đọc, bị read_all_sheets bỏ qua tại tầng đọc file (độc lập với fix Finding #8 ở
    # tầng dựng DataFrame -- không còn dùng lệch-số-cột để giả lập file hỏng nữa, vì sau fix đó
    # không còn làm file hỏng theo cách đó).
    (business_dir / "bad.csv").write_bytes(b"A,B\n\xff\xfe,2\n")

    summary = build_business(business_dir, tmp_path / "out")

    table_names = [t["table_name"] for t in summary["tables"]]
    assert "good" in table_names
    assert "bad" not in table_names  # bị bỏ qua, không làm hỏng cả business
```

Run: `.venv/Scripts/python.exe -m pytest "tests/data_loader/test_build_business_db.py::test_one_broken_file_does_not_crash_other_tables" -v`
Expected: PASS (đổi nguyên nhân hỏng file, nhưng kết quả mong đợi giống cũ).

- [ ] **Step 2: Viết test mới thất bại cho Finding #8**

Thêm vào `tests/data_loader/test_build_business_db.py`, import `warnings` ở đầu file:

```python
import warnings
```

```python
def test_clean_sheet_to_table_pads_short_rows_without_pandas_warning(tmp_path: Path):
    """Finding #8: dòng ngắn hơn header (xlsx có dòng bị cắt cell rỗng ở cuối) không được để pandas
    tự pad NaN lúc dựng DataFrame -- Pandas4Warning, dự kiến raise lỗi ở bản sau."""
    business_dir = tmp_path / "biz"
    business_dir.mkdir()
    (business_dir / "a.csv").write_text("A,B,C\n1,2\n3,4,5\n", encoding="utf-8")

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        summary = build_business(business_dir, tmp_path / "out")

    table = next(t for t in summary["tables"] if t["table_name"] == "a")
    assert table["columns"][2]["n_rows"] == 2  # cả 2 dòng đều có mặt, dòng ngắn được pad None ở "C"
```

- [ ] **Step 3: Chạy test, xác nhận fail**

Run: `.venv/Scripts/python.exe -m pytest "tests/data_loader/test_build_business_db.py::test_clean_sheet_to_table_pads_short_rows_without_pandas_warning" -v`
Expected: FAIL — `warnings.simplefilter("error")` biến `Pandas4Warning` thành exception, làm
`build_business` lỗi (bị catch bởi try/except nội bộ, bảng "a" không được tạo -> `next(...)` raise
`StopIteration`).

- [ ] **Step 4: Thêm `_align_row_length` và áp dụng ở 2 nơi**

Trong `src/data_loader/build_business_db.py`, thêm hàm mới ngay TRƯỚC `_clean_sheet_to_table`
(sau `_apply_value_cleaning`, trước dòng 89):

```python
def _align_row_length(rows: list[tuple], length: int) -> list[tuple]:
    """Chuẩn hoá mọi row về đúng len(header) TRƯỚC khi dựng DataFrame -- nếu không, pandas tự pad
    NaN cho row ngắn hơn (Pandas4Warning, dự kiến raise lỗi ở bản sau) và có thể lỗi âm thầm cho
    row dài hơn."""
    aligned = []
    for row in rows:
        if len(row) < length:
            row = row + (None,) * (length - len(row))
        elif len(row) > length:
            row = row[:length]
        aligned.append(row)
    return aligned
```

Sửa `_clean_sheet_to_table` (dòng 96-97 hiện tại), từ:

```python
    header = _build_header(header_row)
    frame = pd.DataFrame(data_rows, columns=header)
```

thành:

```python
    header = _build_header(header_row)
    data_rows = _align_row_length(data_rows, len(header))
    frame = pd.DataFrame(data_rows, columns=header)
```

Sửa `_clean_raw_group_to_table` (dòng 178 hiện tại), từ:

```python
    frame = pd.DataFrame(all_data_rows, columns=header)
```

thành:

```python
    all_data_rows = _align_row_length(all_data_rows, len(header))
    frame = pd.DataFrame(all_data_rows, columns=header)
```

- [ ] **Step 5: Chạy lại toàn bộ test của file, xác nhận PASS**

Run: `.venv/Scripts/python.exe -m pytest tests/data_loader/test_build_business_db.py -v`
Expected: toàn bộ PASS, kể cả `test_build_business_writes_schema_json_with_time_of_day_raw_column`
(không đụng tới, dòng dữ liệu của nó đã đúng độ dài header từ đầu).

- [ ] **Step 6: Commit**

```bash
git add src/data_loader/build_business_db.py tests/data_loader/test_build_business_db.py
git commit -m "fix(data-loader): pad/truncate rows to header length before building DataFrame (C5 #8)"
```

---

### Task 6: T006 `schema_grouping.py` + `build_business_db.py` — gộp period-series theo SHEET trong 1 file (Finding #5)

**Files:**
- Modify: `src/data_loader/schema_grouping.py` (thêm `_SHEET_PERIOD_RE`, `_is_period_sheet_name`,
  refactor `group_same_schema_files` + helper `_merge_group`)
- Modify: `src/data_loader/build_business_db.py:114-149` (`_group_raw_period_series`)
- Test: `tests/data_loader/test_schema_grouping.py`
- Test: `tests/data_loader/test_build_business_db_golden.py` (golden, dữ liệu thật)

**Interfaces:**
- Consumes: không có task nào khác trong plan này sửa cùng vùng.
- Produces: `schema_grouping._is_period_sheet_name(name: str | None) -> bool` (MỚI, dùng lại ở
  `build_business_db.py`). `group_same_schema_files` giữ nguyên signature
  `(tables: list[LoadedTable]) -> list[LoadedTable]`.

**Bối cảnh đã verify bằng dữ liệu thật (quét lại toàn bộ `.xlsx`, 2026-10-31) — 15 business bị
Finding #5 ảnh hưởng:**
- `train`: biz_102 (`DonHang_ChiTiet.xlsx`, sheet `T01_2025`..`T06_2026`, README khai cột KHÔNG
  theo sheet — `columns_for` trả cùng 1 list cho mọi sheet của file này), biz_103 (tương tự, sheet
  `04.2025`..`07.2026`), biz_105 (2 file CÙNG business: `SoBanHang_1.xlsx` sheet
  `Thang 02 2025`..`Thang 01 2026` + `SoBanHang_2026.xlsx` sheet `Thang 02 2026`..`Thang 06 2026`
  — README khai 2 list cột GIỐNG NHAU 100% cho 2 file này, nên gộp xuyên file tự nhiên xảy ra),
  biz_112, biz_115, biz_117, biz_118, biz_119, biz_120, biz_122, biz_128 (cùng dạng).
- `public_test`: dev_004, dev_012 (sheet `T7-2025`..`T8-2026`, KHÔNG đệm số 0), dev_013 (2 file
  `BanHang_2025.xlsx` + `BanHang_2026.xlsx`, README khai 2 list cột GIỐNG NHAU), dev_014 (sheet
  `Ghi tắt` + `T7-2025`..`T9-2026` — dev_014 là 1 trong 7 business README dạng văn xuôi, KHÔNG có
  `## Cột trong` nào -> `columns_for` luôn trả `None` cho dev_014 -> PHẢI được gộp ở tầng
  post-clean (`group_same_schema_files`), không ở tầng raw -- và sheet `Ghi tắt` KHÔNG được kéo
  vào nhóm gộp).
- KHÔNG đụng (nhiều sheet nhưng là các bảng nghiệp vụ khác nhau, không phải period):
  biz_109 (`DuLieuBanHang.xlsx`), biz_116 (`Bao_cao_ban_hang.xlsx`), biz_121 (`DuLieuXuat.xlsx`),
  dev_003 (`BanHang_TongHop_2025.xlsx`), dev_013/`QuanLy.xlsx`.

- [ ] **Step 1: Viết test đơn vị thất bại cho `_is_period_sheet_name` + `group_same_schema_files` mở rộng**

Thêm vào `tests/data_loader/test_schema_grouping.py` (đầu file, sau import hiện có):

```python
from data_loader.schema_grouping import _is_period_sheet_name, group_same_schema_files
```

(đổi dòng import hiện tại `from data_loader.schema_grouping import group_same_schema_files` thành
dòng trên).

Thêm vào cuối file:

```python
def test_is_period_sheet_name_matches_all_real_patterns_found_in_the_dataset():
    # Toàn bộ pattern thật đã quét được từ train/ + public_test/ (xem Task 6 bối cảnh).
    real_period_names = [
        "T01_2025", "T06_2026",       # biz_102, biz_112
        "04.2025", "07.2026",          # biz_103, biz_115, biz_120, biz_128
        "Thang 02 2025", "Thang 01 2026",  # biz_105
        "Tháng 01-2025", "Tháng 05-2026",  # biz_117
        "T02-2025", "T09-2026",        # biz_118, biz_119, biz_122, dev_004
        "T7-2025", "T8-2026",          # dev_012, dev_014 (không đệm số 0)
    ]
    for name in real_period_names:
        assert _is_period_sheet_name(name), f"{name!r} phải khớp pattern kỳ"

    not_period_names = ["Ghi tắt", "DanhMuc", "KhachHang", "NhapHang", "KhuyenMai", None]
    for name in not_period_names:
        assert not _is_period_sheet_name(name), f"{name!r} KHÔNG được khớp pattern kỳ"


def test_groups_sheets_sharing_a_single_file_by_period_sheet_name():
    # Mô phỏng biz_102: 1 file, nhiều sheet tên theo kỳ, cùng schema (cùng cột sau khi clean).
    jan = _table("DonHang_ChiTiet.xlsx", {"Mã đơn hàng": ["A1"], "Tổng tiền": [1000]})
    jan.sheet_name = "T01_2025"
    feb = _table("DonHang_ChiTiet.xlsx", {"Mã đơn hàng": ["B1"], "Tổng tiền": [2000]})
    feb.sheet_name = "T02_2025"

    result = group_same_schema_files([jan, feb])

    assert len(result) == 1
    merged = result[0]
    assert len(merged.frame) == 2
    assert merged.source_files == ["DonHang_ChiTiet.xlsx", "DonHang_ChiTiet.xlsx"]


def test_does_not_pull_a_non_period_sheet_into_the_period_group():
    # Mô phỏng dev_014: sheet "Ghi tắt" tình cờ CÙNG schema với các sheet kỳ, nhưng tên sheet
    # không khớp pattern kỳ -- không được bị kéo vào nhóm gộp.
    t7 = _table("SoBanHang.xlsx", {"Mã": ["X1"], "Tiền": [500]})
    t7.sheet_name = "T7-2025"
    t8 = _table("SoBanHang.xlsx", {"Mã": ["X2"], "Tiền": [600]})
    t8.sheet_name = "T8-2025"
    ghi_tat = _table("SoBanHang.xlsx", {"Mã": ["X3"], "Tiền": [700]})
    ghi_tat.sheet_name = "Ghi tắt"

    result = group_same_schema_files([t7, t8, ghi_tat])

    assert len(result) == 2
    merged = next(t for t in result if len(t.source_files) > 1)
    assert len(merged.frame) == 2
    standalone = next(t for t in result if len(t.source_files) == 1)
    assert standalone.sheet_name == "Ghi tắt"
    assert len(standalone.frame) == 1


def test_file_based_period_grouping_still_takes_priority_when_it_matches():
    # Hành vi gốc (gộp theo hậu tố tên FILE, sheet_name=None) phải giữ nguyên không đổi.
    jan = _table("BanHang_Thang01_2025.xlsx", {"Mã đơn": ["A1"], "Tổng tiền": [1000]})
    feb = _table("BanHang_Thang02_2025.xlsx", {"Mã đơn": ["B1"], "Tổng tiền": [2000]})

    result = group_same_schema_files([jan, feb])

    assert len(result) == 1
    assert len(result[0].frame) == 2
```

- [ ] **Step 2: Chạy test, xác nhận các test mới fail, test cũ vẫn pass**

Run: `.venv/Scripts/python.exe -m pytest tests/data_loader/test_schema_grouping.py -v`
Expected: `test_is_period_sheet_name_matches_all_real_patterns_found_in_the_dataset` FAIL (import
error, hàm chưa tồn tại) — các test còn lại trong Step 1 cũng FAIL vì cùng lý do import.
`test_groups_monthly_files_with_same_schema_and_numeric_suffix` và
`test_does_not_group_same_schema_with_unrelated_text_suffix` (test cũ) vẫn PASS.

- [ ] **Step 3: Viết `_SHEET_PERIOD_RE` + `_is_period_sheet_name` + refactor `group_same_schema_files`**

Trong `src/data_loader/schema_grouping.py`, thêm sau `_PERIOD_SUFFIX_RE` (dòng 13):

```python
_SHEET_PERIOD_RE = re.compile(
    r"^(?:t\d{1,2}[_\-]\d{4}"              # T01_2025, T02-2025, T7-2025 (không đệm số 0)
    r"|\d{1,2}\.\d{4}"                      # 04.2025
    r"|th[aá]ng\s*\d{1,2}[\s\-]\d{4})$",    # Thang 02 2025 / Tháng 01-2025
    re.IGNORECASE,
)


def _is_period_sheet_name(name: str | None) -> bool:
    return name is not None and bool(_SHEET_PERIOD_RE.match(name.strip()))
```

Thay toàn bộ `group_same_schema_files` (dòng 26-59 hiện tại) bằng:

```python
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
```

- [ ] **Step 4: Chạy lại test, xác nhận PASS**

Run: `.venv/Scripts/python.exe -m pytest tests/data_loader/test_schema_grouping.py -v`
Expected: toàn bộ PASS.

- [ ] **Step 5: Viết test thất bại cho raw-level merge xuyên FILE (biz_105-style) trong `build_business_db.py`**

Thêm vào `tests/data_loader/test_build_business_db_golden.py` (sau import hiện có, thêm):

```python
def test_merges_period_sheets_within_a_single_file_for_biz_102(tmp_path: Path):
    """Finding #5: biz_102/DonHang_ChiTiet.xlsx chia 18 sheet theo tháng (T01_2025..T06_2026)
    trong CÙNG 1 file -- phải gộp thành 1 table, không ra 18 table rời rạc."""
    business_dir = PROJECT_ROOT / "train" / "data" / "biz_102"
    assert business_dir.exists(), "Cần có dữ liệu thật train/data/biz_102"

    summary = build_business(business_dir, tmp_path)

    don_hang_tables = [t for t in summary["tables"] if t["table_name"].startswith("DonHang_ChiTiet")]
    assert len(don_hang_tables) == 1, f"Phải gộp thành 1 table, hiện ra: {don_hang_tables}"
    assert len(don_hang_tables[0]["source_files"]) == 18


def test_merges_period_sheets_across_two_files_for_biz_105(tmp_path: Path):
    """Finding #5(b): biz_105 có 2 file (SoBanHang_1.xlsx 12 sheet + SoBanHang_2026.xlsx 5 sheet)
    cùng khai cột giống nhau trong README -- phải gộp XUYÊN FILE thành 1 table duy nhất."""
    business_dir = PROJECT_ROOT / "train" / "data" / "biz_105"
    assert business_dir.exists(), "Cần có dữ liệu thật train/data/biz_105"

    summary = build_business(business_dir, tmp_path)

    so_ban_hang_tables = [t for t in summary["tables"] if t["table_name"].startswith("SoBanHang")]
    assert len(so_ban_hang_tables) == 1, f"Phải gộp thành 1 table, hiện ra: {so_ban_hang_tables}"
    assert len(so_ban_hang_tables[0]["source_files"]) == 17  # 12 sheet file 1 + 5 sheet file 2


def test_merges_period_sheets_for_dev_014_without_readme_and_excludes_stray_sheet(tmp_path: Path):
    """Finding #5(c): dev_014 (1 trong 7 business README văn xuôi, không có cột khai báo) --
    phải gộp ở tầng post-clean (không cần README), và sheet "Ghi tắt" không khớp pattern kỳ phải
    đứng riêng, không bị kéo vào nhóm gộp."""
    business_dir = PROJECT_ROOT / "public_test" / "data" / "dev_014"
    assert business_dir.exists(), "Cần có dữ liệu thật public_test/data/dev_014"

    summary = build_business(business_dir, tmp_path)

    so_ban_hang_tables = [
        t for t in summary["tables"] if t["table_name"].startswith("SoBanHang") and len(t["source_files"]) > 1
    ]
    assert len(so_ban_hang_tables) == 1, f"Phải có đúng 1 table gộp theo kỳ, hiện ra: {summary['tables']}"
```

- [ ] **Step 6: Chạy test, xác nhận fail**

Run: `.venv/Scripts/python.exe -m pytest tests/data_loader/test_build_business_db_golden.py -v -k "biz_102 or biz_105 or dev_014"`
Expected: 3 test mới FAIL (hiện ra nhiều table rời rạc theo từng sheet, không gộp).

- [ ] **Step 7: Sửa `_group_raw_period_series` trong `build_business_db.py`**

Đổi import dòng 18 từ:

```python
from data_loader.schema_grouping import _is_period_series, group_same_schema_files
```

thành:

```python
from data_loader.schema_grouping import _is_period_series, _is_period_sheet_name, group_same_schema_files
```

Thay toàn bộ `_group_raw_period_series` (dòng 114-149 hiện tại), cụ thể đoạn bucket+validate
(dòng 127-147), từ:

```python
    buckets: dict[tuple, list[RawSheet]] = defaultdict(list)
    singles: list[RawSheet] = []

    for rs in raw_sheets:
        expected = columns_for(readme, rs.source_file, rs.sheet_name) if readme else None
        if expected is None:
            singles.append(rs)
            continue
        buckets[(rs.sheet_name, tuple(expected))].append(rs)

    groups: list[list[RawSheet]] = []
    for bucket in buckets.values():
        if len(bucket) < 2:
            singles.extend(bucket)
            continue
        stems = [os.path.splitext(rs.source_file)[0] for rs in bucket]
        prefix = os.path.commonprefix(stems)
        if _is_period_series(stems, prefix):
            groups.append(bucket)
        else:
            singles.extend(bucket)

    return groups, singles
```

thành:

```python
    _PERIOD_SHEET_MARKER = "__PERIOD_SHEET__"
    buckets: dict[tuple, list[RawSheet]] = defaultdict(list)
    singles: list[RawSheet] = []

    for rs in raw_sheets:
        expected = columns_for(readme, rs.source_file, rs.sheet_name) if readme else None
        if expected is None:
            singles.append(rs)
            continue
        # Nhiều sheet tên theo kỳ khác nhau (vd "T01_2025" và "T02_2025") trong CÙNG 1 bucket,
        # để gộp được -- nếu dùng đúng sheet_name làm key như cũ, mỗi tên kỳ sẽ ra 1 bucket riêng.
        bucket_sheet_key = _PERIOD_SHEET_MARKER if _is_period_sheet_name(rs.sheet_name) else rs.sheet_name
        buckets[(bucket_sheet_key, tuple(expected))].append(rs)

    groups: list[list[RawSheet]] = []
    for (bucket_sheet_key, _expected_key), bucket in buckets.items():
        if len(bucket) < 2:
            singles.extend(bucket)
            continue
        if bucket_sheet_key == _PERIOD_SHEET_MARKER:
            # Mọi sheet trong bucket này đã vào đây CHÍNH VÌ sheet_name khớp pattern kỳ -- không
            # cần soi lại hậu tố tên FILE như nhánh dưới (period ở đây là theo SHEET, có thể nhiều
            # sheet trong CÙNG 1 file như biz_102, hoặc cùng tên sheet rải ở nhiều file như
            # biz_105/dev_013 khi README khai cùng 1 list cột cho cả 2 file).
            groups.append(bucket)
            continue
        stems = [os.path.splitext(rs.source_file)[0] for rs in bucket]
        prefix = os.path.commonprefix(stems)
        if _is_period_series(stems, prefix):
            groups.append(bucket)
        else:
            singles.extend(bucket)

    return groups, singles
```

- [ ] **Step 8: Chạy lại test, xác nhận PASS**

Run: `.venv/Scripts/python.exe -m pytest tests/data_loader/test_build_business_db_golden.py -v -k "biz_102 or biz_105 or dev_014"`
Expected: 3 test PASS.

Nếu `test_merges_period_sheets_for_dev_014_without_readme_and_excludes_stray_sheet` KHÔNG pass vì
2 lý do có thể xảy ra với dữ liệu thật (không chắc trước khi chạy thật):
(a) tên file thật không phải `SoBanHang.xlsx` (đổi `startswith("SoBanHang")` theo tên file thật
của `dev_014` — kiểm bằng `ls public_test/data/dev_014/`), hoặc
(b) `_build_header` ra 2 cột khác nhau giữa các sheet period của dev_014 dù cùng ý nghĩa (lệch
khoảng trắng/viết hoa trong header thô, không dùng được README để chuẩn hoá vì dev_014 không có
`## Cột trong`) khiến `_schema_signature` không khớp -- NẾU xảy ra, đây là giới hạn THẬT của cơ
chế post-clean-by-signature (đã có từ trước, không phải lỗi mới do Task 6 gây ra), KHÔNG mở rộng
thêm logic chuẩn hoá tên cột trong task này (ngoài phạm vi Finding #5) -- ghi nhận lại phát hiện
thật (số table thực tế ra sao) vào ledger, báo lại ở Task 8, để Khang quyết có cần 1 finding mới
hay không.

- [ ] **Step 9: Chạy lại TOÀN BỘ test suite `data_loader` để chắc không phá cái đã có**

Run: `.venv/Scripts/python.exe -m pytest tests/data_loader/ -v`
Expected: toàn bộ PASS, bao gồm `test_merges_monthly_files_for_dev_005` (hành vi gốc FR-011 theo
tên FILE, phải không đổi).

- [ ] **Step 10: Commit**

```bash
git add src/data_loader/schema_grouping.py src/data_loader/build_business_db.py tests/data_loader/test_schema_grouping.py tests/data_loader/test_build_business_db_golden.py
git commit -m "feat(data-loader): merge period-series sheets within/across files, not just by file suffix (C5 #5)"
```

---

### Task 7: T007 Verify Finding #4 — 7 business README văn xuôi vẫn ra table hợp lý sau fix #3

**Files:**
- Test: `tests/data_loader/test_build_business_db_golden.py`

**Interfaces:**
- Consumes: fix của Task 3 (header-locator bỏ qua caption) PHẢI đã có trong code trước khi chạy
  task này — không sửa code nào khác trong task này, chỉ verify + ghi test giữ hành vi.

Finding #4 (7 business README dạng văn xuôi: `train/biz_106`, `biz_109`, `biz_123`, `biz_124`;
`public_test/dev_003`, `dev_006`, `dev_014`) ĐÃ XÁC NHẬN không cần sửa code (README không hề liệt
kê tên cột). Task này chỉ verify pipeline thật vẫn chạy ổn cho 7 business này sau khi Task 3 đổi
fallback header-locator, và `header_confidence` thấp có lộ đúng ra `schema.json`.

- [ ] **Step 1: Viết test verify (test này PHẢI pass ngay, không cần sửa code gì thêm — nếu fail,
  dừng lại và báo cáo, không tự sửa thêm ngoài phạm vi Task 3 đã làm)**

Thêm vào `tests/data_loader/test_build_business_db_golden.py`:

```python
import pytest

_PROSE_README_BUSINESSES = [
    ("train", "biz_106"),
    ("train", "biz_109"),
    ("train", "biz_123"),
    ("train", "biz_124"),
    ("public_test", "dev_003"),
    ("public_test", "dev_006"),
    ("public_test", "dev_014"),
]


@pytest.mark.parametrize("dataset, business_id", _PROSE_README_BUSINESSES)
def test_prose_readme_businesses_still_produce_valid_tables(tmp_path: Path, dataset, business_id):
    """Finding #4: 7 business README dạng văn xuôi (không liệt kê cột) -- sau fix Finding #3
    (header-locator bỏ caption), vẫn phải ra >=1 table hợp lệ, không crash."""
    business_dir = PROJECT_ROOT / dataset / "data" / business_id
    assert business_dir.exists(), f"Cần có dữ liệu thật {dataset}/data/{business_id}"

    summary = build_business(business_dir, tmp_path / business_id)

    assert len(summary["tables"]) > 0, f"{business_id}: phải ra >=1 table hợp lệ"
    for table in summary["tables"]:
        assert table["header_confidence"] in ("high", "low")
```

- [ ] **Step 2: Chạy test**

Run: `.venv/Scripts/python.exe -m pytest tests/data_loader/test_build_business_db_golden.py -v -k "prose_readme"`
Expected: 7 test PASS (mỗi business ra ít nhất 1 table).

Nếu MỘT trong 7 business KHÔNG ra được table nào (fail): đây là 1 finding MỚI (không nằm trong 8
finding đã duyệt) — KHÔNG tự sửa code trong task này, ghi lại cụ thể business nào/lỗi gì vào
ledger, báo cáo lại ở Task 8, để Khang quyết hướng xử lý.

- [ ] **Step 3: Commit**

```bash
git add tests/data_loader/test_build_business_db_golden.py
git commit -m "test(data-loader): verify prose-README businesses still load after header-locator fix (C5 #4)"
```

---

### Task 8: T008 Re-verify toàn bộ pipeline thật — `train/` + `public_test/`, không regression

**Files:**
- Test: `tests/data_loader/test_build_all_golden.py` (không sửa code của file, chỉ CHẠY để xác nhận)

**Interfaces:**
- Consumes: TẤT CẢ fix từ Task 1-7 phải đã commit xong trước khi chạy task này.

Đây là task cuối, không sửa code thêm — chỉ chạy lại toàn bộ test suite + pipeline thật, đo số
liệu cụ thể để chứng minh C5 đã xong (Điều 2: không báo "xong" chỉ vì code không lỗi).

- [ ] **Step 1: Chạy toàn bộ test suite `data_loader` (không chỉ golden)**

Run: `.venv/Scripts/python.exe -m pytest tests/data_loader/ -v`
Expected: toàn bộ PASS. Ghi lại số lượng test PASS cụ thể vào ledger (vd "58/58 passed").

- [ ] **Step 2: Chạy `build_all` thật trên TOÀN BỘ `train/` + `public_test/`, bắt mọi warning**

```bash
.venv/Scripts/python.exe -W error::pandas.errors.Pandas4Warning -c "
from pathlib import Path
from data_loader.build_all import build_all
import json

train_results = build_all(Path('train'), Path('/tmp/c5_verify_train'))
public_results = build_all(Path('public_test'), Path('/tmp/c5_verify_public'))

print('train:', len(train_results), 'business, not-ok:', {k: v for k, v in train_results.items() if v != 'ok'})
print('public_test:', len(public_results), 'business, not-ok:', {k: v for k, v in public_results.items() if v != 'ok'})
"
```

(Trên Windows PowerShell, dùng `/tmp/...` tương đương path tạm hợp lệ trong Git Bash hoặc đổi
sang `Path(r'C:\Users\NK004\AppData\Local\Temp\c5_verify_train')` nếu chạy thuần PowerShell —
chọn theo shell đang dùng, không hard-code path cụ thể vào code nguồn.)

Expected: `-W error::pandas.errors.Pandas4Warning` biến MỌI `Pandas4Warning` còn sót thành lỗi
cứng ngay — script phải chạy xong KHÔNG lỗi, `train: 30 business, not-ok: {}`,
`public_test: 14 business, not-ok: {}` (SC-001 vẫn giữ nguyên, không business nào bị crash hoàn
toàn sau tất cả các fix).

- [ ] **Step 3: Verify số table của các business Finding #5 đã giảm đúng như kỳ vọng**

```bash
.venv/Scripts/python.exe -c "
import json
from pathlib import Path

for dataset, biz in [('train','biz_102'), ('train','biz_105'), ('public_test','dev_014')]:
    p = Path(f'/tmp/c5_verify_{\"train\" if dataset==\"train\" else \"public\"}') / f'{biz}.schema.json'
    summary = json.loads(p.read_text(encoding='utf-8'))
    print(biz, '->', len(summary['tables']), 'table(s):', [t['table_name'] for t in summary['tables']])
"
```

Expected: `biz_102` và `biz_105` mỗi business chỉ còn ĐÚNG 1 table tên `DonHang_ChiTiet`/`SoBanHang`
(không còn rải theo từng tháng); `dev_014` có 1 table gộp theo kỳ + 1 table riêng cho sheet
"Ghi tắt" (trừ khi Task 6 Step 8 đã ghi nhận giới hạn thật ở bước đó — nếu vậy, ghi lại số liệu
THẬT quan sát được ở đây, không ép đúng kỳ vọng).

- [ ] **Step 4: Ghi lại số liệu vào `TIEN_DO.md` + đóng checklist C5**

Thêm vào cuối `TIEN_DO.md` (tạo mục `## 4. ĐỢT 2026-10-31 — Sửa C5 (8 finding hoãn từ
001-data-loader)`, theo đúng format mục 3.8 của skill `nk-project-conventions`): liệt kê 8
finding, task nào sửa, số liệu PASS thật từ Step 1-3, và kết quả Task 6 Step 8/Task 7 Step 2 nếu
có finding mới phát sinh.

Sửa `CHECKLIST-ZALO-DATAMATE-DUYET.md`: đổi `- [ ] C5. ...` thành `- [x] ✅ C5. ...` kèm tóm tắt 1
dòng mỗi finding đã sửa + số liệu verify, GIỮ LẠI bất kỳ finding mới phát sinh (nếu có từ Task 6/7)
dưới dạng mục con `⚠️` mới — KHÔNG xoá, chờ Khang quyết riêng.

- [ ] **Step 5: Commit**

```bash
git add TIEN_DO.md CHECKLIST-ZALO-DATAMATE-DUYET.md
git commit -m "docs: close C5 hardening — 8 findings fixed and re-verified on full train/public_test"
```

---
