import uuid
import json
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..db import get_db
from ..deps import get_current_user
from ..models import CandidateProfile, HRApprovalStatus, HRProfile, User, UserRole
from ..runtime_cache import runtime_cache
from ..schemas import (
    CandidateProfileOut,
    CandidateProfileUpdateIn,
    HRProfileOut,
    HRProfileUpdateIn,
    UpdateBasicProfileIn,
    UpdateEmailIn,
    UpdatePasswordIn,
    UserOut,
)
from ..security import hash_password, verify_password
from ..storage_paths import absolute_path, relative_key, resolve_existing_file

router = APIRouter(prefix="/users", tags=["users"])

_AVATAR_EXT = {".jpg", ".jpeg", ".png", ".gif", ".webp"}


def _to_candidate_profile_out(profile: CandidateProfile) -> CandidateProfileOut:
    skills_dict = profile.skills_as_dict()
    return CandidateProfileOut(
        id=profile.id,
        user_id=profile.user_id,
        tagline=profile.tagline,
        phone=profile.phone,
        address=profile.address,
        professional_field=profile.professional_field,
        degree=profile.degree,
        experience_text=profile.experience_text,
        language=profile.language,
        skills_json=skills_dict,
        updated_at=profile.updated_at,
    )


@router.get("/me", response_model=UserOut)
def me(user: Annotated[User, Depends(get_current_user)]) -> User:
    return user


@router.get("/me/avatar/view")
def view_my_avatar(user: Annotated[User, Depends(get_current_user)]) -> FileResponse:
    if not user.avatar_storage_key:
        raise HTTPException(status_code=404, detail="Avatar not found")
    path = resolve_existing_file(settings, user.avatar_storage_key)
    if not path or not path.is_file():
        raise HTTPException(status_code=404, detail="Avatar file not found")
    return FileResponse(path=str(path), media_type="image/*", filename=path.name)


@router.get("/me/hr-profile", response_model=HRProfileOut | None)
def my_hr_profile(user: Annotated[User, Depends(get_current_user)]) -> HRProfileOut | None:
    if user.role.value != "hr" or user.hr_profile is None:
        return None
    return user.hr_profile


@router.put("/me/hr-profile", response_model=HRProfileOut)
def update_my_hr_profile(
    body: HRProfileUpdateIn,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> HRProfileOut:
    if user.role != UserRole.hr:
        raise HTTPException(status_code=403, detail="HR only")

    profile = user.hr_profile
    if profile is None:
        profile = HRProfile(user_id=user.id, company_name=body.company_name.strip())
        db.add(profile)
        db.flush()

    new_company_name = body.company_name.strip()
    new_contact_phone = (body.contact_phone or "").strip() or None
    new_company_description = (body.company_description or "").strip() or None

    company_info_changed = (
        str(profile.company_name or "").strip() != new_company_name
        or (str(profile.contact_phone or "").strip() or None) != new_contact_phone
        or (str(profile.company_description or "").strip() or None) != new_company_description
    )

    profile.company_name = new_company_name
    profile.contact_phone = new_contact_phone
    profile.company_description = new_company_description

    if company_info_changed:
        profile.approval_status = HRApprovalStatus.pending

    db.commit()
    db.refresh(profile)
    runtime_cache.upsert_hr_profile(profile)
    return profile


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
    runtime_cache.upsert_hr_profile(user.hr_profile)

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
        return _to_candidate_profile_out(cached)
    row = db.scalar(select(CandidateProfile).where(CandidateProfile.user_id == user.id))
    if row:
        runtime_cache.upsert_candidate_profile(row)
        return _to_candidate_profile_out(row)
    return None


@router.put("/me/candidate-profile", response_model=CandidateProfileOut)
def upsert_my_candidate_profile(
    body: CandidateProfileUpdateIn,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> CandidateProfileOut:
    if user.role != UserRole.candidate:
        raise HTTPException(status_code=403, detail="Candidate only")
    profile = db.scalar(select(CandidateProfile).where(CandidateProfile.user_id == user.id))
    if not profile:
        profile = CandidateProfile(user_id=user.id)
        db.add(profile)
        db.flush()
    profile.tagline = body.tagline
    profile.phone = body.phone
    profile.address = body.address
    profile.professional_field = body.professional_field
    profile.degree = body.degree
    profile.experience_text = body.experience_text
    profile.language = body.language
    if body.skills_json is not None:
        profile.skills_json = json.dumps(body.skills_json, ensure_ascii=False)
    db.commit()
    db.refresh(profile)
    runtime_cache.upsert_candidate_profile(profile)
    return _to_candidate_profile_out(profile)


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


@router.put("/me/basic", response_model=UserOut)
def update_me_basic(
    body: UpdateBasicProfileIn,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    if body.email is not None:
        normalized_email = body.email.strip().lower()
        exists = db.scalar(select(User).where(User.email == normalized_email, User.id != user.id))
        if exists:
            raise HTTPException(status_code=400, detail="Email đã được sử dụng")
        user.email = normalized_email
    if body.full_name is not None:
        user.full_name = body.full_name.strip() or None
    db.commit()
    db.refresh(user)
    runtime_cache.upsert_user(user)
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
