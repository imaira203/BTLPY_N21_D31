import uuid
import base64
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Request, UploadFile, status
from fastapi.responses import FileResponse, HTMLResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..billing import build_sepay_checkout_fields, create_invoice, mark_invoice_paid
from ..config import settings
from ..db import get_db
from ..deps import get_current_user
from ..models import (
    CVDocument,
    CandidateSavedJob,
    CandidateSubscription,
    CandidateSubscriptionPayment,
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
from ..schemas import (
    ApplyIn,
    CandidateApplicationHistoryOut,
    CandidateSubscriptionOut,
    CandidateSubscriptionPaymentOut,
    CVOut,
    InvoiceOut,
    JobOut,
    ProUpgradeIn,
    SavedJobOut,
)
from ..storage_paths import absolute_path, relative_key, resolve_existing_file

router = APIRouter(prefix="/candidate", tags=["candidate"])
log = logging.getLogger("jobhub.api.candidate")


def _require_candidate(user: User) -> None:
    if user.role != UserRole.candidate:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Candidate only")


def _is_pro_active(subscription: CandidateSubscription | None) -> bool:
    if not subscription or subscription.status != SubscriptionStatus.active:
        return False
    if not subscription.pro_expires_at:
        return False
    return subscription.pro_expires_at > datetime.utcnow()


def _ensure_subscription_row(db: Session, candidate_id: int) -> CandidateSubscription:
    # Luôn lấy từ DB session hiện tại để đảm bảo object persistent (không detached từ runtime_cache).
    sub = db.scalar(select(CandidateSubscription).where(CandidateSubscription.candidate_id == candidate_id))
    if not sub:
        sub = CandidateSubscription(candidate_id=candidate_id, status=SubscriptionStatus.inactive)
        db.add(sub)
        db.flush()
    return sub


def _refresh_subscription_status(sub: CandidateSubscription) -> None:
    if sub.pro_expires_at and sub.pro_expires_at <= datetime.utcnow():
        sub.status = SubscriptionStatus.expired
    elif sub.pro_expires_at and sub.pro_expires_at > datetime.utcnow():
        sub.status = SubscriptionStatus.active
    elif sub.status == SubscriptionStatus.active:
        sub.status = SubscriptionStatus.expired


def _apply_pro_upgrade_from_invoice(db: Session, invoice: Invoice) -> None:
    sub = _ensure_subscription_row(db, invoice.owner_user_id)
    current_start = sub.pro_expires_at if sub.pro_expires_at and sub.pro_expires_at > datetime.utcnow() else datetime.utcnow()
    duration_days = 30
    amount = int(float(invoice.amount))
    months = max(1, round(amount / max(1, settings.pro_monthly_price_vnd)))
    sub.status = SubscriptionStatus.active
    sub.pro_expires_at = current_start + timedelta(days=duration_days * months)
    existing_payment = db.scalar(
        select(CandidateSubscriptionPayment).where(CandidateSubscriptionPayment.invoice_id == invoice.id)
    )
    if not existing_payment:
        db.add(
            CandidateSubscriptionPayment(
                candidate_id=invoice.owner_user_id,
                invoice_id=invoice.id,
                months=months,
                amount=invoice.amount,
                currency=invoice.currency,
                paid_at=invoice.paid_at or datetime.utcnow(),
            )
        )
    runtime_cache.upsert_subscription(sub)


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
        app_count = db.scalar(select(func.count()).select_from(JobApplication).where(JobApplication.job_id == job.id)) or 0
        out.append(
            JobOut(
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
        )
    return out


@router.post("/jobs/{job_id}/view")
def track_job_view(
    job_id: int,
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    job = db.get(Job, job_id)
    if not job or job.status != JobStatus.published:
        raise HTTPException(status_code=404, detail="Job not found")
    job.view_count = int(job.view_count or 0) + 1
    db.commit()
    return {"ok": True, "job_id": job.id, "view_count": int(job.view_count)}


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
    cv_id = body.cv_id
    if cv_id is None:
        latest_cv = db.scalar(
            select(CVDocument)
            .where(CVDocument.user_id == user.id)
            .order_by(CVDocument.id.desc())
            .limit(1)
        )
        if not latest_cv:
            raise HTTPException(status_code=400, detail="Ban can tai len CV truoc khi ung tuyen")
        cv_id = latest_cv.id
    cv = db.get(CVDocument, cv_id)
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
    db.refresh(app)
    return {"ok": True, "application_id": app.id, "status": app.status.value}


@router.post("/jobs/{job_id}/apply-with-cv")
async def apply_job_with_optional_new_cv(
    job_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    cv_id: int | None = Form(default=None),
    cv_file: UploadFile | None = File(default=None),
) -> dict:
    _require_candidate(user)
    job = db.get(Job, job_id)
    if not job or job.status != JobStatus.published:
        raise HTTPException(status_code=404, detail="Job not found")
    existing = db.scalar(
        select(JobApplication).where(
            JobApplication.job_id == job_id,
            JobApplication.candidate_id == user.id,
        )
    )
    if existing:
        raise HTTPException(status_code=400, detail="Already applied")

    selected_cv_id = cv_id
    if cv_file is not None:
        settings.upload_dir.mkdir(parents=True, exist_ok=True)
        ext = Path(cv_file.filename or "").suffix[:16] or ".bin"
        fname = f"{user.id}_{uuid.uuid4().hex}{ext}"
        sub = settings.subdir_for("cvs")
        storage_key = relative_key(sub, fname)
        dest = absolute_path(settings, storage_key)
        dest.parent.mkdir(parents=True, exist_ok=True)
        content = await cv_file.read()
        if len(content) > settings.max_upload_mb * 1024 * 1024:
            raise HTTPException(status_code=400, detail="File too large")
        dest.write_bytes(content)
        doc = CVDocument(
            user_id=user.id,
            original_name=cv_file.filename or fname,
            stored_filename=storage_key,
            mime_type=cv_file.content_type,
        )
        db.add(doc)
        db.flush()
        selected_cv_id = doc.id
    elif selected_cv_id is None:
        latest_cv = db.scalar(
            select(CVDocument)
            .where(CVDocument.user_id == user.id)
            .order_by(CVDocument.id.desc())
            .limit(1)
        )
        if latest_cv:
            selected_cv_id = latest_cv.id

    if selected_cv_id is None:
        raise HTTPException(status_code=400, detail="Ban can chon CV co san hoac tai len CV moi")

    cv = db.get(CVDocument, selected_cv_id)
    if not cv or cv.user_id != user.id:
        raise HTTPException(status_code=400, detail="Invalid CV")

    app = JobApplication(job_id=job_id, candidate_id=user.id, cv_id=cv.id)
    db.add(app)
    db.commit()
    db.refresh(app)
    return {"ok": True, "application_id": app.id, "status": app.status.value, "cv_id": cv.id}


@router.get("/applications", response_model=list[CandidateApplicationHistoryOut])
def list_my_applications(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[CandidateApplicationHistoryOut]:
    _require_candidate(user)
    rows = db.execute(
        select(JobApplication, Job, HRProfile.company_name)
        .join(Job, Job.id == JobApplication.job_id)
        .outerjoin(HRProfile, HRProfile.user_id == Job.hr_user_id)
        .where(JobApplication.candidate_id == user.id)
        .order_by(JobApplication.created_at.desc(), JobApplication.id.desc())
    ).all()
    out: list[CandidateApplicationHistoryOut] = []
    for app, job, company_name in rows:
        out.append(
            CandidateApplicationHistoryOut(
                id=app.id,
                job_id=app.job_id,
                title=job.title,
                company_name=company_name,
                location=job.location,
                status=app.status,
                applied_at=app.created_at,
            )
        )
    return out


@router.post("/jobs/{job_id}/save", response_model=SavedJobOut)
def save_job(
    job_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> CandidateSavedJob:
    _require_candidate(user)
    job = db.get(Job, job_id)
    if not job or job.status != JobStatus.published:
        raise HTTPException(status_code=404, detail="Job not found")
    existing = db.scalar(
        select(CandidateSavedJob).where(
            CandidateSavedJob.candidate_id == user.id,
            CandidateSavedJob.job_id == job_id,
        )
    )
    if existing:
        return existing
    saved_job = CandidateSavedJob(candidate_id=user.id, job_id=job_id)
    db.add(saved_job)
    db.commit()
    db.refresh(saved_job)
    return saved_job


@router.delete("/jobs/{job_id}/save")
def unsave_job(
    job_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    _require_candidate(user)
    saved = db.scalar(
        select(CandidateSavedJob).where(
            CandidateSavedJob.candidate_id == user.id,
            CandidateSavedJob.job_id == job_id,
        )
    )
    if not saved:
        return {"ok": True}
    db.delete(saved)
    db.commit()
    return {"ok": True}


@router.get("/jobs/saved", response_model=list[JobOut])
def list_saved_jobs(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[JobOut]:
    _require_candidate(user)
    rows = db.execute(
        select(Job, HRProfile.company_name)
        .join(CandidateSavedJob, CandidateSavedJob.job_id == Job.id)
        .outerjoin(HRProfile, HRProfile.user_id == Job.hr_user_id)
        .where(CandidateSavedJob.candidate_id == user.id, Job.status == JobStatus.published)
        .order_by(CandidateSavedJob.created_at.desc())
    ).all()
    out: list[JobOut] = []
    for job, company_name in rows:
        app_count = db.scalar(select(func.count()).select_from(JobApplication).where(JobApplication.job_id == job.id)) or 0
        out.append(
            JobOut(
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
        )
    return out


@router.get("/subscription", response_model=CandidateSubscriptionOut)
def my_subscription(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> CandidateSubscriptionOut:
    _require_candidate(user)
    sub = _ensure_subscription_row(db, user.id)
    _refresh_subscription_status(sub)
    db.commit()
    db.refresh(sub)
    runtime_cache.upsert_subscription(sub)
    is_active = _is_pro_active(sub)
    days_remaining = 0
    if sub.pro_expires_at and sub.pro_expires_at > datetime.utcnow():
        days_remaining = max(0, (sub.pro_expires_at - datetime.utcnow()).days)
    return CandidateSubscriptionOut(
        status=sub.status,
        pro_expires_at=sub.pro_expires_at,
        is_pro_active=is_active,
        tier="pro" if is_active else "basic",
        days_remaining=days_remaining,
    )


@router.post("/subscription/pro/upgrade", response_model=InvoiceOut)
def create_pro_upgrade_invoice(
    body: ProUpgradeIn,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Invoice:
    _require_candidate(user)
    pendings = db.scalars(
        select(Invoice).where(
            Invoice.owner_user_id == user.id,
            Invoice.invoice_type == InvoiceType.pro_upgrade,
            Invoice.status == InvoiceStatus.pending,
        )
    ).all()
    # Mỗi lần đăng ký/gia hạn cần order code mới: đóng invoice pending cũ trước khi tạo invoice mới.
    for old_invoice in pendings:
        old_invoice.status = InvoiceStatus.cancelled
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
        _apply_pro_upgrade_from_invoice(db, invoice)
    db.commit()
    db.refresh(invoice)
    return invoice


@router.post("/subscription/sepay/webhook")
def sepay_webhook_callback(
    payload: dict,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    x_sepay_secret: str | None = Header(default=None, alias="X-Sepay-Secret"),
    authorization: str | None = Header(default=None, alias="Authorization"),
    token: str | None = None,
) -> dict:
    configured_secret = (settings.sepay_webhook_secret or "").strip()
    fallback_secret_key = (settings.sepay_secret_key or "").strip()

    def _extract_auth_secret(auth_header: str | None) -> str | None:
        if not auth_header:
            return None
        raw = auth_header.strip()
        if not raw:
            return None
        low = raw.lower()
        if low.startswith("bearer "):
            return raw[7:].strip() or None
        if low.startswith("basic "):
            b64 = raw[6:].strip()
            try:
                decoded = base64.b64decode(b64).decode("utf-8", errors="ignore")
            except Exception:
                return None
            if ":" in decoded:
                return decoded.split(":", 1)[1].strip() or None
            return decoded.strip() or None
        return None

    # Tạm thời bỏ bắt buộc auth secret để test end-to-end webhook từ SePay.
    accepted_secrets: list[str] = []
    def _mask(value: str | None) -> str:
        if not value:
            return ""
        if len(value) <= 8:
            return "*" * len(value)
        return f"{value[:4]}...{value[-4:]}"

    auth_secret = _extract_auth_secret(authorization)
    log.warning(
        "SePay webhook auth debug ip=%s ua=%s x_sepay_secret=%s token=%s authorization=%s extracted_auth_secret=%s headers=%s",
        request.client.host if request.client else "",
        request.headers.get("user-agent", ""),
        _mask((x_sepay_secret or "").strip()),
        _mask((token or "").strip()),
        (authorization or "")[:40],
        _mask((auth_secret or "").strip()),
        {
            "x-sepay-secret": request.headers.get("x-sepay-secret", ""),
            "authorization": request.headers.get("authorization", "")[:40],
            "x-forwarded-for": request.headers.get("x-forwarded-for", ""),
            "cf-connecting-ip": request.headers.get("cf-connecting-ip", ""),
        },
    )

    if accepted_secrets:
        provided_secret = (
            (x_sepay_secret or "").strip()
            or (token or "").strip()
            or (auth_secret or "").strip()
        )
        if not provided_secret or provided_secret not in accepted_secrets:
            raise HTTPException(status_code=401, detail="Invalid webhook secret")

    order_obj = payload.get("order") if isinstance(payload.get("order"), dict) else {}
    txn_obj = payload.get("transaction") if isinstance(payload.get("transaction"), dict) else {}
    order_code = str(
        payload.get("order_code")
        or payload.get("sepay_order_code")
        or order_obj.get("order_invoice_number")
        or order_obj.get("order_id")
        or ""
    ).strip()
    status_text = str(
        payload.get("status")
        or payload.get("transaction_status")
        or payload.get("notification_type")
        or order_obj.get("order_status")
        or txn_obj.get("transaction_status")
        or ""
    ).strip().lower()
    if not order_code:
        raise HTTPException(status_code=400, detail="Missing order_code")

    invoice = db.scalar(select(Invoice).where(Invoice.sepay_order_code == order_code))
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    if status_text and status_text not in {
        "paid",
        "success",
        "completed",
        "done",
        "approved",
        "captured",
        "order_paid",
    }:
        return {"ok": True, "accepted": False, "reason": f"status={status_text}"}

    if invoice.status != InvoiceStatus.paid:
        invoice.mark_paid()
        if invoice.invoice_type == InvoiceType.pro_upgrade:
            _apply_pro_upgrade_from_invoice(db, invoice)
        db.commit()
    return {"ok": True, "accepted": True, "invoice_id": invoice.id}


@router.get("/subscription/sepay/checkout/{order_code}", response_class=HTMLResponse)
def sepay_checkout_redirect_page(
    order_code: str,
    db: Annotated[Session, Depends(get_db)],
) -> HTMLResponse:
    invoice = db.scalar(select(Invoice).where(Invoice.sepay_order_code == order_code))
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    fields = build_sepay_checkout_fields(
        order_code=invoice.sepay_order_code,
        amount_vnd=int(float(invoice.amount)),
        note=str(invoice.note or "Payment"),
        owner_user_id=invoice.owner_user_id,
    )
    inputs = "\n".join(
        f'<input type="hidden" name="{k}" value="{v}"/>'
        for k, v in fields.items()
    )
    html = f"""<!doctype html>
<html>
<head><meta charset="utf-8"><title>Redirecting to SePay</title></head>
<body>
  <p>Dang chuyen den SePay...</p>
  <form id="sepay_checkout_form" method="POST" action="{settings.sepay_checkout_base_url}">
    {inputs}
  </form>
  <script>
    document.getElementById('sepay_checkout_form').submit();
  </script>
</body>
</html>"""
    return HTMLResponse(content=html)


@router.get("/subscription/payments", response_model=list[CandidateSubscriptionPaymentOut])
def list_subscription_payments(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[CandidateSubscriptionPayment]:
    _require_candidate(user)
    rows = db.scalars(
        select(CandidateSubscriptionPayment)
        .where(CandidateSubscriptionPayment.candidate_id == user.id)
        .order_by(CandidateSubscriptionPayment.paid_at.desc(), CandidateSubscriptionPayment.id.desc())
    ).all()
    return list(rows)


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
