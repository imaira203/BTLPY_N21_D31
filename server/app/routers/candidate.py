import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..billing import create_invoice, mark_invoice_paid
from ..config import settings
from ..db import get_db
from ..deps import get_current_user
from ..models import (
    CVDocument,
    CandidateSubscription,
    HRProfile,
    Invoice,
    InvoiceStatus,
    InvoiceType,
    Job,
    JobApplication,
    JobStatus,
    SubscriptionStatus,
    User,
    UserRole,
)
from ..runtime_cache import runtime_cache
from ..schemas import CandidateSubscriptionOut, InvoiceOut, ProUpgradeIn, ApplyIn, CVOut, JobOut
from ..storage_paths import absolute_path, relative_key, resolve_existing_file

router = APIRouter(prefix="/candidate", tags=["candidate"])


def _require_candidate(user: User) -> None:
    if user.role != UserRole.candidate:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Candidate only")


def _is_pro_active(subscription: CandidateSubscription | None) -> bool:
    if not subscription or subscription.status != SubscriptionStatus.active:
        return False
    if not subscription.pro_expires_at:
        return False
    return subscription.pro_expires_at > datetime.utcnow()


@router.post("/cvs", response_model=CVOut)
async def upload_cv(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    file: UploadFile = File(...),
) -> CVDocument:
    _require_candidate(user)
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    ext = Path(file.filename or "").suffix[:16] or ".bin"
    fname = f"{user.id}_{uuid.uuid4().hex}{ext}"
    sub = settings.subdir_for("cvs")
    storage_key = relative_key(sub, fname)
    dest = absolute_path(settings, storage_key)
    dest.parent.mkdir(parents=True, exist_ok=True)
    content = await file.read()
    if len(content) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large")
    dest.write_bytes(content)
    doc = CVDocument(
        user_id=user.id,
        original_name=file.filename or fname,
        stored_filename=storage_key,
        mime_type=file.content_type,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


@router.get("/cvs", response_model=list[CVOut])
def list_cvs(user: Annotated[User, Depends(get_current_user)], db: Annotated[Session, Depends(get_db)]) -> list[CVOut]:
    _require_candidate(user)
    rows = db.scalars(select(CVDocument).where(CVDocument.user_id == user.id).order_by(CVDocument.id.desc())).all()
    return list(rows)


@router.get("/cvs/{cv_id}/download")
def download_cv(
    cv_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> FileResponse:
    _require_candidate(user)
    cv = db.get(CVDocument, cv_id)
    if not cv or cv.user_id != user.id:
        raise HTTPException(status_code=404, detail="CV not found")
    path = resolve_existing_file(settings, cv.stored_filename)
    if not path or not path.is_file():
        raise HTTPException(status_code=404, detail="CV file not found")
    return FileResponse(path=str(path), filename=cv.original_name, media_type=cv.mime_type or "application/octet-stream")


@router.get("/cvs/{cv_id}/view")
def view_cv(
    cv_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> FileResponse:
    _require_candidate(user)
    cv = db.get(CVDocument, cv_id)
    if not cv or cv.user_id != user.id:
        raise HTTPException(status_code=404, detail="CV not found")
    path = resolve_existing_file(settings, cv.stored_filename)
    if not path or not path.is_file():
        raise HTTPException(status_code=404, detail="CV file not found")
    return FileResponse(path=str(path), filename=cv.original_name, media_type=cv.mime_type or "application/pdf")


@router.delete("/cvs/{cv_id}")
def delete_cv(
    cv_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    _require_candidate(user)
    cv = db.get(CVDocument, cv_id)
    if not cv or cv.user_id != user.id:
        raise HTTPException(status_code=404, detail="CV not found")
    used = db.scalar(select(JobApplication).where(JobApplication.cv_id == cv_id))
    if used:
        raise HTTPException(status_code=400, detail="CV đã dùng để ứng tuyển, không thể xóa")
    path = resolve_existing_file(settings, cv.stored_filename)
    db.delete(cv)
    db.commit()
    if path and path.is_file():
        try:
            path.unlink()
        except OSError:
            pass
    return {"ok": True}


@router.get("/jobs", response_model=list[JobOut])
def browse_jobs(db: Annotated[Session, Depends(get_db)]) -> list[JobOut]:
    cached_jobs = runtime_cache.get_published_jobs()
    rows = []
    if cached_jobs:
        for job in sorted(cached_jobs, key=lambda item: item.id, reverse=True)[:200]:
            profile = runtime_cache.hr_profile_by_user_id.get(job.hr_user_id)
            rows.append((job, profile.company_name if profile else None))
    else:
        q = (
            select(Job, HRProfile.company_name)
            .outerjoin(HRProfile, HRProfile.user_id == Job.hr_user_id)
            .where(Job.status == JobStatus.published)
            .order_by(Job.id.desc())
            .limit(200)
        )
        rows = db.execute(q).all()
    out: list[JobOut] = []
    for job, company_name in rows:
        out.append(
            JobOut(
                id=job.id,
                hr_user_id=job.hr_user_id,
                title=job.title,
                description=job.description,
                salary_text=job.salary_text,
                location=job.location,
                job_type=job.job_type,
                status=job.status,
                admin_note=job.admin_note,
                created_at=job.created_at,
                company_name=company_name,
            )
        )
    return out


@router.post("/jobs/{job_id}/apply")
def apply_job(
    job_id: int,
    body: ApplyIn,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    _require_candidate(user)
    job = db.get(Job, job_id)
    if not job or job.status != JobStatus.published:
        raise HTTPException(status_code=404, detail="Job not found")
    cv = db.get(CVDocument, body.cv_id)
    if not cv or cv.user_id != user.id:
        raise HTTPException(status_code=400, detail="Invalid CV")
    existing = db.scalar(
        select(JobApplication).where(
            JobApplication.job_id == job_id,
            JobApplication.candidate_id == user.id,
        )
    )
    if existing:
        raise HTTPException(status_code=400, detail="Already applied")
    app = JobApplication(job_id=job_id, candidate_id=user.id, cv_id=cv.id)
    db.add(app)
    db.commit()
    return {"ok": True, "application_id": app.id}


@router.get("/subscription", response_model=CandidateSubscriptionOut)
def my_subscription(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> CandidateSubscriptionOut:
    _require_candidate(user)
    sub = runtime_cache.subscription_by_candidate_id.get(user.id)
    if not sub:
        sub = db.scalar(select(CandidateSubscription).where(CandidateSubscription.candidate_id == user.id))
    if not sub:
        sub = CandidateSubscription(candidate_id=user.id, status=SubscriptionStatus.inactive)
        db.add(sub)
        db.commit()
        db.refresh(sub)
    runtime_cache.upsert_subscription(sub)
    return CandidateSubscriptionOut(status=sub.status, pro_expires_at=sub.pro_expires_at)


@router.post("/subscription/pro/upgrade", response_model=InvoiceOut)
def create_pro_upgrade_invoice(
    body: ProUpgradeIn,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Invoice:
    _require_candidate(user)
    pending = db.scalar(
        select(Invoice).where(
            Invoice.owner_user_id == user.id,
            Invoice.invoice_type == InvoiceType.pro_upgrade,
            Invoice.status == InvoiceStatus.pending,
        )
    )
    if pending:
        return pending
    amount = body.months * settings.pro_monthly_price_vnd
    note = f"Nang cap tai khoan PRO {body.months} thang"
    inv = create_invoice(
        db=db,
        owner_user_id=user.id,
        invoice_type=InvoiceType.pro_upgrade,
        amount_vnd=amount,
        note=note,
    )
    db.commit()
    db.refresh(inv)
    return inv


@router.post("/invoices/{invoice_id}/mark-paid", response_model=InvoiceOut)
def mark_candidate_invoice_paid(
    invoice_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Invoice:
    _require_candidate(user)
    invoice = mark_invoice_paid(db, user.id, invoice_id)
    if invoice.invoice_type == InvoiceType.pro_upgrade:
        sub = runtime_cache.subscription_by_candidate_id.get(user.id)
        if not sub:
            sub = db.scalar(select(CandidateSubscription).where(CandidateSubscription.candidate_id == user.id))
        if not sub:
            sub = CandidateSubscription(candidate_id=user.id, status=SubscriptionStatus.inactive)
            db.add(sub)
            db.flush()
        current_start = sub.pro_expires_at if sub.pro_expires_at and sub.pro_expires_at > datetime.utcnow() else datetime.utcnow()
        duration_days = 30
        amount = int(float(invoice.amount))
        months = max(1, round(amount / max(1, settings.pro_monthly_price_vnd)))
        sub.status = SubscriptionStatus.active
        sub.pro_expires_at = current_start + timedelta(days=duration_days * months)
        runtime_cache.upsert_subscription(sub)
    db.commit()
    db.refresh(invoice)
    return invoice


@router.get("/jobs/{job_id}/competitors")
def job_competitor_insights(
    job_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    _require_candidate(user)
    sub = runtime_cache.subscription_by_candidate_id.get(user.id)
    if not sub:
        sub = db.scalar(select(CandidateSubscription).where(CandidateSubscription.candidate_id == user.id))
    if not _is_pro_active(sub):
        raise HTTPException(status_code=403, detail="Can nang cap PRO de xem thong tin doi thu")

    my_application = db.scalar(
        select(JobApplication).where(JobApplication.job_id == job_id, JobApplication.candidate_id == user.id)
    )
    if not my_application:
        raise HTTPException(status_code=403, detail="Chi xem duoc doi thu tai tin da ung tuyen")

    total = db.scalar(select(func.count()).select_from(JobApplication).where(JobApplication.job_id == job_id)) or 0
    rank = (
        db.scalar(
            select(func.count())
            .select_from(JobApplication)
            .where(JobApplication.job_id == job_id, JobApplication.created_at <= my_application.created_at)
        )
        or 1
    )
    rows = db.execute(
        select(JobApplication.id, JobApplication.created_at)
        .where(JobApplication.job_id == job_id, JobApplication.candidate_id != user.id)
        .order_by(JobApplication.created_at.desc())
        .limit(30)
    ).all()
    competitors = [{"alias": f"Ung vien #{rid}", "applied_at": created.isoformat()} for rid, created in rows]
    return {
        "job_id": job_id,
        "total_competitors": max(0, int(total) - 1),
        "my_apply_order": int(rank),
        "recent_competitors": competitors,
    }
