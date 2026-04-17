
from __future__ import annotations

# ─── MOCK USERS (Candidate) ─────────────────────────────────────────────
MOCK_USERS: list[dict] = [
    {
        "id": 1,
        "full_name": "Nguyễn Văn An",
        "email": "an.nguyen@email.com",
        "phone": "0901234567",
        "created_at": "15/03/2026",
        "applications_count": 5,
        "is_active": True,
        "role": "candidate",
    },
    {
        "id": 2,
        "full_name": "Trần Thị Bình",
        "email": "binh.tran@email.com",
        "phone": "0902345678",
        "created_at": "20/03/2026",
        "applications_count": 3,
        "is_active": True,
        "role": "candidate",
    },
    {
        "id": 3,
        "full_name": "Lê Hoàng Cường",
        "email": "cuong.le@email.com",
        "phone": "0903456789",
        "created_at": "22/03/2026",
        "applications_count": 8,
        "is_active": True,
        "role": "candidate",
    },
    {
        "id": 4,
        "full_name": "Phạm Minh Đức",
        "email": "duc.pham@email.com",
        "phone": "0904567890",
        "created_at": "25/03/2026",
        "applications_count": 2,
        "is_active": False,
        "role": "candidate",
    },
    {
        "id": 5,
        "full_name": "Võ Thị Em",
        "email": "em.vo@email.com",
        "phone": "0905678901",
        "created_at": "01/04/2026",
        "applications_count": 4,
        "is_active": True,
        "role": "candidate",
    },
]

# ─── MOCK HR ─────────────────────────────────────────────────────────────
MOCK_HR_LIST: list[dict] = [
    {
        "id": 1,
        "company_name": "TechCorp Vietnam",
        "email": "hr@techcorp.vn",
        "phone": "0241234567",
        "created_at": "10/02/2026",
        "jobs_count": 12,
        "is_active": True,
    },
    {
        "id": 2,
        "company_name": "StartUp Innovation",
        "email": "recruit@startup.vn",
        "phone": "0282345678",
        "created_at": "15/02/2026",
        "jobs_count": 8,
        "is_active": True,
    },
    {
        "id": 3,
        "company_name": "Design Studio",
        "email": "jobs@designstudio.vn",
        "phone": "0236789012",
        "created_at": "20/02/2026",
        "jobs_count": 5,
        "is_active": True,
    },
    {
        "id": 4,
        "company_name": "Digital Agency",
        "email": "hr@digital.vn",
        "phone": "0243456789",
        "created_at": "25/02/2026",
        "jobs_count": 3,
        "is_active": False,
    },
    {
        "id": 5,
        "company_name": "Cloud Solutions",
        "email": "recruit@cloud.vn",
        "phone": "0285678901",
        "created_at": "01/03/2026",
        "jobs_count": 9,
        "is_active": True,
    },
]

# ─── MOCK JOBS (Admin view) ─────────────────────────────────────────────
MOCK_ADMIN_JOBS: list[dict] = [
    {
        "id": 1,
        "title": "Senior Frontend Developer",
        "company_name": "TechCorp Vietnam",
        "location": "Hà Nội",
        "salary_text": "2000 - 3000 USD",
        "job_type": "Full-time",
        "applicants_count": 23,
        "created_at": "10/04/2026",
        "status": "published",
    },
    {
        "id": 2,
        "title": "Backend Developer (Node.js)",
        "company_name": "StartUp Innovation",
        "location": "Hồ Chí Minh",
        "salary_text": "1500 - 2500 USD",
        "job_type": "Full-time",
        "applicants_count": 18,
        "created_at": "08/04/2026",
        "status": "published",
    },
    {
        "id": 3,
        "title": "UI/UX Designer",
        "company_name": "Design Studio",
        "location": "Đà Nẵng",
        "salary_text": "1000 - 1800 USD",
        "job_type": "Remote",
        "applicants_count": 31,
        "created_at": "05/04/2026",
        "status": "published",
    },
    {
        "id": 4,
        "title": "Full Stack Developer",
        "company_name": "Digital Agency",
        "location": "Hà Nội",
        "salary_text": "2500 - 3500 USD",
        "job_type": "Full-time",
        "applicants_count": 15,
        "created_at": "03/04/2026",
        "status": "rejected",
    },
    {
        "id": 5,
        "title": "DevOps Engineer",
        "company_name": "Cloud Solutions",
        "location": "Hồ Chí Minh",
        "salary_text": "2200 - 3200 USD",
        "job_type": "Full-time",
        "applicants_count": 9,
        "created_at": "01/04/2026",
        "status": "draft",
    },
]

