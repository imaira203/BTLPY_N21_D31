import calendar
import re
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..billing import build_sepay_checkout_url, create_invoice, mark_invoice_paid
from ..config import settings
from ..db import get_db
from ..deps import get_current_user
from ..models import (
    CandidateProfile,
    CandidateSubscription,
    CVDocument,
    HRApprovalStatus,
    HRProfile,
    Invoice,
    InvoiceStatus,
    InvoiceType,
    Job,
    JobApplication,
    JobStatus,
    ProfileView,
    User,
    UserRole,
    ApplicationStatus,
    SubscriptionStatus,
)
from ..notifications import notify_role, notify_user
from ..runtime_cache import runtime_cache
from ..schemas import ApplicationDecisionIn, InvoiceOut, JobBoostInvoiceCreateIn, JobCreate, JobOut, StatsOut
from ..storage_paths import resolve_existing_file

router = APIRouter(prefix="/hr", tags=["hr"])


def _require_hr(user: User) -> User:
    if user.role != UserRole.hr:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="HR only")
    return user


def _require_approved_hr(user: User) -> None:
    _require_hr(user)
    if user.hr_profile is None or user.hr_profile.approval_status != HRApprovalStatus.approved:
        raise HTTPException(status_code=403, detail="HR profile not approved yet")


def _is_candidate_pro_active(db: Session, candidate_id: int) -> bool:
    sub = runtime_cache.subscription_by_candidate_id.get(candidate_id)
    if not sub:
        sub = db.scalar(select(CandidateSubscription).where(CandidateSubscription.candidate_id == candidate_id))
    if not sub or sub.status != SubscriptionStatus.active or not sub.pro_expires_at:
        return False
    return sub.pro_expires_at > datetime.utcnow()


def _normalized_app_status(value: object) -> ApplicationStatus:
    if isinstance(value, ApplicationStatus):
        return value
    try:
        return ApplicationStatus(str(value))
    except Exception:
        return ApplicationStatus.pending


def _invoice_type_key(value: object) -> str:
    if value is None:
        return ""
    return value.value if hasattr(value, "value") else str(value)


def _extract_job_id_from_boost_text(text: str | None) -> int | None:
    raw = str(text or "").strip()
    if not raw:
        return None
    m = re.search(r"#\s*(\d+)", raw)
    if not m:
        return None
    try:
        return int(m.group(1))
    except Exception:
        return None


def _mark_candidate_profile_view(
    db: Session,
    *,
    candidate_id: int,
    viewer_user_id: int,
    job_id: int,
    application_id: int,
) -> None:
    existed = db.scalar(
        select(ProfileView).where(
            ProfileView.viewed_user_id == candidate_id,
            ProfileView.viewer_user_id == viewer_user_id,
        )
    )
    if existed:
        existed.viewed_at = datetime.utcnow()
        return
    db.add(
        ProfileView(
            viewed_user_id=candidate_id,
            viewer_user_id=viewer_user_id,
            viewed_at=datetime.utcnow(),
        )
    )


def _approval_fee_from_job(job: Job) -> int:
    """10% * lương trung bình của job; fallback khi thiếu dải lương."""
    min_salary = int(job.min_salary or 0)
    max_salary = int(job.max_salary or 0)
    if min_salary > 0 and max_salary > 0:
        base_salary = int((min_salary + max_salary) / 2)
    elif max_salary > 0:
        base_salary = max_salary
    elif min_salary > 0:
        base_salary = min_salary
    else:
        base_salary = 1_000_000
    return max(1_000, int(base_salary * 0.1))


def _parse_deadline_text(deadline_text: str | None) -> datetime | None:
    raw = str(deadline_text or "").strip()
    if not raw:
        return None
    for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw, fmt)
        except Exception:
            continue
    return None


def _enforce_job_immutable_rules(db: Session, job: Job) -> None:
    now_utc = datetime.utcnow()
    if job.boost_expires_at and job.boost_expires_at > now_utc:
        raise HTTPException(
            status_code=400,
            detail="Tin đang trong thời gian boost nên không thể chỉnh sửa.",
        )
    deadline_dt = _parse_deadline_text(job.deadline_text)
    if deadline_dt and deadline_dt.date() < now_utc.date():
        job.status = JobStatus.closed
        db.commit()
        db.refresh(job)
        runtime_cache.upsert_job(job)
        raise HTTPException(
            status_code=400,
            detail="Tin đã quá hạn tuyển dụng và được chuyển archived (bất khả xâm phạm).",
        )


