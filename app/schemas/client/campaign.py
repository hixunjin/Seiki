from __future__ import annotations

from datetime import date
from enum import Enum
from typing import List, Optional

from pydantic import Field

from app.schemas.base import BaseSchema, BaseResponseSchema


class Gender(str, Enum):
    ALL = "all"
    MALE = "male"
    FEMALE = "female"


class SocioProfessionalCategory(str, Enum):
    CSP_PLUS = "CSP_PLUS"
    CSP_MINUS = "CSP_MINUS"
    OTHER = "OTHER"


class CampaignStatus(str, Enum):
    """Computed campaign status for filtering and display."""

    ACTIVE = "active"
    UPCOMING = "upcoming"
    COMPLETED = "completed"


class CampaignCreate(BaseSchema):
    """Payload for creating a campaign (活动)."""

    # 基础信息
    name: str = Field(..., max_length=255)
    price_eur: int = Field(..., ge=0)
    description: Optional[str] = None

    # 时间
    start_date: date
    end_date: date

    # 地理
    country_code: str = Field("SA", max_length=2)
    city: Optional[str] = Field(None, max_length=100)

    # 人群
    gender: Gender = Gender.ALL
    age_ranges: Optional[List[str]] = None

    # 社会职业 & 出行 & 兴趣点
    socio_professional_category: Optional[SocioProfessionalCategory] = None
    mobility_modes: Optional[List[str]] = None
    poi_categories: Optional[List[str]] = None

    # 选择的广告牌 ID 列表
    inventory_ids: List[int] = Field(default_factory=list)


class CampaignResponse(BaseResponseSchema):
    """Basic campaign response with selected billboard count."""

    name: str
    price_eur: int
    description: Optional[str]

    start_date: date
    end_date: date

    country_code: str
    city: Optional[str]

    gender: Gender
    age_ranges: Optional[List[str]]

    socio_professional_category: Optional[SocioProfessionalCategory]
    mobility_modes: Optional[List[str]]
    poi_categories: Optional[List[str]]

    # 该活动下关联的广告牌数量
    billboard_count: int = 0


class CampaignDetailResponse(CampaignResponse):
    """Campaign detail response including billboard ids and KPI data."""

    billboard_ids: List[int] = Field(default_factory=list)
    kpi_data: dict | None = None


class CampaignUpdate(BaseSchema):
    """Payload for updating a campaign (活动).

    All fields except country_code can be updated.
    country_code is fixed to 'SA' and cannot be changed.
    """

    # 基础信息
    name: str = Field(..., max_length=255)
    price_eur: int = Field(..., ge=0)
    description: Optional[str] = None

    # 时间
    start_date: date
    end_date: date

    # 地理 (city only, country_code is fixed)
    city: Optional[str] = Field(None, max_length=100)

    # 人群
    gender: Gender = Gender.ALL
    age_ranges: Optional[List[str]] = None

    # 社会职业 & 出行 & 兴趣点
    socio_professional_category: Optional[SocioProfessionalCategory] = None
    mobility_modes: Optional[List[str]] = None
    poi_categories: Optional[List[str]] = None

    # 选择的广告牌 ID 列表
    inventory_ids: List[int] = Field(default_factory=list)


class CampaignListFilter(BaseSchema):
    """Filters for campaign list endpoint with pagination."""

    keyword: Optional[str] = None
    status: Optional[CampaignStatus] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None

    page: int = 1
    per_page: int = 10

