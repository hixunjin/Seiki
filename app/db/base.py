from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.core.config import settings

SQLALCHEMY_DATABASE_URL = (
    f"mysql+aiomysql://{settings.MYSQL_USER}:{settings.MYSQL_PASSWORD}"
    f"@{settings.MYSQL_HOST}:{settings.MYSQL_PORT}/{settings.MYSQL_DB}"
)

engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL,
    echo=True,
    future=True,
    pool_pre_ping=True,
    # 增强连接池配置以提高稳定性
    pool_recycle=1800,  # 30分钟内回收连接
    pool_timeout=30,    # 获取连接的超时时间
    max_overflow=10,    # 允许的最大连接溢出数
    pool_size=20,       # 连接池大小
    connect_args={"connect_timeout": 10}  # 连接超时时间
)

# 为调度任务创建一个独立的引擎和会话工厂
# 这样每个调度任务都会使用自己的连接池和事件循环
def create_scheduler_engine():
    """为调度任务创建独立的数据库引擎，确保不会与主应用程序共享事件循环"""
    return create_async_engine(
        SQLALCHEMY_DATABASE_URL,
        echo=True,
        future=True,
        pool_pre_ping=True,
        pool_recycle=1800,
        pool_timeout=30,
        max_overflow=5,
        pool_size=5,
        connect_args={"connect_timeout": 10}
    )

def create_scheduler_session_factory(engine):
    """为调度任务创建独立的会话工厂"""
    return async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

AsyncSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

Base = declarative_base()


async def close_db_engine():
    """关闭数据库引擎和连接池"""
    await engine.dispose()
