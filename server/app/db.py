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
        dialect = engine.dialect.name

        def add_column_if_missing(table: str, column: str, sql_type: str, after: str | None = None) -> None:
            if not insp.has_table(table):
                return
            names = {c["name"] for c in insp.get_columns(table)}
            if column in names:
                return
            stmt = f"ALTER TABLE {table} ADD COLUMN {column} {sql_type}"
            if dialect == "mysql" and after:
                stmt += f" AFTER {after}"
            with engine.begin() as conn:
                conn.execute(text(stmt))
            log.info("Đã thêm cột %s.%s (DB cũ).", table, column)

        add_column_if_missing("users", "avatar_storage_key", "VARCHAR(512) NULL", after="full_name")
        add_column_if_missing("jobs", "avg_salary", "INT NULL", after="salary_text")
        add_column_if_missing("job_applications", "accepted_at", "DATETIME NULL", after="status")
        add_column_if_missing("job_applications", "contact_unlocked_at", "DATETIME NULL", after="accepted_at")
        if not insp.has_table("candidate_profiles"):
            stmt = (
                "CREATE TABLE candidate_profiles ("
                "id INT AUTO_INCREMENT PRIMARY KEY, "
                "user_id INT NOT NULL UNIQUE, "
                "headline VARCHAR(255) NULL, "
                "introduction TEXT NULL, "
                "skills TEXT NULL, "
                "experience TEXT NULL, "
                "updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP, "
                "INDEX idx_candidate_profile_user (user_id), "
                "CONSTRAINT fk_candidate_profiles_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE"
                ")"
            )
            with engine.begin() as conn:
                conn.execute(text(stmt))
            log.info("Đã tạo bảng candidate_profiles (DB cũ).")
    except Exception as e:
        log.warning("Không áp dụng được patch schema: %s", e)
