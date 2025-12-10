from enum import Enum
from typing import Optional
from pydantic import Field
from app.schemas.base import BaseSchema, BaseResponseSchema


class BillboardType(str, Enum):
    DIGITAL_BRIDGE = "Digital Bridge"
    STATIC_UNIPOLE = "Static Unipole"
    DIGITAL_UNIPOLE = "Digital Unipole"
    DIGITAL_HOARDING = "Digital Hoarding"
    DIGITAL_SCREEN = "Digital Screen"
    DIGITAL_GATE = "Digital Gate"
    MAXI_BILLBOARDS = "Maxi Billboards"
    OTHER = "Other"


class InventoryStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class InventoryCreate(BaseSchema):
    face_id: str = Field(...)
    billboard_type: str = Field(...)
    custom_billboard_type: Optional[str] = None
    latitude: float = Field(...)
    longitude: float = Field(...)
    height_from_ground: Optional[float] = None
    loop_timing: Optional[float] = None
    address: Optional[str] = None
    is_indoor: bool = Field(...)
    azimuth_from_north: float = Field(...)
    width: float = Field(...)
    height: float = Field(...)
    media_owner_name: Optional[str] = None
    network_name: str = Field(...)
    status: InventoryStatus = Field(...)


class InventoryResponse(BaseResponseSchema):
    face_id: str
    billboard_type: str
    latitude: float
    longitude: float
    height_from_ground: Optional[float] = None
    loop_timing: Optional[float] = None
    address: Optional[str] = None
    is_indoor: bool
    azimuth_from_north: float
    width: float
    height: float
    media_owner_name: str
    network_name: str
    status: InventoryStatus


class InventoryUpdate(BaseSchema):
    """Payload for updating an existing inventory (billboard)."""

    face_id: str = Field(...)
    billboard_type: str = Field(...)
    custom_billboard_type: Optional[str] = None
    latitude: float = Field(...)
    longitude: float = Field(...)
    height_from_ground: Optional[float] = None
    loop_timing: Optional[float] = None
    address: Optional[str] = None
    is_indoor: bool = Field(...)
    azimuth_from_north: float = Field(...)
    width: float = Field(...)
    height: float = Field(...)
    # Media owner is effectively read-only from client perspective; backend will
    # always keep the existing media_owner_name for the inventory record.
    media_owner_name: Optional[str] = None
    network_name: str = Field(...)
    status: InventoryStatus = Field(...)


class InventoryListFilter(BaseSchema):
    """Query params for inventory list (right side table)."""
    # Generic keyword for searching face_id, network_name, or media_owner_name
    keyword: Optional[str] = None
    # Filter by billboard type (exact match on stored value)
    billboard_type: Optional[str] = None
    media_owner_name: Optional[str] = None
    network_name: Optional[str] = None
    face_id: Optional[str] = None
    status: Optional[InventoryStatus] = None
    page: int = 1
    per_page: int = 10


class InventoryOwnerNode(BaseSchema):
    media_owner_name: str
    total: int


class InventoryNetworkNode(BaseSchema):
    network_name: str
    total: int


class InventoryFaceNode(BaseSchema):
    face_id: str
