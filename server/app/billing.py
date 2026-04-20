from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import settings
from .models import Invoice, InvoiceStatus, InvoiceType


def create_invoice(
    db: Session,
    owner_user_id: int,
    invoice_type: InvoiceType,
    amount_vnd: int,
    note: str,
    application_id: int | None = None,
) -> Invoice:
    due_at = datetime.utcnow() + timedelta(days=max(1, settings.invoice_due_days))
    order_code = f"INV-{owner_user_id}-{uuid4().hex[:14].upper()}"
    payment_url = f"{settings.sepay_checkout_base_url}?order_code={order_code}"
    invoice = Invoice(
        owner_user_id=owner_user_id,
        invoice_type=invoice_type,
        amount=Decimal(amount_vnd),
        currency="VND",
        due_at=due_at,
        sepay_order_code=order_code,
        sepay_payment_url=payment_url,
        note=note,
        application_id=application_id,
    )
    db.add(invoice)
    db.flush()
    return invoice


def mark_invoice_paid(db: Session, owner_user_id: int, invoice_id: int) -> Invoice:
    invoice = db.scalar(select(Invoice).where(Invoice.id == invoice_id, Invoice.owner_user_id == owner_user_id))
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    if invoice.status == InvoiceStatus.paid:
        return invoice
    if invoice.status in (InvoiceStatus.cancelled, InvoiceStatus.overdue):
        raise HTTPException(status_code=400, detail="Invoice is not payable")
    invoice.mark_paid()
    return invoice
