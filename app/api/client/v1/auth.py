from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db, transaction
from app.schemas.client.auth import (
    UserRegister, UserResponse, SendVerificationCode, VerifyEmail,
    UserLogin, Token, RefreshToken, Logout,
    ForgotPasswordRequest, ResetPassword
)
from app.services.client.auth import client_auth_service
from app.schemas.response import ApiResponse

router = APIRouter()


@router.post("/register", response_model=UserResponse)
async def register(
    data: UserRegister,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    User registration

    Register a new user with email, password and profile information.
    After registration, a verification code will be sent to the email automatically.
    """
    async with transaction(db):
        result = await client_auth_service.register(db, data, background_tasks)
        return ApiResponse.success(data=result)


@router.post("/resend-code")
async def resend_verification_code(
    data: SendVerificationCode,
    background_tasks: BackgroundTasks
):
    """
    Resend verification code

    Resend verification code to the specified email.
    Rate limited to once per 60 seconds.
    """
    result = await client_auth_service.send_verification_code(data.email, background_tasks)
    return ApiResponse.success(data=result)


@router.post("/verify-email")
async def verify_email(
    data: VerifyEmail,
    db: AsyncSession = Depends(get_db)
):
    """
    Verify email

    Verify user email with the 6-digit verification code.
    After successful verification, user's is_verified status will be set to True.
    """
    async with transaction(db):
        await client_auth_service.verify_email(db, data.email, data.code)
        return ApiResponse.success_without_data()


@router.post("/login", response_model=Token)
async def login(
    data: UserLogin,
    db: AsyncSession = Depends(get_db)
):
    """
    User login

    Login with email and password.
    Returns access token and refresh token.
    User must have verified email to login.
    """
    async with transaction(db):
        result = await client_auth_service.login(db, data.email, data.password)
        return ApiResponse.success(data=result)


@router.post("/refresh", response_model=Token)
async def refresh_token(
    data: RefreshToken,
    db: AsyncSession = Depends(get_db)
):
    """
    Refresh token

    Get a new access token using refresh token.
    """
    async with transaction(db):
        result = await client_auth_service.refresh_token(db, data.refresh_token)
        return ApiResponse.success(data=result)


@router.post("/logout")
async def logout(
    data: Logout,
    db: AsyncSession = Depends(get_db)
):
    """
    User logout

    Invalidate the refresh token.
    """
    async with transaction(db):
        await client_auth_service.logout(db, data.refresh_token)
        return ApiResponse.success_without_data()


@router.post("/forgot-password")
async def forgot_password(
    data: ForgotPasswordRequest,
    background_tasks: BackgroundTasks
):
    """
    Request password reset

    Send a password reset code to the specified email.
    Rate limited to once per 60 seconds.
    """
    result = await client_auth_service.send_reset_code(data.email, background_tasks)
    return ApiResponse.success(data=result)


@router.post("/reset-password", response_model=Token)
async def reset_password(
    data: ResetPassword,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Reset password

    Reset password using the 6-digit verification code.
    After successful reset, user will be automatically logged in.
    Returns access token and refresh token.
    """
    async with transaction(db):
        result = await client_auth_service.reset_password(
            db, data.email, data.code, data.new_password, background_tasks
        )
        return ApiResponse.success(data=result)
