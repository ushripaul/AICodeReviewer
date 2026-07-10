import os
import streamlit as st
import google.generativeai as genai
import re
import requests
import random
import resend
import sqlite3
import json
from datetime import datetime
from typing import Optional, Tuple
from streamlit_ace import st_ace

# ── Database Setup ────────────────────────────────────────────────────────────
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "codeware.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT,
            language TEXT,
            code TEXT,
            review TEXT,
            score REAL,
            focus_areas TEXT,
            created_at TEXT
        )
    """)
    conn.commit()
    conn.close()

def save_review(email: str, language: str, code: str, review: str, score: float, focus_areas: list):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        INSERT INTO reviews (email, language, code, review, score, focus_areas, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (email, language, code, review, score, json.dumps(focus_areas), datetime.now().strftime("%Y-%m-%d %H:%M")))
    conn.commit()
    conn.close()

def get_reviews(email: str):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM reviews WHERE email=? ORDER BY created_at DESC", (email,))
    rows = c.fetchall()
    conn.close()
    return rows

init_db()

# ── Policy content ─────────────────────────────────────────────────────────
POLICY_CONTENT = {
    "privacy": ("Privacy Policy", """
**Last updated:** June 2026

**1. Information We Collect**
We collect your email address for sign-in, and the code you submit for review.

**2. How We Use It**
Your code is sent to Google's Gemini API to generate a review. We store your
review history (code, feedback, score) so you can revisit it from your account.

**3. Data Sharing**
We do not sell your data. Code submitted for review is processed by our AI
provider solely to generate your review.

**4. Your Rights**
You may request deletion of your account and review history at any time by
contacting support.

*This is placeholder text — replace with your actual policy, ideally reviewed
by legal counsel before going live.*
"""),
    "terms": ("Terms of Use", """
**Last updated:** June 2026

**1. Acceptance of Terms**
By using Codeware, you agree to these Terms of Use.

**2. Acceptable Use**
Do not submit malicious, illegal, or copyrighted code you don't have rights to.

**3. No Warranty**
AI-generated reviews are provided "as is" without guarantee of accuracy or
completeness. Always verify suggestions before applying them to production code.

**4. Termination**
We may suspend access for violations of these terms.

*This is placeholder text — replace with your actual terms, ideally reviewed
by legal counsel before going live.*
"""),
    "cookie": ("Cookie Policy", """
**Last updated:** June 2026

**1. What We Use**
Codeware uses Streamlit's session cookies to keep you signed in during your
session. We do not use third-party tracking or advertising cookies.

**2. Essential Cookies**
These are required for sign-in and cannot be disabled without breaking core
functionality.

**3. Managing Cookies**
You can clear cookies via your browser settings, which will sign you out.

*This is placeholder text — replace with your actual policy, ideally reviewed
by legal counsel before going live.*
"""),
}

def render_footer():
    """Footer with real <a> hyperlinks (white, bold, underlined) driven by query params."""
    st.markdown(f"""
<style>
.cw-footer-spacer {{ height: 56px; }}
.cw-footer-bar {{
    position: fixed; left: 0; bottom: 0; width: 100%;
    background: {FOOTER_BG};
    border-top: 1px solid {BORDER};
    padding: 14px 28px;
    z-index: 1000;
    display: flex; align-items: center; justify-content: center; gap: 28px;
    font-family: 'Inter', sans-serif;
}}
.cw-footer-copy {{
    color: #71717A; font-size: 0.8rem;
    margin-right: 12px;
}}
.cw-footer-bar a {{
    color: {FOOTER_LINK} !important;
    font-size: 0.85rem;
    font-weight: 700;
    text-decoration: underline;
    text-decoration-thickness: 1.5px;
}}
.cw-footer-bar a:hover {{ opacity: 0.8; }}
</style>
<div class="cw-footer-bar">
  <span class="cw-footer-copy">&copy; 2026 Codeware</span>
  <a href="?policy=privacy" target="_self">Privacy Policy</a>
  <a href="?policy=terms" target="_self">Terms of Use</a>
  <a href="?policy=cookie" target="_self">Cookie Policy</a>
</div>
<div class="cw-footer-spacer"></div>
""", unsafe_allow_html=True)

def render_policy_page():
    key = st.session_state.show_policy
    title, body = POLICY_CONTENT[key]
    if st.button("⬅ Back", key="policy_back_btn"):
        st.session_state.show_policy = None
        st.query_params.clear()
        st.rerun()
    st.markdown(f"## {title}")
    st.markdown(body)

def render_consent_line():
    """'By signing in, you agree to our Terms of Use and have read our Privacy Policy.'
    rendered as one real HTML paragraph with blue underlined <a> links — matches the mockup."""
    st.markdown(f"""
