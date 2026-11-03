import duckdb
import pytest

from reasoning_agent.semantic_tools import build_semantic_tools

SCHEMA = {
    "tables": [
        {"table_name": "Don", "columns": [{"name": n, "dtype": d} for n, d in
                                            [("Ngày", "DATE"), ("Mã", "VARCHAR"), ("Tiền", "DOUBLE"), ("Trạng thái", "VARCHAR")]]},
        {"table_name": "Hang", "columns": [{"name": n, "dtype": d} for n, d in [("Mã", "VARCHAR"), ("SL", "BIGINT")]]},
    ]
}


@pytest.fixture
def tools():
    conn = duckdb.connect()
    conn.execute('CREATE TABLE Don ("Ngày" DATE, "Mã" VARCHAR, "Tiền" DOUBLE, "Trạng thái" VARCHAR)')
    conn.execute(
        "INSERT INTO Don VALUES ('2026-03-01','A',100,'ok'),('2026-03-02','B',50,'ok'),"
        "('2026-03-02','A',25,'Đã hủy'),('2026-04-01','A',10,'ok')"
    )
    conn.execute('CREATE TABLE Hang ("Mã" VARCHAR, "SL" BIGINT)')
    conn.execute("INSERT INTO Hang VALUES ('Y',10),('X',10),('Z',5)")
    return build_semantic_tools(SCHEMA, conn)


def agg(tools, **kw):
    return tools["aggregate"].handler(**kw)


def test_sum_in_date_range_with_exclusion_filter(tools):
    result = agg(
        tools, table="Don", agg="sum", value_column="Tiền", date_column="Ngày",
        start="2026-03-01", end="2026-03-31",
        filters=[{"column": "Trạng thái", "op": "not_in", "value": ["Đã hủy"]}],
    )
    assert result["rows"] == [[150.0]]
    assert "SUM" in result["sql"]


def test_count_distinct_and_plain_count(tools):
    assert agg(tools, table="Don", agg="count_distinct", value_column="Mã")["rows"] == [[2]]
    assert agg(tools, table="Don", agg="count")["rows"] == [[4]]


def test_group_by_top_n_with_tie_break_ascending(tools):
    result = agg(tools, table="Hang", agg="sum", value_column="SL", group_by=["Mã"], order="desc",
                 limit=2, tie_break_column="Mã")
    assert result["rows"] == [["X", 10], ["Y", 10]]


def test_unknown_names_list_valid_ones(tools):
    with pytest.raises(ValueError, match="Các table có"):
        agg(tools, table="Nope", agg="count")
    with pytest.raises(ValueError, match="Các cột có"):
        agg(tools, table="Don", agg="sum", value_column="Thành tiền")


def test_invalid_agg_op_and_missing_value_column(tools):
    with pytest.raises(ValueError):
        agg(tools, table="Don", agg="median", value_column="Tiền")
    with pytest.raises(ValueError):
        agg(tools, table="Don", agg="sum")
    with pytest.raises(ValueError):
        agg(tools, table="Don", agg="count", filters=[{"column": "Mã", "op": "regex", "value": "A"}])


def test_dates_without_date_column_rejected(tools):
    with pytest.raises(ValueError):
        agg(tools, table="Don", agg="count", start="2026-03-01")


def test_like_filter(tools):
    result = agg(tools, table="Don", agg="count", filters=[{"column": "Trạng thái", "op": "like", "value": "Đã%"}])
    assert result["rows"] == [[1]]


def test_percent_change(tools):
    handler = tools["percent_change"].handler
    assert handler(current=90, previous=100) == {"percent_change": -10.0}
    assert handler(current=150, previous=100) == {"percent_change": 50.0}
    with pytest.raises(ValueError):
        handler(current=1, previous=0)
