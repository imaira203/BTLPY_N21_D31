"""Đường dẫn upload theo loại — mỗi loại một thư mục con dưới `upload_dir`."""

from __future__ import annotations

from pathlib import Path

from .config import Settings


def upload_dir_for_kind(settings: Settings, kind: str) -> Path:
    """
    kind: tên thư mục con (ví dụ cấu hình UPLOAD_SUBDIR_CVS -> 'cvs').
    Tạo thư mục nếu chưa có.
    """
    sub = settings.subdir_for(kind)
    path = settings.upload_dir / sub
    path.mkdir(parents=True, exist_ok=True)
    return path


def relative_key(subdir: str, filename: str) -> str:
    """Khóa lưu DB: `subdir/filename` (dùng dấu / thuận Unix)."""
    return f"{subdir.strip('/')}/{filename.lstrip('/')}"


def absolute_path(settings: Settings, storage_key: str) -> Path:
    """storage_key dạng `cvs/1_abc.pdf` hoặc `avatars/2_x.jpg`."""
    return settings.upload_dir / storage_key.replace("\\", "/")


def resolve_existing_file(settings: Settings, storage_key: str) -> Path | None:
    """
    Tìm file trên đĩa. Hỗ trợ bản ghi cũ chỉ lưu tên file (không có thư mục):
    thử `upload_dir/key` rồi `upload_dir/cvs/basename(key)`.
    """
    key = storage_key.replace("\\", "/").strip()
    if not key:
        return None
    direct = settings.upload_dir / key
    if direct.is_file():
        return direct
    base = Path(key).name
    if "/" not in key:
        under_cvs = upload_dir_for_kind(settings, "cvs") / base
        if under_cvs.is_file():
            return under_cvs
        flat = settings.upload_dir / base
        if flat.is_file():
            return flat
    return None
