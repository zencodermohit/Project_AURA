import os
import streamlit as st
import requests

st.set_page_config(
    page_title="Admin Exclusive | Project AURA",
    page_icon="🔒",
    layout="wide",
)

# Backend URL config
API_URL = os.environ.get("API_URL", "http://localhost:8000").rstrip("/")

def load_css():
    st.markdown("""
        <style>
        .stApp { background-color: #0a0a0f; color: #e0e0e0; }
        .admin-header { color: #9B59B6; font-size: 2.5rem; text-align: center; margin-bottom: 20px; }
        .stat-card { background: rgba(255,255,255,0.05); padding: 20px; border-radius: 12px; text-align: center; margin-bottom: 20px; border: 1px solid rgba(255,255,255,0.1); }
        .stat-card h1 { color: #1ABC9C; margin: 0; font-size: 3rem; }
        .stat-card p { margin: 0; color: #aaa; text-transform: uppercase; font-size: 0.9rem; letter-spacing: 1px; }
        .entry-card { background: rgba(255,255,255,0.03); border-radius: 12px; padding: 20px; margin-bottom: 20px; border-left: 4px solid #9B59B6; }
        .badge { background: #9B59B630; padding: 4px 10px; border-radius: 20px; font-size: 0.8rem; border: 1px solid #9B59B680; color: #fff; }
        .answer-box { background: rgba(0,0,0,0.3); padding: 10px; border-radius: 8px; font-size: 0.85rem; color: #bbb; height: 150px; overflow-y: auto; }
        </style>
    """, unsafe_allow_html=True)

def login():
    st.markdown('<h1 class="admin-header">🔒 Exclusive Admin Access</h1>', unsafe_allow_html=True)
    st.markdown("<p style='text-align:center;'>Enter your secret token to view the private database.</p>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        token = st.text_input("Admin Token", type="password")
        if st.button("Unlock Database", use_container_width=True):
            if token:
                st.session_state["admin_token"] = token
                st.rerun()

def fetch_data(token):
    try:
        response = requests.get(f"{API_URL}/results", params={"admin_token": token})
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 401:
            st.error("❌ Invalid Admin Token.")
            st.session_state.pop("admin_token", None)
            return None
        else:
            st.error(f"❌ Backend Error: {response.status_code}")
            return None
    except Exception as e:
        st.error(f"🔌 Unable to reach the backend API: {e}")
        return None

def render_dashboard(data):
    st.markdown('<h1 class="admin-header">👑 Exclusive Admin Database</h1>', unsafe_allow_html=True)
    
    mbti_entries = [e for e in data if "mbti_type" in e]
    text_entries = [e for e in data if "mbti_type" not in e]
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f'<div class="stat-card"><h1>{len(data)}</h1><p>Total Entries</p></div>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div class="stat-card"><h1>{len(mbti_entries)}</h1><p>MBTI / Selfies</p></div>', unsafe_allow_html=True)
    with col3:
        st.markdown(f'<div class="stat-card"><h1>{len(text_entries)}</h1><p>Text Readings</p></div>', unsafe_allow_html=True)

    st.markdown("### 📸 MBTI & Selfie Submissions")
    if not mbti_entries:
        st.info("No MBTI entries yet.")
        
    for entry in mbti_entries:
        mcode = entry.get("mbti_type", "Unknown")
        color = entry.get("aura_color", "#9B59B6")
        ts = entry.get("timestamp", "")[:19].replace("T", " ")
        photo = entry.get("photo_url")
        answers = entry.get("raw_answers", {})
        
        with st.container():
            st.markdown(f'<div class="entry-card" style="border-left-color: {color};">', unsafe_allow_html=True)
            col_img, col_data, col_ans = st.columns([1, 1.5, 2])
            
            with col_img:
                if photo:
                    st.image(f"{API_URL}{photo}", use_container_width=True)
                else:
                    st.markdown(f'<div style="width:100%; height:150px; background:{color}30; display:flex; align-items:center; justify-content:center; border-radius:8px;">No Selfie</div>', unsafe_allow_html=True)
            
            with col_data:
                st.markdown(f'<h3 style="color:{color}; margin-top:0;">{mcode}</h3>', unsafe_allow_html=True)
                st.markdown(f'<span class="badge" style="background:{color}30; border-color:{color};">{entry.get("title", "")}</span>', unsafe_allow_html=True)
                st.markdown(f"<p style='margin-top:10px; font-size:0.9rem;'><b>Time:</b> {ts}</p>", unsafe_allow_html=True)
                st.markdown(f"<p style='font-size:0.9rem;'><b>Energy:</b> {entry.get('energy_score', 0)} / 100</p>", unsafe_allow_html=True)
                
            with col_ans:
                st.markdown("<b>Raw Answers:</b>", unsafe_allow_html=True)
                ans_text = "<br>".join([f"<b>{k}:</b> {v}" for k, v in answers.items()])
                if not ans_text:
                    ans_text = "<i>No raw answers stored for this entry.</i>"
                st.markdown(f'<div class="answer-box">{ans_text}</div>', unsafe_allow_html=True)
                
            st.markdown('</div>', unsafe_allow_html=True)

def main():
    load_css()
    token = st.session_state.get("admin_token")
    
    if not token:
        login()
    else:
        if st.sidebar.button("🔒 Logout"):
            st.session_state.pop("admin_token", None)
            st.rerun()
            
        data = fetch_data(token)
        if data is not None:
            render_dashboard(data)

if __name__ == "__main__":
    main()
