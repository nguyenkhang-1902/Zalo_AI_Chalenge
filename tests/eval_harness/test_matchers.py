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


# --- Task 2: list / table / unanswerable / dispatcher ---
from eval_harness.matchers import is_correct, match_list, match_table, match_unanswerable


def test_match_list_exact_with_alias_codes():
    # q_019ec94d9799 trong train/answers.jsonl thật
    truth = ["Cà phê sữa (M)", "Trà đào cam sả (M)", "Cà phê đen (M)"]
    alias = [["SP0003"], ["SP0017"], ["SP0001"]]
    assert match_list(["Cà phê sữa (M)", "Trà đào cam sả (M)", "Cà phê đen (M)"], truth, alias) is True


def test_match_list_accepts_alias_per_position():
    truth = ["Cà phê sữa (M)", "Trà đào cam sả (M)", "Cà phê đen (M)"]
    alias = [["SP0003"], ["SP0017"], ["SP0001"]]
    assert match_list(["SP0003", "SP0017", "SP0001"], truth, alias) is True


def test_match_list_rejects_wrong_order():
    truth = ["Cà phê sữa (M)", "Trà đào cam sả (M)", "Cà phê đen (M)"]
    alias = [["SP0003"], ["SP0017"], ["SP0001"]]
    assert match_list(["Trà đào cam sả (M)", "Cà phê sữa (M)", "Cà phê đen (M)"], truth, alias) is False


def test_match_list_rejects_wrong_length():
    truth = ["Cà phê sữa (M)", "Trà đào cam sả (M)", "Cà phê đen (M)"]
    assert match_list(["Cà phê sữa (M)", "Trà đào cam sả (M)"], truth, [[], [], []]) is False


def test_match_list_of_numbers():
    assert match_list([287435200, 346554700, 309693800], [287435200, 346554700, 309693800], [[], [], []]) is True


TABLE_TRUTH = {
    "columns": ["khach_hang", "so_tien_no"],
    "rows": [
        ["Đỗ Đức An", 404500],
        ["Dương Tâm Bích", 158600],
        ["Phùng Hồng Nam", 126000],
    ],
}
TABLE_ALIAS = [["KH0124"], ["KH0233"], ["KH0137"]]


def test_match_table_exact_same_order():
    predicted = {
        "columns": ["khach_hang", "so_tien_no"],
        "rows": [
            ["Đỗ Đức An", 404500],
            ["Dương Tâm Bích", 158600],
            ["Phùng Hồng Nam", 126000],
        ],
    }
    assert match_table(predicted, TABLE_TRUTH, TABLE_ALIAS) is True


def test_match_table_row_order_does_not_matter():
    predicted = {
        "columns": ["khach_hang", "so_tien_no"],
        "rows": [
            ["Phùng Hồng Nam", 126000],
            ["Đỗ Đức An", 404500],
            ["Dương Tâm Bích", 158600],
        ],
    }
    assert match_table(predicted, TABLE_TRUTH, TABLE_ALIAS) is True


def test_match_table_accepts_alias_code_as_row_key():
    predicted = {
        "columns": ["khach_hang", "so_tien_no"],
        "rows": [
            ["KH0124", 404500],
            ["KH0233", 158600],
            ["KH0137", 126000],
        ],
    }
    assert match_table(predicted, TABLE_TRUTH, TABLE_ALIAS) is True


def test_match_table_column_order_independent_when_names_match():
    predicted = {
        "columns": ["so_tien_no", "khach_hang"],
        "rows": [
            [404500, "Đỗ Đức An"],
            [158600, "Dương Tâm Bích"],
            [126000, "Phùng Hồng Nam"],
        ],
    }
    assert match_table(predicted, TABLE_TRUTH, TABLE_ALIAS) is True


def test_match_table_rejects_wrong_value():
    predicted = {
        "columns": ["khach_hang", "so_tien_no"],
        "rows": [
            ["Đỗ Đức An", 999999],
            ["Dương Tâm Bích", 158600],
            ["Phùng Hồng Nam", 126000],
        ],
    }
    assert match_table(predicted, TABLE_TRUTH, TABLE_ALIAS) is False


def test_match_unanswerable_ignores_reason_content():
    assert match_unanswerable("unanswerable") is True
    assert match_unanswerable("number") is False


def test_is_correct_dispatches_by_type():
    assert is_correct("number", {"type": "number", "answer": 89526400}, 89526400, []) is True
    assert is_correct("number", {"type": "string", "answer": "x"}, 89526400, []) is False
    assert is_correct("unanswerable", {"type": "unanswerable", "reason": "..."}, None, []) is True


def test_is_correct_rejects_non_dict_predicted_without_raising():
    assert is_correct("number", "not_a_dict", 89526400, []) is False
    assert is_correct("number", None, 89526400, []) is False
    assert is_correct("number", ["x"], 89526400, []) is False
