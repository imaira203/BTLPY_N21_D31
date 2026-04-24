from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..billing import create_invoice, mark_invoice_paid
from ..config import settings
from ..db import get_db
from ..deps import get_current_user
from ..models import (
    CandidateProfile,
    CVDocument,
    HRApprovalStatus,
    HRProfile,
    Invoice,
    InvoiceStatus,
    InvoiceType,
    Job,
    JobApplication,
    JobStatus,
    User,
    UserRole,
    ApplicationStatus,
)
from ..runtime_cache import runtime_cache
from ..schemas import ApplicationDecisionIn, InvoiceOut, JobCreate, JobOut, StatsOut
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


def _to_job_out(job: Job, db: Session, company_name: str | None = None) -> JobOut:
    app_count = db.scalar(select(func.count()).select_from(JobApplication).where(JobApplication.job_id == job.id)) or 0
    if company_name is None:
        hp = db.scalar(select(HRProfile).where(HRProfile.user_id == job.hr_user_id))
        company_name = hp.company_name if hp else None
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
        status=job.status,
        admin_note=job.admin_note,
        created_at=job.created_at,
        company_name=company_name,
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
        recent_pending_apps.append(
            {
                "application_id": app.id,
                "job_title": job.title,
                "candidate_name": cand.full_name or cand.email,
                "status": app.status.value,
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
    job = db.get(Job, job_id)
    if not job or job.hr_user_id != user.id:
        raise HTTPException(status_code=404, detail="Not found")
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
    if job.status in (JobStatus.draft, JobStatus.rejected):
        job.status = JobStatus.draft if body.as_draft else JobStatus.pending_approval
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
    job = db.get(Job, job_id)
    if not job or job.hr_user_id != user.id:
        raise HTTPException(status_code=404, detail="Not found")
    if job.status == JobStatus.published:
        raise HTTPException(status_code=400, detail="Không thể xóa tin đã publish")
    db.delete(job)
    db.commit()
    runtime_cache.jobs_by_id.pop(job.id, None)
    runtime_cache.published_job_ids = [jid for jid in runtime_cache.published_job_ids if jid != job.id]
    return {"ok": True}


@router.put("/jobs/{job_id}/submit", response_model=JobOut)
def submit_job(
    job_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> JobOut:
    _require_approved_hr(user)
    job = db.get(Job, job_id)
    if not job or job.hr_user_id != user.id:
        raise HTTPException(status_code=404, detail="Not found")
    if job.status == JobStatus.published:
        raise HTTPException(status_code=400, detail="Already published")
    job.status = JobStatus.pending_approval
    db.commit()
    db.refresh(job)
    runtime_cache.upsert_job(job)
    return _to_job_out(job, db, company_name=user.hr_profile.company_name if user.hr_profile else None)


@router.get("/applications", response_model=list[dict])
def list_applications_for_hr(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[dict]:
    _require_hr(user)
    q = (
        select(JobApplication, Job, User, HRProfile.company_name)
        .join(Job, Job.id == JobApplication.job_id)
        .join(User, User.id == JobApplication.candidate_id)
        .outerjoin(HRProfile, HRProfile.user_id == Job.hr_user_id)
        .where(Job.hr_user_id == user.id)
        .order_by(JobApplication.id.desc())
        .limit(500)
    )
    rows = db.execute(q).all()
    out: list[dict] = []
    for app, job, cand, company_name in rows:
        cv = db.get(CVDocument, app.cv_id) if app.cv_id else None
        cprof = runtime_cache.candidate_profile_by_user_id.get(cand.id)
        if not cprof:
            cprof = db.scalar(select(CandidateProfile).where(CandidateProfile.user_id == cand.id))
            if cprof:
                runtime_cache.upsert_candidate_profile(cprof)
        out.append(
            {
                "application_id": app.id,
                "job_title": job.title,
                "candidate_name": cand.full_name or cand.email,
                "candidate_email": cand.email if app.contact_unlocked_at else "",
                "contact_unlocked": bool(app.contact_unlocked_at),
                "status": app.status.value,
                "cv_id": app.cv_id,
                "cv_name": cv.original_name if cv else None,
                "applied_at": app.created_at.strftime("%d/%m/%Y"),
                "company": company_name or "",
                "location": job.location or "",
                "candidate_profile": {
                    "headline": cprof.headline if cprof else None,
                    "introduction": cprof.introduction if cprof else None,
                    "skills": cprof.skills if cprof else None,
                    "experience": cprof.experience if cprof else None,
                },
            }
        )
    return out


@router.get("/applications/{application_id}/cv/download")
def download_application_cv(
    application_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> FileResponse:
    _require_hr(user)
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
    row = db.execute(
        select(JobApplication, Job)
        .join(Job, Job.id == JobApplication.job_id)
        .where(JobApplication.id == application_id, Job.hr_user_id == user.id)
    ).first()
    if not row:
        raise HTTPException(status_code=404, detail="Application not found")
    app, job = row
    if app.status == ApplicationStatus.approved:
        existing = db.scalar(
            select(Invoice).where(
                Invoice.application_id == app.id,
                Invoice.invoice_type == InvoiceType.candidate_contact_unlock,
                Invoice.owner_user_id == user.id,
            )
        )
        if existing:
            return existing
    amount = job.contact_unlock_fee()
    existing_pending = db.scalar(
        select(Invoice).where(
            Invoice.application_id == app.id,
            Invoice.invoice_type == InvoiceType.candidate_contact_unlock,
            Invoice.owner_user_id == user.id,
            Invoice.status == InvoiceStatus.pending,
        )
    )
    if existing_pending:
        return existing_pending

    app.accept()
    invoice = create_invoice(
        db=db,
        owner_user_id=user.id,
        invoice_type=InvoiceType.candidate_contact_unlock,
        amount_vnd=amount,
        note=f"Phi mo lien he ung vien {app.id} (tinh theo luong cao nhat hoac cap bac)",
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
    invoice = mark_invoice_paid(db, user.id, invoice_id)
    if invoice.invoice_type == InvoiceType.candidate_contact_unlock and invoice.application_id:
        app = db.get(JobApplication, invoice.application_id)
        if app:
            app.unlock_contact()
    db.commit()
    db.refresh(invoice)
    return invoice


@router.put("/applications/{application_id}/status")
def update_application_status(
    application_id: int,
    body: ApplicationDecisionIn,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    _require_hr(user)
    row = db.execute(
        select(JobApplication, Job)
        .join(Job, Job.id == JobApplication.job_id)
        .where(JobApplication.id == application_id, Job.hr_user_id == user.id)
    ).first()
    if not row:
        raise HTTPException(status_code=404, detail="Application not found")
    app, _job = row
    app.status = body.status
    if body.status == ApplicationStatus.approved:
        app.accepted_at = datetime.utcnow()
    db.commit()
    return {"ok": True, "application_id": application_id, "status": app.status.value}


@router.get("/applications/{application_id}/contact")
def get_candidate_contact(
    application_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    _require_hr(user)
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
