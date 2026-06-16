# 🐘 FreshElephant — 冰箱里的大象 OS

> **鲜到位，省到家，冰象守护你的冰箱**

A smart fridge management app with AI-powered recipe suggestions, expiry alerts, and a self-learning food knowledge base. Built with Python + Flask + LLM API.

The idea came from a real-life problem: food gets pushed to the back of the fridge, forgotten, and eventually wasted. This app turns the fridge into a small inventory system with reminders and AI cooking suggestions.

## Features

**6 tabs in the web UI:**

- 📦 **冰箱库存** — View all items across fridge (冷藏), freezer (冷冻), and fresh shelf (保鲜); track quantity and days remaining
- ➕ **添加食材** — Add items with smart auto-expiry lookup; click **AI建议** when unsure how long a food keeps
- ⚠️ **到期预警** — Alerts for items expiring within 1 or 2 days; select items directly from alerts to cook with
- 🍳 **标准菜谱** — AI suggests recipes from your fridge; prioritises expiring items; supports 1–10 recipe count
- 👨‍🍳 **私人定制** — Personalised recipes filtered by region, taste, occasion, and dietary restrictions
- 📅 **本周膳食** — AI generates a full 7-day breakfast/lunch/dinner meal plan

## Project Structure

```text
.
|-- app.py              # Flask web server
|-- main.py             # Command-line app
|-- models.py           # Fridge item and storage models
|-- database.py         # JSON-based local storage logic
|-- expiry_rules.py     # Food expiry knowledge base
|-- llm_advisor.py      # LLM provider integration and recipe prompts
|-- templates/
|   `-- index.html      # Web UI
|-- .env.example        # Example environment variables
`-- .gitignore          # Keeps API keys and local data out of Git
```

## Setup

**1. Install dependencies**

```powershell
pip install flask anthropic openai
```

**2. Configure your API key** — create a `.env` file in the project root:

```env
# Option A: Anthropic Claude (recommended)
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxx

# Option B: OpenRouter (free models available)
OPENROUTER_API_KEY=sk-or-xxxxxxxxxxxxxxxx
LLM_ENGINE=openrouter
OPENROUTER_MODEL=google/gemma-3-27b-it:free

# Option C: OpenAI
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
```

The app auto-detects which engine to use. Priority order: **OpenRouter → Anthropic → OpenAI**.

## Run the CLI App

```powershell
python main.py
```

The command-line version lets you add food, check expiry warnings, use ingredients, and ask AI for recipe ideas.

## Run the Web App

```powershell
python app.py
```

Then open:

```text
http://localhost:5000
```

## AI Self-Learning Knowledge Base

Every time you ask AI for a shelf-life suggestion, the result is saved to `user_kb.json` automatically. Next time you add the same food, it uses the cached answer — **no extra tokens spent**.

Lookup priority:
1. `user_kb.json` — AI-learned items (highest priority)
2. Built-in database — 70+ common Chinese foods pre-loaded
3. Fuzzy match — e.g. "猪肉末" matches "猪肉"
4. Default fallback — 冷藏: 5 days, 保鲜: 4 days, 冷冻: 90 days

## API Key Safety

The real `.env` file is listed in `.gitignore` and is never committed to Git. Keep real keys local and avoid uploading `fridge_data.json` if it contains personal grocery data.

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Python 3.10+, Flask |
| Frontend | Vanilla HTML / CSS / JS (single file) |
| Storage | JSON file — no database needed |
| AI | Anthropic Claude / OpenRouter / OpenAI |
| Default models | `claude-haiku-4-5-20251001` · `google/gemma-3-27b-it:free` · `gpt-4o-mini` |

## Learning Context

Built during Week 4 of learning Python as a real-world capstone project, studying Andrew Ng's [AI Python for Beginners](https://www.deeplearning.ai/short-courses/ai-python-for-beginners/) on DeepLearning.AI.

Python concepts practised: `@dataclass`, `@property`, `Enum`, JSON I/O, Flask REST API, LLM SDK integration, `.env` secrets management, early return pattern, DRY principle.

## Next Steps

- Add a shopping list workflow
- Add image or receipt recognition for grocery entry
- Add scheduled push reminders for expiring food
- Expand the food expiry knowledge base
- Add unit tests for expiry logic and database operations

---

*小亮出品，必属精品* 🐘
