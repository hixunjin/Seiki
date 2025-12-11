from __future__ import annotations

from datetime import date
from enum import Enum
from typing import List, Optional

from pydantic import Field

from app.schemas.base import BaseSchema, BaseResponseSchema


class MediaPlanStatus(str, Enum):
    ACTIVE = "active"
    UPCOMING = "upcoming"
    COMPLETED = "completed"


class MediaPlanCreate(BaseSchema):
    """Payload for creating a media plan."""

    name: str = Field(..., max_length=255)
    budget: Optional[int] = Field(default=None, ge=0)
    description: Optional[str] = None

    # 计划包含的活动 ID 列表
    campaign_ids: List[int] = Field(default_factory=list)


class MediaPlanResponse(BaseResponseSchema):
    """Basic media plan response for list/detail."""

    name: str
    budget: Optional[int]
    description: Optional[str]

    # 从关联活动计算出的总体时间范围
    start_date: Optional[date] = None
    end_date: Optional[date] = None

    status: Optional[MediaPlanStatus] = None
    campaigns_count: int = 0

    operator_first_name: Optional[str] = None
    operator_last_name: Optional[str] = None


class MediaPlanDetailResponse(MediaPlanResponse):
    Campaigns: List[str] = Field(default_factory=list)


class MediaPlanListFilter(BaseSchema):
    """Filters for media plan list endpoint with pagination."""

    # 媒体计划名称模糊查询
    keyword: Optional[str] = None

    # 状态筛选：active / upcoming / completed
    status: Optional[MediaPlanStatus] = None

    # 日期范围筛选：between and，包含端点
    start_date: Optional[date] = None
    end_date: Optional[date] = None

    page: int = 1
    per_page: int = 10
