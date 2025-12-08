from sqlalchemy import Boolean, Column, Integer, String, TIMESTAMP
from sqlalchemy.sql import func
from .base import BaseModel
from passlib.context import CryptContext
import enum

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")



# Organization type enum
class OrganizationType(str, enum.Enum):
    """Organization type enum"""
    MEDIA_OWNER = "media owner"
    MEDIA_AGENCY = "media agency"
    BRAND_ADVERTISER = "brand advertiser"


class TeamRole(str, enum.Enum):
    """Team role enum within an organization"""
    OWNER = "owner"
    ADMIN = "admin"
    OPERATOR = "operator"


class MemberStatus(str, enum.Enum):
    """Team member status enum"""
    ACTIVE = "active"
    DEACTIVATED = "deactivated"
    PENDING = "pending"


class User(BaseModel):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    phone = Column(String(50), nullable=True)
    organization_type = Column(String(50), nullable=False)
    company_name = Column(String(255), nullable=True)
    role = Column(String(50), nullable=False, default=TeamRole.OWNER.value)
    member_status = Column(String(50), nullable=False, default=MemberStatus.ACTIVE.value)
    avatar = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    last_active_at = Column(TIMESTAMP(timezone=True), nullable=True, default=func.now())

    @staticmethod
    def get_password_hash(password: str) -> str:
        return pwd_context.hash(password)

    def verify_password(self, plain_password: str) -> bool:
        return pwd_context.verify(plain_password, self.hashed_password)

