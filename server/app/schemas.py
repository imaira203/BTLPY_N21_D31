from datetime import datetime
from typing import Any

from pydantic import BaseModel, EmailStr, Field

from .models import ApplicationStatus, HRApprovalStatus, JobStatus, UserRole


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: int
    email: str
    full_name: str | None
    avatar_storage_key: str | None = None
    role: UserRole
    created_at: datetime

    model_config = {"from_attributes": True}


class RegisterCandidate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    full_name: str | None = None


class RegisterHR(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    full_name: str | None = None
    company_name: str = Field(min_length=1)
    contact_phone: str | None = None
    company_description: str | None = None


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class HRProfileOut(BaseModel):
    id: int
    company_name: str
    contact_phone: str | None
    company_description: str | None
    approval_status: HRApprovalStatus
    admin_note: str | None

    model_config = {"from_attributes": True}


class JobCreate(BaseModel):
    title: str = Field(min_length=1)
    description: str | None = None
    salary_text: str | None = None
    location: str | None = None
    job_type: str | None = None
    as_draft: bool = False


class JobOut(BaseModel):
    id: int
    hr_user_id: int
    title: str
    description: str | None
    salary_text: str | None
    location: str | None
    job_type: str | None
    status: JobStatus
    admin_note: str | None
    created_at: datetime
    company_name: str | None = None

    model_config = {"from_attributes": True}


class CVOut(BaseModel):
    id: int
    original_name: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ApplyIn(BaseModel):
    cv_id: int


class AdminDecision(BaseModel):
    note: str | None = None


class StatsOut(BaseModel):
    labels: list[str]
    values: list[int]
    cards: dict[str, Any]


class JobApplicationOut(BaseModel):
    id: int
    job_id: int
    candidate_id: int
    cv_id: int | None
    status: ApplicationStatus
    created_at: datetime

    model_config = {"from_attributes": True}
