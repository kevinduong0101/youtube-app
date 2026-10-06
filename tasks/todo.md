# Danh Sách Nhiệm Vụ: Sửa Lỗi Preview, Nâng Cấp Presets & AI Semantic Chunking

- [x] **Task 1: Sửa Lỗi Image Preview Streamlit**
  - [x] Thay thế `use_container_width=True` thành `use_column_width=True` tại mọi lệnh gọi `st.image()` trong `app.py`.
- [x] **Task 2: Thuật Toán Nhận Diện Từ Ghép Tiếng Việt & AI Subtitle Optimizer**
  - [x] Tích hợp từ điển từ ghép `VIETNAMESE_COMPOUND_PAIRS` và danh sách từ liên kết treo `DANGLING_PARTICLES`.
  - [x] Cải tiến `create_smart_rhythm_chunks` không ngắt giữa từ ghép (như 'kế hoạch', 'lập trình', 'browse web').
  - [x] Thêm hàm `ai_optimize_subtitle_chunks` rà soát và hàn gắn các cụm từ ghép bị cắt rời.
  - [x] Bổ sung nút `✨ AI TỰ ĐỘNG TỐI ƯU NHỊP SUB` và nút gộp câu nhanh `🔗` trong Tab 2.
- [x] **Task 3: Nâng Cấp 7 Studio Presets Độc Quyền**
  - [x] Thêm MrBeast Action Punch (chữ in nghiêng `\i1`, viền kép, pop 125%).
  - [x] Thêm Ali Abdaal Minimalist (thanh lịch, nét mỏng, bóng đổ mềm mại).
  - [x] Cập nhật mockup điện thoại CSS tương ứng theo từng preset.
- [x] **Task 4: Kiểm Thử Tự Động & Xác Minh E2E**
  - [x] Tạo `test_semantic_chunking.py` và chạy kiểm thử thành công 100%.
  - [x] Kiểm thử sinh phụ đề ASS cho các preset mới không lỗi.
- [ ] **Task 5: Git Commit & Cập Nhật Walkthrough**
  - [ ] Commit code và push lên remote repo.
