from datetime import datetime
from typing import Any

from pydantic import BaseModel, EmailStr, Field

from .models import (
    ApplicationStatus,
    HRApprovalStatus,
    InvoiceStatus,
    InvoiceType,
    JobStatus,
    SubscriptionStatus,
    UserRole,
)


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


class UpdateEmailIn(BaseModel):
    new_email: EmailStr
    current_password: str = Field(min_length=1)


class UpdatePasswordIn(BaseModel):
    current_password: str = Field(min_length=1)
    new_password: str = Field(min_length=6)


class UpdateBasicProfileIn(BaseModel):
    full_name: str | None = Field(default=None, max_length=255)
    email: EmailStr | None = None


class HRProfileOut(BaseModel):
    id: int
    company_name: str
    avatar_storage_key: str | None = None
    contact_phone: str | None
    company_description: str | None
    approval_status: HRApprovalStatus
    admin_note: str | None

    model_config = {"from_attributes": True}


class HRProfileUpdateIn(BaseModel):
    company_name: str = Field(min_length=1, max_length=255)
    contact_phone: str | None = Field(default=None, max_length=64)
    company_description: str | None = None


class CandidateProfileUpdateIn(BaseModel):
    tagline: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=64)
    address: str | None = Field(default=None, max_length=255)
    professional_field: str | None = Field(default=None, max_length=255)
    degree: str | None = Field(default=None, max_length=255)
    experience_text: str | None = Field(default=None, max_length=255)
    language: str | None = Field(default=None, max_length=255)
    skills_json: dict[str, list[str]] | None = None


class CandidateProfileOut(BaseModel):
    id: int
    user_id: int
    tagline: str | None = None
    phone: str | None = None
    address: str | None = None
    professional_field: str | None = None
    degree: str | None = None
    experience_text: str | None = None
    language: str | None = None
    skills_json: dict[str, list[str]] = Field(default_factory=dict)
    updated_at: datetime

    model_config = {"from_attributes": True}


class JobCreate(BaseModel):
    title: str = Field(min_length=1)
    description: str | None = None
    department: str | None = None
    level: str | None = None
    min_salary: int | None = Field(default=None, ge=0)
    max_salary: int | None = Field(default=None, ge=0)
    location: str | None = None
    job_type: str | None = None
    count: int | None = Field(default=None, ge=1)
    deadline: str | None = None
    as_draft: bool = False


class JobOut(BaseModel):
    id: int
    hr_user_id: int
    title: str
    description: str | None
    department: str | None = None
    level: str | None = None
    salary_text: str | None = None
    min_salary: int | None = None
    max_salary: int | None = None
    location: str | None
    job_type: str | None
    count: int | None = None
    deadline: str | None = None
    applicants_count: int = 0
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
    cv_id: int | None = None


class AdminDecision(BaseModel):
    note: str | None = None


class ApplicationDecisionIn(BaseModel):
    status: ApplicationStatus


class StatsOut(BaseModel):
    labels: list[str]
    values: list[int]
    cards: dict[str, Any]
    recent_pending_applications: list[dict[str, Any]] = Field(default_factory=list)


class JobApplicationOut(BaseModel):
    id: int
    job_id: int
    candidate_id: int
    cv_id: int | None
    status: ApplicationStatus
    accepted_at: datetime | None
    contact_unlocked_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class CandidateApplicationHistoryOut(BaseModel):
    id: int
    job_id: int
    title: str
    company_name: str | None = None
    location: str | None = None
    status: ApplicationStatus
    applied_at: datetime


class CandidateSubscriptionOut(BaseModel):
    status: SubscriptionStatus
    pro_expires_at: datetime | None
    is_pro_active: bool = False
    tier: str = "basic"
    days_remaining: int = 0


class ProUpgradeIn(BaseModel):
    months: int = Field(default=1, ge=1, le=12)


class SavedJobOut(BaseModel):
    id: int
    candidate_id: int
    job_id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class InvoiceOut(BaseModel):
    id: int
    owner_user_id: int
    invoice_type: InvoiceType
    status: InvoiceStatus
    amount: float
    currency: str
    due_at: datetime
    sepay_order_code: str
    sepay_payment_url: str | None
    note: str | None
    created_at: datetime
    paid_at: datetime | None
    application_id: int | None

    model_config = {"from_attributes": True}
