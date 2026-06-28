// =============================================================================
// TeachMe Agent — Frontend JavaScript
// =============================================================================
// Handles:
//   - Chat messaging (send/receive with the ADK api_server)
//   - Student profile form submission
//   - PDF file upload
//   - Study mode selection
//   - UI state management (sidebar toggle, typing indicators, etc.)
//
// Backend: Connects to ADK api_server at http://localhost:8000
//          Endpoints used:
//            POST /run      — Send a message to the agent
//            POST /upload   — Upload PDF files (custom endpoint)
//
// Note: For the capstone POC, this frontend is designed to work with
//       `uv run adk api_server teachme` running locally.
// =============================================================================

// ---------------------------------------------------------------------------
// Configuration
// ---------------------------------------------------------------------------
const API_BASE_URL = "http://localhost:8000";
const APP_NAME = "teachme";
const USER_ID = "web_user";
let SESSION_ID = `session-${Date.now()}`;
let currentStudyMode = "normal";
let uploadedPdfName = "";
let studentProfile = null;

// ---------------------------------------------------------------------------
// DOM Elements
// ---------------------------------------------------------------------------
const chatMessages = document.getElementById("chat-messages");
const chatInput = document.getElementById("chat-input");
const sendBtn = document.getElementById("send-btn");
const profileForm = document.getElementById("profile-form");
const onboardingSection = document.getElementById("onboarding-section");
const profileDisplay = document.getElementById("profile-display");
const pdfUpload = document.getElementById("pdf-upload");
const uploadedFileEl = document.getElementById("uploaded-file");
const uploadedFileName = document.getElementById("uploaded-file-name");
const statusDot = document.getElementById("status-dot");
const statusText = document.getElementById("status-text");

// ---------------------------------------------------------------------------
// Initialize — Check for existing profile in localStorage
// ---------------------------------------------------------------------------
document.addEventListener("DOMContentLoaded", () => {
    const savedProfile = localStorage.getItem("teachme_profile");
    if (savedProfile) {
        studentProfile = JSON.parse(savedProfile);
        showProfileDisplay(studentProfile);
    }

    // Auto-resize textarea as user types
    chatInput.addEventListener("input", autoResizeTextarea);
});

// ---------------------------------------------------------------------------
// Chat — Send Message
// ---------------------------------------------------------------------------
async function sendMessage() {
    const message = chatInput.value.trim();
    if (!message) return;

    // Add context about uploaded PDF if relevant
    let fullMessage = message;
    if (uploadedPdfName && (message.toLowerCase().includes("plan") || message.toLowerCase().includes("study"))) {
        fullMessage += `\n\n[Note: The student has uploaded a PDF file: '${uploadedPdfName}' saved at 'data/uploads/${uploadedPdfName}']`;
    }

    // Add student profile context if available
    if (studentProfile) {
        fullMessage += `\n\n[Student Profile: Name=${studentProfile.name}, Class=${studentProfile.student_class}, Board=${studentProfile.board}, Medium=${studentProfile.medium}, Student ID=${studentProfile.student_id || 'pending'}]`;
    }

    // Clear input and display user message
    chatInput.value = "";
    chatInput.style.height = "auto";
    appendMessage("user", message);

    // Show typing indicator
    showTypingIndicator();
    setStatus("thinking", "Thinking...");

    try {
        // Send to ADK api_server
        const response = await fetch(`${API_BASE_URL}/run`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                app_name: APP_NAME,
                user_id: USER_ID,
                session_id: SESSION_ID,
                new_message: {
                    role: "user",
                    parts: [{ text: fullMessage }],
                },
            }),
        });

        removeTypingIndicator();

        if (response.ok) {
            const data = await response.json();
            // Extract agent response text from the ADK response format
            let agentText = extractAgentResponse(data);
            appendMessage("agent", agentText);
            setStatus("ready", "Ready");
        } else {
            appendMessage("agent", `⚠️ Server returned error (${response.status}). Make sure the ADK api_server is running:\n\`uv run adk api_server teachme\``);
            setStatus("error", "Error");
        }
    } catch (error) {
        removeTypingIndicator();
        // If the API server isn't running, show a helpful message
        appendMessage("agent",
            `⚠️ Could not connect to the TeachMe agent server.\n\n` +
            `**To start the server, run:**\n` +
            `\`\`\`\nuv run adk api_server teachme\n\`\`\`\n\n` +
            `Then refresh this page. The agent will respond to your messages!`
        );
        setStatus("offline", "Offline");
    }
}

/**
 * Extract the agent's text response from the ADK api_server response format.
 * The response structure may vary, so we handle multiple formats.
 */
function extractAgentResponse(data) {
    // Try different response formats
    if (typeof data === "string") return data;

    // ADK api_server typically returns events or a response object
    if (data.response) return data.response;
    if (data.text) return data.text;

    // Handle array of events
    if (Array.isArray(data)) {
        const texts = data
            .filter(event => event.content && event.content.parts)
            .flatMap(event => event.content.parts)
            .filter(part => part.text)
            .map(part => part.text);
        return texts.join("") || "I received your message but couldn't generate a response. Please try again.";
    }

    // Handle nested content
    if (data.content && data.content.parts) {
        return data.content.parts.map(p => p.text || "").join("");
    }

    return JSON.stringify(data, null, 2);
}

