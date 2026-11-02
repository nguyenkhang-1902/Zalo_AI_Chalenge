import json
from datetime import date
from pathlib import Path

from reasoning_agent.agent import answer_question

from .conftest import build_real_business

_REAL_SQL = (
    'SELECT COUNT(DISTINCT "Mã đơn hàng") FROM DonHang_ChiTiet '
    "WHERE \"Ngày đặt hàng\" = DATE '2026-03-28' "
    "AND \"Trạng thái đơn hàng\" NOT IN ('Đã hủy', 'Đã hoàn hàng')"
)


def test_answer_question_on_real_train_question_biz_102(tmp_path, monkeypatch):
    build_real_business(tmp_path, "biz_102")
    monkeypatch.setenv("REASONING_AGENT_MODEL", "fake-model")
    monkeypatch.setenv("REASONING_AGENT_BASE_URL", "http://fake")

    call_count = {"n": 0}

    def fake_chat_fn(config, messages, tools, timeout):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return {
                "content": None,
                "tool_calls": [{"id": "1", "name": "run_sql", "arguments": json.dumps({"query": _REAL_SQL})}],
            }
        return {
            "content": None,
            "tool_calls": [
                {"id": "2", "name": "submit_answer", "arguments": json.dumps({"type": "number", "answer_json": "73"})}
            ],
        }

    monkeypatch.setattr("reasoning_agent.agent.call_chat_completion", fake_chat_fn)

    result = answer_question(
        question="Hôm qua cửa hàng bán được mấy đơn?",
        business_id="biz_102",
        as_of_date=date(2026, 3, 29),
        dataset_dir=tmp_path,
    )

    assert result == {"type": "number", "answer": 73}


def test_missing_rulebook_raises_at_init(tmp_path, monkeypatch):
    build_real_business(tmp_path, "biz_102", copy_dataset_files=False)
    monkeypatch.setenv("REASONING_AGENT_MODEL", "fake-model")
    monkeypatch.setenv("REASONING_AGENT_BASE_URL", "http://fake")

    try:
        answer_question("câu hỏi?", "biz_102", date(2026, 3, 29), tmp_path)
        assert False, "phải raise vì thiếu rulebook.md"
    except FileNotFoundError as e:
        assert "rulebook.md" in str(e)


def test_missing_calendar_raises_at_init(tmp_path, monkeypatch):
    build_real_business(tmp_path, "biz_102", copy_dataset_files=False)
    import shutil

    from .conftest import TRAIN_DIR

    shutil.copy(TRAIN_DIR / "rulebook.md", tmp_path / "rulebook.md")  # có rulebook, thiếu calendar
    monkeypatch.setenv("REASONING_AGENT_MODEL", "fake-model")
    monkeypatch.setenv("REASONING_AGENT_BASE_URL", "http://fake")

    try:
        answer_question("câu hỏi?", "biz_102", date(2026, 3, 29), tmp_path)
        assert False, "phải raise vì thiếu calendar.csv"
    except FileNotFoundError as e:
        assert "calendar.csv" in str(e)


def test_no_hardcoded_business_or_question_id_branching():
    src_dir = Path(__file__).resolve().parents[2] / "src" / "reasoning_agent"
    import re

    pattern = re.compile(r"business_id\s*==|question_id\s*==")
    offending = [f.name for f in src_dir.glob("*.py") if pattern.search(f.read_text(encoding="utf-8"))]
    assert offending == [], f"File rẽ nhánh theo business_id/question_id cụ thể: {offending}"


def test_no_hardcoded_model_name_in_source():
    src_dir = Path(__file__).resolve().parents[2] / "src" / "reasoning_agent"
    offending = [f.name for f in src_dir.glob("*.py") if "qwen" in f.read_text(encoding="utf-8").lower()]
    assert offending == [], f"File hard-code tên model: {offending}"
