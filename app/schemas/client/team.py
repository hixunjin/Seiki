from pydantic import BaseModel, EmailStr, field_validator
from enum import Enum
from typing import Optional


class TeamRole(str, Enum):
    """Team role enum for invitation and filtering"""
    OWNER = "owner"
    ADMIN = "admin"
    OPERATOR = "operator"


class MemberStatus(str, Enum):
    """Team member status enum for filtering"""
    ACTIVE = "active"
    DEACTIVATED = "deactivated"
    PENDING = "pending"


class TeamInviteRequest(BaseModel):
    """Request to invite a team member"""
    email: EmailStr
    role: TeamRole


class AcceptInviteRequest(BaseModel):
    """Request to accept team invitation"""
    token: str
    first_name: str
    last_name: str
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


class TeamMemberFilter(BaseModel):
    """Query parameters for team member list"""
    keyword: Optional[str] = None  # search by name or email
    status: Optional[MemberStatus] = None
    role: Optional[TeamRole] = None
    page: int = 1
    per_page: int = 10
