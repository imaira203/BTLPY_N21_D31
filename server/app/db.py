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
        add_column_if_missing("job_applications", "cv_id", "INT NULL", after="candidate_id")
        add_column_if_missing("candidate_profiles", "tagline", "VARCHAR(255) NULL", after="user_id")
        add_column_if_missing("candidate_profiles", "phone", "VARCHAR(64) NULL", after="tagline")
        add_column_if_missing("candidate_profiles", "address", "VARCHAR(255) NULL", after="phone")
        add_column_if_missing("candidate_profiles", "professional_field", "VARCHAR(255) NULL", after="address")
        add_column_if_missing("candidate_profiles", "degree", "VARCHAR(255) NULL", after="professional_field")
        add_column_if_missing("candidate_profiles", "experience_text", "VARCHAR(255) NULL", after="degree")
        add_column_if_missing("candidate_profiles", "language", "VARCHAR(255) NULL", after="experience_text")
        add_column_if_missing("candidate_profiles", "skills_json", "TEXT NULL", after="language")
        add_column_if_missing("candidate_subscriptions", "status", "VARCHAR(16) NOT NULL DEFAULT 'inactive'", after="candidate_id")
        add_column_if_missing("candidate_subscriptions", "pro_expires_at", "DATETIME NULL", after="status")
        add_column_if_missing("candidate_subscriptions", "updated_at", "DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP", after="pro_expires_at")
        add_column_if_missing("invoices", "sepay_order_code", "VARCHAR(64) NULL", after="due_at")
        add_column_if_missing("invoices", "sepay_payment_url", "VARCHAR(1024) NULL", after="sepay_order_code")
        add_column_if_missing("invoices", "application_id", "INT NULL", after="paid_at")
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
        if not insp.has_table("candidate_subscriptions"):
            stmt = (
                "CREATE TABLE candidate_subscriptions ("
                "id INT AUTO_INCREMENT PRIMARY KEY, "
                "candidate_id INT NOT NULL UNIQUE, "
                "status VARCHAR(16) NOT NULL DEFAULT 'inactive', "
                "pro_expires_at DATETIME NULL, "
                "updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP, "
                "INDEX idx_candidate_subscription_candidate (candidate_id), "
                "CONSTRAINT fk_candidate_subscription_candidate FOREIGN KEY (candidate_id) REFERENCES users(id) ON DELETE CASCADE"
                ")"
            )
            with engine.begin() as conn:
                conn.execute(text(stmt))
            log.info("Đã tạo bảng candidate_subscriptions (DB cũ).")
        if insp.has_table("candidate_subscription_payments"):
            with engine.begin() as conn:
                conn.execute(text("DROP TABLE candidate_subscription_payments"))
            log.info("Đã xóa bảng candidate_subscription_payments (không còn sử dụng).")
        if not insp.has_table("candidate_profile_views"):
            stmt = (
                "CREATE TABLE candidate_profile_views ("
                "id INT AUTO_INCREMENT PRIMARY KEY, "
                "candidate_id INT NOT NULL, "
                "viewer_user_id INT NOT NULL, "
                "job_id INT NOT NULL, "
                "application_id INT NULL, "
                "viewed_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, "
                "INDEX idx_candidate_profile_views_candidate (candidate_id), "
                "INDEX idx_candidate_profile_views_viewer (viewer_user_id), "
                "INDEX idx_candidate_profile_views_job (job_id), "
                "INDEX idx_candidate_profile_views_application (application_id), "
                "INDEX idx_candidate_profile_views_viewed_at (viewed_at), "
                "UNIQUE KEY uq_candidate_profile_view (candidate_id, viewer_user_id, job_id), "
                "CONSTRAINT fk_candidate_profile_views_candidate FOREIGN KEY (candidate_id) REFERENCES users(id) ON DELETE CASCADE, "
                "CONSTRAINT fk_candidate_profile_views_viewer FOREIGN KEY (viewer_user_id) REFERENCES users(id) ON DELETE CASCADE, "
                "CONSTRAINT fk_candidate_profile_views_job FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE, "
                "CONSTRAINT fk_candidate_profile_views_application FOREIGN KEY (application_id) REFERENCES job_applications(id) ON DELETE SET NULL"
                ")"
            )
            with engine.begin() as conn:
                conn.execute(text(stmt))
            log.info("Đã tạo bảng candidate_profile_views (DB cũ).")
        if insp.has_table("invoices"):
            with engine.begin() as conn:
                conn.execute(
                    text(
                        "UPDATE invoices SET sepay_order_code = CONCAT('INV-', owner_user_id, '-', id) "
                        "WHERE sepay_order_code IS NULL OR sepay_order_code = ''"
                    )
                )
            if dialect == "mysql":
                with engine.begin() as conn:
                    conn.execute(text("ALTER TABLE invoices MODIFY COLUMN sepay_order_code VARCHAR(64) NOT NULL"))
            log.info("Đã chuẩn hóa invoices.sepay_order_code cho DB cũ.")
        if dialect == "mysql" and insp.has_table("jobs"):
            with engine.begin() as conn:
                conn.execute(
                    text(
                        "ALTER TABLE jobs "
                        "MODIFY COLUMN status "
                        "ENUM('draft','pending_approval','published','closed','rejected') "
                        "NOT NULL DEFAULT 'pending_approval'"
                    )
                )
            log.info("Đã chuẩn hóa enum jobs.status để hỗ trợ trạng thái 'closed'.")
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
        if insp.has_table("users") and insp.has_table("candidate_subscriptions"):
            stmt = (
                "INSERT INTO candidate_subscriptions (candidate_id, status) "
                "SELECT u.id, 'inactive' "
                "FROM users u "
                "LEFT JOIN candidate_subscriptions cs ON cs.candidate_id = u.id "
                "WHERE u.role = 'candidate' AND cs.candidate_id IS NULL"
            )
            with engine.begin() as conn:
                conn.execute(text(stmt))
    except Exception as e:
        log.warning("Không áp dụng được patch schema: %s", e)
