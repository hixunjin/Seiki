from typing import TypeVar, Generic, Optional, Any, List, Dict, Callable
from fastapi import Response, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from math import ceil
from sqlalchemy import func, select
from sqlalchemy.orm import Query
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.encoders import jsonable_encoder
from app.exceptions.http_exceptions import APIException

T = TypeVar('T')


class PaginatedData(BaseModel, Generic[T]):
    """Paginated data structure"""
    items: List[T]
    total: int
    per_page: int
    current_page: int
    last_page: int
    has_more: bool


class ApiResponse:
    """API response handler class"""

    @staticmethod
    def success(
            data: Any = None,
            message: str = "Success",
            body_code: int = 200,  # Business success code, 0 indicates success
            http_code: int = status.HTTP_200_OK,
            headers: Dict = None
    ) -> JSONResponse:
        """Success response"""
        response_data = {
            "code": body_code,  # Business code
            "message": message,
            "data": jsonable_encoder(data) if data is not None else None
        }
        return JSONResponse(
            content=response_data,
            status_code=http_code,
            headers=headers
        )

    @staticmethod
    def success_without_data(
            http_code: int = status.HTTP_204_NO_CONTENT,
            headers: Dict = None
    ) -> Response:
        """Success response without data"""
        return Response(status_code=http_code, headers=headers)

    @staticmethod
    def failed(
            message: str,
            body_code: int,
            http_code: int = status.HTTP_400_BAD_REQUEST,
            data: Any = None,
            headers: Dict = None
    ) -> JSONResponse:
        """Failed response"""
        response_data = {
            "code": body_code,
            "message": message
        }
        if data is not None:  # Only add field when data is not None
            response_data["data"] = jsonable_encoder(data)
        return JSONResponse(
            content=response_data,
            status_code=http_code,
            headers=headers
        )

    async def paginate(
        db: AsyncSession,
        query,
        page: int = 1,
        per_page: int = 10,
        transform_func: Optional[Callable[[List[Any]], List[Any]]] = None,
        message: str = "Success",
        body_code: int = 200,
        http_code: int = status.HTTP_200_OK,
        headers: Dict = None
    ) -> JSONResponse:
        """Optimized pagination response method"""
        # Input validation
        if page < 1 or per_page < 1:
            raise APIException(status_code=400, message="Invalid page or per_page parameter")
        
        # Optimize total count query
        total_query = select(func.count()).select_from(query.subquery())
        total = await db.scalar(total_query)
        
        # Calculate pagination parameters
        last_page = ceil(total / per_page) if per_page > 0 else 0
        
        # Validate if page number exceeds range
        if page > last_page and last_page > 0:
            raise APIException(status_code=404, message="Page not found")
        
        # Execute paginated query
        offset_query = query.offset((page - 1) * per_page).limit(per_page)
        result = await db.execute(offset_query)
        items = result.scalars().all()
        
        # Optional data transformation
        if transform_func is not None:
            items = transform_func(items)
        
        # Build paginated data
        paginated_data = PaginatedData(
            items=items,
            total=total,
            per_page=per_page,
            current_page=page,
            last_page=last_page,
            has_more=page < last_page
        )
        
        return JSONResponse(
            content={
                "code": body_code,
                "message": message,
                "data": jsonable_encoder(paginated_data)
            },
            status_code=http_code,
            headers=headers
        )
