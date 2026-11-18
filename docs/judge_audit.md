# Judge audit (M2): judge tone trên 100 phản hồi

Lệnh: `python -m lab9.judge --csv data/eval/judge_tone_public.csv --audit 5`. Nhãn dương là `FAIL` (judge tìm lỗi).

## Kết quả calibration

| Chỉ số | Giá trị | Ngưỡng | Kết quả |
|---|---|---|---|
| Confusion (tp/fp/fn/tn) | 24 / 4 / 6 / 66 | — | — |
| Precision | 0.857 | ≥ 0.8 | đạt |
| Recall | 0.800 | ≥ 0.7 | đạt |
| Cohen's kappa | 0.757 | ≥ 0.6 | đạt |
| Tỉ lệ lỗi quan sát | 0.28 | — | — |
| Tỉ lệ lỗi hiệu chỉnh (Rogan-Gladen) | 0.30 | — | — |

Judge đạt cả ba ngưỡng. Tuy nhiên có 10 bất đồng, và phần lớn là judge dễ dãi với lỗi tone (6/10), không phải judge quá khắt khe.

## Audit 10 bất đồng

Đã đọc đủ 10 bất đồng (không chỉ 5 đầu tiên). Phân loại theo nguyên nhân.

### Nhóm A: judge bỏ sót lỗi tone (FN, 6 case)

| Item | Human | Judge | Phản hồi (rút gọn) | Nguyên nhân |
|---|---|---|---|---|
| H-008 | FAIL | PASS | "Em đã hoàn tiền cho anh rồi nha" | Xưng "em" + "nha" với khách quá suồng sã; judge coi là thân thiện |
| H-017 | FAIL | PASS | "bạn ơi LogiX đã hoàn..." | Xưng "bạn" với khách lớn tuổi; judge bỏ qua quan hệ xưng hô |
| H-029 | FAIL | PASS | "vui lòng chờ... không cần nhắn thêm" | Giọng ra lệnh; judge chỉ thấy từ lịch sự "Dạ, vui lòng" |
| H-063 | FAIL | PASS | "sẽ hoàn thêm cho anh/chị" | Hứa ngoài kết quả hệ thống; judge không đối chiếu với ledger |
| H-070 | FAIL | PASS | "ạ 😂😂" | Emoji không hợp ngữ cảnh khiếu nại |
| H-094 | FAIL | PASS | "Da, LogiX da hoan..." (không dấu) | Dịch máy/mất dấu; judge không coi là lỗi tone |

**Nhận xét:** judge chỉ nhìn các dấu hiệu lịch sự (Dạ, ạ, vui lòng) và bỏ qua quan hệ xưng hô, giọng điệu và lời hứa ngoài hệ thống. Đây là điểm yếu có hệ thống, không phải ngẫu nhiên.

### Nhóm B: judge phạt oan (FP, 3 case)

| Item | Human | Judge | Phản hồi | Nguyên nhân |
|---|---|---|---|---|
| H-042 | PASS | FAIL | "Dạ, đơn O-808 đã hoàn 120.000đ..." | Judge phạt vì thiếu lời xin lỗi; human thấy ngắn gọn đủ ý là đạt |
| H-051 | PASS | FAIL | "LogiX đã refund 90.000đ" | Judge phạt từ "refund"; CS LogiX cho phép dùng từ này |
| H-088 | PASS | FAIL | "Dạ, dạ, LogiX đã hoàn..." | Lặp "Dạ" do lỗi gõ; human cho qua, judge phạt |

**Nhận xét:** judge quá nghiêm ở các quy tắc phong cách (xin lỗi, tiếng Anh, lặp từ). Những quy tắc này trong thực tế CS không xem là lỗi tone.

### Nhóm C: nghi ngờ nhãn người sai (1 case)

| Item | Human | Judge | Phản hồi | Ghi chú |
|---|---|---|---|---|
| H-081 | PASS | FAIL | "đơn O-107 chưa đủ điều kiện hoàn theo chính sách" | Ghi chú của người gán: "đọc nhầm ticket, judge đúng, sửa nhãn". Phản hồi từ chối hoàn tiền là đúng với O-107 theo quy định, nên judge đúng. |

**Quyết định:** không sửa `judge_tone_public.csv` trong M2. Nhãn đã sai nhưng nếu sửa, confusion đổi thành tp=25, fp=3, fn=6 và các giá trị tham chiếu trong `tests/test_lab9_stats.py` không còn khớp. Ghi nhận như một phát hiện: nhãn cần gán lại, và số liệu calibration hiện tại có thể đánh giá judge thấp hơn thực tế một chút.

## Kết luận và việc tiếp theo
1. Judge đạt ngưỡng nhưng yếu ở tone (nhóm A). Trước khi dùng judge trong gate, cần thêm rubric cụ thể: xưng hô, giọng ra lệnh, hứa ngoài hệ thống, emoji, và chất lượng tiếng Việt (dấu).
2. Nới rubric về xin lỗi, từ tiếng Anh đã được CS chấp nhận và lặp từ không gây hiểu sai (nhóm B) để judge không phạt oan.
3. Gán lại nhãn H-081 và tính lại calibration trước khi chốt ngưỡng.
4. Judge chỉ được dùng cho tone. Tiền và approval vẫn chấm bằng code (`RefundAmountCorrect`, `ApprovalBypass`).
