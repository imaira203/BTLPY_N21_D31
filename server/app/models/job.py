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
    department: Mapped[Optional[str]] = mapped_column(String(128))
    level: Mapped[Optional[str]] = mapped_column(String(64))
    min_salary: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    max_salary: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String(128))
    job_type: Mapped[Optional[str]] = mapped_column(String(64))
    headcount: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    deadline_text: Mapped[Optional[str]] = mapped_column(String(32))
    view_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
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
        """Ưu tiên tính theo lương cao nhất; nếu không có thì tính theo cấp bậc."""
        if self.max_salary and self.max_salary > 0:
            return max(1000, int(self.max_salary * 0.1))
        level_fee_map = {
            "thuc tap sinh": 300_000,
            "thực tập sinh": 300_000,
            "nhan vien": 600_000,
            "nhân viên": 600_000,
            "chuyen vien": 900_000,
            "chuyên viên": 900_000,
            "truong nhom": 1_000_000,
            "trưởng nhóm": 1_000_000,
            "truong phong": 1_500_000,
            "trưởng phòng": 1_500_000,
            "quan ly": 1_500_000,
            "quản lý": 1_500_000,
            "giam doc": 2_500_000,
            "giám đốc": 2_500_000,
        }
        key = (self.level or "").strip().lower()
        return level_fee_map.get(key, 800_000)

    @property
    def count(self) -> int | None:
        return self.headcount

    @count.setter
    def count(self, value: int | None) -> None:
        self.headcount = value

    @property
    def deadline(self) -> str | None:
        return self.deadline_text

    @deadline.setter
    def deadline(self, value: str | None) -> None:
        self.deadline_text = value

    @property
    def applicants_count(self) -> int:
        return len(self.applications or [])

    @property
    def salary_text(self) -> str:
        if (not self.min_salary or self.min_salary <= 0) and (not self.max_salary or self.max_salary <= 0):
            return "Thương lượng"
        if self.min_salary and self.max_salary and self.min_salary > 0 and self.max_salary > 0:
            return f"{self.min_salary:,} - {self.max_salary:,} VND"
        single = self.max_salary if self.max_salary and self.max_salary > 0 else self.min_salary
        return f"Từ {int(single):,} VND" if single else "Thương lượng"
