from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import settings
from ..db import get_db
from ..deps import get_current_user
from ..models import CVDocument, HRApprovalStatus, Job, JobApplication, JobStatus, User, UserRole
from ..schemas import JobCreate, JobOut, StatsOut
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
    views = total_jobs * 42 + total_apps * 3
    rate = min(100, int(50 + (total_apps / max(1, total_jobs))))
    monthly = db.execute(
        select(func.month(Job.created_at), func.count())
        .where(Job.hr_user_id == user.id)
        .group_by(func.month(Job.created_at))
        .order_by(func.month(Job.created_at))
    ).all()
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
    )


@router.post("/jobs", response_model=JobOut)
def create_job(
    body: JobCreate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Job:
    _require_approved_hr(user)
    st = JobStatus.draft if body.as_draft else JobStatus.pending_approval
    job = Job(
        hr_user_id=user.id,
        title=body.title,
        description=body.description,
        salary_text=body.salary_text,
        location=body.location,
        job_type=body.job_type,
        status=st,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


@router.get("/jobs", response_model=list[JobOut])
def my_jobs(user: Annotated[User, Depends(get_current_user)], db: Annotated[Session, Depends(get_db)]) -> list[JobOut]:
    _require_hr(user)
    rows = db.scalars(select(Job).where(Job.hr_user_id == user.id).order_by(Job.id.desc())).all()
    return list(rows)


@router.get("/jobs/{job_id}", response_model=JobOut)
def get_job_detail(
    job_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Job:
    _require_hr(user)
    job = db.get(Job, job_id)
    if not job or job.hr_user_id != user.id:
        raise HTTPException(status_code=404, detail="Not found")
    return job


@router.put("/jobs/{job_id}", response_model=JobOut)
def update_job(
    job_id: int,
    body: JobCreate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Job:
    _require_approved_hr(user)
    job = db.get(Job, job_id)
    if not job or job.hr_user_id != user.id:
        raise HTTPException(status_code=404, detail="Not found")
    job.title = body.title
    job.description = body.description
    job.salary_text = body.salary_text
    job.location = body.location
    job.job_type = body.job_type
    if job.status in (JobStatus.draft, JobStatus.rejected):
        job.status = JobStatus.draft if body.as_draft else JobStatus.pending_approval
    db.commit()
    db.refresh(job)
    return job


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
    return {"ok": True}


@router.put("/jobs/{job_id}/submit", response_model=JobOut)
def submit_job(
    job_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Job:
    _require_approved_hr(user)
    job = db.get(Job, job_id)
    if not job or job.hr_user_id != user.id:
        raise HTTPException(status_code=404, detail="Not found")
    if job.status == JobStatus.published:
        raise HTTPException(status_code=400, detail="Already published")
    job.status = JobStatus.pending_approval
    db.commit()
    db.refresh(job)
    return job


@router.get("/applications", response_model=list[dict])
def list_applications_for_hr(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[dict]:
    _require_hr(user)
    q = (
        select(JobApplication, Job, User)
        .join(Job, Job.id == JobApplication.job_id)
        .join(User, User.id == JobApplication.candidate_id)
        .where(Job.hr_user_id == user.id)
        .order_by(JobApplication.id.desc())
        .limit(500)
    )
    rows = db.execute(q).all()
    out: list[dict] = []
    for app, job, cand in rows:
        cv = db.get(CVDocument, app.cv_id) if app.cv_id else None
        out.append(
            {
                "application_id": app.id,
                "job_title": job.title,
                "candidate_name": cand.full_name or cand.email,
                "candidate_email": cand.email,
                "status": app.status.value,
                "cv_id": app.cv_id,
                "cv_name": cv.original_name if cv else None,
                "created_at": app.created_at.isoformat(),
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
