"""
FreshElephant 🐘
鲜到位，省到家，冰象守护你的冰箱

用法:
    python main.py

安装依赖（二选一）:
    pip install anthropic      # 用 Claude
    pip install openai         # 用 ChatGPT

设置API Key:
    Windows CMD:
        set ANTHROPIC_API_KEY=<your-anthropic-key>
        set OPENAI_API_KEY=<your-openai-key>
    Mac/Linux:
        export ANTHROPIC_API_KEY=<your-anthropic-key>
        export OPENAI_API_KEY=<your-openai-key>
"""

from datetime import date
from models import FridgeItem, StorageZone
import database as db
from expiry_rules import lookup, list_all_foods
from llm_advisor import (
    get_recipe_suggestions,
    get_personalized_recipe,
    check_api_connection,
    _get_engine,
    get_engine_display_name,
)


BANNER = """
╔══════════════════════════════════════════╗
║   🐘  FreshElephant  冰箱里的大象OS      ║
║   自从有了这只大象，每天的食材新鲜又像样儿  ║
╚══════════════════════════════════════════╝"""

MENU = """
┌──────────────────────────────────────┐
│  1. ➕ 添加食材到冰箱                 │
│  2. 📋 查看所有食材                   │
│  3. ⚠️  查看即将到期预警              │
│  4. 🍽️  使用食材（扣减用量）          │
│  5. 🍳 AI标准菜谱建议                 │
│  6. ✨ AI私人定制菜谱                 │
│  7. 🗑️  删除食材（整份丢弃）          │
│  8. 🧹 清理所有过期食材               │
│  9. 📚 查看食材知识库                 │
│  0. 👋 退出                           │
└──────────────────────────────────────┘"""

MEAT_TIPS = """
  💡 【分装小贴士】肉类建议放冰箱前先按每次用量分装：
     每份装入保鲜袋/保鲜盒，标注日期和重量，放入冷冻。
     这样每次只取一份解冻，其余保持冷冻新鲜，避免反复解冻。"""


def print_sep():
    print("─" * 46)


def print_items_table(items: list[FridgeItem], title: str = "食材列表"):
    print(f"\n📦 {title}（共 {len(items)} 项）")
    print_sep()
    if not items:
        print("  （空）")
        return
    print(f"{'ID':8} {'名称':12} {'区域':6} {'数量':12} {'状态'}")
    print_sep()
    for item in items:
        qty = item.quantity_display
        print(f"{item.item_id:8} {item.name:12} {item.zone.value:6} {qty:12} {item.status}")


# ─────────────────────────────────────────
# 功能流程
# ─────────────────────────────────────────

def add_item_flow():
    print("\n➕ 添加食材到冰箱")
    print_sep()

    name = input("食材名称（如：鸡胸肉、西兰花）: ").strip()
    if not name:
        print("名称不能为空")
        return

    suggested_zone, suggested_days = lookup(name)
    print(f"  💡 知识库建议：存放={suggested_zone.value}，保质={suggested_days}天")

    zone_input = input(f"  存放区域 [冷藏/冷冻/保鲜]（回车用'{suggested_zone.value}'）: ").strip()
    zone_map = {"冷藏": StorageZone.FRIDGE, "冷冻": StorageZone.FREEZER, "保鲜": StorageZone.FRESH}
    zone = zone_map.get(zone_input, suggested_zone)

    days_input = input(f"  保质天数（回车用'{suggested_days}天'）: ").strip()
    expiry_days = int(days_input) if days_input.isdigit() else suggested_days

    # 数值化数量（可选）
    qty_input = input("  数量（如：500g、1颗、2包，直接回车跳过精确追踪）: ").strip()
    amount, unit, quantity_str = 0.0, "", qty_input or "1份"

    if qty_input:
        # 尝试解析数字+单位，如 "500g" / "2 个"
        import re
        m = re.match(r"^([\d.]+)\s*([^\d\s]*)$", qty_input)
        if m:
            amount = float(m.group(1))
            unit = m.group(2) or "份"
            quantity_str = qty_input

    portions_input = input("  是否已分装份数？（如：3，未分装直接回车）: ").strip()
    portions = int(portions_input) if portions_input.isdigit() else 1

    notes = input("  备注（可选，回车跳过）: ").strip()

    item = FridgeItem(
        name=name, zone=zone, quantity=quantity_str,
        date_added=date.today(), expiry_days=expiry_days,
        amount=amount, unit=unit, portions=portions, notes=notes,
    )
    db.add_item(item)

    # 肉类分装提示
    if item.is_meat and item.zone != StorageZone.FREEZER:
        print(MEAT_TIPS)


def view_all_flow():
    items = db.get_all_items()
    print_items_table(items, "冰箱全部食材")


