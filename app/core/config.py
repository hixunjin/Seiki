from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # 环境配置
    ENV: str = "development"  # 默认值为 "development"

    # 基础配置
    PROJECT_NAME: str = "FastAPI Template"
    API_V1_STR: str = "/api/v1"

    # 数据库配置
    MYSQL_USER: str
    MYSQL_PASSWORD: str
    MYSQL_HOST: str
    MYSQL_PORT: str
    MYSQL_DB: str

    # Redis配置
    REDIS_HOST: str
    REDIS_PORT: int
    REDIS_PASSWORD: str

    # HTTP代理配置 - 仅在测试环境使用
    USE_HTTP_PROXY: bool = False  # 默认不使用代理
    HTTP_PROXY: str = "http://127.0.0.1:7890"
    HTTPS_PROXY: str = "http://127.0.0.1:7890"

    # Email配置(Brevo)
    BREVO_API_KEY: str
    EMAIL_FROM: str
    EMAIL_FROM_NAME: str

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


settings = Settings()
