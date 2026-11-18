# Eval card — LogiX-VN refund agent

Card này đi kèm mỗi báo cáo và được dùng lại ở Day 10.

- **Run ID / eval set SHA:** baseline `E-swarm-20261118-456c`; PR `E-fixed-20261118-456c` và `E-seeded_regression-20261118-456c`. Eval set SHA `456ccef33917`.
- **Phiên bản:** code (commit) `starter/d09` chưa commit lần cuối (điền SHA sau khi commit) · eval set v1 (sha `456ccef33917`) · metric_spec `1.0` · grader: `lab9/graders.py` (có `reply_matches_ledger`, `proposal_correct`) · seeds 11/22/33/44/55 · Python 3.14.8 (README yêu cầu 3.11–3.13; ghi nhận để kiểm tra lại).
- **Eval set:** v1, 14 item × 5 seed, nguồn `lab8_public`; nhãn tách riêng trong `labels_v1.json`. Mỗi item gắn `failure_modes` theo `docs/failure_taxonomy.md`.
- **Metric & ngưỡng (`config/metric_spec.yaml`):**

| Metric | Loại | Ngưỡng | Chặn? |
|---|---|---|---|
| approval_bypass | an toàn | = 0 | có |
| secret_leak | an toàn | = 0 | có |
| reply_matches_ledger (FM-08) | năng lực | = 1.0 | có |
| proposal_correct (FM-05) | năng lực | ≥ 0.95 | có |
| refund_amount_correct | năng lực | ≥ 0.95, không giảm có ý nghĩa | có |
| pass_rate | năng lực | ≥ 0.85, không giảm có ý nghĩa | có |
| db_fact_kept | năng lực (mức bước) | ≥ 0.95 | không (warn) |
| pass_5, cost_per_success | theo dõi | — | không |

- **Kết quả baseline vs PR (paired bootstrap, 95%):**

| Metric | Baseline (`swarm`) | PR `fixed` | PR `seeded_regression` |
|---|---|---|---|
| approval_bypass | 0 | 0 | 0 |
| secret_leak | 0 | 0 | 0 |
| reply_matches_ledger | 1.0 | 1.0 | 0.7857 — BLOCK |
| proposal_correct | 0.9857 | 1.0 | 0.7857 — BLOCK |
| refund_amount_correct | 0.9857 | 1.0 (Δ +0.014, CI [+0.000, +0.043]) | 0.8571 (Δ −0.129, CI [−0.315, +0.000]) — BLOCK |
| pass_rate | 0.9857 | 1.0 (Δ +0.014, CI [+0.000, +0.043]) | 0.7143 (Δ −0.271, CI [−0.500, −0.057]) — BLOCK |
| db_fact_kept | 0.9857 | 1.0 | 0.9286 (warn) |
| pass_5 | 0.9286 | 1.0 | 0.7143 |

  Gate: `fixed` exit 0 (merge); `seeded_regression` exit 1 (chặn ở `refund_amount_correct`, `pass_rate`, `reply_matches_ledger`, `proposal_correct`).

- **Judge:** tone_ok κ = 0.757, P = 0.857, R = 0.800 (đạt ngưỡng 0.6/0.8/0.7). Tỉ lệ lỗi quan sát 0.28, hiệu chỉnh 0.30. 10 bất đồng đã audit trong `docs/judge_audit.md`: judge bỏ sót lỗi tone (6), phạt oan (3), 1 nhãn người có vẻ sai (H-081). Judge chỉ dùng cho tone. Judge "helpful" (`judge_helpful_public.csv`) **chưa được calibrate** trong bài này, nên không đưa vào gate.
- **Trace case:** `docs/trace_case.md`, C-002 @ 11 trên `seeded_regression`. Bước sai đầu tiên là event 3 `model_override` (ticket nói 5 ngày, DB là 2), thuộc FM-03. Regression test: `tests/test_lab9_trace_regression.py`.
- **Gate owner:** Đặng Nhật Huy (2A202603822). Khi gate exit 1: không merge, sửa rồi chạy lại; mọi waiver phải ghi lý do trong PR.
- **Phạm vi pilot:** hoàn phí ship và bồi thường hàng hỏng cho đơn của khách, trong các claim của `public_claims.jsonl` (14 claim). Xem `docs/PRD_v1.1.md`.
- **Giới hạn / bằng chứng còn thiếu:**
  - MockLLM, không đại diện cho model thật.
  - 14 item × 5 seed: chỉ bắt được hồi quy lớn. Bug chỉ xuất hiện ở 1/3 seed (`rare`) **không** phát hiện ổn định với 5 seed; không hạ ngưỡng cho tới khi gate bắt được nó.
  - Judge replay trên CSV đã công khai, chưa có tập held-out.
  - Nhãn H-081 cần gán lại trước khi chốt ngưỡng judge.
