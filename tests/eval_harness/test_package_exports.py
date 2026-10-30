def test_all_public_symbols_importable_from_package_root():
    from eval_harness import EvalReport, TypeBreakdown, format_report, score_submission

    assert score_submission is not None
    assert EvalReport is not None
    assert TypeBreakdown is not None
    assert format_report is not None
