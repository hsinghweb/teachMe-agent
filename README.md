# 📚 TeachMe Agent — AI Teaching Assistant

> An AI-powered multi-agent teaching system that helps Indian school students (Class 6-12) study textbook chapters effectively — built with Google ADK, MCP, and Gemini.

[![Built with Google ADK](https://img.shields.io/badge/Built%20with-Google%20ADK-4285F4?style=for-the-badge&logo=google&logoColor=white)](https://google.github.io/adk-docs/)
[![MCP Protocol](https://img.shields.io/badge/MCP-Protocol-8B5CF6?style=for-the-badge)](https://modelcontextprotocol.io/)
[![Python 3.13](https://img.shields.io/badge/Python-3.13-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Kaggle Capstone](https://img.shields.io/badge/Kaggle-Capstone-20BEFF?style=for-the-badge&logo=kaggle&logoColor=white)](https://www.kaggle.com/)

---

## 🎯 Problem Statement

Students in Class 6-12 across India increasingly use AI tools like ChatGPT and Gemini for homework help. However, their usage is **passive and unguided**:

- ❌ They don't set proper context (class, board, syllabus)
- ❌ They get generic answers not aligned with their curriculum
- ❌ There's no structured learning flow — just Q&A
- ❌ No progress tracking or mastery assessment
- ❌ Young students (age 10-15) can't prompt AI effectively

## 💡 Solution: TeachMe Agent

TeachMe flips the dynamic — **the AI agent drives the learning**, not the student.

Inspired by how coding agents (Cursor, Devin) work, TeachMe:
1. **Understands context** — Student profile with class, board, medium
2. **Grounds content** — Uses actual textbook PDFs (NCERT/ICSE)
3. **Plans proactively** — Creates structured study plans with tasks
4. **Teaches progressively** — Explains topics from simple → detailed
5. **Evaluates understanding** — Tests with quizzes and tracks mastery
6. **Loops for improvement** — Re-teaches weak areas until mastery

```
📋 Onboard → 📄 Upload PDF → 📝 Plan → 📖 Teach → ✅ Test → 📊 Track → 🔄 Loop
```

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────┐
│                  FRONTENDS (3 options)               │
│  ┌──────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │ ADK Web  │  │  Streamlit   │  │  HTML/CSS/JS  │  │
│  │  UI      │  │  App         │  │  (standalone)  │  │
│  └────┬─────┘  └──────┬───────┘  └──────┬────────┘  │
└───────┼───────────────┼────────────────┼────────────┘
        └───────────────┼───────────────┘
                        ▼
┌─────────────────────────────────────────────────────┐
│           GOOGLE ADK — Multi-Agent System            │
│                                                      │
│  ┌─────────────────────────────────────────────┐    │
│  │        root_agent (Router/Orchestrator)       │    │
│  └─────┬──────┬──────┬──────┬──────────────────┘    │
│        │      │      │      │                        │
│   ┌────▼──┐ ┌─▼───┐ ┌▼────┐ ┌▼──────────┐          │
│   │Profile│ │Plan │ │Teach│ │ Evaluate  │           │
│   │Agent  │ │Agent│ │Agent│ │ Agent     │           │
│   └───────┘ └─────┘ └─────┘ └──────────┘           │
│                                                      │
└──────────────────────┬──────────────────────────────┘
                       │ (MCP Protocol — stdio)
                       ▼
┌─────────────────────────────────────────────────────┐
│              MCP SERVER (FastMCP)                     │
│  Tools: parse_pdf, save_profile, get_profile,        │
│         save_progress, get_progress,                 │
│         save_study_plan, get_study_plan              │
└──────────────────────┬──────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────┐
│              JSON FILE STORAGE                       │
│  data/profiles/   data/progress/   data/plans/       │
└─────────────────────────────────────────────────────┘
```

### Agent Design (Coding Agent Pattern → Teaching Agent)

| Coding Agent | TeachMe Agent | Agent Name |
|---|---|---|
| Understand codebase | Understand student + chapter | `profile_agent` |
| Create task plan | Create study plan | `planner_agent` |
| Write code | Teach content | `teacher_agent` |
| Run tests (CI/CD) | Quiz & evaluate | `evaluator_agent` |
| Track progress | Track mastery | MCP `track_progress` |
| Loop if failing | Re-teach weak areas | `root_agent` |

---

## 🛠️ Tech Stack

| Technology | Purpose |
|---|---|
| **Google ADK** | Multi-agent orchestration framework |
| **Gemini 2.5 Flash** | LLM for agent reasoning |
| **FastMCP** | MCP server for tool exposure |
| **PyMuPDF** | PDF text extraction |
| **Streamlit** | Rich web frontend |
| **HTML/CSS/JS** | Standalone web frontend |
| **UV** | Python dependency management |
| **Python 3.13** | Runtime |

### Course Concepts Demonstrated

| Concept | Where | Details |
|---|---|---|
| ✅ **ADK Multi-Agent** | Code | 4 specialized agents + router |
| ✅ **MCP Server** | Code | 7 tools via FastMCP |
| ✅ **Antigravity IDE** | Video | Built using Antigravity |
| ✅ **Security** | Code | .env for keys, .gitignore, no hardcoded secrets |
| ✅ **Agent Skills** | Code | TeachMe as agent skill |
| ✅ **Deployability** | Video/Docs | UV project, reproducible setup |

---

## 🚀 Setup & Installation

### Prerequisites
- **Python 3.13.2** installed
- **UV** package manager ([install guide](https://docs.astral.sh/uv/getting-started/installation/))
- **Google Gemini API Key** ([get one here](https://aistudio.google.com/apikey))

### Step 1: Clone the Repository
```bash
git clone https://github.com/hsinghweb/teachMe-agent.git
cd teachMe-agent
```

### Step 2: Install Dependencies
```bash
uv sync
```

### Step 3: Configure API Key
```bash
# Copy the example env file
cp .env.example teachme/.env

# Edit teachme/.env and add your Gemini API key
# GOOGLE_API_KEY=your_actual_key_here
```

> ⚠️ **Never commit your `.env` file!** It's already in `.gitignore`.

### Step 4: Run the Agent

**Option A: ADK Web UI (Built-in)**
```bash
uv run adk web teachme
```
Then open `http://localhost:8000` in your browser.

**Option B: Streamlit Frontend**
```bash
uv run streamlit run streamlit_app.py
```
Then open `http://localhost:8501` in your browser.

**Option C: HTML/CSS/JS Frontend**
```bash
# Start the API server
uv run adk api_server teachme

# Open web/index.html in your browser
```

**Option D: CLI Mode**
```bash
uv run adk run teachme
```

---

## 📖 Usage Guide

### 1. Create Your Profile
Tell TeachMe your name, age, class, board, and medium. This creates a persistent profile that personalizes all interactions.

### 2. Upload a Chapter PDF
Upload your NCERT or textbook chapter PDF. The agent extracts the text and uses it to ground all responses.

### 3. Get a Study Plan
Tell the agent your study mode (normal/exam prep/revision) and available time. It creates a structured plan with tasks.

### 4. Learn Topics
The agent teaches each topic using progressive disclosure — starting simple, then going deeper. Content is grounded in your actual textbook.

### 5. Take a Quiz
After studying, the agent generates quiz questions (MCQ, True/False, short answer) and evaluates your answers.

### 6. Track Progress
Your accuracy, mastery level, and study history are saved and used to personalize future sessions.

---

## 📁 Project Structure

```
teachMe-agent/
├── teachme/                    # ADK Agent Package
│   ├── __init__.py             # Package init
│   ├── agent.py                # Multi-agent definitions (root + 4 sub-agents)
│   └── .env                    # API keys (gitignored)
│
├── mcp_server/                 # MCP Server Package
│   ├── __init__.py             # Package init
│   └── server.py               # FastMCP server with 7 tools
│
├── web/                        # HTML/CSS/JS Frontend
│   ├── index.html              # Chat interface
│   ├── style.css               # Premium styles
│   └── app.js                  # Frontend logic
│
├── data/                       # JSON File Storage
│   ├── profiles/               # Student profiles
│   ├── progress/               # Learning progress
│   ├── plans/                  # Study plans
│   └── uploads/                # Uploaded PDFs (gitignored)
│
├── streamlit_app.py            # Streamlit frontend
├── pyproject.toml              # UV project config & dependencies
├── .python-version             # Python version pin (3.13.2)
├── .env.example                # Environment variable template
├── .gitignore                  # Git ignore rules
├── LICENSE                     # MIT License
└── README.md                   # This file
```

---

## 🎓 Capstone Project Details

- **Track**: Agents for Good — Advancing Education
- **Course**: Kaggle 5-Day AI Agents: Intensive Vibe Coding Course with Google
- **Author**: Himanshu Singh
- **Timeline**: June 19, 2026 — July 6, 2026

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
