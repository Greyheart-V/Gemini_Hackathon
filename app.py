"""
Resilience Planner 2026 — Climate Bridge
A simple Streamlit app for Kenyan farmers: get weather, crop advice, and a resilience plan.
Uses Google Gemini for the plan and Open-Meteo for weather. All 47 counties supported.
"""

import json
import os
from urllib.error import URLError
from urllib.request import urlopen

import google.generativeai as genai
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# -----------------------------------------------------------------------------
# Constants (change these if you need to adjust behaviour)
# -----------------------------------------------------------------------------

# Latitude/longitude per county for the weather API (one point per county).
NAIROBI_FALLBACK = (-1.29, 36.82)

COUNTY_COORDS = {
    "Baringo": (0.47, 35.97),
    "Bomet": (-0.78, 35.34),
    "Bungoma": (0.57, 34.56),
    "Busia": (0.46, 34.11),
    "Elgeyo-Marakwet": (0.82, 35.47),
    "Embu": (-0.54, 37.45),
    "Garissa": (-0.45, 39.64),
    "Homa Bay": (-0.53, 34.46),
    "Isiolo": (0.35, 37.58),
    "Kajiado": (-1.85, 36.78),
    "Kakamega": (0.28, 34.75),
    "Kericho": (-0.37, 35.28),
    "Kiambu": (-1.17, 36.82),
    "Kilifi": (-3.63, 39.85),
    "Kirinyaga": (-0.50, 37.38),
    "Kisii": (-0.68, 34.77),
    "Kisumu": (-0.10, 34.76),
    "Kitui": (-1.37, 38.01),
    "Kwale": (-4.18, 39.45),
    "Laikipia": (0.20, 36.72),
    "Lamu": (-2.27, 40.90),
    "Machakos": (-1.52, 37.26),
    "Makueni": (-1.80, 37.62),
    "Mandera": (3.94, 41.86),
    "Marsabit": (2.33, 37.99),
    "Meru": (-0.05, 37.65),
    "Migori": (-1.06, 34.47),
    "Mombasa": (-4.04, 39.67),
    "Murang'a": (-0.72, 37.15),
    "Nairobi City": (-1.29, 36.82),
    "Nakuru": (-0.30, 36.08),
    "Nandi": (-0.20, 35.12),
    "Narok": (-1.08, 35.87),
    "Nyamira": (-0.57, 34.95),
    "Nyandarua": (-0.24, 36.52),
    "Nyeri": (-0.42, 36.95),
    "Samburu": (1.10, 36.67),
    "Siaya": (-0.06, 34.29),
    "Taita-Taveta": (-3.40, 38.36),
    "Tana River": (-1.50, 39.90),
    "Tharaka-Nithi": (-0.30, 37.65),
    "Trans Nzoia": (1.00, 34.95),
    "Turkana": (3.12, 35.60),
    "Uasin Gishu": (0.52, 35.27),
    "Vihiga": (-0.06, 34.72),
    "Wajir": (1.75, 40.06),
    "West Pokot": (1.24, 35.11),
}

COUNTIES_LIST = [
    "Baringo", "Bomet", "Bungoma", "Busia", "Elgeyo-Marakwet", "Embu", "Garissa",
    "Homa Bay", "Isiolo", "Kajiado", "Kakamega", "Kericho", "Kiambu", "Kilifi",
    "Kirinyaga", "Kisii", "Kisumu", "Kitui", "Kwale", "Laikipia", "Lamu",
    "Machakos", "Makueni", "Mandera", "Marsabit", "Meru", "Migori", "Mombasa",
    "Murang'a", "Nairobi City", "Nakuru", "Nandi", "Narok", "Nyamira",
    "Nyandarua", "Nyeri", "Samburu", "Siaya", "Taita-Taveta", "Tana River",
    "Tharaka-Nithi", "Trans Nzoia", "Turkana", "Uasin Gishu", "Vihiga",
    "Wajir", "West Pokot",
]

# Markers we ask the AI to put around the short rundown so we can split it from the full report.
RUNDOWN_START = "--- RUNDOWN ---"
RUNDOWN_END = "--- END RUNDOWN ---"

