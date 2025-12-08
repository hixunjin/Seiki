import secrets
import logging
from typing import Dict
from datetime import datetime, timedelta, UTC
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.models.user import User, TeamRole as ModelTeamRole, MemberStatus
from app.models.token import Token
from app.schemas.client.team import TeamRole
from app.exceptions.http_exceptions import APIException
from app.services.common.redis import redis_client
from app.services.common.email import email_service
from app.core.security import AuthBase
from app.core.config import settings
from fastapi import status, BackgroundTasks

logger = logging.getLogger(__name__)

# Redis key prefixes
INVITE_TOKEN_KEY = "invite_token:{token}"
INVITE_EMAIL_KEY = "invite_email:{email}"

# Configuration
INVITE_TOKEN_EXPIRE_SECONDS = 7 * 24 * 60 * 60  # 7 days


class TeamService:
    @staticmethod
    def generate_invite_token() -> str:
        """Generate a secure random invite token"""
        return secrets.token_urlsafe(32)

    @staticmethod
    async def get_user_by_email_and_company(
        db: AsyncSession,
        email: str,
        organization_type: str,
        company_name: str
    ) -> User | None:
        """Get user by email within the same company"""
        query = select(User).where(
            (User.email == email) &
            (User.organization_type == organization_type) &
            (User.company_name == company_name)
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
        """Get user by email"""
        query = select(User).where(User.email == email)
        result = await db.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def invite_member(
        db: AsyncSession,
        current_user: User,
        email: str,
        role: TeamRole,
        background_tasks: BackgroundTasks
    ) -> dict:
        """
        Invite a new team member

        Args:
            db: Database session
            current_user: The user sending the invitation (must be owner/admin)
            email: Email of the person to invite
            role: Role to assign (admin/operator)
            background_tasks: FastAPI background tasks

        Returns:
            dict: Success message with expiration info

        Raises:
            APIException: If permission denied or user already exists
        """
        # Permission check: only owner/admin can invite
        if current_user.role not in [ModelTeamRole.OWNER.value, ModelTeamRole.ADMIN.value]:
            raise APIException(
                status_code=status.HTTP_403_FORBIDDEN,
                message="Only owner or admin can invite team members"
            )

        if current_user.member_status != MemberStatus.ACTIVE.value:
            raise APIException(
                status_code=status.HTTP_403_FORBIDDEN,
                message="Your account is not active"
            )

        # Check if email already exists in the same company
        existing_user = await TeamService.get_user_by_email(db, email)
        if existing_user:
            if (existing_user.organization_type == current_user.organization_type and
                existing_user.company_name == current_user.company_name):
                if existing_user.member_status == MemberStatus.ACTIVE.value:
                    raise APIException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        message="This email is already a team member"
                    )
                # If pending, we can resend invitation
            else:
                # Email exists but in different company
                raise APIException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    message="This email is already registered"
                )

        # Generate invite token
        invite_token = TeamService.generate_invite_token()

        # Create or update user record
        if existing_user and existing_user.member_status == MemberStatus.PENDING.value:
            # Update existing pending user
            existing_user.role = role.value
            user = existing_user
        else:
            # Create new pending user
            user = User(
                email=email,
                hashed_password=User.get_password_hash(secrets.token_urlsafe(16)),  # Random password
                first_name="",
                last_name="",
                organization_type=current_user.organization_type,
                company_name=current_user.company_name,
                role=role.value,
                member_status=MemberStatus.PENDING.value,
                is_active=False,
                is_verified=False,
            )
            db.add(user)

        await db.flush()

        # Store invite token in Redis
        # Key: invite_token:{token} -> email
        token_key = INVITE_TOKEN_KEY.format(token=invite_token)
        await redis_client.set_with_ttl(token_key, email, INVITE_TOKEN_EXPIRE_SECONDS)

        # Also store email -> token mapping for potential resend/cancel
        email_key = INVITE_EMAIL_KEY.format(email=email)
        await redis_client.set_with_ttl(email_key, invite_token, INVITE_TOKEN_EXPIRE_SECONDS)

        # Send invitation email
        invite_link = f"https://seiki.co/accept-invite?token={invite_token}"
        html_content = f"""
        <html>
            <body>
                <h2>You've been invited to join {current_user.company_name} on Seiki!</h2>
                <p>You have been invited as a <strong>{role.value}</strong>.</p>
                <p>Click the link below to accept the invitation and set up your account:</p>
                <p><a href="{invite_link}">{invite_link}</a></p>
                <p>This invitation will expire in 7 days.</p>
                <p>If you did not expect this invitation, please ignore this email.</p>
            </body>
        </html>
        """
        background_tasks.add_task(
            email_service.send,
            to_emails=email,
            subject=f"Seiki - You're invited to join {current_user.company_name}",
            html_content=html_content
        )

        logger.info(f"Invitation sent to {email} by {current_user.email}")

        return {
            "message": "Invitation sent successfully",
            "expires_in": INVITE_TOKEN_EXPIRE_SECONDS
        }

    @staticmethod
    async def accept_invite(
        db: AsyncSession,
        token: str,
        first_name: str,
        last_name: str,
        password: str
    ) -> Dict:
        """
        Accept team invitation and complete registration

        Args:
            db: Database session
            token: Invite token from email link
            first_name: User's first name
            last_name: User's last name
            password: User's chosen password

        Returns:
            Dict: Token information (auto-login)

        Raises:
            APIException: If token is invalid or expired
        """
        # Get email from token
        token_key = INVITE_TOKEN_KEY.format(token=token)
        email = await redis_client.get(token_key)

        if not email:
            raise APIException(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Invalid or expired invitation"
            )

        # Get user by email
        user = await TeamService.get_user_by_email(db, email)

        if not user:
            raise APIException(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="User not found"
            )

        if user.member_status != MemberStatus.PENDING.value:
            raise APIException(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="This invitation has already been used"
            )

        # Update user information
        user.first_name = first_name
        user.last_name = last_name
        user.hashed_password = User.get_password_hash(password)
        user.is_active = True
        user.is_verified = True
        user.member_status = MemberStatus.ACTIVE.value

        await db.flush()

        # Delete invite token from Redis
        await redis_client.delete(token_key)
        email_key = INVITE_EMAIL_KEY.format(email=email)
        await redis_client.delete(email_key)

        logger.info(f"Invitation accepted by {email}")

        # Auto-login: generate tokens
        # Mark old tokens as inactive (shouldn't have any, but just in case)
        stmt = update(Token).where(
            (Token.user_id == user.id) &
            (Token.is_active == True)
        ).values(is_active=False)
        await db.execute(stmt)

        # Generate new tokens
        access_token = AuthBase.create_access_token(
            str(user.id),
            scope="client",
            expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        )
        refresh_token = AuthBase.create_refresh_token(str(user.id))

        # Store new refresh token
        hashed_token = AuthBase.hash_token(refresh_token)
        token_record = Token(
            user_id=user.id,
            token=hashed_token,
            expires_at=datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
            is_active=True
        )
        db.add(token_record)
        await db.flush()

        logger.info(f"User auto-logged in after accepting invite: {email}")

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer"
        }

    @staticmethod
    async def _get_member_in_same_company(
        db: AsyncSession,
        user_id: int,
        current_user: User,
    ) -> User:
        """Helper: get member by id within current user's company"""
        query = select(User).where(
            (User.id == user_id)
            & (User.organization_type == current_user.organization_type)
            & (User.company_name == current_user.company_name)
        )
        result = await db.execute(query)
        member = result.scalar_one_or_none()
        if not member:
            raise APIException(
                status_code=status.HTTP_404_NOT_FOUND,
                message="Member not found",
            )
        return member

    @staticmethod
    async def deactivate_member(
        db: AsyncSession,
        current_user: User,
        member_id: int,
    ) -> None:
        """Deactivate a team member (set member_status=deactivated, is_active=False)."""
        # Permission check: only owner/admin & active
        if current_user.role not in [ModelTeamRole.OWNER.value, ModelTeamRole.ADMIN.value]:
            raise APIException(
                status_code=status.HTTP_403_FORBIDDEN,
                message="Only owner or admin can manage team members",
            )
        if current_user.member_status != MemberStatus.ACTIVE.value:
            raise APIException(
                status_code=status.HTTP_403_FORBIDDEN,
                message="Your account is not active",
            )

        member = await TeamService._get_member_in_same_company(db, member_id, current_user)

        # Optional: prevent owner from deactivating themselves
        if member.id == current_user.id:
            raise APIException(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="You cannot deactivate yourself",
            )

        member.member_status = MemberStatus.DEACTIVATED.value
        member.is_active = False

        # Note: 不删除已有的 token，由前端控制下次登录
        await db.flush()
        logger.info(f"Member deactivated: {member.email} by {current_user.email}")

    @staticmethod
    async def activate_member(
        db: AsyncSession,
        current_user: User,
        member_id: int,
    ) -> None:
        """Activate a team member (set member_status=active, is_active=True)."""
        # Permission check: only owner/admin & active
        if current_user.role not in [ModelTeamRole.OWNER.value, ModelTeamRole.ADMIN.value]:
            raise APIException(
                status_code=status.HTTP_403_FORBIDDEN,
                message="Only owner or admin can manage team members",
            )
        if current_user.member_status != MemberStatus.ACTIVE.value:
            raise APIException(
                status_code=status.HTTP_403_FORBIDDEN,
                message="Your account is not active",
            )

        member = await TeamService._get_member_in_same_company(db, member_id, current_user)

        member.member_status = MemberStatus.ACTIVE.value
        member.is_active = True

        await db.flush()
        logger.info(f"Member activated: {member.email} by {current_user.email}")

    @staticmethod
    async def change_role_admin_to_operator(
        db: AsyncSession,
        current_user: User,
        member_id: int,
    ) -> None:
        """Change member role from admin to operator. Only owner can perform this."""
        # Only owner can change roles
        if current_user.role != ModelTeamRole.OWNER.value:
            raise APIException(
                status_code=status.HTTP_403_FORBIDDEN,
                message="Only owner can change member roles",
            )
        if current_user.member_status != MemberStatus.ACTIVE.value:
            raise APIException(
                status_code=status.HTTP_403_FORBIDDEN,
                message="Your account is not active",
            )

        member = await TeamService._get_member_in_same_company(db, member_id, current_user)

        # 不允许修改 owner
        if member.role == ModelTeamRole.OWNER.value:
            raise APIException(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Cannot change role of owner",
            )

        member.role = ModelTeamRole.OPERATOR.value
        await db.flush()
        logger.info(f"Member role changed admin->operator: {member.email} by {current_user.email}")

    @staticmethod
    async def change_role_operator_to_admin(
        db: AsyncSession,
        current_user: User,
        member_id: int,
    ) -> None:
        """Change member role from operator to admin. Only owner can perform this."""
        # Only owner can change roles
        if current_user.role != ModelTeamRole.OWNER.value:
            raise APIException(
                status_code=status.HTTP_403_FORBIDDEN,
                message="Only owner can change member roles",
            )
        if current_user.member_status != MemberStatus.ACTIVE.value:
            raise APIException(
                status_code=status.HTTP_403_FORBIDDEN,
                message="Your account is not active",
            )

        member = await TeamService._get_member_in_same_company(db, member_id, current_user)

        # 不允许修改 owner
        if member.role == ModelTeamRole.OWNER.value:
            raise APIException(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Cannot change role of owner",
            )

        member.role = ModelTeamRole.ADMIN.value
        await db.flush()
        logger.info(f"Member role changed operator->admin: {member.email} by {current_user.email}")


team_service = TeamService()
