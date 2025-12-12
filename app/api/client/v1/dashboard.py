from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import select, func, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.client.deps import get_current_user
from app.db.session import get_db
from app.models.inventory import Inventory
from app.models.campaign import Campaign, CampaignInventory
from app.models.media_plan import MediaPlan, MediaPlanCampaign
from app.models.user import User
from app.schemas.response import ApiResponse
from app.services.client.campaign import campaign_service

router = APIRouter()


@router.get("/summary")
async def get_dashboard_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get dashboard summary statistics.

    Returns:
    - total_billboards: Total count of all inventories
    - total_networks: Count of distinct network names
    - digital_screen: Count of inventories with billboard_type = 'Digital Screen'
    - digital_hoarding: Count of inventories with billboard_type = 'Digital Hoarding'
    - digital_bridges: Count of inventories with billboard_type = 'Digital Bridge'
    """

    # Single query to get all statistics
    query = select(
        func.count(Inventory.id).label("total_billboards"),
        func.count(func.distinct(Inventory.network_name)).label("total_networks"),
        func.sum(
            case(
                (Inventory.billboard_type == "Digital Screen", 1),
                else_=0,
            )
        ).label("digital_screen"),
        func.sum(
            case(
                (Inventory.billboard_type == "Digital Hoarding", 1),
                else_=0,
            )
        ).label("digital_hoarding"),
        func.sum(
            case(
                (Inventory.billboard_type == "Digital Bridge", 1),
                else_=0,
            )
        ).label("digital_bridges"),
    )

    result = await db.execute(query)
    row = result.one()

    data = {
        "total_billboards": row.total_billboards or 0,
        "total_networks": row.total_networks or 0,
        "digital_screen": row.digital_screen or 0,
        "digital_hoarding": row.digital_hoarding or 0,
        "digital_bridges": row.digital_bridges or 0,
    }

    return ApiResponse.success(data=data)


@router.get("/active-campaigns")
async def get_active_campaigns(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get latest 4 active campaigns for dashboard.

    Active = start_date <= today <= end_date
    Ordered by updated_at desc, limit 4.
    """
    today = datetime.utcnow().date()

    # Query active campaigns with billboard count and operator info
    query = (
        select(
            Campaign,
            func.count(CampaignInventory.id).label("billboard_count"),
            User.first_name.label("operator_first_name"),
            User.last_name.label("operator_last_name"),
        )
        .outerjoin(CampaignInventory, Campaign.id == CampaignInventory.campaign_id)
        .outerjoin(User, Campaign.created_by == User.id)
        .where(Campaign.start_date <= today)
        .where(Campaign.end_date >= today)
        .group_by(Campaign.id, User.first_name, User.last_name)
        .order_by(Campaign.updated_at.desc())
        .limit(4)
    )

    result = await db.execute(query)
    rows = result.all()

    data = []
    for row in rows:
        campaign = row[0]
        billboard_count = row.billboard_count or 0

        # Compute KPI snapshot
        kpi_snapshot = campaign_service.compute_kpi_for_campaign(
            budget_eur=campaign.price_eur,
            start_date=campaign.start_date,
            end_date=campaign.end_date,
            billboard_count=billboard_count,
        )

        data.append({
            "id": campaign.id,
            "campaign_name": campaign.name,
            "start_date": campaign.start_date,
            "end_date": campaign.end_date,
            "total_billboards": billboard_count,
            "kpi_snapshot": kpi_snapshot,
            "operator_first_name": row.operator_first_name,
            "operator_last_name": row.operator_last_name,
            "last_updated_date": campaign.updated_at,
        })

    return ApiResponse.success(data=data)


@router.get("/active-media-plans")
async def get_active_media_plans(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get latest 5 active media plans for dashboard.

    Active = aggregated start_date <= today <= aggregated end_date
    Ordered by updated_at desc, limit 5.
    """
    today = datetime.utcnow().date()

    # Query media plans with aggregated date range, campaigns count and operator info
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
        .outerjoin(User, MediaPlan.created_by == User.id)
        .group_by(MediaPlan.id, User.first_name, User.last_name)
        .having(func.min(Campaign.start_date) <= today)
        .having(func.max(Campaign.end_date) >= today)
        .order_by(MediaPlan.updated_at.desc())
        .limit(5)
    )

    result = await db.execute(query)
    rows = result.all()

    data = []
    for row in rows:
        media_plan = row[0]
        data.append({
            "id": media_plan.id,
            "plan_name": media_plan.name,
            "start_date": row.start_date,
            "end_date": row.end_date,
            "campaigns_count": row.campaigns_count or 0,
            "budget": media_plan.budget or 0,
            "operator_first_name": row.operator_first_name,
            "operator_last_name": row.operator_last_name,
            "last_updated_date": media_plan.updated_at,
        })

    return ApiResponse.success(data=data)
