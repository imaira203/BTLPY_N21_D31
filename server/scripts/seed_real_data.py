import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import SessionLocal, engine
from app.models import (
    ApplicationStatus,
    Base,
    CVDocument,
    HRApprovalStatus,
    HRProfile,
    Job,
    JobApplication,
    JobStatus,
    User,
    UserRole,
)
from app.security import hash_password


def _ensure_user(db: Session, *, email: str, password: str, role: UserRole, full_name: str) -> User:
    existing = db.scalar(select(User).where(User.email == email))
    if existing:
        return existing
    user = User(
        email=email,
        password_hash=hash_password(password),
        full_name=full_name,
        role=role,
        is_active=True,
    )
    db.add(user)
    db.flush()
    return user


def run() -> None:
    Base.metadata.create_all(bind=engine)
    db: Session = SessionLocal()
    try:
        admin = _ensure_user(
            db, email="admin@jobhub.local", password="admin123", role=UserRole.admin, full_name="System Admin"
        )
        candidate_1 = _ensure_user(
            db, email="an.nguyen@email.com", password="user123", role=UserRole.candidate, full_name="Nguyen Van An"
        )
        candidate_2 = _ensure_user(
            db, email="binh.tran@email.com", password="user123", role=UserRole.candidate, full_name="Tran Thi Binh"
        )
        hr_user = _ensure_user(
            db, email="hr@techcorp.vn", password="hr123", role=UserRole.hr, full_name="HR TechCorp"
        )

        if not hr_user.hr_profile:
            db.add(
                HRProfile(
                    user_id=hr_user.id,
                    company_name="TechCorp Vietnam",
                    contact_phone="0241234567",
                    company_description="Tech company hiring engineers.",
                    approval_status=HRApprovalStatus.approved,
                )
            )

        jobs = db.scalars(select(Job).where(Job.hr_user_id == hr_user.id)).all()
        if not jobs:
            db.add_all(
                [
                    Job(
                        hr_user_id=hr_user.id,
                        title="Senior Frontend Developer",
                        description="React, TypeScript, modern UI systems.",
                        department="Kỹ thuật & Công nghệ",
                        level="Senior",
                        min_salary=20000000,
                        max_salary=30000000,
                        location="Ha Noi",
                        job_type="Full-time",
                        headcount=2,
                        deadline_text="31/12/2026",
                        status=JobStatus.published,
                    ),
                    Job(
                        hr_user_id=hr_user.id,
                        title="Backend Developer (Python)",
                        description="FastAPI, PostgreSQL, async processing.",
                        department="Kỹ thuật & Công nghệ",
                        level="Mid",
                        min_salary=18000000,
                        max_salary=28000000,
                        location="Ho Chi Minh",
                        job_type="Full-time",
                        headcount=1,
                        deadline_text="20/12/2026",
                        status=JobStatus.pending_approval,
                    ),
                    Job(
                        hr_user_id=hr_user.id,
                        title="UI/UX Designer",
                        description="Product design and user research.",
                        department="Thiết kế",
                        level="Junior",
                        min_salary=12000000,
                        max_salary=20000000,
                        location="Da Nang",
                        job_type="Hybrid",
                        headcount=1,
                        deadline_text="15/12/2026",
                        status=JobStatus.draft,
                    ),
                ]
            )
            db.flush()
            jobs = db.scalars(select(Job).where(Job.hr_user_id == hr_user.id)).all()

        cv_1 = db.scalar(select(CVDocument).where(CVDocument.user_id == candidate_1.id))
        if not cv_1:
            cv_1 = CVDocument(
                user_id=candidate_1.id,
                original_name="CV_NguyenVanAn.pdf",
                stored_filename=f"cvs/{candidate_1.id}_sample_cv.pdf",
                mime_type="application/pdf",
            )
            db.add(cv_1)
            db.flush()

        cv_2 = db.scalar(select(CVDocument).where(CVDocument.user_id == candidate_2.id))
        if not cv_2:
            cv_2 = CVDocument(
                user_id=candidate_2.id,
                original_name="CV_TranThiBinh.pdf",
                stored_filename=f"cvs/{candidate_2.id}_sample_cv.pdf",
                mime_type="application/pdf",
            )
            db.add(cv_2)
            db.flush()

        published_job = next((j for j in jobs if j.status == JobStatus.published), None)
        if published_job:
            exists_app_1 = db.scalar(
                select(JobApplication).where(
                    JobApplication.job_id == published_job.id,
                    JobApplication.candidate_id == candidate_1.id,
                )
            )
            if not exists_app_1:
                db.add(
                    JobApplication(
                        job_id=published_job.id,
                        candidate_id=candidate_1.id,
                        cv_id=cv_1.id if cv_1 else None,
                        status=ApplicationStatus.pending,
                    )
                )

            exists_app_2 = db.scalar(
                select(JobApplication).where(
                    JobApplication.job_id == published_job.id,
                    JobApplication.candidate_id == candidate_2.id,
                )
            )
            if not exists_app_2:
                db.add(
                    JobApplication(
                        job_id=published_job.id,
                        candidate_id=candidate_2.id,
                        cv_id=cv_2.id if cv_2 else None,
                        status=ApplicationStatus.reviewed,
                    )
                )

        db.commit()
        print("Seeded real data successfully.")
        print("Admin: admin@jobhub.local / admin123")
        print("HR: hr@techcorp.vn / hr123")
        print("Candidate: an.nguyen@email.com / user123")
    finally:
        db.close()


if __name__ == "__main__":
    run()

