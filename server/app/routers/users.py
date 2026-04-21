import uuid
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..db import get_db
from ..deps import get_current_user
from ..models import CandidateProfile, User, UserRole
from ..runtime_cache import runtime_cache
from ..schemas import CandidateProfileOut, CandidateProfileUpdateIn, HRProfileOut, UpdateEmailIn, UpdatePasswordIn, UserOut
from ..security import hash_password, verify_password
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


@router.post("/me/hr-avatar", response_model=HRProfileOut)
async def upload_my_hr_avatar(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    file: UploadFile = File(...),
) -> HRProfileOut:
    if user.role != UserRole.hr or user.hr_profile is None:
        raise HTTPException(status_code=403, detail="HR only")
    ext = Path(file.filename or "").suffix[:16].lower()
    if not ext:
        ext = ".jpg"
    if ext not in _AVATAR_EXT:
        raise HTTPException(status_code=400, detail="Chỉ chấp nhận ảnh: jpg, jpeg, png, gif, webp")
    sub = settings.subdir_for("hr_assets")
    fname = f"hr_{user.id}_{uuid.uuid4().hex}{ext}"
    storage_key = relative_key(sub, fname)
    dest = absolute_path(settings, storage_key)
    dest.parent.mkdir(parents=True, exist_ok=True)
    content = await file.read()
    if len(content) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large")

    old_key = user.hr_profile.avatar_storage_key
    dest.write_bytes(content)
    user.hr_profile.avatar_storage_key = storage_key
    db.commit()
    db.refresh(user.hr_profile)

    if old_key and old_key != storage_key:
        old_path = resolve_existing_file(settings, old_key)
        if old_path and old_path.is_file():
            try:
                old_path.unlink()
            except OSError:
                pass

    return user.hr_profile


@router.get("/me/candidate-profile", response_model=CandidateProfileOut | None)
def my_candidate_profile(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> CandidateProfileOut | None:
    if user.role != UserRole.candidate:
        return None
    cached = runtime_cache.candidate_profile_by_user_id.get(user.id)
    if cached:
        return cached
    row = db.scalar(select(CandidateProfile).where(CandidateProfile.user_id == user.id))
    if row:
        runtime_cache.upsert_candidate_profile(row)
    return row


@router.put("/me/candidate-profile", response_model=CandidateProfileOut)
def upsert_my_candidate_profile(
    body: CandidateProfileUpdateIn,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> CandidateProfile:
    if user.role != UserRole.candidate:
        raise HTTPException(status_code=403, detail="Candidate only")
    profile = db.scalar(select(CandidateProfile).where(CandidateProfile.user_id == user.id))
    if not profile:
        profile = CandidateProfile(user_id=user.id)
        db.add(profile)
        db.flush()
    profile.headline = body.headline
    profile.introduction = body.introduction
    profile.skills = body.skills
    profile.experience = body.experience
    db.commit()
    db.refresh(profile)
    runtime_cache.upsert_candidate_profile(profile)
    return profile


@router.put("/me/email", response_model=UserOut)
def update_me_email(
    body: UpdateEmailIn,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    if not verify_password(body.current_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Mật khẩu hiện tại không đúng")
    exists = db.scalar(select(User).where(User.email == body.new_email, User.id != user.id))
    if exists:
        raise HTTPException(status_code=400, detail="Email đã được sử dụng")
    user.email = body.new_email
    db.commit()
    db.refresh(user)
    return user


@router.put("/me/password", response_model=UserOut)
def update_me_password(
    body: UpdatePasswordIn,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    if not verify_password(body.current_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Mật khẩu hiện tại không đúng")
    user.password_hash = hash_password(body.new_password)
    db.commit()
    db.refresh(user)
    return user


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
