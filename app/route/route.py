from fastapi import FastAPI, Request, status, HTTPException
from fastapi.middleware.cors import CORSMiddleware
# client
from app.api.client.v1 import demo as client_demo
from app.api.client.v1 import config as client_config

# backoffice
from app.api.backoffice.v1 import auth as backoffice_auth
from app.api.backoffice.v1 import admin as backoffice_admin


from app.core.config import settings
from fastapi.exceptions import RequestValidationError
from app.exceptions.http_exceptions import APIException
from app.schemas.response import ApiResponse
from contextlib import asynccontextmanager
from app.core.log_config import setup_logging, shutdown_logging
from app.services.common.redis import redis_client
from app.services.common.thread_pool import thread_pool_service
from app.db.base import close_db_engine
from app.schedule.schedule import setup_scheduler, shutdown_scheduler
import logging

logger = logging.getLogger(__name__)

# 根据环境设置CORS来源
ALLOWED_ORIGINS = ["*"] if settings.ENV == "development" or settings.ENV == "preview" else [
    "*"  # TODO: replace with production domain
]


@asynccontextmanager
async def lifespan(application: FastAPI):
    # 启动时执行
    setup_logging()
    logger.info("Application starting up")
    
    # 初始化定时任务调度器
    setup_scheduler(application)
    logger.info("Task scheduler initialized")

    yield  # 应用运行期间

    # 关闭时执行
    shutdown_scheduler()  # 关闭定时任务调度器
    await close_db_engine()  # 清理数据库引擎
    await redis_client.close()  # 关闭Redis连接
    thread_pool_service.shutdown()  # 关闭邮件线程池
    shutdown_logging()
    logger.info("Application shutting down")


def create_app():
    app = FastAPI(
        lifespan=lifespan,
        title=settings.PROJECT_NAME,
        openapi_url=f"{settings.API_V1_STR}/openapi.json"
    )

    # 配置CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=ALLOWED_ORIGINS,  # 在生产环境中应该设置具体的域名
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/")
    async def root():
        logger.info("Root endpoint called")
        return {"message": "Welcome to TIP API"}

    # Client 路由
    app.include_router(
        client_demo.router,
        prefix=f"{settings.API_V1_STR}/demo",
        tags=["client-demo"]
    )

    app.include_router(
        client_config.router,
        prefix=f"{settings.API_V1_STR}/config",
        tags=["client-config"]
    )

    # Backoffice 路由
    app.include_router(
        backoffice_auth.router,
        prefix=f"{settings.API_V1_STR}/backoffice/auth",
        tags=["backoffice-auth"]
    )

    app.include_router(
        backoffice_admin.router,
        prefix=f"{settings.API_V1_STR}/backoffice/admins",
        tags=["backoffice-admin"]
    )

    @app.exception_handler(APIException)
    async def api_exception_handler(request: Request, exc: APIException):
        logger.error(f"API Exception: {exc.status_code} - {exc.code} - {exc.detail}",
                    extra={"request": f"{request.method} {request.url}"})
        return ApiResponse.failed(
            message=exc.detail,
            body_code=exc.code,  # 业务错误码
            http_code=exc.status_code,
            data=exc.data
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        logger.error(f"HTTP Exception: {exc.status_code} - {exc.detail}",
                    extra={"request": f"{request.method} {request.url}"})
        return ApiResponse.failed(
            message=exc.detail,
            body_code=exc.status_code,  # 回落使用 HTTP 状态码
            http_code=exc.status_code,
            data=None
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        logger.warning(f"Validation Error: {exc.errors()}",
                    extra={"request": f"{request.method} {request.url}"})
        return ApiResponse.failed(
            message="Validation error",
            body_code=1001,
            http_code=status.HTTP_400_BAD_REQUEST,
            data=exc.errors()
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.exception(f"Unhandled Exception: {str(exc)}",
                        extra={"request": f"{request.method} {request.url}"})
        return ApiResponse.failed(
            message="Internal server error",
            body_code=1005,
            http_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    return app