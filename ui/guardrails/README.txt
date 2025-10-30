VideoUltra Guardrails (UI) — v1.0.0.1

Mục tiêu: chặn lỗi 400 trước khi gửi request.

Cách dùng (không cần thay đổi logic server):
1) Thu thập các trường đầu vào của job (prompt, width, height, fps, duration, project_id).
2) Gọi hàm kiểm tra trong services/validators.validate_video_job(...) trước khi tạo payload gửi API.
3) Nếu có lỗi:
   - Hiển thị danh sách lỗi cho người dùng.
   - Không gọi API cho tới khi hết lỗi.
4) Nếu không lỗi: cho phép bấm chạy.

Gợi ý UI/UX:
- Disable nút "Chạy" khi đang có lỗi; highlight trường lỗi.
- Suggest kích thước mặc định 512×512 (chia hết cho 16), fps 24, duration 5–10s.

Không cần thay đổi UI hiện tại nếu đã có nơi gom dữ liệu trước khi gửi — chỉ cần chèn bước validate.
