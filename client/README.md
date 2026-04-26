# 📋 JobHub Desktop Client — Tài liệu dự án

> Ứng dụng desktop tuyển dụng nội bộ, xây dựng bằng **Python + PySide6 (Qt6)**

---

## 🗂️ Cấu trúc thư mục

```
client/
├── main.py                        # Điểm khởi động ứng dụng
├── run_client.bat                 # Chạy nhanh trên Windows
├── requirements.txt               # Danh sách thư viện cần cài
│
├── app/
│   ├── __init__.py
│   ├── config.py                  # Cấu hình (API URL, mock mode, theme)
│   ├── mock_data.py               # Dữ liệu mẫu offline (jobs, users, CV...)
│   ├── paths.py                   # Đường dẫn tài nguyên (icons, fonts...)
│   ├── session_store.py           # Lưu / khôi phục session đăng nhập
│   ├── theme.py                   # Hằng màu sắc, font toàn cục
│   ├── ui_theme.py                # Helper theme bổ sung
│   │
│   ├── client/
│   │   ├── __init__.py
│   │   └── jobhub_api.py          # Tất cả lời gọi HTTP tới backend (hoặc mock)
│   │
│   └── ui/
│       ├── __init__.py
│       ├── auth_window.py         # Màn hình Đăng nhập / Đăng ký
│       ├── hr_dashboard.py        # Dashboard HR (quản lý tin, ứng viên)
│       ├── user_dashboard.py      # Dashboard ứng viên (tìm việc, CV, lịch sử)
│       ├── admin_dashboard.py     # Dashboard Admin (quản lý người dùng, duyệt tin)
│       ├── charts.py              # Widget biểu đồ (bar chart tuyển dụng)
│       ├── qss_loader.py          # Load file QSS stylesheet
│       ├── quanly_enhanced.py     # Tab quản lý nâng cao
│       └── ui_loader.py           # Load file .ui (Qt Designer)
│
├── resources/
│   ├── fonts/                     # Font chữ bundled
│   │   └── PlusJakartaSans-*.ttf  # Plus Jakarta Sans (Regular → ExtraBold)
│   ├── icons/                     # SVG icons (Soft Line + Duotone style)
│   └── ui/                        # File .ui Qt Designer (nếu có)
│
└── jobhub_data/
    └── session.json               # Session đăng nhập đã lưu (tự động tạo)
```

---

## ▶️ Cách chạy

### Windows (nhanh nhất)
```bat
run_client.bat
```

### Terminal
```bash
cd client
pip install -r requirements.txt
python main.py
```

### Chế độ Demo (offline, không cần backend)
Tạo file `.env` tại thư mục `client/`:
```env
USE_MOCK_DATA=1
```
Sau đó chạy bình thường.

---

## 🔑 Tài khoản đăng nhập demo

> Chỉ dùng khi `USE_MOCK_DATA=1`. Mật khẩu nhập bất kỳ (mock không kiểm tra).

| Role | Email | Mật khẩu | Chức năng |
|------|-------|-----------|-----------|
| **Admin** | `admin@jobhub.local` | _(bất kỳ)_ | Quản lý toàn hệ thống |
| **HR** | `hr@demo.local` | _(bất kỳ)_ | Đăng tin, quản lý ứng viên |
| **Candidate** | `user@demo.local` | _(bất kỳ)_ | Tìm việc, nộp CV |

---

## 🖥️ Các màn hình chính

### 🔐 AuthWindow (`auth_window.py`)
Màn hình xác thực 2 tab: **Đăng nhập** / **Đăng ký**

| Widget | Tên biến | Mô tả |
|--------|----------|-------|
| Input Email | `self.inp_email` | Ô nhập email |
| Input Mật khẩu | `self.inp_pw` | Ô nhập mật khẩu (có toggle ẩn/hiện) |
| Checkbox | `self.chk_remember` | Ghi nhớ đăng nhập |
| **Nút Đăng nhập** | `self.btn_login` | Gọi `_do_login()` |
| Label lỗi | `self.lbl_login_err` | Hiện thông báo lỗi login |
| Input Họ tên | `self.inp_fullname` | _(trang Đăng ký)_ |
| Input Email DK | `self.inp_reg_email` | _(trang Đăng ký)_ |
| Input PW DK | `self.inp_reg_pw` | _(trang Đăng ký)_ |
| **Nút Đăng ký** | `self.btn_register` | Gọi `_do_register()` |
| Label lỗi DK | `self.lbl_reg_err` | Hiện thông báo lỗi đăng ký |

---

### 👔 HRDashboard (`hr_dashboard.py`)
Dashboard chính của HR sau khi đăng nhập

