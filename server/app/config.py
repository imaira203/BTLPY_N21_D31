from pathlib import Path
from urllib.parse import quote_plus

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_SERVER_ROOT = Path(__file__).resolve().parent.parent
_ENV_FILE = _SERVER_ROOT / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    mysql_host: str = Field(default="127.0.0.1", description="MySQL host")
    mysql_port: int = Field(default=3306, description="MySQL port")
    mysql_user: str = Field(default="root", description="MySQL user")
    mysql_password: str = Field(default="", description="MySQL password")
    mysql_database: str = Field(default="jobhub", description="Database name")
    mysql_charset: str = Field(default="utf8mb4", description="Client charset")

    jwt_secret: str = "change-me-in-production-use-long-random-string"
    jwt_algorithm: str = "HS256"
    access_token_expire_days: int = 30
    upload_dir: Path = Path(__file__).resolve().parent.parent / "uploads"
    max_upload_mb: int = 16

    # Thư mục con trong `uploads/` — tách loại file (đổi qua biến môi trường nếu cần)
    upload_subdir_cvs: str = Field(default="cvs", description="Thư mục chứa CV")
    upload_subdir_avatars: str = Field(default="avatars", description="Thư mục chứa avatar")
    upload_subdir_hr_assets: str = Field(default="hr_assets", description="Logo/tài liệu HR (mở rộng)")
    pro_monthly_price_vnd: int = Field(default=199000, description="Giá Pro cho ứng viên / tháng")
    invoice_due_days: int = Field(default=7, description="Số ngày đến hạn invoice")
    sepay_checkout_base_url: str = Field(
        default="https://my.sepay.vn/checkout",
        description="URL checkout Sepay (dựng pay link theo order code)",
    )

    def subdir_for(self, kind: str) -> str:
        """Map logical kind -> tên thư mục đã cấu hình."""
        mapping = {
            "cvs": self.upload_subdir_cvs,
            "avatars": self.upload_subdir_avatars,
            "hr_assets": self.upload_subdir_hr_assets,
        }
        return mapping.get(kind, kind)

    @property
    def database_url(self) -> str:
        user = quote_plus(self.mysql_user)
        password = quote_plus(self.mysql_password)
        return (
            f"mysql+pymysql://{user}:{password}@{self.mysql_host}:{self.mysql_port}/"
            f"{self.mysql_database}?charset={self.mysql_charset}"
        )


settings = Settings()
