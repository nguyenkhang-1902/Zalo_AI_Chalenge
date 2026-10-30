from eval_harness.report import EvalReport, TypeBreakdown, format_report


def test_type_breakdown_records_outcomes():
    bd = TypeBreakdown()
    bd.record("correct")
    bd.record("correct")
    bd.record("incorrect")
    bd.record("abstained")
    assert bd.correct == 2
    assert bd.incorrect == 1
    assert bd.abstained == 1
    assert bd.total == 4
    assert bd.accuracy == 0.5


def test_type_breakdown_accuracy_zero_when_empty():
    bd = TypeBreakdown()
    assert bd.total == 0
    assert bd.accuracy == 0.0


def test_format_report_includes_totals_and_breakdowns():
    by_type = {"number": TypeBreakdown(correct=1, incorrect=0, abstained=0)}
    by_business = {"biz_001": TypeBreakdown(correct=1, incorrect=0, abstained=0)}
    report = EvalReport(
        total_score=1,
        total_questions=1,
        correct=1,
        incorrect=0,
        abstained=0,
        accuracy=1.0,
        by_type=by_type,
        by_business=by_business,
        malformed_count=0,
        extra_ids_ignored=0,
    )
    text = format_report(report)
    assert "Tổng điểm: 1 / 1" in text
    assert "number" in text
    assert "biz_001" in text
