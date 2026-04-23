from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db import Base
from .enums import JobStatus


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    hr_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    salary_text: Mapped[Optional[str]] = mapped_column(String(128))
    avg_salary: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String(128))
    job_type: Mapped[Optional[str]] = mapped_column(String(64))
    status: Mapped[JobStatus] = mapped_column(Enum(JobStatus), default=JobStatus.pending_approval)
    admin_note: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    hr_user: Mapped["User"] = relationship(back_populates="jobs", foreign_keys=[hr_user_id])
    applications: Mapped[List["JobApplication"]] = relationship(back_populates="job")
    saved_by_candidates: Mapped[List["CandidateSavedJob"]] = relationship(back_populates="job")

    def is_published(self) -> bool:
        return self.status == JobStatus.published

    def contact_unlock_fee(self) -> int:
        if not self.avg_salary or self.avg_salary <= 0:
            return 0
        return max(1000, int(self.avg_salary * 0.1))
