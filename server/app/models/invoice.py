from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db import Base
from .enums import InvoiceStatus, InvoiceType


class Invoice(Base):
    __tablename__ = "invoices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    owner_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    invoice_type: Mapped[InvoiceType] = mapped_column(Enum(InvoiceType), nullable=False)
    status: Mapped[InvoiceStatus] = mapped_column(Enum(InvoiceStatus), default=InvoiceStatus.pending, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), default="VND", nullable=False)
    due_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    sepay_order_code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    sepay_payment_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    paid_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    application_id: Mapped[Optional[int]] = mapped_column(ForeignKey("job_applications.id"), nullable=True, index=True)

    owner: Mapped["User"] = relationship(back_populates="invoices")

    def is_payable(self) -> bool:
        return self.status == InvoiceStatus.pending

    def mark_paid(self) -> None:
        self.status = InvoiceStatus.paid
        self.paid_at = datetime.utcnow()
