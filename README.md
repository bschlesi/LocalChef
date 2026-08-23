# LocalChef 🍳

**LocalChef** is a local SLM-based cooking assistant and pantry tracking application.

Powered by:
- **Python & Flask** (Backend & Local REST API)
- **HTML5, CSS3, & Vanilla JS** (Frontend interface)
- **Phi4-mini via Ollama** (Local SLM for recipe building and shopping lists)
- **Local CSV & JSON storage** (Pantry inventory & user customization preferences)

---

## Features

1. **Pantry Tracker (`/pantry`)**
   - View current pantry items with dates, quantities, and units.
   - Add new items or edit existing items with auto-date stamps.
   - Multi-select and remove items.
   - Import items directly from a CSV file located in `./data/`.
   - Clear pantry action.

2. **Recipes & Cooking (`/cooking` or `/`)**
   - Interactive recipe prompt builder tailored to your active pantry inventory.
   - Fast shortcuts: *"Give me a recipe"* and *"I'm going shopping"*.
   - Free-form prompt bar to request specific dishes, variations, or pantry-limited meals.
   - Clean, chat-style response stream with ingredient lists and step-by-step instructions.

3. **Customization (`/customization`)**
   - Free-text custom instructions & prompt injections (e.g. dietary restrictions, appliance limitations).
   - Toggle switch for meal prep optimization (portioning & storage guidance).
   - Toggle switch for estimated macronutrients and portion sizing.
   - Clear pantry button.

---

## Getting Started

### 1. Prerequisites
- **Python 3.10+**
- **Ollama** installed with `phi4-mini`:
  ```bash
  ollama run phi4-mini
  ```

### 2. Installation
Install dependencies:
```bash
pip install -r requirements.txt
```

### 3. Run the App
Launch using Python or the included batch script:
```bash
python app.py
```
Or double-click `run.bat`.

Open your browser and navigate to:
```
http://localhost:5000
```

---

## Pantry CSV Import Format

When importing a CSV file into `./data/pantry_import.csv`, the file should have the following 4 columns:
```csv
Date Added/Updated,Item,Quantity,Unit(s)
2026-01-01,Tyson boneless skinless chicken breast,1,lb
2026-01-01,Yellow bell pepper,2,count
2026-01-04,Onion,1,count
2026-01-07,Taco seasoning,12,oz
2026-01-07,All purpose flour,1,lb
```

---

## Running Tests

Run the test suite using `pytest`:
```bash
python -m pytest tests/
```