<style>
.cw-consent {{
    text-align: center;
    font-size: 0.82rem;
    color: {LABEL};
    margin-top: 0.6rem;
    line-height: 1.6;
}}
.cw-consent a {{
    color: #6e8bff !important;
    text-decoration: underline;
    font-weight: 500;
}}
.cw-consent a:hover {{ opacity: 0.8; }}
</style>
<div class="cw-consent">
  By signing in, you agree to our <a href="?policy=terms" target="_self">Terms of Use</a>
  and have read our <a href="?policy=privacy" target="_self">Privacy Policy</a>.
</div>
""", unsafe_allow_html=True)

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Codeware · AI Code Reviewer",
    page_icon="</>",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Theme (dark-only) ─────────────────────────────────────────────────────────
dark = True

BG     = "#09090B"
EDITOR = "#18181B"
PANEL  = "#121214"
FOOTER_BG   = "#18181B"
FOOTER_TEXT = "#A1A1AA"
FOOTER_LINK = "#FAFAFA"
BORDER = "#27272A"
TEXT   = "#FAFAFA"
LABEL  = "#A1A1AA"
ACCENT = "#8B5CF6"  # purple

AURORA = "linear-gradient(125deg, #0A1628, #0D2B1F, #0A2420, #0D1628, #1A2F2A, #0A1628)"


# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');

html, body, [class*="css"] {{
    font-family: 'Inter', sans-serif;
    color: {TEXT};
}}
html, body {{
    background: {AURORA} !important;
    background-size: 400% 400% !important;
    animation: auroraMove 10s ease infinite !important;
    margin: 0 !important;
}}
.stApp,
[data-testid="stAppViewContainer"],
[data-testid="stAppViewContainer"] > section,
section[data-testid="stMain"],
.main {{
    background: transparent !important;
}}
[data-testid="stHeader"] {{ background: transparent !important; }}
#root {{
    background: {AURORA} !important;
    background-size: 400% 400% !important;
    animation: auroraMove 10s ease infinite !important;
    min-height: 100vh;
}}
@keyframes auroraMove {{
    0% {{ background-position: 0% 50%; }}
    50% {{ background-position: 100% 50%; }}
    100% {{ background-position: 0% 50%; }}
}}
#root::after {{
    content: "";
    position: fixed; top: 0; left: 0; width: 100%; height: 100%;
    background: radial-gradient(ellipse at 30% 40%, rgba(32,178,140,0.25) 0%, transparent 55%),
                radial-gradient(ellipse at 70% 60%, rgba(0,128,128,0.2) 0%, transparent 50%),
                radial-gradient(ellipse at 50% 20%, rgba(16,100,120,0.2) 0%, transparent 45%),
                radial-gradient(ellipse at 20% 70%, rgba(0,80,100,0.15) 0%, transparent 40%);
    pointer-events: none; z-index: 0;
}}
#MainMenu, footer, header {{ visibility: hidden; }}
.block-container {{ padding: 2rem 2.5rem 3rem; max-width: 1200px; position: relative; z-index: 1; }}
[data-testid="stVerticalBlock"] > [data-testid="stVerticalBlockBorderWrapper"] > div {{
    background: {PANEL} !important;
    border: 1px solid {BORDER} !important;
    border-radius: 12px !important;
    padding: 1.4rem 1.6rem !important;
}}
.hero {{ display: flex; align-items: center; gap: 14px; margin-bottom: 0.25rem; }}
.hero-icon {{
    width: 44px; height: 44px;
    background: linear-gradient(135deg, #6D28D9, #FB7185) !important;
    border-radius: 12px;
    display: flex; align-items: center; justify-content: center;
    font-size: 14px; font-weight: 700;
    box-shadow: 0 0 24px #C026D344;
}}
.hero-title {{
    font-size: 1.75rem; font-weight: 700;
    background: linear-gradient(90deg, #6D28D9, #FB7185);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    letter-spacing: -0.5px;
}}
.hero-sub {{
    font-size: 0.82rem; color: {LABEL};
    margin-top: 2px; letter-spacing: 0.5px;
    font-family: 'JetBrains Mono', monospace;
}}
.divider {{ border: none; border-top: 1px solid {BORDER}; margin: 1.1rem 0 1.6rem; }}
.section-title {{
    font-size: 0.7rem; font-weight: 600;
    text-transform: uppercase; letter-spacing: 1.2px;
    color: {LABEL}; margin-bottom: 0.9rem;
}}
.stSelectbox > div > div {{
    background: {BG} !important;
    border: 1px solid {BORDER} !important;
    border-radius: 8px !important;
    color: {TEXT} !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.88rem !important;
}}
.stSelectbox > div > div:focus-within {{
    border-color: {ACCENT} !important;
    box-shadow: 0 0 0 3px {ACCENT}33 !important;
}}
.stSelectbox > div > div:hover {{ cursor: pointer; }}
.stSelectbox input {{ pointer-events: none !important; caret-color: transparent !important; }}
.stMultiSelect > div > div {{
    background: {BG} !important;
    border: 1px solid {BORDER} !important;
    border-radius: 8px !important;
    color: {TEXT} !important;
}}
.stMultiSelect > div > div > div {{
    background: {BG} !important;
    color: {TEXT} !important;
}}
.stMultiSelect label {{ color: {LABEL} !important; }}
[data-baseweb="select"] > div {{
    background: {BG} !important;
    border: 1px solid {BORDER} !important;
    color: {TEXT} !important;
}}
[data-baseweb="tag"] {{ background: {ACCENT} !important; color: #fff !important; }}
[data-baseweb="menu"] {{
    background: {PANEL} !important;
    border: 1px solid {BORDER} !important;
}}
[data-baseweb="menu"] li {{
    background: {PANEL} !important;
    color: {TEXT} !important;
}}
[data-baseweb="menu"] li:hover {{ background: {ACCENT}33 !important; }}
.stSelectbox svg, .stMultiSelect svg {{
    fill: {TEXT} !important;
    color: {TEXT} !important;
}}
div[data-testid="stTextInput"] input {{
    caret-color: {ACCENT};
    background: {BG} !important;
    color: {TEXT} !important;
    border: 1px solid {BORDER} !important;
    border-radius: 8px !important;
}}
div[data-testid="stTextInput"] input:focus {{
    border-color: {ACCENT} !important;
    box-shadow: 0 0 0 3px {ACCENT}26 !important;
    outline: none !important;
}}
[data-testid="InputInstructions"] {{ display: none !important; }}
div[data-testid="stTextInput"] label {{
    color: {LABEL} !important;
    font-size: 0.8rem !important;
    font-weight: 500 !important;
}}
[data-baseweb="select"] input {{ color: {TEXT} !important; }}
div[data-baseweb="select"] > div {{ background-color: {BG} !important; color: {TEXT} !important; }}
div[data-baseweb="select"] > div > div {{ color: {TEXT} !important; }}
div[data-baseweb="select"] > div > div > div {{ color: {TEXT} !important; }}
div[data-baseweb="select"] > div:first-child {{ background: {BG} !important; color: {TEXT} !important; }}
[data-baseweb="select"] > div > div[aria-label] {{ color: {TEXT} !important; }}
[class*="placeholder"] {{ color: {LABEL} !important; }}
div[data-baseweb="select"] span {{ color: {TEXT} !important; }}
/* Ace editor wrapper */
.ace-editor-wrapper {{
    border: 1px solid {BORDER};
    border-radius: 8px;
    overflow: hidden;
}}
.ace_editor {{
    border-radius: 8px !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 14px !important;
}}
.stButton > button {{
    width: 100%;
    background: linear-gradient(135deg, {ACCENT}, {ACCENT}cc) !important;
    color: #fff !important;
    border: none !important;
    border-radius: 9px !important;
    font-weight: 600 !important;
    font-size: 0.9rem !important;
    padding: 0.65rem 1.2rem !important;
    box-shadow: 0 4px 18px {ACCENT}55 !important;
}}
.stButton > button:hover {{ opacity: 0.88 !important; transform: translateY(-1px); }}
.stButton > button:active {{ transform: translateY(0px); }}
/* Fix spinner dot color to match accent */
.stSpinner > div {{ border-top-color: {ACCENT} !important; }}
[data-testid="stSpinner"] svg circle {{
    stroke: {ACCENT} !important;
}}
div[data-testid="stStatusWidget"] {{ color: {ACCENT} !important; }}
/* Override any teal/aqua spinner colors */
.stSpinner * {{ color: {ACCENT} !important; border-color: {ACCENT} transparent transparent transparent !important; }}
.score-wrap {{ display: flex; align-items: center; gap: 14px; margin: 0.5rem 0 1.2rem; }}
.score-number {{ font-family: 'JetBrains Mono', monospace; font-size: 2.6rem; font-weight: 600; line-height: 1; }}
.score-bar-bg {{ flex: 1; height: 8px; background: {BORDER}; border-radius: 99px; overflow: hidden; }}
.score-bar-fill {{ height: 100%; border-radius: 99px; }}
.badge {{
    display: inline-block; font-size: 0.67rem; font-weight: 700;
    text-transform: uppercase; letter-spacing: 1px;
    padding: 3px 10px; border-radius: 99px; margin-bottom: 0.55rem;
}}
.badge-red    {{ background: rgba(248,81,73,0.15);  color: #F85149; border: 1px solid rgba(248,81,73,0.3); }}
.badge-yellow {{ background: rgba(210,153,34,0.15); color: #E3B341; border: 1px solid rgba(210,153,34,0.3); }}
.badge-blue   {{ background: rgba(88,166,255,0.12); color: #58A6FF; border: 1px solid rgba(88,166,255,0.25); }}
.badge-green  {{ background: rgba(63,185,80,0.12);  color: #3FB950; border: 1px solid rgba(63,185,80,0.25); }}
.badge-purple {{ background: rgba(99,102,241,0.15); color: {ACCENT}; border: 1px solid rgba(99,102,241,0.3); }}
.result-section {{
    background: #1e1e2e !important;
    border: 1px solid {BORDER};
    border-radius: 10px;
    padding: 1rem 1.2rem;
    margin-bottom: 0.9rem;
    font-size: 0.88rem;
    line-height: 1.7;
    color: {TEXT} !important;
}}
.result-section * {{ color: {TEXT} !important; }}
.result-section ul {{ margin: 0.3rem 0 0 1rem; padding: 0; }}
.result-section li {{ margin-bottom: 0.35rem; color: {TEXT} !important; }}
.result-section p {{ color: {TEXT} !important; }}
.result-section code {{
    background: {PANEL};
    border: 1px solid {BORDER};
    border-radius: 4px;
    padding: 1px 6px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.82em;
    color: {ACCENT} !important;
}}
.stSelectbox label, .stTextArea label {{
    color: {LABEL} !important;
    font-size: 0.8rem !important;
    font-weight: 500 !important;
}}
div[data-testid="stNotification"] {{ white-space: nowrap !important; width: auto !important; }}
/* Expander fixes for both themes */
div[data-testid="stExpander"] {{
    background: #1a1a2e !important;
    border: 1px solid {BORDER} !important;
    border-radius: 10px !important;
    margin-bottom: 0.6rem !important;
}}
div[data-testid="stExpander"] summary {{
    background: #1a1a2e !important;
    color: {TEXT} !important;
    font-size: 0.88rem !important;
    font-weight: 500 !important;
    padding: 0.75rem 1rem !important;
    border-radius: 10px !important;
}}
div[data-testid="stExpander"] summary:hover {{
    color: {ACCENT} !important;
}}
div[data-testid="stExpander"] svg {{
    fill: {TEXT} !important;
}}
div[data-testid="stExpander"] > div[data-testid="stExpanderDetails"] {{
    background: #1e1e2e !important;
    color: {TEXT} !important;
    padding: 0.75rem 1rem 1rem !important;
    border-radius: 0 0 10px 10px !important;
}}
div[data-testid="stExpander"] > div[data-testid="stExpanderDetails"] p,
div[data-testid="stExpander"] > div[data-testid="stExpanderDetails"] li,
div[data-testid="stExpander"] > div[data-testid="stExpanderDetails"] span,
div[data-testid="stExpander"] > div[data-testid="stExpanderDetails"] div {{
    color: {TEXT} !important;
}}
h1, h2, h3, h4, h5, h6 {{
    color: {TEXT} !important;
}}
p, li, span, div {{
    color: {TEXT};
}}
strong {{
    color: {TEXT} !important;
}}
em {{
    color: {LABEL} !important;
}}
[data-testid="stMarkdownContainer"] {{
    color: {TEXT} !important;
}}
[data-testid="stMarkdownContainer"] * {{
    color: {TEXT} !important;
}}
[data-testid="stMarkdownContainer"] strong {{
    color: {TEXT} !important;
    font-weight: 700 !important;
}}
[data-testid="stMarkdownContainer"] em {{
    color: {LABEL} !important;
}}
h1 a, h2 a, h3 a {{
    display: none !important;
}}
[data-testid="stMarkdownContainer"] h1 a,
[data-testid="stMarkdownContainer"] h2 a,
[data-testid="stMarkdownContainer"] h3 a {{
    display: none !important;
}}
.header-anchor {{
    display: none !important;
}}
</style>
""", unsafe_allow_html=True)