# How much of the plan we send to the model in the chat (to stay under token limits).
MAX_PLAN_LENGTH_FOR_CHAT = 12_000


def weather_code_to_label(code):
    """Turn Open-Meteo weather code into a short readable label."""
    if code == 0:
        return "Clear"
    if code in (1, 2, 3):
        return "Mainly clear / partly cloudy"
    if code in (45, 48):
        return "Foggy"
    if code in (51, 53, 55, 56, 57):
        return "Drizzle"
    if code in (61, 63, 65, 66, 67):
        return "Rain"
    if code in (80, 81, 82):
        return "Rain showers"
    if code in (95, 96, 99):
        return "Thunderstorm"
    return "Variable"


def fetch_weather_for_county(county_name):
    """
    Get current weather and 7-day forecast for a county from Open-Meteo (free, no key).
    Returns a dict with 'current' and 'daily' or None if the request fails.
    """
    lat, lon = COUNTY_COORDS.get(county_name, NAIROBI_FALLBACK)
    url = (
        f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
        "&current=temperature_2m,relative_humidity_2m,precipitation,weather_code"
        "&daily=temperature_2m_max,temperature_2m_min,precipitation_sum"
        "&timezone=Africa/Nairobi&forecast_days=7"
    )
    try:
        with urlopen(url, timeout=8) as resp:
            return json.loads(resp.read().decode())
    except (URLError, json.JSONDecodeError):
        return None


def init_session_state():
    """Set default values in Streamlit session state so we don't get errors on first run."""
    if "last_plan" not in st.session_state:
        st.session_state.last_plan = ""
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []
    if "dark_theme" not in st.session_state:
        st.session_state.dark_theme = True


