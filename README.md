# FastAPI Template

> 基于 FastAPI 的现代化企业级 Web API 模板项目

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115.12-009688.svg)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.12+-3776ab.svg)](https://www.python.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-336791.svg)](https://www.postgresql.org)
[![Redis](https://img.shields.io/badge/Redis-7+-dc382d.svg)](https://redis.io)
[![Docker](https://img.shields.io/badge/Docker-支持-2496ed.svg)](https://www.docker.com)

## 🚀 项目特色

### 核心架构
- **双客户端架构**: 分离的客户端 API 和后台管理 API
- **分离式文档**: 独立的 Swagger 文档系统，环境控制访问
- **异步优先**: 全异步架构，高并发处理能力
- **企业级设计**: 完整的认证、权限、监控体系

### 技术栈
- 🏗️ **Web 框架**: FastAPI 0.115.12 (高性能异步框架)
- 🗄️ **数据库**: PostgreSQL + SQLAlchemy 2.0 (异步 ORM)
- 🔄 **缓存**: Redis 7+ (缓存 + 消息队列)
- ⚡ **后台任务**: Celery 5.5.1 (分布式任务队列)
- 🔐 **认证**: JWT 认证 + 权限管理
- ☁️ **云存储**: AWS S3 集成
- 📧 **邮件服务**: SMTP / Brevo API 支持
- 🐳 **容器化**: Docker + Docker Compose

### 开发特性
- 📊 **智能监控**: 健康检查 + 结构化日志
- 🧪 **完整测试**: 单元测试 + 集成测试框架
- 📝 **API 导出**: OpenAPI 3.0 JSON 导出功能
- 🔧 **开发工具**: 热重载 + 调试支持
- 📚 **完整文档**: 架构文档 + 开发指南

## 📋 快速开始

### 环境要求

- Python 3.12+
- Docker & Docker Compose
- PostgreSQL 15+ (可选，可使用 Docker)
- Redis 7+ (可选，可使用 Docker)

### 1. 克隆项目

```bash
git clone <repository-url>
cd fastapi-template
```

### 2. 环境配置

```bash
# 复制环境配置文件
cp .env.example .env

# 编辑配置文件
vim .env
```

**必需的环境变量**:
```env
# 环境设置
ENV=development

# 数据库配置
POSTGRES_USER=demo
POSTGRES_PASSWORD=demo123
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=demo

# Redis 配置
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=

# JWT 密钥
SECRET_KEY=your-secret-key-here

# AWS 配置 (可选)
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_REGION=us-east-1
AWS_BUCKET_NAME=your-bucket

# 邮件配置 (可选)
ADMIN_EMAIL=admin@example.com
```

### 3. Docker 启动 (推荐)

```bash
# 启动所有服务
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f fastapi-app
```

### 4. 本地开发启动

```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate     # Windows

# 安装依赖
pip install -r requirements.txt

# 运行数据库迁移
alembic upgrade head

# 启动开发服务器
python main.py
```

### 5. 验证安装

访问以下地址验证安装成功：

- **健康检查**: http://localhost:8001/api/v1/config/health
- **文档导航**: http://localhost:8001/ (仅开发环境)

## 📖 API 文档

### 文档访问地址

| 文档类型 | 地址 | 描述 |
|---------|------|------|
| 🏠 **根导航** | http://localhost:8001/ | 开发环境文档导航 |
| 📱 **客户端 Swagger** | http://localhost:8001/client/docs | 客户端 API 交互式文档 |
| 📱 **客户端 ReDoc** | http://localhost:8001/client/redoc | 客户端 API 阅读文档 |
| 🔧 **后台 Swagger** | http://localhost:8001/backoffice/docs | 后台管理 API 文档 |
| 🔧 **后台 ReDoc** | http://localhost:8001/backoffice/redoc | 后台管理 API 阅读文档 |
| 💾 **API 导出** | http://localhost:8001/api-docs/ | OpenAPI JSON 导出 |

### 环境控制

- **开发环境** (`ENV=development`): 显示完整文档导航
- **生产环境** (`ENV=production`): 隐藏文档导航，提高安全性
- **预览环境** (`ENV=preview`): 与开发环境相同

### 认证使用

**客户端 API**: 无需认证，直接测试

**后台管理 API**: 需要 JWT 认证
1. 访问 `/api/v1/backoffice/auth/login` 获取 token
2. 在 Swagger UI 右上角点击 🔒 **Authorize**
3. 输入: `Bearer <your-token>`
4. 完成认证后即可测试所有后台接口

## 🏗️ 项目架构

### 目录结构

```
fastapi-template/
├── app/                          # 主应用目录
│   ├── api/                      # API 路由层
│   │   ├── client/v1/            # 客户端 API v1
│   │   ├── backoffice/v1/        # 后台管理 API v1
│   │   └── docs_export.py        # API 文档导出
│   ├── core/                     # 核心系统配置
│   │   ├── config.py             # 环境配置
│   │   ├── security.py           # 安全配置
│   │   └── log_config.py         # 日志配置
│   ├── configs/                  # 应用配置
│   │   ├── client_swagger_config.py      # 客户端 Swagger 配置
│   │   ├── backoffice_swagger_config.py  # 后台 Swagger 配置
│   │   └── docs_apps.py          # 文档应用配置
│   ├── route/                    # 路由管理
│   │   ├── route.py              # 主路由配置
│   │   └── router_registry.py    # 路由注册中心
│   ├── models/                   # 数据模型
│   ├── schemas/                  # Pydantic 模式
│   ├── services/                 # 业务逻辑层
│   ├── db/                       # 数据库层
│   └── utils/                    # 工具函数
├── docs/                         # 项目文档
│   ├── architecture/             # 架构文档
│   ├── development/              # 开发文档
│   └── api/                      # API 文档
├── migrations/                   # 数据库迁移
├── logs/                         # 日志文件
├── docker-compose.yml            # Docker 编排
├── requirements.txt              # Python 依赖
└── main.py                       # 应用入口
```

### 架构特点

- **分层架构**: API → Service → Model 清晰分层
- **依赖注入**: 服务层依赖注入，提高测试性
- **事务管理**: 业务逻辑层统一事务边界
- **路由注册**: 中心化路由管理，避免重复配置
- **环境隔离**: 开发/生产环境配置分离

## 🚀 部署指南

### Docker 部署 (推荐)

```bash
# 生产环境启动
ENV=production docker-compose up -d

# 扩展服务实例
docker-compose up -d --scale fastapi-app=3

# 更新部署
docker-compose pull
docker-compose up -d --force-recreate
```

### 传统部署

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 设置环境变量
export ENV=production
export POSTGRES_HOST=your-db-host
# ... 其他环境变量

# 3. 运行迁移
alembic upgrade head

# 4. 启动服务
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8001
```

### Nginx 配置示例

```nginx
upstream fastapi_backend {
    server 127.0.0.1:8001;
}

server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://fastapi_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # 生产环境隐藏文档访问 (可选)
    location ~ ^/(client|backoffice|api-docs) {
        deny all;
        return 404;
    }
}
```

## 🔧 开发指南

### 添加新的 API 接口

1. **创建路由文件** (`app/api/client/v1/new_module.py`):
```python
from fastapi import APIRouter, Depends
from app.schemas.response import ApiResponse

router = APIRouter()

@router.get("/example")
async def example_endpoint():
    return ApiResponse.success(data={"message": "Hello World"})
```

2. **注册路由** (`app/route/router_registry.py`):
```python
def get_client_routes():
    return [
        # 现有路由...
        RouteConfig("app.api.client.v1.new_module", "/new-module", ["new-module"]),
    ]
```

3. **更新 Swagger 配置** (`app/configs/client_swagger_config.py`):
```python
CLIENT_OPENAPI_TAGS = [
    # 现有标签...
    {
        "name": "new-module",
        "description": "新模块接口",
        "externalDocs": {
            "description": "模块文档",
            "url": "https://example.com/docs",
        },
    },
]
```

### 数据库操作

```bash
# 创建新迁移
alembic revision --autogenerate -m "description"

# 应用迁移
alembic upgrade head

# 回滚迁移
alembic downgrade -1
```

### 后台任务

```bash
# 启动 Celery Worker
celery -A app.core.celery_app worker --loglevel=info

# 启动 Celery Beat (定时任务)
celery -A app.core.celery_app beat --loglevel=info

# 监控 Celery (可选)
celery -A app.core.celery_app flower
```

## 🧪 测试

### 运行测试

```bash
# 安装测试依赖
pip install pytest pytest-asyncio httpx

# 运行所有测试
pytest

# 运行特定测试
pytest tests/test_api.py

# 生成覆盖率报告
pytest --cov=app tests/
```

### API 测试示例

```python
import pytest
from fastapi.testclient import TestClient
from app.route.route import create_app

@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)

def test_health_check(client):
    response = client.get("/api/v1/config/health")
    assert response.status_code == 200
    assert response.json()["data"]["status"] == "healthy"
```

## 📊 监控和日志

### 健康检查

系统提供多层健康检查：

- **API 健康**: 基础服务状态
- **数据库健康**: PostgreSQL 连接状态
- **Redis 健康**: 缓存服务状态

访问: http://localhost:8001/api/v1/config/health

### 日志系统

- **结构化日志**: JSON 格式，便于分析
- **日志轮转**: 按日分割，保留 7 天
- **异步写入**: Redis 队列，性能优化
- **分类存储**: 应用日志和 SQL 日志分离

日志位置: `logs/` 目录

### 性能监控

- **请求响应时间**: 自动记录 API 响应时间
- **错误率监控**: 实时错误统计
- **资源使用**: 数据库连接池状态

## 🔒 安全特性

### 认证和授权

- **JWT 认证**: 安全的令牌认证机制
- **Token 刷新**: 自动令牌续期
- **权限控制**: 基于角色的访问控制

### 安全配置

- **CORS 控制**: 跨域资源共享配置
- **数据验证**: Pydantic 严格数据验证
- **SQL 注入防护**: SQLAlchemy ORM 安全保护
- **环境隔离**: 敏感信息环境变量管理

### 生产安全

- **文档隐藏**: 生产环境自动隐藏 API 文档
- **错误处理**: 统一错误响应格式
- **日志安全**: 敏感信息过滤

## 🤝 贡献指南

### 开发流程

1. Fork 项目到个人仓库
2. 创建功能分支: `git checkout -b feature/new-feature`
3. 提交代码: `git commit -m 'Add new feature'`
4. 推送到分支: `git push origin feature/new-feature`
5. 创建 Pull Request

### 代码规范

- **Python**: 遵循 PEP 8 规范
- **命名约定**:
  - 函数和变量: `snake_case`
  - 路由和枚举: `kebab-case`
  - 类名: `PascalCase`
- **类型注解**: 必须添加类型注解
- **文档字符串**: 公共函数必须有文档说明

### 提交规范

- `feat`: 新功能
- `fix`: 错误修复
- `docs`: 文档更新
- `style`: 代码格式调整
- `refactor`: 重构
- `test`: 测试相关
- `chore`: 构建或辅助工具的变动

## 📚 文档链接

### 项目文档

- [项目架构文档](docs/architecture/project-architecture.md)
- [开发框架指南](docs/development/development-framework.md)
- [Swagger 使用指南](docs/api/swagger-guide.md)
- [Claude 开发指引](CLAUDE.md)

### 相关技术文档

- [FastAPI 官方文档](https://fastapi.tiangolo.com/)
- [SQLAlchemy 2.0 文档](https://docs.sqlalchemy.org/en/20/)
- [Celery 文档](https://docs.celeryproject.org/)
- [Docker 使用指南](https://docs.docker.com/)
- [PostgreSQL 文档](https://www.postgresql.org/docs/)

## 📄 许可证

本项目基于 [MIT License](https://opensource.org/licenses/MIT) 开源协议。

## 🚨 常见问题

### Q1: Docker 容器启动失败？
- 检查端口占用: `lsof -i :8001`
- 查看容器日志: `docker-compose logs fastapi-app`
- 确认环境变量配置正确

### Q2: 数据库连接失败？
- 检查 PostgreSQL 服务状态
- 验证数据库连接参数
- 确认网络连通性

### Q3: Swagger 文档无法访问？
- 确认服务启动在正确端口 (8001)
- 检查环境变量 `ENV` 设置
- 验证 OpenAPI JSON 端点: `/client/openapi.json`

### Q4: Redis 连接错误？
- 检查 Redis 服务状态
- 验证 Redis 连接参数
- 确认防火墙设置

### Q5: Celery 任务不执行？
- 确认 Redis 作为 broker 正常运行
- 检查 Celery worker 启动状态
- 查看 Celery 日志输出

---

📧 **联系我们**: 如有问题或建议，请通过 Issues 或邮件联系开发团队。

🌟 **Star 支持**: 如果这个项目对您有帮助，请给我们一个 Star！