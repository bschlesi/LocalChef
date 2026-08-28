# LocalChef - Long-Term & Low-Priority Objectives

This document outlines strategic, architectural, and lower-priority roadmap goals for LocalChef.

---

## 1. Local SLM Exploration & Benchmarking
* **Explore Non-Thinking vs. Thinking Models**:
  - Test lightweight instruction models (e.g. `qwen2.5:3b-instruct`, `llama3.2:3b`, `gemma2:2b`) as alternatives to `phi4-mini`.
  - **The Thinking Model Problem**: When testing models with chain-of-thought (e.g., Qwen 3.5 / R1 distillations), reasoning tokens inflate the total token count past 2,000+ tokens, slowing down CPU inference significantly.
  - Evaluate techniques to disable reasoning tokens, strip thought tags before streaming to UI, or enforce strict output schemas.
* **Performance Profiling on Consumer Hardware**:
  - Target: Keep generation time under 3-5 minutes (minimum ~3-5 tok/s on typical 13th Gen Intel Core i7 / 16GB RAM laptops with Intel Iris Xe graphics).

---

## 2. Recipe History, Favorites & Cook Log
* **Local Recipe Database**:
  - Store generated recipes that the user marks as cooked or favorites into a lightweight local SQLite database (`recipes.db`) or JSON store.
* **User Feedback & Custom Notes**:
  - Allow users to rate recipes (1-5 stars), add cooking notes (e.g., "Used 2 tsp salt instead of 1", "Needed 5 extra minutes in oven"), and re-generate modified versions.
* **Personalized Feedback Loop**:
  - Feed favorite recipes and flavor profiles into future recipe and shopping list prompts.

---

## 3. Historic Pantry & Predictive Grocery Intelligence
* **Ingredient Lifecycle & Velocity Tracking**:
  - Record history of purchased and consumed ingredients (e.g., user buys chicken breasts every 2 weeks, pasta box lasts 3 meals).
* **Smart Restock Prediction**:
  - Upgrade the **"I'm going shopping"** SLM prompt by supplying consumption velocity data to predict what staples are likely running low before they run out completely.

---

## 4. Standalone Desktop Packaging & App Distribution
* **Native Desktop Bundle (.exe / installer)**:
  - Package the Flask backend, frontend assets, and Python runtime into a single standalone installer/executable (using PyInstaller, Tauri, or Electron).
  - Eliminates the need for end users to install Python, git, or command-line dependencies.
* **Embedded Ollama & Model Lifecycle Management**:
  - Automatic detection of Ollama service status with in-app buttons to start Ollama or pull models (`phi4-mini`, etc.) directly from the GUI.

---

## 5. Kitchen "Cook Mode" & Voice/Timer Assistance
* **Step-by-Step Focus Mode**:
  - A distraction-free, large-type UI view designed for kitchen counter devices (tablets/phones).
  - High-contrast buttons and gestures for hands-free or messy-hand usability.
* **Integrated Timers**:
  - Automatically parse time mentions from instruction steps (e.g., "bake for 25 minutes") and provide interactive one-tap timers with browser audio alerts.
* **Hands-Free Voice Commands**:
  - Integrate local speech-to-text (e.g., Whisper.cpp / Web Speech API) for voice commands like *"Next step"*, *"Read current step"*, or *"Set timer for 10 minutes"*.

---

## 6. Offline Nutritional Analysis & Macro Profiling
* **Accurate Macro Engine**:
  - Complement model estimations with an offline USDA FoodData Central lookup or local nutrition dictionary to give verified macronutrient (protein, carbs, fat, calories) calculations per serving.
* **Dietary & Calorie Goal Tracking**:
  - Allow users to specify daily macro/calorie targets and let the recipe generator size ingredient proportions to hit those targets accurately.

---

## 7. Barcode & Receipt Scanning (Fast Pantry Input)
* **Barcode Scanner**:
  - Integrate barcode lookup (via OpenFoodFacts offline dump or camera-based barcode scanning) to quickly add packaged pantry items with quantities and units.
* **Receipt OCR**:
  - Allow uploading grocery receipts or images to automatically extract and populate new items into `pantry.csv`.

---

## 8. Local Network Access & Multi-Device Sync
* **LAN Hosting**:
  - Provide a simple toggle/flag to bind Flask to `0.0.0.0` with a generated QR code in the terminal or browser, allowing immediate access from mobile devices on the same Wi-Fi network without external cloud exposure.
