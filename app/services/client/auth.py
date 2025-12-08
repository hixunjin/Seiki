import random
import logging
from typing import Dict
from datetime import datetime, timedelta, UTC
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.models.user import User
from app.models.token import Token
from app.schemas.client.auth import UserRegister, UserResponse
from app.exceptions.http_exceptions import APIException
from app.services.common.redis import redis_client
from app.services.common.email import email_service
from app.core.security import AuthBase
from app.core.config import settings
from fastapi import status, BackgroundTasks

logger = logging.getLogger(__name__)

# Redis key prefixes
VERIFY_CODE_KEY = "verify_code:{email}"
VERIFY_CODE_COOLDOWN_KEY = "verify_code_cooldown:{email}"
RESET_CODE_KEY = "reset_code:{email}"
RESET_CODE_COOLDOWN_KEY = "reset_code_cooldown:{email}"

# Configuration
VERIFY_CODE_EXPIRE_SECONDS = 5 * 60  # 5 minutes
VERIFY_CODE_COOLDOWN_SECONDS = 60  # 60 seconds
RESET_CODE_EXPIRE_SECONDS = 5 * 60  # 5 minutes
RESET_CODE_COOLDOWN_SECONDS = 60  # 60 seconds


class ClientAuthService:
    @staticmethod
    def generate_verification_code() -> str:
        """Generate 6-digit verification code"""
        return str(random.randint(100000, 999999))

    @staticmethod
    async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
        """Get user by email"""
        query = select(User).where(User.email == email)
        result = await db.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def send_verification_code(email: str, background_tasks: BackgroundTasks) -> dict:
        """
        Send verification code to email

        Args:
            email: User email address
            background_tasks: FastAPI background tasks

        Returns:
            dict: Response with cooldown info

        Raises:
            APIException: If in cooldown period
        """
        # Check cooldown
        cooldown_key = VERIFY_CODE_COOLDOWN_KEY.format(email=email)
        if await redis_client.check_cooldown(cooldown_key):
            raise APIException(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Please wait 60 seconds before requesting a new code"
            )

        # Generate and store verification code
        code = ClientAuthService.generate_verification_code()
        code_key = VERIFY_CODE_KEY.format(email=email)
        await redis_client.set_with_ttl(code_key, code, VERIFY_CODE_EXPIRE_SECONDS)

        # Set cooldown
        await redis_client.set_cooldown(cooldown_key, VERIFY_CODE_COOLDOWN_SECONDS)

        # Send email asynchronously using SMTP
        html_content = f"""
        <html>
            <body>
                <h2>Welcome to Seiki!</h2>
                <p>Your verification code is: <strong>{code}</strong></p>
                <p>This verification code will expire in 5 minutes.</p>
            </body>
        </html>
        """
        background_tasks.add_task(
            email_service.send,
            to_emails=email,
            subject="Seiki - Email Verification Code",
            html_content=html_content
        )
        logger.info(f"Verification code sent to {email}")

        return {"message": "Verification code sent", "expires_in": VERIFY_CODE_EXPIRE_SECONDS}

    @staticmethod
    async def verify_email(db: AsyncSession, email: str, code: str) -> bool:
        """
        Verify email with verification code

        Args:
            db: Database session
            email: User email address
            code: Verification code

        Returns:
            bool: True if verification successful

        Raises:
            APIException: If code is invalid or expired
        """
        # Get stored code from Redis
        code_key = VERIFY_CODE_KEY.format(email=email)
        stored_code = await redis_client.get(code_key)

        if not stored_code:
            raise APIException(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Verification code expired or not found"
            )

        if stored_code != code:
            raise APIException(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Invalid verification code"
            )

        # Update user is_verified status
        stmt = update(User).where(User.email == email).values(is_verified=True)
        result = await db.execute(stmt)

        if result.rowcount == 0:
            raise APIException(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="User not found"
            )

        # Delete verification code from Redis
        await redis_client.delete(code_key)

        logger.info(f"Email verified successfully: {email}")
        return True

    @staticmethod
    async def register(
        db: AsyncSession,
        data: UserRegister,
        background_tasks: BackgroundTasks
    ) -> UserResponse:
        """
        Register a new user and send verification code

        Args:
            db: Database session
            data: User registration data
            background_tasks: FastAPI background tasks

        Returns:
            UserResponse: Created user data

        Raises:
            APIException: If email already exists
        """
        # Check if email already exists
        existing_user = await ClientAuthService.get_user_by_email(db, data.email)
        if existing_user:
            raise APIException(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Email already registered"
            )

        # Create new user
        user = User(
            email=data.email,
            hashed_password=User.get_password_hash(data.password),
            first_name=data.first_name,
            last_name=data.last_name,
            phone=data.phone,
            organization_type=data.organization_type.value,
            company_name=data.company_name,
            is_active=True,
            is_verified=False,
        )

        db.add(user)
        await db.flush()
        await db.refresh(user)

        # Send verification code after registration
        await ClientAuthService.send_verification_code(data.email, background_tasks)

        return UserResponse.model_validate(user)

    @staticmethod
    async def authenticate_user(db: AsyncSession, email: str, password: str) -> User | None:
        """Authenticate user by email and password"""
        user = await ClientAuthService.get_user_by_email(db, email)
        if not user or not user.verify_password(password):
            return None
        return user

    @staticmethod
    async def login(db: AsyncSession, email: str, password: str) -> Dict:
        """
        User login

        Args:
            db: Database session
            email: User email
            password: User password

        Returns:
            Dict: Token information

        Raises:
            APIException: If credentials are invalid or account is not verified
        """
        user = await ClientAuthService.authenticate_user(db, email, password)
        if not user:
            raise APIException(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Incorrect email or password"
            )

        if not user.is_verified:
            raise APIException(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Email not verified. Please verify your email first."
            )

        if not user.is_active:
            raise APIException(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Account is inactive"
            )

        # Mark old tokens as inactive
        stmt = update(Token).where(
            (Token.user_id == user.id) &
            (Token.is_active == True)
        ).values(is_active=False)
        await db.execute(stmt)

        # Generate new access token and refresh token
        access_token = AuthBase.create_access_token(
            str(user.id),
            scope="client",
            expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        )
        refresh_token = AuthBase.create_refresh_token(str(user.id))

        # Store new refresh token
        hashed_token = AuthBase.hash_token(refresh_token)
        token = Token(
            user_id=user.id,
            token=hashed_token,
            expires_at=datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
            is_active=True
        )
        db.add(token)
        await db.flush()

        logger.info(f"User logged in: {email}")

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer"
        }

    @staticmethod
    async def refresh_token(db: AsyncSession, refresh_token: str) -> Dict:
        """
        Refresh user token

        Args:
            db: Database session
            refresh_token: Refresh token

        Returns:
            Dict: New access token

        Raises:
            APIException: If refresh token is invalid
        """
        payload = AuthBase.verify_token(refresh_token, scope="refresh")
        if not payload:
            raise APIException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                message="Invalid refresh token"
            )

        user_id = payload.get("sub")
        token_query = select(Token).where(
            (Token.user_id == user_id) &
            (Token.is_active == True)
        )
        result = await db.execute(token_query)
        token = result.scalar_one_or_none()

        if not token or not AuthBase.verify_token_hash(refresh_token, token.token):
            raise APIException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                message="Invalid or expired refresh token"
            )

        # Update last used time
        token.last_used_at = datetime.now(UTC)
        await db.flush()

        # Generate new access token
        access_token = AuthBase.create_access_token(
            user_id,
            scope="client",
            expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        )

        return {
            "access_token": access_token,
            "token_type": "bearer"
        }

    @staticmethod
    async def logout(db: AsyncSession, refresh_token: str) -> None:
        """
        User logout

        Args:
            db: Database session
            refresh_token: Refresh token
        """
        payload = AuthBase.verify_token(refresh_token, scope="refresh")
        if not payload:
            return  # Ignore invalid token

        user_id = payload.get("sub")
        stmt = update(Token).where(
            (Token.user_id == user_id) &
            (Token.is_active == True)
        ).values(is_active=False)
        await db.execute(stmt)

        logger.info(f"User logged out: user_id={user_id}")

    @staticmethod
    async def send_reset_code(email: str, background_tasks: BackgroundTasks) -> dict:
        """
        Send password reset code to email

        Args:
            email: User email address
            background_tasks: FastAPI background tasks

        Returns:
            dict: Response with cooldown info

        Raises:
            APIException: If in cooldown period or user not found
        """
        # Check cooldown
        cooldown_key = RESET_CODE_COOLDOWN_KEY.format(email=email)
        if await redis_client.check_cooldown(cooldown_key):
            raise APIException(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Please wait 60 seconds before requesting a new code"
            )

        # Generate and store reset code
        code = ClientAuthService.generate_verification_code()
        code_key = RESET_CODE_KEY.format(email=email)
        await redis_client.set_with_ttl(code_key, code, RESET_CODE_EXPIRE_SECONDS)

        # Set cooldown
        await redis_client.set_cooldown(cooldown_key, RESET_CODE_COOLDOWN_SECONDS)

        # Send email asynchronously
        html_content = f"""
        <html>
            <body>
                <h2>Password Reset Request</h2>
                <p>Your password reset code is: <strong>{code}</strong></p>
                <p>This code will expire in 5 minutes.</p>
                <p>If you did not request this, please ignore this email.</p>
            </body>
        </html>
        """
        background_tasks.add_task(
            email_service.send,
            to_emails=email,
            subject="Seiki - Password Reset Code",
            html_content=html_content
        )
        logger.info(f"Password reset code sent to {email}")

        return {"message": "Reset code sent", "expires_in": RESET_CODE_EXPIRE_SECONDS}

    @staticmethod
    async def reset_password(
        db: AsyncSession,
        email: str,
        code: str,
        new_password: str,
        background_tasks: BackgroundTasks
    ) -> Dict:
        """
        Reset password with verification code and auto-login

        Args:
            db: Database session
            email: User email
            code: Reset verification code
            new_password: New password
            background_tasks: FastAPI background tasks

        Returns:
            Dict: Token information (auto-login)

        Raises:
            APIException: If code is invalid or user not found
        """
        # Verify reset code
        code_key = RESET_CODE_KEY.format(email=email)
        stored_code = await redis_client.get(code_key)

        if not stored_code:
            raise APIException(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Reset code expired or not found"
            )

        if stored_code != code:
            raise APIException(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Invalid reset code"
            )

        # Get user
        user = await ClientAuthService.get_user_by_email(db, email)
        if not user:
            raise APIException(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="User not found"
            )

        # Update password
        user.hashed_password = User.get_password_hash(new_password)
        await db.flush()

        # Delete reset code from Redis
        await redis_client.delete(code_key)

        logger.info(f"Password reset successfully for: {email}")

        # Auto-login: generate tokens
        # Mark old tokens as inactive
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
        token = Token(
            user_id=user.id,
            token=hashed_token,
            expires_at=datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
            is_active=True
        )
        db.add(token)
        await db.flush()

        logger.info(f"User auto-logged in after password reset: {email}")

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer"
        }


client_auth_service = ClientAuthService()
