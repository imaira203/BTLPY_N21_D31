from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
import base64
import hashlib
import hmac
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import settings
from .models import Invoice, InvoiceStatus, InvoiceType


def build_sepay_checkout_fields(order_code: str, amount_vnd: int, note: str, owner_user_id: int) -> dict[str, str]:
    if not settings.sepay_merchant_id or not settings.sepay_secret_key:
        raise HTTPException(status_code=500, detail="SePay chua duoc cau hinh merchant_id/secret_key")
    fields: dict[str, str] = {
        "order_amount": str(int(amount_vnd)),
        "merchant": settings.sepay_merchant_id,
        "currency": "VND",
        "operation": settings.sepay_operation,
        "order_description": note,
        "order_invoice_number": order_code,
        "customer_id": f"CANDIDATE_{owner_user_id}",
        "payment_method": settings.sepay_payment_method,
    }
    if settings.sepay_success_url:
        fields["success_url"] = settings.sepay_success_url
    if settings.sepay_error_url:
        fields["error_url"] = settings.sepay_error_url
    if settings.sepay_cancel_url:
        fields["cancel_url"] = settings.sepay_cancel_url

    signed_fields_order = [
        "order_amount",
        "merchant",
        "currency",
        "operation",
        "order_description",
        "order_invoice_number",
        "customer_id",
        "payment_method",
        "success_url",
        "error_url",
        "cancel_url",
    ]
    signed_parts: list[str] = []
    for key in signed_fields_order:
        if key in fields:
            signed_parts.append(f"{key}={fields[key]}")
    signing_payload = ",".join(signed_parts)
    signature = base64.b64encode(
        hmac.new(
            settings.sepay_secret_key.encode("utf-8"),
            signing_payload.encode("utf-8"),
            hashlib.sha256,
        ).digest()
    ).decode("utf-8")
    fields["signature"] = signature
    return fields


def build_sepay_checkout_url(order_code: str) -> str:
    base = settings.public_api_base_url.rstrip("/")
    return f"{base}/api/candidate/subscription/sepay/checkout/{order_code}"


def create_invoice(
    db: Session,
    owner_user_id: int,
    invoice_type: InvoiceType,
    amount_vnd: int,
    note: str,
    application_id: int | None = None,
    due_at: datetime | None = None,
) -> Invoice:
    due_at_final = due_at or (datetime.utcnow() + timedelta(days=max(1, settings.invoice_due_days)))
    order_code = f"INV-{owner_user_id}-{uuid4().hex[:14].upper()}"
    _ = build_sepay_checkout_fields(
        order_code=order_code,
        amount_vnd=amount_vnd,
        note=note,
        owner_user_id=owner_user_id,
    )
    payment_url = build_sepay_checkout_url(order_code=order_code)

    invoice = Invoice(
        owner_user_id=owner_user_id,
        invoice_type=invoice_type,
        amount=Decimal(amount_vnd),
        currency="VND",
        due_at=due_at_final,
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
