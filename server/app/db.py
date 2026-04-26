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

        def drop_column_if_exists(table: str, column: str) -> None:
            if not insp.has_table(table):
                return
            names = {c["name"] for c in insp.get_columns(table)}
            if column not in names:
                return
            stmt = f"ALTER TABLE {table} DROP COLUMN {column}"
            with engine.begin() as conn:
                conn.execute(text(stmt))
            log.info("Đã xóa cột %s.%s (dọn schema cũ).", table, column)

        add_column_if_missing("users", "avatar_storage_key", "VARCHAR(512) NULL", after="full_name")
        add_column_if_missing("hr_profiles", "avatar_storage_key", "VARCHAR(512) NULL", after="company_name")
        add_column_if_missing("jobs", "department", "VARCHAR(128) NULL", after="description")
        add_column_if_missing("jobs", "level", "VARCHAR(64) NULL", after="department")
        add_column_if_missing("jobs", "min_salary", "INT NULL", after="level")
        add_column_if_missing("jobs", "max_salary", "INT NULL", after="min_salary")
        add_column_if_missing("jobs", "headcount", "INT NULL", after="job_type")
        add_column_if_missing("jobs", "deadline_text", "VARCHAR(32) NULL", after="headcount")
        add_column_if_missing("jobs", "view_count", "INT NOT NULL DEFAULT 0", after="deadline_text")
        add_column_if_missing("job_applications", "accepted_at", "DATETIME NULL", after="status")
        add_column_if_missing("job_applications", "contact_unlocked_at", "DATETIME NULL", after="accepted_at")
        add_column_if_missing("candidate_profiles", "tagline", "VARCHAR(255) NULL", after="user_id")
        add_column_if_missing("candidate_profiles", "phone", "VARCHAR(64) NULL", after="tagline")
        add_column_if_missing("candidate_profiles", "address", "VARCHAR(255) NULL", after="phone")
        add_column_if_missing("candidate_profiles", "professional_field", "VARCHAR(255) NULL", after="address")
        add_column_if_missing("candidate_profiles", "degree", "VARCHAR(255) NULL", after="professional_field")
        add_column_if_missing("candidate_profiles", "experience_text", "VARCHAR(255) NULL", after="degree")
        add_column_if_missing("candidate_profiles", "language", "VARCHAR(255) NULL", after="experience_text")
        add_column_if_missing("candidate_profiles", "skills_json", "TEXT NULL", after="language")
        drop_column_if_exists("candidate_profiles", "headline")
        drop_column_if_exists("candidate_profiles", "introduction")
        drop_column_if_exists("candidate_profiles", "skills")
        drop_column_if_exists("candidate_profiles", "experience")
        if not insp.has_table("candidate_profiles"):
            stmt = (
                "CREATE TABLE candidate_profiles ("
                "id INT AUTO_INCREMENT PRIMARY KEY, "
                "user_id INT NOT NULL UNIQUE, "
                "tagline VARCHAR(255) NULL, "
                "phone VARCHAR(64) NULL, "
                "address VARCHAR(255) NULL, "
                "professional_field VARCHAR(255) NULL, "
                "degree VARCHAR(255) NULL, "
                "experience_text VARCHAR(255) NULL, "
                "language VARCHAR(255) NULL, "
                "skills_json TEXT NULL, "
                "updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP, "
                "INDEX idx_candidate_profile_user (user_id), "
                "CONSTRAINT fk_candidate_profiles_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE"
                ")"
            )
            with engine.begin() as conn:
                conn.execute(text(stmt))
            log.info("Đã tạo bảng candidate_profiles (DB cũ).")
        if not insp.has_table("candidate_saved_jobs"):
            stmt = (
                "CREATE TABLE candidate_saved_jobs ("
                "id INT AUTO_INCREMENT PRIMARY KEY, "
                "candidate_id INT NOT NULL, "
                "job_id INT NOT NULL, "
                "created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, "
                "UNIQUE KEY uq_candidate_saved_job (candidate_id, job_id), "
                "INDEX idx_saved_jobs_candidate (candidate_id), "
                "INDEX idx_saved_jobs_job (job_id), "
                "CONSTRAINT fk_saved_jobs_candidate FOREIGN KEY (candidate_id) REFERENCES users(id) ON DELETE CASCADE, "
                "CONSTRAINT fk_saved_jobs_job FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE"
                ")"
            )
            with engine.begin() as conn:
                conn.execute(text(stmt))
            log.info("Đã tạo bảng candidate_saved_jobs (DB cũ).")
        if not insp.has_table("candidate_subscription_payments"):
            stmt = (
                "CREATE TABLE candidate_subscription_payments ("
                "id INT AUTO_INCREMENT PRIMARY KEY, "
                "candidate_id INT NOT NULL, "
                "invoice_id INT NULL UNIQUE, "
                "months INT NOT NULL, "
                "amount DECIMAL(12,2) NOT NULL, "
                "currency VARCHAR(8) NOT NULL DEFAULT 'VND', "
                "paid_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, "
                "created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, "
                "INDEX idx_candidate_sub_payments_candidate (candidate_id), "
                "INDEX idx_candidate_sub_payments_paid_at (paid_at), "
                "CONSTRAINT fk_sub_payment_candidate FOREIGN KEY (candidate_id) REFERENCES users(id) ON DELETE CASCADE, "
                "CONSTRAINT fk_sub_payment_invoice FOREIGN KEY (invoice_id) REFERENCES invoices(id) ON DELETE SET NULL"
                ")"
            )
            with engine.begin() as conn:
                conn.execute(text(stmt))
            log.info("Đã tạo bảng candidate_subscription_payments (DB cũ).")
        if insp.has_table("users") and insp.has_table("candidate_profiles"):
            stmt = (
                "INSERT INTO candidate_profiles (user_id) "
                "SELECT u.id "
                "FROM users u "
                "LEFT JOIN candidate_profiles cp ON cp.user_id = u.id "
                "WHERE u.role = 'candidate' AND cp.user_id IS NULL"
            )
            with engine.begin() as conn:
                conn.execute(text(stmt))
    except Exception as e:
        log.warning("Không áp dụng được patch schema: %s", e)
