import uuid
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..db import get_db
from ..deps import get_current_user
from ..models import CVDocument, HRProfile, Job, JobApplication, JobStatus, User, UserRole
from ..schemas import ApplyIn, CVOut, JobOut
from ..storage_paths import absolute_path, relative_key

router = APIRouter(prefix="/candidate", tags=["candidate"])


def _require_candidate(user: User) -> None:
    if user.role != UserRole.candidate:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Candidate only")


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


@router.get("/jobs", response_model=list[JobOut])
def browse_jobs(db: Annotated[Session, Depends(get_db)]) -> list[JobOut]:
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