# ── Header + top bar ─────────────────────────────────────────────────────────
st.markdown(f"""
<div class="hero">
  <div class="hero-icon" style="font-family:'JetBrains Mono',monospace;font-size:14px;font-weight:700;color:#fff;">&lt;/&gt;</div>
  <div>
    <div class="hero-title">Codeware</div>
    <div class="hero-sub">AI-powered code reviewer · Powered by Gemini 2.5 Flash</div>
  </div>
</div>
""", unsafe_allow_html=True)

# ── Auth state ────────────────────────────────────────────────────────────────
if "signed_in" not in st.session_state:
    st.session_state.signed_in = False
if "username" not in st.session_state:
    st.session_state.username = ""
if "otp" not in st.session_state:
    st.session_state.otp = None
if "otp_email" not in st.session_state:
    st.session_state.otp_email = ""
if "otp_sent" not in st.session_state:
    st.session_state.otp_sent = False
if "show_policy" not in st.session_state:
    st.session_state.show_policy = None

# Pick up ?policy=... from a clicked <a> link and route to the policy page
_qp_policy = st.query_params.get("policy")
if _qp_policy in POLICY_CONTENT:
    st.session_state.show_policy = _qp_policy

resend.api_key = st.secrets["resend.api_key"]
GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]

def send_otp(receiver_email: str, otp: int) -> bool:
    if not resend.api_key:
        st.error("Email service is not configured.")
        return False
    try:
        resend.Emails.send({
            "from": "onboarding@resend.dev",
            "to": receiver_email,
            "subject": "Codeware - Your OTP Code",
            "html": f"""
<div style="font-family:Inter,sans-serif;padding:2rem;max-width:400px;">
  <h2 style="color:#8B5CF6;">Codeware OTP</h2>
  <p>Your one-time password is:</p>
  <div style="font-size:2rem;font-weight:700;letter-spacing:8px;color:#8B5CF6;">{otp}</div>
  <p style="color:#888;font-size:0.85rem;">Valid for 10 minutes. Do not share it with anyone.</p>
</div>
"""
        })
        return True
    except Exception as e:
        st.error(f"Email Error: {str(e)}")
        return False

