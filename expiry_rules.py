"""
FreshElephant 🐘 - 食材保质期知识库
"""

import json
from pathlib import Path
from models import StorageZone

# ─── 用户知识库（AI学到的食材存这里，优先级最高）─────────────────────────────
USER_KB_FILE = Path(__file__).parent / "user_kb.json"

def _load_user_kb() -> dict:
    if not USER_KB_FILE.exists():
        return {}
    try:
        return json.loads(USER_KB_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}

def save_to_user_kb(name: str, zone: StorageZone, days: int):
    """把AI给出的建议存入用户知识库"""
    kb = _load_user_kb()
    kb[name] = {"zone": zone.value, "days": days}
    USER_KB_FILE.write_text(json.dumps(kb, ensure_ascii=False, indent=2), encoding="utf-8")

def get_user_kb_all() -> dict:
    return _load_user_kb()

# ─── 内置知识库 ───────────────────────────────────────────────────────────────
EXPIRY_DATABASE: dict[str, tuple[StorageZone, int]] = {
    # 蔬菜
    "菠菜":     (StorageZone.FRESH,   3),
    "生菜":     (StorageZone.FRESH,   3),
    "韭菜":     (StorageZone.FRESH,   3),
    "豆腐":     (StorageZone.FRIDGE,  3),
    "西兰花":   (StorageZone.FRESH,   5),
    "花椰菜":   (StorageZone.FRESH,   5),
    "青椒":     (StorageZone.FRESH,   7),
    "红椒":     (StorageZone.FRESH,   7),
    "黄瓜":     (StorageZone.FRESH,   7),
    "番茄":     (StorageZone.FRIDGE,  7),
    "西红柿":   (StorageZone.FRIDGE,  7),
    "茄子":     (StorageZone.FRIDGE,  7),
    "胡萝卜":   (StorageZone.FRESH,  14),
    "白萝卜":   (StorageZone.FRESH,  14),
    "土豆":     (StorageZone.FRIDGE, 14),
    "洋葱":     (StorageZone.FRIDGE, 21),
    "大蒜":     (StorageZone.FRIDGE, 21),
    "姜":       (StorageZone.FRIDGE, 21),
    "玉米":     (StorageZone.FRESH,   3),
    "豆芽":     (StorageZone.FRESH,   2),
    # 水果
    "草莓":     (StorageZone.FRIDGE,  3),
    "蓝莓":     (StorageZone.FRIDGE,  5),
    "葡萄":     (StorageZone.FRIDGE,  7),
    "樱桃":     (StorageZone.FRIDGE,  7),
    "苹果":     (StorageZone.FRIDGE, 21),
    "梨":       (StorageZone.FRIDGE, 14),
    "桃子":     (StorageZone.FRIDGE,  5),
    "芒果":     (StorageZone.FRIDGE,  5),
    "西瓜":     (StorageZone.FRIDGE,  5),
    "哈密瓜":   (StorageZone.FRIDGE,  5),
    "柠檬":     (StorageZone.FRIDGE, 21),
    # 肉类
    "猪肉":     (StorageZone.FRIDGE,  3),
    "牛肉":     (StorageZone.FRIDGE,  3),
    "羊肉":     (StorageZone.FRIDGE,  3),
    "鸡肉":     (StorageZone.FRIDGE,  2),
    "鸡胸肉":   (StorageZone.FRIDGE,  2),
    "鸡腿":     (StorageZone.FRIDGE,  2),
    "鸭肉":     (StorageZone.FRIDGE,  2),
    "猪排":     (StorageZone.FRIDGE,  3),
    "五花肉":   (StorageZone.FRIDGE,  3),
    "猪肉末":   (StorageZone.FRIDGE,  2),
    "牛肉末":   (StorageZone.FRIDGE,  2),
    "冷冻猪肉": (StorageZone.FREEZER,180),
    "冷冻牛肉": (StorageZone.FREEZER,270),
    "冷冻鸡肉": (StorageZone.FREEZER,270),
    "冷冻羊肉": (StorageZone.FREEZER,180),
    # 海鲜
    "虾":       (StorageZone.FRIDGE,  2),
    "鱼":       (StorageZone.FRIDGE,  2),
    "三文鱼":   (StorageZone.FRIDGE,  2),
    "螃蟹":     (StorageZone.FRIDGE,  1),
    "蛤蜊":     (StorageZone.FRIDGE,  2),
    "冷冻虾":   (StorageZone.FREEZER, 90),
    "冷冻鱼":   (StorageZone.FREEZER, 90),
    # 乳制品/蛋
    "鸡蛋":     (StorageZone.FRIDGE, 21),
    "牛奶":     (StorageZone.FRIDGE,  7),
    "酸奶":     (StorageZone.FRIDGE, 14),
    "奶酪":     (StorageZone.FRIDGE, 14),
    "黄油":     (StorageZone.FRIDGE, 30),
    "淡奶油":   (StorageZone.FRIDGE,  7),
    # 熟食/剩菜
    "剩菜":     (StorageZone.FRIDGE,  2),
    "剩饭":     (StorageZone.FRIDGE,  2),
    "卤肉":     (StorageZone.FRIDGE,  3),
    "熟鸡":     (StorageZone.FRIDGE,  3),
    "炒菜":     (StorageZone.FRIDGE,  2),
    # 冷冻食品
    "饺子":     (StorageZone.FREEZER, 60),
    "汤圆":     (StorageZone.FREEZER, 90),
    "包子":     (StorageZone.FREEZER, 30),
    "冰淇淋":   (StorageZone.FREEZER,180),
    "冷冻蔬菜": (StorageZone.FREEZER,180),
    "冷冻玉米": (StorageZone.FREEZER,180),
}

DEFAULT_EXPIRY: dict[StorageZone, int] = {
    StorageZone.FRIDGE: 5,
    StorageZone.FRESH: 4,
    StorageZone.FREEZER: 90,
}

# ─── 查询函数 ─────────────────────────────────────────────────────────────────

def lookup(name: str, zone: StorageZone | None = None) -> tuple[StorageZone, int]:
    """
    匹配优先级：
      ① 用户知识库精确匹配（AI学到的，最高优先级）
      ② 内置库精确匹配
      ③ 内置库模糊匹配
      ④ 默认值兜底
    """
    zone_map = {z.value: z for z in StorageZone}

    # ① 用户知识库
    user_kb = _load_user_kb()
    if name in user_kb:
        entry = user_kb[name]
        return zone_map[entry["zone"]], entry["days"]

    # ② 内置库精确匹配
    if name in EXPIRY_DATABASE:
        return EXPIRY_DATABASE[name]

    # ③ 内置库模糊匹配
    for key, (z, days) in EXPIRY_DATABASE.items():
        if key in name:
            return z, days

    # ④ 兜底
    fallback_zone = zone or StorageZone.FRIDGE
    return fallback_zone, DEFAULT_EXPIRY[fallback_zone]


def list_all_foods() -> list[str]:
    """列出所有内置食材名"""
    return sorted(EXPIRY_DATABASE.keys())
