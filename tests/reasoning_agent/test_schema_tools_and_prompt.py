import pytest

from reasoning_agent.prompt import build_system_prompt
from reasoning_agent.schema_tools import build_schema_tools, load_schema

from .conftest import build_real_business


def test_load_schema_reads_real_biz_102_schema_json(tmp_path):
    build_real_business(tmp_path, "biz_102", copy_dataset_files=False)

    schema = load_schema(tmp_path, "biz_102")

    assert schema["business_id"] == "biz_102"
    table_names = {t["table_name"] for t in schema["tables"]}
    assert "DonHang_ChiTiet" in table_names


def test_get_readme_returns_real_readme_text(tmp_path):
    build_real_business(tmp_path, "biz_102", copy_dataset_files=False)
    schema = load_schema(tmp_path, "biz_102")
    tools = build_schema_tools(schema)

    result = tools["get_readme"].handler()

    assert "DonHang_ChiTiet.xlsx" in result["readme"]


def test_get_table_detail_returns_real_columns(tmp_path):
    build_real_business(tmp_path, "biz_102", copy_dataset_files=False)
    schema = load_schema(tmp_path, "biz_102")
    tools = build_schema_tools(schema)

    result = tools["get_table_detail"].handler(table_name="DonHang_ChiTiet")

    column_names = {c["name"] for c in result["columns"]}
    assert column_names == {
        "Mã đơn hàng", "Ngày đặt hàng", "Trạng thái đơn hàng", "Tên khách hàng",
        "Tên sản phẩm", "Số lượng sản phẩm", "Giá sản phẩm", "Tổng tiền", "Đơn vị tính",
    }


def test_get_table_detail_raises_for_unknown_table(tmp_path):
    build_real_business(tmp_path, "biz_102", copy_dataset_files=False)
    schema = load_schema(tmp_path, "biz_102")
    tools = build_schema_tools(schema)

    with pytest.raises(ValueError, match="table không tồn tại"):
        tools["get_table_detail"].handler(table_name="khong_ton_tai")


def test_system_prompt_includes_table_names_and_rulebook_text(tmp_path):
    build_real_business(tmp_path, "biz_102", copy_dataset_files=False)
    schema = load_schema(tmp_path, "biz_102")

    prompt = build_system_prompt(schema, rulebook_text="LUẬT RIÊNG: test marker 12345")

    assert "DonHang_ChiTiet" in prompt
    assert "LUẬT RIÊNG: test marker 12345" in prompt
    assert "query_end" in prompt
    assert "submit_answer" in prompt
    assert '"Mã đơn hàng"' in prompt  # tên cột PHẢI xuất hiện có ngoặc kép trong phần liệt kê table
    assert "KHÔNG" in prompt and "đoán" in prompt  # có cảnh báo chống đoán/hallucinate tên cột