def setup_gemini():
    """
    Load Gemini API key from env, pick a model that supports generateContent, and return the model.
    Shows an error and returns None if something fails.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        st.error("GEMINI_API_KEY not set. Add it to your .env file or environment.")
        st.stop()
        return None

    genai.configure(api_key=api_key)

    try:
        models = [
            m for m in genai.list_models()
            if "generateContent" in getattr(m, "supported_generation_methods", [])
        ]
        if not models:
            st.error("No Gemini model with generateContent found for your API key. Check Google AI Studio.")
            st.stop()
            return None
        return genai.GenerativeModel(models[0].name)
    except Exception as e:
        st.error(f"Could not load Gemini models: {e}")
        st.stop()
        return None


def get_dark_theme_css():
    """CSS so the county dropdown and rest of the app are readable in dark mode."""
    return """
    <style>
    .stApp, [data-testid="stAppViewContainer"], main { background-color: #0e1117 !important; }
    .stApp header { background: #1e1e1e !important; }
    [data-testid="stSidebar"] { background: #1e1e1e !important; }
    [data-testid="stSidebar"] * { color: #fafafa !important; }
    h1, h2, h3, p, span, label, .stMarkdown { color: #fafafa !important; }
    .stMetric label { color: #fafafa !important; }
    div[data-testid="stExpander"] { background: #262730 !important; color: #fafafa !important; }
    .stChatMessage { background: #262730 !important; }
    .stInfo, .stSuccess, .stWarning, .stError { background: #262730 !important; border-color: #555 !important; }
    .stInfo *, .stSuccess *, .stWarning *, .stError * { color: #fafafa !important; }
    input, textarea, [data-baseweb="select"] { background: #262730 !important; color: #fafafa !important; }
    [data-testid="stSelectbox"] label, [data-testid="stSelectbox"] span,
    [data-testid="stSelectbox"] div, [data-testid="stSelectbox"] input { color: #fafafa !important; }
    div[data-baseweb="select"] > div { background: #262730 !important; color: #fafafa !important; }
    [data-baseweb="menu"], [role="listbox"], ul[role="listbox"],
    li[role="option"], [data-baseweb="popover"] li, div[data-baseweb="menu"] {
        background: #262730 !important; color: #fafafa !important;
    }
    [data-baseweb="menu"] *, [role="listbox"] *, [data-baseweb="popover"] *,
    li[role="option"], div[data-baseweb="menu"] li { color: #fafafa !important; }
    [data-testid="stRadio"] label, [data-testid="stRadio"] span { color: #fafafa !important; }
    ul[role="listbox"] li, [role="listbox"] li { background: #262730 !important; color: #fafafa !important; }
    [data-baseweb="select"] span, [data-baseweb="select"] [role="combobox"] { color: #fafafa !important; }
    </style>
    """


def get_light_theme_css():
    """Light theme: white background and dark text so the app is readable on Streamlit Cloud."""
    return """
    <style>
    .stApp, [data-testid="stAppViewContainer"], main { background-color: #ffffff !important; }
    [data-testid="stSidebar"] { background: #f0f2f6 !important; }
    /* Force dark text in main content (Streamlit Cloud can show faint grey otherwise) */
    .stApp h1, .stApp h2, .stApp h3, .stApp p, .stApp span, .stApp label,
    .stApp .stMarkdown, .stApp .stMetric label, main h1, main h2, main h3,
    main p, main span, main label, main .stMarkdown, main .stMetric label {
        color: #1f2937 !important;
    }
    main [data-testid="stMetricValue"] { color: #1f2937 !important; }
    </style>
    """


def get_mobile_css():
    """Responsive CSS so the app is usable on phones and small tablets."""
    return """
    <style>
    /* Single-column layout and readable tap targets on small screens */
    @media (max-width: 768px) {
        [data-testid="column"] { min-width: 100% !important; width: 100% !important; flex: 1 1 100% !important; }
        .stButton > button { min-height: 44px !important; padding: 0.5rem 1rem !important; font-size: 1rem !important; }
        [data-testid="stSidebar"] { width: 85% !important; min-width: 0 !important; }
        .stMarkdown { font-size: 0.95rem !important; }
        [data-testid="stChatInput"] textarea { min-height: 44px !important; }
    }
    @media (max-width: 480px) {
        h1 { font-size: 1.5rem !important; }
        h2, h3 { font-size: 1.2rem !important; }
        .stMetric { padding: 0.5rem 0 !important; }
    }
    /* Prevent horizontal scroll and keep content within viewport */
    .stApp { max-width: 100vw !important; overflow-x: hidden !important; }
    main { padding-left: 1rem !important; padding-right: 1rem !important; }
    </style>
    """


# -----------------------------------------------------------------------------
# App setup: API, session state, page config
# -----------------------------------------------------------------------------

init_session_state()
model = setup_gemini()

st.set_page_config(
    page_title="Resilience Planner 2026",
    page_icon="🌱",
    layout="wide",
)

st.title("🌱 Resilience Planner: 2026 Climate Bridge")
st.markdown(
    "Helping Kenyan smallholder farmers pivot from failing crops to climate-smart survival. "
    "Covers all 47 counties."
)

# -----------------------------------------------------------------------------
# Sidebar: farm details and theme toggle
# -----------------------------------------------------------------------------

with st.sidebar:
    st.header("📋 Farm Data")

    county = st.selectbox(
        "County (Kenya's 47 counties)",
        COUNTIES_LIST,
        index=COUNTIES_LIST.index("Kiambu"),
        help="County where your farm is",
    )
    location = st.text_input(
        "Nearest town / ward / market",
        value="Ruiru",
        help="Closest town or market to your farm",
    )
    soil_type = st.radio(
        "Soil type",
        ["Red Volcanic", "Black Cotton", "Sandy/Loamy"],
        help="Your soil type",
    )
    planted_crop = st.text_input(
        "Currently planted crop",
        value="Maize",
        help="What you are growing now",
    )
    quick_plan = st.toggle(
        "Quick action plan summary",
        value=False,
        help="On = short bullet plan. Off = full detailed strategy.",
    )

    st.markdown("---")
    st.session_state.dark_theme = st.toggle(
        "Dark theme",
        value=st.session_state.dark_theme,
        help="Switch between light and dark layout.",
    )

# Apply theme (so county list and text are visible in dark mode).
if st.session_state.dark_theme:
    st.markdown(get_dark_theme_css(), unsafe_allow_html=True)
else:
    st.markdown(get_light_theme_css(), unsafe_allow_html=True)
# Mobile: stack columns, bigger tap targets, no horizontal scroll.
st.markdown(get_mobile_css(), unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# Main area: weather and quick stats
# -----------------------------------------------------------------------------

st.markdown("---")
col_left, col_right = st.columns([0.7, 0.3])

with col_left:
    st.subheader("Climate Context for 2026")
    weather = fetch_weather_for_county(county)
    if weather:
        cur = weather.get("current", {})
        daily = weather.get("daily", {})
        temp = cur.get("temperature_2m")
        prec = cur.get("precipitation", 0)
        rh = cur.get("relative_humidity_2m")
        code = cur.get("weather_code", 0)
        wlabel = weather_code_to_label(code)
        temp_max = daily.get("temperature_2m_max", [None])[0]
        temp_min = daily.get("temperature_2m_min", [None])[0]
        prec_sums = daily.get("precipitation_sum", [0])
        prec_week = sum(p for p in prec_sums if p is not None) if prec_sums else 0
        st.info(
            f"""
            🌡️ **Now ({county})**: {temp}°C, {wlabel} · Rain: {prec or 0} mm · Humidity: {rh or '—'}%  
            📅 **7-day**: Highs ~{temp_max}°C, Lows ~{temp_min}°C · Total rain: ~{prec_week:.0f} mm  
            🌧️ **2026 outlook**: Heavy rains/floods then dry spells — plan for both.  
            ⚠️ **Challenge**: Unpredictable weather; many traditional crops at risk.
            """
        )
    else:
        st.info(
            f"""
            🌧️ **2026 outlook**: Heavy rains/floods expected, then dry spells.  
            📍 **Region**: {county}, Kenya (all 47 counties).  
            ⚠️ **Challenge**: Unpredictable weather; many traditional crops at risk.
            """
        )

with col_right:
    st.subheader("Quick Stats")
    st.metric("Selected County", county)
    st.metric("National Coverage", "47 Counties")
    st.metric("Planning Horizon", "2026")

st.markdown("---")


# Generate plan: prompt, call Gemini, show rundown + full report

if st.button("🚀 Generate Resilience Plan", type="primary", use_container_width=True):
    with st.spinner("Analyzing 2026 forecasts and climate data…"):
        if quick_plan:
            plan_style = """
PROVIDE A SHORT, ACTION-FOCUSED RESILIENCE PLAN with:
- 3–5 bullet points on the main climate risks for the farmer.
- 3–5 bullet points listing specific alternative crops and varieties.
- 3–5 bullet points outlining immediate next steps for the coming weeks.
Keep it clear and practical. Add one short paragraph on how farmers in other Kenyan counties with similar conditions can adapt the same ideas.
            """
        else:
            plan_style = """
PROVIDE A COMPREHENSIVE RESILIENCE STRATEGY with these sections:

1. **CLIMATE RISK ASSESSMENT**
   - Why is the current crop at risk in 2026 given the forecasted weather?
   - Specific vulnerabilities for the given soil type and local microclimate.

2. **RECOMMENDED PIVOT CROPS (Short-cycle alternatives)**
   - Suggest 3–4 specific crop varieties suitable for the farmer's location and county.
   - Include expected maturity period and yield potential.
   - Explain how each handles flood/drought cycles.

3. **LOCAL SUPPLIER RECOMMENDATIONS**
   - Name 2–3 likely types of agrovets or seed suppliers in the area.
   - What seeds/inputs they typically stock and timeframe to source.

4. **IMPLEMENTATION TIMELINE**
   - Weekly action steps for immediate preparation (Feb–March 2026).
   - Soil preparation for the given soil type and planting schedule aligned with weather.

5. **RISK MITIGATION PRACTICES**
   - Water harvest/conservation, soil amendments, crop insurance or safety nets in Kenya.

Close with a brief note on adapting this plan for other Kenyan counties with different microclimates.
            """

        rundown_instruction = f"""
FIRST output a very short RUNDOWN (under 80 words) in this exact format, then a blank line, then the full plan:

{RUNDOWN_START}
Advisable to grow [crop] now: Yes or No
Current season: [e.g. Short rains / Long rains / Dry]
Best season for [crop]: [e.g. Long rains, March–May]
Tips: • One short tip • Another • One more
{RUNDOWN_END}

Then continue with the full resilience plan as requested below.
"""

        prompt_text = f"""
Act as an expert Kenyan Agricultural Scientist for smallholder farming across all 47 counties of Kenya in 2026.

CONTEXT:
- Weather forecast: Heavy rains/floods followed by dry spells in 2026.
- Farmer county: {county}
- Farmer local area: {location}
- Soil type: {soil_type}
- Currently growing: {planted_crop}

{rundown_instruction}

The plan must be grounded in the selected county and relevant to farmers across Kenya's 47 counties.

{plan_style}
        """

        try:
            response = model.generate_content(prompt_text)
            full_text = response.text or ""

            # Split short rundown from full report using the markers we asked the AI to use.
            rundown_text = ""
            if RUNDOWN_START in full_text and RUNDOWN_END in full_text:
                start = full_text.index(RUNDOWN_START) + len(RUNDOWN_START)
                end = full_text.index(RUNDOWN_END)
                rundown_text = full_text[start:end].strip()
                full_report = full_text[end + len(RUNDOWN_END):].strip()
            else:
                full_report = full_text

            st.success("Resilience plan generated.")
            st.markdown("---")

            if rundown_text:
                st.subheader("📌 Quick rundown")
                st.caption("Advisability, season, and tips. Full details are in the report below.")
                st.info(rundown_text)
                st.markdown("---")

            st.subheader("📊 Your 2026 Resilience Strategy")
            st.markdown(full_report)

            st.session_state.last_plan = (rundown_text + "\n\n" + full_report) if rundown_text else full_report
            st.session_state.chat_messages = []

            st.markdown("---")
            c1, c2 = st.columns(2)
            with c1:
                if st.button("📥 Copy plan to clipboard"):
                    st.info("Copy the plan from the report above and paste it into your document.")
            with c2:
                if st.button("📧 Share strategy"):
                    st.info("Email/share feature can be added later (e.g. mailto or export).")
        except Exception as e:
            st.error(f"Error generating plan: {e}")
            st.write("Check your API key and internet connection.")

# -----------------------------------------------------------------------------
# Chat: follow-up questions about the last plan
# -----------------------------------------------------------------------------

st.markdown("---")
st.subheader("💬 Follow-up questions")
if st.session_state.last_plan:
    st.caption("Ask about your plan or ask for another report. Answers use your last generated plan.")
    for msg in st.session_state.chat_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    user_question = st.chat_input("Ask a follow-up about your plan…")
    if user_question:
        with st.chat_message("user"):
            st.markdown(user_question)
        with st.chat_message("assistant"):
            try:
                plan_snippet = st.session_state.last_plan[:MAX_PLAN_LENGTH_FOR_CHAT]
                chat_prompt = (
                    "Use this resilience plan as the only source. Answer the user's question "
                    "briefly and practically. If they ask for another report or summary, provide it.\n\n"
                    f"--- PLAN ---\n{plan_snippet}\n--- END PLAN ---\n\nUser question: {user_question}"
                )
                reply = model.generate_content(chat_prompt)
                reply_text = reply.text or "Could not generate a reply."
                st.markdown(reply_text)
                st.session_state.chat_messages.append({"role": "user", "content": user_question})
                st.session_state.chat_messages.append({"role": "assistant", "content": reply_text})
            except Exception as e:
                st.error(str(e))
                st.session_state.chat_messages.append({"role": "user", "content": user_question})
                st.session_state.chat_messages.append({"role": "assistant", "content": f"Error: {e}"})
else:
    st.info("Generate a resilience plan above first. Then you can ask follow-up questions here.")

# -----------------------------------------------------------------------------
# Footer
# -----------------------------------------------------------------------------

st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: gray; font-size: 12px;'>
    🌱 Resilience Planner 2026 | Powered by Google Gemini | Supporting farmers across Kenya's 47 counties
    </div>
    """,
    unsafe_allow_html=True,
)
