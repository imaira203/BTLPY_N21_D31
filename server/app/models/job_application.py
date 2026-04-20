from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Enum, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db import Base
from .enums import ApplicationStatus


class JobApplication(Base):
    __tablename__ = "job_applications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id"), nullable=False, index=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    cv_id: Mapped[Optional[int]] = mapped_column(ForeignKey("cv_documents.id"))
    status: Mapped[ApplicationStatus] = mapped_column(Enum(ApplicationStatus), default=ApplicationStatus.submitted)
    accepted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    contact_unlocked_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    job: Mapped["Job"] = relationship(back_populates="applications")
    candidate: Mapped["User"] = relationship(back_populates="applications")

    def accept(self) -> None:
        self.status = ApplicationStatus.accepted
        self.accepted_at = datetime.utcnow()

    def unlock_contact(self) -> None:
        self.contact_unlocked_at = datetime.utcnow()
