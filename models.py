"""
FreshElephant 🐘 - 数据模型
大象永不忘记，食物不再浪费
"""

from dataclasses import dataclass
from datetime import date, timedelta
from enum import Enum


class StorageZone(Enum):
    """冰箱分区"""
    FRIDGE  = "冷藏"   # 0-4°C，蔬菜水果熟食
    FREEZER = "冷冻"   # -18°C，肉类冷冻食品
    FRESH   = "保鲜"   # 蔬果保鲜抽屉


# 肉类关键词（用于分装提示）
MEAT_KEYWORDS = ["猪肉", "牛肉", "羊肉", "鸡肉", "鸡胸", "鸡腿", "鸭肉", "猪排",
                 "五花肉", "排骨", "虾", "鱼", "三文鱼", "螃蟹"]


@dataclass
class FridgeItem:
    """冰箱里的一个食材"""

    # ── 必填字段（创建时必须传入） ──
    name: str           # 食材名称（如：鸡胸肉、西兰花）
    zone: StorageZone   # 存放区域
    quantity: str       # 原始数量描述（如：500g、1颗、2包）
    date_added: date    # 放入冰箱的日期
    expiry_days: int    # 从放入当天算，能存多少天

    # ── 可选字段（有默认值，可以不传） ──
    item_id: str = ""   # 唯一ID（add_item 时自动生成）
    notes: str = ""     # 备注
    amount: float = 0.0 # 当前剩余数量（0 表示不追踪精确用量）
    unit: str = ""      # 单位（g、个、份、包、ml 等）
    portions: int = 1   # 分装份数（>1 表示已分装入多份）

    @property
    def expiry_date(self) -> date:
        return self.date_added + timedelta(days=self.expiry_days)

    @property
    def days_remaining(self) -> int:
        return (self.expiry_date - date.today()).days

    @property
    def status(self) -> str:
        d = self.days_remaining
        if d < 0:
            return f"❌ 已过期 {abs(d)} 天"
        elif d == 0:
            return "🚨 今天到期！"
        elif d <= 2:
            return f"⚠️  还剩 {d} 天（即将到期！）"
        else:
            return f"✅ 还剩 {d} 天"

    @property
    def quantity_display(self) -> str:
        """显示用的数量字符串"""
        if self.amount > 0:
            if self.portions > 1:
                return f"{self.amount}{self.unit}（已分{self.portions}份）"
            return f"{self.amount}{self.unit}"
        return self.quantity

    @property
    def is_meat(self) -> bool:
        """是否是肉类（用于分装提示）"""
        return any(k in self.name for k in MEAT_KEYWORDS)

    @property
    def is_expiring_soon(self) -> bool:
        return 0 <= self.days_remaining <= 2

    @property
    def is_expired(self) -> bool:
        return self.days_remaining < 0

    @property
    def is_ok(self) -> bool:
        return not self.is_expired  # DRY：复用 is_expired，避免逻辑重复

    def use_amount(self, used: float) -> float:
        """
        扣减使用量，返回剩余量。
        如果剩余<=0返回0.0（调用方负责删除该item）。
        """
        if self.amount <= 0:
            return 0.0  # 未追踪数值，无法扣减（保持 float 类型一致）
        self.amount = max(0.0, self.amount - used)
        return self.amount

    def to_dict(self) -> dict:
        return {
            "item_id":     self.item_id,
            "name":        self.name,
            "zone":        self.zone.value,
            "quantity":    self.quantity,
            "date_added":  self.date_added.isoformat(),
            "expiry_days": self.expiry_days,
            "notes":       self.notes,
            "amount":      self.amount,
            "unit":        self.unit,
            "portions":    self.portions,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "FridgeItem":
        zone_map = {z.value: z for z in StorageZone}
        return cls(
            item_id=data["item_id"],
            name=data["name"],
            zone=zone_map[data["zone"]],
            quantity=data["quantity"],
            date_added=date.fromisoformat(data["date_added"]),
            expiry_days=data["expiry_days"],
            notes=data.get("notes", ""),
            amount=data.get("amount", 0.0),
            unit=data.get("unit", ""),
            portions=data.get("portions", 1),
        )
