<div align="center">
  <img src="https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=Streamlit&logoColor=white" />
  <img src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/FFmpeg-007808?style=for-the-badge&logo=FFmpeg&logoColor=white" />
  <img src="https://img.shields.io/badge/OpenAI_Whisper-412991?style=for-the-badge&logo=openai&logoColor=white" />
</div>

<h1 align="center">🎬 AutoSub Pro - AI Subtitle Generator</h1>

<p align="center">
  Công cụ tạo phụ đề tự động siêu việt dành cho <b>TikTok, YouTube Shorts, và Reels</b>. Tích hợp AI bóc băng chính xác, tự động ghép nhịp, và bộ lọc xử lý hình ảnh/âm thanh chuẩn Studio!
</p>

---

## 🌟 Tính Năng Nổi Bật

### 🎯 Phụ Đề Năng Động (Karaoke Highlights)
- **3 Phong cách chuyên nghiệp**: 
  - 🕺 `TikTok Karaoke`: Chữ nhảy màu với viền nền đen mờ (Chống lẹm sub gốc).
  - 🎥 `YouTube Vlog`: Viền chữ đen siêu dày, sắc nét.
  - 🍿 `Netflix Style`: Tiêu chuẩn điện ảnh thanh lịch.
- **Tùy biến Font chữ**: Tự do tải lên bất kỳ font tiếng Việt nào (`.ttf`, `.otf`). Mặc định sử dụng font *UVN Ban Tay*.
- **Forced Alignment (Ghép nhịp tự động)**: Thuật toán *SequenceMatcher* đảm bảo chữ bắt dính vào mốc mili-giây của âm thanh, dù bạn có sửa lại kịch bản!
- **Độ trễ Phụ đề (Offset)**: Tinh chỉnh thời gian chữ xuất hiện sớm hay muộn tùy ý.

### 🎛️ Nâng Cấp A/V Chuẩn Studio (FFmpeg Engine)
- **Khử ồn & Nén âm lượng**: Tích hợp bộ lọc âm thanh cực mạnh (`highpass`, `treble`, `loudnorm`, `acompressor`) giúp giọng đọc trong vắt và rõ ràng.
- **Enhance Hình Ảnh**: Khử nhiễu hột (`hqdn3d`), làm nét (`unsharp`), và tăng cường màu sắc (`eq`).
- **Ép khung TikTok**: Tự động crop hoặc thêm viền đen (padding) để xuất file đúng chuẩn dọc `1080x1920`.
- **Export Specs**: Xuất video chuẩn vàng `30 FPS`, codec `H.264`, âm thanh `AAC 320kbps`, hệ màu `Rec.709`.

### 🤖 AI Dubbing & Tự Động Chọn Nhạc Nền (BGM)
- Tự động gợi ý nhạc nền phù hợp với "vibe" của giọng đọc thông qua LLM (Llama 3.1).
- Trộn nhạc nền tự động giảm âm lượng (ducking) không làm chìm giọng chính.

## 🚀 Cài Đặt (Installation)

1. **Yêu cầu hệ thống**: Python 3.10+, FFmpeg đã cài đặt và thêm vào biến môi trường.
2. **Clone repo và cài đặt thư viện**:
```bash
git clone https://github.com/kevinduong0101/youtube-app.git
cd youtube-app
pip install -r requirements.txt
```
3. **Cấu hình API**: 
Tạo file `.env` hoặc điền khóa API NVIDIA (Llama 3.1) trực tiếp trên giao diện để sử dụng tính năng Auto-sync và BGM.

## 🎮 Hướng Dẫn Sử Dụng
Chỉ với 1 dòng lệnh để khởi động Web App:
```bash
streamlit run app.py
```
1. **Chế Độ 1 (Bọc Phụ Đề Nhanh)**: Tải lên `Video gốc` -> Bấm Xử Lý.
2. **Chế Độ 2 (Lồng Tiếng AI)**: Tải lên `Video gốc` + `File Âm Thanh` -> Hệ thống tự động cắt ghép video cho khớp với tiếng!

---
<div align="center">
  <i>Được phát triển để giúp quá trình edit video ngắn trở nên dễ dàng và rực rỡ hơn bao giờ hết! ✨</i>
</div>
