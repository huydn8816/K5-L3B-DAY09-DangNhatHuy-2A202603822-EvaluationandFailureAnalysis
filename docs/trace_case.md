# Trace case: từ trace tới quyết định sai đầu tiên

Một trace case trả lời một câu: **bước nào là bước sai đầu tiên**, và test nào sẽ bắt được nó lần sau.

```bash
cd src
python -m lab9.trace_case --shape seeded_regression --claim C-002 --seed 11
python -m lab9.trace_case --shape fixed --claim C-002 --seed 11   # đối chứng
```

## Case đã điền: C-002 @ seed 11 (`seeded_regression`)

| Trường | Nội dung |
|---|---|
| Trial | `seeded_regression C-002@11`, thuộc run `E-seeded_regression-20261118-456c` (eval set `456ccef33917`) |
| Triệu chứng | `TrialPass` (lab8) fail: status `resolved`, nhãn `denied`. Ledger ghi `refund_vnd=20000`, `refund_count=1`; nhãn là 0 và 0. `RefundAmountCorrect` = False, `DbFactKept` = False. Reply nói "Dạ, LogiX đã hoàn 20.000đ cho đơn O-202." |
| Bước sai đầu tiên | **Event 3, `model_override`**, payload `{"delay_days": 5}`. Đây là lần agent ghi đè số ngày trễ bằng số trong ticket. |
| Vì sao là bước *đầu tiên* | Event 1 (`handoff`) đúng phạm vi: `owner_order_only`. Event 2 (`investigator`) đọc đúng đơn `O-202` từ DB với `delay_days = 2`. Chỉ đến event 3 số liệu bị đổi sang 5. Event 4 (`quote`) tính 20.000đ theo `SHIP-LATE-03` dựa trên số 5 đã bị ghi đè, nên đây là hệ quả, không phải nguyên nhân. |
| Failure mode | **FM-03** `ticket_trust` (`docs/failure_taxonomy.md`) |
| Đối chứng | `fixed C-002@11`: event 2 vẫn đọc `delay_days = 2`, không có event `model_override`. Quote `no_entitlement`, reply "chưa đủ điều kiện", ledger 0. Khớp nhãn. |
| Regression test | `tests/test_lab9_trace_regression.py` gồm 3 test: `test_ticket_trust_is_caught_at_the_step` (DbFactKept = False trên `seeded_regression`), `test_ticket_trust_is_caught_at_the_outcome` (RefundAmountCorrect và TrialPass = False), `test_fixed_shape_keeps_db_fact` (cả ba = True trên `fixed`). Cả 3 pass trên bản hiện tại. |
| Chưa chắc chắn | Trace không chứng minh được vì sao `seeded_regression` chọn ghi đè ở event 3. Bug `ticket_trust` bật cố định trong variant này, còn bản gốc chỉ tin ticket ở seed chia hết cho 5. Trace chỉ cho thấy hành vi, không cho thấy lý do nội tại của model. |

## Mẫu điền (dùng cho case tiếp theo)

| Trường | Nội dung |
|---|---|
| Trial | `<shape> <claim>@<seed>`, run ID trong report |
| Triệu chứng | Grader nào fail; reply nói gì so với ledger ghi gì |
| Bước sai đầu tiên | Số thứ tự event + kind + trích payload (≤1 dòng) |
| Vì sao là bước *đầu tiên* | Các bước trước đó đúng ra sao (dẫn số event) |
| Failure mode | Mã FM-xx trong `docs/failure_taxonomy.md` |
| Đối chứng | Cùng claim@seed trên shape `fixed`: bước đó khác thế nào |
| Regression test | Tên test + grader/assert nào bắt được; đã thấy fail trên variant lỗi và pass trên `fixed` chưa |
| Chưa chắc chắn | Điều trace không chứng minh được |

## Quy tắc

- Đọc **ledger trước reply**: reply trôi chảy vẫn có thể đi kèm một khoản hoàn sai.
- "Bước sai đầu tiên" phải dẫn số event cụ thể, không phải "agent bị nhầm".
- Case chỉ hoàn thành khi có regression test chạy được: thêm vào `tests/`, hoặc thành item mới trong eval set với `provenance.from_trace`.
