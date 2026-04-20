from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Enum, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db import Base
from .enums import SubscriptionStatus


class CandidateSubscription(Base):
    __tablename__ = "candidate_subscriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, unique=True, index=True)
    status: Mapped[SubscriptionStatus] = mapped_column(Enum(SubscriptionStatus), default=SubscriptionStatus.inactive)
    pro_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    candidate: Mapped["User"] = relationship(back_populates="candidate_subscription")

    def is_active_pro(self) -> bool:
        return bool(
            self.status == SubscriptionStatus.active
            and self.pro_expires_at is not None
            and self.pro_expires_at > datetime.utcnow()
        )
