# JobHub — Hướng dẫn chạy chương trình
*Tài liệu trình bày nội dung bài tập: `BAI_TAP.md`.*
Ứng dụng gồm **máy chủ API** (FastAPI + MySQL) và **client desktop** (Python + PySide6). Thứ tự khuyến nghị: cài MySQL → tạo DB → cấu hình `.env` → chạy server → chạy client.


# Nhớ chia branch server và client. hoạt động trên 2 branch. sau test ok mới merge vào master rồi push lên

## Yêu cầu môi trường

- **Python** 3.11+ (đã thử với 3.14; nên dùng bản ổn định 3.11–3.12 nếu gặp lỗi gói).
- **MySQL** 8.x (hoặc tương thích), tài khoản có quyền tạo database / bảng.
- Thư viện Python (cài trong môi trường ảo nếu có):

```bash
# Server
pip install fastapi uvicorn[standard] sqlalchemy pymysql pydantic pydantic-settings python-jose[cryptography] passlib[bcrypt] python-multipart

# Client
pip install PySide6 requests matplotlib pydantic pydantic-settings
```

## 1. Cơ sở dữ liệu MySQL

1. Tạo database (ví dụ tên `jobhub`):

```sql
CREATE DATABASE jobhub CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

2. Import schema (từ thư mục gốc repo):

```bash
mysql -u root -p jobhub < database/schema.sql
```

Hoặc mở file `database/schema.sql` trong MySQL Workbench / phpMyAdmin và thực thi.

> **Lưu ý:** Nếu bạn đã có bảng `users` tạo từ phiên bản cũ thiếu cột `avatar_storage_key`, khi **khởi động server** lần đầu, code sẽ cố gắng thêm cột tự động. Nếu vẫn lỗi, chạy thủ công: `database/migrate_add_avatar_column.sql`.

## 2. Máy chủ API (`server/`)

1. Sao chép cấu hình:

```bash
copy server\.env.example server\.env
```

2. Sửa `server/.env`: `MYSQL_*` trùng với MySQL của bạn; nên đổi `JWT_SECRET` khi triển khai thật.

3. Chạy server (Windows):

```bat
cd server
run_server.bat
```

Hoặc:

```bash
cd server
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

4. Kiểm tra:

- Trình duyệt: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) (Swagger).
- [http://127.0.0.1:8000/](http://127.0.0.1:8000/) → JSON có `"service": "jobhub"`.
- [http://127.0.0.1:8000/api/health](http://127.0.0.1:8000/api/health) → `{"status":"ok"}`.

Toàn bộ REST nằm dưới tiền tố **`/api`** (ví dụ `/api/auth/login`).

### Tạo tài khoản admin mặc định (tùy chọn)

Trong thư mục `server/`:

```bash
python -m scripts.seed_admin
```

Mặc định: `admin@jobhub.local` / `admin123` — **đổi mật khẩu** sau khi test.

## 3. Client desktop (`client/`)

1. Sao chép `.env`:

```bash
copy client\.env.example client\.env
```

2. `client/.env`:

- `API_BASE_URL`: URL gốc của API. Có thể dùng `http://127.0.0.1:8000` hoặc `http://127.0.0.1:8000/api` — client sẽ chuẩn hóa để gọi đúng các đường dẫn dưới `/api`.

3. Chạy (từ thư mục `client/`):

```bash
cd client
python main.py
```

Đảm bảo server đã chạy trước khi đăng nhập / đăng ký.

## Xử lý sự cố nhanh

| Hiện tượng | Gợi ý |
|------------|--------|
| Client không kết nối được API | Kiểm tra server đang chạy, đúng cổng; mở `/api/health`. |
| `404` trên `/api/...` | Đang không chạy đúng ứng dụng JobHub trên cổng đó; tắt process cũ hoặc đổi cổng. |
| `Unknown column 'avatar_storage_key'` | Khởi động lại server (có patch tự động) hoặc chạy file SQL migration trong `database/`. |
| `WinError 10013` khi bind cổng | Cổng bị chặn / xung đột; đổi `--port` (ví dụ 8001) và cập nhật `API_BASE_URL` trên client. |
| Đăng nhập `422` | Body JSON phải có `email`, `password` hợp lệ; gửi `Content-Type: application/json`. |

---
