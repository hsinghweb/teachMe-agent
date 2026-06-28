# =============================================================================
# TeachMe Agent — Streamlit Frontend
# =============================================================================
# A beautiful, interactive web UI for the TeachMe teaching agent.
# Connects to the Google ADK agent backend and provides:
#   - Student profile sidebar with progress dashboard
#   - Chat interface for interacting with the teaching agent
#   - PDF upload widget for chapter grounding
#   - Visual progress tracking (accuracy, mastery levels)
#
# Run with: uv run streamlit run streamlit_app.py
# =============================================================================

import asyncio
import json
import os
import shutil
import sys
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Load environment variables from the teachme agent's .env file
# ---------------------------------------------------------------------------
ENV_PATH = Path(__file__).parent / "teachme" / ".env"
load_dotenv(ENV_PATH)

# ---------------------------------------------------------------------------
# Import ADK components for running the agent
# ---------------------------------------------------------------------------
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

# Import our agent
from teachme.agent import root_agent

# ---------------------------------------------------------------------------
# Data directories
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).parent
DATA_DIR = PROJECT_ROOT / "data"
UPLOADS_DIR = DATA_DIR / "uploads"
PROFILES_DIR = DATA_DIR / "profiles"
PROGRESS_DIR = DATA_DIR / "progress"

UPLOADS_DIR.mkdir(parents=True, exist_ok=True)


# =============================================================================
# Page Configuration
# =============================================================================
st.set_page_config(
    page_title="TeachMe — AI Teaching Assistant",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)

# =============================================================================
# Custom CSS for Premium Look & Feel
# =============================================================================
st.markdown("""
<style>
    /* ---------- Global Styles ---------- */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    .stApp {
        font-family: 'Inter', sans-serif;
    }

    /* ---------- Header ---------- */
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem 2rem;
        border-radius: 16px;
        margin-bottom: 1.5rem;
        color: white;
        text-align: center;
    }

    .main-header h1 {
        margin: 0;
        font-size: 2rem;
        font-weight: 700;
    }

    .main-header p {
        margin: 0.5rem 0 0 0;
        opacity: 0.9;
        font-size: 1rem;
    }

    /* ---------- Profile Card ---------- */
    .profile-card {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        padding: 1.2rem;
        border-radius: 12px;
        margin-bottom: 1rem;
    }

    .profile-card h3 {
        margin: 0 0 0.5rem 0;
        color: #2d3748;
        font-size: 1.1rem;
    }

    .profile-card .detail {
        font-size: 0.9rem;
        color: #4a5568;
        margin: 0.3rem 0;
    }

    /* ---------- Stats Card ---------- */
    .stats-card {
        background: linear-gradient(135deg, #e0c3fc 0%, #8ec5fc 100%);
        padding: 1rem;
        border-radius: 12px;
        text-align: center;
        margin-bottom: 0.5rem;
    }

    .stats-card .value {
        font-size: 1.8rem;
        font-weight: 700;
        color: #2d3748;
    }

    .stats-card .label {
        font-size: 0.8rem;
        color: #4a5568;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    /* ---------- Chat Messages ---------- */
    .chat-msg-user {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1rem 1.2rem;
        border-radius: 16px 16px 4px 16px;
        margin: 0.5rem 0;
        max-width: 80%;
        margin-left: auto;
    }

    .chat-msg-agent {
        background: #f7fafc;
        color: #2d3748;
        padding: 1rem 1.2rem;
        border-radius: 16px 16px 16px 4px;
        margin: 0.5rem 0;
        max-width: 80%;
        border: 1px solid #e2e8f0;
    }

    /* ---------- Upload Section ---------- */
    .upload-section {
        background: linear-gradient(135deg, #ffecd2 0%, #fcb69f 100%);
        padding: 1rem;
        border-radius: 12px;
        margin-bottom: 1rem;
    }

    /* ---------- Sidebar Styling ---------- */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #f8f9ff 0%, #eef1ff 100%);
    }

    /* ---------- Study Mode Badges ---------- */
    .mode-badge {
        display: inline-block;
        padding: 0.3rem 0.8rem;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 500;
        margin: 0.2rem;
    }

    .mode-normal { background: #c6f6d5; color: #22543d; }
    .mode-exam { background: #fed7d7; color: #742a2a; }
    .mode-revision { background: #fefcbf; color: #744210; }
    .mode-test { background: #bee3f8; color: #2a4365; }

    /* ---------- Mastery Levels ---------- */
    .mastery-beginner { color: #e53e3e; }
    .mastery-developing { color: #dd6b20; }
    .mastery-proficient { color: #38a169; }
    .mastery-mastered { color: #3182ce; }
</style>
""", unsafe_allow_html=True)


