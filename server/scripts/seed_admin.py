"""Create default admin user. Run: python -m scripts.seed_admin from server directory."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import SessionLocal, engine
from app.models import Base, User, UserRole
from app.security import hash_password


def run() -> None:
    Base.metadata.create_all(bind=engine)
    db: Session = SessionLocal()
    try:
        email = "admin@jobhub.local"
        existing = db.scalar(select(User).where(User.email == email))
        if existing:
            print("Admin already exists.")
            return
        admin = User(
            email=email,
            password_hash=hash_password("admin123"),
            full_name="Administrator",
            role=UserRole.admin,
        )
        db.add(admin)
        db.commit()
        print(f"Created admin: {email} / admin123 — đổi mật khẩu sau khi triển khai.")
    finally:
        db.close()


if __name__ == "__main__":
    run()
