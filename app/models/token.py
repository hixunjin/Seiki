from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .base import BaseModel


class Token(BaseModel):
    __tablename__ = "tokens"

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    token = Column(String(255), unique=True, index=True)  # 存储hashed refresh token
    expires_at = Column(DateTime, nullable=False)
    last_used_at = Column(DateTime, default=func.now(), onupdate=func.now())
    is_active = Column(Boolean, default=True)

    user = relationship("User", backref="tokens")


class AdminToken(BaseModel):
    __tablename__ = "admin_tokens"

    admin_id = Column(Integer, ForeignKey("admins.id"), nullable=False)
    token = Column(String(255), unique=True, index=True)  # 存储hashed refresh token
    expires_at = Column(DateTime, nullable=False)
    last_used_at = Column(DateTime, default=func.now(), onupdate=func.now())
    is_active = Column(Boolean, default=True)

    admin = relationship("Admin", backref="admin_tokens")