# ─── MOCK: Danh sách job công khai (cho Candidate Dashboard) ─────────────
MOCK_JOBS: list[dict] = [
    {
        "id": 101,
        "title": "Lập trình viên Python (Backend)",
        "description": "Phát triển API FastAPI, tích hợp PostgreSQL, viết test tự động. "
        "Môi trường làm việc linh hoạt, đào tạo nội bộ.",
        "company_name": "TechViet Solutions",
        "location": "Hà Nội (hybrid)",
        "job_type": "Full-time",
        "salary_text": "18–28 triệu",
    },
    {
        "id": 102,
        "title": "Frontend React / TypeScript",
        "description": "Xây dựng giao diện web hiện đại, làm việc với design system và CI/CD.",
        "company_name": "Bright Apps",
        "location": "TP.HCM",
        "job_type": "Full-time",
        "salary_text": "20–35 triệu",
    },
    {
        "id": 103,
        "title": "Thực tập sinh Data Analyst",
        "description": "Phân tích dữ liệu kinh doanh, SQL, báo cáo dashboard cho ban lãnh đạo.",
        "company_name": "Retail Analytics Co.",
        "location": "Đà Nẵng",
        "job_type": "Internship",
        "salary_text": "5 triệu + phụ cấp",
    },
    {
        "id": 104,
        "title": "DevOps Engineer",
        "description": "Kubernetes, Docker, pipeline GitHub Actions, giám sát hạ tầng cloud.",
        "company_name": "CloudScale VN",
        "location": "Remote",
        "job_type": "Full-time",
        "salary_text": "25–40 triệu",
    },
]

MOCK_CVS: list[dict] = [
    {"id": 1, "original_name": "CV_NguyenVanA.pdf"},
    {"id": 2, "original_name": "Portfolio_EN.docx"},
]

MOCK_HR_DASHBOARD: dict = {
    "cards": {"jobs": 12, "candidates": 48, "views": 3200, "response_rate": 42},
    "labels": ["Tuần 1", "Tuần 2", "Tuần 3", "Tuần 4"],
    "values": [18, 24, 31, 27],
}

MOCK_HR_JOBS: list[dict] = [
    {"id": 501, "title": "Senior Backend Engineer", "status": "published"},
    {"id": 502, "title": "Product Designer (UI/UX)", "status": "draft"},
]

MOCK_HR_APPLICATIONS: list[dict] = [
    {
        "application_id": 9001,
        "candidate_name": "Trần Thị B",
        "candidate_email": "b.tran@email.com",
        "job_title": "Senior Backend Engineer",
        "status": "pending",
        "cv_name": "TranThiB_CV.pdf",
    },
    {
        "application_id": 9002,
        "candidate_name": "Lê Văn C",
        "candidate_email": "c.le@email.com",
        "job_title": "Product Designer (UI/UX)",
        "status": "reviewed",
        "cv_name": "LeVanC_Portfolio.pdf",
    },
]

MOCK_ADMIN_DASHBOARD: dict = {
    "cards": {"users": 1240, "hr": 86, "jobs": 320, "activity_today": 45},
    "labels": ["T2", "T3", "T4", "T5", "T6", "T7", "CN"],
    "values": [12, 19, 15, 22, 18, 8, 5],
}

MOCK_ADMIN_USERS: list[dict] = [
    {"id": 1, "email": "admin@jobhub.local", "role": "admin"},
    {"id": 2, "email": "hr@demo.local", "role": "hr"},
    {"id": 3, "email": "user@demo.local", "role": "candidate"},
]

MOCK_PENDING_HR: list[dict] = [
    {"id": 10, "email": "pending.hr@company.com"},
]

MOCK_PENDING_JOBS: list[dict] = [
    {"id": 701, "title": "Marketing Executive — chờ duyệt"},
]