if st.session_state.show_policy:
    render_policy_page()
    render_footer()
    st.stop()

if not st.session_state.signed_in:
    col1, col2, col3 = st.columns([1.5, 2, 1.5])
    with col2:
        st.markdown(f"""
<div style="text-align:center;padding:2rem 0 1.5rem;">
  <div style="font-size:2rem;font-weight:700;color:{TEXT};">Welcome to Codeware</div>
  <div style="color:{LABEL};font-size:0.9rem;margin-top:0.5rem;">Sign in to start reviewing your code</div>
</div>
""", unsafe_allow_html=True)
        if not st.session_state.otp_sent:
            email = st.text_input("Email Address")
            if st.button("Send OTP", key="send_otp_btn"):
                if not email:
                    st.warning("Please enter your email.")
                elif "@" not in email:
                    st.warning("Please enter a valid email address.")
                else:
                    otp = random.randint(100000, 999999)
                    st.session_state.otp = otp
                    st.session_state.otp_email = email
                    if send_otp(email, otp):
                        st.session_state.otp_sent = True
                        st.rerun()
            render_consent_line()
        else:
            st.markdown(f"<div style='color:{LABEL};font-size:0.85rem;margin-bottom:0.5rem;'>OTP sent to <strong>{st.session_state.otp_email}</strong></div>", unsafe_allow_html=True)
            entered_otp = st.text_input("Enter OTP", max_chars=6)
            col_verify, col_resend = st.columns(2)
            with col_verify:
                if st.button("Verify & Sign In", key="verify_btn"):
                    if not entered_otp:
                        st.warning("Please enter the OTP.")
                    elif not entered_otp.isdigit():
                        st.error("❌ OTP must be a 6-digit number.")
                    elif int(entered_otp) == st.session_state.otp:
                        st.session_state.signed_in = True
                        st.session_state.username = st.session_state.otp_email
                        st.session_state.otp = None
                        st.session_state.otp_sent = False
                        st.rerun()
                    else:
                        st.error("❌ Incorrect OTP. Please try again.")
            with col_resend:
                if st.button("Resend OTP", key="resend_btn"):
                    otp = random.randint(100000, 999999)
                    st.session_state.otp = otp
                    if send_otp(st.session_state.otp_email, otp):
                        st.success("✅ OTP resent successfully.")
    render_footer()
    st.stop()

