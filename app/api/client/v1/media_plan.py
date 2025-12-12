from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.client.deps import get_current_user
from app.db.session import get_db, transaction
from app.models.media_plan import MediaPlan, MediaPlanCampaign
from app.models.campaign import Campaign
from app.models.user import User
from app.schemas.client.media_plan import (
    MediaPlanCreate,
    MediaPlanUpdate,
    MediaPlanResponse,
    MediaPlanListFilter,
    MediaPlanStatus,
    MediaPlanDetailResponse,
)
from app.schemas.response import ApiResponse
from app.services.client.media_plan import media_plan_service

router = APIRouter()


@router.post("", response_model=MediaPlanResponse)
async def create_media_plan(
    data: MediaPlanCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new media plan with selected campaigns."""
    async with transaction(db):
        result = await media_plan_service.create_media_plan(
            db=db,
            current_user=current_user,
            data=data,
        )
        return ApiResponse.success(data=result)


@router.get("")
async def list_media_plans(
    filters: MediaPlanListFilter = Depends(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List media plans with filters and pagination.

    Return Fields：
    - id
    - name
    - description
    - budget
    - start_date / end_date: 计划下所有活动的最早开始和最晚结束时间
    - status: active / upcoming / completed
    - campaigns_count: 关联的活动数量
    - operator_first_name / operator_last_name: 创建人姓名
    - created_at / updated_at
    """

    # 聚合查询：计算每个媒体计划的 start_date / end_date / campaigns_count
    query = (
        select(
            MediaPlan,
            func.min(Campaign.start_date).label("start_date"),
            func.max(Campaign.end_date).label("end_date"),
            func.count(Campaign.id).label("campaigns_count"),
            User.first_name.label("operator_first_name"),
            User.last_name.label("operator_last_name"),
        )
        .outerjoin(MediaPlanCampaign, MediaPlan.id == MediaPlanCampaign.media_plan_id)
        .outerjoin(Campaign, Campaign.id == MediaPlanCampaign.campaign_id)
        .outerjoin(User, User.id == MediaPlan.created_by)
        .group_by(MediaPlan.id, User.first_name, User.last_name)
        .order_by(MediaPlan.created_at.desc())
    )

    # 1) 名称模糊查询
    if filters.keyword:
        kw = f"%{filters.keyword.strip()}%"
        query = query.where(MediaPlan.name.ilike(kw))

    # 2) 日期范围：between and，包含端点
    # start_date_filter <= plan.start_date AND plan.end_date <= end_date_filter
    if filters.start_date:
        query = query.having(func.min(Campaign.start_date) >= filters.start_date)
    if filters.end_date:
        query = query.having(func.max(Campaign.end_date) <= filters.end_date)

    # 3) 状态筛选（基于聚合出来的 start_date / end_date 与今天比较）
    today = datetime.utcnow().date()
    if filters.status == MediaPlanStatus.ACTIVE:
        query = query.having(
            func.min(Campaign.start_date) <= today,
            func.max(Campaign.end_date) >= today,
        )
    elif filters.status == MediaPlanStatus.UPCOMING:
        query = query.having(func.min(Campaign.start_date) > today)
    elif filters.status == MediaPlanStatus.COMPLETED:
        query = query.having(func.max(Campaign.end_date) < today)

    def transform(items):
        result = []
        for mp in items:
            start_date = getattr(mp, "start_date", None)
            end_date = getattr(mp, "end_date", None)
            campaigns_count = getattr(mp, "campaigns_count", 0) or 0
            operator_first_name = getattr(mp, "operator_first_name", None)
            operator_last_name = getattr(mp, "operator_last_name", None)

            # 计算状态（与创建接口保持一致）
            status_value: str | None = None
            if start_date and end_date:
                if start_date > today:
                    status_value = MediaPlanStatus.UPCOMING.value
                elif end_date < today:
                    status_value = MediaPlanStatus.COMPLETED.value
                else:
                    status_value = MediaPlanStatus.ACTIVE.value

            result.append(
                {
                    "id": mp.id,
                    "name": mp.name,
                    "description": mp.description,
                    "budget": mp.budget,
                    "start_date": start_date,
                    "end_date": end_date,
                    "status": status_value,
                    "campaigns_count": campaigns_count,
                    "operator_first_name": operator_first_name,
                    "operator_last_name": operator_last_name,
                    "created_at": mp.created_at,
                    "updated_at": mp.updated_at,
                }
            )

        return result

    return await ApiResponse.paginate(
        db=db,
        query=query,
        page=filters.page,
        per_page=filters.per_page,
        transform_func=transform,
    )


@router.get("/{media_plan_id}", response_model=MediaPlanDetailResponse)
async def get_media_plan_detail(
    media_plan_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get media plan detail by id, including campaign name list."""

    result = await media_plan_service.get_media_plan_detail(
        db=db,
        current_user=current_user,
        media_plan_id=media_plan_id,
    )
    return ApiResponse.success(data=result)


@router.put("/{media_plan_id}", response_model=MediaPlanResponse)
async def update_media_plan(
    media_plan_id: int,
    data: MediaPlanUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a media plan by id.

    All fields can be updated, including the list of campaigns.
    """
    async with transaction(db):
        result = await media_plan_service.update_media_plan(
            db=db,
            current_user=current_user,
            media_plan_id=media_plan_id,
            data=data,
        )
        return ApiResponse.success(data=result)


@router.delete("/{media_plan_id}")
async def delete_media_plan(
    media_plan_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a media plan by id.

    Campaigns will NOT be deleted, only the association is removed.
    """
    async with transaction(db):
        await media_plan_service.delete_media_plan(
            db=db,
            current_user=current_user,
            media_plan_id=media_plan_id,
        )
        return ApiResponse.success(message="Media plan deleted successfully")
