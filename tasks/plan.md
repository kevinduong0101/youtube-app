# Kế Hoạch Cải Tiến Toàn Diện: AutoSub Pro

## 1. Đánh Giá Hiện Trạng Kỹ Thuật (Architecture & Product Audit)

| Tiêu chí | Trạng thái hiện tại | Vấn đề cốt lõi | Hướng giải quyết chuẩn công nghiệp |
|---|---|---|---|
| **Độ khớp phụ đề (Sync & Rhythm)** | Trung bình (6/10) | Cắt cụm cứng `MAX_WORDS = 6` bỏ qua nhịp thở; Whisper `base` lệch timestamp 200-400ms | Chunking theo khoảng lặng (Pause-aware VAD); Tích hợp Whisper tối ưu (Whisper Small / faster-whisper) |
| **Trải nghiệm người dùng (UX)** | Yếu (4/10) | Quy trình "Hộp đen": Render xong mới thấy kết quả, sai 1 chữ phải render lại từ đầu | Quy trình 2 pha: **Bóc băng & Preview/Sửa text** -> **Render xuất file** |
| **Tốc độ xử lý (Performance)** | Chậm (5/10) | CPU software encoding (`libx264`) kèm bộ lọc `hqdn3d` nặng nề | Tối ưu hóa chuỗi filter FFmpeg; Hỗ trợ hardware acceleration trên Mac (`videotoolbox`) |
| **Chất lượng hình ảnh & Tỷ lệ** | Cứng nhắc (5/10) | Ép cứng 1080x1920 thêm viền đen mù quáng cho mọi loại video | Tùy chọn: Giữ nguyên tỷ lệ gốc (Original) HOẶC Chuyển đổi 9:16 (Shorts/TikTok) |
| **Bảo mật & Mã nguồn** | Cần dọn dẹp (5/10) | Hardcode API key trong code; Tồn tại nhiều hàm dead code | Loại bỏ secret ra khỏi git; Dọn dẹp clean architecture |

---

## 2. Lộ Trình Cải Tiến (Phase Breakdown)

### Pha 1: Tối ưu Lõi Nhận Diện & Thuật toán Chia Cụm (Core Engine & Sync)
- **Tách cụm thông minh (Smart Rhythm Chunking):** Không ngắt cứng 6 từ. Tự động ngắt khi phát hiện khoảng lặng (silence gap > 0.35s) hoặc gặp dấu câu (`,`, `.`, `?`), giữ mỗi cụm từ 3-5 từ dễ đọc trên điện thoại.
- **Tùy chọn Model Whisper:** Cho phép chọn giữa mô hình `base` (nhẹ) và `small` (chính xác hơn nhiều cho tiếng Việt).
- **Loại bỏ Secret & Dead Code:** Di chuyển API Key vào cấu hình an toàn, loại bỏ các hàm không còn sử dụng.

### Pha 2: Nâng Cấp UX - Quy Trình 2 Giai Đoạn (Preview & In-Place Editor)
- **Giai đoạn 1 - Bóc băng & Chỉnh sửa:**
  - Nhận diện giọng nói -> Hiển thị danh sách các câu kèm timestamp.
  - Cho phép người dùng bấm vào sửa trực tiếp từng từ nếu AI nhận diện nhầm.
- **Giai đoạn 2 - Xem trước (Live Frame Preview):**
  - Trích xuất 1 frame mẫu có áp style phụ đề để người dùng duyệt vị trí, font, màu sắc trước khi xuất video.
- **Giai đoạn 3 - Xuất bản (Export):**
  - Chỉ render FFmpeg khi người dùng đã hoàn toàn hài lòng với nội dung và giao diện.

### Pha 3: Tối Ưu Render & Tỷ Lệ Video (FFmpeg & Export Options)
- **Quản lý Tỷ lệ khung hình:** Tùy chọn giữ nguyên khung hình gốc hoặc ép tỷ lệ 9:16.
- **Tăng tốc Render:** Tối ưu bộ lọc FFmpeg, loại bỏ các filter làm chậm không cần thiết, hỗ trợ export nhanh.
- **Preset Phụ đề Đỉnh Cao:** Tinh chỉnh các style chữ (YouTube Vlog, TikTok Badge, Minimalist) với kích thước và khoảng cách dòng chuẩn thị giác mạng xã hội.

---

## 3. Rủi Ro & Biện Pháp Kiểm Soát (Risks & Mitigations)

| Rủi ro | Mức độ | Biện pháp kiểm soát |
|---|---|---|
| Model Whisper lớn hơn chạy tốn RAM | Trung bình | Mặc định `base`, cung cấp tùy chọn `small` có cảnh báo tài nguyên |
| Preview video trên Streamlit gây lag trình duyệt | Thấp | Chỉ preview frame ảnh tĩnh đại diện (Single Frame Preview) thay vì re-render toàn bộ video |
| Lỗi đường dẫn font tiếng Việt trên macOS | Thấp | Kiểm tra và fallback về hệ thống font an toàn nếu file font không nạp được |
