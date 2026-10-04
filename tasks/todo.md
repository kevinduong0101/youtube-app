# Danh Sách Nhiệm Vụ Thực Thi (Task Checklist)

## Pha 1: Nâng Cấp Lõi Đồng Bộ & Thuật Toán Chia Cụm (Core Engine)
- [x] **Task 1.1**: Tái cấu trúc thuật toán chia cụm phụ đề (`Smart Rhythm Chunking`) dựa trên khoảng lặng (silence gap > 0.35s) và dấu câu thay vì cắt cứng 6 từ.
- [x] **Task 1.2**: Thêm tùy chọn chọn mô hình Whisper (`base` hoặc `small`) để tăng độ chính xác nhận diện từ và timestamp tiếng Việt.
- [x] **Task 1.3**: Dọn dẹp dead-code trong `core/subtitle_engine.py` và bảo mật API Key (loại bỏ hardcoded secrets).

## Checkpoint 1: Xác minh Lõi Nhận Diện
- [x] Kiểm thử bóc băng với video có nhịp thở ngắt quãng: xác nhận phụ đề không bị treo ngang qua đoạn im lặng.
- [x] Codebase sạch, không còn hardcoded secrets.

---

## Pha 2: Nâng Cấp Quy Trình 2 Bước & Trình Chỉnh Sửa Trực Tiếp (Interactive UX)
- [x] **Task 2.1**: Tách quy trình trên giao diện `app.py`: Bước 1 (Trích xuất & Bóc băng) -> Hiển thị Bảng xem trước danh sách câu.
- [x] **Task 2.2**: Cho phép chỉnh sửa trực tiếp nội dung từng câu trên giao diện trước khi xuất video.
- [x] **Task 2.3**: Tạo tính năng "Xem trước 1 Frame (Preview Frame)" để hiển thị ảnh mẫu kèm subtitle theo font/vị trí đã chọn mà không cần render cả video.

## Checkpoint 2: Trải Nghiệm Người Dùng
- [x] Người dùng xem được trước font, vị trí, nội dung chữ trong vòng dưới 1 giây.
- [x] Sửa được lỗi chính tả trực tiếp trên giao diện mà không cần chạy lại từ đầu.

---

## Pha 3: Tối Ưu Hóa Render & Tỷ Lệ Khung Hình (FFmpeg Engine)
- [x] **Task 3.1**: Bổ sung tùy chọn Tỷ lệ khung hình: "Giữ tỷ lệ gốc" hoặc "Chuẩn 9:16 TikTok/Shorts".
- [x] **Task 3.2**: Tối ưu chuỗi filter FFmpeg để tăng tốc độ render xuất file, giữ nguyên 100% âm thanh gốc qua `-c:a copy`.
- [x] **Task 3.3**: Hoàn thiện preset phụ đề YouTube Vlog và TikTok Karaoke với độ tương phản sắc nét.

## Checkpoint 3: Hoàn Tất Dự Án
- [x] Đã chạy kiểm thử E2E: Tất cả các luồng render, preview và trích xuất kích thước đều đạt 100%.
