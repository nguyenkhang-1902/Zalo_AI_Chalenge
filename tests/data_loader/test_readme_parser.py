from pathlib import Path

from data_loader.readme_parser import columns_for, parse_readme

README_TEXT = """# Dữ liệu biz_129

## File
- `don_hang.csv` (csv)

## Cột trong `don_hang.csv`
- **Hình thức thanh toán**: hình thức thanh toán của đơn
- **Số phiếu**: mã đơn

## Cột trong `BanHang_Thang<tháng>_<năm>.xlsx`, sheet `DonHang_ChiTiet`
- **Mã đơn hàng**: mã đơn
- **Tổng tiền**: thành tiền

## Quy ước
- Dữ liệu có đến hết 14/08/2026.
"""


def test_parses_simple_and_templated_sections(tmp_path: Path):
    readme_path = tmp_path / "README.md"
    readme_path.write_text(README_TEXT, encoding="utf-8")

    info = parse_readme(readme_path)

    assert columns_for(info, "don_hang.csv", None) == ["Hình thức thanh toán", "Số phiếu"]
    assert columns_for(info, "BanHang_Thang01_2025.xlsx", "DonHang_ChiTiet") == [
        "Mã đơn hàng",
        "Tổng tiền",
    ]
    assert columns_for(info, "BanHang_Thang01_2025.xlsx", "SheetKhác") is None
    assert columns_for(info, "khong_ton_tai.csv", None) is None
