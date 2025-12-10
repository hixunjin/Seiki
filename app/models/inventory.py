from sqlalchemy import Column, Integer, String, Float, Boolean
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class Inventory(BaseModel):
    __tablename__ = "inventories"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    face_id = Column(String(255), nullable=False, index=True)
    billboard_type = Column(String(255), nullable=False)
    is_indoor = Column(Boolean, nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    address = Column(String(512), nullable=True)
    height_from_ground = Column(Float, nullable=True)
    loop_timing = Column(Float, nullable=True)
    azimuth_from_north = Column(Float, nullable=False)
    width = Column(Float, nullable=False)
    height = Column(Float, nullable=False)
    network_name = Column(String(255), nullable=False)
    media_owner_name = Column(String(255), nullable=False)
    status = Column(String(50), nullable=False, default="active")

    # 关联的活动列表（多对多，通过中间表）
    campaigns = relationship(
        "Campaign",
        secondary="campaign_inventories",
        back_populates="inventories",
        lazy="selectin",
    )
