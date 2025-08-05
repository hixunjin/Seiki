# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Global Development Rules

### Code Style & Formatting
- Use underscores for function and variable names (`function_name`, `variable_name`)
- Use hyphens for routes and enum labels (`route-name`, `enum-label`)
- Use modern, non-deprecated syntax when writing code
- Use timestamp type consistently for time fields in database design

### Design Patterns
- Obtain service layer instances using dependency injection to improve testability and flexibility
- Place database model conversion in the service layer to keep the routing layer clean
- Handle transactions in the service layer to align business logic with transaction boundaries

### Language Guidelines
- Use English for all code comments and documentation
- Answer questions in Chinese when requested by the user

## Development Commands

### Virtual Environment (CRITICAL)
- **ALWAYS activate virtual environment first**: `source venv/bin/activate`
- **Command format**: `source venv/bin/activate && python script.py`
- This applies to ALL Python operations: scripts, tests, migrations, etc.

### Server

- **Start development server**: `source venv/bin/activate && python main.py` (runs on port 8001 with hot reload)
- **Start production server**: Set `ENV=production` in .env, then `source venv/bin/activate && python main.py`

### Database

- **Run migrations**: `source venv/bin/activate && alembic upgrade head`
- **Create new migration**: `source venv/bin/activate && alembic revision --autogenerate -m "migration_name"`
- **Downgrade migration**: `source venv/bin/activate && alembic downgrade -1`

### Background Tasks

- **Start Celery worker**: `source venv/bin/activate && python celery_worker.py`
- **Start Celery beat (scheduler)**: `source venv/bin/activate && celery -A app.core.celery_app beat --loglevel=info`
- **Monitor Celery**: `source venv/bin/activate && celery -A app.core.celery_app flower`

## Architecture Overview

### API Structure

The API follows a dual-client architecture pattern:

- **Client API** (`/api/v1/`): Public-facing endpoints for client applications
- **Backoffice API** (`/api/v1/backoffice/`): Admin/management endpoints with authentication

### Core Components

#### Application Layer (`app/`)

- **`route/route.py`**: Main FastAPI app factory with middleware, CORS, and global exception handlers
- **`core/config.py`**: Environment-based configuration using Pydantic Settings (MySQL, Redis, Celery, JWT, AWS S3, Email)
- **`core/celery_app.py`**: Celery configuration for background tasks with Redis broker

#### Data Layer

- **`db/`**: SQLAlchemy async setup with session management and transaction contexts
  - `base.py`: Database connection setup
  - `session.py`: General transaction management and asynchronous sessions
- **`models/`**: SQLAlchemy ORM models inheriting from BaseModel (includes id, created_at, updated_at)
- **`migrations/`**: Alembic database migrations

#### Business Logic

- **`services/`**: Business logic separated by client/backoffice domains
- **`schemas/`**: Pydantic models for request/response validation
  - `response.py`: Unified response format using `ApiResponse`
  - `paginator.py`: Pagination utilities
- **`api/`**: Route handlers organized by client/backoffice and versioned (v1)

#### Background Processing

- **`schedule/`**: Celery task definitions and job scheduling
- **`schedule/jobs/`**: Individual scheduled task implementations

### Response Design

#### Unified Response Format

- **ALWAYS use `ApiResponse`** from `app.schemas.response` (NOT `SuccessResponse`)
- For pagination, refer to `paginator.py`

```python
from app.schemas.response import ApiResponse  # ✓ Correct

return ApiResponse.success(data=result)
```

#### Exception Handling

- Use `APIException` from `app.exceptions.http_exceptions.py` for standardized exception responses

#### HTTP Status Code Guidelines

- **400 (Bad Request)**: User-facing errors that should be displayed to users
  - Validation errors, missing required fields, invalid input formats
  - These error messages will be shown directly to users in the frontend
- **404 (Not Found)**: Resource not found errors (NOT displayed to users)
- **500 (Internal Server Error)**: System/server errors (NOT displayed to users)

**Important**: Only 400 status code errors are displayed to end users.

### Service Layer Pattern

```python
# In route handler
@router.post("/example")
async def example_handler(
    service: ExampleService = Depends(get_example_service),  # Dependency injection
    db: AsyncSession = Depends(get_db)
):
    result = await service.process_data(db)  # Business logic in service
    return ApiResponse.success(data=result)

# In service layer
async def process_data(self, db: AsyncSession):
    async with transaction(db):  # Transaction in service layer
        # Business logic here
        pass
```

### Key Dependencies

- **FastAPI**: Web framework with OpenAPI documentation
- **SQLAlchemy**: Async ORM with MySQL backend
- **Alembic**: Database migrations
- **Celery**: Background task processing with Redis broker
- **Pydantic**: Data validation and settings management
- **Redis**: Caching and Celery broker
- **JWT**: Authentication using python-jose
- **AWS SDK**: S3 integration via boto3

### Configuration Requirements

Environment variables needed in `.env`:

- Database: `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_DB`
- Redis: `REDIS_HOST`, `REDIS_PORT`, `REDIS_PASSWORD`
- JWT: `SECRET_KEY`
- AWS: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION`, `AWS_BUCKET_NAME`
- Email: Mail server or Brevo API credentials

### File Organization Rules

- **Temporary scripts**: Place in `shell/` directory (test scripts, analysis scripts, debugging files)
- **Documentation**: Place in `doc/` directory (API docs, flow summaries, markdown files)
- **Always check for existing files** before creating new scripts or documentation
- **Clean up unused files** promptly to maintain directory cleanliness
- **Use descriptive names** that clearly indicate purpose and scope

### Logging & Monitoring

- Structured logging with file rotation in `logs/` directory
- Redis-based log aggregation with separate consumer thread
- Master process detection to prevent duplicate background services
