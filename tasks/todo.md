# Danh Sách Nhiệm Vụ: Nâng Cấp Hệ Thống Hiệu Ứng Chữ Kinetic Typography (JIZURA-Inspired)

- [x] **Task 1: Nghiên Cứu Mã Nguồn JIZURA (852wa/JIZURA)**
  - [x] Phân tích công thức chuyển động vật lý lò xo (Damped Spring Physics `sprg`), co giãn hoạt họa (Squash & Stretch), lắc góc (Kinetic Tilt), và tách lớp Chromatic Glitch.
- [x] **Task 2: Lập Kế Hoạch & Thiết Kế Kiến Trúc Kinetic ASS**
  - [x] Tạo `implementation_plan.md` chi tiết và nhận phê duyệt từ người dùng.
- [x] **Task 3: Nâng Cấp Lõi `core/subtitle_engine.py`**
  - [x] Tích hợp bộ sinh thẻ `get_kinetic_motion_tags`: Elastic Spring Pop, Kinetic Angle Tilt, Cartoon Squash & Stretch, Chromatic 3D Glitch, Pop Strong, Smooth Fade.
  - [x] Hỗ trợ cú pháp kịch bản JIZURA `*từ nhấn mạnh*` tự động phóng to 140% và đổi màu riêng.
  - [x] Hỗ trợ cơ chế Dual-Accent Karaoke (màu riêng cho từ thường vs từ nhấn mạnh).
  - [x] Tích hợp phân tầng 3D Chromatic Glitch (GhostCyan & GhostMagenta layers).
- [x] **Task 4: Nâng Cấp Giao Diện `app.py`**
  - [x] Bộ chọn Hiệu ứng chữ động Kinetic Motion FX trong Tab 3.
  - [x] Bộ chọn Bảng màu kép Dual-Accent (Active Word vs Emphasis Word).
  - [x] Mockup smartphone động thời gian thực bằng CSS Keyframes (`jizuraSpring`, `jizuraTilt`, `jizuraSquash`, `jizuraGlitch`).
  - [x] Nút `🎲 JIZURA Omakase` đổi biến thể nhanh 1-click.
- [x] **Task 5: Kiểm Thử Tự Động & Xác Minh E2E**
  - [x] Viết `test_kinetic_effects.py` kiểm thử toàn bộ 7 chế độ chuyển động thành công 100%.
- [ ] **Task 6: Git Commit & Cập Nhật Walkthrough**
  - [ ] Commit code và push lên remote repository.
