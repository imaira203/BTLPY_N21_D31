from datetime import datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import get_current_user
from ..models import HRApprovalStatus, HRProfile, Job, JobApplication, JobStatus, User, UserRole
from ..runtime_cache import runtime_cache
from ..schemas import AdminDecision, JobOut, StatsOut, UserOut

router = APIRouter(prefix="/admin", tags=["admin"])


def _require_admin(user: User) -> User:
    if user.role != UserRole.admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")
    return user


@router.get("/dashboard", response_model=StatsOut)
def admin_dashboard(user: Annotated[User, Depends(get_current_user)], db: Annotated[Session, Depends(get_db)]) -> StatsOut:
    _require_admin(user)
    total_users = db.scalar(select(func.count()).select_from(User).where(User.role == UserRole.candidate)) or 0
    total_hr = db.scalar(select(func.count()).select_from(User).where(User.role == UserRole.hr)) or 0
    total_jobs = db.scalar(select(func.count()).select_from(Job)) or 0
    since = datetime.utcnow() - timedelta(days=1)
    activity = db.scalar(select(func.count()).select_from(Job).where(Job.created_at >= since)) or 0
    monthly_users = db.execute(
        select(func.month(User.created_at), func.count())
        .where(User.role == UserRole.candidate)
        .group_by(func.month(User.created_at))
        .order_by(func.month(User.created_at))
    ).all()
    monthly_jobs = db.execute(
        select(func.month(Job.created_at), func.count()).group_by(func.month(Job.created_at)).order_by(func.month(Job.created_at))
    ).all()
    labels = [f"T{max(1, min(12, i))}" for i in range(1, 7)]
    u_vals = [0] * 6
    j_vals = [0] * 6
    for m, c in monthly_users:
        idx = (int(m or 1) - 1) % 6
        u_vals[idx] = int(c)
    for m, c in monthly_jobs:
        idx = (int(m or 1) - 1) % 6
        j_vals[idx] = int(c)
    values = [u + j for u, j in zip(u_vals, j_vals)]
    return StatsOut(
        labels=labels,
        values=values,
        cards={
            "users": int(total_users),
            "hr": int(total_hr),
            "jobs": int(total_jobs),
            "activity_today": int(activity),
        },
    )


@router.get("/pending/hr", response_model=list[UserOut])
def pending_hr(user: Annotated[User, Depends(get_current_user)], db: Annotated[Session, Depends(get_db)]) -> list[User]:
    _require_admin(user)
    rows = db.scalars(
        select(User)
        .join(HRProfile, HRProfile.user_id == User.id)
        .where(HRProfile.approval_status == HRApprovalStatus.pending)
    ).all()
    return list(rows)