// ---------------------------------------------------------------------------
// Chat — Append Message to UI
// ---------------------------------------------------------------------------
function appendMessage(role, text) {
    const messageDiv = document.createElement("div");
    messageDiv.className = `message ${role === "user" ? "user-message" : "agent-message"}`;

    const avatar = role === "user" ? "🧑‍🎓" : "📚";

    // Convert markdown-like formatting to HTML (basic)
    const formattedText = formatMessageText(text);

    messageDiv.innerHTML = `
        <div class="message-avatar">${avatar}</div>
        <div class="message-content">
            <div class="message-text">${formattedText}</div>
        </div>
    `;

    chatMessages.appendChild(messageDiv);
    scrollToBottom();
}

/**
 * Basic markdown-to-HTML converter for chat messages.
 * Handles bold, italic, code blocks, lists, and line breaks.
 */
function formatMessageText(text) {
    if (!text) return "";

    return text
        // Code blocks (```)
        .replace(/```(\w*)\n([\s\S]*?)```/g, '<pre><code>$2</code></pre>')
        // Inline code (`)
        .replace(/`([^`]+)`/g, '<code>$1</code>')
        // Bold (**)
        .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
        // Italic (*)
        .replace(/\*([^*]+)\*/g, '<em>$1</em>')
        // Ordered lists
        .replace(/^\d+\.\s+(.+)$/gm, '<li>$1</li>')
        // Unordered lists
        .replace(/^[-•]\s+(.+)$/gm, '<li>$1</li>')
        // Line breaks
        .replace(/\n/g, '<br>');
}

// ---------------------------------------------------------------------------
// Chat — Typing Indicator
// ---------------------------------------------------------------------------
function showTypingIndicator() {
    const indicator = document.createElement("div");
    indicator.className = "message agent-message";
    indicator.id = "typing-indicator";
    indicator.innerHTML = `
        <div class="message-avatar">📚</div>
        <div class="message-content">
            <div class="typing-indicator">
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
            </div>
        </div>
    `;
    chatMessages.appendChild(indicator);
    scrollToBottom();
}

function removeTypingIndicator() {
    const indicator = document.getElementById("typing-indicator");
    if (indicator) indicator.remove();
}

// ---------------------------------------------------------------------------
// Chat — Status Indicator
// ---------------------------------------------------------------------------
function setStatus(state, text) {
    statusText.textContent = text;
    statusDot.style.background =
        state === "ready" ? "var(--success)" :
        state === "thinking" ? "var(--warning)" :
        state === "error" ? "var(--error)" :
        "var(--neutral-400)";

    // Animate the dot when thinking
    statusDot.style.animation = state === "thinking" ? "pulse 1s infinite" : "pulse 2s infinite";
}

// ---------------------------------------------------------------------------
// Chat — Input Handling
// ---------------------------------------------------------------------------
function handleKeyDown(event) {
    if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        sendMessage();
    }
}

function autoResizeTextarea() {
    chatInput.style.height = "auto";
    chatInput.style.height = Math.min(chatInput.scrollHeight, 120) + "px";
}

function scrollToBottom() {
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// ---------------------------------------------------------------------------
// Quick Actions — Send predefined messages
// ---------------------------------------------------------------------------
function sendQuickAction(message) {
    chatInput.value = message;
    sendMessage();
}

// ---------------------------------------------------------------------------
// Study Mode — Toggle active mode
// ---------------------------------------------------------------------------
function setStudyMode(mode, btn) {
    currentStudyMode = mode;
    // Update active button
    document.querySelectorAll(".mode-btn").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
}

// ---------------------------------------------------------------------------
// Profile Form — Create student profile
// ---------------------------------------------------------------------------
profileForm.addEventListener("submit", async (e) => {
    e.preventDefault();

    const profile = {
        name: document.getElementById("student-name").value,
        age: parseInt(document.getElementById("student-age").value),
        student_class: document.getElementById("student-class").value,
        board: document.getElementById("student-board").value,
        medium: document.getElementById("student-medium").value,
        student_id: `stu-${Date.now().toString(36)}`,
    };

    studentProfile = profile;
    localStorage.setItem("teachme_profile", JSON.stringify(profile));
    showProfileDisplay(profile);

    // Send onboarding message to agent
    chatInput.value = `Hi! I'm ${profile.name}. I'm ${profile.age} years old, studying in Class ${profile.student_class} under ${profile.board} board with ${profile.medium} medium. Please create my profile.`;
    sendMessage();
});

/**
 * Show the profile display card and hide the onboarding form.
 */
function showProfileDisplay(profile) {
    onboardingSection.classList.add("hidden");
    profileDisplay.classList.remove("hidden");

    document.getElementById("display-name").textContent = `👤 ${profile.name}`;
    document.getElementById("display-class").textContent = `Class ${profile.student_class}`;
    document.getElementById("display-board").textContent = profile.board;
    document.getElementById("display-medium").textContent = profile.medium;
}

// ---------------------------------------------------------------------------
// PDF Upload — Handle file selection
// ---------------------------------------------------------------------------
pdfUpload.addEventListener("change", (e) => {
    const file = e.target.files[0];
    if (!file) return;

    uploadedPdfName = file.name;
    uploadedFileEl.classList.remove("hidden");
    uploadedFileName.textContent = file.name;

    // Notify in chat
    appendMessage("agent", `✅ PDF uploaded: **${file.name}**\n\nI've noted your chapter file. When you're ready, click "📋 New Plan" or tell me you'd like to study this chapter!`);

    // Note: In a full implementation, we would upload the file to the server.
    // For the POC, the student can also manually place PDFs in data/uploads/
});

// ---------------------------------------------------------------------------
// Sidebar — Toggle (mobile responsive)
// ---------------------------------------------------------------------------
function toggleSidebar() {
    const sidebar = document.getElementById("sidebar");
    sidebar.classList.toggle("open");
}