# ── Signed in header ──────────────────────────────────────────────────────────
if "show_account" not in st.session_state:
    st.session_state.show_account = False

initial = st.session_state.username[0].upper()

# Topbar: Gmail-toolbar-style flex row — align-items center on the row itself
st.markdown(f"""
<style>
div[data-testid="stHorizontalBlock"]:has(button[key="signout_btn_header"]) {{
    display: flex !important;
    align-items: center !important;
    gap: 0.5rem !important;
}}
div[data-testid="stHorizontalBlock"]:has(button[key="signout_btn_header"]) > div[data-testid="column"] {{
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    padding: 0 !important;
}}
div[data-testid="stHorizontalBlock"]:has(button[key="signout_btn_header"]) div.element-container {{
    margin: 0 !important;
}}
div[data-testid="stButton"]:has(button[key="signout_btn_header"]) button {{
    height: 36px !important;
    padding: 0 1.1rem !important;
    margin: 0 !important;
    box-sizing: border-box !important;
    font-size: 0.85rem !important;
    line-height: 36px !important;
    white-space: nowrap !important;
    min-width: 95px !important;
    width: auto !important;
}}
div[data-testid="stButton"]:has(button[key="avatar_btn"]) button {{
    width: 36px !important; height: 36px !important; min-width: 36px !important;
    border-radius: 50% !important; padding: 0 !important;
    margin: 0 !important;
    box-sizing: border-box !important;
    font-size: 0.85rem !important; font-weight: 700 !important;
    line-height: 36px !important;
    background: linear-gradient(135deg, {ACCENT}, {ACCENT}cc) !important;
    box-shadow: 0 0 12px {ACCENT}55 !important;
    border: none !important;
}}
</style>
""", unsafe_allow_html=True)

if st.session_state.show_account:
    # On the account page: show only Sign Out, hide avatar
    col_gap, col_signout = st.columns([9.4, 1.2], gap="small")
    col_avatar = None