def _monthly_cycle_due_at(now_utc: datetime) -> datetime:
    """
    Due date là ngày cuối cùng của tháng.
    Nếu phát sinh trong 5 ngày cuối tháng thì dồn sang kỳ tháng sau.
    """
    year = now_utc.year
    month = now_utc.month
    last_day = calendar.monthrange(year, month)[1]
    window_start = max(1, last_day - 4)  # 5 ngày cuối tháng
    if now_utc.day >= window_start:
        if month == 12:
            year += 1
            month = 1
        else:
            month += 1
        last_day = calendar.monthrange(year, month)[1]
    return datetime(year, month, last_day, 23, 59, 59)


def _cycle_range_from_due(due_at: datetime) -> tuple[datetime, datetime]:
    """Kỳ hóa đơn: từ (due kỳ trước + 1 ngày) đến due hiện tại."""
    y = due_at.year
    m = due_at.month
    if m == 1:
        prev_y, prev_m = y - 1, 12
    else:
        prev_y, prev_m = y, m - 1
    prev_last_day = calendar.monthrange(prev_y, prev_m)[1]
    prev_due_day = max(1, prev_last_day - 5)
    prev_due = datetime(prev_y, prev_m, prev_due_day, 23, 59, 59)
    start = datetime(prev_due.year, prev_due.month, prev_due.day) + timedelta(days=1)
    end = datetime(due_at.year, due_at.month, due_at.day)
    return start, end


def _payment_window_from_due(due_at: datetime) -> tuple[datetime, datetime]:
    """Cửa sổ thanh toán: 5 ngày cuối tháng của kỳ invoice."""
    last_day = calendar.monthrange(due_at.year, due_at.month)[1]
    start_day = max(1, last_day - 4)
    start = datetime(due_at.year, due_at.month, start_day, 0, 0, 0)
    end = datetime(due_at.year, due_at.month, last_day, 23, 59, 59)
    return start, end


def _has_overdue_hr_invoice(db: Session, hr_user_id: int) -> bool:
    now = datetime.utcnow()
    inv_id = db.scalar(
        select(Invoice.id).where(
            Invoice.owner_user_id == hr_user_id,
            Invoice.invoice_type == InvoiceType.candidate_contact_unlock,
            Invoice.status == InvoiceStatus.pending,
            Invoice.due_at < now,
        )
    )
    return inv_id is not None


def _require_hr_billing_clear(db: Session, user: User) -> None:
    if _has_overdue_hr_invoice(db, user.id):
        raise HTTPException(
            status_code=403,
            detail="Tài khoản đang bị tạm khoá do hóa đơn quá hạn. Vui lòng thanh toán để tiếp tục sử dụng hệ thống.",
        )


def _upsert_monthly_hr_invoice(
    db: Session,
    *,
    owner_user_id: int,
    amount_vnd: int,
    application_id: int,
) -> Invoice:
    due_at = _monthly_cycle_due_at(datetime.utcnow())
    base_note = f"Hoa don tuyen dung theo ky {due_at.strftime('%m/%Y')}"
    inv = db.scalar(
        select(Invoice).where(
            Invoice.owner_user_id == owner_user_id,
            Invoice.invoice_type == InvoiceType.candidate_contact_unlock,
            Invoice.status == InvoiceStatus.pending,
            Invoice.due_at == due_at,
        )
    )
    if inv:
        inv.amount = Decimal(inv.amount) + Decimal(amount_vnd)
        inv.note = base_note
        return inv
    return create_invoice(
        db=db,
        owner_user_id=owner_user_id,
        invoice_type=InvoiceType.candidate_contact_unlock,
        amount_vnd=amount_vnd,
        note=base_note,
        application_id=None,
        due_at=due_at,
    )


