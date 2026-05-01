from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base


class ProfileView(Base):
    __tablename__ = "profile_views"
    __table_args__ = (
        UniqueConstraint("viewer_user_id", "viewed_user_id", name="uq_profile_views_pair"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    viewer_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    viewed_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    viewed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)
