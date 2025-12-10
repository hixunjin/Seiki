from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Date,
    ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class Campaign(BaseModel):
    """Campaign (活动) model.

    Stores campaign basic info and targeting filters.
    Related to inventories via CampaignInventory (many-to-many).
    """

    __tablename__ = "campaigns"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # ========== 基础信息 ==========
    name = Column(String(255), nullable=False, comment="活动名称")
    price_eur = Column(Integer, nullable=False, comment="价格（欧元）")
    description = Column(Text, nullable=True, comment="描述")

    # ========== 时间定向 ==========
    start_date = Column(Date, nullable=False, comment="活动开始日期")
    end_date = Column(Date, nullable=False, comment="活动结束日期")

    # ========== 地理定向 ==========
    country_code = Column(
        String(2), nullable=False, default="SA", comment="国家代码，默认沙特"
    )
    city = Column(String(100), nullable=True, comment="城市")

    # ========== 人群定向 ==========
    # 性别：all / male / female
    gender = Column(String(10), nullable=False, default="all", comment="性别定向")
    # 年龄段（多选），存 JSON 字符串，如 '["20-24","30-34"]'
    age_ranges = Column(Text, nullable=True, comment="年龄段列表 JSON")

    # ========== 社会职业 & 出行 & 兴趣点 ==========
    # 社会职业类别：CSP_PLUS / CSP_MINUS / OTHER
    socio_professional_category = Column(
        String(10), nullable=True, comment="社会职业类别"
    )
    # 出行模式（多选），存 JSON 字符串，如 '["Driving","Walking"]'
    mobility_modes = Column(Text, nullable=True, comment="出行模式列表 JSON")
    # 兴趣点类别（多选），存 JSON 字符串，如 '["Education","Transit"]'
    poi_categories = Column(Text, nullable=True, comment="兴趣点类别列表 JSON")

    # ========== 归属 ==========
    created_by = Column(Integer, nullable=True, comment="创建人用户ID")

    # ========== 关系 ==========
    # 通过中间表关联的广告牌列表
    inventories = relationship(
        "Inventory",
        secondary="campaign_inventories",
        back_populates="campaigns",
        lazy="selectin",
    )


class CampaignInventory(BaseModel):
    """Campaign-Inventory association table (中间表).

    Implements many-to-many relationship between campaigns and inventories.
    """

    __tablename__ = "campaign_inventories"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    campaign_id = Column(
        Integer,
        ForeignKey("campaigns.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="活动ID",
    )
    inventory_id = Column(
        Integer,
        ForeignKey("inventories.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="广告牌ID",
    )

    # 唯一约束：同一活动不能重复关联同一广告牌
    __table_args__ = (
        UniqueConstraint("campaign_id", "inventory_id", name="uq_campaign_inventory"),
    )
