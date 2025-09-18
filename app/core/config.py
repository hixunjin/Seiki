from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Environment configuration
    ENV: str = "development"  # Default value is "development"

    # Basic configuration
    PROJECT_NAME: str = "FastAPI Template"
    API_V1_STR: str = "/api/v1"
    API_PORT: int = 8001

    # Database configuration
    POSTGRES_USER: str = "demo"
    POSTGRES_PASSWORD: str = "demo123"
    POSTGRES_HOST: str = "100.108.167.94"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "demo"

    # Redis configuration
    REDIS_HOST: str
    REDIS_PORT: int
    REDIS_PASSWORD: str

    # Celery configuration
    CELERY_BROKER_URL: str = None  # Will be set in __init__
    CELERY_RESULT_BACKEND: str = None  # Will be set in __init__

    # HTTP proxy configuration - only for testing environment
    USE_HTTP_PROXY: bool = False  # Default not to use proxy
    HTTP_PROXY: str = "http://127.0.0.1:7890"
    HTTPS_PROXY: str = "http://127.0.0.1:7890"

    # Email configuration
    MAIL_MAILER: str
    MAIL_HOST: str
    MAIL_PORT: int
    MAIL_USERNAME: str
    MAIL_PASSWORD: str
    MAIL_FROM_ADDRESS: str
    MAIL_FROM_NAME: str
    MAIL_ENCRYPTION: str

    # Brevo configuration
    BREVO_API_KEY: str = None
    BREVO_EMAIL_FROM: str = None
    BREVO_EMAIL_FROM_NAME: str = None

    # Admin email
    ADMIN_EMAIL: str = "dev@zetos.fr"

    # JWT configuration
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # S3 configuration
    AWS_ACCESS_KEY_ID: str
    AWS_SECRET_ACCESS_KEY: str
    AWS_REGION: str
    AWS_BUCKET_NAME: str
    AWS_ENDPOINT: str

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"  # Optional, specify encoding

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Now set Celery URLs after all attributes are loaded from env
        self.CELERY_BROKER_URL = f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/0"
        self.CELERY_RESULT_BACKEND = f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/0"

settings = Settings()
