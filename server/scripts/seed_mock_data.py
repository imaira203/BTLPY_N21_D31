import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import SessionLocal, engine
from app.models import (
    Base, User, UserRole, HRProfile, HRApprovalStatus, 
    Job, JobStatus, CVDocument, JobApplication, ApplicationStatus
)
from app.security import hash_password

def run() -> None:
    Base.metadata.create_all(bind=engine)
    db: Session = SessionLocal()
    
    try:
        print("Đang tạo dữ liệu mẫu...")
        
        # 1. Admin
        admin_email = "admin@jobhub.local"
        admin = db.scalar(select(User).where(User.email == admin_email))
        if not admin:
            admin = User(
                email=admin_email,
                password_hash=hash_password("admin123"),
                full_name="Administrator",
                role=UserRole.admin,
            )
            db.add(admin)
            db.commit()
            print(f"Created admin: {admin_email}")

        # 2. Candidate
        cand_email = "user@demo.local"
        candidate = db.scalar(select(User).where(User.email == cand_email))
        if not candidate:
            candidate = User(
                email=cand_email,
                password_hash=hash_password("user123"),
                full_name="Ứng viên Demo",
                role=UserRole.candidate,
            )
            db.add(candidate)
            db.commit()
            print(f"Created candidate: {cand_email}")

        # 3. HR 1 (Approved)
        hr1_email = "hr@demo.local"
        hr1 = db.scalar(select(User).where(User.email == hr1_email))
        if not hr1:
            hr1 = User(
                email=hr1_email,
                password_hash=hash_password("hr123"),
                full_name="Nhà tuyển dụng 1",
                role=UserRole.hr,
            )
            db.add(hr1)
            db.flush()
            
            hr1_profile = HRProfile(
                user_id=hr1.id,
                company_name="TechViet Solutions",
                contact_phone="0123456789",
                company_description="Công ty công nghệ hàng đầu.",
                approval_status=HRApprovalStatus.approved
            )
            db.add(hr1_profile)
            db.commit()
            print(f"Created HR: {hr1_email}")

        # 4. HR 2 (Pending)
        hr2_email = "pending.hr@company.com"
        hr2 = db.scalar(select(User).where(User.email == hr2_email))
        if not hr2:
            hr2 = User(
                email=hr2_email,
                password_hash=hash_password("hr123"),
                full_name="HR Chờ duyệt",
                role=UserRole.hr,
            )
            db.add(hr2)
            db.flush()
            
            hr2_profile = HRProfile(
                user_id=hr2.id,
                company_name="Pending Corp",
                contact_phone="0987654321",
                approval_status=HRApprovalStatus.pending
            )
            db.add(hr2_profile)
            db.commit()
            print(f"Created Pending HR: {hr2_email}")

        # 5. Jobs
        if db.scalar(select(Job).where(Job.title == "Lập trình viên Python (Backend)")) is None:
            jobs_data = [
                {
                    "title": "Lập trình viên Python (Backend)",
                    "description": "Phát triển API FastAPI, tích hợp PostgreSQL, viết test tự động. Môi trường làm việc linh hoạt, đào tạo nội bộ.",
                    "salary_text": "18–28 triệu",
                    "location": "Hà Nội (hybrid)",
                    "job_type": "Full-time",
                    "status": JobStatus.published,
                    "hr_user_id": hr1.id
                },
                {
                    "title": "Frontend React / TypeScript",
                    "description": "Xây dựng giao diện web hiện đại, làm việc với design system và CI/CD.",
                    "salary_text": "20–35 triệu",
                    "location": "TP.HCM",
                    "job_type": "Full-time",
                    "status": JobStatus.published,
                    "hr_user_id": hr1.id
                },
                {
                    "title": "Thực tập sinh Data Analyst",
                    "description": "Phân tích dữ liệu kinh doanh, SQL, báo cáo dashboard cho ban lãnh đạo.",
                    "salary_text": "5 triệu + phụ cấp",
                    "location": "Đà Nẵng",
                    "job_type": "Internship",
                    "status": JobStatus.published,
                    "hr_user_id": hr1.id
                },
                {
                    "title": "DevOps Engineer",
                    "description": "Kubernetes, Docker, pipeline GitHub Actions, giám sát hạ tầng cloud.",
                    "salary_text": "25–40 triệu",
                    "location": "Remote",
                    "job_type": "Full-time",
                    "status": JobStatus.published,
                    "hr_user_id": hr1.id
                },
                {
                    "title": "Product Designer (UI/UX)",
                    "description": "Thiết kế UI/UX cho các sản phẩm mới.",
                    "salary_text": "15-25 triệu",
                    "location": "Hà Nội",
                    "job_type": "Full-time",
                    "status": JobStatus.draft,
                    "hr_user_id": hr1.id
                },
                {
                    "title": "Marketing Executive — chờ duyệt",
                    "description": "Lên kế hoạch marketing",
                    "salary_text": "10-15 triệu",
                    "location": "Hà Nội",
                    "job_type": "Full-time",
                    "status": JobStatus.pending_approval,
                    "hr_user_id": hr1.id
                }
            ]
            
            db.bulk_insert_mappings(Job, jobs_data)
            db.commit()
            print("Created Jobs.")

        print("Đã tạo dữ liệu mẫu thành công!")
        
    finally:
        db.close()

if __name__ == "__main__":
    run()
