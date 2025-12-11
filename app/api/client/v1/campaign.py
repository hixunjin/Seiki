from datetime import date, datetime

from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.client.deps import get_current_user
from app.db.session import get_db, transaction
from app.models.campaign import Campaign, CampaignInventory
from app.models.user import User
from app.schemas.client.campaign import (
    CampaignCreate,
    CampaignResponse,
    CampaignDetailResponse,
    CampaignListFilter,
    CampaignStatus,
)
from app.schemas.response import ApiResponse
from app.services.client.campaign import campaign_service

router = APIRouter()


@router.post("", response_model=CampaignResponse)
async def create_campaign(
    data: CampaignCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new campaign with selected inventories."""
    async with transaction(db):
        result = await campaign_service.create_campaign(
            db=db,
            current_user=current_user,
            data=data,
        )
        return ApiResponse.success(data=result)


@router.get("")
async def list_campaigns(
    filters: CampaignListFilter = Depends(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List campaigns with filters and pagination.

    Returns rows for the campaigns table, including:
    - Campaign Name
    - Date Range
    - Billboards count
    - Budget
    - KPI snapshot (computed mock data)
    - Status (computed from dates)
    - Operator (creator name)
    - Last Updated Date
    """

    # Base query with billboard count (many-to-many association)
    query = (
        select(
            Campaign,
            func.count(CampaignInventory.id).label("billboard_count"),
        )
        .outerjoin(
            CampaignInventory,
            Campaign.id == CampaignInventory.campaign_id,
        )
        .group_by(Campaign.id)
        .order_by(Campaign.created_at.desc())
    )

    # Keyword filter on campaign name
    if filters.keyword:
        kw = f"%{filters.keyword.strip()}%"
        query = query.where(Campaign.name.ilike(kw))

    # Date range filter: campaign fully inside the selected range (inclusive)
    # start_date_filter <= campaign.start_date AND campaign.end_date <= end_date_filter
    if filters.start_date:
        query = query.where(Campaign.start_date >= filters.start_date)
    if filters.end_date:
        query = query.where(Campaign.end_date <= filters.end_date)

    # Status filter based on current date
    today = datetime.utcnow().date()
    if filters.status == CampaignStatus.ACTIVE:
        query = query.where(Campaign.start_date <= today, Campaign.end_date >= today)
    elif filters.status == CampaignStatus.UPCOMING:
        query = query.where(Campaign.start_date > today)
    elif filters.status == CampaignStatus.COMPLETED:
        query = query.where(Campaign.end_date < today)

    def transform(items):
        result = []
        today_local = today
        for c in items:
            # billboard_count is attached by paginator when using multi-column select
            billboard_count = getattr(c, "billboard_count", 0) or 0

            # Compute status for display
            if c.start_date > today_local:
                status_value = CampaignStatus.UPCOMING.value
            elif c.end_date < today_local:
                status_value = CampaignStatus.COMPLETED.value
            else:
                status_value = CampaignStatus.ACTIVE.value

            # Compute mock KPI data
            kpi_data = campaign_service.compute_kpi_for_campaign(
                budget_eur=c.price_eur,
                start_date=c.start_date,
                end_date=c.end_date,
                billboard_count=billboard_count,
            )

            # Operator name from created_by is not joined yet; for now we return
            # only campaign data, and front-end can use current user's name as operator.
            operator_name = None

            result.append(
                {
                    "id": c.id,
                    "name": c.name,
                    "date_range": f"{c.start_date} - {c.end_date}",
                    "billboards": billboard_count,
                    "budget": c.price_eur,
                    "kpi_data": kpi_data,
                    "status": status_value,
                    "operator": operator_name,
                    "last_updated_at": c.updated_at,
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


@router.get("/{campaign_id}", response_model=CampaignDetailResponse)
async def get_campaign_detail(
    campaign_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get single campaign detail by id.

    Used by the eye icon in the campaign list.
    """
    result = await campaign_service.get_campaign_detail(
        db=db,
        current_user=current_user,
        campaign_id=campaign_id,
    )
    return ApiResponse.success(data=result)
