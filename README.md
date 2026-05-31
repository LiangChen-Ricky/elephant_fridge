# Elephant Fridge

FreshElephant is a Python project for managing groceries in a home fridge. It helps track food expiry dates, warns about ingredients that should be used soon, and uses an LLM to suggest simple recipes from what is already available.

The idea came from a real-life problem: food gets pushed to the back of the fridge, forgotten, and eventually wasted. This app turns the fridge into a small inventory system with reminders and cooking suggestions.

## Features

- Add fridge items with name, storage zone, quantity, and notes
- Automatically estimate expiry days from a food knowledge base
- View all stored ingredients
- Highlight food that is expiring soon or already expired
- Use or remove ingredients from the inventory
- Generate recipe suggestions with an LLM
- Create personalized recipes based on taste, region, occasion, and dietary restrictions
- Run as either a command-line program or a Flask web app
- Support OpenRouter, Anthropic, and OpenAI API providers

## Project Structure

```text
.
├── app.py              # Flask web server
├── main.py             # Command-line app
├── models.py           # Fridge item and storage models
├── database.py         # JSON-based local storage logic
├── expiry_rules.py     # Food expiry knowledge base
├── llm_advisor.py      # LLM provider integration and recipe prompts
├── templates/
│   └── index.html      # Web UI
├── .env.example        # Example environment variables
└── .gitignore          # Keeps API keys and local data out of Git
```

## Setup

Install the Python dependency used for OpenRouter/OpenAI-compatible APIs:

```powershell
pip install openai
```

If you want to use Anthropic directly:

```powershell
pip install anthropic
```

Create a local `.env` file from `.env.example`:

```powershell
copy .env.example .env
```

Then add your own API key:

```env
LLM_ENGINE=openrouter
OPENROUTER_API_KEY=<your-openrouter-key>
OPENROUTER_MODEL=google/gemma-3-27b-it:free
```

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

## API Key Safety

The real `.env` file is ignored by Git and should never be committed.

This project intentionally commits only `.env.example`, which contains placeholders. Keep real keys local, rotate any key that has been exposed in screenshots, and avoid uploading `fridge_data.json` if it contains personal grocery data.

## Why This Project Matters

This is a beginner-friendly Python + AI project, but it solves a real problem:

- less food waste
- better weekly grocery planning
- safer awareness of expiry dates
- practical use of LLM APIs inside everyday software

## Next Steps

- Add a shopping list workflow
- Improve the web interface
- Add image or receipt recognition for grocery entry
- Add scheduled reminders for expiring food
- Expand the food expiry knowledge base
- Add tests for expiry logic and database operations