def _to_job_out(job: Job, db: Session, company_name: str | None = None) -> JobOut:
    app_count = db.scalar(select(func.count()).select_from(JobApplication).where(JobApplication.job_id == job.id)) or 0
    if company_name is None:
        hp = db.scalar(select(HRProfile).where(HRProfile.user_id == job.hr_user_id))
        company_name = hp.company_name if hp else None
    raw_status = job.status.value if hasattr(job.status, "value") else str(job.status or "").strip()
    if raw_status not in {s.value for s in JobStatus}:
        raw_status = JobStatus.closed.value
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
def hr_dashboard(user: Annotated[User, Depends(get_current_user)], db: Annotated[Session, Depends(get_db)]) -> StatsOut:
    _require_hr(user)
    total_jobs = db.scalar(select(func.count()).select_from(Job).where(Job.hr_user_id == user.id)) or 0
    total_apps = (
        db.scalar(
            select(func.count())
            .select_from(JobApplication)
            .join(Job, Job.id == JobApplication.job_id)
            .where(Job.hr_user_id == user.id)
        )
        or 0
    )
    views = (
        db.scalar(
            select(func.coalesce(func.sum(Job.view_count), 0)).where(Job.hr_user_id == user.id)
        )
        or 0
    )
    responded_apps = (
        db.scalar(
            select(func.count())
            .select_from(JobApplication)
            .join(Job, Job.id == JobApplication.job_id)
            .where(
                Job.hr_user_id == user.id,
                JobApplication.status != ApplicationStatus.pending,
            )
        )
        or 0
    )
    rate = int((responded_apps * 100) / total_apps) if total_apps > 0 else 0
    monthly = db.execute(
        select(func.month(Job.created_at), func.count())
        .where(Job.hr_user_id == user.id)
        .group_by(func.month(Job.created_at))
        .order_by(func.month(Job.created_at))
    ).all()
    pending_rows = db.execute(
        select(JobApplication, Job, User)
        .join(Job, Job.id == JobApplication.job_id)
        .join(User, User.id == JobApplication.candidate_id)
        .where(
            Job.hr_user_id == user.id,
            JobApplication.status == ApplicationStatus.pending,
        )
        .order_by(JobApplication.created_at.desc(), JobApplication.id.desc())
        .limit(30)
    ).all()
    recent_pending_apps: list[dict] = []
    for app, job, cand in pending_rows:
        app_status = _normalized_app_status(app.status)
        recent_pending_apps.append(
            {
                "application_id": app.id,
                "job_title": job.title,
                "candidate_name": cand.full_name or cand.email,
                "status": app_status.value,
                "applied_at": app.created_at.isoformat(),
            }
        )
    labels = [f"T{m[0]}" for m in monthly] if monthly else ["T1", "T2", "T3"]
    values = [int(m[1]) for m in monthly] if monthly else [0, 0, 0]
    return StatsOut(
        labels=labels,
        values=values,
        cards={
            "jobs": int(total_jobs),
            "candidates": int(total_apps),
            "views": views,
            "response_rate": rate,
        },
        recent_pending_applications=recent_pending_apps,
    )


