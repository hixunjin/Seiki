from pathlib import Path

from fastapi import APIRouter, Depends, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from app.db.session import get_db, transaction
from app.api.client.deps import get_current_user
from app.models.user import User
from app.models.inventory import Inventory
from app.schemas.client.inventory import (
    InventoryCreate,
    InventoryUpdate,
    InventoryResponse,
    InventoryListFilter,
    InventoryOwnerNode,
    InventoryNetworkNode,
    InventoryFaceNode,
)
from app.schemas.response import ApiResponse
from app.services.client.inventory import inventory_service

router = APIRouter()

# Path to static template file
TEMPLATE_FILE = Path(__file__).resolve().parent.parent.parent.parent / "static" / "inventory_template.csv"


@router.get("/template")
async def download_template():
    """Download the CSV template for inventory import.

    Returns a CSV file that users can fill in and upload via /import.
    """
    return FileResponse(
        path=TEMPLATE_FILE,
        filename="inventory_template.csv",
        media_type="text/csv",
    )


@router.post("", response_model=InventoryResponse)
async def create_inventory(
    data: InventoryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new inventory (billboard).

    Only media owners (owner/admin) can create inventory.
    """
    async with transaction(db):
        result = await inventory_service.create_inventory(
            db=db,
            current_user=current_user,
            data=data,
        )
        return ApiResponse.success(data=result)


@router.post("/import")
async def import_inventories(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Import inventories from a CSV/XLS file.

    Expected format (semicolon-separated, no loop_timing column):

    face_id;billboard_type;is_indoor;latitude;longitude;address;height_from_ground;\
azimuth_from_north;width;height;network_name;media_owner_name
    """
    import csv
    import io

    content = await file.read()
    text = content.decode("utf-8-sig")

    reader = csv.DictReader(io.StringIO(text), delimiter=';')
    rows = list(reader)

    async with transaction(db):
        result = await inventory_service.import_from_rows(
            db=db,
            current_user=current_user,
            rows=rows,
        )
        return ApiResponse.success(data=result)


@router.delete("/{face_id}")
async def delete_inventory(
    face_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete an inventory (billboard) by face_id.

    Only media owners (owner/admin) can delete inventory.
    """
    async with transaction(db):
        await inventory_service.delete_inventory(
            db=db,
            current_user=current_user,
            face_id=face_id,
        )
        return ApiResponse.success(message="Inventory deleted successfully")


@router.put("/{inventory_id}", response_model=InventoryResponse)
async def update_inventory(
    inventory_id: int,
    data: InventoryUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update an existing inventory (billboard).

    Only media owners (owner/admin) can update inventory.
    """
    async with transaction(db):
        result = await inventory_service.update_inventory(
            db=db,
            current_user=current_user,
            inventory_id=inventory_id,
            data=data,
        )
        return ApiResponse.success(data=result)


@router.get("/list")
async def list_inventories(
    filters: InventoryListFilter = Depends(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List inventories with optional filters for the right side table.

    - media_owner_name: filter by media owner
    - network_name: filter by network
    - face_id: filter by one face ID
    - keyword: search face_id / network_name / media_owner_name
    - billboard_type: filter by billboard type
    - status: active/inactive
    - page, per_page: pagination
    """
    query = select(Inventory)

    if filters.media_owner_name:
        query = query.where(Inventory.media_owner_name == filters.media_owner_name)

    if filters.network_name:
        query = query.where(Inventory.network_name == filters.network_name)

    if filters.face_id:
        query = query.where(Inventory.face_id == filters.face_id)

    # Generic keyword search on face_id / network_name / media_owner_name
    if filters.keyword:
        kw = f"%{filters.keyword.strip()}%"
        query = query.where(
            or_(
                Inventory.face_id.ilike(kw),
                Inventory.network_name.ilike(kw),
                Inventory.media_owner_name.ilike(kw),
            )
        )

    # Filter by billboard type (exact stored value, including "Other: xxx")
    if filters.billboard_type:
        query = query.where(Inventory.billboard_type == filters.billboard_type)

    if filters.status is not None:
        query = query.where(Inventory.status == filters.status.value)

    # Map Inventory model to simple dict for table
    def transform(items):
        result = []
        for inv in items:
            result.append(
                {
                    "id": inv.id,
                    "face_id": inv.face_id,
                    "latitude": inv.latitude,
                    "longitude": inv.longitude,
                    "address": inv.address,
                    "media_owner_name": inv.media_owner_name,
                    "network_name": inv.network_name,
                    "billboard_type": inv.billboard_type,
                    "status": inv.status,
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


@router.get("/tree/search")
async def search_inventory_owners(
    keyword: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Search media owners by keyword matching media_owner_name or network_name.

    Returns media owners whose name matches the keyword, OR who have networks
    matching the keyword. Each result includes the billboard count.
    """
    kw = f"%{keyword.strip()}%"

    # Find media owners where:
    # 1. media_owner_name matches keyword, OR
    # 2. any of their network_name matches keyword
    query = (
        select(Inventory.media_owner_name, func.count().label("total"))
        .where(
            or_(
                Inventory.media_owner_name.ilike(kw),
                Inventory.network_name.ilike(kw),
            )
        )
        .group_by(Inventory.media_owner_name)
        .order_by(Inventory.media_owner_name)
    )

    result = await db.execute(query)
    rows = result.all()
    data = [
        InventoryOwnerNode(media_owner_name=row[0], total=row[1])
        for row in rows
    ]
    return ApiResponse.success(data=data)


@router.get("/tree/owners")
async def get_inventory_owners(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get media owners and their inventory counts for left tree first level.

    For media owner clients, this will typically return only their own company.
    """
    # Platform view: aggregate over all media owners (no company restriction)
    query = (
        select(Inventory.media_owner_name, func.count().label("total"))
        .group_by(Inventory.media_owner_name)
    )

    result = await db.execute(query)
    rows = result.all()
    data = [
        InventoryOwnerNode(media_owner_name=row[0], total=row[1])
        for row in rows
    ]
    return ApiResponse.success(data=data)


@router.get("/tree/networks")
async def get_inventory_networks(
    media_owner_name: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get networks and counts under a media owner for left tree second level."""
    query = (
        select(Inventory.network_name, func.count().label("total"))
        .where(Inventory.media_owner_name == media_owner_name)
        .group_by(Inventory.network_name)
    )
    result = await db.execute(query)
    rows = result.all()
    data = [
        InventoryNetworkNode(network_name=row[0], total=row[1])
        for row in rows
    ]
    return ApiResponse.success(data=data)


@router.get("/tree/faces")
async def get_inventory_faces(
    media_owner_name: str,
    network_name: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get face IDs under a specific owner + network for left tree third level."""
    query = (
        select(Inventory.face_id)
        .where(
            (Inventory.media_owner_name == media_owner_name)
            & (Inventory.network_name == network_name)
        )
        .order_by(Inventory.face_id)
    )
    result = await db.execute(query)
    rows = result.scalars().all()
    data = [InventoryFaceNode(face_id=fid) for fid in rows]
    return ApiResponse.success(data=data)


@router.get("/types")
async def get_inventory_types(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all distinct billboard types across all companies for dropdown.

    This endpoint is not restricted by media owner; it returns the set of
    unique `billboard_type` values present in the inventories table, including
    custom types like "Other: xxx".
    """
    query = (
        select(Inventory.billboard_type)
        .group_by(Inventory.billboard_type)
        .order_by(Inventory.billboard_type)
    )
    result = await db.execute(query)
    types = result.scalars().all()
    return ApiResponse.success(data=types)

@router.get("/{inventory_id}", response_model=InventoryResponse)
async def get_inventory_detail(
    inventory_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """View a single inventory's full details (read-only).

    Used by the "eye" action in the list to open the View Inventory modal.
    """
    result = await inventory_service.get_inventory(
        db=db,
        current_user=current_user,
        inventory_id=inventory_id,
    )
    return ApiResponse.success(data=result)

