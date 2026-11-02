import duckdb

from reasoning_agent.sql_tool import build_sql_tool

from .conftest import build_real_business

_REAL_SQL = (
    'SELECT COUNT(DISTINCT "Mã đơn hàng") FROM DonHang_ChiTiet '
    "WHERE \"Ngày đặt hàng\" = DATE '2026-03-28' "
    "AND \"Trạng thái đơn hàng\" NOT IN ('Đã hủy', 'Đã hoàn hàng')"
)


def test_run_sql_on_real_biz_102_data_matches_ground_truth(tmp_path):
    build_real_business(tmp_path, "biz_102", copy_dataset_files=False)
    conn = duckdb.connect(str(tmp_path / "biz_102.duckdb"), read_only=True)
    tool = build_sql_tool(conn)

    result = tool.handler(query=_REAL_SQL)

    assert result["rows"] == [[73]]
    conn.close()


def test_run_sql_returns_error_dict_on_bad_sql_without_raising(tmp_path):
    build_real_business(tmp_path, "biz_102", copy_dataset_files=False)
    conn = duckdb.connect(str(tmp_path / "biz_102.duckdb"), read_only=True)
    tool = build_sql_tool(conn)

    result = tool.handler(query="SELECT * FROM table_khong_ton_tai")

    assert "error" in result
    conn.close()


def test_run_sql_returns_column_names(tmp_path):
    build_real_business(tmp_path, "biz_102", copy_dataset_files=False)
    conn = duckdb.connect(str(tmp_path / "biz_102.duckdb"), read_only=True)
    tool = build_sql_tool(conn)

    result = tool.handler(query='SELECT "Mã đơn hàng" FROM DonHang_ChiTiet LIMIT 1')

    assert result["columns"] == ["Mã đơn hàng"]
    conn.close()


def test_run_sql_rejects_insert_on_read_only_connection_as_error_not_raise(tmp_path):
    # Edge case spec: INSERT/DROP trên connection read-only -> DuckDB tự raise lỗi quyền,
    # tool trả lỗi đó cho model như lỗi SQL thường (không có logic chặn riêng).
    build_real_business(tmp_path, "biz_102", copy_dataset_files=False)
    conn = duckdb.connect(str(tmp_path / "biz_102.duckdb"), read_only=True)
    tool = build_sql_tool(conn)

    result = tool.handler(
        query="INSERT INTO DonHang_ChiTiet SELECT * FROM DonHang_ChiTiet LIMIT 0"
    )

    assert "error" in result
    assert "read-only" in result["error"].lower() or "read_only" in result["error"].lower()
    conn.close()