@router.post("/hr/{target_user_id}/approve")
def approve_hr(
    target_user_id: int,
    body: AdminDecision,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    _require_admin(user)
    target = db.get(User, target_user_id)
    if not target or target.role != UserRole.hr or not target.hr_profile:
        raise HTTPException(status_code=404, detail="HR not found")
    target.hr_profile.approval_status = HRApprovalStatus.approved
    target.hr_profile.admin_note = body.note
    db.commit()
    return {"ok": True}


@router.post("/hr/{target_user_id}/reject")
def reject_hr(
    target_user_id: int,
    body: AdminDecision,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    _require_admin(user)
    target = db.get(User, target_user_id)
    if not target or target.role != UserRole.hr or not target.hr_profile:
        raise HTTPException(status_code=404, detail="HR not found")
    target.hr_profile.approval_status = HRApprovalStatus.rejected
    target.hr_profile.admin_note = body.note
    db.commit()
    return {"ok": True}


@router.get("/pending/jobs", response_model=list[JobOut])
def pending_jobs(user: Annotated[User, Depends(get_current_user)], db: Annotated[Session, Depends(get_db)]) -> list[JobOut]:
    _require_admin(user)
    rows = db.scalars(select(Job).where(Job.status == JobStatus.pending_approval).order_by(Job.id.desc())).all()
    return list(rows)


@router.get("/jobs", response_model=list[JobOut])
def all_jobs(user: Annotated[User, Depends(get_current_user)], db: Annotated[Session, Depends(get_db)]) -> list[JobOut]:
    _require_admin(user)
    rows = db.scalars(select(Job).order_by(Job.id.desc()).limit(1000)).all()
    return list(rows)


@router.post("/jobs/{job_id}/approve", response_model=JobOut)
def approve_job(
    job_id: int,
    body: AdminDecision,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Job:
    _require_admin(user)
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    job.status = JobStatus.published
    job.admin_note = body.note
    db.commit()
    db.refresh(job)
    runtime_cache.upsert_job(job)
    return job


@router.post("/jobs/{job_id}/reject", response_model=JobOut)
def reject_job(
    job_id: int,
    body: AdminDecision,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Job:
    _require_admin(user)
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    job.status = JobStatus.rejected
    job.admin_note = body.note
    db.commit()
    db.refresh(job)
    runtime_cache.upsert_job(job)
    return job


@router.delete("/jobs/{job_id}")
def delete_job(
    job_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    _require_admin(user)
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    db.delete(job)
    db.commit()
    runtime_cache.jobs_by_id.pop(job_id, None)
    runtime_cache.published_job_ids = [jid for jid in runtime_cache.published_job_ids if jid != job_id]
    return {"ok": True}


@router.get("/users", response_model=list[UserOut])
def list_users(user: Annotated[User, Depends(get_current_user)], db: Annotated[Session, Depends(get_db)]) -> list[User]:
    _require_admin(user)
    rows = db.scalars(select(User).order_by(User.id.desc()).limit(500)).all()
    return list(rows)


@router.get("/users/candidates")
def candidate_overview(user: Annotated[User, Depends(get_current_user)], db: Annotated[Session, Depends(get_db)]) -> list[dict]:
    _require_admin(user)
    rows = db.execute(
        select(
            User.id,
            User.full_name,
            User.email,
            User.created_at,
            User.is_active,
            User.role,
            func.count(JobApplication.id),
        )
        .outerjoin(JobApplication, JobApplication.candidate_id == User.id)
        .where(User.role == UserRole.candidate)
        .group_by(User.id, User.full_name, User.email, User.created_at, User.is_active, User.role)
        .order_by(User.id.desc())
    ).all()
    out: list[dict] = []
    for user_id, full_name, email, created_at, is_active, role, app_count in rows:
        out.append(
            {
                "id": user_id,
                "full_name": full_name,
                "email": email,
                "phone": "",
                "created_at": created_at.strftime("%d/%m/%Y"),
                "applications_count": int(app_count or 0),
                "is_active": bool(is_active),
                "role": role.value,
            }
        )
    return out


@router.get("/users/hrs")
def hr_overview(user: Annotated[User, Depends(get_current_user)], db: Annotated[Session, Depends(get_db)]) -> list[dict]:
    _require_admin(user)
    rows = db.execute(
        select(
            User.id,
            User.email,
            User.created_at,
            User.is_active,
            HRProfile.company_name,
            HRProfile.contact_phone,
            func.count(Job.id),
        )
        .join(HRProfile, HRProfile.user_id == User.id)
        .outerjoin(Job, Job.hr_user_id == User.id)
        .where(User.role == UserRole.hr)
        .group_by(
            User.id,
            User.email,
            User.created_at,
            User.is_active,
            HRProfile.company_name,
            HRProfile.contact_phone,
        )
        .order_by(User.id.desc())
    ).all()
    out: list[dict] = []
    for user_id, email, created_at, is_active, company_name, contact_phone, jobs_count in rows:
        out.append(
            {
                "id": user_id,
                "company_name": company_name,
                "email": email,
                "phone": contact_phone or "",
                "created_at": created_at.strftime("%d/%m/%Y"),
                "jobs_count": int(jobs_count or 0),
                "is_active": bool(is_active),
            }
        )
    return out


@router.get("/users/{target_user_id}", response_model=UserOut)
def get_user_detail(
    target_user_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    _require_admin(user)
    target = db.get(User, target_user_id)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    return target


@router.post("/users/{target_user_id}/lock")
def lock_user(
    target_user_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    _require_admin(user)
    target = db.get(User, target_user_id)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    if target.role == UserRole.admin:
        raise HTTPException(status_code=400, detail="Không thể khóa tài khoản admin")
    target.is_active = False
    db.commit()
    return {"ok": True}


@router.post("/users/{target_user_id}/unlock")
def unlock_user(
    target_user_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    _require_admin(user)
    target = db.get(User, target_user_id)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    target.is_active = True
    db.commit()
    return {"ok": True}


@router.get("/hr/{target_user_id}")
def hr_detail(
    target_user_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    _require_admin(user)
    target = db.get(User, target_user_id)
    if not target or target.role != UserRole.hr or not target.hr_profile:
        raise HTTPException(status_code=404, detail="HR not found")
    hp = target.hr_profile
    return {
        "user_id": target.id,
        "email": target.email,
        "full_name": target.full_name,
        "is_active": target.is_active,
        "company_name": hp.company_name,
        "avatar_storage_key": hp.avatar_storage_key,
        "contact_phone": hp.contact_phone,
        "company_description": hp.company_description,
        "approval_status": hp.approval_status.value,
        "admin_note": hp.admin_note,
    }


@router.get("/jobs/{job_id}", response_model=JobOut)
def job_detail(
    job_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Job:
    _require_admin(user)
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job