else:
    col_gap, col_avatar, col_signout = st.columns([8.7, 0.6, 1.2], gap="small")

if col_avatar is not None:
    with col_avatar:
        st.markdown(f"""
<style>
div[data-testid="column"]:has(button[key="avatar_btn"]) {{
    position: relative !important;
}}
.cw-account-card {{
    visibility: hidden;
    opacity: 0;
    position: absolute;
    top: 44px;
    right: 0;
    min-width: 200px;
    background: #2d2d34;
    color: #fff;
    font-family: 'Inter', sans-serif;
    padding: 14px 16px;
    border-radius: 10px;
    box-shadow: 0 8px 24px rgba(0,0,0,0.35);
    transition: opacity 0.15s ease;
    z-index: 999;
    pointer-events: none;
    text-align: left;
}}
.cw-account-card .cw-account-name {{
    font-size: 0.85rem;
    font-weight: 600;
    margin-bottom: 3px;
    color: #fff;
}}
.cw-account-card .cw-account-email {{
    font-size: 0.8rem;
    color: #b8b8c0;
}}
div[data-testid="column"]:has(button[key="avatar_btn"]):hover .cw-account-card {{
    visibility: visible !important;
    opacity: 1 !important;
}}
</style>
<div class="cw-account-card">
  <div class="cw-account-name">{st.session_state.username.split('@')[0]}</div>
  <div class="cw-account-email">{st.session_state.username}</div>
</div>
""", unsafe_allow_html=True)
        if st.button(initial, key="avatar_btn"):
            st.session_state.show_account = not st.session_state.show_account
            st.rerun()

with col_signout:
    if st.button("Sign Out", key="signout_btn_header", use_container_width=True):
        st.session_state.signed_in = False
        st.session_state.otp_sent = False
        st.session_state.otp = None
        st.session_state.otp_email = ""
        st.rerun()

st.markdown('<hr class="divider"/>', unsafe_allow_html=True)

# ── Review Logic ──────────────────────────────────────────────────────────────
SECTION_CONFIG = {
    "bugs":           ("🐛 Bugs",           "badge-red",    "Bugs"),
    "performance":    ("🚀 Performance",    "badge-yellow", "Performance"),
    "best practices": ("🌟 Best Practices", "badge-blue",   "Best Practices"),
    "security":       ("🛡️ Security",       "badge-red",    "Security"),
    "code quality":   ("💎 Code Quality",   "badge-green",  "Code Quality"),
}

