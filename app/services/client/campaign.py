from __future__ import annotations

import json
from datetime import date
from typing import List, Dict

from fastapi import status
from sqlalchemy import select, func, delete as sql_delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions.http_exceptions import APIException
from app.models.campaign import Campaign, CampaignInventory
from app.models.media_plan import MediaPlanCampaign
from app.models.inventory import Inventory
from app.models.user import User, TeamRole, OrganizationType
from app.schemas.client.campaign import CampaignCreate, CampaignUpdate, CampaignResponse, CampaignDetailResponse


class CampaignService:
    @staticmethod
    def compute_kpi_for_campaign(
        *,
        budget_eur: int,
        start_date: date,
        end_date: date,
        billboard_count: int,
    ) -> Dict:
        """Compute mock KPI data for a campaign.

        This is a placeholder implementation that derives numbers from
        budget, duration and billboard count so that front-end has
        realistic-looking data. It does NOT reflect real business logic.
        """

        days = max((end_date - start_date).days, 1)
        boards = max(billboard_count, 1)

        # Simple mock formulas
        net_contacts = boards * days * 100
        gross_contacts = int(net_contacts * 1.5)

        # Frequency roughly increases with boards and days
        frequency = 1.0 + boards * 0.5 + days / 30.0

        # Coverage between 20% and 90%
        coverage_percent = max(20.0, min(20.0 + boards * 5.0, 90.0))

        if gross_contacts > 0 and budget_eur > 0:
            cpm = round(budget_eur / gross_contacts * 1000.0, 2)
        else:
            cpm = 0.0

        # Attention index between 50 and 90
        attention_index = int(max(50.0, min(50.0 + boards * 3.0, 90.0)))

        return {
            "net_contacts": int(net_contacts),
            "gross_contacts": gross_contacts,
            "frequency": round(frequency, 2),
            "coverage_percent": round(coverage_percent, 2),
            "cpm": cpm,
            "attention_index": attention_index,
        }

    @staticmethod
    async def create_campaign(
        db: AsyncSession,
        current_user: User,
        data: CampaignCreate,
    ) -> CampaignResponse:
        """Create a campaign with selected inventories.

        - Only media owner owner/admin can create.
        - Can attach multiple inventories via many-to-many relation.
        """
        # 权限：同 inventory 模块
        if current_user.role not in [TeamRole.OWNER.value, TeamRole.ADMIN.value]:
            raise APIException(
                status_code=status.HTTP_403_FORBIDDEN,
                message="Only owner or admin can create campaign",
            )

        org_type_normalized = (current_user.organization_type or "").replace("-", " ").lower()
        media_owner_normalized = OrganizationType.MEDIA_OWNER.value.lower()
        if org_type_normalized != media_owner_normalized:
            raise APIException(
                status_code=status.HTTP_403_FORBIDDEN,
                message="Only media owners can create campaign",
            )

        # 创建 Campaign 记录
        campaign = Campaign(
            name=data.name,
            price_eur=data.price_eur,
            description=data.description,
            start_date=data.start_date,
            end_date=data.end_date,
            country_code=data.country_code,
            city=data.city,
            gender=data.gender.value,
            age_ranges=json.dumps(data.age_ranges) if data.age_ranges else None,
            socio_professional_category=data.socio_professional_category.value
            if data.socio_professional_category
            else None,
            mobility_modes=json.dumps(data.mobility_modes)
            if data.mobility_modes
            else None,
            poi_categories=json.dumps(data.poi_categories)
            if data.poi_categories
            else None,
            created_by=current_user.id,
        )
        db.add(campaign)
        await db.flush()

        # 关联广告牌（如果有）
        billboard_count = 0
        if data.inventory_ids:
            # 确认这些 inventory 都存在
            query = select(Inventory.id).where(Inventory.id.in_(data.inventory_ids))
            result = await db.execute(query)
            existing_ids = {row[0] for row in result.all()}

            missing_ids = set(data.inventory_ids) - existing_ids
            if missing_ids:
                raise APIException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    message=f"Inventories not found: {sorted(missing_ids)}",
                )

            for inv_id in existing_ids:
                db.add(
                    CampaignInventory(
                        campaign_id=campaign.id,
                        inventory_id=inv_id,
                    )
                )
            billboard_count = len(existing_ids)

        await db.flush()
        await db.refresh(campaign)

        # 构造响应模型
        return CampaignResponse(
            id=campaign.id,
            created_at=campaign.created_at,
            updated_at=campaign.updated_at,
            name=campaign.name,
            price_eur=campaign.price_eur,
            description=campaign.description,
            start_date=campaign.start_date,
            end_date=campaign.end_date,
            country_code=campaign.country_code,
            city=campaign.city,
            gender=data.gender,
            age_ranges=data.age_ranges,
            socio_professional_category=data.socio_professional_category,
            mobility_modes=data.mobility_modes,
            poi_categories=data.poi_categories,
            billboard_count=billboard_count,
        )

    @staticmethod
    async def get_campaign_detail(
        db: AsyncSession,
        current_user: User,
        campaign_id: int,
    ) -> CampaignDetailResponse:
        """Get single campaign detail including billboard ids and KPI data."""

        query = (
            select(Campaign)
            .where(Campaign.id == campaign_id)
        )

        result = await db.execute(query)
        campaign = result.scalar_one_or_none()
        if not campaign:
            raise APIException(
                status_code=status.HTTP_404_NOT_FOUND,
                message="Campaign not found",
            )

        # Get billboard ids for this campaign
        link_query = select(CampaignInventory.inventory_id).where(
            CampaignInventory.campaign_id == campaign.id
        )
        link_result = await db.execute(link_query)
        billboard_ids = link_result.scalars().all()
        billboard_count = len(billboard_ids)

        # Compute KPI data
        kpi_data = CampaignService.compute_kpi_for_campaign(
            budget_eur=campaign.price_eur,
            start_date=campaign.start_date,
            end_date=campaign.end_date,
            billboard_count=billboard_count or 0,
        )

        return CampaignDetailResponse(
            id=campaign.id,
            created_at=campaign.created_at,
            updated_at=campaign.updated_at,
            name=campaign.name,
            price_eur=campaign.price_eur,
            description=campaign.description,
            start_date=campaign.start_date,
            end_date=campaign.end_date,
            country_code=campaign.country_code,
            city=campaign.city,
            gender=campaign.gender,
            age_ranges=json.loads(campaign.age_ranges) if campaign.age_ranges else None,
            socio_professional_category=campaign.socio_professional_category,
            mobility_modes=json.loads(campaign.mobility_modes) if campaign.mobility_modes else None,
            poi_categories=json.loads(campaign.poi_categories) if campaign.poi_categories else None,
            billboard_count=billboard_count,
            billboard_ids=billboard_ids,
            kpi_data=kpi_data,
        )

    @staticmethod
    async def delete_campaign(
        db: AsyncSession,
        current_user: User,
        campaign_id: int,
    ) -> None:
        """Delete a campaign by id.

        - Only owner/admin of media owner organization can delete.
        - Cannot delete if campaign is used by any media plan.
        """
        # Permission checks
        if current_user.role not in [TeamRole.OWNER.value, TeamRole.ADMIN.value]:
            raise APIException(
                status_code=status.HTTP_403_FORBIDDEN,
                message="Only owner or admin can delete campaign",
            )

        org_type_normalized = (current_user.organization_type or "").replace("-", " ").lower()
        media_owner_normalized = OrganizationType.MEDIA_OWNER.value.lower()
        if org_type_normalized != media_owner_normalized:
            raise APIException(
                status_code=status.HTTP_403_FORBIDDEN,
                message="Only media owners can delete campaign",
            )

        # Find campaign
        query = select(Campaign).where(Campaign.id == campaign_id)
        result = await db.execute(query)
        campaign = result.scalar_one_or_none()
        if not campaign:
            raise APIException(
                status_code=status.HTTP_404_NOT_FOUND,
                message="Campaign not found",
            )

        # Check if campaign is used by any media plan
        usage_query = select(func.count()).where(
            MediaPlanCampaign.campaign_id == campaign_id
        )
        usage_result = await db.execute(usage_query)
        usage_count = usage_result.scalar() or 0

        if usage_count > 0:
            raise APIException(
                status_code=status.HTTP_400_BAD_REQUEST,
                message=f"Cannot delete: campaign is used by {usage_count} media plan(s)",
            )

        # Delete campaign (campaign_inventories will cascade)
        await db.delete(campaign)
        await db.flush()

    @staticmethod
    async def update_campaign(
        db: AsyncSession,
        current_user: User,
        campaign_id: int,
        data: CampaignUpdate,
    ) -> CampaignResponse:
        """Update a campaign by id.

        - Only owner/admin of media owner organization can update.
        - country_code is fixed to 'SA' and cannot be changed.
        - Billboard associations will be updated (old removed, new added).
        """
        # Permission checks
        if current_user.role not in [TeamRole.OWNER.value, TeamRole.ADMIN.value]:
            raise APIException(
                status_code=status.HTTP_403_FORBIDDEN,
                message="Only owner or admin can update campaign",
            )

        org_type_normalized = (current_user.organization_type or "").replace("-", " ").lower()
        media_owner_normalized = OrganizationType.MEDIA_OWNER.value.lower()
        if org_type_normalized != media_owner_normalized:
            raise APIException(
                status_code=status.HTTP_403_FORBIDDEN,
                message="Only media owners can update campaign",
            )

        # Find campaign
        query = select(Campaign).where(Campaign.id == campaign_id)
        result = await db.execute(query)
        campaign = result.scalar_one_or_none()
        if not campaign:
            raise APIException(
                status_code=status.HTTP_404_NOT_FOUND,
                message="Campaign not found",
            )

        # Validate date range
        if data.start_date > data.end_date:
            raise APIException(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="start_date must be before or equal to end_date",
            )

        # Deduplicate inventory_ids
        unique_inventory_ids = list(set(data.inventory_ids))

        # Validate inventory_ids exist
        if unique_inventory_ids:
            inv_query = select(func.count()).where(Inventory.id.in_(unique_inventory_ids))
            inv_result = await db.execute(inv_query)
            found_count = inv_result.scalar() or 0
            if found_count != len(unique_inventory_ids):
                raise APIException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    message="Some inventory IDs do not exist",
                )

        # Update campaign fields (country_code stays as 'SA')
        campaign.name = data.name
        campaign.price_eur = data.price_eur
        campaign.description = data.description
        campaign.start_date = data.start_date
        campaign.end_date = data.end_date
        campaign.city = data.city
        campaign.gender = data.gender.value
        campaign.age_ranges = json.dumps(data.age_ranges) if data.age_ranges else None
        campaign.socio_professional_category = (
            data.socio_professional_category.value if data.socio_professional_category else None
        )
        campaign.mobility_modes = json.dumps(data.mobility_modes) if data.mobility_modes else None
        campaign.poi_categories = json.dumps(data.poi_categories) if data.poi_categories else None

        # Update billboard associations: delete old, insert new
        # 1. Delete existing associations using SQL delete
        delete_stmt = sql_delete(CampaignInventory).where(
            CampaignInventory.campaign_id == campaign_id
        )
        await db.execute(delete_stmt)

        # 2. Insert new associations (using deduplicated list)
        for inv_id in unique_inventory_ids:
            assoc = CampaignInventory(campaign_id=campaign_id, inventory_id=inv_id)
            db.add(assoc)

        await db.flush()
        await db.refresh(campaign)

        # Count billboards for response
        billboard_count = len(unique_inventory_ids)

        return CampaignResponse(
            id=campaign.id,
            name=campaign.name,
            price_eur=campaign.price_eur,
            description=campaign.description,
            start_date=campaign.start_date,
            end_date=campaign.end_date,
            country_code=campaign.country_code,
            city=campaign.city,
            gender=campaign.gender,
            age_ranges=json.loads(campaign.age_ranges) if campaign.age_ranges else None,
            socio_professional_category=campaign.socio_professional_category,
            mobility_modes=json.loads(campaign.mobility_modes) if campaign.mobility_modes else None,
            poi_categories=json.loads(campaign.poi_categories) if campaign.poi_categories else None,
            billboard_count=billboard_count,
            created_at=campaign.created_at,
            updated_at=campaign.updated_at,
        )


campaign_service = CampaignService()
