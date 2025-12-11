from sqlalchemy import Column, Integer, String, Text, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


class MediaPlan(BaseModel):
    """Media plan model.

    A media plan groups multiple campaigns together with an optional budget.
    """

    __tablename__ = "media_plans"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # Basic fields
    name = Column(String(255), nullable=False, comment="Media plan name")
    budget = Column(Integer, nullable=True, comment="Plan budget in EUR (optional)")
    description = Column(Text, nullable=True, comment="Plan description")

    # Ownership
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True, comment="Creator user ID")

    # Relations: many-to-many to campaigns (one-way for now)
    campaigns = relationship(
        "Campaign",
        secondary="media_plan_campaigns",
        lazy="selectin",
    )


class MediaPlanCampaign(BaseModel):
    """Junction table between media plans and campaigns (many-to-many)."""

    __tablename__ = "media_plan_campaigns"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    media_plan_id = Column(
        Integer,
        ForeignKey("media_plans.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Media plan ID",
    )

    campaign_id = Column(
        Integer,
        ForeignKey("campaigns.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Campaign ID",
    )

    __table_args__ = (
        UniqueConstraint("media_plan_id", "campaign_id", name="uq_media_plan_campaign"),
    )