# =============================================================================
# Session State Initialization
# =============================================================================
if "messages" not in st.session_state:
    st.session_state.messages = []

if "student_id" not in st.session_state:
    st.session_state.student_id = ""

if "session_id" not in st.session_state:
    st.session_state.session_id = "teachme-session-001"

if "adk_session_service" not in st.session_state:
    st.session_state.adk_session_service = InMemorySessionService()

if "uploaded_pdf_name" not in st.session_state:
    st.session_state.uploaded_pdf_name = ""


# =============================================================================
# Helper Functions
# =============================================================================
def load_student_profile(student_id: str) -> dict | None:
    """Load a student profile from JSON file storage."""
    profile_path = PROFILES_DIR / f"{student_id}.json"
    if profile_path.exists():
        with open(profile_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def load_student_progress(student_id: str) -> dict | None:
    """Load a student's learning progress from JSON file storage."""
    progress_path = PROGRESS_DIR / f"{student_id}_progress.json"
    if progress_path.exists():
        with open(progress_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def get_mastery_color(level: str) -> str:
    """Get CSS class for mastery level display."""
    colors = {
        "beginner": "mastery-beginner",
        "developing": "mastery-developing",
        "proficient": "mastery-proficient",
        "mastered": "mastery-mastered",
    }
    return colors.get(level.lower(), "mastery-beginner")


async def run_agent(user_message: str) -> str:
    """
    Send a message to the TeachMe agent and get a response.
    Uses ADK Runner with InMemorySessionService for session management.
    """
    try:
        runner = Runner(
            agent=root_agent,
            app_name="teachme",
            session_service=st.session_state.adk_session_service,
        )

        # Create or get existing session
        session = await st.session_state.adk_session_service.get_session(
            app_name="teachme",
            user_id="streamlit_user",
            session_id=st.session_state.session_id,
        )

        if session is None:
            session = await st.session_state.adk_session_service.create_session(
                app_name="teachme",
                user_id="streamlit_user",
                session_id=st.session_state.session_id,
            )

        # Build user message content
        content = types.Content(
            role="user",
            parts=[types.Part(text=user_message)],
        )

        # Run the agent and collect response
        response_text = ""
        async for event in runner.run_async(
            user_id="streamlit_user",
            session_id=st.session_state.session_id,
            new_message=content,
        ):
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        response_text += part.text

        return response_text if response_text else "I'm thinking... Could you try again?"

    except Exception as e:
        return f"⚠️ Something went wrong: {str(e)}\n\nPlease make sure your GOOGLE_API_KEY is set correctly in `teachme/.env`"


# =============================================================================
# Sidebar — Profile & Progress Dashboard
# =============================================================================
with st.sidebar:
    # TeachMe Logo / Title
    st.markdown("## 📚 TeachMe")
    st.markdown("*Your AI Study Buddy*")
    st.divider()

    # Student ID Input
    st.markdown("### 🎓 Student Profile")
    student_id_input = st.text_input(
        "Enter your Student ID",
        value=st.session_state.student_id,
        placeholder="e.g., a1b2c3d4",
        help="Enter your student ID to load your profile. New student? Just start chatting!",
    )

    if student_id_input != st.session_state.student_id:
        st.session_state.student_id = student_id_input

    # Display profile if available
    if st.session_state.student_id:
        profile = load_student_profile(st.session_state.student_id)
        if profile:
            st.markdown(f"""
            <div class="profile-card">
                <h3>👤 {profile.get('name', 'Student')}</h3>
                <div class="detail">🎂 Age: {profile.get('age', 'N/A')}</div>
                <div class="detail">📖 Class: {profile.get('student_class', 'N/A')}</div>
                <div class="detail">🏫 Board: {profile.get('board', 'N/A')}</div>
                <div class="detail">🗣️ Medium: {profile.get('medium', 'N/A')}</div>
            </div>
            """, unsafe_allow_html=True)

            # Stats
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"""
                <div class="stats-card">
                    <div class="value">{profile.get('total_sessions', 0)}</div>
                    <div class="label">Sessions</div>
                </div>
                """, unsafe_allow_html=True)
            with col2:
                st.markdown(f"""
                <div class="stats-card">
                    <div class="value">{profile.get('overall_accuracy', 0):.0f}%</div>
                    <div class="label">Accuracy</div>
                </div>
                """, unsafe_allow_html=True)

            # Progress per chapter
            progress = load_student_progress(st.session_state.student_id)
            if progress and progress.get("chapters"):
                st.markdown("### 📊 Chapter Progress")
                for key, chapter in progress["chapters"].items():
                    mastery = chapter.get("current_mastery", "beginner")
                    accuracy = chapter.get("best_accuracy", 0)
                    st.markdown(f"**{chapter.get('chapter_name', key)}**")
                    st.progress(accuracy / 100)
                    st.caption(f"Mastery: {mastery.title()} | Best: {accuracy:.0f}%")
        else:
            st.info("No profile found. Start chatting to create one!")

    st.divider()

    # PDF Upload Section
    st.markdown("### 📄 Upload Chapter PDF")
    uploaded_file = st.file_uploader(
        "Choose a textbook chapter PDF",
        type=["pdf"],
        help="Upload your NCERT or textbook chapter PDF to study",
    )

    if uploaded_file is not None:
        # Save the uploaded PDF to the uploads directory
        save_path = UPLOADS_DIR / uploaded_file.name
        with open(save_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        st.session_state.uploaded_pdf_name = uploaded_file.name
        st.success(f"✅ Uploaded: {uploaded_file.name}")

    if st.session_state.uploaded_pdf_name:
        st.caption(f"📎 Current PDF: {st.session_state.uploaded_pdf_name}")

    st.divider()

    # Quick Actions
    st.markdown("### ⚡ Quick Actions")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📋 New Plan", use_container_width=True):
            st.session_state.messages.append(
                {"role": "user", "content": "I want to create a study plan for my uploaded chapter."}
            )
            st.rerun()
    with col2:
        if st.button("✅ Take Quiz", use_container_width=True):
            st.session_state.messages.append(
                {"role": "user", "content": "I'm ready for a quiz on what I've studied."}
            )
            st.rerun()


# =============================================================================
# Main Content Area — Chat Interface
# =============================================================================

# Header
st.markdown("""
<div class="main-header">
    <h1>📚 TeachMe — Your AI Study Buddy</h1>
    <p>Upload a chapter PDF, get a personalized study plan, learn with explanations, and test your knowledge!</p>
</div>
""", unsafe_allow_html=True)

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"], avatar="🧑‍🎓" if message["role"] == "user" else "📚"):
        st.markdown(message["content"])

# Chat input
if prompt := st.chat_input("Ask me anything about your studies... 💬"):
    # If a PDF was uploaded, include that context in the first relevant message
    if st.session_state.uploaded_pdf_name and "pdf" not in prompt.lower() and "plan" in prompt.lower():
        prompt = f"{prompt}\n\n[Note: The student has uploaded a PDF file: '{st.session_state.uploaded_pdf_name}' which is saved at 'data/uploads/{st.session_state.uploaded_pdf_name}']"

    # Add user message to chat
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar="🧑‍🎓"):
        st.markdown(prompt)

    # Get agent response
    with st.chat_message("assistant", avatar="📚"):
        with st.spinner("TeachMe is thinking... 🤔"):
            response = asyncio.run(run_agent(prompt))
        st.markdown(response)

    # Add assistant message to chat
    st.session_state.messages.append({"role": "assistant", "content": response})

    # Refresh sidebar (profile may have been created/updated)
    st.rerun()

# Welcome message for empty chat
if not st.session_state.messages:
    with st.chat_message("assistant", avatar="📚"):
        st.markdown("""
        **Welcome to TeachMe!** 📚✨

        I'm your AI study buddy, designed to help you study your textbook chapters effectively.

        **Here's how I can help:**

        1. **📋 Create your profile** — Tell me your name, class, and board so I can personalize your learning.
        2. **📄 Upload a chapter PDF** — Use the sidebar to upload your textbook chapter.
        3. **📝 Get a study plan** — I'll create a personalized plan based on your study mode and time.
        4. **📖 Learn topics** — I'll teach you each topic with simple explanations.
        5. **✅ Take quizzes** — Test your understanding and track your progress!

        **Let's get started! What's your name?** 🎓
        """)
