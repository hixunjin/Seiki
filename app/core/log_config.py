import os
from datetime import datetime
from queue import SimpleQueue
from logging.handlers import QueueListener, QueueHandler
from logging.handlers import TimedRotatingFileHandler
from app.core.config import settings
import logging
from logging.config import dictConfig

# 日志目录
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
LOG_DIR = os.path.join(BASE_DIR, "logs")
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

LOG_FILE = os.path.join(LOG_DIR, f"app_{datetime.now().strftime('%Y%m%d')}.log")
SQLALCHEMY_LOG_FILE = os.path.join(LOG_DIR, f"sqlalchemy_{datetime.now().strftime('%Y%m%d')}.log")

# 根据环境设置日志级别
ENV = settings.ENV.lower()
LOG_LEVELS = {
    "development": "DEBUG",
    "testing": "INFO",
    "production": "WARNING"
}
LOG_LEVEL = LOG_LEVELS.get(ENV, "INFO")
SQLALCHEMY_LEVEL = "INFO" if ENV == "production" else "DEBUG"

# 创建日志队列和处理器
log_queue = SimpleQueue()
console_handler = logging.StreamHandler()
file_handler = TimedRotatingFileHandler(
    filename=LOG_FILE,
    when="midnight",
    interval=1,
    backupCount=7,
    encoding="utf-8"
)
sqlalchemy_file_handler = TimedRotatingFileHandler(
    filename=SQLALCHEMY_LOG_FILE,
    when="midnight",
    interval=1,
    backupCount=7,
    encoding="utf-8"
)

# 设置格式
console_handler.setFormatter(logging.Formatter(
    "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
))
file_handler.setFormatter(logging.Formatter(
    "%(asctime)s [%(levelname)s] %(name)s [%(pathname)s:%(lineno)d]: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
))
sqlalchemy_file_handler.setFormatter(logging.Formatter(
    "%(asctime)s [%(levelname)s] %(name)s [%(pathname)s:%(lineno)d]: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
))

# 设置级别
console_handler.setLevel(LOG_LEVEL)
file_handler.setLevel(LOG_LEVEL)
sqlalchemy_file_handler.setLevel(SQLALCHEMY_LEVEL)

# 创建 QueueListener 并启动
listener = QueueListener(
    log_queue,
    console_handler,
    file_handler,
    sqlalchemy_file_handler,
    respect_handler_level=True
)
listener.start()

# 创建自定义 QueueHandler 类，解决 Python 3.12 中的兼容性问题
class CustomQueueHandler(QueueHandler):
    def __init__(self, queue):
        super().__init__(queue)

# 使用自定义 QueueHandler 创建实例
queue_handler = CustomQueueHandler(log_queue)

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "console_formatter": {
            "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
        "file_formatter": {
            "format": "%(asctime)s [%(levelname)s] %(name)s [%(pathname)s:%(lineno)d]: %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": LOG_LEVEL,
            "formatter": "console_formatter",
        },
        "file": {
            "class": "logging.handlers.TimedRotatingFileHandler",
            "level": LOG_LEVEL,
            "formatter": "file_formatter",
            "filename": LOG_FILE,
            "when": "midnight",
            "interval": 1,
            "backupCount": 7,
            "encoding": "utf-8",
        },
        "sqlalchemy_file": {
            "class": "logging.handlers.TimedRotatingFileHandler",
            "level": SQLALCHEMY_LEVEL,
            "formatter": "file_formatter",
            "filename": SQLALCHEMY_LOG_FILE,
            "when": "midnight",
            "interval": 1,
            "backupCount": 7,
            "encoding": "utf-8",
        },
        "queue": {
            "()": "app.core.log_config.CustomQueueHandler",
            "queue": log_queue,
        },
    },
    "loggers": {
        "": {
            "handlers": ["queue"],
            "level": LOG_LEVEL,
            "propagate": True,
        },
        "sqlalchemy.engine": {
            "handlers": ["queue"],
            "level": SQLALCHEMY_LEVEL,
            "propagate": False,
        },
        "uvicorn.access": {
            "handlers": ["queue"],
            "level": LOG_LEVEL,
            "propagate": False,
        },
    },
}

def setup_logging():
    """应用日志配置"""
    dictConfig(LOGGING_CONFIG)


def shutdown_logging():
    """关闭日志监听器"""
    listener.stop()