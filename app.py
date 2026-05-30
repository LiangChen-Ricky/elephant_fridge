"""
FreshElephant - Flask Web Server
API Key: create .env with ANTHROPIC_API_KEY=... or OPENAI_API_KEY=...
Run: python app.py -> http://localhost:5000
"""

import sys, os, re, json as _json
from datetime import date
from pathlib import Path
from flask import Flask, jsonify, request, render_template

sys.path.insert(0, os.path.dirname(__file__))

ENV_FILE = Path(__file__).parent / ".env"

def load_env():
    if not ENV_FILE.exists(): return
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

load_env()

from models import FridgeItem, StorageZone
import database as db
from expiry_rules import lookup, list_all_foods, EXPIRY_DATABASE, save_to_user_kb, get_user_kb_all
import llm_advisor

app = Flask(__name__)

def item_to_json(item):
    return {
        "item_id": item.item_id, "name": item.name, "zone": item.zone.value,
        "quantity": item.quantity, "quantity_display": item.quantity_display,
        "amount": item.amount, "unit": item.unit, "portions": item.portions,
        "date_added": item.date_added.isoformat(), "expiry_date": item.expiry_date.isoformat(),
        "expiry_days": item.expiry_days, "days_remaining": item.days_remaining,
        "status": item.status, "is_expiring_soon": item.is_expiring_soon,
        "is_expired": item.is_expired, "is_meat": item.is_meat, "notes": item.notes,
    }

@app.route("/")
def index():
    return render_template("index.html")

# Items

@app.route("/api/items", methods=["GET"])
def api_get_items():
    return jsonify([item_to_json(i) for i in db.get_all_items()])

@app.route("/api/items", methods=["POST"])
def api_add_item():
    data = request.json or {}
    name = data.get("name", "").strip()
    if not name: return jsonify({"error": "食材名称不能为空"}), 400
    zone_map = {"冷藏": StorageZone.FRIDGE, "冷冻": StorageZone.FREEZER, "保鲜": StorageZone.FRESH}
    zone = zone_map.get(data.get("zone", ""), StorageZone.FRIDGE)
    expiry_days = int(data.get("expiry_days", 5))
    if expiry_days <= 0: return jsonify({"error": "保质天数必须大于 0"}), 400
    quantity_str = data.get("quantity", "1份")
    portions = int(data.get("portions", 1))
    notes = data.get("notes", "")
    amount, unit = 0.0, ""
    m = re.match(r"^([\d.]+)\s*([^\d\s]*)$", quantity_str)
    if m: amount = float(m.group(1)); unit = m.group(2) or "份"
    item = FridgeItem(name=name, zone=zone, quantity=quantity_str, date_added=date.today(),
                      expiry_days=expiry_days, amount=amount, unit=unit, portions=portions, notes=notes)
    db.add_item(item)
    return jsonify({"success": True, "item": item_to_json(item)})

@app.route("/api/items/<item_id>", methods=["DELETE"])
def api_delete_item(item_id):
    return jsonify({"success": db.remove_item(item_id)})

@app.route("/api/items/<item_id>/use", methods=["POST"])
def api_use_item(item_id):
    data = request.json or {}
    item = db.get_item_by_id(item_id)
    if not item: return jsonify({"error": "食材不存在"}), 404
    if item.amount <= 0:
        db.remove_item(item_id)
        return jsonify({"status": "depleted", "remaining": 0, "is_meat": item.is_meat})
    amount_used = float(data.get("amount_used", 0))
    status, remaining = db.use_item(item_id, amount_used)
    return jsonify({"status": status, "remaining": remaining, "unit": item.unit, "is_meat": item.is_meat})

@app.route("/api/alerts", methods=["GET"])
def api_alerts():
    expiring, expired = db.get_alert_items()
    return jsonify({"expiring": [item_to_json(i) for i in expiring], "expired": [item_to_json(i) for i in expired]})

@app.route("/api/clear-expired", methods=["POST"])
def api_clear_expired():
    return jsonify({"success": True, "removed": db.clear_expired()})

@app.route("/api/stats", methods=["GET"])
def api_stats():
    all_items = db.get_all_items()
    return jsonify({
        "total": len(all_items),
        "ok": sum(1 for i in all_items if i.is_ok and not i.is_expiring_soon),
        "expiring_soon": sum(1 for i in all_items if i.is_expiring_soon),
        "expired": sum(1 for i in all_items if i.is_expired),
    })

