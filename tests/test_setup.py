def test_core_dependencies_importable():
    import duckdb
    import openpyxl
    import pandas

    assert duckdb and openpyxl and pandas
