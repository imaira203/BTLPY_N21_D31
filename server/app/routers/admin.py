from datetime import datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import get_current_user
from ..models import (
    CandidateSubscription,
    HRApprovalStatus,
    HRProfile,
    Invoice,
    InvoiceStatus,
    InvoiceType,
    Job,
    JobApplication,
    JobStatus,
    ProfileView,
    SubscriptionStatus,
    User,
    UserRole,
)
from ..runtime_cache import runtime_cache
from ..notifications import notify_role, notify_user
from ..schemas import AdminDecision, JobOut, StatsOut, UserOut

router = APIRouter(prefix="/admin", tags=["admin"])


def _require_admin(user: User) -> User:
    if user.role != UserRole.admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")
    return user


def _is_candidate_pro_active(db: Session, candidate_id: int) -> bool:
    sub = runtime_cache.subscription_by_candidate_id.get(candidate_id)
    if not sub:
        sub = db.scalar(select(CandidateSubscription).where(CandidateSubscription.candidate_id == candidate_id))
    if not sub or sub.status != SubscriptionStatus.active or not sub.pro_expires_at:
        return False
    return sub.pro_expires_at > datetime.utcnow()


def _to_job_out(job: Job, db: Session, company_name: str | None = None) -> JobOut:
    if company_name is None:
        hp = db.scalar(select(HRProfile).where(HRProfile.user_id == job.hr_user_id))
        company_name = hp.company_name if hp else None
    raw_status = job.status.value if hasattr(job.status, "value") else str(job.status or "").strip()
    if raw_status not in {s.value for s in JobStatus}:
        raw_status = JobStatus.pending_approval.value
    app_count = db.scalar(select(func.count()).select_from(JobApplication).where(JobApplication.job_id == job.id)) or 0
    is_boost_active = bool(
        (job.boost_budget_vnd or 0) > 0
        and job.boost_expires_at
        and job.boost_expires_at > datetime.utcnow()
    )
    return JobOut(
        id=job.id,
        hr_user_id=job.hr_user_id,
        title=job.title,
        description=job.description,
        department=job.department,
        level=job.level,
        salary_text=job.salary_text,
        min_salary=job.min_salary,
        max_salary=job.max_salary,
        location=job.location,
        job_type=job.job_type,
        count=job.headcount,
        deadline=job.deadline_text,
        applicants_count=int(app_count),
        status=JobStatus(raw_status),
        admin_note=job.admin_note,
        created_at=job.created_at,
        company_name=company_name,
        boost_budget_vnd=int(job.boost_budget_vnd or 0),
        is_boosted=is_boost_active,
        boost_last_paid_at=job.boost_last_paid_at,
        boost_expires_at=job.boost_expires_at,
    )


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
    notify_user(
        db,
        user_id=int(target.id),
        title="HR đã được phê duyệt",
        message="Tài khoản HR của bạn đã được admin phê duyệt.",
    )
    notify_role(
        db,
        role=UserRole.candidate,
        title="Nhà tuyển dụng mới",
        message=f"Nhà tuyển dụng '{target.hr_profile.company_name}' đã được xác minh.",
    )
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
    notify_user(
        db,
        user_id=int(target.id),
        title="HR bị từ chối",
        message="Hồ sơ HR của bạn đã bị từ chối. Vui lòng cập nhật và gửi lại.",
    )
    db.commit()
    return {"ok": True}


@router.get("/pending/jobs", response_model=list[JobOut])
def pending_jobs(user: Annotated[User, Depends(get_current_user)], db: Annotated[Session, Depends(get_db)]) -> list[JobOut]:
    _require_admin(user)
    rows = db.scalars(select(Job).where(Job.status == JobStatus.pending_approval).order_by(Job.id.desc())).all()
    return [_to_job_out(job, db) for job in rows]


