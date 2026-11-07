import json
from datetime import date

from reasoning_agent.config import AgentConfig

from distill.trace_generator import generate_trace

from .conftest import build_real_business

_SQL = (
    'SELECT COUNT(DISTINCT "Mã đơn hàng") FROM DonHang_ChiTiet '
    "WHERE \"Ngày đặt hàng\" = DATE '2026-03-28' "
    "AND \"Trạng thái đơn hàng\" NOT IN ('Đã hủy', 'Đã hoàn hàng')"
)


def _fake_teacher():
    n = {"i": 0}

    def fn(config, messages, tools, timeout, **kw):
        n["i"] += 1
        if n["i"] == 1:
            return {
                "content": None,
                "tool_calls": [{"id": "1", "name": "run_sql", "arguments": json.dumps({"query": _SQL})}],
            }
        return {
            "content": None,
            "tool_calls": [
                {"id": "2", "name": "submit_answer", "arguments": json.dumps({"type": "number", "answer_json": "73"})}
            ],
        }

    return fn


def test_generate_trace_captures_full_messages(tmp_path):
    build_real_business(tmp_path, "biz_102")
    tc = AgentConfig(model="t", base_url="http://x", api_key="")
    tr = generate_trace(
        "Hôm qua bán mấy đơn?",
        "biz_102",
        date(2026, 3, 29),
        tmp_path,
        tc,
        chat_completion_fn=_fake_teacher(),
    )
    assert tr.result == {"type": "number", "answer": 73}
    assert any(m.get("role") == "tool" for m in tr.messages)  # có kết quả run_sql
    last = tr.messages[-1]
    assert last["role"] == "assistant"
    assert last["tool_calls"][0]["function"]["name"] == "submit_answer"  # trace kết ở submit
    tool_names = {t["function"]["name"] for t in tr.tools}
    assert {"run_sql", "submit_answer"} <= tool_names  # tools lưu kèm để train khớp inference
