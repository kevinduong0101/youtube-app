# Danh Sách Nhiệm Vụ: AutoSub Pro Studio Overhaul

- [x] **Phase 1: Module Presets & Fonts**
  - [x] Tạo `core/presets.py` định nghĩa 5 Design Systems độc lập.
  - [x] Tạo `core/fonts.py` với font inspector, metadata parser, và fallback system.
- [x] **Phase 2: Subtitle Renderer & Motion Engine**
  - [x] Tạo `core/subtitle_renderer.py` với motion curves đàn hồi, letter-spacing, mask pill badge.
  - [x] Tích hợp renderer vào `core/subtitle_engine.py` (bảo toàn 100% thuật toán chunking & alignment).
- [x] **Phase 3: Safe Area Overlay & Media Pipeline**
  - [x] Cập nhật `core/media_utils.py` bổ sung Safe Area Guides cho preview 9:16.
- [x] **Phase 4: Redesign Studio UI**
  - [x] Tái thiết kế `app.py` thành bố cục 2 cột Studio Canvas (Stage ở trung tâm, Inspector bên phải).
  - [x] Áp dụng Dark Studio Design System (`#0B0C0F`, `#13151A`, `#191C22`).
- [ ] **Phase 5: Kiểm Thử & Xuất Bản**
  - [x] Chạy E2E automated test cho cả 5 presets.
  - [ ] Cập nhật Walkthrough, commit và push lên GitHub.
