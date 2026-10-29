import pandas as pd

from data_loader.models import LoadedTable
from data_loader.schema_summary import summarize_business


def test_summarize_business_reports_dtype_and_samples():
    table = LoadedTable(
        source_files=["a.csv"],
        sheet_name=None,
        table_name="a",
        header_confidence="high",
        frame=pd.DataFrame({"Tổng tiền": [1000.0, 2000.0, None]}),
        column_dtypes={"Tổng tiền": "numeric"},
    )

    summary = summarize_business("biz_test", [table], readme_raw="# readme")

    assert summary["business_id"] == "biz_test"
    assert summary["readme"] == "# readme"
    col = summary["tables"][0]["columns"][0]
    assert col["name"] == "Tổng tiền"
    assert col["dtype"] == "numeric"
    assert col["n_null"] == 1
    assert col["n_rows"] == 3
    assert col["sample_values"] == [1000.0, 2000.0]
