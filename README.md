#this is an mvp and a display of consept not the final product
# Resilience Planner 2026 — Climate Bridge

A web app for Kenyan smallholder farmers. You pick your county, soil type, and current crop; the app shows local weather and gives you a written resilience plan: whether it’s advisable to keep growing that crop, what to grow instead, and when to plant. It works on desktop and on mobile (phones and tablets).

---

## The problem it solves

Smallholders in Kenya often rely on one or two crops. When the weather turns—heavy rains, then long dry spells—those crops fail and families have little to fall back on. Extension officers can’t reach everyone, and generic advice doesn’t fit every county or soil type.

This app gives farmers:

- **Local weather** — Current conditions and a 7-day outlook for their county (no sign-up, no cost).
- **A short answer first** — “Is it advisable to grow my crop now?” plus current season, best season for that crop, and a few tips.
- **A full plan** — Climate risks, alternative crops, where to get seeds, a rough timeline, and simple risk mitigation (water harvesting, soil, insurance).
- **Follow-up** — After the plan is generated, they can ask questions in plain language and get answers based on their plan.

All 47 Kenyan counties are supported. The idea is to bridge the gap between broad climate forecasts and what a single farmer in one place should do next.

---

## What’s in the project

- **`app.py`** — The whole app: weather fetch, Gemini API calls, and the Streamlit UI (sidebar form, climate section, generate button, rundown, full report, chat, footer). Written so a beginner can follow the flow.
- **`requirements.txt`** — Python dependencies (Streamlit, Google Generative AI, python-dotenv).
- **`.env.example`** — Example env file; you copy it to `.env` and add your Gemini API key. `.env` is gitignored.
- **`.streamlit/config.toml`** — Streamlit settings (theme, toolbar). Optional.
- **`.gitignore`** — So you don’t commit `.env`, `venv/`, cache, or IDE files.

Tech: Streamlit for the UI, Google Gemini for the written plan, Open-Meteo for weather (no key). The app chooses a Gemini model that supports text generation so you don’t have to hard-code a model name.

---

## Run it on your machine

1. **Clone the repo** (or download and unzip):

   ```bash
   git clonehttps://github.com/Greyheart-V/Gemini_Hackathon/edit/main/README.md
   cd resilience-planner-2026
   ```

2. **Create a virtual environment** (recommended):

   ```bash
   python -m venv venv
   # Windows:
   venv\Scripts\activate
   # macOS/Linux:
   source venv/bin/activate
   ```

3. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

4. **Set your Gemini API key:**

   - Get a key from [Google AI Studio](https://ai.google.dev/).
   - Copy `.env.example` to `.env` and put your key there:

   ```bash
   # Windows (PowerShell):
   copy .env.example .env
   # macOS/Linux:
   cp .env.example .env
   ```

   Then edit `.env`:

   ```
   GEMINI_API_KEY=paste_your_key_here
   ```

5. **Start the app:**

   ```bash
   streamlit run app.py
   ```

   Open the URL it prints (usually `http://localhost:8501`). Use the sidebar to pick county, town, soil type, and crop; click “Generate Resilience Plan”; then you can use the chat to ask follow-ups.

---

## Deploy to GitHub and run it online (Streamlit Community Cloud)

The app is a Python web app. It doesn’t run on static hosts like Netlify or GitHub Pages; it needs a server. The simplest free option is Streamlit Community Cloud, which runs the app from your GitHub repo.

### Step 1: Put the project on GitHub

1. Create a **new repository** on GitHub (e.g. `resilience-planner-2026`). Do not add a README, .gitignore, or license yet if you already have them locally.

2. **Initialize Git in your project folder** (if you haven’t already):

   ```bash
   cd path/to/resilience-planner-2026
   git init
   ```

3. **Add and commit everything** (`.env` is ignored, so it won’t be committed):

   ```bash
   git add .
   git commit -m "Initial commit: Resilience Planner 2026 app"
   ```

4. **Connect to GitHub and push:**

   ```bash
   git remote add origin https://github.com/YOUR_USERNAME/resilience-planner-2026.git
   git branch -M main
   git push -u origin main
   ```

   Replace `YOUR_USERNAME` and `resilience-planner-2026` with your GitHub username and repo name.

### Step 2: Deploy on Streamlit Community Cloud

1. Go to [share.streamlit.io](https://share.streamlit.io) and sign in with GitHub.

2. Click **“New app”**.

3. Choose:
   - **Repository**: `YOUR_USERNAME/resilience-planner-2026`
   - **Branch**: `main`
   - **Main file path**: `app.py`

4. Open **“Advanced settings”** and add a secret:
   - Name: `GEMINI_API_KEY`
   - Value: your Gemini API key (same as in your local `.env`).

5. Click **“Deploy”**. Streamlit will install dependencies from `requirements.txt` and run `streamlit run app.py`. When it’s ready, you get a public URL (e.g. `https://your-app-name.streamlit.app`).

6. **Mobile:** Open that URL on a phone or tablet. The layout stacks on small screens and buttons are sized for touch. The sidebar becomes a menu you open from the top-left.

---

## Mobile behaviour

The UI is built to work on phones and tablets:

- On narrow screens (e.g. under 768px), the main content columns stack vertically so you don’t have to scroll sideways.
- Buttons and the chat input are large enough to tap comfortably.
- The sidebar collapses into a hamburger menu; opening it shows county, town, soil type, crop, and theme toggle.
- Text and spacing scale so the plan and weather are readable without zooming.

If something looks broken on a specific device, try refreshing or using the latest Chrome or Safari.

---

## If something goes wrong

| Issue | What to do |
|-------|------------|
| “GEMINI_API_KEY not found” | Create a `.env` file (copy from `.env.example`) and set `GEMINI_API_KEY=...`. Restart the app. On Streamlit Cloud, add the secret in Advanced settings. |
| “No module named 'streamlit'” | Run `pip install -r requirements.txt` in the same environment you use for `streamlit run app.py`. |
| Plan never loads / 404 or model error | The app picks a Gemini model automatically. Check that your API key is valid and has access to at least one generative model in [Google AI Studio](https://ai.google.dev/). |
| County list hard to read | Turn on “Dark theme” in the sidebar. |
| Weather doesn’t show | Open-Meteo is used for weather; if their API is down or your network blocks it, the app shows a short fallback message instead of live data. |

---

## Licence and use

This project is open source (e.g. for hackathon or learning use). If you reuse it, keep the spirit: it’s for farmers who need simple, local, actionable advice.

---

**Resilience Planner 2026 — for farmers across Kenya’s 47 counties.**


