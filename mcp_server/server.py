# =============================================================================
# TeachMe Agent — MCP Server
# =============================================================================
# A FastMCP server that exposes tools for the TeachMe teaching agent system.
#
# Tools provided:
#   1. parse_pdf       — Extract text content from uploaded PDF chapter files
#   2. save_profile    — Create or update a student's profile (JSON storage)
#   3. get_profile     — Retrieve a student's profile by student_id
#   4. save_progress   — Record a student's learning progress for a chapter
#   5. get_progress    — Retrieve a student's learning progress history
#   6. save_study_plan — Persist a generated study plan for a chapter
#   7. get_study_plan  — Retrieve a saved study plan
#
# Storage: All data is stored as flat JSON files under the `data/` directory.
# This keeps the project lightweight (no database needed for the POC).
#
# Usage:
#   Run standalone:  uv run python -m mcp_server.server
#   Used by ADK:     Connected via StdioServerParameters in the agent config
# =============================================================================

import json
import os
import uuid
from datetime import datetime
from pathlib import Path

import pymupdf  # PyMuPDF for PDF text extraction
from fastmcp import FastMCP

# ---------------------------------------------------------------------------
# Configuration — resolve data directory paths relative to project root
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
PROFILES_DIR = DATA_DIR / "profiles"
PROGRESS_DIR = DATA_DIR / "progress"
PLANS_DIR = DATA_DIR / "plans"
UPLOADS_DIR = DATA_DIR / "uploads"