def extract_score(text: str) -> Optional[float]:
    if not text:
        return None
    patterns = [
        r'(?:score|rating)[^\d]*(\d+(?:\.\d+)?)\s*/\s*10',
        r'(\d+(?:\.\d+)?)\s*/\s*10',
        r'(\d+(?:\.\d+)?)\s*out\s*of\s*10',
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            val = float(m.group(1))
            if 0 <= val <= 10:
                return val
    return None

def score_color(score: float) -> Tuple[str, str]:
    if score >= 8:
        return "#3FB950", "Excellent"
    if score >= 6:
        return "#E3B341", "Good"
    if score >= 4:
        return "#F78166", "Fair"
    return "#F85149", "Needs Work"

def render_score(score: float) -> None:
    color, label = score_color(score)
    pct = score / 10 * 100
    st.markdown(f"""
<div class="score-wrap">
  <div class="score-number" style="color:{color}">{score:.1f}</div>
  <div style="flex:1">
    <div style="font-size:0.7rem;color:{LABEL};margin-bottom:6px;">
      QUALITY SCORE &nbsp;·&nbsp; <span style="color:{color}">{label}</span>
    </div>
    <div class="score-bar-bg">
      <div class="score-bar-fill"
           style="width:{pct}%;background:linear-gradient(90deg,{color}aa,{color});">
      </div>
    </div>
  </div>
  <div style="font-size:0.72rem;color:{LABEL};font-family:'JetBrains Mono',monospace;">/ 10</div>
</div>
""", unsafe_allow_html=True)

def render_result(response_text: str) -> None:
    if not response_text:
        st.error("Empty response received.")
        return
    score = extract_score(response_text)
    st.markdown('<p class="section-title">🎯 Review Results</p>', unsafe_allow_html=True)
    if score is not None:
        render_score(score)
    sections_found = False
    for _key, (icon_label, badge_class, search_term) in SECTION_CONFIG.items():
        pattern = (
            rf'(?:#{{1,3}}\s*)?(?:\d+\.\s*)?(?:\*{{1,2}})?'
            rf'{re.escape(search_term)}s?(?:\*{{1,2}})?[:\-\u2013]?\s*'
            rf'(.*?)(?=(?:#{{1,3}}|\d+\.\s|\Z))'
        )
        m = re.search(pattern, response_text, re.IGNORECASE | re.DOTALL)
        if m:
            content = (m.group(1) or "").strip()
            if content and len(content) > 10:
                sections_found = True
                st.markdown(f'<span class="badge {badge_class}">{icon_label}</span>', unsafe_allow_html=True)
                st.markdown(f'<div class="result-section">{content}</div>', unsafe_allow_html=True)
    if not sections_found:
        st.markdown(response_text)

# ── Account page ──────────────────────────────────────────────────────────────
if st.session_state.show_account:
    if st.button("⬅ Back", key="back_btn"):
        st.session_state.show_account = False
        st.rerun()
    reviews = get_reviews(st.session_state.username)
    if not reviews:
        st.info("No reviews yet. Paste some code and click Review Code!")
    else:
        for row in reviews:
            _, r_email, lang, code_snippet, review_text, r_score, focus_json, created_at = row
            focus_list = json.loads(focus_json)
            r_color, r_label = score_color(r_score)
            with st.expander(f"{created_at} · {lang}"):
                st.markdown(f"<div style='color:{LABEL};font-size:0.8rem;margin-bottom:0.5rem;'><b>Focus Areas:</b> {', '.join(focus_list)}</div>", unsafe_allow_html=True)
                st.code(code_snippet, language=lang.lower())
                render_result(review_text)
    render_footer()
    st.stop()

# ── API Setup ─────────────────────────────────────────────────────────────────
if not GEMINI_API_KEY:
    st.error("Gemini API key is not configured.")
    st.stop()

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.5-flash")

# ── Ace language + theme map ──────────────────────────────────────────────────
ACE_LANG_MAP = {
    "python":        "python",
    "html, css, js": "html",
    "java":          "java",
    "c++":           "c_cpp",
    "typescript":    "typescript",
    "go":            "golang",
    "rust":          "rust",
    "ruby":          "ruby",
    "kotlin":        "kotlin",
    "php":           "php",
    "bash":          "sh",
    "ocaml":         "ocaml",
    "vb":            "vbscript",
    "perl":          "perl",
    "swift":         "swift",
    "r":             "r",
    "haskell":       "haskell",
    "lua":           "lua",
    "dart":          "dart",
    "groovy":        "groovy",
    "sqlite":        "sql",
    "c":             "c_cpp",
    "pascal":        "pascal",
    "tcl":           "tcl",
    "prolog":        "prolog",
    "fortran":       "fortran",
    "zig":           "text",
    "cobol":         "cobol",
    "d":             "d",
    "ada":           "ada",
    "smalltalk":     "text",
}

# ── Layout ────────────────────────────────────────────────────────────────────
left_col, right_col = st.columns([1, 2.4], gap="large")

with left_col:
    with st.container(border=True):
        st.markdown('<p class="section-title">⚙ Review Settings</p>', unsafe_allow_html=True)
        language = st.selectbox(
            "Programming Language",
            ["Python", "HTML, CSS, JS", "Java", "C++", "TypeScript", "Go", "Rust", "Ruby",
             "Kotlin", "PHP", "Bash", "OCaml", "VB", "Perl", "Pascal", "Swift", "Prolog",
             "Ada", "D", "Cobol", "R", "Haskell", "Fortran", "Zig", "Lua", "Tcl", "Dart",
             "Smalltalk", "Groovy", "SQLite", "C"],
            label_visibility="visible"
        )
        focus = st.multiselect(
            "Focus Areas",
            ["Bugs", "Performance", "Security", "Best Practices", "Code Quality"],
            default=[],
        )

    with st.container(border=True):
        st.markdown('<p class="section-title">📋 Quick Guide</p>', unsafe_allow_html=True)
        st.markdown(f"""
<div style="font-size:0.8rem; color:{LABEL}; line-height:1.75;">
① Paste your code in the editor<br>
② Select language &amp; focus areas<br>
③ Hit Review Code<br>
④ Get instant AI feedback
</div>
""", unsafe_allow_html=True)

with right_col:
    with st.container(border=True):
        st.markdown('<p class="section-title">📝 Code Editor</p>', unsafe_allow_html=True)
        ace_mode  = ACE_LANG_MAP.get(language.lower(), "text")
        ace_theme = "tomorrow_night"
        st.markdown('<div class="ace-editor-wrapper">', unsafe_allow_html=True)
        code = st_ace(
            placeholder="# Paste your code here...",
            language=ace_mode,
            theme=ace_theme,
            font_size=14,
            tab_size=4,
            show_gutter=True,
            show_print_margin=False,
            wrap=False,
            auto_update=True,
            height=340,
            key=f"ace_{language}",
        ) or ""
        st.markdown('</div>', unsafe_allow_html=True)
    review_btn = st.button("🔍  Review Code", use_container_width=True, key="review_btn")

# ── Code Output ───────────────────────────────────────────────────────────────
if code.strip():
    with st.container(border=True):
        st.markdown('<p class="section-title">⚙ Code Output</p>', unsafe_allow_html=True)
        try:
            LANGUAGE_MAP = {
                "python":        ("python",      "3.10.0"),
                "javascript":    ("javascript",  "18.15.0"),
                "html, css, js": ("javascript",  "18.15.0"),
                "java":          ("java",        "15.0.2"),
                "c++":           ("c++",         "10.2.0"),
                "typescript":    ("typescript",  "5.0.3"),
                "go":            ("go",          "1.16.2"),
                "rust":          ("rust",        "1.50.0"),
                "ruby":          ("ruby",        "3.0.1"),
                "kotlin":        ("kotlin",      "1.8.20"),
                "php":           ("php",         "8.2.3"),
                "bash":          ("bash",        "5.2.0"),
                "r":             ("r",           "4.1.1"),
                "dart":          ("dart",        "2.19.6"),
                "swift":         ("swift",       "5.3.3"),
                "lua":           ("lua",         "5.4.4"),
                "perl":          ("perl",        "5.36.0"),
                "c":             ("c",           "10.2.0"),
                "haskell":       ("haskell",     "9.0.1"),
                "ocaml":         ("ocaml",       "4.12.0"),
                "groovy":        ("groovy",      "3.0.7"),
                "fortran":       ("fortran",     "10.2.0"),
                "zig":           ("zig",         "0.10.1"),
                "tcl":           ("tcl",         "8.6.11"),
                "prolog":        ("prolog",      "8.2.4"),
                "cobol":         ("cobol",       "3.1.2"),
                "d":             ("d",           "10.2.0"),
                "pascal":        ("pascal",      "3.2.0"),
                "vb":            ("vb",          "2.0.0"),
                "ada":           ("ada",         "10.2.0"),
                "sqlite":        ("sqlite",      "3.36.0"),
                "smalltalk":     ("smalltalk",   "gst"),
            }
            lang_info = LANGUAGE_MAP.get(language.lower())
            if lang_info is None:
                st.warning(f"⚠ Execution not supported for {language}.")
            else:
                lang_name, lang_version = lang_info
                piston_response = requests.post(
                    "https://emkc.org/api/v2/piston/execute",
                    json={"language": lang_name, "version": lang_version, "files": [{"content": code}]},
                    timeout=15
                )
                piston_response.raise_for_status()
                result = piston_response.json()
                run = result.get("run", {})
                output = run.get("stdout") or run.get("stderr") or "No output"
                st.code(output, language="text")
        except requests.exceptions.RequestException as ex:
            st.error(f"Execution Error: could not reach the code execution service ({str(ex)})")
        except Exception as ex:
            st.error(f"Execution Error: {str(ex)}")

# ── Trigger review ────────────────────────────────────────────────────────────
if review_btn:
    if not code.strip():
        st.warning("⚠ Please paste some code before reviewing.")
    else:
        focus_str = (
            ", ".join(focus) if focus
            else "Bugs, Performance, Security, Best Practices, Code Quality"
        )
        headers = "\n".join([f"### {f}" for f in focus]) if focus else (
            "### Bugs\n### Performance\n### Security\n### Best Practices\n### Code Quality"
        )
        prompt = (
            "You are a senior software engineer performing a thorough code review.\n\n"
            f"Review the following {language} code and provide structured feedback "
            f"covering: {focus_str}.\n\n"
            f"Format your response with clear sections using ONLY these exact headers:\n"
            f"{headers}\n\n"
            "End with a **Code Quality Score: X/10** line, where X is a number from 1-10.\n"
            "Be specific, actionable, and concise. Use bullet points within each section.\n\n"
            "Code to review:\n"
            "~~~" + language.lower() + "\n"
            + code + "\n~~~"
        )
        spinner_placeholder = st.empty()
        spinner_placeholder.markdown(f"""
<div style="display:flex;align-items:center;gap:12px;padding:1rem 0;">
  <style>
    @keyframes spin {{ to {{ transform: rotate(360deg); }} }}
    .cw-spinner {{
      width: 22px; height: 22px;
      border: 3px solid {ACCENT}33;
      border-top-color: {ACCENT};
      border-radius: 50%;
      animation: spin 0.75s linear infinite;
      flex-shrink: 0;
    }}
  </style>
  <div class="cw-spinner"></div>
  <span style="color:{LABEL};font-size:0.88rem;font-family:'JetBrains Mono',monospace;">Analyzing your code...</span>
</div>
""", unsafe_allow_html=True)
        try:
            gemini_response = model.generate_content(prompt)
            spinner_placeholder.empty()
            if gemini_response and gemini_response.text:
                with st.container(border=True):
                    render_result(gemini_response.text)
                r_score = extract_score(gemini_response.text) or 0.0
                save_review(
                    st.session_state.username,
                    language,
                    code,
                    gemini_response.text,
                    r_score,
                    focus
                )
            else:
                st.error("No response received from the API. Please try again.")
        except Exception as e:
            spinner_placeholder.empty()
            st.error(f"API Error: {str(e)}")

render_footer()