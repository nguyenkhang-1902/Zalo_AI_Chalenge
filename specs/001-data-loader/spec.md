# Feature Specification: Data Loader & Schema Layer

**Feature Branch**: `001-data-loader` | **Created**: 2026-10-29 | **Status**: 🚧 Draft

## User Scenarios & Testing (mandatory)

### User Story 1 - Nạp dữ liệu 1 doanh nghiệp thành dạng truy vấn được (Priority: P1)

Hệ thống (sub-project kế tiếp — reasoning agent) cần, với mỗi doanh nghiệp (`business_id`),
có sẵn toàn bộ dữ liệu thô của doanh nghiệp đó (Excel/CSV, schema khác nhau mỗi doanh nghiệp)
ở dạng bảng có thể truy vấn (SQL), với tên cột đúng theo `README.md` của doanh nghiệp đó, kiểu
dữ liệu (số/ngày/text) đã được làm sạch, mà **không cần biết trước business đó có cấu trúc gì**.

**Why this priority**: Đây là nền tảng — không có dữ liệu sạch, không sub-project nào sau có thể
trả lời đúng câu hỏi.

**Independent Test**: Chạy loader trên 1 thư mục business thật (vd `train/data/biz_104/`), không
cần agent/LLM nào khác, kiểm tra bằng tay/script kết quả DuckDB có đúng số dòng, đúng tên cột,
đúng kiểu dữ liệu.

**Acceptance Scenarios**:

1. **Given** thư mục `train/data/biz_104/` có `README.md` + file `.xlsx`, **When** chạy loader,
   **Then** sinh ra 1 file DuckDB chứa các table tương ứng từng sheet/file, tên cột khớp đúng
   tên cột liệt kê trong `README.md`.
2. **Given** 1 cột trong file gốc có giá trị lẫn lộn `42000` (số) và `'51,000'` (chuỗi có dấu
   phẩy ngăn nghìn), **When** loader xử lý cột đó, **Then** toàn bộ giá trị được chuẩn hoá về
   cùng kiểu số, không còn ký tự dấu phẩy.
3. **Given** 1 cột số lượng có giá trị dạng `"1 kg"`, `"2 cái"` (số lẫn đơn vị), **When** loader
   xử lý, **Then** tách được thành 1 cột số lượng thuần số + 1 cột đơn vị riêng (nếu đa số giá
   trị trong cột theo đúng pattern này).
4. **Given** 1 file Excel có 2-3 dòng tiêu đề báo cáo phía trên dòng header thật (như
   `biz_118/Bảng kê phiếu giao hàng.xlsx`), **When** loader xử lý, **Then** tự định vị đúng dòng
   header thật (dựa vào danh sách cột trong README), bỏ qua các dòng rác phía trên.
5. **Given** 1 file/sheet không parse được (hỏng, cấu trúc bất thường) hoặc không khớp được với
   bất kỳ mô tả nào trong README, **When** loader chạy cho cả business đó, **Then** các table
   khác của business vẫn được tạo ra bình thường — không crash toàn bộ, chỉ log cảnh báo cho
   table lỗi.
6. **Given** 1 business có nhiều file cùng schema bị chia theo kỳ (vd `dev_005` có 17 file
   `BanHang_Thang<tháng>_<năm>.xlsx`, cùng cột, README ghi rõ "các tháng cùng cột"), **When**
   loader xử lý, **Then** các file này được **hợp nhất thành 1 table logic duy nhất** (UNION),
   không tạo ra 17 table rời rạc mà sub-project sau phải tự ghép.
7. **Given** 1 business có nhiều file hơn mức đã thấy ở `train/` (thực tế đã gặp tới 24 file/
   business ở `public_test/`, và `private_test` nhiều khả năng còn nhiều/đa dạng hơn — thêm
   ngành nghề mới ngoài 6 ngành đã biết), **When** loader chạy, **Then** vẫn hoạt động đúng mà
   không cần sửa code gì thêm (toàn bộ logic phải tổng quát theo số lượng/loại file, không giả
   định trước số file hay loại ngành).

### Edge Cases

- ⚠️ File/sheet rỗng (0 dòng dữ liệu) → bỏ qua, không tạo table rỗng.
- ⚠️ README không nhắc tới 1 file nào đó, hoặc mô tả cột không khớp dữ liệu thật → vẫn tạo table
  bằng heuristic dự phòng, gắn cờ độ tin cậy thấp để sub-project sau biết mà cẩn trọng.
- ⚠️ Cột không thể xác định rõ kiểu dữ liệu (không theo pattern số/ngày/unit nào) → giữ nguyên
  dạng text thô, không ép kiểu sai.
- ⚠️ Business mới chưa từng thấy (schema hoàn toàn khác 30 business trong `train/`, như
  `dev_00x` trong `public_test/`) → loader phải tự hoạt động được, không được viết logic riêng
  cho bất kỳ `business_id` cụ thể nào (vi phạm rule 4 của cuộc thi).

## Requirements (mandatory)

### Functional Requirements

- **FR-001**: Hệ thống MUST đọc được `README.md` của 1 business và trích ra danh sách tên cột
  được khai báo cho từng file dữ liệu của business đó.
- **FR-002**: Hệ thống MUST đọc được cả file `.csv` và `.xlsx` (nhiều sheet), với mọi business
  trong `train/data/` và `public_test/data/`.
- **FR-003**: Hệ thống MUST tự định vị đúng dòng header thật của mỗi file/sheet, kể cả khi có
  dòng tiêu đề/rác phía trên dòng header.
