from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from app.db.session import get_db, transaction
from app.schemas.client.team import (
    TeamInviteRequest,
    AcceptInviteRequest,
    TeamMemberFilter,
)
from app.schemas.client.auth import Token
from app.services.client.team import team_service
from app.schemas.response import ApiResponse
from app.api.client.deps import get_current_user
from app.models.user import User

router = APIRouter()


@router.post("/invite")
async def invite_member(
    data: TeamInviteRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Invite a team member

    Send an invitation email to a new team member.
    Only owner or admin can invite new members.
    The invited user will receive an email with a link to complete registration.
    """
    async with transaction(db):
        result = await team_service.invite_member(
            db=db,
            current_user=current_user,
            email=data.email,
            role=data.role,
            background_tasks=background_tasks
        )
        return ApiResponse.success(data=result)


@router.get("/members")
async def list_members(
    filters: TeamMemberFilter = Depends(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List team members with filtering and pagination

    - keyword: search by name or email
    - status: member status (active/pending/deactivated)
    - role: team role (owner/admin/operator)
    """
    # Base query: only members in the same company as current user
    query = select(User).where(
        User.organization_type == current_user.organization_type,
        User.company_name == current_user.company_name,
    )

    # Keyword search on name or email
    if filters.keyword:
        kw = f"%{filters.keyword.strip()}%"
        query = query.where(
            or_(
                User.first_name.ilike(kw),
                User.last_name.ilike(kw),
                User.email.ilike(kw),
            )
        )

    # Filter by status
    if filters.status is not None:
        query = query.where(User.member_status == filters.status.value)

    # Filter by role
    if filters.role is not None:
        query = query.where(User.role == filters.role.value)

    # Transform users to a simplified structure matching UI expectations
    def transform(items):
        result = []
        for u in items:
            name = f"{(u.first_name or '').strip()} {(u.last_name or '').strip()}".strip()
            result.append(
                {
                    "id": u.id,
                    "name": name,
                    "email": u.email,
                    "role": u.role,
                    "status": u.member_status,
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


@router.post("/members/{member_id}/deactivate")
async def deactivate_member(
    member_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Deactivate a team member.

    Only owner or admin in the same company can perform this action.
    """
    async with transaction(db):
        await team_service.deactivate_member(
            db=db,
            current_user=current_user,
            member_id=member_id,
        )
        return ApiResponse.success_without_data()


@router.post("/members/{member_id}/make-operator")
async def make_operator(
    member_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Change member role from admin to operator.

    Only media owner in the same company can perform this action.
    """
    async with transaction(db):
        await team_service.change_role_admin_to_operator(
            db=db,
            current_user=current_user,
            member_id=member_id,
        )
        return ApiResponse.success_without_data()


@router.post("/members/{member_id}/make-admin")
async def make_admin(
    member_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Change member role from operator to admin.

    Only media owner in the same company can perform this action.
    """
    async with transaction(db):
        await team_service.change_role_operator_to_admin(
            db=db,
            current_user=current_user,
            member_id=member_id,
        )
        return ApiResponse.success_without_data()


@router.post("/members/{member_id}/activate")
async def activate_member(
    member_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Activate a team member.

    Only owner or admin in the same company can perform this action.
    """
    async with transaction(db):
        await team_service.activate_member(
            db=db,
            current_user=current_user,
            member_id=member_id,
        )
        return ApiResponse.success_without_data()


@router.post("/accept-invite", response_model=Token)
async def accept_invite(
    data: AcceptInviteRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Accept team invitation

    Complete registration by providing personal information and password.
    After successful acceptance, user will be automatically logged in.
    Returns access token and refresh token.
    """
    async with transaction(db):
        result = await team_service.accept_invite(
            db=db,
            token=data.token,
            first_name=data.first_name,
            last_name=data.last_name,
            password=data.password
        )
        return ApiResponse.success(data=result)