| Widget / Method | Mô tả |
|-----------------|-------|
| `HRDashboard(on_logout)` | Khởi tạo dashboard HR |
| `_build_sidebar()` | Sidebar điều hướng (light theme, trắng) |
| `_build_topbar()` | Thanh trên: tiêu đề trang + search global |
| `_load_dash()` | Load tab Dashboard (metric cards + chart + feed) |
| `_build_jobs_tab()` | Tab Quản lý tin đăng |
| `_build_cands_tab()` | Tab Danh sách ứng viên |
| `_build_post_tab()` | Tab Đăng tin mới |
| `_fill_jobs_table()` | Render bảng tin đăng có phân trang |
| `_fill_cands_table()` | Render bảng ứng viên có phân trang |
| `_filter_jobs(text)` | Lọc tin theo từ khoá + status + loại |
| `_filter_cands(text)` | Lọc ứng viên theo từ khoá + status + sort |
| `_make_job_actions(job_id)` | 3 nút thao tác: Sửa / Xem / Xoá |
| `_make_cand_actions(app_id)` | 3 nút: Xem CV / Phê duyệt / Từ chối |
| `_show_toast(text, icon, color)` | Toast notification góc dưới phải |
| `_rebuild_activity_feed()` | Cập nhật feed hoạt động gần đây |
| `_show_global_search_popup()` | Popup tìm kiếm toàn cục |

**Metric Cards (4 thẻ)**

| Thẻ | Màu accent | Dữ liệu |
|-----|-----------|---------|
| Tin đang đăng | Xanh dương `#3b82f6` | `cards["jobs"]` |
| Tổng ứng viên | Tím `#8b5cf6` | `cards["candidates"]` |
| Lượt xem tin | Cam `#f97316` | `cards["views"]` |
| Tỷ lệ phản hồi | Xanh lá `#10b981` | `cards["response_rate"]` |

---

### 👤 UserDashboard (`user_dashboard.py`)
Dashboard ứng viên

| Method | Mô tả |
|--------|-------|
| `UserDashboard(on_logout)` | Khởi tạo dashboard ứng viên |
| `_build_home_page()` | Trang tìm việc (grid job cards) |
| `_build_history_page()` | Lịch sử nộp đơn |
| `_build_saved_page()` | Tin đã lưu |
| `_build_profile_page()` | Hồ sơ cá nhân / CV |
| `_build_job_detail_page(...)` | Chi tiết công việc + nút Ứng tuyển |
| `_load_jobs_grid(...)` | Render lưới card công việc |
| `_go(index)` | Chuyển tab sidebar |

---

### 🛡️ AdminDashboard (`admin_dashboard.py`)
Dashboard Admin

| Method | Mô tả |
|--------|-------|
| `AdminDashboard(on_logout)` | Khởi tạo dashboard admin |
| `_fill_user_table()` | Bảng danh sách người dùng |
| `_fill_hr_table()` | Bảng danh sách HR |
| `_fill_jobs_table()` | Bảng tất cả tin đăng |
| `_make_admin_job_actions(...)` | Nút Duyệt / Từ chối / Xoá tin |
| `_setup_revenue_chart()` | Biểu đồ doanh thu |
| `_load_dash()` | Load tổng quan Admin |

---

## 🌐 API Client (`jobhub_api.py`)

Tất cả request HTTP được định nghĩa tại đây. Tự động chuyển sang **mock data** nếu backend không khả dụng hoặc `USE_MOCK_DATA=1`.

| Hàm | Mô tả |
|-----|-------|
| `login(email, password)` | Đăng nhập |
| `register_candidate(...)` | Đăng ký ứng viên |
| `register_hr(...)` | Đăng ký HR |
| `me()` | Lấy thông tin user hiện tại |
| `list_jobs_public()` | Danh sách tin tuyển dụng công khai |
| `apply_job(job_id, cv_id)` | Nộp đơn ứng tuyển |
| `hr_dashboard()` | Số liệu dashboard HR |
| `hr_create_job(payload)` | Tạo tin mới |
| `hr_my_jobs()` | Danh sách tin của HR |
| `hr_update_job(job_id, payload)` | Cập nhật tin |
| `hr_delete_job(job_id)` | Xoá tin |
| `upload_cv(file_path)` | Upload CV |
| `candidate_view_cv(cv_id)` | Xem CV ứng viên |

---

## ⚙️ Cấu hình môi trường (`.env`)

Tạo file `client/.env`:

```env
# URL backend API (mặc định: localhost:8000)
API_BASE_URL=http://127.0.0.1:8000/api

# Bật chế độ demo offline (không cần backend)
USE_MOCK_DATA=1

# Giao diện (light / dark)
UI_THEME=light
```

---

## 📦 Thư viện sử dụng

| Thư viện | Phiên bản | Mục đích |
|----------|-----------|---------|
| `PySide6` | ≥ 6.10.1 | Framework UI (Qt6) |
| `requests` | ≥ 2.32.0 | Gọi HTTP tới backend |
| `matplotlib` | ≥ 3.9.0 | Vẽ biểu đồ |
| `pydantic-settings` | ≥ 2.6.0 | Đọc biến môi trường `.env` |

---

## 🎨 Design System

- **Font**: Plus Jakarta Sans (bundled tại `resources/fonts/`)
- **Primary color**: `#6366f1` (Indigo)
- **Icon style**: Soft Line + Duotone SVG (`currentColor` + `softColor`)
- **Card style**: White bg, shadow nhẹ, border-radius 16-18px
- **Sidebar**: Light white theme, accent bar trái khi active

---

## 👨‍💻 Nhóm phát triển

| Vai trò | Thông tin |
|---------|-----------|
| Nhóm | N21 — D31 |
| Môn học | Bài tập lớn Python |
| Năm học | 2023 – 2024 |
