# tests/eval_harness/test_matchers.py
from eval_harness.matchers import (
    match_boolean,
    match_date,
    match_number,
    match_percent,
    match_string,
)


def test_match_number_exact():
    assert match_number(89526400, 89526400) is True


def test_match_number_tolerates_float_epsilon():
    assert match_number(2954200.0000001, 2954200) is True


def test_match_number_rejects_wrong_value():
    assert match_number(89526400, 89526401) is False


def test_match_percent_exact():
    # q_00558c1410ef trong train/answers.jsonl thật: tỉ lệ huỷ đơn 6/2025 = 2.08%
    assert match_percent(2.08, 2.08) is True


def test_match_percent_rejects_wrong_value():
    assert match_percent(2.09, 2.08) is False


def test_match_date_exact_day():
    # q_046b75d6192e trong train/answers.jsonl thật
    assert match_date("2025-02-15", "2025-02-15") is True


def test_match_date_rejects_wrong_format():
    assert match_date("15/02/2025", "2025-02-15") is False


def test_match_boolean_exact():
    # q_0fc33ac2add7 trong train/answers.jsonl thật
    assert match_boolean(False, False) is True


def test_match_boolean_rejects_non_bool():
    assert match_boolean(0, False) is False  # 0 không phải bool, dù 0 == False trong Python


def test_match_string_exact():
    # q_06de33fa21cc trong train/answers.jsonl thật
    assert match_string(
        "Xi măng Hà Tiên PCB40 bao 50kg", "Xi măng Hà Tiên PCB40 bao 50kg", ["SP0001"]
    ) is True


def test_match_string_case_whitespace_punctuation_insensitive():
    assert match_string(
        "  xi măng   hà tiên pcb40, bao 50kg.  ", "Xi măng Hà Tiên PCB40 bao 50kg", ["SP0001"]
    ) is True


def test_match_string_accepts_alias_code():
    assert match_string("SP0001", "Xi măng Hà Tiên PCB40 bao 50kg", ["SP0001"]) is True


def test_match_string_rejects_wrong_diacritics():
    # dấu tiếng Việt phải đúng — "mang" khác "măng"
    assert match_string(
        "Xi mang Hà Tiên PCB40 bao 50kg", "Xi măng Hà Tiên PCB40 bao 50kg", ["SP0001"]
    ) is False


def test_match_string_rejects_unrelated_value():
    assert match_string("Gạch ống 8x8x18 Tuynel", "Xi măng Hà Tiên PCB40 bao 50kg", ["SP0001"]) is False