- **FR-004**: Hệ thống MUST chuẩn hoá giá trị số bị viết dạng chuỗi có dấu phẩy ngăn nghìn
  (`"51,000"` → `51000`) về kiểu số thống nhất trong cùng 1 cột.
- **FR-005**: Hệ thống MUST tách được số lượng kèm đơn vị (`"1 kg"`) thành số + đơn vị khi phần
  lớn giá trị trong cột theo đúng pattern đó.
- **FR-006**: Hệ thống MUST ghi kết quả đã làm sạch vào DuckDB — mỗi business 1 file, mỗi
  file/sheet gốc tương ứng 1 table.
- **FR-007**: Hệ thống MUST sinh kèm 1 bản tóm tắt schema (tên cột, kiểu dữ liệu, số dòng, vài
  giá trị mẫu, độ tin cậy xác định header) cho mỗi table, cùng nguyên văn `README.md`.
- **FR-008**: Hệ thống MUST tiếp tục xử lý các file/table khác của cùng business khi 1 file/sheet
  thất bại, không dừng toàn bộ.
- **FR-009**: Hệ thống MUST NOT chứa bất kỳ logic rẽ nhánh theo `business_id` cụ thể (vd
  `if business_id == "biz_104"`) — mọi xử lý phải tổng quát cho cấu trúc file bất kỳ.
- **FR-010**: Hệ thống MUST chạy lại được nhiều lần cho cùng 1 business và cho ra kết quả giống
  nhau (idempotent), ghi đè sạch kết quả cũ.
- **FR-011**: Hệ thống MUST phát hiện các file cùng schema (cùng tập tên cột sau khi chuẩn hoá)
  bị chia theo kỳ/tháng trong cùng 1 business, và **hợp nhất thành 1 table duy nhất** (UNION),
  dựa trên: (a) mô tả tường minh trong README nếu có (vd dev_005), (b) fallback — so khớp tên
  cột giống nhau giữa các file có tên tương tự (cùng tiền tố, khác hậu tố tháng/năm) khi README
  không nói rõ.
- **SHOULD-012**: Hệ thống NÊN phát hiện khoá liên kết khả dĩ giữa các table khác schema trong
  cùng business (vd `Mã đơn hàng` ở `chi_tiet_don` khớp giá trị với `Số phiếu` ở `don_hang`) bằng
  cách so sánh độ phủ giá trị giữa các cột, ghi vào schema summary dưới dạng gợi ý (không bắt
  buộc đúng 100%) — giúp sub-project `004-reasoning-agent` viết SQL join đúng hơn. Không phải
  MUST cho v1 vì agent vẫn có thể tự suy ra từ tên cột + README; làm sau nếu còn thời gian trước
  deadline 16/11.
- **FR-013**: Hệ thống MUST đọc `rulebook.md` đi kèm bộ dữ liệu (không phải bản cố định nào khác)
  và đưa nguyên văn vào output cho sub-project sau dùng — vì nội dung rulebook khác nhau giữa
  `train`/`public_test`/`private_test` (xem constitution.md).

## 🎯 Success Criteria (mandatory)

- **SC-001**: Chạy loader trên toàn bộ 30 business trong `train/data/` không có business nào bị
  crash hoàn toàn (tối thiểu tạo được ≥1 table hợp lệ/business).
- **SC-002**: Với các cột được câu hỏi mẫu trong `train/questions.jsonl` tham chiếu tới (doanh
  thu, số lượng, ngày...), tỉ lệ giá trị parse ra đúng kiểu số/ngày (không rơi về `raw`/`NaN`
  ngoài dự kiến) đạt ít nhất 95%.
- **SC-003**: Toàn bộ thời gian xử lý 30 business trong `train/` dưới 2 phút trên máy dev (laptop
  16GB RAM) — vì đây chỉ là bước chuẩn bị dữ liệu, không phải bước tốn thời gian chính của pipeline.
- **SC-004**: Chạy lại loader trên cùng input 2 lần → schema summary giống nhau 100% (không có
  phần ngẫu nhiên).

## 💡 Assumptions

- README của mỗi business theo format bullet khá nhất quán
  (`- **TênCột**: mô tả`), dù có thể lệch nhẹ về khoảng trắng/định dạng.
- Dữ liệu `dev_00x` (public_test) có thể dùng file khác tên (`SoGiaoHang.xlsx` thay vì
  `DonHang_ChiTiet.xlsx`) nhưng vẫn theo cùng dạng "README mô tả cột + file Excel/CSV thô".
- Việc áp dụng **quy đổi đơn vị kinh doanh** (ví dụ "1 thùng = 24 lon" trong README biz_129)
  KHÔNG thuộc phạm vi sub-project này — đó là suy luận ngữ nghĩa, để sub-project
  `004-reasoning-agent` tự đọc README và xử lý lúc trả lời câu hỏi.
- ⚠️ **Đã kiểm chứng lại (29/10)**: số file/business dao động rất rộng — từ 2 (`dev_006`,
  `dev_009`, `dev_011`) tới **24** (`dev_005`), và `train/data/biz_124` cũng có 14 file — không
  phải toàn business chỉ có 3-7 file như mẫu ban đầu xem qua. `private_test` nhiều khả năng còn
  rộng hơn + thêm ngành nghề mới ngoài 6 ngành đã thấy trong `rulebook.md`. Thiết kế loader PHẢI
  tổng quát theo số lượng/loại file, test coverage khi implement phải chạy qua **toàn bộ 30
  business `train/` + toàn bộ 14 business `public_test/`**, không chỉ vài mẫu đã xem khi
  brainstorm.
