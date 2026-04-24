from __future__ import annotations

import enum


class UserRole(str, enum.Enum):
    candidate = "candidate"
    hr = "hr"
    admin = "admin"


class HRApprovalStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class JobStatus(str, enum.Enum):
    draft = "draft"
    pending_approval = "pending_approval"
    published = "published"
    closed = "closed"
    rejected = "rejected"


class ApplicationStatus(str, enum.Enum):
    pending = "pending"
    reviewed = "reviewed"
    approved = "approved"
    rejected = "rejected"


class SubscriptionStatus(str, enum.Enum):
    inactive = "inactive"
    active = "active"
    expired = "expired"


class InvoiceType(str, enum.Enum):
    pro_upgrade = "pro_upgrade"
    candidate_contact_unlock = "candidate_contact_unlock"


class InvoiceStatus(str, enum.Enum):
    pending = "pending"
    paid = "paid"
    overdue = "overdue"
    cancelled = "cancelled"
