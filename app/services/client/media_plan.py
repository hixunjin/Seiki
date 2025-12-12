from __future__ import annotations

from datetime import date
from typing import List, Optional, Tuple

from fastapi import status
from sqlalchemy import select, func, delete as sql_delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions.http_exceptions import APIException
from app.models.media_plan import MediaPlan, MediaPlanCampaign
from app.models.campaign import Campaign
from app.models.user import User, TeamRole, OrganizationType
from app.schemas.client.media_plan import (
    MediaPlanCreate,
    MediaPlanUpdate,
    MediaPlanResponse,
    MediaPlanDetailResponse,
    MediaPlanStatus,
)


class MediaPlanService:
    @staticmethod
    def _compute_status(start_date: Optional[date], end_date: Optional[date]) -> Optional[MediaPlanStatus]:
        if not start_date or not end_date:
            return None
        today = date.today()
        if start_date > today:
            return MediaPlanStatus.UPCOMING
        if end_date < today:
            return MediaPlanStatus.COMPLETED
        return MediaPlanStatus.ACTIVE

    @staticmethod
    async def _get_date_range_and_count(
        db: AsyncSession,
        campaign_ids: List[int],
    ) -> Tuple[Optional[date], Optional[date], int]:
        """Compute min(start_date), max(end_date) and count for given campaigns."""
        if not campaign_ids:
            return None, None, 0

        query = select(
            func.min(Campaign.start_date),
            func.max(Campaign.end_date),
            func.count(Campaign.id),
        ).where(Campaign.id.in_(campaign_ids))

        result = await db.execute(query)
        min_start, max_end, count = result.one()
        return min_start, max_end, count or 0

    @staticmethod
    async def create_media_plan(
        db: AsyncSession,
        current_user: User,
        data: MediaPlanCreate,
    ) -> MediaPlanResponse:
        """Create a media plan and link it to selected campaigns."""
        # 权限：与 Campaign 保持一致，只允许 media owner 的 owner/admin
        if current_user.role not in [TeamRole.OWNER.value, TeamRole.ADMIN.value]:
            raise APIException(
                status_code=status.HTTP_403_FORBIDDEN,
                message="Only owner or admin can create media plan",
            )

        org_type_normalized = (current_user.organization_type or "").replace("-", " ").lower()
        media_owner_normalized = OrganizationType.MEDIA_OWNER.value.lower()
        if org_type_normalized != media_owner_normalized:
            raise APIException(
                status_code=status.HTTP_403_FORBIDDEN,
                message="Only media owners can create media plan",
            )

        # 如果有 campaign_ids，先检查是否存在
        campaign_ids = list(set(data.campaign_ids or []))
        if campaign_ids:
            check_query = select(Campaign.id).where(Campaign.id.in_(campaign_ids))
            check_result = await db.execute(check_query)
            existing_ids = {row[0] for row in check_result.all()}
            missing_ids = set(campaign_ids) - existing_ids
            if missing_ids:
                raise APIException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    message=f"Campaigns not found: {sorted(missing_ids)}",
                )
            campaign_ids = list(existing_ids)

        # 计算整体时间范围和数量
        start_date, end_date, campaigns_count = await MediaPlanService._get_date_range_and_count(
            db=db,
            campaign_ids=campaign_ids,
        )

        # 创建媒体计划记录
        media_plan = MediaPlan(
            name=data.name,
            budget=data.budget,
            description=data.description,
            created_by=current_user.id,
        )
        db.add(media_plan)
        await db.flush()

        # 关联中间表
        for cid in campaign_ids:
            db.add(
                MediaPlanCampaign(
                    media_plan_id=media_plan.id,
                    campaign_id=cid,
                )
            )

        await db.flush()
        await db.refresh(media_plan)

        status_value = MediaPlanService._compute_status(start_date, end_date)

        # 解析操作者姓名
        operator_first_name = current_user.first_name
        operator_last_name = current_user.last_name

        return MediaPlanResponse(
            id=media_plan.id,
            created_at=media_plan.created_at,
            updated_at=media_plan.updated_at,
            name=media_plan.name,
            budget=media_plan.budget,
            description=media_plan.description,
            start_date=start_date,
            end_date=end_date,
            status=status_value,
            campaigns_count=campaigns_count,
            operator_first_name=operator_first_name,
            operator_last_name=operator_last_name,
        )

    @staticmethod
    async def get_media_plan_detail(
        db: AsyncSession,
        current_user: User,
        media_plan_id: int,
    ) -> MediaPlanDetailResponse:
        """Get single media plan detail including campaign name list."""

        # 查询媒体计划以及创建人姓名
        query = (
            select(
                MediaPlan,
                User.first_name.label("operator_first_name"),
                User.last_name.label("operator_last_name"),
            )
            .outerjoin(User, User.id == MediaPlan.created_by)
            .where(MediaPlan.id == media_plan_id)
        )

        result = await db.execute(query)
        row = result.first()
        if not row:
            raise APIException(
                status_code=status.HTTP_404_NOT_FOUND,
                message="Media plan not found",
            )

        media_plan: MediaPlan = row[0]
        operator_first_name = row.operator_first_name
        operator_last_name = row.operator_last_name

        # 通过 relationship 获取关联的活动（lazy="selectin" 会自动加载）
        # 需要先 refresh 以确保 relationship 被加载
        await db.refresh(media_plan, ["campaigns"])

        campaign_names = [c.name for c in media_plan.campaigns]

        if media_plan.campaigns:
            start_date = min(c.start_date for c in media_plan.campaigns)
            end_date = max(c.end_date for c in media_plan.campaigns)
            campaigns_count = len(media_plan.campaigns)
        else:
            start_date = None
            end_date = None
            campaigns_count = 0

        status_value = MediaPlanService._compute_status(start_date, end_date)

        return MediaPlanDetailResponse(
            id=media_plan.id,
            created_at=media_plan.created_at,
            updated_at=media_plan.updated_at,
            name=media_plan.name,
            budget=media_plan.budget,
            description=media_plan.description,
            start_date=start_date,
            end_date=end_date,
            status=status_value,
            campaigns_count=campaigns_count,
            operator_first_name=operator_first_name,
            operator_last_name=operator_last_name,
            Campaigns=campaign_names,
        )

    @staticmethod
    async def delete_media_plan(
        db: AsyncSession,
        current_user: User,
        media_plan_id: int,
    ) -> None:
        """Delete a media plan by id.

        - Only owner/admin of media owner organization can delete.
        - Media plan campaigns association will be cascade deleted.
        - Campaigns themselves will NOT be deleted.
        """
        # Permission checks
        if current_user.role not in [TeamRole.OWNER.value, TeamRole.ADMIN.value]:
            raise APIException(
                status_code=status.HTTP_403_FORBIDDEN,
                message="Only owner or admin can delete media plan",
            )

        org_type_normalized = (current_user.organization_type or "").replace("-", " ").lower()
        media_owner_normalized = OrganizationType.MEDIA_OWNER.value.lower()
        if org_type_normalized != media_owner_normalized:
            raise APIException(
                status_code=status.HTTP_403_FORBIDDEN,
                message="Only media owners can delete media plan",
            )

        # Find media plan
        query = select(MediaPlan).where(MediaPlan.id == media_plan_id)
        result = await db.execute(query)
        media_plan = result.scalar_one_or_none()
        if not media_plan:
            raise APIException(
                status_code=status.HTTP_404_NOT_FOUND,
                message="Media plan not found",
            )

        # Delete media plan (media_plan_campaigns will cascade)
        await db.delete(media_plan)
        await db.flush()

    @staticmethod
    async def update_media_plan(
        db: AsyncSession,
        current_user: User,
        media_plan_id: int,
        data: MediaPlanUpdate,
    ) -> MediaPlanResponse:
        """Update a media plan by id.

        - Only owner/admin of media owner organization can update.
        - Campaign associations will be updated (old removed, new added).
        """
        # Permission checks
        if current_user.role not in [TeamRole.OWNER.value, TeamRole.ADMIN.value]:
            raise APIException(
                status_code=status.HTTP_403_FORBIDDEN,
                message="Only owner or admin can update media plan",
            )

        org_type_normalized = (current_user.organization_type or "").replace("-", " ").lower()
        media_owner_normalized = OrganizationType.MEDIA_OWNER.value.lower()
        if org_type_normalized != media_owner_normalized:
            raise APIException(
                status_code=status.HTTP_403_FORBIDDEN,
                message="Only media owners can update media plan",
            )

        # Find media plan
        query = select(MediaPlan).where(MediaPlan.id == media_plan_id)
        result = await db.execute(query)
        media_plan = result.scalar_one_or_none()
        if not media_plan:
            raise APIException(
                status_code=status.HTTP_404_NOT_FOUND,
                message="Media plan not found",
            )

        # Deduplicate campaign_ids
        unique_campaign_ids = list(set(data.campaign_ids))

        # Validate campaign_ids exist
        if unique_campaign_ids:
            camp_query = select(func.count()).where(Campaign.id.in_(unique_campaign_ids))
            camp_result = await db.execute(camp_query)
            found_count = camp_result.scalar() or 0
            if found_count != len(unique_campaign_ids):
                raise APIException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    message="Some campaign IDs do not exist",
                )

        # Update media plan fields
        media_plan.name = data.name
        media_plan.budget = data.budget
        media_plan.description = data.description

        # Update campaign associations: delete old, insert new
        # 1. Delete existing associations using SQL delete
        delete_stmt = sql_delete(MediaPlanCampaign).where(
            MediaPlanCampaign.media_plan_id == media_plan_id
        )
        await db.execute(delete_stmt)

        # 2. Insert new associations (using deduplicated list)
        for camp_id in unique_campaign_ids:
            assoc = MediaPlanCampaign(media_plan_id=media_plan_id, campaign_id=camp_id)
            db.add(assoc)

        await db.flush()
        await db.refresh(media_plan)

        # Calculate date range from campaigns
        start_date = None
        end_date = None
        if unique_campaign_ids:
            date_query = select(
                func.min(Campaign.start_date).label("start_date"),
                func.max(Campaign.end_date).label("end_date"),
            ).where(Campaign.id.in_(unique_campaign_ids))
            date_result = await db.execute(date_query)
            date_row = date_result.one()
            start_date = date_row.start_date
            end_date = date_row.end_date

        # Get operator info
        operator_first_name = None
        operator_last_name = None
        if media_plan.created_by:
            user_query = select(User).where(User.id == media_plan.created_by)
            user_result = await db.execute(user_query)
            creator = user_result.scalar_one_or_none()
            if creator:
                operator_first_name = creator.first_name
                operator_last_name = creator.last_name

        return MediaPlanResponse(
            id=media_plan.id,
            name=media_plan.name,
            budget=media_plan.budget,
            description=media_plan.description,
            start_date=start_date,
            end_date=end_date,
            status=MediaPlanService._compute_status(start_date, end_date),
            campaigns_count=len(unique_campaign_ids),
            operator_first_name=operator_first_name,
            operator_last_name=operator_last_name,
            created_at=media_plan.created_at,
            updated_at=media_plan.updated_at,
        )


media_plan_service = MediaPlanService()
