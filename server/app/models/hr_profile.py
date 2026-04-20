from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db import Base
from .enums import HRApprovalStatus


class HRProfile(Base):
    __tablename__ = "hr_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, nullable=False)
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    contact_phone: Mapped[Optional[str]] = mapped_column(String(64))
    company_description: Mapped[Optional[str]] = mapped_column(Text)
    approval_status: Mapped[HRApprovalStatus] = mapped_column(Enum(HRApprovalStatus), default=HRApprovalStatus.pending)
    admin_note: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship(back_populates="hr_profile")

    def is_approved(self) -> bool:
        return self.approval_status == HRApprovalStatus.approved