def view_alerts_flow():
    print("\n⚠️  即将到期预警")
    print_sep()

    expiring, expired = db.get_alert_items()  # 一次读文件，同时拿两个列表

    if not expiring and not expired:
        print("🎉 冰箱里没有即将过期或已过期的食材，很棒！")
        return

    if expired:
        print_items_table(expired, "❌ 已过期（建议扔掉）")
    if expiring:
        print_items_table(expiring, "⚠️  2天内到期（赶紧用）")
        print(f"\n👉 共 {len(expiring)} 种食材即将到期！")
        suggest = input("  要让AI给菜谱建议吗？[y/n]: ").strip().lower()
        if suggest == "y":
            standard_recipe_flow(items=expiring)


def use_item_flow():
    """使用食材，扣减用量"""
    print("\n🍽️  使用食材")
    print_sep()

    items = db.get_all_items()
    if not items:
        print("冰箱是空的！")
        return

    print_items_table(items, "当前冰箱食材")
    print()

    item_id = input("输入要使用的食材ID（回车取消）: ").strip()
    if not item_id:
        return

    item = db.get_item_by_id(item_id)
    if not item:
        print(f"❌ 未找到ID为 {item_id} 的食材")
        return

    print(f"\n  食材：{item.name}，当前：{item.quantity_display}")

    if item.amount <= 0:
        # 未追踪数值，只能整份删除
        print("  （此食材未设置精确数量追踪）")
        confirm = input("  整份标记为用完并删除？[y/n]: ").strip().lower()
        if confirm == "y":
            db.remove_item(item_id)
            print(f"✅ {item.name} 已从冰箱移除")
    else:
        used_input = input(f"  使用了多少 {item.unit}？（当前剩余 {item.amount}{item.unit}）: ").strip()
        try:
            used = float(used_input)
        except ValueError:
            print("❌ 请输入数字")
            return

        status, remaining = db.use_item(item_id, used)

        if status == "depleted":
            print(f"✅ {item.name} 已用完，自动从冰箱移除！")
        elif status == "updated":
            print(f"✅ 已使用 {used}{item.unit}，剩余：{remaining}{item.unit}")
            if remaining <= item.amount * 0.3:
                print(f"  💡 提示：{item.name} 剩余不多了，下次购物别忘记补货！")
        elif status == "not_found":
            print("❌ 食材不存在")

    # 肉类使用后的分装提示
    if item and item.is_meat:
        print(MEAT_TIPS)


def standard_recipe_flow(items=None):
    print("\n🍳 AI标准菜谱建议")
    print_sep()

    if not check_api_connection():
        _show_api_help()
        return

    if items is None:
        items = db.get_ok_items()
    if not items:
        print("冰箱是空的，无法推荐菜谱 🫙")
        return

    print(f"  使用引擎：{get_engine_display_name()}")
    print(f"  正在分析 {len(items)} 种食材，生成菜谱建议...")
    print_sep()
    result = get_recipe_suggestions(items, focus_expiring=True)
    print(result)


def personalized_recipe_flow():
    """私人定制菜谱"""
    print("\n✨ AI私人定制菜谱")
    print_sep()

    if not check_api_connection():
        _show_api_help()
        return

    items = db.get_ok_items()
    if not items:
        print("冰箱是空的，无法推荐菜谱 🫙")
        return

    print("  请回答几个问题，让AI为您量身定制菜谱 😊")
    print()

    # ── 口味地域 ──
    print("  【口味地域】")
    print("  1. 北方（饺子、包子、炖菜风格）")
    print("  2. 南方（清蒸、白灼、煲汤风格）")
    print("  3. 川湘（麻辣香辣）")
    print("  4. 粤式（清淡鲜美）")
    print("  5. 随意（不限制）")
    region_map = {"1": "北方", "2": "南方", "3": "川湘麻辣", "4": "粤式清淡", "5": "随意"}
    r = input("  请选择 [1-5]（默认5随意）: ").strip()
    flavor_region = region_map.get(r, "随意")

    # ── 口味偏好 ──
    print("\n  【口味偏好】")
    print("  1. 偏咸  2. 偏甜  3. 清淡  4. 重口味  5. 随意")
    taste_map = {"1": "偏咸", "2": "偏甜", "3": "清淡", "4": "重口味", "5": "随意"}
    t = input("  请选择 [1-5]（默认5随意）: ").strip()
    flavor_taste = taste_map.get(t, "随意")

    # ── 用餐场景 ──
    print("\n  【用餐场景】")
    print("  1. 日常家常  2. 朋友聚餐  3. 节日大餐  4. 减脂健康  5. 快手菜（30分钟内）")
    occ_map = {"1": "日常家常", "2": "朋友聚餐", "3": "节日大餐", "4": "减脂健康", "5": "快手菜"}
    o = input("  请选择 [1-5]（默认1家常）: ").strip()
    occasion = occ_map.get(o, "日常家常")

    # ── 忌口 ──
    avoid = input("\n  【忌口/过敏】有什么不能吃的？（如：不吃辣、海鲜过敏，没有直接回车）: ").strip() or "无"

    # ── 自由输入 ──
    print("\n  【特殊要求】（可选，自由输入）")
    print("  例如：今天有客人来，想做一道拿手好菜")
    print("        最近在减肥，希望低脂低卡")
    print("        家里有老人小孩，口味要温和一些")
    custom = input("  您的特殊要求（回车跳过）: ").strip()

    n_input = input("\n  需要推荐几道菜？[1-3]（默认2）: ").strip()
    n = int(n_input) if n_input.isdigit() and 1 <= int(n_input) <= 3 else 2

    preferences = {
        "flavor_region": flavor_region,
        "flavor_taste": flavor_taste,
        "occasion": occasion,
        "avoid": avoid,
        "custom_note": custom,
        "n_suggestions": n,
    }

    print(f"\n  使用引擎：{get_engine_display_name()}")
    print(f"  正在为您定制专属菜谱，请稍候...")
    print_sep()
    result = get_personalized_recipe(items, preferences)
    print(result)


