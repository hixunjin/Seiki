"""
Client端 Swagger UI 配置文件
专门用于客户端API文档
"""

from typing import Dict, Any
from app.core.config import settings

# Client Swagger UI 配置
CLIENT_SWAGGER_UI_PARAMETERS = {
    "deepLinking": True,
    "displayRequestDuration": True,
    "docExpansion": "list",  # 展开标签但不展开操作
    "operationsSorter": "alpha",  # 按字母排序
    "filter": True,
    "tryItOutEnabled": True,
}

# Client OpenAPI 元数据配置
CLIENT_OPENAPI_INFO = {
    "title": f"{settings.PROJECT_NAME} - 客户端API",
    "description": f"""
# 客户端API服务

这是面向客户端应用的公共API接口文档。

## 功能模块

### 演示功能 (Demo)
- 基础演示接口
- 功能测试接口

### 配置管理 (Config)
- 客户端配置获取
- 系统配置查询

### 云存储服务 (AWS)
- 文件上传功能
- S3存储集成

## 技术特性

- 🚀 **高性能**: 基于FastAPI异步框架
- 📊 **数据库**: PostgreSQL + SQLAlchemy ORM
- 🎯 **缓存**: Redis缓存系统
- ☁️ **云存储**: AWS S3集成
- 📝 **文档**: 自动生成的OpenAPI文档
- ⚡ **异步**: 全异步处理提升性能

## 响应格式

所有API响应都遵循统一的格式：

```json
{{
    "success": true,
    "message": "操作成功", 
    "data": {{}},
    "code": 200
}}
```

## 环境信息

- **当前环境**: {settings.ENV}
- **API版本**: v1
- **文档类型**: 客户端API
    """,
    "version": "1.0.0",
    "contact": {
        "name": "开发团队",
        "email": settings.ADMIN_EMAIL,
    },
    "license_info": {
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    },
}

# Client OpenAPI 标签配置
CLIENT_OPENAPI_TAGS = [
    {
        "name": "client-demo",
        "description": "客户端演示接口",
        "externalDocs": {
            "description": "了解更多",
            "url": "https://fastapi.tiangolo.com/",
        },
    },
    {
        "name": "client-config",
        "description": "客户端配置接口",
        "externalDocs": {
            "description": "配置说明",
            "url": "https://fastapi.tiangolo.com/tutorial/",
        },
    },
    {
        "name": "client-aws",
        "description": "客户端云存储接口",
        "externalDocs": {
            "description": "AWS S3文档",
            "url": "https://docs.aws.amazon.com/s3/",
        },
    },
]

def get_client_openapi_config() -> Dict[str, Any]:
    """
    获取客户端OpenAPI配置
    """
    return {
        **CLIENT_OPENAPI_INFO,
        "openapi": "3.0.2",
        "tags": CLIENT_OPENAPI_TAGS,
    }