
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

MOCK_HR_ACTIVITY: list[dict] = [
    {
        "type": "apply",
        "dot_color": "#6366f1",
        "text": "Nguyễn Văn A ứng tuyển cho Senior Backend Engineer",
        "time": "30 phút trước",
        "group": "today",
        "bold": True,
        "action_label": "Xem hồ sơ",
        "action_page": 3,
    },
    {
        "type": "apply",
        "dot_color": "#6366f1",
        "text": "Trần Thị Bình ứng tuyển cho Product Designer",
        "time": "1 giờ trước",
        "group": "today",
        "bold": True,
        "action_label": "Xem hồ sơ",
        "action_page": 3,
    },
    {
        "type": "interview",
        "dot_color": "#0ea5e9",
        "text": "Lịch phỏng vấn với Lê Hoàng Cường lúc 14:00",
        "time": "10:00 sáng nay",
        "group": "today",
        "bold": False,
        "action_label": "Xem lịch",
        "action_page": 3,
    },
    {
        "type": "approved",
        "dot_color": "#10b981",
        "text": "Tin đăng 'Senior Backend Engineer' được duyệt",
        "time": "Hôm qua 17:30",
        "group": "yesterday",
        "bold": False,
        "action_label": "Xem tin",
        "action_page": 2,
    },
    {
        "type": "view",
        "dot_color": "#94a3b8",
        "text": "Phạm Minh Đức đã xem tin tuyển dụng DevOps",
        "time": "Hôm qua 15:20",
        "group": "yesterday",
        "bold": False,
        "action_label": "Chi tiết",
        "action_page": 2,
    },
    {
        "type": "update",
        "dot_color": "#f59e0b",
        "text": "Hồ sơ của Võ Thị Em đã được cập nhật kỹ năng",
        "time": "Hôm qua 09:00",
        "group": "yesterday",
        "bold": False,
        "action_label": "Xem hồ sơ",
        "action_page": 3,
    },
    {
        "type": "apply",
        "dot_color": "#6366f1",
        "text": "Hoàng Anh Tuấn ứng tuyển cho Data Analyst",
        "time": "T2, 09/04",
        "group": "week",
        "bold": False,
        "action_label": "Xem hồ sơ",
        "action_page": 3,
    },
    {
        "type": "approved",
        "dot_color": "#10b981",
        "text": "Tin đăng 'UX Researcher' được phê duyệt đăng",
        "time": "T3, 08/04",
        "group": "week",
        "bold": False,
        "action_label": "Xem tin",
        "action_page": 2,
    },
]

# ── Chart data for different time periods ──────────────────────────────────
MOCK_HR_CHART_DATA: dict = {
    "week": {
        "labels": ["T2", "T3", "T4", "T5", "T6", "T7", "CN"],
        "values": [18, 24, 31, 27, 35, 22, 14],
    },
    "month": {
        "labels": ["Tuần 1", "Tuần 2", "Tuần 3", "Tuần 4"],
        "values": [68, 85, 97, 74],
    },
    "quarter": {
        "labels": ["Tháng 1", "Tháng 2", "Tháng 3"],
        "values": [210, 265, 240],
    },
}

