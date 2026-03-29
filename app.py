from __future__ import annotations

import random
import time
from datetime import datetime

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from advisor_llm import generate_advice
from interpreter import interpret

try:
    from camera import CVModule
except Exception:
    CVModule = None


st.set_page_config(
    page_title="NeuroSense Console",
    page_icon="NS",
    layout="wide",
    initial_sidebar_state="expanded",
)


def init_state() -> None:
    defaults = {
        "history": [],
        "journals": [],
        "last_summary": "",
        "current_entry": "",
        "clear_input": False,
        "camera_module": None,
        "camera_running": False,
        "camera_error": "",
        "last_snapshot_key": "",
        "last_chat_reply": "",
        "last_insight_reply": "",
        "live_auto_refresh": True,
        "live_refresh_seconds": 4,
        "live_terminal_context": "",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


init_state()


st.markdown(
    """
    <style>
    :root {
        --bg-top: #020814;
        --bg-bottom: #1a2448;
        --glass: rgba(10, 20, 36, 0.55);
        --glass-strong: rgba(17, 31, 52, 0.78);
        --border: rgba(255, 255, 255, 0.16);
        --text: #eef6ff;
        --muted: #afc2db;
        --accent: #80d6ff;
        --accent-soft: rgba(128, 214, 255, 0.16);
        --rose: #ff9fbc;
        --mint: #7af5c7;
        --amber: #ffd27d;
        --ink: #06111d;
        --mist: rgba(214, 237, 255, 0.07);
    }

    [data-testid="stAppViewContainer"] {
        background:
            radial-gradient(circle at 18% 10%, rgba(164, 214, 255, 0.18), transparent 0 30%),
            radial-gradient(circle at 82% 12%, rgba(191, 176, 255, 0.16), transparent 0 28%),
            radial-gradient(circle at 50% 120%, rgba(111, 145, 255, 0.16), transparent 0 40%),
            linear-gradient(155deg, var(--bg-top), #091126 32%, #121938 62%, var(--bg-bottom));
        color: var(--text);
        position: relative;
        overflow: hidden;
    }

    [data-testid="stAppViewContainer"]::before,
    [data-testid="stAppViewContainer"]::after,
    [data-testid="stAppViewContainer"] > .main::before {
        content: "";
        position: fixed;
        inset: 0;
        pointer-events: none;
        z-index: 0;
        transition: opacity 260ms ease, transform 380ms ease, filter 380ms ease;
    }

    [data-testid="stAppViewContainer"]::before {
        opacity: 1;
        background:
            radial-gradient(circle 520px at var(--cursor-x, 50vw) var(--cursor-y, 28vh), rgba(174, 232, 255, 0.18), transparent 0 58%),
            radial-gradient(circle 680px at calc(var(--cursor-x, 50vw) - 18%) calc(var(--cursor-y, 28vh) + 18%), rgba(181, 163, 255, 0.14), transparent 0 64%),
            radial-gradient(circle 420px at 24% 24%, rgba(255,255,255,0.08), transparent 0 26%),
            radial-gradient(circle 520px at 78% 16%, rgba(198, 223, 255, 0.07), transparent 0 24%);
        filter: blur(8px);
        animation: nebulaDrift 34s ease-in-out infinite alternate;
    }

    [data-testid="stAppViewContainer"]::after {
        opacity: 0.92;
        background:
            radial-gradient(circle 360px at calc(var(--cursor-x, 50vw) + 8%) calc(var(--cursor-y, 28vh) - 10%), rgba(228, 214, 255, 0.15), transparent 0 62%),
            radial-gradient(circle 920px at 50% 118%, rgba(120, 163, 255, 0.12), transparent 0 58%),
            linear-gradient(125deg, transparent 0%, rgba(255,255,255,0.03) 24%, transparent 48%);
        mix-blend-mode: screen;
        animation: celestialVeil 42s linear infinite;
    }

    [data-testid="stAppViewContainer"] > .main::before {
        opacity: 0.88;
        background:
            radial-gradient(circle 2.4px at 12% 16%, rgba(255,255,255,0.42), transparent 98%),
            radial-gradient(circle 1.8px at 20% 34%, rgba(227, 236, 255, 0.26), transparent 98%),
            radial-gradient(circle 2.2px at 31% 26%, rgba(255,255,255,0.3), transparent 98%),
            radial-gradient(circle 1.7px at 44% 18%, rgba(214, 237, 255, 0.22), transparent 98%),
            radial-gradient(circle 2.4px at 58% 30%, rgba(255,255,255,0.35), transparent 98%),
            radial-gradient(circle 1.8px at 73% 20%, rgba(226, 233, 255, 0.24), transparent 98%),
            radial-gradient(circle 2.2px at 84% 34%, rgba(255,255,255,0.34), transparent 98%),
            radial-gradient(circle 1.7px at 66% 68%, rgba(214, 237, 255, 0.22), transparent 98%),
            radial-gradient(circle 2.2px at 36% 78%, rgba(255,255,255,0.24), transparent 98%),
            radial-gradient(circle 1.7px at 82% 82%, rgba(227, 236, 255, 0.2), transparent 98%),
            radial-gradient(circle 2px at 54% 10%, rgba(255,255,255,0.28), transparent 98%),
            radial-gradient(circle 1.8px at 8% 72%, rgba(227, 236, 255, 0.22), transparent 98%);
        animation: starlightPulse 11s ease-in-out infinite alternate;
    }

    [data-testid="stAppViewContainer"][data-desktop-live="false"]::before,
    [data-testid="stAppViewContainer"][data-desktop-live="false"]::after,
    [data-testid="stAppViewContainer"][data-desktop-live="false"] > .main::before {
        opacity: 0.4;
    }

    @keyframes nebulaDrift {
        0% { transform: translate3d(0, 0, 0) scale(1); }
        50% { transform: translate3d(-1.4%, 1.2%, 0) scale(1.04); }
        100% { transform: translate3d(1.2%, -1.6%, 0) scale(1.06); }
    }

    @keyframes celestialVeil {
        0% { transform: translateX(-4%) translateY(0%) scale(1); }
        50% { transform: translateX(2.5%) translateY(1.8%) scale(1.04); }
        100% { transform: translateX(-1.5%) translateY(-1.2%) scale(1.02); }
    }

    @keyframes starlightPulse {
        0% { opacity: 0.28; transform: translateY(0) scale(1); }
        50% { opacity: 0.58; transform: translateY(-0.3%) scale(1.02); }
        100% { opacity: 0.34; transform: translateY(-0.5%) scale(1); }
    }

    @media (max-width: 900px), (pointer: coarse) {
        [data-testid="stAppViewContainer"]::before,
        [data-testid="stAppViewContainer"]::after,
        [data-testid="stAppViewContainer"] > .main::before {
            animation: none;
            opacity: 0.5;
        }
    }

    [data-testid="stAppViewContainer"] > .main,
    [data-testid="stSidebar"] {
        position: relative;
        z-index: 1;
    }

    header[data-testid="stHeader"] {
        display: none;
    }

    [data-testid="stToolbar"] {
        display: none;
    }

    [data-testid="stDecoration"] {
        display: none;
    }

    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, rgba(7, 17, 31, 0.94), rgba(10, 23, 39, 0.92));
        border-right: 1px solid rgba(255,255,255,0.08);
    }

    .block-container {
        padding-top: 0.4rem;
        padding-bottom: 2rem;
    }

    h1, h2, h3, h4, p, label, div, span {
        color: var(--text);
    }

    .hero {
        position: relative;
        overflow: hidden;
        background: linear-gradient(135deg, rgba(255,255,255,0.13), rgba(225, 235, 255, 0.045));
        border: 1px solid var(--border);
        backdrop-filter: blur(18px);
        -webkit-backdrop-filter: blur(18px);
        border-radius: 28px;
        padding: 1.8rem 1.8rem 1.4rem 1.8rem;
        margin-top: 0.45rem;
        margin-bottom: 1.3rem;
        box-shadow: 0 24px 60px rgba(0, 0, 0, 0.18);
    }

    .hero::after {
        content: "";
        position: absolute;
        inset: auto -40px -40px auto;
        width: 180px;
        height: 180px;
        background: radial-gradient(circle, rgba(204, 220, 255, 0.16), transparent 70%);
    }

    .hero::before {
        content: "";
        position: absolute;
        inset: -25% auto auto -8%;
        width: 240px;
        height: 240px;
        background: radial-gradient(circle, rgba(191, 176, 255, 0.11), transparent 72%);
        filter: blur(14px);
    }

    .eyebrow {
        text-transform: uppercase;
        letter-spacing: 0.18em;
        font-size: 0.76rem;
        color: var(--accent);
        margin-bottom: 0.45rem;
    }

    .hero-title {
        font-size: 2.4rem;
        font-weight: 700;
        line-height: 1.1;
        margin-bottom: 0.45rem;
    }

    .hero-copy {
        color: var(--muted);
        max-width: 760px;
        font-size: 1rem;
    }

    .glass-card {
        background: var(--glass);
        border: 1px solid var(--border);
        border-radius: 22px;
        padding: 1.1rem 1.15rem;
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        box-shadow: 0 10px 35px rgba(0, 0, 0, 0.16);
        margin-bottom: 1rem;
    }

    .metric-card {
        background: linear-gradient(180deg, rgba(255,255,255,0.15), rgba(255,255,255,0.06));
        border: 1px solid var(--border);
        border-radius: 22px;
        padding: 1rem 1rem 0.9rem 1rem;
        min-height: 196px;
        height: 100%;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
    }

    .metric-slot {
        height: 100%;
    }

    .snapshot-slot {
        height: 100%;
    }

    div[data-testid="stHorizontalBlock"]:has(.metric-slot) {
        align-items: stretch;
    }

    div[data-testid="stHorizontalBlock"]:has(.metric-slot) > div[data-testid="column"] {
        display: flex;
    }

    div[data-testid="stHorizontalBlock"]:has(.metric-slot) > div[data-testid="column"] > div {
        height: 100%;
    }

    div[data-testid="stHorizontalBlock"]:has(.snapshot-slot) {
        align-items: stretch;
    }

    div[data-testid="stHorizontalBlock"]:has(.snapshot-slot) > div[data-testid="column"] {
        display: flex;
    }

    div[data-testid="stHorizontalBlock"]:has(.snapshot-slot) > div[data-testid="column"] > div {
        height: 100%;
    }

    .metric-label {
        color: var(--muted);
        font-size: 0.82rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
    }

    .metric-value {
        font-size: 1.85rem;
        font-weight: 700;
        margin-top: 0.35rem;
    }

    .metric-subtle {
        color: var(--muted);
        font-size: 0.92rem;
        margin-top: 0.3rem;
    }

    .pill {
        display: inline-block;
        padding: 0.35rem 0.7rem;
        margin: 0.2rem 0.25rem 0 0;
        border-radius: 999px;
        background: var(--accent-soft);
        border: 1px solid rgba(128, 214, 255, 0.18);
        color: var(--text);
        font-size: 0.85rem;
    }

    .section-title {
        font-size: 1.05rem;
        font-weight: 700;
        margin-bottom: 0.7rem;
    }

    .eeg-band {
        background: linear-gradient(180deg, rgba(255,255,255,0.1), rgba(255,255,255,0.04));
        border: 1px solid rgba(255,255,255,0.1);
        border-radius: 18px;
        padding: 0.9rem;
        margin-bottom: 0.9rem;
        backdrop-filter: blur(14px);
        -webkit-backdrop-filter: blur(14px);
    }

    .eeg-head {
        display: flex;
        justify-content: space-between;
        align-items: baseline;
        gap: 0.6rem;
        margin-bottom: 0.55rem;
    }

    .eeg-name {
        font-size: 0.92rem;
        font-weight: 700;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: var(--text);
    }

    .eeg-value {
        font-size: 0.9rem;
        color: var(--muted);
    }

    .eeg-track {
        position: relative;
        width: 100%;
        height: 12px;
        background: rgba(255,255,255,0.08);
        border-radius: 999px;
        overflow: hidden;
        margin-bottom: 0.65rem;
        box-shadow: inset 0 1px 2px rgba(0,0,0,0.22);
    }

    .eeg-fill {
        height: 100%;
        border-radius: 999px;
        box-shadow: 0 0 18px rgba(128,214,255,0.22);
    }

    .eeg-note {
        color: var(--muted);
        font-size: 0.82rem;
        line-height: 1.35;
    }

    .snapshot-card {
        background: linear-gradient(180deg, rgba(255,255,255,0.1), rgba(255,255,255,0.04));
        border: 1px solid rgba(255,255,255,0.1);
        border-radius: 18px;
        padding: 0.9rem;
        backdrop-filter: blur(14px);
        -webkit-backdrop-filter: blur(14px);
        min-height: 132px;
        margin-bottom: 0.85rem;
        height: 100%;
    }

    .snapshot-row {
        align-items: stretch;
    }

    .snapshot-value {
        font-size: 1.55rem;
        font-weight: 700;
        color: var(--text);
        margin-bottom: 0.55rem;
    }

    .snapshot-note {
        color: var(--muted);
        font-size: 0.82rem;
        line-height: 1.35;
    }

    .context-text {
        color: var(--muted);
        line-height: 1.55;
    }

    .status-good {
        color: var(--mint);
    }

    .status-warn {
        color: var(--amber);
    }

    .status-alert {
        color: var(--rose);
    }

    div[data-testid="stMetric"] {
        background: transparent;
    }

    .stTextInput input, .stTextArea textarea, .stSelectbox div[data-baseweb="select"] > div,
    .stNumberInput input {
        background: rgba(255,255,255,0.9) !important;
        border: 1px solid rgba(255,255,255,0.18) !important;
        color: var(--ink) !important;
        border-radius: 14px !important;
    }

    .stTextInput input::placeholder,
    .stTextArea textarea::placeholder,
    .stNumberInput input::placeholder {
        color: rgba(6, 17, 29, 0.62) !important;
    }

    .stSelectbox div[data-baseweb="select"] span,
    .stSelectbox div[data-baseweb="select"] input,
    .stSelectbox div[data-baseweb="select"] div,
    .stSelectbox div[data-baseweb="select"] svg,
    .stTextInput label,
    .stTextArea label,
    .stNumberInput label,
    .stSelectbox label {
        color: var(--ink) !important;
    }

    div[data-baseweb="popover"] *,
    ul[role="listbox"] *,
    div[role="listbox"] * {
        color: var(--ink) !important;
    }

    .stSlider [data-baseweb="slider"] {
        padding-top: 0.6rem;
    }

    .stButton button {
        border-radius: 999px;
        border: 1px solid rgba(122,245,199,0.18);
        background: linear-gradient(135deg, rgba(18, 72, 58, 0.88), rgba(12, 49, 42, 0.82));
        color: var(--text);
        box-shadow: 0 10px 24px rgba(4, 18, 15, 0.24);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        font-weight: 600;
    }

    .stButton button:hover {
        border-color: rgba(122,245,199,0.3);
        background: linear-gradient(135deg, rgba(24, 91, 73, 0.92), rgba(15, 61, 50, 0.88));
        color: var(--text);
    }

    .stButton button:focus {
        color: var(--text);
        box-shadow: 0 0 0 0.18rem rgba(122,245,199,0.18);
    }

    div[data-testid="stToggle"] {
        display: flex;
        justify-content: flex-end;
    }

    div[data-testid="stToggle"] > label {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        min-width: 88px;
        padding: 0.42rem 0.72rem;
        border-radius: 999px;
        border: 1px solid rgba(255,255,255,0.12);
        background: linear-gradient(180deg, rgba(255,255,255,0.1), rgba(255,255,255,0.04));
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        transition: background 180ms ease, border-color 180ms ease, box-shadow 180ms ease, transform 180ms ease;
        cursor: pointer;
    }

    div[data-testid="stToggle"] > label[data-checked="true"] {
        background: linear-gradient(135deg, rgba(165, 34, 66, 0.92), rgba(119, 20, 52, 0.9));
        border-color: rgba(255, 159, 188, 0.42);
        box-shadow: 0 0 0 0.12rem rgba(255, 159, 188, 0.12);
    }

    div[data-testid="stToggle"] > label:hover {
        transform: translateY(-1px);
    }

    div[data-testid="stToggle"] > label p {
        color: var(--text) !important;
        font-size: 0.82rem !important;
        font-weight: 700 !important;
        letter-spacing: 0.04em;
        margin: 0 !important;
        text-align: center;
    }

    div[data-testid="stToggle"] > label > div:first-child {
        display: none !important;
    }

    div[data-testid="stToggle"] > label > div:last-child {
        margin: 0 !important;
        display: flex !important;
        align-items: center;
        justify-content: center;
        width: 100%;
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 0.5rem;
    }

    .stTabs [data-baseweb="tab"] {
        background: rgba(255,255,255,0.06);
        border-radius: 999px;
        padding: 0.4rem 1rem;
    }

    .stTabs [aria-selected="true"] {
        background: rgba(128,214,255,0.18);
    }

    div[data-testid="stAlertContainer"] *,
    div[data-testid="stNotification"] *,
    div[data-baseweb="notification"] * {
        color: var(--ink) !important;
    }

    div[data-testid="stAlertContainer"] > div,
    div[data-baseweb="notification"] {
        background: rgba(255,255,255,0.92) !important;
        border: 1px solid rgba(6, 17, 29, 0.08) !important;
    }

    div[data-testid="stTooltipContent"] *,
    div[role="tooltip"] *,
    [data-baseweb="tooltip"] * {
        color: var(--ink) !important;
    }

    div[data-testid="stCodeBlock"] *,
    .stCodeBlock *,
    pre,
    code {
        color: var(--ink) !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

components.html(
    """
    <script>
    (() => {
        const root = parent.document.documentElement;
        const app = parent.document.querySelector('[data-testid="stAppViewContainer"]');
        if (!root || !app) return;

        const desktopQuery = parent.matchMedia("(min-width: 901px) and (pointer: fine)");
        let rafId = null;
        let targetX = parent.innerWidth * 0.55;
        let targetY = parent.innerHeight * 0.22;

        const paint = () => {
            root.style.setProperty("--cursor-x", `${targetX}px`);
            root.style.setProperty("--cursor-y", `${targetY}px`);
            rafId = null;
        };

        const syncMode = () => {
            app.setAttribute("data-desktop-live", desktopQuery.matches ? "true" : "false");
        };

        const onMove = (event) => {
            if (!desktopQuery.matches) return;
            targetX = event.clientX;
            targetY = event.clientY;
            if (rafId === null) {
                rafId = parent.requestAnimationFrame(paint);
            }
        };

        const equalizeSnapshotCards = () => {
            const cards = Array.from(parent.document.querySelectorAll(".snapshot-card"));
            if (!cards.length) return;

            cards.forEach((card) => {
                card.style.height = "auto";
            });

            const rows = new Map();
            cards.forEach((card) => {
                const top = Math.round(card.getBoundingClientRect().top);
                if (!rows.has(top)) rows.set(top, []);
                rows.get(top).push(card);
            });

            rows.forEach((rowCards) => {
                const maxHeight = Math.max(...rowCards.map((card) => card.getBoundingClientRect().height));
                rowCards.forEach((card) => {
                    card.style.height = `${maxHeight}px`;
                });
            });
        };

        const syncTogglePills = () => {
            const toggleLabels = Array.from(parent.document.querySelectorAll('div[data-testid="stToggle"] > label'));
            toggleLabels.forEach((label) => {
                const input = label.querySelector('input[type="checkbox"]');
                if (!input) return;
                label.setAttribute("data-checked", input.checked ? "true" : "false");
            });
        };

        let equalizeTimer = null;
        const scheduleEqualize = () => {
            if (equalizeTimer) {
                parent.clearTimeout(equalizeTimer);
            }
            equalizeTimer = parent.setTimeout(() => {
                equalizeSnapshotCards();
                syncTogglePills();
            }, 40);
        };

        syncMode();
        paint();
        scheduleEqualize();
        parent.addEventListener("pointermove", onMove, { passive: true });
        parent.addEventListener("resize", scheduleEqualize, { passive: true });
        if (desktopQuery.addEventListener) {
            desktopQuery.addEventListener("change", syncMode);
        } else if (desktopQuery.addListener) {
            desktopQuery.addListener(syncMode);
        }

        const observer = new parent.MutationObserver(scheduleEqualize);
        observer.observe(parent.document.body, { childList: true, subtree: true });
    })();
    </script>
    """,
    height=0,
)


CLASSROOM_DATA = {
    "eeg": {"alpha": 0.2, "beta": 0.7, "theta": 0.1, "gamma": 0.3},
    "metrics": {"focus": 35, "stress": 80, "fatigue": 60},
    "context": "User is sitting in a classroom, looking at notes.",
    "physio": {"heart_rate": 95, "stress_level": 80, "sleep_quality": 40},
    "behaviour": {"steps": 2000, "exercise_minutes": 10, "food_quality": "poor"},
    "journal": "I have exams coming up and feel overwhelmed.",
}

SOLO_WORK_DATA = {
    "eeg": {"alpha": 0.35, "beta": 0.55, "theta": 0.15, "gamma": 0.25},
    "metrics": {"focus": 65, "stress": 40, "fatigue": 30},
    "context": "User is working alone on a laptop, focused on a task.",
    "physio": {"heart_rate": 78, "stress_level": 35, "sleep_quality": 70},
    "behaviour": {"steps": 1200, "exercise_minutes": 5, "food_quality": "average"},
    "journal": "Working alone today. Feeling productive but slightly distracted at times.",
}

TEAMWORK_DATA = {
    "eeg": {"alpha": 0.15, "beta": 0.75, "theta": 0.2, "gamma": 0.4},
    "metrics": {"focus": 55, "stress": 65, "fatigue": 45},
    "context": "User is in a group discussion, collaborating with teammates.",
    "physio": {"heart_rate": 92, "stress_level": 70, "sleep_quality": 55},
    "behaviour": {"steps": 3000, "exercise_minutes": 20, "food_quality": "good"},
    "journal": "Team meeting today. Lots of pressure to contribute. Feeling stressed but engaged.",
}

SCENARIO_MAP = {
    "Focused solo session": SOLO_WORK_DATA,
    "High-stress class": CLASSROOM_DATA,
    "Collaborative meeting": TEAMWORK_DATA,
}

SITUATION_TO_TEMPLATE = {
    "SOLO WORK": SOLO_WORK_DATA,
    "STUDY GROUP": TEAMWORK_DATA,
    "MEETING": TEAMWORK_DATA,
    "LECTURE": CLASSROOM_DATA,
}


def clone_payload(template: dict) -> dict:
    return {
        "eeg": dict(template["eeg"]),
        "metrics": dict(template["metrics"]),
        "context": template["context"],
        "physio": dict(template["physio"]),
        "behaviour": dict(template["behaviour"]),
        "journal": template.get("journal", ""),
    }


def confidence_meta(confidence: float) -> tuple[str, str]:
    if confidence >= 0.85:
        return "High confidence", "status-good"
    if confidence >= 0.7:
        return "Moderate confidence", "status-warn"
    return "Low confidence", "status-alert"


def compute_score(metrics: dict) -> int:
    score = int((metrics["focus"] - metrics["stress"] - metrics["fatigue"] * 0.35) + 85)
    return max(0, min(score, 100))


def start_camera() -> None:
    if st.session_state.camera_running:
        return
    if CVModule is None:
        st.session_state.camera_error = (
            "Live camera mode is unavailable because the vision dependencies could not be imported."
        )
        return
    try:
        module = CVModule(show_window=False)
        module.start()
        st.session_state.camera_module = module
        st.session_state.camera_running = True
        st.session_state.live_auto_refresh = True
        st.session_state.camera_error = ""
    except Exception as exc:
        st.session_state.camera_module = None
        st.session_state.camera_running = False
        st.session_state.camera_error = str(exc)


def stop_camera() -> None:
    module = st.session_state.get("camera_module")
    if module is not None:
        try:
            module.stop()
        except Exception:
            pass
    st.session_state.camera_module = None
    st.session_state.camera_running = False


def manual_slider_with_na(label: str, min_value: int, max_value: int, default: int, key_base: str) -> tuple[int, bool]:
    slider_col, toggle_col = st.columns([5.2, 1.2], vertical_alignment="bottom")
    with slider_col:
        value = st.slider(label, min_value, max_value, default, key=f"{key_base}_value")
    with toggle_col:
        unavailable = st.toggle("N/A", key=f"{key_base}_na")
    return value, unavailable


def build_manual_payload() -> tuple[dict, dict | None]:
    st.markdown("#### Manual cognitive and physiological input")
    col1, col2 = st.columns(2)
    with col1:
        focus, focus_na = manual_slider_with_na("Focus", 0, 100, 58, "manual_focus")
        stress, stress_na = manual_slider_with_na("Stress", 0, 100, 44, "manual_stress")
        fatigue, fatigue_na = manual_slider_with_na("Fatigue", 0, 100, 38, "manual_fatigue")
        heart_rate, heart_rate_na = manual_slider_with_na("Heart rate", 50, 140, 81, "manual_heart_rate")
        sleep_quality, sleep_quality_na = manual_slider_with_na("Sleep quality", 0, 100, 72, "manual_sleep_quality")
        body_cols = st.columns([1, 1])
        with body_cols[0]:
            height_cm = st.number_input(
                "Height (cm)",
                min_value=50,
                max_value=260,
                value=170,
                step=1,
                key="manual_height_cm",
            )
        with body_cols[1]:
            weight_kg = st.number_input(
                "Weight (kg)",
                min_value=20,
                max_value=300,
                value=70,
                step=1,
                key="manual_weight_kg",
            )
    with col2:
        steps, steps_na = manual_slider_with_na("Steps", 0, 20000, 5400, "manual_steps")
        exercise, exercise_na = manual_slider_with_na("Exercise minutes", 0, 180, 30, "manual_exercise")
        food = st.selectbox("Food quality", ["good", "average", "poor"])
        context = st.text_area(
            "Context",
            value="User is studying independently with intermittent distractions.",
            height=124,
        )
        journal = st.text_area(
            "Optional note for analysis",
            value="",
            placeholder="Add a short check-in or symptom note.",
            height=92,
        )

    available_inputs = {
        "metrics": {
            "focus": not focus_na,
            "stress": not stress_na,
            "fatigue": not fatigue_na,
        },
        "physio": {
            "heart_rate": not heart_rate_na,
            "stress_level": not stress_na,
            "sleep_quality": not sleep_quality_na,
        },
        "behaviour": {
            "steps": not steps_na,
            "exercise_minutes": not exercise_na,
            "food_quality": True,
        },
    }

    payload = {
        "eeg": {band: round(random.uniform(0.1, 0.9), 2) for band in ["alpha", "beta", "theta", "gamma"]},
        "metrics": {"focus": focus, "stress": stress, "fatigue": fatigue},
        "context": context,
        "physio": {
            "heart_rate": heart_rate,
            "stress_level": stress,
            "sleep_quality": sleep_quality,
            "height_cm": height_cm,
            "weight_kg": weight_kg,
        },
        "behaviour": {"steps": steps, "exercise_minutes": exercise, "food_quality": food},
        "journal": journal,
        "available_inputs": available_inputs,
    }
    return payload, None


def build_demo_payload() -> tuple[dict, dict | None]:
    scenario = st.selectbox("Scenario", list(SCENARIO_MAP.keys()))
    base = clone_payload(SCENARIO_MAP[scenario])
    base["metrics"]["focus"] = max(0, min(100, base["metrics"]["focus"] + random.randint(-4, 4)))
    base["metrics"]["stress"] = max(0, min(100, base["metrics"]["stress"] + random.randint(-5, 5)))
    base["metrics"]["fatigue"] = max(0, min(100, base["metrics"]["fatigue"] + random.randint(-4, 4)))
    base["physio"]["heart_rate"] = max(55, min(130, base["physio"]["heart_rate"] + random.randint(-3, 3)))
    base["behaviour"]["steps"] = max(0, base["behaviour"]["steps"] + random.randint(-600, 600))
    return base, None


def build_live_payload() -> tuple[dict, dict | None]:
    controls = st.columns([1.2, 1, 1])
    with controls[0]:
        if st.button("Start camera sensing", use_container_width=True):
            start_camera()
    with controls[1]:
        if st.button("Stop camera", use_container_width=True):
            stop_camera()
    with controls[2]:
        st.session_state.live_auto_refresh = st.toggle(
            "Auto refresh",
            value=st.session_state.live_auto_refresh,
            help="Refresh the live environment snapshot automatically.",
        )

    refresh_seconds = st.slider(
        "Refresh interval (seconds)",
        min_value=2,
        max_value=10,
        value=st.session_state.live_refresh_seconds,
    )
    st.session_state.live_refresh_seconds = refresh_seconds

    if st.session_state.camera_error:
        st.warning(st.session_state.camera_error)

    module = st.session_state.get("camera_module")
    if not st.session_state.camera_running or module is None:
        fallback = clone_payload(SOLO_WORK_DATA)
        fallback["context"] = (
            "Live camera mode is idle. Start camera sensing to replace this fallback simulation "
            "with environment-aware context."
        )
        st.session_state.live_terminal_context = (
            "[main] Live camera mode is idle - start camera sensing to begin environment detection."
        )
        return fallback, None

    env_state = module.get_state()
    template = clone_payload(SITUATION_TO_TEMPLATE.get(env_state.situation, SOLO_WORK_DATA))

    fatigue_base = 35 + min(int(env_state.session_seconds / 90), 40)
    stress_bonus = 18 if env_state.cognitive_load == "high" else 8 if env_state.cognitive_load == "medium" else 0
    focus_shift = 10 if env_state.situation == "SOLO WORK" else -6 if env_state.situation == "LECTURE" else 0

    template["metrics"] = {
        "focus": max(15, min(95, template["metrics"]["focus"] + focus_shift)),
        "stress": max(15, min(96, template["metrics"]["stress"] + stress_bonus)),
        "fatigue": max(template["metrics"]["fatigue"], min(95, fatigue_base)),
    }
    template["physio"]["heart_rate"] = max(
        60,
        min(128, template["physio"]["heart_rate"] + (10 if env_state.cognitive_load == "high" else 0)),
    )
    template["context"] = (
        f"User is in a {env_state.scene} environment. Situation: {env_state.situation}. "
        f"People visible: {env_state.person_count}. Session duration: {env_state.session_seconds:.0f} seconds. "
        f"Cognitive load: {env_state.cognitive_load}."
    )
    template["journal"] = ""
    if env_state.situation == "UNKNOWN":
        st.session_state.live_terminal_context = (
            f"{env_state.as_dict()}\n\n"
            f"[main] Situation is {env_state.situation} - waiting for valid detection."
        )
    else:
        st.session_state.live_terminal_context = (
            f"{env_state.as_dict()}\n\n"
            f"User is in a {env_state.scene} environment.\n"
            f"Situation: {env_state.situation}.\n"
            f"People visible: {env_state.person_count}.\n"
            f"Session duration: {env_state.session_seconds:.0f} seconds.\n"
            f"Cognitive load: {env_state.cognitive_load}."
        )
    return template, env_state.as_dict()


def build_payload(source_mode: str) -> tuple[dict, dict | None]:
    if source_mode == "Manual":
        return build_manual_payload()
    if source_mode == "Live Camera":
        return build_live_payload()
    return build_demo_payload()


def input_is_available(payload: dict, section: str, key: str) -> bool:
    return payload.get("available_inputs", {}).get(section, {}).get(key, True)


def filtered_section(payload: dict, section: str) -> dict:
    values = payload.get(section, {})
    availability = payload.get("available_inputs", {}).get(section, {})
    return {key: value for key, value in values.items() if availability.get(key, True)}


def build_llm_physio(payload: dict) -> dict:
    physio = dict(filtered_section(payload, "physio"))
    height_cm = physio.get("height_cm")
    weight_kg = physio.get("weight_kg")

    if height_cm and weight_kg:
        height_m = height_cm / 100
        if height_m > 0:
            bmi = round(weight_kg / (height_m * height_m), 1)
            physio["bmi"] = bmi
            if bmi < 18.5:
                physio["bmi_band"] = "underweight"
            elif bmi < 25:
                physio["bmi_band"] = "healthy range"
            elif bmi < 30:
                physio["bmi_band"] = "overweight range"
            else:
                physio["bmi_band"] = "obesity range"
    return physio


def excluded_inputs(payload: dict) -> list[str]:
    labels = {
        ("metrics", "focus"): "focus",
        ("metrics", "stress"): "stress",
        ("metrics", "fatigue"): "fatigue",
        ("physio", "heart_rate"): "heart rate",
        ("physio", "sleep_quality"): "sleep quality",
        ("behaviour", "steps"): "steps",
        ("behaviour", "exercise_minutes"): "exercise minutes",
    }
    exclusions = []
    for (section, key), label in labels.items():
        if not input_is_available(payload, section, key):
            exclusions.append(label)
    return exclusions


def maybe_record_history(source_mode: str, payload: dict, result: dict, env_state: dict | None) -> None:
    metrics = payload["metrics"]
    signature = "|".join(
        [
            source_mode,
            result["state"],
            str(metrics["focus"]),
            str(metrics["stress"]),
            str(metrics["fatigue"]),
            str(env_state["situation"] if env_state else payload["context"][:32]),
        ]
    )

    if st.session_state.last_snapshot_key == signature:
        return

    st.session_state.last_snapshot_key = signature
    st.session_state.history.append(
        {
            "time": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            "state": result["state"],
            "focus": metrics["focus"],
            "stress": metrics["stress"],
            "fatigue": metrics["fatigue"],
            "score": compute_score(metrics),
            "heart_rate": payload["physio"]["heart_rate"],
            "source": source_mode,
            "situation": env_state["situation"] if env_state else "MANUAL",
        }
    )


def render_metric_card(label: str, value: str, subtle: str) -> None:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
            <div class="metric-subtle">{subtle}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_eeg_panel(eeg: dict) -> None:
    band_meta = {
        "alpha": {
            "color": "linear-gradient(90deg, #7af5c7, #80d6ff)",
            "note": "Calm alertness and steady readiness.",
        },
        "beta": {
            "color": "linear-gradient(90deg, #80d6ff, #57a7ff)",
            "note": "Active focus, analysis, and mental effort.",
        },
        "theta": {
            "color": "linear-gradient(90deg, #ffd27d, #ff9fbc)",
            "note": "Introspection, drift, or growing fatigue.",
        },
        "gamma": {
            "color": "linear-gradient(90deg, #a6b6ff, #80d6ff)",
            "note": "Higher-order integration and deep cognition.",
        },
    }

    items = list(eeg.items())
    columns = st.columns(2)
    for index, (name, value) in enumerate(items):
        meta = band_meta.get(
            name,
            {"color": "linear-gradient(90deg, #80d6ff, #7af5c7)", "note": "Signal intensity."},
        )
        percent = max(0, min(100, int(round(value * 100))))
        with columns[index % 2]:
            st.markdown(
                f"""
                <div class="eeg-band">
                    <div class="eeg-head">
                        <div class="eeg-name">{name}</div>
                        <div class="eeg-value">{percent}%</div>
                    </div>
                    <div class="eeg-track">
                        <div class="eeg-fill" style="width: {percent}%; background: {meta["color"]};"></div>
                    </div>
                    <div class="eeg-note">{meta["note"]}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def render_snapshot_metric(name: str, value: int, note: str, color: str) -> None:
    percent = max(0, min(100, int(value)))
    st.markdown(
        f"""
        <div class="snapshot-slot">
            <div class="snapshot-card">
                <div class="eeg-head">
                    <div class="eeg-name">{name}</div>
                    <div class="eeg-value">{percent}%</div>
                </div>
                <div class="eeg-track">
                    <div class="eeg-fill" style="width: {percent}%; background: {color};"></div>
                </div>
                <div class="snapshot-note">{note}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_snapshot_stat(name: str, value: str, note: str) -> None:
    st.markdown(
        f"""
        <div class="snapshot-slot">
            <div class="snapshot-card">
                <div class="eeg-name">{name}</div>
                <div class="snapshot-value">{value}</div>
                <div class="snapshot-note">{note}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_snapshot_metric_state(name: str, value: int, note: str, color: str, available: bool) -> None:
    if not available:
        render_snapshot_stat(name, "N/A", "Excluded from AI reasoning and breakdowns.")
        return
    render_snapshot_metric(name, value, note, color)


def render_snapshot_stat_state(name: str, value: str, note: str, available: bool) -> None:
    if not available:
        render_snapshot_stat(name, "N/A", "Excluded from AI reasoning and breakdowns.")
        return
    render_snapshot_stat(name, value, note)


with st.sidebar:
    st.markdown("### NeuroSense")
    st.caption("A glass-console for cognitive and physiological state sensing.")
    source_mode = st.radio("Signal source", ["Live Camera", "Manual", "Demo"], index=0)
    st.divider()
    st.markdown("#### Workflow")
    st.write("Use the dashboard for a current snapshot, then move into insights and journal reflection.")
    if st.button("Reset session data", use_container_width=True):
        stop_camera()
        reset_values = {
            "history": [],
            "journals": [],
            "last_summary": "",
            "current_entry": "",
            "clear_input": False,
            "last_snapshot_key": "",
            "last_chat_reply": "",
            "last_insight_reply": "",
            "live_terminal_context": "",
        }
        for key, value in reset_values.items():
            st.session_state[key] = value
        st.rerun()


payload, env_state = build_payload(source_mode)
result = interpret(payload)
maybe_record_history(source_mode, payload, result, env_state)
excluded_input_labels = excluded_inputs(payload)

llm_input = {
    "state": result["state"],
    "confidence": result["confidence"],
    "reasoning": result["reasoning"],
    "history": [item["state"] for item in st.session_state.history[-5:]],
    "journal": payload.get("journal", ""),
    "physio": build_llm_physio(payload),
    "behaviour": filtered_section(payload, "behaviour"),
    "excluded_inputs": excluded_input_labels,
}

advice = generate_advice(llm_input)
score = compute_score(payload["metrics"])
confidence_label, confidence_class = confidence_meta(result["confidence"])

# Kept for development/debug use even though confidence is no longer shown in the UI.
dev_confidence_meta = {
    "value": result["confidence"],
    "label": confidence_label,
    "class": confidence_class,
}

context_display = payload["context"]
if source_mode == "Live Camera":
    context_display = st.session_state.get("live_terminal_context") or payload["context"]

st.markdown(
    f"""
    <div class="hero">
        <div class="eyebrow">Cognitive wellbeing cockpit</div>
        <div class="hero-title">NeuroSense Console</div>
        <div class="hero-copy">
            Live camera context, simulated EEG and physiology, and journal reflection are now
            brought together in one interface. Switch input modes in the sidebar and use the
            tabs below to move from current-state sensing into trends and personal notes.
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

overview_tab, insights_tab, journal_tab = st.tabs(["Dashboard", "Insights", "Journal"])

with overview_tab:
    top_cols = st.columns(4)
    top_card_data = [
        ("Current State", result["state"], payload["context"][:64]),
        ("Wellbeing Score", f"{score}/100", f"Source: {source_mode}"),
        (
            "Heart Rate",
            f"{payload['physio']['heart_rate']} bpm",
            f"Sleep quality: {payload['physio']['sleep_quality']}/100",
        ),
        (
            "Signal Mode",
            source_mode,
            env_state["situation"].title() if env_state else payload["behaviour"]["food_quality"].title(),
        ),
    ]
    for column, (label, value, subtle) in zip(top_cols, top_card_data):
        with column:
            st.markdown('<div class="metric-slot">', unsafe_allow_html=True)
            render_metric_card(label, value, subtle)
            st.markdown("</div>", unsafe_allow_html=True)

    left, right = st.columns([1.2, 0.8], gap="large")
    with left:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Signal snapshot</div>', unsafe_allow_html=True)
        if excluded_input_labels and source_mode == "Manual":
            st.caption(f"Excluded from AI reasoning: {', '.join(excluded_input_labels)}")
        st.markdown('<div class="snapshot-row">', unsafe_allow_html=True)
        metric_cols = st.columns(3)
        with metric_cols[0]:
            render_snapshot_metric_state(
                "Focus",
                payload["metrics"]["focus"],
                "Cognitive steadiness and task engagement right now.",
                "linear-gradient(90deg, #7af5c7, #80d6ff)",
                input_is_available(payload, "metrics", "focus"),
            )
        with metric_cols[1]:
            render_snapshot_metric_state(
                "Stress",
                payload["metrics"]["stress"],
                "Mental and physiological strain across the current snapshot.",
                "linear-gradient(90deg, #ffd27d, #ff9fbc)",
                input_is_available(payload, "metrics", "stress"),
            )
        with metric_cols[2]:
            render_snapshot_metric_state(
                "Fatigue",
                payload["metrics"]["fatigue"],
                "Signs of cognitive drain, depletion, or reduced resilience.",
                "linear-gradient(90deg, #a6b6ff, #80d6ff)",
                input_is_available(payload, "metrics", "fatigue"),
            )
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown('<div class="snapshot-row">', unsafe_allow_html=True)
        phys_cols = st.columns(3)
        with phys_cols[0]:
            render_snapshot_stat_state(
                "Steps",
                f"{payload['behaviour']['steps']:,}",
                "Daily movement can buffer stress and sharpen regulation.",
                input_is_available(payload, "behaviour", "steps"),
            )
        with phys_cols[1]:
            render_snapshot_stat_state(
                "Exercise",
                f"{payload['behaviour']['exercise_minutes']} min",
                "Short activity bursts often lift energy and concentration.",
                input_is_available(payload, "behaviour", "exercise_minutes"),
            )
        with phys_cols[2]:
            render_snapshot_stat_state(
                "Nutrition",
                payload["behaviour"]["food_quality"].title(),
                "Food quality influences steadiness, recovery, and mood.",
                input_is_available(payload, "behaviour", "food_quality"),
            )
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown('<div class="section-title">Reasoning trace</div>', unsafe_allow_html=True)
        if result["reasoning"]:
            st.markdown(
                "".join(f"<span class='pill'>{reason}</span>" for reason in result["reasoning"]),
                unsafe_allow_html=True,
            )
        else:
            st.caption("No strong reasoning signals were detected in this snapshot.")

        st.markdown('<div class="section-title">Context</div>', unsafe_allow_html=True)
        st.code(context_display, language="text")
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">AI guidance</div>', unsafe_allow_html=True)
        st.write(advice)
        dashboard_question = st.text_input(
            "Ask a follow-up about the current state",
            placeholder="What should I do in the next 15 minutes?",
            key="dashboard_question",
        )
        if dashboard_question:
            st.session_state.last_chat_reply = generate_advice({**llm_input, "journal": dashboard_question})
        if st.session_state.last_chat_reply:
            st.info(st.session_state.last_chat_reply)
        st.markdown("</div>", unsafe_allow_html=True)

    with right:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Live environment</div>', unsafe_allow_html=True)
        if env_state:
            env_cols = st.columns(2)
            with env_cols[0]:
                st.metric("Scene", env_state["scene"].title())
                st.metric("Situation", env_state["situation"].title())
                st.metric("People visible", env_state["person_count"])
            with env_cols[1]:
                st.metric("Cognitive load", env_state["cognitive_load"].title())
                st.metric("Scene confidence", f"{int(env_state['scene_confidence'] * 100)}%")
                st.metric("Session length", f"{int(env_state['session_seconds'])}s")
        else:
            st.write(
                "Manual and demo modes still feed the full interpretation pipeline, but the live environment "
                "panel activates when camera sensing is running."
            )
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">EEG band blend</div>', unsafe_allow_html=True)
        render_eeg_panel(payload["eeg"])
        st.markdown("</div>", unsafe_allow_html=True)

with insights_tab:
    history = st.session_state.history
    if history:
        history_df = pd.DataFrame(history)
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Trend view</div>', unsafe_allow_html=True)
        st.line_chart(history_df.set_index("time")[["focus", "stress", "fatigue", "score"]])
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Recent state transitions</div>', unsafe_allow_html=True)
        for item in history[-8:][::-1]:
            st.write(
                f"{item['time']} | {item['state']} | score {item['score']} | "
                f"{item['source']} | {item['situation']}"
            )

        if len(history_df) >= 3:
            last_three = history_df.tail(3)
            if (
                not st.session_state.last_summary
                or abs(int(last_three["stress"].iloc[-1]) - int(last_three["stress"].iloc[-2])) >= 15
            ):
                st.session_state.last_summary = generate_advice(
                    {
                        "state": "Trend Analysis",
                        "confidence": 0.78,
                        "reasoning": list(last_three["state"]),
                        "history": list(history_df["state"].tail(6)),
                        "journal": "",
                        "physio": {"heart_rate": int(history_df["heart_rate"].tail(1).iloc[0])},
                        "behaviour": {},
                    }
                )
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Pattern insight</div>', unsafe_allow_html=True)
        if st.session_state.last_summary:
            st.write(st.session_state.last_summary)
        else:
            st.write("More history will unlock a stronger trend summary.")

        insight_question = st.text_input(
            "Ask about the pattern",
            placeholder="What does this trend suggest about my workload?",
            key="insight_question",
        )
        if insight_question:
            st.session_state.last_insight_reply = generate_advice(
                {**llm_input, "history": list(history_df["state"].tail(8)), "journal": insight_question}
            )
        if st.session_state.last_insight_reply:
            st.info(st.session_state.last_insight_reply)
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.info("History will appear here once the app has captured a few snapshots.")

with journal_tab:
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Reflection journal</div>', unsafe_allow_html=True)

    if st.session_state.clear_input:
        st.session_state.current_entry = ""
        st.session_state.clear_input = False

    entry = st.text_area(
        "Write your thoughts",
        key="current_entry",
        placeholder="Describe how you feel, what you were doing, or anything you want the model to consider.",
        height=160,
    )

    journal_cols = st.columns([1, 1.3])
    with journal_cols[0]:
        if st.button("Save entry", use_container_width=True):
            if entry.strip():
                st.session_state.journals.append(
                    {"text": entry.strip(), "time": datetime.now().strftime("%d/%m/%Y %H:%M:%S")}
                )
                st.session_state.clear_input = True
                st.rerun()
    with journal_cols[1]:
        if st.button("Analyze current entry", use_container_width=True):
            if entry.strip():
                st.session_state.last_insight_reply = generate_advice(
                    {
                        "state": result["state"],
                        "confidence": result["confidence"],
                        "reasoning": result["reasoning"],
                        "history": [item["state"] for item in st.session_state.history[-5:]],
                        "journal": entry.strip(),
                        "physio": payload["physio"],
                        "behaviour": payload["behaviour"],
                    }
                )

    if st.session_state.last_insight_reply:
        st.info(st.session_state.last_insight_reply)

    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Saved entries</div>', unsafe_allow_html=True)

    selected_entries = []
    for idx, item in enumerate(reversed(st.session_state.journals)):
        label = f"{item['time']} | {item['text'][:100]}"
        if st.checkbox(label, key=f"journal_item_{idx}"):
            selected_entries.append(item["text"])

    if st.button("Analyze selected entries"):
        if selected_entries:
            st.session_state.last_summary = generate_advice(
                {
                    "state": "Journal Analysis",
                    "confidence": 0.74,
                    "reasoning": result["reasoning"],
                    "history": [item["state"] for item in st.session_state.history[-5:]],
                    "journal": " ".join(selected_entries),
                    "physio": payload["physio"],
                    "behaviour": payload["behaviour"],
                }
            )

    if st.session_state.last_summary:
        st.write(st.session_state.last_summary)
    else:
        st.write("Select journal entries to generate a longer reflection.")
    st.markdown("</div>", unsafe_allow_html=True)


if source_mode != "Live Camera" and st.session_state.camera_running:
    stop_camera()

if source_mode == "Live Camera" and st.session_state.camera_running and st.session_state.live_auto_refresh:
    time.sleep(st.session_state.live_refresh_seconds)
    st.rerun()
