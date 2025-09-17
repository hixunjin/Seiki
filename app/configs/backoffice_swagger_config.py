"""
Backoffice端 Swagger UI 配置文件
专门用于后台管理API文档
"""

from typing import Dict, Any
from app.core.config import settings

# Backoffice Swagger UI 配置
BACKOFFICE_SWAGGER_UI_PARAMETERS = {
    "deepLinking": True,
    "displayRequestDuration": True,
    "docExpansion": "list",  # 展开标签但不展开操作
    "operationsSorter": "alpha",  # 按字母排序
    "filter": True,
    "tryItOutEnabled": True,
}

# Backoffice OpenAPI 元数据配置
BACKOFFICE_OPENAPI_INFO = {
    "title": f"{settings.PROJECT_NAME} - 后台管理API",
    "description": f"""
# 后台管理API服务

这是面向后台管理系统的内部API接口文档。

## 功能模块

### 认证管理 (Auth)
- 管理员登录/登出
- JWT令牌管理
- 刷新令牌操作

### 管理员管理 (Admin)
- 管理员账户CRUD操作
- 权限管理
- 用户信息维护
- 密码管理功能

### 云存储管理 (AWS)
- 文件管理功能
- S3存储操作
- 上传权限控制

## 认证说明

⚠️ **所有后台接口都需要JWT认证**（除了登录接口）

### 如何使用认证：
1. 调用 `/login` 接口获取访问令牌
2. 点击右上角 🔒 **Authorize** 按钮
3. 在输入框中填入：`Bearer 你的访问令牌`
4. 点击 **Authorize** 完成认证设置

## 技术特性

- 🔒 **安全**: JWT认证 + 权限控制
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

## 错误码说明

- **400**: 参数错误（显示给用户）
- **401**: 认证失败
- **403**: 权限不足
- **404**: 资源不存在
- **500**: 服务器错误

## 环境信息

- **当前环境**: {settings.ENV}
- **API版本**: v1
- **文档类型**: 后台管理API
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

# Backoffice OpenAPI 标签配置
BACKOFFICE_OPENAPI_TAGS = [
    {
        "name": "backoffice-auth",
        "description": "后台认证接口",
        "externalDocs": {
            "description": "认证文档",
            "url": "https://fastapi.tiangolo.com/tutorial/security/",
        },
    },
    {
        "name": "backoffice-admin",
        "description": "后台管理员接口",
        "externalDocs": {
            "description": "管理员文档",
            "url": "https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/",
        },
    },
    {
        "name": "backoffice-aws",
        "description": "后台云存储管理",
        "externalDocs": {
            "description": "AWS管理文档",
            "url": "https://docs.aws.amazon.com/s3/",
        },
    },
]

# JWT认证配置
BACKOFFICE_SECURITY_SCHEMES = {
    "BearerAuth": {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT",
        "description": "JWT认证令牌，格式：Bearer {token}。请先通过登录接口获取令牌。",
    }
}

def get_backoffice_openapi_config() -> Dict[str, Any]:
    """
    获取后台管理OpenAPI配置
    """
    return {
        **BACKOFFICE_OPENAPI_INFO,
        "openapi": "3.0.2",
        "tags": BACKOFFICE_OPENAPI_TAGS,
        "components": {
            "securitySchemes": BACKOFFICE_SECURITY_SCHEMES
        },
    }