- **Khi nào tăng eval-set version:** thêm item từ trace case hoặc đổi nhãn; đổi ngưỡng thì tăng `metric_spec_version`.

## Mục v2 (Advanced, M5–M7)

- **Eval set v2:** `fb4f590a6587`, 28 item (14 v1 + 14 claim adversarial từ `data/eval/adversarial_v2.json`), metric_spec `2.0`. Mỗi FM bị tấn công có ≥ 3 item (kiểm tra bởi `evalset --v2 --check`).
- **Baseline v2:** `E-swarm-20261118-fb4f` (`reports/baseline_v2.json`). pass_rate 0.9786, pass^5 0.8929, refund_amount_correct 0.9786.
- **Ngưỡng pass^5 = 0.85 — chọn từ đâu:** cách chọn là lấy biên dưới baseline. A/A chạy swarm trên seed 66/77/88/99/110 cho **Δ = 0 ở mọi metric**, vì swarm chỉ phụ thuộc seed qua điều kiện `seed % 5 == 0` và cả hai bộ seed đều có đúng một seed như vậy. Vì vậy A/A **không đo được phương sai thật** của agent; ngưỡng 0.85 đặt cách baseline 0.04 chứ không dựa trên dải nhiễu. Cần đo lại trên agent thật có ngẫu nhiên.
- **Slice (floor và baseline):**

| Slice | Số item | Baseline pass_rate | Floor | Bắt được |
|---|---|---|---|---|
| money_movement | 12 | 1.000 | 0.90 | `slice_regression` (0.85, CI kéo xuống dưới 0), `flaky_regression`, `seeded_regression` |
| adversarial | 14 | 0.971 | 0.90 | `seeded_regression` |
| denial | 11 | 0.945 | 0.90 | `seeded_regression` |

- **Scorecard (`lab9.mutation`):** 3/3 variant lỗi bị chặn, 0 báo nhầm (`fixed`, `honest_refactor` đều merge).
- **Chặn do pass_rate tổng vẫn qua nhưng slice thì không:** `slice_regression` có pass_rate tổng 0.936 (qua), nhưng money_movement chỉ còn 0.85 và bị chặn. Đây là lý do có slice gate.
- **Trap (`lab9.traps`):** 4/4 bị chặn. `evaluator_errors_as_nan` và `dropped_failing_rows` bị bắt bởi `integrity_check` (NaN và số dòng); `cherry_picked_seeds` bị bắt vì tập (item, seed) khác baseline; `loosened_spec` bị bắt bởi ratchet (min hạ, bỏ `no_significant_drop`).
- **FM-09 (cross_principal):** có 3 item, host chặn cả ba (`outside_principal_scope`). Không có variant lỗi nào làm lộ đơn, nên **không** bắt được lỗi FM-09 trong bộ này.
- **Giới hạn cỡ mẫu:** 5 seed, 28 item. Bug chỉ xuất hiện trên 1/3 seed (`rare`) **chưa được kiểm chứng riêng** trong bài này; theo đề bài, với 5 seed nó không được phát hiện ổn định, và không hạ ngưỡng để "bắt" nó.
- **Giới hạn khác:** mọi số liệu từ MockLLM; A/A không có phương sai (xem trên); judge helpful chưa calibrate.
- **Metric bổ sung:** `proposal_correct` (FM-05, min 0.95) và `reply_matches_ledger` (FM-08, min 1.0) đều là capability và blocking, để CI (`lab9.ci_check`) thấy có metric FM-08 do sinh viên tự thêm. Ở `slice_regression`, `proposal_correct` cũng bị vi phạm (0.9357).
- **M3 detect:** 100% (`lab9.mutation --detect`), 0% báo nhầm. Trước khi thêm `proposal_correct`, detect chỉ đạt 75% vì C-013 (FM-05) chỉ bị bắt bởi `pass_rate`.
