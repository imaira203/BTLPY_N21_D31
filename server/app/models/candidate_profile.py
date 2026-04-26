from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db import Base


class CandidateProfile(Base):
    __tablename__ = "candidate_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, nullable=False, index=True)
    tagline: Mapped[Optional[str]] = mapped_column(String(255))
    phone: Mapped[Optional[str]] = mapped_column(String(64))
    address: Mapped[Optional[str]] = mapped_column(String(255))
    professional_field: Mapped[Optional[str]] = mapped_column(String(255))
    degree: Mapped[Optional[str]] = mapped_column(String(255))
    experience_text: Mapped[Optional[str]] = mapped_column(String(255))
    language: Mapped[Optional[str]] = mapped_column(String(255))
    skills_json: Mapped[Optional[str]] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user: Mapped["User"] = relationship(back_populates="candidate_profile")

    def skills_as_dict(self) -> dict[str, list[str]]:
        if not self.skills_json:
            return {}
        try:
            parsed: Any = json.loads(self.skills_json)
        except Exception:
            return {}
        if not isinstance(parsed, dict):
            return {}
        out: dict[str, list[str]] = {}
        for category, tags in parsed.items():
            cat_name = str(category).strip()
            if not cat_name:
                continue
            if isinstance(tags, list):
                normalized_tags = [str(tag).strip() for tag in tags if str(tag).strip()]
                if normalized_tags:
                    out[cat_name] = normalized_tags
        return out
