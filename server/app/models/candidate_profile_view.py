from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base


class CandidateProfileView(Base):
    __tablename__ = "candidate_profile_views"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    viewer_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id"), nullable=False, index=True)
    application_id: Mapped[int | None] = mapped_column(ForeignKey("job_applications.id"), nullable=True, index=True)
    viewed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