@router.get("/jobs", response_model=list[JobOut])
def all_jobs(user: Annotated[User, Depends(get_current_user)], db: Annotated[Session, Depends(get_db)]) -> list[JobOut]:
    _require_admin(user)
    rows = db.scalars(select(Job).order_by(Job.id.desc()).limit(1000)).all()
    return [_to_job_out(job, db) for job in rows]


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
    notify_user(
        db,
        user_id=int(job.hr_user_id),
        title="Tin tuyển dụng đã được duyệt",
        message=f"Tin '{job.title}' đã được admin phê duyệt và hiển thị công khai.",
    )
    notify_role(
        db,
        role=UserRole.candidate,
        title="Tin mới vừa mở",
        message=f"Có tin tuyển dụng mới: '{job.title}'.",
    )
    db.commit()
    db.refresh(job)
    runtime_cache.upsert_job(job)
    return _to_job_out(job, db)


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
    notify_user(
        db,
        user_id=int(job.hr_user_id),
        title="Tin tuyển dụng bị từ chối",
        message=f"Tin '{job.title}' đã bị admin từ chối.",
    )
    db.commit()
    db.refresh(job)
    runtime_cache.upsert_job(job)
    return _to_job_out(job, db)


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
        profile_views = db.scalar(
            select(func.count()).select_from(ProfileView).where(ProfileView.viewed_user_id == user_id)
        ) or 0
        out.append(
            {
                "id": user_id,
                "full_name": full_name,
                "email": email,
                "phone": "",
                "created_at": created_at.strftime("%d/%m/%Y"),
                "applications_count": int(app_count or 0),
                "profile_views": int(profile_views),
                "is_pro_active": _is_candidate_pro_active(db, int(user_id)),
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
    return _to_job_out(job, db)


@router.get("/payment-insights")
def payment_insights(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    limit: int = 100,
    period: str = "all",
) -> dict:
    _require_admin(user)
    max_limit = max(10, min(int(limit or 100), 500))

    period_key = str(period or "all").strip().lower()
    month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    paid_filter = [Invoice.status == InvoiceStatus.paid]
    if period_key in {"month", "this_month"}:
        paid_filter.append(Invoice.paid_at >= month_start)

    paid_invoices = db.scalars(
        select(Invoice)
        .where(*paid_filter)
        .order_by(Invoice.paid_at.desc(), Invoice.id.desc())
        .limit(max_limit)
    ).all()
    all_paid_count = int(
        db.scalar(select(func.count()).select_from(Invoice).where(*paid_filter)) or 0
    )
    all_paid_amount = float(
        db.scalar(select(func.coalesce(func.sum(Invoice.amount), 0)).where(*paid_filter)) or 0
    )

    role_stats_rows = db.execute(
        select(
            User.id,
            User.role,
            User.full_name,
            User.email,
            HRProfile.company_name,
            func.count(Invoice.id),
            func.coalesce(func.sum(Invoice.amount), 0),
            func.max(Invoice.paid_at),
        )
        .join(Invoice, Invoice.owner_user_id == User.id)
        .outerjoin(HRProfile, HRProfile.user_id == User.id)
        .where(*paid_filter)
        .group_by(User.id, User.role, User.full_name, User.email, HRProfile.company_name)
        .order_by(func.count(Invoice.id).desc(), func.max(Invoice.paid_at).desc())
        .limit(max_limit)
    ).all()

    candidate_paid_count = int(
        db.scalar(
            select(func.count())
            .select_from(Invoice)
            .join(User, User.id == Invoice.owner_user_id)
            .where(*paid_filter, User.role == UserRole.candidate)
        )
        or 0
    )
    hr_paid_count = int(
        db.scalar(
            select(func.count())
            .select_from(Invoice)
            .join(User, User.id == Invoice.owner_user_id)
            .where(*paid_filter, User.role == UserRole.hr)
        )
        or 0
    )

    now_utc = datetime.utcnow()
    boost_rows = db.execute(
        select(Job, HRProfile.company_name)
        .outerjoin(HRProfile, HRProfile.user_id == Job.hr_user_id)
        .where(Job.boost_budget_vnd > 0)
        .order_by(Job.boost_budget_vnd.desc(), Job.boost_last_paid_at.desc(), Job.id.desc())
        .limit(max_limit)
    ).all()

    return {
        "summary": {
            "total_paid_invoices": all_paid_count,
            "total_paid_amount_vnd": int(all_paid_amount),
            "candidate_paid_count": candidate_paid_count,
            "hr_paid_count": hr_paid_count,
        },
        "payment_by_account": [
            {
                "user_id": int(uid),
                "role": role.value if hasattr(role, "value") else str(role),
                "display_name": (full_name or email or company_name or f"User#{uid}"),
                "email": email,
                "company_name": company_name,
                "paid_count": int(paid_count or 0),
                "total_paid_amount_vnd": int(float(total_paid_amount or 0)),
                "last_paid_at": last_paid_at.isoformat() if last_paid_at else None,
            }
            for uid, role, full_name, email, company_name, paid_count, total_paid_amount, last_paid_at in role_stats_rows
        ],
        "recent_payments": [
            {
                "invoice_id": int(inv.id),
                "owner_user_id": int(inv.owner_user_id),
                "invoice_type": inv.invoice_type.value if hasattr(inv.invoice_type, "value") else str(inv.invoice_type),
                "amount_vnd": int(float(inv.amount or 0)),
                "paid_at": inv.paid_at.isoformat() if inv.paid_at else None,
                "job_id": int(inv.job_id) if inv.job_id else None,
                "application_id": int(inv.application_id) if inv.application_id else None,
            }
            for inv in paid_invoices
        ],
        "boost_ranking": [
            {
                "job_id": int(job.id),
                "job_title": job.title,
                "company_name": company_name or "",
                "hr_user_id": int(job.hr_user_id),
                "boost_budget_vnd": int(job.boost_budget_vnd or 0),
                "boost_last_paid_at": job.boost_last_paid_at.isoformat() if job.boost_last_paid_at else None,
                "boost_expires_at": job.boost_expires_at.isoformat() if job.boost_expires_at else None,
                "is_boost_active": bool(job.boost_expires_at and job.boost_expires_at > now_utc),
            }
            for job, company_name in boost_rows
        ],
    }
