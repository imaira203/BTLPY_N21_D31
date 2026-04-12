import uuid
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from ..config import settings
from ..db import get_db
from ..deps import get_current_user
from ..models import User
from ..schemas import HRProfileOut, UserOut
from ..storage_paths import absolute_path, relative_key, resolve_existing_file

router = APIRouter(prefix="/users", tags=["users"])

_AVATAR_EXT = {".jpg", ".jpeg", ".png", ".gif", ".webp"}


@router.get("/me", response_model=UserOut)
def me(user: Annotated[User, Depends(get_current_user)]) -> User:
    return user


@router.get("/me/hr-profile", response_model=HRProfileOut | None)
def my_hr_profile(user: Annotated[User, Depends(get_current_user)]) -> HRProfileOut | None:
    if user.role.value != "hr" or user.hr_profile is None:
        return None
    return user.hr_profile


@router.post("/me/avatar", response_model=UserOut)
async def upload_me_avatar(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    file: UploadFile = File(...),
) -> User:
    """Lưu avatar vào thư mục `uploads/<avatars>/` (theo cấu hình)."""
    ext = Path(file.filename or "").suffix[:16].lower()
    if not ext:
        ext = ".jpg"
    if ext not in _AVATAR_EXT:
        raise HTTPException(status_code=400, detail="Chỉ chấp nhận ảnh: jpg, jpeg, png, gif, webp")
    sub = settings.subdir_for("avatars")
    fname = f"{user.id}_{uuid.uuid4().hex}{ext}"
    storage_key = relative_key(sub, fname)
    dest = absolute_path(settings, storage_key)
    dest.parent.mkdir(parents=True, exist_ok=True)
    content = await file.read()
    if len(content) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large")

    old_key = user.avatar_storage_key
    dest.write_bytes(content)
    user.avatar_storage_key = storage_key
    db.commit()
    db.refresh(user)

    if old_key and old_key != storage_key:
        old_path = resolve_existing_file(settings, old_key)
        if old_path and old_path.is_file():
            try:
                old_path.unlink()
            except OSError:
                pass

    return user
