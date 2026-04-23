from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db import Base


class CandidateProfile(Base):
    __tablename__ = "candidate_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, nullable=False, index=True)
    headline: Mapped[Optional[str]] = mapped_column(String(255))
    introduction: Mapped[Optional[str]] = mapped_column(Text)
    skills: Mapped[Optional[str]] = mapped_column(Text)
    experience: Mapped[Optional[str]] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user: Mapped["User"] = relationship(back_populates="candidate_profile")

    def skills_as_list(self) -> list[str]:
        if not self.skills:
            return []
        return [item.strip() for item in self.skills.split(",") if item.strip()]
