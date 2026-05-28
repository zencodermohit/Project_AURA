"""
AURA - AI Personality, Aura, & MBTI Selfie Dashboard
===================================================

Streamlit-based frontend for the AURA project. This dashboard provides a
premium, futuristic interface. It supports two modes:
1. 🔮 Text Aura Reader: Submit text and receive a sentiment-keyword aura.
2. 🧬 MBTI & Selfie Reader: A 3-step wizard with 20 questions and a selfie camera
   input to decode your MBTI profile and visual aura!
"""

import streamlit as st
import requests
import json
import time
import os
from datetime import datetime

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

API_URL: str = os.environ.get("API_URL", "https://projectaura-production.up.railway.app")

# Aura color mapping
AURA_COLORS: dict[str, str] = {
    "visionary":  "#9B59B6",
    "strategic":  "#3498DB",
    "calm_sage":  "#1ABC9C",
    "rebel":      "#E74C3C",
    "analytical": "#5DADE2",
    "empathic":   "#2ECC71",
    "leader":     "#F39C12",
    "mystic":     "#00BCD4",
}

DEFAULT_AURA_COLOR: str = "#9B59B6"

# ---------------------------------------------------------------------------
# Page Configuration (must be the first Streamlit command)
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="✨ AURA - AI MBTI & Aura Reader",
    page_icon="🔮",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ---------------------------------------------------------------------------
# Session State Initialization
# ---------------------------------------------------------------------------

# Text Aura Mode State
if "analyzing" not in st.session_state:
    st.session_state.analyzing = False
if "current_result" not in st.session_state:
    st.session_state.current_result = None
if "request_id" not in st.session_state:
    st.session_state.request_id = None

# MBTI Mode State
if "mbti_step" not in st.session_state:
    st.session_state.mbti_step = 1  # 1: Questions, 2: Camera, 3: Results
if "mbti_answers" not in st.session_state:
    st.session_state.mbti_answers = {}
if "mbti_photo_bytes" not in st.session_state:
    st.session_state.mbti_photo_bytes = None
if "mbti_result" not in st.session_state:
    st.session_state.mbti_result = None
if "mbti_submitting" not in st.session_state:
    st.session_state.mbti_submitting = False

# ---------------------------------------------------------------------------
# CSS Loader
# ---------------------------------------------------------------------------

def load_css() -> None:
    """Load the custom style.css and inject it."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    css_path = os.path.join(script_dir, "static", "style.css")

    if not os.path.exists(css_path):
        css_path = "/app/static/style.css"

    if os.path.exists(css_path):
        with open(css_path, "r", encoding="utf-8") as f:
            css_content = f.read()
        st.markdown(f"<style>{css_content}</style>", unsafe_allow_html=True)
    else:
        st.warning("⚠️ Custom stylesheet not found.")

# ---------------------------------------------------------------------------
# Helper: Resolve Aura Color
# ---------------------------------------------------------------------------

def get_aura_color(aura_type: str) -> str:
    if not aura_type:
        return DEFAULT_AURA_COLOR
    key = aura_type.lower().replace(" ", "_").replace("-", "_").replace("rebel_creator", "rebel").replace("analytical_thinker", "analytical").replace("empathic_soul", "empathic").replace("ambitious_leader", "leader").replace("mystic_dreamer", "mystic")
    return AURA_COLORS.get(key, DEFAULT_AURA_COLOR)

# ---------------------------------------------------------------------------
# Helper: Safe API Request
# ---------------------------------------------------------------------------

def api_request(method: str, endpoint: str, **kwargs) -> dict | list | None:
    try:
        url = f"{API_URL}{endpoint}"
        response = requests.request(method, url, timeout=20, **kwargs)
        response.raise_for_status()
        return response.json()
    except Exception:
        return None

# ---------------------------------------------------------------------------
# UI Component: Header & Side Menu
# ---------------------------------------------------------------------------

def render_header(mode_label: str) -> None:
    st.markdown(
        f"""
        <div class="aura-header">
            <h1>✨ AURA</h1>
            <div class="subtitle">{mode_label}</div>
            <div class="header-divider"></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