MOCK_HR_JOBS: list[dict] = [
    {
        "id": 501,
        "title": "Senior Backend Engineer",
        "department": "Kỹ thuật & Công nghệ",
        "created_at": "15/10/2023",
        "applicants_count": 24,
        "status": "published",
    },
    {
        "id": 502,
        "title": "Product Designer (UI/UX)",
        "department": "Thiết kế",
        "created_at": "14/10/2023",
        "applicants_count": 18,
        "status": "draft",
    },
    {
        "id": 503,
        "title": "Marketing Manager",
        "department": "Marketing",
        "created_at": "10/10/2023",
        "applicants_count": 0,
        "status": "published",
    },
    {
        "id": 504,
        "title": "Content Writer",
        "department": "Marketing",
        "created_at": "05/10/2023",
        "applicants_count": 32,
        "status": "closed",
    },
    {
        "id": 505,
        "title": "Data Analyst",
        "department": "Kinh doanh",
        "created_at": "28/09/2023",
        "applicants_count": 11,
        "status": "published",
    },
    {
        "id": 506,
        "title": "DevOps Engineer",
        "department": "Kỹ thuật & Công nghệ",
        "created_at": "20/09/2023",
        "applicants_count": 7,
        "status": "pending_approval",
    },
    {
        "id": 507,
        "title": "UX Researcher",
        "department": "Thiết kế",
        "created_at": "15/09/2023",
        "applicants_count": 14,
        "status": "published",
    },
    {
        "id": 508,
        "title": "Backend Engineer (Python)",
        "department": "Kỹ thuật & Công nghệ",
        "created_at": "10/09/2023",
        "applicants_count": 22,
        "status": "draft",
    },
    {
        "id": 509,
        "title": "Sales Manager",
        "department": "Kinh doanh",
        "created_at": "05/09/2023",
        "applicants_count": 0,
        "status": "pending_approval",
    },
]