def delete_item_flow():
    view_all_flow()
    print()
    item_id = input("输入要删除的食材ID（回车取消）: ").strip()
    if not item_id:
        return
    item = db.get_item_by_id(item_id)
    if item:
        confirm = input(f"  确认删除 {item.name}？[y/n]: ").strip().lower()
        if confirm != "y":
            return
    if db.remove_item(item_id):
        print(f"✅ 已删除")
    else:
        print(f"❌ 未找到该食材")


def clear_expired_flow():
    expired = db.get_expired_items()
    if not expired:
        print("✅ 没有过期食材，冰箱很干净！")
        return
    print_items_table(expired, "以下食材已过期")
    confirm = input(f"\n确认删除以上 {len(expired)} 项过期食材？[y/n]: ").strip().lower()
    if confirm == "y":
        n = db.clear_expired()
        print(f"🧹 已清理 {n} 项过期食材")


def show_knowledge_base():
    print("\n📚 食材保质期知识库")
    print_sep()
    foods = list_all_foods()
    print(f"共收录 {len(foods)} 种常见食材：")
    for i in range(0, len(foods), 5):
        row = foods[i:i+5]
        print("  " + "  ".join(f"{f:8}" for f in row))


def _show_api_help():
    print("\n⚠️  未配置LLM API，请选择一种方式：")
    print()
    print("  【推荐】OpenRouter（一个 Key 调用很多模型，可用免费模型）:")
    print("    pip install openai")
    print("    在 .env 里写：")
    print("      LLM_ENGINE=openrouter")
    print("      OPENROUTER_API_KEY=<your-openrouter-key>")
    print("      OPENROUTER_MODEL=google/gemma-3-27b-it:free")
    print("    获取Key: https://openrouter.ai")
    print()
    print("  【方案A】Anthropic Claude（推荐，吴恩达课程同款）:")
    print("    pip install anthropic")
    print("    set ANTHROPIC_API_KEY=<your-anthropic-key>")
    print("    获取Key: https://console.anthropic.com")
    print()
    print("  【方案B】OpenAI ChatGPT:")
    print("    pip install openai")
    print("    set OPENAI_API_KEY=<your-openai-key>")
    print("    获取Key: https://platform.openai.com")


# ─────────────────────────────────────────
# 主循环
# ─────────────────────────────────────────

def main():
    print(BANNER)

    # 启动预警
    expiring, expired = db.get_alert_items()  # 一次读文件
    if expiring or expired:
        print(f"\n🔔 注意：{len(expiring)} 种食材即将到期，{len(expired)} 种已过期！（选项3查看）")

    # 显示当前LLM状态
    engine = _get_engine()
    if engine in ("openrouter", "anthropic", "openai"):
        print(f"🤖 AI引擎：{get_engine_display_name()} ✅")
    else:
        print("🤖 AI引擎：未配置（菜谱功能不可用）")

    while True:
        print(MENU)
        choice = input("请选择功能 [0-9]: ").strip()

        if choice == "1":
            add_item_flow()
        elif choice == "2":
            view_all_flow()
        elif choice == "3":
            view_alerts_flow()
        elif choice == "4":
            use_item_flow()
        elif choice == "5":
            standard_recipe_flow()
        elif choice == "6":
            personalized_recipe_flow()
        elif choice == "7":
            delete_item_flow()
        elif choice == "8":
            clear_expired_flow()
        elif choice == "9":
            show_knowledge_base()
        elif choice == "0":
            print("\n👋 再见！大象永不忘记 🐘\n")
            break
        else:
            print("❌ 无效选项，请输入 0-9")

        input("\n回车继续...")


if __name__ == "__main__":
    main()
    main()