def render_sidebar() -> str:
    with st.sidebar:
        st.markdown(
            """
            <div style="text-align: center; padding-top: 1rem;">
                <span style="font-size: 3rem;">🔮</span>
                <h3 style="margin-top: 0.5rem; letter-spacing: 2px;">AURA SYSTEM</h3>
                <p style="font-size: 0.8rem; color: #a0a0a0;">Distributed AI Vibe Decoders</p>
            </div>
            <hr/>
            """,
            unsafe_allow_html=True
        )
        
        mode = st.radio(
            "Select Analysis Mode:",
            options=["🧬 MBTI & Camera Selfie", "🔮 Text Sentiment Aura"],
            index=0,
            key="analysis_mode"
        )
        
        st.markdown(
            f"""
            <hr/>
            <div style="padding: 10px; background: rgba(255,255,255,0.02); border-radius: 8px; border: 1px solid rgba(255,255,255,0.05);">
                <div style="font-size: 0.75rem; color:#888; text-transform: uppercase;">Infrastructure Status</div>
                <div style="font-size: 0.85rem; margin-top: 5px; display:flex; align-items:center; gap: 8px;">
                    <span style="color:#2ecc71;">●</span> FastAPI: <code>{API_URL}</code>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
    return mode

# ---------------------------------------------------------------------------
# MODE 1: Text Sentiment Aura
# ---------------------------------------------------------------------------

def render_text_input_section() -> None:
    st.markdown('<div class="input-section">', unsafe_allow_html=True)
    st.markdown(
        '<div class="section-header">'
        '<span class="icon">💬</span> Share Your Thoughts'
        '</div>',
        unsafe_allow_html=True,
    )

    user_text = st.text_area(
        "Enter your text below",
        placeholder="Share your thoughts, dreams, and aspirations... Let our AI read your verbal aura.",
        height=160,
        label_visibility="collapsed",
    )

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        analyze_clicked = st.button(
            "🔮 Analyze My verbal Aura",
            type="primary",
            use_container_width=True,
            disabled=st.session_state.analyzing,
        )

    if analyze_clicked:
        if not user_text or not user_text.strip():
            st.warning("✏️ Please enter some text before analyzing.")
        else:
            result = api_request("post", "/analyze", json={"text": user_text.strip()})
            if result and "request_id" in result:
                st.session_state.request_id = result["request_id"]
                st.session_state.analyzing = True
                st.session_state.current_result = None
                st.rerun()
            else:
                st.error("🔌 Unable to reach the backend API.")

    st.markdown("</div>", unsafe_allow_html=True)

def render_text_analyzing_animation() -> None:
    try:
        from streamlit_autorefresh import st_autorefresh
        st_autorefresh(interval=3000, limit=None, key="text_aura_refresh")
    except ImportError:
        pass

    st.markdown(
        """
        <div class="analyzing-container">
            <div class="analyzing-orb"></div>
            <div class="analyzing-text">🔮 Analyzing Verbal Aura...</div>
            <div class="analyzing-subtext">Decoding word patterns and sentiment flow</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.session_state.request_id:
        result = api_request("get", f"/results/{st.session_state.request_id}")
        if result and isinstance(result, dict) and result.get("aura_type"):
            st.session_state.current_result = result
            st.session_state.analyzing = False
            st.rerun()

def render_text_results(result: dict) -> None:
    aura_type = result.get("aura_type", "Unknown")
    aura_color = get_aura_color(aura_type)
    energy_score = result.get("energy_score", 0)
    confidence = result.get("confidence_score", 0)
    traits = result.get("personality_traits", [])
    keywords = result.get("keywords_detected", [])
    sentiment = result.get("sentiment", {})
    energy_description = result.get("energy_level", "")
    timestamp = result.get("timestamp", "")

    st.markdown('<div class="results-section">', unsafe_allow_html=True)
    st.markdown(
        f"""
        <div class="aura-card" style="border-left: 4px solid {aura_color};">
            <div style="display:flex;align-items:center;gap:2rem;flex-wrap:wrap;">
                <div style="flex:1;min-width:250px;">
                    <div class="aura-type-name" style="color:{aura_color};">
                        🔮 {aura_type}
                    </div>
                    <div class="aura-energy-desc">
                        {energy_description or "Your verbal energy signature has been parsed successfully."}
                    </div>
                </div>
                <div style="flex-shrink:0;">
                    <div style="
                        width:110px;height:110px;border-radius:50%;
                        background:radial-gradient(circle,{aura_color}40,{aura_color}10,transparent);
                        box-shadow:0 0 50px {aura_color}60,0 0 100px {aura_color}30;
                    "></div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_en, col_conf = st.columns(2)
    with col_en:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-value" style="color:{aura_color};">{energy_score}</div>
                <div class="metric-label">Energy Score</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown(
            f"""
            <div class="energy-bar-container">
                <div class="energy-bar-track">
                    <div class="energy-bar-fill" style="width: {energy_score}%; background: {aura_color};"></div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_conf:
        radius = 48
        circ = 2 * 3.14159 * radius
        offset = circ - (confidence / 100) * circ
        st.markdown(
            f"""
            <div class="metric-card" style="padding-bottom:2.5rem; display:flex; flex-direction:column; align-items:center;">
                <div style="position:relative; width:120px; height:100px; margin: 0 auto;">
                    <svg width="100" height="100" viewBox="0 0 120 120" style="transform: rotate(-90deg);">
                        <circle cx="60" cy="60" r="{radius}" fill="none" stroke="rgba(255,255,255,0.05)" stroke-width="8" />
                        <circle cx="60" cy="60" r="{radius}" fill="none" stroke="{aura_color}" stroke-width="8"
                                stroke-dasharray="{circ}" stroke-dashoffset="{offset}" stroke-linecap="round" />
                    </svg>
                    <div style="position:absolute; top:50%; left:50%; transform:translate(-50%, -50%); font-size:1.4rem; font-weight:700; color:{aura_color};">
                        {confidence}%
                    </div>
                </div>
                <div class="metric-label" style="margin-top:10px;">Confidence Score</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    if traits:
        st.markdown("---")
        st.markdown('<div class="section-header">🧬 Verbal Traits</div>', unsafe_allow_html=True)
        tags_html = "".join(f'<span class="trait-tag" style="background: {aura_color}25; border: 1px solid {aura_color}60;">{t}</span>' for t in traits)
        st.markdown(f'<div class="trait-tags-container">{tags_html}</div>', unsafe_allow_html=True)

    if keywords:
        st.markdown('<div class="section-header">🔑 Semantic Keywords</div>', unsafe_allow_html=True)
        kw_html = "".join(f'<span class="keyword-tag">{kw}</span>' for kw in keywords)
        st.markdown(f'<div class="trait-tags-container">{kw_html}</div>', unsafe_allow_html=True)

    if sentiment:
        st.markdown("---")
        st.markdown('<div class="section-header">📊 Sentiment Core</div>', unsafe_allow_html=True)
        pol = sentiment.get("polarity", 0)
        sub = sentiment.get("subjectivity", 0)
        comp = sentiment.get("compound", 0)
        st.markdown(
            f"""
            <div class="sentiment-container">
                <div class="sentiment-item"><div class="sentiment-value" style="color:{aura_color};">{pol:+.2f}</div><div class="sentiment-label">Polarity</div></div>
                <div class="sentiment-item"><div class="sentiment-value" style="color:{aura_color};">{sub:.2f}</div><div class="sentiment-label">Subjectivity</div></div>
                <div class="sentiment-item"><div class="sentiment-value" style="color:{aura_color};">{comp:+.2f}</div><div class="sentiment-label">VADER Compound</div></div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    if timestamp:
        st.markdown(f'<div class="timestamp">Analyzed at {timestamp[:19].replace("T", " ")}</div>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)



# ---------------------------------------------------------------------------
# MODE 2: MBTI & Camera Selfie Reader
# ---------------------------------------------------------------------------

MBTI_QUESTIONS_DATA = [
    # Questions are deliberately shuffled across all 4 dimensions and worded
    # indirectly so users cannot game the system or predict their type.
    # The "section" labels are vague to hide what is being measured.

    # T vs F (disguised)
    {"id": "q1", "text": "When a close friend makes a terrible decision, you'd rather tell them the honest truth than protect their feelings.", "section": "Inner Compass"},
    # J vs P (disguised)
    {"id": "q2", "text": "You often start packing for a trip the night before instead of days ahead.", "section": "Life Rhythm"},
    # E vs I (disguised)
    {"id": "q3", "text": "After a long, exhausting week, your ideal Friday night involves other people.", "section": "Energy Source"},
    # S vs N (disguised)
    {"id": "q4", "text": "You sometimes zone out of a conversation because a random thought chain pulled you somewhere fascinating.", "section": "Mental Lens"},
    # T vs F (disguised)
    {"id": "q5", "text": "You find it hard to enjoy a movie if the plot has logical holes, even if it's emotionally powerful.", "section": "Inner Compass"},
    # E vs I (disguised)
    {"id": "q6", "text": "You tend to think out loud — your best ideas come from talking, not sitting in silence.", "section": "Energy Source"},
    # S vs N (disguised)
    {"id": "q7", "text": "You notice when a picture frame is slightly crooked or when someone changes their hairstyle.", "section": "Mental Lens"},
    # J vs P (disguised)
    {"id": "q8", "text": "You feel a quiet satisfaction when every item on your to-do list is checked off.", "section": "Life Rhythm"},
    # E vs I (disguised)
    {"id": "q9", "text": "Being alone for an entire weekend sounds more refreshing than draining.", "section": "Energy Source"},
    # S vs N (disguised)
    {"id": "q10", "text": "You are more interested in what could exist than what already does.", "section": "Mental Lens"},
    # T vs F (disguised)
    {"id": "q11", "text": "When two friends are fighting, you instinctively try to understand both sides logically rather than comfort either one first.", "section": "Inner Compass"},
    # J vs P (disguised)
    {"id": "q12", "text": "Unexpected changes to your plans genuinely excite you more than they annoy you.", "section": "Life Rhythm"},
    # E vs I (disguised)
    {"id": "q13", "text": "You recharge by going somewhere crowded and lively, not by retreating to a quiet room.", "section": "Energy Source"},
    # S vs N (disguised)
    {"id": "q14", "text": "You trust your gut feeling about someone even when there is no logical reason to.", "section": "Mental Lens"},
    # T vs F (disguised)
    {"id": "q15", "text": "You believe the world would be better if people relied on reason instead of emotions for big decisions.", "section": "Inner Compass"},
    # J vs P (disguised)
    {"id": "q16", "text": "You prefer keeping your options open rather than committing to one fixed plan early.", "section": "Life Rhythm"},
    # E vs I (disguised)
    {"id": "q17", "text": "You often process your deepest thoughts internally and share only the conclusion.", "section": "Energy Source"},
    # S vs N (disguised)
    {"id": "q18", "text": "You would rather master a proven skill than experiment with an unproven theory.", "section": "Mental Lens"},
    # T vs F (disguised)
    {"id": "q19", "text": "You easily absorb the emotions of people around you, even strangers.", "section": "Inner Compass"},
    # J vs P (disguised)
    {"id": "q20", "text": "Your workspace is messy but you have a strange internal system that works perfectly for you.", "section": "Life Rhythm"},
]

def render_mbti_stepper(step: int) -> None:
    s1_class = "completed" if step > 1 else ("active" if step == 1 else "")
    s2_class = "completed" if step > 2 else ("active" if step == 2 else "")
    s3_class = "active" if step == 3 else ""
    
    st.markdown(
        f"""
        <div class="stepper-container">
            <div class="stepper-line"></div>
            <div class="stepper-step {s1_class}">
                <div class="step-circle">1</div>
                <div class="step-label">Questions</div>
            </div>
            <div class="stepper-step {s2_class}">
                <div class="step-circle">2</div>
                <div class="step-label">Vibe Capture</div>
            </div>
            <div class="stepper-step {s3_class}">
                <div class="step-circle">3</div>
                <div class="step-label">MBTI Reveal</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

def render_mbti_questionnaire() -> None:
    st.markdown("<h3 class='text-center mt-2'>🧬 MBTI Personality Questionnaire</h3>", unsafe_allow_html=True)
    st.markdown("<p class='text-center opacity-75'>Answer these 20 questions to analyze your baseline personality profile.</p>", unsafe_allow_html=True)
    
    # Initialize answers mapping if empty
    if not st.session_state.mbti_answers:
        st.session_state.mbti_answers = {q["id"]: 3 for q in MBTI_QUESTIONS_DATA}
        
    current_section = ""
    
    for q in MBTI_QUESTIONS_DATA:
        if q["section"] != current_section:
            current_section = q["section"]
            st.markdown(f"<h4 style='color:#9B59B6; margin-top:2rem; border-bottom:1px solid rgba(255,255,255,0.05); padding-bottom:5px;'>✦ {current_section}</h4>", unsafe_allow_html=True)
            
        st.markdown(f"<div class='question-card'><div class='question-text'>{q['text']}</div>", unsafe_allow_html=True)
        
        # Horizontal agreement radio buttons
        ans = st.radio(
            label=f"Radio_{q['id']}",
            options=[1, 2, 3, 4, 5],
            format_func=lambda x: {
                1: "Disagree",
                2: "Slightly Disagree",
                3: "Neutral",
                4: "Slightly Agree",
                5: "Agree"
            }[x],
            index=st.session_state.mbti_answers.get(q["id"], 3) - 1,
            key=f"radio_{q['id']}",
            label_visibility="collapsed"
        )
        st.session_state.mbti_answers[q["id"]] = ans
        st.markdown("</div>", unsafe_allow_html=True)
        
    st.markdown("<br/>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if st.button("📸 Capture My Selfie Vibe", type="primary", use_container_width=True):
            st.session_state.mbti_step = 2
            st.rerun()

def render_mbti_camera_capture() -> None:
    st.markdown("""
    <div style="background: rgba(155, 89, 182, 0.15); border: 2px dashed #9B59B6; border-radius: 12px; padding: 25px; text-align: center; margin-top: 20px; margin-bottom: 25px; box-shadow: 0 0 25px rgba(155, 89, 182, 0.2);">
        <h2 style="color: #9B59B6; margin-top: 0; font-size: 2.2rem; letter-spacing: 2px;">📸 STEP 2: CAMERA CAPTURE</h2>
        <p style="font-size: 1.15rem; color: #fff; max-width: 600px; margin: 10px auto 0 auto; line-height: 1.6;">
            Our visual processing engine needs to scan your face to detect brightness, color balance, and entropy to derive your aura. 
            <br/><br/>
            <span style="color: #1ABC9C; font-weight: bold; font-size: 1.3rem;">👇 CLICK THE 'TAKE PHOTO' BUTTON INSIDE THE BOX BELOW 👇</span>
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    img_buffer = st.camera_input("Camera Feed", key="mbti_selfie_camera", label_visibility="collapsed")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("⬅ Back to Questions", use_container_width=True):
            st.session_state.mbti_step = 1
            st.rerun()
            
    with col2:
        # Proceed either with a photo or fallback with neutral
        disabled = False
        button_label = "🔮 Reveal My MBTI Aura"
        if img_buffer is None:
            button_label = "🔮 Reveal Without Photo"
            
        if st.button(button_label, type="primary", use_container_width=True, disabled=disabled):
            st.session_state.mbti_submitting = True
            
            # Pack payload
            answers_str = json.dumps(st.session_state.mbti_answers)
            data = {"answers": answers_str}
            
            files = {}
            if img_buffer is not None:
                files = {"file": ("selfie.jpg", img_buffer.getvalue(), "image/jpeg")}
                
            with st.spinner("Decoding your personality vibe..."):
                try:
                    res = requests.post(f"{API_URL}/analyze/mbti", data=data, files=files, timeout=25)
                    if res.ok:
                        st.session_state.mbti_result = res.json()
                        st.session_state.mbti_step = 3
                    else:
                        st.error(f"Error calling backend: {res.text}")
                except Exception as e:
                    st.error(f"Could not connect to FastAPI server: {e}")
                    
            st.session_state.mbti_submitting = False
            st.rerun()

def render_mbti_dichotomy_bar(left_label: str, left_val: int, right_label: str, right_val: int, color: str) -> None:
    st.markdown(
        f"""
        <div class="dichotomy-row">
            <div class="dichotomy-labels">
                <span style="color:{color if left_val >= 50 else '#888'};">{left_label} ({left_val}%)</span>
                <span style="color:{color if right_val >= 50 else '#888'};">{right_label} ({right_val}%)</span>
            </div>
            <div class="dichotomy-bar-container">
                <div class="dichotomy-fill-left" style="width:{left_val}%; background:linear-gradient(90deg, {color}, {color}99); opacity:{1 if left_val >= 50 else 0.3};"></div>
                <div class="dichotomy-fill-right" style="width:{right_val}%; background:linear-gradient(90deg, {color}99, {color}); opacity:{1 if right_val >= 50 else 0.3};"></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

def render_mbti_results_reveal() -> None:
    result = st.session_state.mbti_result
    if not result:
        st.warning("⚠️ No MBTI results found.")
        st.session_state.mbti_step = 1
        st.rerun()
        
    mbti_type = result.get("mbti_type", "INFJ")
    title = result.get("title", "Advocate")
    aura_color = result.get("aura_color", "#1ABC9C")
    energy_level = result.get("energy_level", "")
    traits = result.get("traits", [])
    desc = result.get("description", "")
    careers = result.get("careers", [])
    famous = result.get("famous_people", [])
    romantic = result.get("romantic_compatible", [])
    en_score = result.get("energy_score", 50)
    conf_score = result.get("confidence_score", 50)
    dichotomies = result.get("dichotomies", {})
    vibe = result.get("vibe", {})
    photo_url = result.get("photo_url")
    
    st.markdown("<h2 class='text-center mt-2'>🔮 Your Personality Aura Decoded</h2>", unsafe_allow_html=True)
    
    # MASSIVE GLOWING AURA PERCENTAGE CIRCLE
    circumference = 2 * 3.14159 * 90
    offset = circumference - (en_score / 100) * circumference
    
    st.markdown(f"""
    <div style="display: flex; justify-content: center; align-items: center; margin-top: 1rem; margin-bottom: 2.5rem; flex-direction: column;">
        <div style="position: relative; width: 220px; height: 220px; animation: float-in 0.8s ease-out;">
            <!-- Outer Glow SVG -->
            <svg width="220" height="220" viewBox="0 0 200 200" style="transform: rotate(-90deg);">
                <circle cx="100" cy="100" r="90" fill="none" stroke="{aura_color}15" stroke-width="12" />
                <circle cx="100" cy="100" r="90" fill="none" stroke="{aura_color}" stroke-width="12" 
                    stroke-dasharray="{circumference}" stroke-dashoffset="{offset}" 
                    stroke-linecap="round" style="filter: drop-shadow(0 0 20px {aura_color}); transition: stroke-dashoffset 2s ease-out;" />
            </svg>
            <!-- Center Text -->
            <div style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; display: flex; flex-direction: column; justify-content: center; align-items: center;">
                <span style="font-size: 4rem; font-weight: 800; color: #fff; text-shadow: 0 0 25px {aura_color}; line-height: 1;">{en_score}<span style="font-size: 1.5rem; opacity:0.8;">%</span></span>
                <span style="font-size: 0.9rem; color: #eee; text-transform: uppercase; letter-spacing: 3px; margin-top: 5px; font-weight:600;">Aura Energy</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    col_photo, col_info = st.columns([1, 1.3])
    
    with col_photo:
        st.markdown('<div class="glowing-selfie-container">', unsafe_allow_html=True)
        if photo_url:
            # Load photo directly from backend static uploads folder
            img_src = f"{API_URL}{photo_url}"
            st.markdown(
                f"""
                <div class="glowing-selfie-frame" style="
                    background: linear-gradient(135deg, {aura_color}, {vibe.get('visual_color', '#00BCD4')});
                    box-shadow: 0 0 35px {aura_color}cc, 0 0 70px {aura_color}40;
                ">
                    <img src="{img_src}" class="selfie-image" />
                    <div class="selfie-badge" style="background:{aura_color};">{mbti_type}</div>
                </div>
                """,
                unsafe_allow_html=True
            )
        else:
            # Fallback to pure neon orb if camera was skipped
            st.markdown(
                f"""
                <div class="glowing-selfie-frame" style="
                    background: radial-gradient(circle, {aura_color}99, {aura_color}20, transparent);
                    box-shadow: 0 0 45px {aura_color}cc, 0 0 90px {aura_color}40;
                ">
                    <div style="font-size:3.5rem;">🔮</div>
                    <div class="selfie-badge" style="background:{aura_color};">{mbti_type}</div>
                </div>
                """,
                unsafe_allow_html=True
            )
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Display Photo vibe details
        st.markdown(
            f"""
            <div class="metric-card" style="margin-top:1.5rem; text-align:left;">
                <div class="metric-label" style="border-bottom:1px solid rgba(255,255,255,0.05); padding-bottom:5px;">📸 Visual Vibe Signature</div>
                <div style="margin-top:10px; font-size:0.9rem; line-height:1.6;">
                    • <b>Luminosity/Brightness</b>: {vibe.get('brightness', 50.0)}%<br/>
                    • <b>Tone Temperature</b>: {'Warm Sunset' if vibe.get('warmth', 0.0) > 0 else 'Cool Ocean'} ({vibe.get('warmth', 0.0):+})<br/>
                    • <b>Energy Complexity/Variance</b>: {vibe.get('complexity', 50.0)}%<br/>
                    • <b>Visual Vibe Aura</b>: <span style="color:{vibe.get('visual_color', aura_color)}; font-weight:600;">{vibe.get('visual_aura', 'Neutral')}</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with col_info:
        st.markdown(
            f"""
            <div style="padding:10px;">
                <h1 style="color:{aura_color}; margin-top:0; font-size:2.8rem; letter-spacing:1px;">{mbti_type}</h1>
                <h3 style="color:#fff; margin-top:-10px; letter-spacing:1px; opacity:0.85;">The {title}</h3>
                <div style="font-size:0.95rem; color:#888; text-transform:uppercase; letter-spacing:1px; margin-top:5px;">Energy Bracket: <span style="color:{aura_color}; font-weight:600;">{energy_level}</span></div>
                <p style="font-size:1.05rem; line-height:1.7; margin-top:15px; color:#e0e0e0;">{desc}</p>
            </div>
            """,
            unsafe_allow_html=True
        )
        
        # Dichotomies breakdown
        st.markdown("<h4 style='margin-top:1.5rem; padding-left:10px;'>📊 Personality Spectrum</h4>", unsafe_allow_html=True)
        render_mbti_dichotomy_bar("Extraversion (E)", dichotomies.get("E", 50), "Introversion (I)", dichotomies.get("I", 50), aura_color)
        render_mbti_dichotomy_bar("Sensing (S)", dichotomies.get("S", 50), "Intuition (N)", dichotomies.get("N", 50), aura_color)
        render_mbti_dichotomy_bar("Thinking (T)", dichotomies.get("T", 50), "Feeling (F)", dichotomies.get("F", 50), aura_color)
        render_mbti_dichotomy_bar("Judging (J)", dichotomies.get("J", 50), "Perceiving (P)", dichotomies.get("P", 50), aura_color)

    st.markdown("---")
    
    col_traits, col_stats = st.columns(2)
    with col_traits:
        if traits:
            st.markdown('<div class="section-header">🧬 Core MBTI Traits</div>', unsafe_allow_html=True)
            tags_html = "".join(f'<span class="trait-tag" style="background: {aura_color}20; border: 1px solid {aura_color}60;">{t}</span>' for t in traits)
            st.markdown(f'<div class="trait-tags-container">{tags_html}</div>', unsafe_allow_html=True)

    with col_stats:
        if famous:
            st.markdown('<div class="section-header">👥 Famous Alignments</div>', unsafe_allow_html=True)
            f_html = "".join(f'<span class="keyword-tag" style="border-color:{aura_color}40; color:#fff;">{p}</span>' for p in famous)
            st.markdown(f'<div class="trait-tags-container">{f_html}</div>', unsafe_allow_html=True)
            
        col_cs, _ = st.columns([1, 1])
        with col_cs:
            st.markdown(f"<div class='metric-card'><div class='metric-value' style='color:{aura_color};'>{conf_score}%</div><div class='metric-label'>Self-Confidence</div></div>", unsafe_allow_html=True)

    if careers or romantic:
        st.markdown("<br/>", unsafe_allow_html=True)
        col_c, col_r = st.columns(2)
        with col_c:
            if careers:
                c_html = "".join(f'<span class="keyword-tag" style="background:rgba(255,255,255,0.08); border:1px solid {aura_color}80; color:#fff;">{c}</span>' for c in careers)
                st.markdown(f"""
                <div style="background: linear-gradient(145deg, rgba(255,255,255,0.03), {aura_color}15); border: 1px solid {aura_color}50; border-radius: 16px; padding: 20px; height: 100%; box-shadow: 0 0 20px {aura_color}20; transition: transform 0.2s;">
                    <h3 style="color: {aura_color}; margin-top: 0; font-size: 1.4rem;">💼 Career Prospects</h3>
                    <div class="trait-tags-container" style="margin-top: 15px;">{c_html}</div>
                </div>
                """, unsafe_allow_html=True)
        
        with col_r:
            if romantic:
                r_html = "".join(f'<span class="keyword-tag" style="background:rgba(255,255,255,0.08); border:1px solid #ff475780; color:#fff;">{r}</span>' for r in romantic)
                st.markdown(f"""
                <div style="background: linear-gradient(145deg, rgba(255,255,255,0.03), #ff475715); border: 1px solid #ff475750; border-radius: 16px; padding: 20px; height: 100%; box-shadow: 0 0 20px #ff475720; transition: transform 0.2s;">
                    <h3 style="color: #ff4757; margin-top: 0; font-size: 1.4rem;">💕 Romantic Compatibility</h3>
                    <div class="trait-tags-container" style="margin-top: 15px;">{r_html}</div>
                </div>
                """, unsafe_allow_html=True)

    st.markdown("<br/>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if st.button("🔄 Retake MBTI Vibe Test", type="primary", use_container_width=True):
            st.session_state.mbti_step = 1
            st.session_state.mbti_answers = {}
            st.session_state.mbti_photo_bytes = None
            st.session_state.mbti_result = None
            st.rerun()



# ---------------------------------------------------------------------------
# Main Flow
# ---------------------------------------------------------------------------

def main() -> None:
    # 1. Load stylesheet
    load_css()
    
    # 2. Render sidebar mode selector
    mode = render_sidebar()
    
    if mode == "🔮 Text Sentiment Aura":
        # MODE 1
        render_header("AI-Powered Sentiment & verbal Aura Reader")
        if st.session_state.analyzing:
            render_text_analyzing_animation()
        else:
            render_text_input_section()
            if st.session_state.current_result:
                render_text_results(st.session_state.current_result)
    else:
        # MODE 2 (MBTI)
        render_header("20-Question MBTI & Camera Vibe Integrator")
        
        # Render wizard steps header
        render_mbti_stepper(st.session_state.mbti_step)
        
        if st.session_state.mbti_step == 1:
            render_mbti_questionnaire()
        elif st.session_state.mbti_step == 2:
            render_mbti_camera_capture()
        else:
            render_mbti_results_reveal()
if __name__ == "__main__":
    main()