MOCK_HR_APPLICATIONS: list[dict] = [
    {
        "application_id": 9001,
        "candidate_name": "Trần Thị Bình",
        "candidate_email": "binh.tran@email.com",
        "job_title": "Senior Backend Engineer",
        "status": "pending",
        "cv_name": "TranThiB_CV.pdf",
        "applied_at": "15/04/2026",
    },
    {
        "application_id": 9002,
        "candidate_name": "Lê Văn Cường",
        "candidate_email": "cuong.le@email.com",
        "job_title": "Product Designer (UI/UX)",
        "status": "reviewed",
        "cv_name": "LeVanC_Portfolio.pdf",
        "applied_at": "14/04/2026",
    },
    {
        "application_id": 9003,
        "candidate_name": "Nguyễn Văn An",
        "candidate_email": "an.nguyen@email.com",
        "job_title": "Data Analyst",
        "status": "approved",
        "cv_name": "NguyenVanA_CV.pdf",
        "applied_at": "13/04/2026",
    },
    {
        "application_id": 9004,
        "candidate_name": "Phạm Minh Đức",
        "candidate_email": "duc.pham@email.com",
        "job_title": "DevOps Engineer",
        "status": "rejected",
        "cv_name": "PhamMinhD_CV.pdf",
        "applied_at": "12/04/2026",
    },
    {
        "application_id": 9005,
        "candidate_name": "Võ Thị Em",
        "candidate_email": "em.vo@email.com",
        "job_title": "Marketing Manager",
        "status": "pending",
        "cv_name": "VoThiE_Resume.pdf",
        "applied_at": "11/04/2026",
    },
    {
        "application_id": 9006,
        "candidate_name": "Hoàng Anh Tuấn",
        "candidate_email": "tuan.hoang@email.com",
        "job_title": "Senior Backend Engineer",
        "status": "reviewed",
        "cv_name": "HoangAnhT_CV.pdf",
        "applied_at": "10/04/2026",
    },
    {
        "application_id": 9007,
        "candidate_name": "Đặng Thị Lan",
        "candidate_email": "lan.dang@email.com",
        "job_title": "Content Writer",
        "status": "approved",
        "cv_name": "DangThiL_Portfolio.pdf",
        "applied_at": "09/04/2026",
    },
    {
        "application_id": 9008,
        "candidate_name": "Trần Văn Hùng",
        "candidate_email": "hung.tran@email.com",
        "job_title": "Senior Backend Engineer",
        "status": "pending",
        "cv_name": "TranVanH_CV.pdf",
        "applied_at": "08/04/2026",
    },
    {
        "application_id": 9009,
        "candidate_name": "Nguyễn Thị Mai",
        "candidate_email": "mai.nguyen@email.com",
        "job_title": "Product Designer (UI/UX)",
        "status": "approved",
        "cv_name": "NguyenThiM_CV.pdf",
        "applied_at": "07/04/2026",
    },
    {
        "application_id": 9010,
        "candidate_name": "Lê Quốc Bảo",
        "candidate_email": "bao.le@email.com",
        "job_title": "Data Analyst",
        "status": "reviewed",
        "cv_name": "LeQuocB_CV.pdf",
        "applied_at": "06/04/2026",
    },
    {
        "application_id": 9011,
        "candidate_name": "Phùng Thị Hoa",
        "candidate_email": "hoa.phung@email.com",
        "job_title": "Marketing Manager",
        "status": "rejected",
        "cv_name": "PhungThiH_CV.pdf",
        "applied_at": "05/04/2026",
    },
    {
        "application_id": 9012,
        "candidate_name": "Bùi Minh Khoa",
        "candidate_email": "khoa.bui@email.com",
        "job_title": "DevOps Engineer",
        "status": "pending",
        "cv_name": "BuiMinhK_CV.pdf",
        "applied_at": "04/04/2026",
    },
    {
        "application_id": 9013,
        "candidate_name": "Vũ Thị Ngọc",
        "candidate_email": "ngoc.vu@email.com",
        "job_title": "Content Writer",
        "status": "reviewed",
        "cv_name": "VuThiN_CV.pdf",
        "applied_at": "03/04/2026",
    },
    {
        "application_id": 9014,
        "candidate_name": "Đinh Công Sơn",
        "candidate_email": "son.dinh@email.com",
        "job_title": "Senior Backend Engineer",
        "status": "approved",
        "cv_name": "DinhCongS_CV.pdf",
        "applied_at": "02/04/2026",
    },
    {
        "application_id": 9015,
        "candidate_name": "Cao Thị Yến",
        "candidate_email": "yen.cao@email.com",
        "job_title": "Data Analyst",
        "status": "pending",
        "cv_name": "CaoThiY_CV.pdf",
        "applied_at": "01/04/2026",
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

# ── Shared Job Store (runtime, mutable) ───────────────────────────────────
# HR đăng → status "draft" hoặc "pending_approval"
# Admin duyệt → "published"; Admin từ chối → "rejected"
# User chỉ thấy job status="published"

JOB_STORE: list[dict] = [
    {
        "id": 501, "title": "Senior Backend Engineer",
        "company_name": "TechCorp Vietnam",
        "department": "Kỹ thuật & Công nghệ",
        "location": "Hà Nội",
        "salary_text": "2000 - 3000 USD",
        "job_type": "Toàn thời gian",
        "level": "Trưởng nhóm",
        "count": "2",
        "deadline": "31/05/2026",
        "description": "Phát triển và duy trì hệ thống backend hiệu suất cao.",
        "applicants_count": 24, "created_at": "15/10/2023",
        "status": "published", "hr_id": 1,
    },
    {
        "id": 502, "title": "Product Designer (UI/UX)",
        "company_name": "Design Studio",
        "department": "Thiết kế",
        "location": "Đà Nẵng",
        "salary_text": "1000 - 1800 USD",
        "job_type": "Remote",
        "level": "Nhân viên",
        "count": "1",
        "deadline": "30/05/2026",
        "description": "Thiết kế trải nghiệm người dùng cho sản phẩm số.",
        "applicants_count": 18, "created_at": "14/10/2023",
        "status": "draft", "hr_id": 3,
    },
    {
        "id": 503, "title": "Marketing Manager",
        "company_name": "StartUp Innovation",
        "department": "Marketing",
        "location": "TP. Hồ Chí Minh",
        "salary_text": "1500 - 2500 USD",
        "job_type": "Toàn thời gian",
        "level": "Quản lý",
        "count": "1",
        "deadline": "15/05/2026",
        "description": "Lên chiến lược và thực thi các chiến dịch marketing.",
        "applicants_count": 0, "created_at": "10/10/2023",
        "status": "published", "hr_id": 2,
    },
    {
        "id": 504, "title": "Content Writer",
        "company_name": "Digital Agency",
        "department": "Marketing",
        "location": "Hà Nội",
        "salary_text": "800 - 1200 USD",
        "job_type": "Bán thời gian",
        "level": "Nhân viên",
        "count": "3",
        "deadline": "01/05/2026",
        "description": "Viết nội dung sáng tạo cho blog, mạng xã hội và website.",
        "applicants_count": 32, "created_at": "05/10/2023",
        "status": "closed", "hr_id": 4,
    },
    {
        "id": 505, "title": "Data Analyst",
        "company_name": "Cloud Solutions",
        "department": "Kinh doanh",
        "location": "TP. Hồ Chí Minh",
        "salary_text": "1800 - 2800 USD",
        "job_type": "Toàn thời gian",
        "level": "Nhân viên",
        "count": "2",
        "deadline": "20/05/2026",
        "description": "Phân tích dữ liệu kinh doanh, xây dựng báo cáo và dashboard.",
        "applicants_count": 11, "created_at": "28/09/2023",
        "status": "published", "hr_id": 5,
    },
    {
        "id": 506, "title": "DevOps Engineer",
        "company_name": "Cloud Solutions",
        "department": "Kỹ thuật & Công nghệ",
        "location": "Remote",
        "salary_text": "2200 - 3200 USD",
        "job_type": "Remote",
        "level": "Nhân viên",
        "count": "1",
        "deadline": "25/05/2026",
        "description": "Quản lý hạ tầng cloud, CI/CD pipeline và container orchestration.",
        "applicants_count": 7, "created_at": "20/09/2023",
        "status": "pending_approval", "hr_id": 5,
    },
    {
        "id": 507, "title": "UX Researcher",
        "company_name": "Design Studio",
        "department": "Thiết kế",
        "location": "Hà Nội",
        "salary_text": "1200 - 2000 USD",
        "job_type": "Toàn thời gian",
        "level": "Nhân viên",
        "count": "1",
        "deadline": "18/05/2026",
        "description": "Nghiên cứu người dùng, phân tích hành vi và đề xuất cải tiến UX.",
        "applicants_count": 14, "created_at": "15/09/2023",
        "status": "published", "hr_id": 3,
    },
    {
        "id": 508, "title": "Backend Engineer (Python)",
        "company_name": "TechCorp Vietnam",
        "department": "Kỹ thuật & Công nghệ",
        "location": "Hà Nội",
        "salary_text": "1500 - 2500 USD",
        "job_type": "Toàn thời gian",
        "level": "Nhân viên",
        "count": "2",
        "deadline": "30/05/2026",
        "description": "Xây dựng API RESTful với Python/FastAPI, tích hợp PostgreSQL.",
        "applicants_count": 22, "created_at": "10/09/2023",
        "status": "draft", "hr_id": 1,
    },
    {
        "id": 509, "title": "Sales Manager",
        "company_name": "StartUp Innovation",
        "department": "Kinh doanh",
        "location": "TP. Hồ Chí Minh",
        "salary_text": "2000 - 3500 USD",
        "job_type": "Toàn thời gian",
        "level": "Quản lý",
        "count": "1",
        "deadline": "10/05/2026",
        "description": "Quản lý đội ngũ bán hàng, phát triển chiến lược doanh thu.",
        "applicants_count": 0, "created_at": "05/09/2023",
        "status": "pending_approval", "hr_id": 2,
    },
    {
        "id": 510, "title": "Senior Frontend Developer",
        "company_name": "TechCorp Vietnam",
        "department": "Kỹ thuật & Công nghệ",
        "location": "Hà Nội",
        "salary_text": "2000 - 3000 USD",
        "job_type": "Toàn thời gian",
        "level": "Trưởng nhóm",
        "count": "1",
        "deadline": "28/05/2026",
        "description": "Xây dựng giao diện web hiện đại với React, TypeScript.",
        "applicants_count": 19, "created_at": "01/04/2026",
        "status": "published", "hr_id": 1,
    },
    {
        "id": 511, "title": "Full Stack Developer",
        "company_name": "Digital Agency",
        "department": "Kỹ thuật & Công nghệ",
        "location": "Đà Nẵng",
        "salary_text": "2500 - 4000 USD",
        "job_type": "Toàn thời gian",
        "level": "Nhân viên",
        "count": "2",
        "deadline": "05/06/2026",
        "description": "Phát triển cả frontend lẫn backend cho các sản phẩm web.",
        "applicants_count": 15, "created_at": "03/04/2026",
        "status": "published", "hr_id": 4,
    },
]
_next_job_id = [600]


def add_job(
    title: str,
    company_name: str,
    department: str,
    location: str,
    salary_text: str,
    job_type: str,
    level: str = "Nhân viên",
    count: str = "1",
    deadline: str = "",
    description: str = "",
    hr_id: int = 1,
    draft: bool = False,
) -> dict:
    """HR tạo tin mới. draft=True → status 'draft', False → 'pending_approval'."""
    from datetime import datetime
    job_id = _next_job_id[0]
    _next_job_id[0] += 1
    entry: dict = {
        "id":              job_id,
        "title":           title,
        "company_name":    company_name,
        "department":      department,
        "location":        location,
        "salary_text":     salary_text,
        "job_type":        job_type,
        "level":           level,
        "count":           count,
        "deadline":        deadline,
        "description":     description,
        "applicants_count": 0,
        "created_at":      datetime.now().strftime("%d/%m/%Y"),
        "status":          "draft" if draft else "pending_approval",
        "hr_id":           hr_id,
    }
    JOB_STORE.append(entry)
    return entry


def update_job_status(job_id: int, new_status: str) -> bool:
    """Admin duyệt/từ chối tin đăng. new_status: 'published' hoặc 'rejected'."""
    for job in JOB_STORE:
        if job.get("id") == job_id:
            job["status"] = new_status
            # ── Đồng bộ sang HR activity feed ─────────────────
            job_title = job.get("title", f"#{job_id}")
            if new_status == "published":
                add_hr_activity(
                    act_type="approved",
                    text=f"✅ Admin đã duyệt tin '{job_title}' — đang hiển thị công khai",
                    action_label="Xem tin",
                    action_page=2,
                    dot_color="#10b981",
                )
            elif new_status == "rejected":
                add_hr_activity(
                    act_type="update",
                    text=f"❌ Admin từ chối tin '{job_title}' — vui lòng kiểm tra lại",
                    action_label="Xem tin",
                    action_page=2,
                    dot_color="#ef4444",
                )
            return True
    return False


def delete_job(job_id: int) -> bool:
    """HR xoá tin đăng theo job_id."""
    for i, job in enumerate(JOB_STORE):
        if job.get("id") == job_id:
            JOB_STORE.pop(i)
            return True
    return False


def get_public_jobs() -> list[dict]:
    """Trả về danh sách tin đăng đang tuyển (status='published') cho ứng viên."""
    return [j for j in JOB_STORE if j.get("status") == "published"]


def get_pending_jobs() -> list[dict]:
    """Trả về tin đăng chờ admin duyệt."""
    return [j for j in JOB_STORE if j.get("status") == "pending_approval"]


def get_hr_jobs(hr_id: int | None = None) -> list[dict]:
    """Trả về tất cả tin của HR. hr_id=None → trả tất cả."""
    if hr_id is None:
        return list(JOB_STORE)
    return [j for j in JOB_STORE if j.get("hr_id") == hr_id]


# ── Shared candidate application store (runtime, mutable) ─────────────────
# Đây là nguồn chung giữa UserDashboard và HRDashboard.
# User apply → add_candidate_application()
# HR approve/reject → update_application_status()
# User polls → đọc status mới nhất để cập nhật lịch sử

CANDIDATE_APPLICATIONS: list[dict] = []
_next_app_id = [10_000]   # mutable counter (list trick)


# ── HR Activity Store (runtime) ──────────────────────────────────────────────
# Các hoạt động thực tế từ User (ứng tuyển) và Admin (duyệt/từ chối tin)
# được push vào đây để HR thấy ngay trên dashboard.

HR_ACTIVITY_STORE: list[dict] = []


def add_hr_activity(
    act_type: str,
    text: str,
    action_label: str = "Xem",
    action_page: int = 3,
    dot_color: str = "#6366f1",
) -> None:
    """Thêm hoạt động vào HR activity feed từ các role khác."""
    from datetime import datetime as _dt
    entry: dict = {
        "type":         act_type,
        "dot_color":    dot_color,
        "text":         text,
        "time":         _dt.now().strftime("%H:%M, %d/%m"),
        "group":        "today",
        "bold":         True,
        "action_label": action_label,
        "action_page":  action_page,
    }
    HR_ACTIVITY_STORE.insert(0, entry)   # mới nhất lên đầu


def add_candidate_application(
    title: str,
    company: str,
    location: str,
    applied_at: str,
    cv_name: str = "CV.pdf",
    candidate_name: str = "Ứng viên",
    candidate_email: str = "user@jobhub.vn",
    job_id: int = 0,
) -> dict:
    """Thêm đơn ứng tuyển mới vào shared store. Trả về entry dict."""
    app_id = _next_app_id[0]
    _next_app_id[0] += 1
    entry: dict = {
        "application_id": app_id,
        "job_id":          job_id,
        "candidate_name":  candidate_name,
        "candidate_email": candidate_email,
        "job_title":       title,
        "company_name":    company,
        "location":        location,
        "applied_at":      applied_at,
        "status":          "pending",
        "cv_name":         cv_name,
    }
    CANDIDATE_APPLICATIONS.append(entry)
    # ── Đồng bộ sang HR activity feed ─────────────────────────
    add_hr_activity(
        act_type="apply",
        text=f"{candidate_name} ứng tuyển cho {title} tại {company}",
        action_label="Xem hồ sơ",
        action_page=3,
        dot_color="#6366f1",
    )
    return entry


def update_application_status(app_id: int, new_status: str) -> bool:
    """Cập nhật trạng thái đơn trong CANDIDATE_APPLICATIONS hoặc MOCK_HR_APPLICATIONS."""
    for store in (CANDIDATE_APPLICATIONS, MOCK_HR_APPLICATIONS):
        for app in store:
            if app.get("application_id") == app_id:
                app["status"] = new_status
                # ── Đồng bộ sang HR activity feed ─────────────
                name  = app.get("candidate_name", "Ứng viên")
                title = app.get("job_title", "")
                if new_status == "approved":
                    add_hr_activity(
                        act_type="approved",
                        text=f"🎉 {name} được phê duyệt cho vị trí {title}",
                        action_label="Xem hồ sơ",
                        action_page=3,
                        dot_color="#10b981",
                    )
                elif new_status == "rejected":
                    add_hr_activity(
                        act_type="update",
                        text=f"Từ chối hồ sơ {name} — vị trí {title}",
                        action_label="Xem hồ sơ",
                        action_page=3,
                        dot_color="#ef4444",
                    )
                elif new_status == "reviewed":
                    add_hr_activity(
                        act_type="view",
                        text=f"Đã xem xét hồ sơ của {name} ({title})",
                        action_label="Xem hồ sơ",
                        action_page=3,
                        dot_color="#94a3b8",
                    )
                return True
    return False


def get_application_status(app_id: int) -> str | None:
    """Lấy trạng thái hiện tại của đơn theo app_id."""
    for store in (CANDIDATE_APPLICATIONS, MOCK_HR_APPLICATIONS):
        for app in store:
            if app.get("application_id") == app_id:
                return app.get("status")
    return None
