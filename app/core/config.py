from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # 环境配置
    ENV: str = "development"  # 默认值为 "development"

    # 基础配置
    PROJECT_NAME: str = "FastAPI Template"
    API_V1_STR: str = "/api/v1"
    API_PORT: int = 8001

    # 数据库配置
    POSTGRES_USER: str = "demo"
    POSTGRES_PASSWORD: str = "demo123"
    POSTGRES_HOST: str = "100.108.167.94"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "demo"

    # Redis配置
    REDIS_HOST: str
    REDIS_PORT: int
    REDIS_PASSWORD: str

    # Celery配置
    CELERY_BROKER_URL: str = None  # Will be set in __init__
    CELERY_RESULT_BACKEND: str = None  # Will be set in __init__

    # HTTP代理配置 - 仅在测试环境使用
    USE_HTTP_PROXY: bool = False  # 默认不使用代理
    HTTP_PROXY: str = "http://127.0.0.1:7890"
    HTTPS_PROXY: str = "http://127.0.0.1:7890"

    # Email配置
    MAIL_MAILER: str
    MAIL_HOST: str
    MAIL_PORT: int
    MAIL_USERNAME: str
    MAIL_PASSWORD: str
    MAIL_FROM_ADDRESS: str
    MAIL_FROM_NAME: str
    MAIL_ENCRYPTION: str

    # Brevo配置
    BREVO_API_KEY: str = None
    BREVO_EMAIL_FROM: str = None
    BREVO_EMAIL_FROM_NAME: str = None

    # 管理员邮箱
    ADMIN_EMAIL: str = "dev@zetos.fr"

    # JWT配置
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # S3配置
    AWS_ACCESS_KEY_ID: str
    AWS_SECRET_ACCESS_KEY: str
    AWS_REGION: str
    AWS_BUCKET_NAME: str
    AWS_ENDPOINT: str

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"  # 可选，指定编码

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Now set Celery URLs after all attributes are loaded from env
        self.CELERY_BROKER_URL = f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/0"
        self.CELERY_RESULT_BACKEND = f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/0"

settings = Settings()
