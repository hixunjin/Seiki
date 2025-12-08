from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional
from enum import Enum


class OrganizationType(str, Enum):
    """Organization type enum for validation"""
    MEDIA_OWNER = "media owner"
    MEDIA_AGENCY = "media agency"
    BRAND_ADVERTISER = "brand advertiser"


class SendVerificationCode(BaseModel):
    """Send verification code request schema"""
    email: EmailStr


class VerifyEmail(BaseModel):
    """Verify email request schema"""
    email: EmailStr
    code: str

    @field_validator("code")
    @classmethod
    def validate_code(cls, v: str) -> str:
        if not v or len(v) != 6 or not v.isdigit():
            raise ValueError("Verification code must be 6 digits")
        return v


class ForgotPasswordRequest(BaseModel):
    """Request password reset code"""
    email: EmailStr


class ResetPassword(BaseModel):
    """Reset password with verification code"""
    email: EmailStr
    code: str
    new_password: str
    confirm_password: str

    @field_validator("code")
    @classmethod
    def validate_code(cls, v: str) -> str:
        if not v or len(v) != 6 or not v.isdigit():
            raise ValueError("Verification code must be 6 digits")
        return v

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v

    @field_validator("confirm_password")
    @classmethod
    def validate_confirm_password(cls, v: str, info) -> str:
        password = info.data.get("new_password")
        if password and v != password:
            raise ValueError("Passwords do not match")
        return v


class UserRegister(BaseModel):
    """User registration request schema"""
    first_name: str
    last_name: str
    email: EmailStr
    phone: Optional[str] = None
    organization_type: OrganizationType
    company_name: Optional[str] = None
    password: str
    confirm_password: str

    @field_validator("first_name", "last_name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Name cannot be empty")
        return v.strip()

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v

    @field_validator("confirm_password")
    @classmethod
    def validate_confirm_password(cls, v: str, info) -> str:
        password = info.data.get("password")
        if password and v != password:
            raise ValueError("Passwords do not match")
        return v


class UserResponse(BaseModel):
    """User response schema"""
    id: int
    email: str
    first_name: str
    last_name: str
    phone: Optional[str] = None
    organization_type: str
    company_name: Optional[str] = None
    is_active: bool
    is_verified: bool

    class Config:
        from_attributes = True


class UserLogin(BaseModel):
    """User login request schema"""
    email: EmailStr
    password: str


class Token(BaseModel):
    """Token response schema"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshToken(BaseModel):
    """Refresh token request schema"""
    refresh_token: str


class Logout(BaseModel):
    """Logout request schema"""
    refresh_token: str
