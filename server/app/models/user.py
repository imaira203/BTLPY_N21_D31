from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from sqlalchemy import Boolean, DateTime, Enum, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db import Base
from .enums import UserRole


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(String(255))
    avatar_storage_key: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    hr_profile: Mapped[Optional["HRProfile"]] = relationship(back_populates="user", uselist=False)
    candidate_profile: Mapped[Optional["CandidateProfile"]] = relationship(back_populates="user", uselist=False)
    candidate_subscription: Mapped[Optional["CandidateSubscription"]] = relationship(back_populates="candidate", uselist=False)
    saved_jobs: Mapped[List["CandidateSavedJob"]] = relationship(back_populates="candidate")
    cvs: Mapped[List["CVDocument"]] = relationship(back_populates="user")
    jobs: Mapped[List["Job"]] = relationship(back_populates="hr_user")
    applications: Mapped[List["JobApplication"]] = relationship(back_populates="candidate")
    invoices: Mapped[List["Invoice"]] = relationship(back_populates="owner")

    @property
    def display_name(self) -> str:
        return self.full_name or self.email

    def is_candidate(self) -> bool:
        return self.role == UserRole.candidate

    def is_hr(self) -> bool:
        return self.role == UserRole.hr

    def is_admin(self) -> bool:
        return self.role == UserRole.admin
