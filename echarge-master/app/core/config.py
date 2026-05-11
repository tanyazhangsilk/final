from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from pydantic_settings import BaseSettings

# project root -> app -> core
BASE_DIR = Path(__file__).resolve().parents[2]
BACKEND_DIR = BASE_DIR / "backend"

load_dotenv(BACKEND_DIR / ".env", override=False)
load_dotenv(BASE_DIR / ".env", override=False)


class Settings(BaseSettings):
    PROJECT_NAME: str = "E-Charge 聚合平台"
    API_V1_PREFIX: str = "/api/v1"
    # 逗号分隔的额外 CORS 源，便于局域网调试微信小程序（例如 http://192.168.1.3:5173）
    CORS_EXTRA_ORIGINS: str = ""

    MYSQL_USER: str = "root"
    MYSQL_PASSWORD: str = "password"
    MYSQL_HOST: str = "localhost"
    MYSQL_PORT: int = 3306
    MYSQL_DB: str = "e_charge"

    DB_HOST: Optional[str] = None
    DB_PORT: Optional[int] = None
    DB_USER: Optional[str] = None
    DB_PASSWORD: Optional[str] = None
    DB_NAME: Optional[str] = None

    SQLALCHEMY_DATABASE_URI: Optional[str] = None

    class Config:
        env_file_encoding = "utf-8"

    @property
    def database_url(self) -> str:
        if self.SQLALCHEMY_DATABASE_URI:
            return self.SQLALCHEMY_DATABASE_URI
        user = self.DB_USER or self.MYSQL_USER
        password = self.DB_PASSWORD or self.MYSQL_PASSWORD
        host = self.DB_HOST or self.MYSQL_HOST
        port = self.DB_PORT or self.MYSQL_PORT
        db = self.DB_NAME or self.MYSQL_DB
        return f"mysql+pymysql://{user}:{password}@{host}:{port}/{db}"


settings = Settings()
