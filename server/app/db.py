import logging
from collections.abc import Generator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import settings

log = logging.getLogger("jobhub.db")


class Base(DeclarativeBase):
    pass


engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_recycle=3600,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def apply_mysql_schema_patches() -> None:
    """`Base.metadata.create_all()` không thêm cột mới vào bảng đã tồn tại — bổ sung cột thiếu (DB cũ)."""
    try:
        insp = inspect(engine)
        if not insp.has_table("users"):
            return
        names = {c["name"] for c in insp.get_columns("users")}
        if "avatar_storage_key" in names:
            return
        dialect = engine.dialect.name
        if dialect == "mysql":
            stmt = "ALTER TABLE users ADD COLUMN avatar_storage_key VARCHAR(512) NULL AFTER full_name"
        else:
            stmt = "ALTER TABLE users ADD COLUMN avatar_storage_key VARCHAR(512) NULL"
        with engine.begin() as conn:
            conn.execute(text(stmt))
        log.info("Đã thêm cột users.avatar_storage_key (DB cũ).")
    except Exception as e:
        log.warning("Không áp dụng được patch schema (avatar_storage_key): %s", e)