# Ensure all data directories exist at startup
for directory in [PROFILES_DIR, PROGRESS_DIR, PLANS_DIR, UPLOADS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Initialize FastMCP server
# ---------------------------------------------------------------------------
mcp = FastMCP(
    name="TeachMe-MCP-Server",
    instructions=(
        "MCP server for the TeachMe teaching agent. "
        "Provides tools for PDF parsing, student profile management, "
        "and learning progress tracking."
    ),
)


# =============================================================================
# Tool 1: PDF Parsing
# =============================================================================
@mcp.tool()
def parse_pdf(file_path: str) -> str:
    """
    Extract all text content from a PDF file.

    This tool reads a PDF file (typically a textbook chapter) and returns
    its full text content. The extracted text is used by the teaching agent
    to ground its responses in the actual curriculum material.

    Args:
        file_path: Absolute or relative path to the PDF file to parse.

    Returns:
        The extracted text content from all pages of the PDF.
        Returns an error message string if parsing fails.
    """
    try:
        # Resolve path — support both absolute and relative (to uploads dir)
        pdf_path = Path(file_path)
        if not pdf_path.is_absolute():
            pdf_path = UPLOADS_DIR / pdf_path

        if not pdf_path.exists():
            return f"Error: PDF file not found at '{pdf_path}'"

        if not pdf_path.suffix.lower() == ".pdf":
            return f"Error: File '{pdf_path.name}' is not a PDF file"

        # Extract text from all pages using PyMuPDF
        doc = pymupdf.open(str(pdf_path))
        text_parts = []
        for page_num, page in enumerate(doc, start=1):
            page_text = page.get_text()
            if page_text.strip():
                text_parts.append(f"--- Page {page_num} ---\n{page_text}")
        doc.close()

        if not text_parts:
            return "Warning: PDF was parsed successfully but no text was found. The PDF might contain only images."

        full_text = "\n\n".join(text_parts)
        return full_text

    except Exception as e:
        return f"Error parsing PDF: {str(e)}"


# =============================================================================
# Tool 2 & 3: Student Profile Management
# =============================================================================
@mcp.tool()
def save_profile(
    name: str,
    age: int,
    student_class: str,
    board: str,
    medium: str,
    student_id: str = "",
) -> str:
    """
    Create or update a student profile.

    Saves the student's basic information to a JSON file. If student_id is
    provided, updates the existing profile. Otherwise, creates a new one
    with a generated ID.

    Args:
        name: Student's full name.
        age: Student's age in years.
        student_class: Student's class/grade (e.g., "6", "7", "8", "10").
        board: Education board (e.g., "CBSE", "ICSE", "State Board").
        medium: Language medium (e.g., "English", "Hindi", "Marathi").
        student_id: Optional. Existing student ID to update. Leave empty for new profile.

    Returns:
        JSON string with the saved profile data including the student_id.
    """
    try:
        # Generate or use provided student ID
        if not student_id:
            student_id = str(uuid.uuid4())[:8]

        profile = {
            "student_id": student_id,
            "name": name,
            "age": age,
            "student_class": student_class,
            "board": board,
            "medium": medium,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            # Dynamic fields — populated as student uses the platform
            "chapters_studied": [],
            "overall_accuracy": 0.0,
            "total_sessions": 0,
        }

        # If updating, preserve dynamic fields from existing profile
        profile_path = PROFILES_DIR / f"{student_id}.json"
        if profile_path.exists():
            with open(profile_path, "r", encoding="utf-8") as f:
                existing = json.load(f)
            # Preserve learning history, update basic info
            profile["created_at"] = existing.get("created_at", profile["created_at"])
            profile["chapters_studied"] = existing.get("chapters_studied", [])
            profile["overall_accuracy"] = existing.get("overall_accuracy", 0.0)
            profile["total_sessions"] = existing.get("total_sessions", 0)

        # Save to JSON file
        with open(profile_path, "w", encoding="utf-8") as f:
            json.dump(profile, f, indent=2, ensure_ascii=False)

        return json.dumps(profile, indent=2, ensure_ascii=False)

    except Exception as e:
        return f"Error saving profile: {str(e)}"


@mcp.tool()
def get_profile(student_id: str) -> str:
    """
    Retrieve a student's profile by their student ID.

    Args:
        student_id: The unique identifier of the student.

    Returns:
        JSON string with the student's profile data.
        Returns an error message if the profile is not found.
    """
    try:
        profile_path = PROFILES_DIR / f"{student_id}.json"
        if not profile_path.exists():
            return f"Error: No profile found for student_id '{student_id}'"

        with open(profile_path, "r", encoding="utf-8") as f:
            profile = json.load(f)

        return json.dumps(profile, indent=2, ensure_ascii=False)

    except Exception as e:
        return f"Error reading profile: {str(e)}"


# =============================================================================
# Tool 4 & 5: Learning Progress Tracking
# =============================================================================
@mcp.tool()
def save_progress(
    student_id: str,
    chapter_name: str,
    subject: str,
    tasks_completed: int,
    total_tasks: int,
    accuracy: float,
    mastery_level: str,
    topics_covered: str,
    weak_areas: str,
) -> str:
    """
    Save or update a student's learning progress for a specific chapter.

    This tool records how well the student performed during a study session,
    including their accuracy on quiz questions and their mastery level.

    Args:
        student_id: The student's unique identifier.
        chapter_name: Name of the chapter studied (e.g., "Light - Reflection and Refraction").
        subject: Subject name (e.g., "Science", "Mathematics").
        tasks_completed: Number of study tasks completed in this session.
        total_tasks: Total number of tasks in the study plan.
        accuracy: Percentage of quiz questions answered correctly (0-100).
        mastery_level: Current mastery level — one of "beginner", "developing", "proficient", "mastered".
        topics_covered: Comma-separated list of topics covered in this session.
        weak_areas: Comma-separated list of topics where the student struggled.

    Returns:
        JSON string with the saved progress data.
    """
    try:
        progress_file = PROGRESS_DIR / f"{student_id}_progress.json"

        # Load existing progress or create new
        if progress_file.exists():
            with open(progress_file, "r", encoding="utf-8") as f:
                all_progress = json.load(f)
        else:
            all_progress = {"student_id": student_id, "chapters": {}}

        # Create a unique key for this chapter
        chapter_key = f"{subject}_{chapter_name}".replace(" ", "_").lower()

        # Build progress entry for this session
        session_entry = {
            "timestamp": datetime.now().isoformat(),
            "tasks_completed": tasks_completed,
            "total_tasks": total_tasks,
            "accuracy": accuracy,
            "mastery_level": mastery_level,
            "topics_covered": [t.strip() for t in topics_covered.split(",") if t.strip()],
            "weak_areas": [w.strip() for w in weak_areas.split(",") if w.strip()],
        }

        # Append to chapter history (or create new chapter entry)
        if chapter_key not in all_progress["chapters"]:
            all_progress["chapters"][chapter_key] = {
                "chapter_name": chapter_name,
                "subject": subject,
                "sessions": [],
                "best_accuracy": 0.0,
                "current_mastery": "beginner",
            }

        chapter_data = all_progress["chapters"][chapter_key]
        chapter_data["sessions"].append(session_entry)
        chapter_data["best_accuracy"] = max(chapter_data["best_accuracy"], accuracy)
        chapter_data["current_mastery"] = mastery_level

        # Save updated progress
        with open(progress_file, "w", encoding="utf-8") as f:
            json.dump(all_progress, f, indent=2, ensure_ascii=False)

        # Also update the student's profile with this chapter
        _update_profile_with_progress(student_id, chapter_key, accuracy)

        return json.dumps(session_entry, indent=2, ensure_ascii=False)

    except Exception as e:
        return f"Error saving progress: {str(e)}"


@mcp.tool()
def get_progress(student_id: str, subject: str = "", chapter_name: str = "") -> str:
    """
    Retrieve a student's learning progress.

    Can retrieve all progress, progress for a specific subject, or progress
    for a specific chapter.

    Args:
        student_id: The student's unique identifier.
        subject: Optional. Filter by subject name (e.g., "Science").
        chapter_name: Optional. Filter by specific chapter name.

    Returns:
        JSON string with the student's progress data.
    """
    try:
        progress_file = PROGRESS_DIR / f"{student_id}_progress.json"
        if not progress_file.exists():
            return json.dumps(
                {"student_id": student_id, "chapters": {}, "message": "No progress recorded yet."},
                indent=2,
            )

        with open(progress_file, "r", encoding="utf-8") as f:
            all_progress = json.load(f)

        # Filter by subject and/or chapter if specified
        if subject or chapter_name:
            filtered_chapters = {}
            for key, data in all_progress.get("chapters", {}).items():
                if subject and data.get("subject", "").lower() != subject.lower():
                    continue
                if chapter_name and data.get("chapter_name", "").lower() != chapter_name.lower():
                    continue
                filtered_chapters[key] = data
            all_progress["chapters"] = filtered_chapters

        return json.dumps(all_progress, indent=2, ensure_ascii=False)

    except Exception as e:
        return f"Error reading progress: {str(e)}"


# =============================================================================
# Tool 6 & 7: Study Plan Management
# =============================================================================
@mcp.tool()
def save_study_plan(
    student_id: str,
    chapter_name: str,
    subject: str,
    study_mode: str,
    time_available: str,
    plan_content: str,
) -> str:
    """
    Save a generated study plan for a student and chapter.

    Args:
        student_id: The student's unique identifier.
        chapter_name: Name of the chapter.
        subject: Subject name.
        study_mode: Study mode — "normal", "exam_prep", "quick_revision", "class_test".
        time_available: Time available for study (e.g., "2 hours", "1 day").
        plan_content: The full study plan content as a formatted string (includes tasks, topics, schedule).

    Returns:
        JSON string confirming the saved plan with its plan_id.
    """
    try:
        plan_id = str(uuid.uuid4())[:8]
        plan = {
            "plan_id": plan_id,
            "student_id": student_id,
            "chapter_name": chapter_name,
            "subject": subject,
            "study_mode": study_mode,
            "time_available": time_available,
            "plan_content": plan_content,
            "created_at": datetime.now().isoformat(),
            "status": "active",
        }

        plan_path = PLANS_DIR / f"{student_id}_{plan_id}.json"
        with open(plan_path, "w", encoding="utf-8") as f:
            json.dump(plan, f, indent=2, ensure_ascii=False)

        return json.dumps(plan, indent=2, ensure_ascii=False)

    except Exception as e:
        return f"Error saving study plan: {str(e)}"


@mcp.tool()
def get_study_plan(student_id: str, plan_id: str = "") -> str:
    """
    Retrieve study plans for a student.

    If plan_id is provided, returns that specific plan.
    Otherwise, returns the most recent plan for the student.

    Args:
        student_id: The student's unique identifier.
        plan_id: Optional. Specific plan ID to retrieve.

    Returns:
        JSON string with the study plan data.
    """
    try:
        if plan_id:
            plan_path = PLANS_DIR / f"{student_id}_{plan_id}.json"
            if not plan_path.exists():
                return f"Error: Plan '{plan_id}' not found for student '{student_id}'"
            with open(plan_path, "r", encoding="utf-8") as f:
                return json.dumps(json.load(f), indent=2, ensure_ascii=False)

        # Find the most recent plan for this student
        plan_files = sorted(
            PLANS_DIR.glob(f"{student_id}_*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )

        if not plan_files:
            return json.dumps(
                {"student_id": student_id, "message": "No study plans found."},
                indent=2,
            )

        with open(plan_files[0], "r", encoding="utf-8") as f:
            return json.dumps(json.load(f), indent=2, ensure_ascii=False)

    except Exception as e:
        return f"Error reading study plan: {str(e)}"


# =============================================================================
# Internal helper — update profile with progress data (not exposed as tool)
# =============================================================================
def _update_profile_with_progress(student_id: str, chapter_key: str, accuracy: float) -> None:
    """
    Internal helper to update a student's profile with their latest progress.
    This enriches the 'long-term memory' of the student profile.
    """
    profile_path = PROFILES_DIR / f"{student_id}.json"
    if not profile_path.exists():
        return

    with open(profile_path, "r", encoding="utf-8") as f:
        profile = json.load(f)

    # Add chapter to studied list if not already there
    if chapter_key not in profile.get("chapters_studied", []):
        profile.setdefault("chapters_studied", []).append(chapter_key)

    # Update session count
    profile["total_sessions"] = profile.get("total_sessions", 0) + 1

    # Recalculate overall accuracy (running average)
    sessions = profile["total_sessions"]
    prev_avg = profile.get("overall_accuracy", 0.0)
    profile["overall_accuracy"] = round(((prev_avg * (sessions - 1)) + accuracy) / sessions, 2)

    profile["updated_at"] = datetime.now().isoformat()

    with open(profile_path, "w", encoding="utf-8") as f:
        json.dump(profile, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    import sys
    print("🚀 Starting TeachMe MCP Server...", file=sys.stderr)
    print(f"📁 Data directory: {DATA_DIR}", file=sys.stderr)
    print("Tools available: parse_pdf, save_profile, get_profile, save_progress, get_progress, save_study_plan, get_study_plan", file=sys.stderr)
    mcp.run(transport="stdio")
