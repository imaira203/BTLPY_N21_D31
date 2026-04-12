from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import HRProfile, HRApprovalStatus, User, UserRole
from ..schemas import LoginIn, RegisterCandidate, RegisterHR, TokenResponse, UserOut
from ..security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


def _issue_token(user: User) -> TokenResponse:
    token = create_access_token(str(user.id), extra={"role": user.role.value})
    return TokenResponse(access_token=token)


@router.post("/register/candidate", response_model=TokenResponse)
def register_candidate(body: RegisterCandidate, db: Annotated[Session, Depends(get_db)]) -> TokenResponse:
    exists = db.scalar(select(User).where(User.email == body.email))
    if exists:
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(
        email=body.email,
        password_hash=hash_password(body.password),
        full_name=body.full_name,
        role=UserRole.candidate,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return _issue_token(user)


@router.post("/register/hr", response_model=TokenResponse)
def register_hr(body: RegisterHR, db: Annotated[Session, Depends(get_db)]) -> TokenResponse:
    exists = db.scalar(select(User).where(User.email == body.email))
    if exists:
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(
        email=body.email,
        password_hash=hash_password(body.password),
        full_name=body.full_name,
        role=UserRole.hr,
    )
    db.add(user)
    db.flush()
    profile = HRProfile(
        user_id=user.id,
        company_name=body.company_name,
        contact_phone=body.contact_phone,
        company_description=body.company_description,
        approval_status=HRApprovalStatus.pending,
    )
    db.add(profile)
    db.commit()
    db.refresh(user)
    return _issue_token(user)


@router.post("/login", response_model=TokenResponse)
def login(body: LoginIn, db: Annotated[Session, Depends(get_db)]) -> TokenResponse:
    user = db.scalar(select(User).where(User.email == body.email))
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return _issue_token(user)
