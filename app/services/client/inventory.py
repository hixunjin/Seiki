from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import status
from app.models.inventory import Inventory
from app.models.user import User, TeamRole, OrganizationType
from app.schemas.client.inventory import InventoryCreate, InventoryUpdate, InventoryResponse
from app.exceptions.http_exceptions import APIException


class InventoryService:
    @staticmethod
    async def create_inventory(
        db: AsyncSession,
        current_user: User,
        data: InventoryCreate,
    ) -> InventoryResponse:
        # Only media owner or admin can create inventory
        if current_user.role not in [TeamRole.OWNER.value, TeamRole.ADMIN.value]:
            raise APIException(
                status_code=status.HTTP_403_FORBIDDEN,
                message="Only owner or admin can create inventory",
            )

        # Some existing data use 'media-owner' instead of 'media owner'
        org_type_normalized = (current_user.organization_type or "").replace("-", " ").lower()
        media_owner_normalized = OrganizationType.MEDIA_OWNER.value.lower()
        if org_type_normalized != media_owner_normalized:
            raise APIException(
                status_code=status.HTTP_403_FORBIDDEN,
                message="Only media owners can create inventory",
            )

        # Ensure face_id is unique within the same media owner
        query = select(Inventory).where(
            (Inventory.face_id == data.face_id)
            & (Inventory.media_owner_name == (data.media_owner_name or current_user.company_name))
        )
        result = await db.execute(query)
        if result.scalar_one_or_none():
            raise APIException(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Face ID already exists for this media owner",
            )

        # Backend concatenation for custom billboard type
        billboard_type_value = data.billboard_type
        if (
            isinstance(billboard_type_value, str)
            and billboard_type_value.strip() == "Other"
            and data.custom_billboard_type
        ):
            custom = data.custom_billboard_type.strip()
            if custom:
                billboard_type_value = f"Other: {custom}"

        inventory = Inventory(
            face_id=data.face_id,
            billboard_type=billboard_type_value,
            is_indoor=data.is_indoor,
            latitude=data.latitude,
            longitude=data.longitude,
            address=data.address,
            height_from_ground=data.height_from_ground,
            loop_timing=data.loop_timing,
            azimuth_from_north=data.azimuth_from_north,
            width=data.width,
            height=data.height,
            network_name=data.network_name,
            media_owner_name=data.media_owner_name or current_user.company_name,
            status=data.status.value,
        )
        db.add(inventory)
        await db.flush()
        await db.refresh(inventory)

        return InventoryResponse.model_validate(inventory)

    @staticmethod
    async def get_inventory(
        db: AsyncSession,
        current_user: User,
        inventory_id: int,
    ) -> InventoryResponse:
        """Get a single inventory detail for view-only modal.

        Restrict to inventories under current user's company when company_name is set.
        """
        query = select(Inventory).where(Inventory.id == inventory_id)

        if current_user.company_name:
            query = query.where(Inventory.media_owner_name == current_user.company_name)

        result = await db.execute(query)
        inventory = result.scalar_one_or_none()
        if not inventory:
            raise APIException(
                status_code=status.HTTP_404_NOT_FOUND,
                message="Inventory not found",
            )

        return InventoryResponse.model_validate(inventory)

    @staticmethod
    async def update_inventory(
        db: AsyncSession,
        current_user: User,
        inventory_id: int,
        data: InventoryUpdate,
    ) -> InventoryResponse:
        """Update an existing inventory (billboard).

        - Only owner/admin of media owner organization can update.
        - Restrict updates to inventories under current user's company.
        - Media owner (ownership) is not changeable via this API.
        """
        # Permission checks (same as create)
        if current_user.role not in [TeamRole.OWNER.value, TeamRole.ADMIN.value]:
            raise APIException(
                status_code=status.HTTP_403_FORBIDDEN,
                message="Only owner or admin can update inventory",
            )

        org_type_normalized = (current_user.organization_type or "").replace("-", " ").lower()
        media_owner_normalized = OrganizationType.MEDIA_OWNER.value.lower()
        if org_type_normalized != media_owner_normalized:
            raise APIException(
                status_code=status.HTTP_403_FORBIDDEN,
                message="Only media owners can update inventory",
            )

        # Load inventory within current user's company
        query = select(Inventory).where(Inventory.id == inventory_id)
        if current_user.company_name:
            query = query.where(Inventory.media_owner_name == current_user.company_name)

        result = await db.execute(query)
        inventory = result.scalar_one_or_none()
        if not inventory:
            raise APIException(
                status_code=status.HTTP_404_NOT_FOUND,
                message="Inventory not found",
            )

        # Ensure face_id is still unique for this media owner when changed
        target_media_owner = inventory.media_owner_name
        if data.face_id != inventory.face_id:
            face_query = select(Inventory).where(
                (Inventory.face_id == data.face_id)
                & (Inventory.media_owner_name == target_media_owner)
                & (Inventory.id != inventory.id)
            )
            face_result = await db.execute(face_query)
            if face_result.scalar_one_or_none():
                raise APIException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    message="Face ID already exists for this media owner",
                )

        # Backend concatenation for custom billboard type (same rule as create)
        billboard_type_value = data.billboard_type
        if (
            isinstance(billboard_type_value, str)
            and billboard_type_value.strip() == "Other"
            and data.custom_billboard_type
        ):
            custom = data.custom_billboard_type.strip()
            if custom:
                billboard_type_value = f"Other: {custom}"

        # Apply updates (keep media_owner_name as-is)
        inventory.face_id = data.face_id
        inventory.billboard_type = billboard_type_value
        inventory.is_indoor = data.is_indoor
        inventory.latitude = data.latitude
        inventory.longitude = data.longitude
        inventory.address = data.address
        inventory.height_from_ground = data.height_from_ground
        inventory.loop_timing = data.loop_timing
        inventory.azimuth_from_north = data.azimuth_from_north
        inventory.width = data.width
        inventory.height = data.height
        inventory.network_name = data.network_name
        inventory.status = data.status.value

        await db.flush()
        await db.refresh(inventory)

        return InventoryResponse.model_validate(inventory)

    @staticmethod
    async def delete_inventory(
        db: AsyncSession,
        current_user: User,
        face_id: str,
    ) -> None:
        """Delete an inventory (billboard) by face_id.

        - Only owner/admin of media owner organization can delete.
        - Restrict deletion to inventories under current user's company.
        """
        # Permission checks (same as create/update)
        if current_user.role not in [TeamRole.OWNER.value, TeamRole.ADMIN.value]:
            raise APIException(
                status_code=status.HTTP_403_FORBIDDEN,
                message="Only owner or admin can delete inventory",
            )

        org_type_normalized = (current_user.organization_type or "").replace("-", " ").lower()
        media_owner_normalized = OrganizationType.MEDIA_OWNER.value.lower()
        if org_type_normalized != media_owner_normalized:
            raise APIException(
                status_code=status.HTTP_403_FORBIDDEN,
                message="Only media owners can delete inventory",
            )

        # Find inventory by face_id within current user's company
        query = select(Inventory).where(Inventory.face_id == face_id)
        if current_user.company_name:
            query = query.where(Inventory.media_owner_name == current_user.company_name)

        result = await db.execute(query)
        inventory = result.scalar_one_or_none()
        if not inventory:
            raise APIException(
                status_code=status.HTTP_404_NOT_FOUND,
                message="Inventory not found",
            )

        await db.delete(inventory)
        await db.flush()


inventory_service = InventoryService()