# Knowledge

@app.route("/api/lookup", methods=["GET"])
def api_lookup():
    name = request.args.get("name", "")
    zone, days = lookup(name)
    return jsonify({"zone": zone.value, "expiry_days": days})

@app.route("/api/foods", methods=["GET"])
def api_foods():
    return jsonify(list_all_foods())

@app.route("/api/user-kb", methods=["GET"])
def api_user_kb():
    return jsonify(get_user_kb_all())

# AI Shelf Life

@app.route("/api/shelf-life", methods=["POST"])
def api_shelf_life():
    if not llm_advisor.check_api_connection(): return jsonify({"error": "no_api"}), 503
    data = request.json or {}
    name = data.get("name", "").strip()
    zone = data.get("zone", "冷藏").strip()
    if not name: return jsonify({"error": "请先填写食材名称"}), 400
    prompt = '你是食品安全专家。请给出「' + name + '」放在「' + zone + '」里从今天起安全存放的天数。只回复JSON不加其他文字:{"days":数字,"reason":"30字内的理由"}'
    try:
        result = llm_advisor._call_llm(prompt)
        match = re.search(r'\{.*?\}', result, re.DOTALL)
        if match:
            parsed = _json.loads(match.group())
            days = int(parsed["days"])
            reason = parsed.get("reason", "")
            zone_obj = {"冷藏": StorageZone.FRIDGE, "冷冻": StorageZone.FREEZER, "保鲜": StorageZone.FRESH}.get(zone, StorageZone.FRIDGE)
            save_to_user_kb(name, zone_obj, days)
            return jsonify({"success": True, "days": days, "reason": reason, "saved_to_kb": True})
        return jsonify({"error": "AI返回格式异常，请重试"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Recipes

@app.route("/api/recipe", methods=["POST"])
def api_recipe():
    if not llm_advisor.check_api_connection(): return jsonify({"error": "no_api"}), 503
    data = request.json or {}
    n = max(1, min(10, int(data.get("n_suggestions", 2))))
    item_ids = data.get("item_ids")
    if item_ids:
        all_items = db.get_all_items()
        items = [i for i in all_items if i.item_id in item_ids]
    elif data.get("expiring_only"):
        items = db.get_expiring_soon()
    else:
        items = db.get_ok_items()
    if not items: return jsonify({"error": "empty_fridge"}), 400
    result = llm_advisor.get_recipe_suggestions(items, focus_expiring=True, n_suggestions=n)
    return jsonify({"success": True, "recipe": result})

@app.route("/api/recipe/personalized", methods=["POST"])
def api_recipe_personalized():
    if not llm_advisor.check_api_connection(): return jsonify({"error": "no_api"}), 503
    data = request.json or {}
    n = max(1, min(10, int(data.get("n_suggestions", 2))))
    data["n_suggestions"] = n
    items = db.get_ok_items()
    if not items: return jsonify({"error": "empty_fridge"}), 400
    result = llm_advisor.get_personalized_recipe(items, data)
    return jsonify({"success": True, "recipe": result})

@app.route("/api/recipe/weekly", methods=["POST"])
def api_recipe_weekly():
    if not llm_advisor.check_api_connection(): return jsonify({"error": "no_api"}), 503
    items = db.get_ok_items()
    if not items: return jsonify({"error": "empty_fridge"}), 400
    lines = "\n".join("- " + i.name + " " + i.quantity_display + "(" + i.zone.value + ", " + str(i.days_remaining) + "天)" for i in items)
    prompt = "你是家庭营养师。根据冰箱食材为家庭制定本周7天膳食建议：\n\n" + lines + "\n\n要求：优先消耗快过期食材；营养均衡；每天早中晚三餐各一句话。格式：【周一】\n早餐：...\n午餐：...\n晚餐：...\n\n【周二】...以此类推。"
    result = llm_advisor._call_llm(prompt)
    return jsonify({"success": True, "plan": result})

# Run

if __name__ == "__main__":
    print("FreshElephant starting...")
    print("Open: http://localhost:5000")
    app.run(debug=True, port=5000)
