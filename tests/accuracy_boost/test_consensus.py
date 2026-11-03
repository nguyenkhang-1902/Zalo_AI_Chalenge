from accuracy_boost.consensus import answer_key, decide, pa_curve
from reasoning_agent.react_loop import BUDGET_EXHAUSTED_REASON

A = {"type": "number", "answer": 100.0}
A_NEAR = {"type": "number", "answer": 100.001}
B = {"type": "number", "answer": 200}
C = {"type": "string", "answer": "Cà phê"}
BUDGET = {"type": "unanswerable", "reason": BUDGET_EXHAUSTED_REASON}
ABSTAIN = {"type": "abstain"}


def test_numbers_equal_after_rounding_to_two_decimals():
    assert answer_key(A) == answer_key(A_NEAR)
    assert answer_key(A) != answer_key(B)


def test_string_key_ignores_case_and_spacing_but_keeps_diacritics():
    assert answer_key({"type": "string", "answer": " Cà  Phê "}) == answer_key(C.copy() | {"answer": "cà phê"})
    assert answer_key({"type": "string", "answer": "ca phe"}) != answer_key(C)


def test_table_rows_compared_as_a_set():
    t1 = {"type": "table", "answer": {"columns": ["a"], "rows": [[1], [2]]}}
    t2 = {"type": "table", "answer": {"columns": ["a"], "rows": [[2], [1]]}}
    assert answer_key(t1) == answer_key(t2)


def test_budget_exhausted_and_abstain_are_abstain_votes():
    assert answer_key(BUDGET) == "abstain"
    assert answer_key(ABSTAIN) == "abstain"
    assert answer_key({"type": "unanswerable", "reason": "thiếu giá vốn"}) == "unanswerable"


def test_majority_above_threshold_is_returned():
    decision = decide([A, B, A_NEAR], threshold=0.6)
    assert decision.result == A
    assert round(decision.agreement, 2) == 0.67


def test_no_majority_abstains():
    assert decide([A, B, C], threshold=0.6).result is None


def test_tie_prefers_first_run():
    assert decide([B, A], threshold=0.5).result == B


def test_abstain_votes_never_win_but_lower_agreement():
    assert decide([BUDGET, BUDGET, A], threshold=0.6).result is None
    assert decide([BUDGET, BUDGET, A], threshold=0.3).result == A
    assert decide([BUDGET, ABSTAIN], threshold=0.0).result is None


def test_pa_curve_scores_plus_minus_and_abstain():
    answers = {
        "q1": {"type": "number", "answer": 100, "alias": []},
        "q2": {"type": "number", "answer": 5, "alias": []},
    }
    runs = {"q1": [A, A, A], "q2": [A, B, C]}
    rows = pa_curve(runs, answers, [0.3, 1.0])
    low, high = rows
    assert (low["correct"], low["wrong"], low["abstained"]) == (1, 1, 0)
    assert low["pa"] == 0.0
    assert (high["correct"], high["wrong"], high["abstained"]) == (1, 0, 1)
    assert high["pa"] == 0.5


def test_table_aliases_do_not_collapse_different_tables_and_gate_abstains():
    t1 = {"type": "table", "answer": {"cols": ["a"], "data": [[1]]}}
    t2 = {"type": "table", "answer": {"cols": ["a"], "data": [[2]]}}
    assert answer_key(decide([t1], 0.0).result) != answer_key(decide([t2], 0.0).result)
    assert decide([t1, t2], threshold=1.0).result is None


def test_abstain_passes_through_decide_normalization():
    assert decide([ABSTAIN, A], threshold=0.5).result == A
    assert decide([ABSTAIN, ABSTAIN], threshold=0.5).result is None


def test_pa_curve_scores_normalized_percent():
    runs = {"q": [{"type": "percent", "answer": 12.3456}]}
    truth = {"q": {"type": "percent", "answer": 12.35}}
    assert pa_curve(runs, truth, [0.0])[0]["correct"] == 1
