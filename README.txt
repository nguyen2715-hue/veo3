
VideoUltra v1.0.0.1 — App Header + Tab "Video bán hàng"

Mục tiêu:
- Tiêu đề ứng dụng ở đỉnh: "Video Super Ultra" (đậm 14px) + "Version: V..." (14px, đọc utils/version.py).
- Thay tab "Video quảng cáo" bằng "Video bán hàng" (bố cục 1/3 | 2/3, các trường theo yêu cầu).

Tích hợp (không chạm vùng đã khóa):
1) App header: thêm widget vào top của main window (trước TabWidget). Header cập nhật version tự động.
2) Đổi tab: đổi label sang "Video bán hàng" và gắn panel từ ui/video_ban_hang_panel.py.
3) Kiểm tra: tên dự án mặc định, ảnh xem trước 128×128, sinh outline/prompt cục bộ, khởi tạo thư mục & log dự án.

Không thay đổi Tab Cài đặt / Image2Video / Text2Video / kết nối Labs Flow.
