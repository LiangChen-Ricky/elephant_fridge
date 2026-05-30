"""
FreshElephant - AI recipe advisor.

Supported engines:
- OpenRouter, using the OpenAI-compatible chat completions API
- Anthropic Claude
- OpenAI ChatGPT
"""

import os
from pathlib import Path
from typing import List

from models import FridgeItem


ENV_FILE = Path(__file__).with_name(".env")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_OPENROUTER_MODEL = "google/gemma-3-27b-it:free"


def _load_env() -> None:
    """Small .env loader so both main.py and app.py can see API keys."""
    if not ENV_FILE.exists():
        return

    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_env()


def _get_engine() -> str:
    """
    Detect the available LLM engine.

    Set LLM_ENGINE=openrouter/openai/anthropic to force one provider.
    If not forced, OpenRouter is preferred because it can use free models.
    """
    forced = os.environ.get("LLM_ENGINE", "").strip().lower()
    if forced in ("openrouter", "anthropic", "openai"):
        return forced

    if os.environ.get("OPENROUTER_API_KEY"):
        try:
            import openai  # noqa: F401
            return "openrouter"
        except ImportError:
            pass

    if os.environ.get("ANTHROPIC_API_KEY"):
        try:
            import anthropic  # noqa: F401
            return "anthropic"
        except ImportError:
            pass

    if os.environ.get("OPENAI_API_KEY"):
        try:
            import openai  # noqa: F401
            return "openai"
        except ImportError:
            pass

    return "none"


def get_engine_display_name() -> str:
    engine = _get_engine()
    if engine == "openrouter":
        model = os.environ.get("OPENROUTER_MODEL", DEFAULT_OPENROUTER_MODEL)
        return f"OpenRouter ({model})"
    if engine == "anthropic":
        return "Claude (Anthropic)"
    if engine == "openai":
        return "ChatGPT (OpenAI)"
    return "Not configured"


def check_api_connection() -> bool:
    return _get_engine() != "none"


def _call_llm(prompt: str) -> str:
    """Unified LLM call entry point."""
    engine = _get_engine()

    if engine == "openrouter":
        import openai

        client = openai.OpenAI(
            api_key=os.environ["OPENROUTER_API_KEY"],
            base_url=OPENROUTER_BASE_URL,
        )
        response = client.chat.completions.create(
            model=os.environ.get("OPENROUTER_MODEL", DEFAULT_OPENROUTER_MODEL),
            max_tokens=1024,
            messages=[
                {
                    "role": "system",
                    "content": "You are a practical Chinese home-cooking assistant. Answer in Chinese.",
                },
                {"role": "user", "content": prompt},
            ],
        )
        return response.choices[0].message.content or ""

    if engine == "anthropic":
        import anthropic

        client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        message = client.messages.create(
            model=os.environ.get("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001"),
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text

    if engine == "openai":
        import openai

        client = openai.OpenAI(api_key=os.environ["OPENAI_API_KEY"])
        response = client.chat.completions.create(
            model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
            max_tokens=1024,
            messages=[
                {
                    "role": "system",
                    "content": "You are a practical Chinese home-cooking assistant. Answer in Chinese.",
                },
                {"role": "user", "content": prompt},
            ],
        )
        return response.choices[0].message.content or ""

    return "\n".join(
        [
            "未配置 LLM API。推荐使用 OpenRouter 免费模型：",
            "",
            "1. 安装依赖：pip install openai",
            "2. 在 .env 里加入：",
            "   LLM_ENGINE=openrouter",
            "   OPENROUTER_API_KEY=<your-openrouter-key>",
            f"   OPENROUTER_MODEL={DEFAULT_OPENROUTER_MODEL}",
            "",
            "OpenRouter: https://openrouter.ai",
        ]
    )


def get_recipe_suggestions(
    items: List[FridgeItem],
    focus_expiring: bool = True,
    n_suggestions: int = 2,
) -> str:
    """Suggest simple recipes from current fridge items."""
    if not items:
        return "冰箱是空的，无法推荐菜谱。"

    ingredient_lines = []
    for item in items:
        expiry_note = "（即将到期）" if item.is_expiring_soon else ""
        if item.is_expired:
            expiry_note = "（已过期，不建议食用）"
        ingredient_lines.append(f"- {item.name} {item.quantity_display} {expiry_note}")
    ingredient_text = "\n".join(ingredient_lines)

    focus_note = "请优先使用即将到期的食材，帮助减少食物浪费。" if focus_expiring else ""

    prompt = f"""你是一位专业的家庭厨师助手。我的冰箱里现在有以下食材：

{ingredient_text}

{focus_note}

请根据这些食材，推荐 {n_suggestions} 道简单实用的家常菜。
每道菜的格式如下：
【菜名】
所需食材：从上面列表中选择
简单做法：3-5步，每步一行
小贴士：一句话烹饪技巧

要求：中文、简洁、实用、适合家庭烹饪。"""

    return _call_llm(prompt)


def get_personalized_recipe(
    items: List[FridgeItem],
    preferences: dict,
) -> str:
    """Suggest personalized recipes from fridge items and user preferences."""
    if not items:
        return "冰箱是空的，无法推荐菜谱。"

    ingredient_lines = []
    for item in items:
        expiry_note = "（即将到期）" if item.is_expiring_soon else ""
        ingredient_lines.append(f"- {item.name} {item.quantity_display} {expiry_note}")
    ingredient_text = "\n".join(ingredient_lines)

    n = preferences.get("n_suggestions", 2)
    region = preferences.get("flavor_region", "随意")
    taste = preferences.get("flavor_taste", "随意")
    occasion = preferences.get("occasion", "家常")
    avoid = preferences.get("avoid", "无")
    custom = preferences.get("custom_note", "")

    custom_section = f"\n用户特殊要求：{custom}" if custom.strip() else ""

    prompt = f"""你是一位专业的私人厨师助手，请根据用户偏好和冰箱食材，定制专属菜谱。

【冰箱现有食材】
{ingredient_text}

【用户偏好】
- 口味地域：{region}
- 口味偏好：{taste}
- 用餐场景：{occasion}
- 忌口/过敏：{avoid}{custom_section}

请推荐 {n} 道最适合用户的菜谱，优先使用即将到期的食材。
每道菜请按以下格式输出：
【菜名】（适合{occasion}，{region}风味）
所需食材：
做法：3-5步
为什么推荐：一句话说明为什么符合用户偏好
贴心提示：食材处理或健康建议

要求：中文，语气亲切，像私人厨师一样。"""

    return _call_llm(prompt)
