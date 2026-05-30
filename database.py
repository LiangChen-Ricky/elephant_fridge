"""
FreshElephant 🐘 - 本地数据库（JSON文件存储）
"""

import json
import uuid
from pathlib import Path

from models import FridgeItem, StorageZone

DB_FILE = Path("fridge_data.json")


def _load_raw() -> list[dict]:
    """读取 JSON 数据文件。文件损坏时自动备份并重置，避免程序崩溃。"""
    if not DB_FILE.exists():
        return []
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        backup = DB_FILE.with_suffix(".json.bak")
        DB_FILE.rename(backup)
        print(f"⚠️  数据文件损坏，已备份至 {backup.name}，冰箱数据已重置。")
        return []


def _save_raw(data: list[dict]):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def add_item(item: FridgeItem) -> FridgeItem:
    """添加食材，返回带ID的item"""
    item.item_id = str(uuid.uuid4())[:8]
    data = _load_raw()
    data.append(item.to_dict())
    _save_raw(data)
    print(f"✅ 已添加：{item.name}（ID: {item.item_id}），到期日：{item.expiry_date}")
    return item


def get_all_items() -> list[FridgeItem]:
    return [FridgeItem.from_dict(d) for d in _load_raw()]


def get_ok_items() -> list[FridgeItem]:
    return [i for i in get_all_items() if i.is_ok]


def get_expiring_soon() -> list[FridgeItem]:
    return [i for i in get_all_items() if i.is_expiring_soon]


def get_expired_items() -> list[FridgeItem]:
    return [i for i in get_all_items() if i.is_expired]


def get_alert_items() -> tuple[list[FridgeItem], list[FridgeItem]]:
    """
    一次读文件，返回 (即将到期列表, 已过期列表)。
    避免分别调用时读两次文件。
    """
    all_items = get_all_items()
    expiring = [i for i in all_items if i.is_expiring_soon]
    expired  = [i for i in all_items if i.is_expired]
    return expiring, expired


def get_item_by_id(item_id: str) -> FridgeItem | None:
    for item in get_all_items():
        if item.item_id == item_id:
            return item
    return None


def update_item(item: FridgeItem) -> bool:
    """更新已有食材的数据（保存修改后的item）"""
    data = _load_raw()
    for i, d in enumerate(data):
        if d["item_id"] == item.item_id:
            data[i] = item.to_dict()
            _save_raw(data)
            return True
    return False


def use_item(item_id: str, amount_used: float) -> tuple[str, float]:
    """
    使用食材，扣减用量。
    返回 (状态, 剩余量)
    状态：'updated' | 'depleted' | 'not_found' | 'not_tracked'
    """
    item = get_item_by_id(item_id)
    if not item:
        return "not_found", 0.0

    if item.amount <= 0:
        return "not_tracked", 0.0

    remaining = item.use_amount(amount_used)

    if remaining <= 0:
        remove_item(item_id)
        return "depleted", 0.0
    # early return：上面已经 return，不需要 else
    update_item(item)
    return "updated", remaining


def remove_item(item_id: str) -> bool:
    """删除食材（吃完/扔掉）"""
    data = _load_raw()
    new_data = [d for d in data if d["item_id"] != item_id]
    if len(new_data) == len(data):
        return False
    _save_raw(new_data)
    return True


def clear_expired() -> int:
    """清理所有过期食材，返回清理数量"""
    all_items = get_all_items()
    ok_items  = [i for i in all_items if i.is_ok]
    removed   = len(all_items) - len(ok_items)
    _save_raw([i.to_dict() for i in ok_items])
    return removed
