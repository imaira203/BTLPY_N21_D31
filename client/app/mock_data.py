
from __future__ import annotations

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