@router.post("/jobs", response_model=JobOut)
def create_job(
    body: JobCreate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> JobOut:
    _require_approved_hr(user)
    _require_hr_billing_clear(db, user)
    st = JobStatus.draft if body.as_draft else JobStatus.pending_approval
    job = Job(
        hr_user_id=user.id,
        title=body.title,
        description=body.description,
        department=body.department,
        level=body.level,
        min_salary=body.min_salary,
        max_salary=body.max_salary,
        location=body.location,
        job_type=body.job_type,
        headcount=body.count,
        deadline_text=body.deadline,
        status=st,
    )
    db.add(job)
    notify_user(
        db,
        user_id=int(user.id),
        title="Tạo tin tuyển dụng",
        message=f"Tin '{body.title}' đã được tạo thành công.",
    )
    notify_role(
        db,
        role=UserRole.admin,
        title="Tin chờ duyệt mới",
        message=f"HR vừa gửi tin '{body.title}' cần phê duyệt.",
    )
    db.commit()
    db.refresh(job)
    runtime_cache.upsert_job(job)
    return _to_job_out(job, db, company_name=user.hr_profile.company_name if user.hr_profile else None)


@router.get("/jobs", response_model=list[JobOut])
def my_jobs(user: Annotated[User, Depends(get_current_user)], db: Annotated[Session, Depends(get_db)]) -> list[JobOut]:
    _require_hr(user)
    rows = db.scalars(select(Job).where(Job.hr_user_id == user.id).order_by(Job.id.desc())).all()
    company_name = user.hr_profile.company_name if user.hr_profile else None
    return [_to_job_out(job, db, company_name=company_name) for job in rows]


@router.get("/jobs/{job_id}", response_model=JobOut)
def get_job_detail(
    job_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> JobOut:
    _require_hr(user)
    _require_hr_billing_clear(db, user)
    job = db.get(Job, job_id)
    if not job or job.hr_user_id != user.id:
        raise HTTPException(status_code=404, detail="Not found")
    return _to_job_out(job, db, company_name=user.hr_profile.company_name if user.hr_profile else None)


@router.put("/jobs/{job_id}", response_model=JobOut)
def update_job(
    job_id: int,
    body: JobCreate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> JobOut:
    _require_approved_hr(user)
    _require_hr_billing_clear(db, user)
    job = db.get(Job, job_id)
    if not job or job.hr_user_id != user.id:
        raise HTTPException(status_code=404, detail="Not found")
    _enforce_job_immutable_rules(db, job)
    job.title = body.title
    job.description = body.description
    job.department = body.department
    job.level = body.level
    job.min_salary = body.min_salary
    job.max_salary = body.max_salary
    job.location = body.location
    job.job_type = body.job_type
    job.headcount = body.count
    job.deadline_text = body.deadline
    job.status = JobStatus.pending_approval
    db.commit()
    db.refresh(job)
    runtime_cache.upsert_job(job)
    return _to_job_out(job, db, company_name=user.hr_profile.company_name if user.hr_profile else None)


@router.delete("/jobs/{job_id}")
def delete_job(
    job_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    _require_hr(user)
    _require_hr_billing_clear(db, user)
    job = db.get(Job, job_id)
    if not job or job.hr_user_id != user.id:
        raise HTTPException(status_code=404, detail="Not found")
    # Soft delete: keep job + applications for history, just stop recruiting.
    current_status = job.status.value if hasattr(job.status, "value") else str(job.status or "").strip()
    if current_status != JobStatus.closed.value:
        # Assign raw string for compatibility with DBs that currently deserialize enum as plain string.
        job.status = JobStatus.closed.value
    db.commit()
    db.refresh(job)
    runtime_cache.upsert_job(job)
    status_value = job.status.value if hasattr(job.status, "value") else str(job.status)
    return {"ok": True, "status": status_value}


@router.put("/jobs/{job_id}/submit", response_model=JobOut)
def submit_job(
    job_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> JobOut:
    _require_approved_hr(user)
    _require_hr_billing_clear(db, user)
    job = db.get(Job, job_id)
    if not job or job.hr_user_id != user.id:
        raise HTTPException(status_code=404, detail="Not found")
    _enforce_job_immutable_rules(db, job)
    if job.status == JobStatus.published:
        raise HTTPException(status_code=400, detail="Already published")
    job.status = JobStatus.pending_approval
    db.commit()
    db.refresh(job)
    runtime_cache.upsert_job(job)
    return _to_job_out(job, db, company_name=user.hr_profile.company_name if user.hr_profile else None)


@router.get("/applications", response_model=dict | list[dict])
def list_applications_for_hr(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    page: int | None = Query(default=None, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    keyword: str | None = Query(default=None),
    status_filter: str | None = Query(default=None),
    sort_by: str = Query(default="newest"),
) -> list[dict] | dict:
    _require_hr(user)
    q = (
        select(JobApplication, Job, User, HRProfile.company_name)
        .join(Job, Job.id == JobApplication.job_id)
        .join(User, User.id == JobApplication.candidate_id)
        .outerjoin(HRProfile, HRProfile.user_id == Job.hr_user_id)
        .where(Job.hr_user_id == user.id)
    )
    if status_filter and status_filter in {"pending", "reviewed", "approved", "rejected"}:
        q = q.where(JobApplication.status == ApplicationStatus(status_filter))
    kw = (keyword or "").strip().lower()
    if kw:
        like = f"%{kw}%"
        q = q.where(
            func.lower(func.coalesce(User.full_name, "")).like(like)
            | func.lower(func.coalesce(User.email, "")).like(like)
            | func.lower(func.coalesce(Job.title, "")).like(like)
            | func.lower(func.coalesce(HRProfile.company_name, "")).like(like)
            | func.lower(func.coalesce(Job.location, "")).like(like)
        )

    if sort_by == "oldest":
        q = q.order_by(JobApplication.created_at.asc(), JobApplication.id.asc())
    elif sort_by == "name_asc":
        q = q.order_by(func.lower(func.coalesce(User.full_name, "")).asc(), User.id.asc())
    elif sort_by == "name_desc":
        q = q.order_by(func.lower(func.coalesce(User.full_name, "")).desc(), User.id.desc())
    else:
        q = q.order_by(JobApplication.created_at.desc(), JobApplication.id.desc())

    count_q = (
        select(func.count())
        .select_from(JobApplication)
        .join(Job, Job.id == JobApplication.job_id)
        .join(User, User.id == JobApplication.candidate_id)
        .outerjoin(HRProfile, HRProfile.user_id == Job.hr_user_id)
        .where(Job.hr_user_id == user.id)
    )
    if status_filter and status_filter in {"pending", "reviewed", "approved", "rejected"}:
        count_q = count_q.where(JobApplication.status == ApplicationStatus(status_filter))
    if kw:
        like = f"%{kw}%"
        count_q = count_q.where(
            func.lower(func.coalesce(User.full_name, "")).like(like)
            | func.lower(func.coalesce(User.email, "")).like(like)
            | func.lower(func.coalesce(Job.title, "")).like(like)
            | func.lower(func.coalesce(HRProfile.company_name, "")).like(like)
            | func.lower(func.coalesce(Job.location, "")).like(like)
        )
    total = int(db.scalar(count_q) or 0)
    if page is not None:
        offset = (page - 1) * page_size
        q = q.offset(offset).limit(page_size)
    else:
        q = q.limit(500)
    rows = db.execute(q).all()
    out: list[dict] = []
    for app, job, cand, company_name in rows:
        cv = db.get(CVDocument, app.cv_id) if app.cv_id else None
        cprof = runtime_cache.candidate_profile_by_user_id.get(cand.id)
        if not cprof:
            cprof = db.scalar(select(CandidateProfile).where(CandidateProfile.user_id == cand.id))
            if cprof:
                runtime_cache.upsert_candidate_profile(cprof)
        app_status = _normalized_app_status(app.status)
        can_view_private = app_status == ApplicationStatus.approved or bool(app.contact_unlocked_at)
        out.append(
            {
                "application_id": app.id,
                "job_title": job.title,
                "candidate_name": cand.full_name or cand.email,
                "candidate_email": cand.email if can_view_private else "",
                "contact_unlocked": bool(app.contact_unlocked_at),
                "can_view_full_profile": bool(can_view_private),
                "can_view_cv_detail": bool(can_view_private and app.cv_id),
                "status": app_status.value,
                "cv_id": app.cv_id,
                "cv_name": cv.original_name if cv else None,
                "applied_at": app.created_at.strftime("%d/%m/%Y"),
                "accepted_at": app.accepted_at.isoformat() if app.accepted_at else None,
                "company": company_name or "",
                "location": job.location or "",
                "candidate_profile": {
                    "tagline": cprof.tagline if cprof else None,
                    "phone": cprof.phone if (cprof and can_view_private) else None,
                    "address": cprof.address if (cprof and can_view_private) else None,
                    "professional_field": cprof.professional_field if cprof else None,
                    "degree": cprof.degree if cprof else None,
                    "experience_text": cprof.experience_text if cprof else None,
                    "language": cprof.language if cprof else None,
                    "skills_json": cprof.skills_as_dict() if cprof else {},
                },
                "is_pro_active": _is_candidate_pro_active(db, cand.id),
            }
        )
    if page is None:
        return out
    return {
        "items": out,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size if page_size > 0 else 1,
    }


@router.post("/applications/{application_id}/view-profile")
def view_candidate_profile(
    application_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    _require_hr(user)
    _require_hr_billing_clear(db, user)
    row = db.execute(
        select(JobApplication, Job, User)
        .join(Job, Job.id == JobApplication.job_id)
        .join(User, User.id == JobApplication.candidate_id)
        .where(JobApplication.id == application_id, Job.hr_user_id == user.id)
    ).first()
    if not row:
        raise HTTPException(status_code=404, detail="Application not found")
    app, job, cand = row
    _mark_candidate_profile_view(
        db,
        candidate_id=cand.id,
        viewer_user_id=user.id,
        job_id=job.id,
        application_id=app.id,
    )
    app_status = _normalized_app_status(app.status)
    if app_status == ApplicationStatus.pending:
        app.status = ApplicationStatus.reviewed
    db.commit()
    return {"ok": True, "application_id": application_id, "status": _normalized_app_status(app.status).value}


@router.get("/applications/{application_id}/cv/download")
def download_application_cv(
    application_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> FileResponse:
    _require_hr(user)
    _require_hr_billing_clear(db, user)
    row = db.execute(
        select(JobApplication, Job, CVDocument)
        .join(Job, Job.id == JobApplication.job_id)
        .join(CVDocument, CVDocument.id == JobApplication.cv_id)
        .where(JobApplication.id == application_id, Job.hr_user_id == user.id)
    ).first()
    if not row:
        raise HTTPException(status_code=404, detail="Không tìm thấy CV ứng viên")
    app, _job, cv = row
    path = resolve_existing_file(settings, cv.stored_filename)
    if not path or not path.is_file():
        raise HTTPException(status_code=404, detail="File CV không tồn tại")
    media_type = cv.mime_type or "application/octet-stream"
    return FileResponse(path=str(path), filename=cv.original_name, media_type=media_type)


@router.post("/applications/{application_id}/accept", response_model=InvoiceOut)
def accept_application_and_generate_invoice(
    application_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Invoice:
    _require_approved_hr(user)
    _require_hr_billing_clear(db, user)
    row = db.execute(
        select(JobApplication, Job)
        .join(Job, Job.id == JobApplication.job_id)
        .where(JobApplication.id == application_id, Job.hr_user_id == user.id)
    ).first()
    if not row:
        raise HTTPException(status_code=404, detail="Application not found")
    app, job = row
    if _normalized_app_status(app.status) == ApplicationStatus.approved:
        due_at = _monthly_cycle_due_at(datetime.utcnow())
        existing_cycle = db.scalar(
            select(Invoice).where(
                Invoice.owner_user_id == user.id,
                Invoice.invoice_type == InvoiceType.candidate_contact_unlock,
                Invoice.status == InvoiceStatus.pending,
                Invoice.due_at == due_at,
            )
        )
        if existing_cycle:
            return existing_cycle
    amount = _approval_fee_from_job(job)

    app.accept()
    invoice = _upsert_monthly_hr_invoice(
        db,
        owner_user_id=user.id,
        amount_vnd=amount,
        application_id=app.id,
    )
    db.commit()
    db.refresh(invoice)
    return invoice


@router.post("/invoices/{invoice_id}/mark-paid", response_model=InvoiceOut)
def mark_hr_invoice_paid(
    invoice_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Invoice:
    _require_hr(user)
    invoice = db.scalar(select(Invoice).where(Invoice.id == invoice_id, Invoice.owner_user_id == user.id))
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    invoice_type = _invoice_type_key(invoice.invoice_type)
    now = datetime.utcnow()
    if invoice_type == InvoiceType.job_boost.value:
        boost_due = invoice.due_at or ((invoice.created_at or now) + timedelta(minutes=30))
        if now > boost_due:
            raise HTTPException(
                status_code=400,
                detail="Hoa don boost da qua han thanh toan (30 phut tu luc tao). Vui long tao hoa don moi.",
            )
    if invoice_type == InvoiceType.candidate_contact_unlock.value:
        win_start, win_end = _payment_window_from_due(invoice.due_at)
        if now < win_start:
            raise HTTPException(
                status_code=400,
                detail=f"Chua den han thanh toan. Thoi gian thanh toan: {win_start.strftime('%d/%m/%Y')} - {win_end.strftime('%d/%m/%Y')}",
            )
        # Quá hạn vẫn cho phép thanh toán để mở khóa tài khoản HR.
    invoice = mark_invoice_paid(db, user.id, invoice_id)
    if invoice_type == InvoiceType.candidate_contact_unlock.value and invoice.application_id:
        app = db.get(JobApplication, invoice.application_id)
        if app:
            app.unlock_contact()
    if invoice_type == InvoiceType.job_boost.value:
        target_job_id = int(invoice.job_id) if invoice.job_id else None
        if target_job_id is None:
            target_job_id = _extract_job_id_from_boost_text(invoice.note)
            if target_job_id:
                invoice.job_id = target_job_id
        job = db.get(Job, int(target_job_id)) if target_job_id else None
        if job and job.hr_user_id == user.id:
            job.boost_budget_vnd = int(job.boost_budget_vnd or 0) + int(float(invoice.amount or 0))
            now_utc = datetime.utcnow()
            base_time = job.boost_expires_at if (job.boost_expires_at and job.boost_expires_at > now_utc) else now_utc
            job.boost_last_paid_at = now_utc
            job.boost_expires_at = base_time + timedelta(days=14)
            runtime_cache.upsert_job(job)
            notify_role(
                db,
                role=UserRole.candidate,
                title="Tin tuyển dụng được đẩy top",
                message=f"Tin '{job.title}' vừa được boost và sẽ hiển thị ưu tiên.",
            )
    db.commit()
    db.refresh(invoice)
    return invoice


@router.get("/invoices", response_model=list[dict])
def list_hr_invoices(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[dict]:
    _require_hr(user)
    rows = db.execute(
        select(Invoice)
        .where(
            Invoice.owner_user_id == user.id,
        )
        .order_by(Invoice.created_at.desc(), Invoice.id.desc())
    ).scalars().all()
    out: list[dict] = []
    for inv in rows:
        invoice_type = _invoice_type_key(inv.invoice_type)
        is_boost_invoice = invoice_type == InvoiceType.job_boost.value
        cycle_start, cycle_end = _cycle_range_from_due(inv.due_at) if (inv.due_at and not is_boost_invoice) else (None, None)
        pay_start, pay_end = _payment_window_from_due(inv.due_at) if (inv.due_at and not is_boost_invoice) else (None, None)
        now = datetime.utcnow()
        checkout_url = build_sepay_checkout_url(str(inv.sepay_order_code)) if inv.sepay_order_code else ""
        boost_due = inv.due_at or ((inv.created_at or now) + timedelta(minutes=30))
        display_status = inv.status.value
        if inv.status == InvoiceStatus.pending:
            if is_boost_invoice:
                display_status = "pending" if now <= boost_due else "expired"
            elif inv.due_at:
                if now > inv.due_at:
                    display_status = "overdue"
                elif pay_start and now >= pay_start:
                    display_status = "due"
        if is_boost_invoice:
            can_pay_now = bool(inv.status == InvoiceStatus.pending and checkout_url and now <= boost_due)
            payment_window_start = (inv.created_at or now).strftime("%d/%m/%Y %H:%M")
            payment_window_end = boost_due.strftime("%d/%m/%Y %H:%M")
        else:
            # Invoice pending luôn được phép redirect thanh toán từ HR dashboard.
            can_pay_now = bool(inv.status == InvoiceStatus.pending and checkout_url)
            payment_window_start = pay_start.strftime("%d/%m/%Y") if pay_start else None
            payment_window_end = pay_end.strftime("%d/%m/%Y") if pay_end else None
        out.append(
            {
                "id": inv.id,
                "invoice_code": inv.sepay_order_code or f"HD-{inv.id:05d}",
                "created_at": inv.created_at.isoformat() if inv.created_at else None,
                "due_at": (boost_due.isoformat() if is_boost_invoice else (inv.due_at.isoformat() if inv.due_at else None)),
                "period": inv.due_at.strftime("%m/%Y") if (inv.due_at and not is_boost_invoice) else "",
                "period_start": cycle_start.strftime("%d/%m/%Y") if cycle_start else None,
                "period_end": cycle_end.strftime("%d/%m/%Y") if cycle_end else None,
                "payment_window_start": payment_window_start,
                "payment_window_end": payment_window_end,
                "amount_vnd": int(inv.amount or 0),
                "status": display_status,
                "invoice_type": invoice_type,
                "note": inv.note,
                "paid_at": inv.paid_at.isoformat() if inv.paid_at else None,
                "sepay_payment_url": checkout_url,
                "can_pay_now": can_pay_now,
                "job_id": int(inv.job_id) if inv.job_id else None,
            }
        )
    def _sort_key(row: dict) -> tuple[int, float]:
        st = str(row.get("status") or "").lower()
        is_pending_group = st in {"pending", "due"}
        created_raw = str(row.get("created_at") or "")
        try:
            created_dt = datetime.fromisoformat(created_raw.replace("Z", "+00:00")) if created_raw else datetime.min
        except Exception:
            created_dt = datetime.min
        return (0 if is_pending_group else 1, -created_dt.toordinal(), -created_dt.hour, -created_dt.minute, -created_dt.second)

    out.sort(key=_sort_key)
    return out


@router.post("/jobs/{job_id}/boost-invoice", response_model=InvoiceOut)
def create_job_boost_invoice(
    job_id: int,
    body: JobBoostInvoiceCreateIn,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Invoice:
    _require_approved_hr(user)
    _require_hr_billing_clear(db, user)
    job = db.get(Job, job_id)
    if not job or job.hr_user_id != user.id:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != JobStatus.published:
        raise HTTPException(
            status_code=400,
            detail="Chi duoc boost tin da duoc duyet va dang hien thi (published).",
        )
    note = (body.note or "").strip() or f"Boost tin tuyển dụng #{job.id} - {job.title}"
    inv = create_invoice(
        db=db,
        owner_user_id=user.id,
        invoice_type=InvoiceType.job_boost,
        amount_vnd=int(body.amount_vnd),
        note=note,
        job_id=int(job.id),
        due_at=datetime.utcnow() + timedelta(minutes=30),
    )
    notify_user(
        db,
        user_id=int(user.id),
        title="Khởi tạo hóa đơn boost",
        message=f"Hóa đơn boost cho tin '{job.title}' đã được tạo.",
    )
    db.commit()
    db.refresh(inv)
    return inv


@router.put("/applications/{application_id}/status")
def update_application_status(
    application_id: int,
    body: ApplicationDecisionIn,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    _require_hr(user)
    _require_hr_billing_clear(db, user)
    row = db.execute(
        select(JobApplication, Job)
        .join(Job, Job.id == JobApplication.job_id)
        .where(JobApplication.id == application_id, Job.hr_user_id == user.id)
    ).first()
    if not row:
        raise HTTPException(status_code=404, detail="Application not found")
    app, job = row
    app_status = _normalized_app_status(app.status)
    if app_status in (ApplicationStatus.approved, ApplicationStatus.rejected):
        if body.status != app_status:
            raise HTTPException(status_code=400, detail="Don da duoc chot, khong the thay doi trang thai")
        return {"ok": True, "application_id": application_id, "status": app_status.value}
    app.status = body.status
    fee_invoice: Invoice | None = None
    if body.status == ApplicationStatus.approved:
        app.accepted_at = datetime.utcnow()
        app.unlock_contact()
        fee_amount = _approval_fee_from_job(job)
        fee_invoice = _upsert_monthly_hr_invoice(
            db,
            owner_user_id=user.id,
            amount_vnd=fee_amount,
            application_id=app.id,
        )
        notify_user(
            db,
            user_id=int(app.candidate_id),
            title="Hồ sơ được phê duyệt",
            message=f"Hồ sơ ứng tuyển cho tin '{job.title}' đã được nhà tuyển dụng phê duyệt.",
        )
    elif body.status == ApplicationStatus.rejected:
        notify_user(
            db,
            user_id=int(app.candidate_id),
            title="Hồ sơ bị từ chối",
            message=f"Hồ sơ ứng tuyển cho tin '{job.title}' đã bị từ chối.",
        )
    db.commit()
    return {
        "ok": True,
        "application_id": application_id,
        "status": _normalized_app_status(app.status).value,
        "invoice_id": fee_invoice.id if fee_invoice else None,
        "invoice_amount_vnd": int(fee_invoice.amount) if fee_invoice else None,
    }


@router.get("/applications/{application_id}/contact")
def get_candidate_contact(
    application_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    _require_hr(user)
    _require_hr_billing_clear(db, user)
    row = db.execute(
        select(JobApplication, Job, User)
        .join(Job, Job.id == JobApplication.job_id)
        .join(User, User.id == JobApplication.candidate_id)
        .where(JobApplication.id == application_id, Job.hr_user_id == user.id)
    ).first()
    if not row:
        raise HTTPException(status_code=404, detail="Application not found")
    app, _job, candidate = row
    if not app.contact_unlocked_at:
        raise HTTPException(status_code=402, detail="Can thanh toan invoice de mo thong tin lien he")
    return {
        "candidate_id": candidate.id,
        "full_name": candidate.full_name,
        "email": candidate.email,
    }


@router.get("/applications/{application_id}/cv/view")
def view_application_cv(
    application_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> FileResponse:
    _require_hr(user)
    _require_hr_billing_clear(db, user)
    row = db.execute(
        select(JobApplication, Job, CVDocument)
        .join(Job, Job.id == JobApplication.job_id)
        .join(CVDocument, CVDocument.id == JobApplication.cv_id)
        .where(JobApplication.id == application_id, Job.hr_user_id == user.id)
    ).first()
    if not row:
        raise HTTPException(status_code=404, detail="Không tìm thấy CV ứng viên")
    app, _job, cv = row
    path = resolve_existing_file(settings, cv.stored_filename)
    if not path or not path.is_file():
        raise HTTPException(status_code=404, detail="File CV không tồn tại")
    media_type = cv.mime_type or "application/pdf"
    return FileResponse(path=str(path), filename=cv.original_name, media_type=media_type)
