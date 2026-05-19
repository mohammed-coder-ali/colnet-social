import os
import re
import json
import sqlite3
import asyncio
import logging
from datetime import datetime
from typing import Optional, List
from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
import uvicorn
import httpx

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("vibe-coder")

# -----------------------------------------------------------------------------
# DATABASE SETUP
# -----------------------------------------------------------------------------
DB_FILE = "vibe_projects.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            prompt TEXT,
            code TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

init_db()

# -----------------------------------------------------------------------------
# SCHEMAS
# -----------------------------------------------------------------------------
class ProjectCreate(BaseModel):
    title: str

class ProjectUpdate(BaseModel):
    title: Optional[str] = None
    prompt: Optional[str] = None
    code: Optional[str] = None

class GenerationRequest(BaseModel):
    prompt: str
    apiKey: Optional[str] = ""

# -----------------------------------------------------------------------------
# FASTAPI INSTANCE
# -----------------------------------------------------------------------------
app = FastAPI(title="Vibe Coding Platform")

# -----------------------------------------------------------------------------
# REUSABLE GEMINI CLIENT WITH EXPONENTIAL BACKOFF
# -----------------------------------------------------------------------------
async def call_gemini_api(prompt: str, user_api_key: Optional[str] = None) -> str:
    # Use user provided key or fallback to environment variable
    api_key = user_api_key or os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        raise HTTPException(
            status_code=400, 
            detail="Gemini API Key is missing. Please provide it in the UI settings or set GEMINI_API_KEY environment variable."
        )

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-09-2025:generateContent?key={api_key}"
    
    system_instruction = (
        "You are an expert web development AI. Generate a fully responsive, visually beautiful, "
        "and complete single-file web application using standard HTML, inline CSS (or Tailwind CDN), "
        "and clean JavaScript. Do not write any markdown wrappers, explanations, introduction, or "
        "conclusions. You MUST return only the clean, executable code starting with <!DOCTYPE html> "
        "and ending with </html>."
    )

    payload = {
        "contents": [{
            "parts": [{"text": prompt}]
        }],
        "systemInstruction": {
            "parts": [{"text": system_instruction}]
        }
    }

    headers = {"Content-Type": "application/json"}
    
    # Exponential Backoff Parameters: 1s, 2s, 4s, 8s, 16s
    retries = 5
    delay = 1.0

    async with httpx.AsyncClient(timeout=45.0) as client:
        for attempt in range(retries):
            try:
                response = await client.post(url, json=payload, headers=headers)
                
                if response.status_code == 200:
                    data = response.json()
                    # Safe extraction path
                    raw_text = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                    
                    if not raw_text:
                        raise ValueError("Received empty content block from Gemini API.")
                        
                    # Clean markdown wrappers if returned despite system prompt
                    cleaned_code = re.sub(r"^```html\s*", "", raw_text, flags=re.IGNORECASE)
                    cleaned_code = re.sub(r"^```xml\s*", "", cleaned_code, flags=re.IGNORECASE)
                    cleaned_code = re.sub(r"^```\s*", "", cleaned_code, flags=re.IGNORECASE)
                    cleaned_code = re.sub(r"```$", "", cleaned_code)
                    return cleaned_code.strip()
                
                elif response.status_code in [429, 500, 502, 503, 504]:
                    # Retryable errors
                    logger.warning(f"Attempt {attempt + 1} failed with status {response.status_code}. Retrying in {delay}s...")
                else:
                    # Non-retryable error
                    error_msg = response.text
                    try:
                        error_json = response.json()
                        error_msg = error_json.get("error", {}).get("message", error_msg)
                    except:
                        pass
                    raise HTTPException(status_code=response.status_code, detail=f"Gemini API Error: {error_msg}")
                    
            except httpx.RequestError as exc:
                logger.warning(f"Attempt {attempt + 1} failed with request error: {exc}. Retrying...")
            
            await asyncio.sleep(delay)
            delay *= 2.0

        raise HTTPException(
            status_code=504, 
            detail="The Gemini API failed to respond after multiple connection attempts. Please check your network and API key."
        )

# -----------------------------------------------------------------------------
# ENDPOINTS
# -----------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def read_root():
    return HTML_TEMPLATE

# GET ALL PROJECTS
@app.get("/api/projects")
async def get_projects():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, prompt, updated_at FROM projects ORDER BY updated_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

# CREATE PROJECT
@app.post("/api/projects")
async def create_project(payload: ProjectCreate):
    import uuid
    project_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    default_code = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <script src="https://cdn.tailwindcss.com"></script>
    <title>Hello Vibe</title>
</head>
<body class="bg-zinc-50 flex items-center justify-center min-h-screen">
    <div class="text-center p-8 bg-white rounded-xl shadow-sm border border-zinc-200 max-w-md">
        <h1 class="text-2xl font-semibold text-zinc-950 mb-2">My New Web Project</h1>
        <p class="text-zinc-500 mb-6">Generated automatically by the Vibe Coding Engine. Start describing your changes!</p>
        <button onclick="changeBackground()" class="px-5 py-2.5 bg-zinc-900 text-white rounded-lg hover:bg-zinc-800 transition-colors font-medium">
            Interact With Me
        </button>
    </div>
    <script>
        function changeBackground() {
            const colors = ['#fafafa', '#f4f4f5', '#e4e4e7', '#d4d4d8', '#ccfbf1', '#fef9c3', '#fee2e2'];
            const randomColor = colors[Math.floor(Math.random() * colors.length)];
            document.body.style.backgroundColor = randomColor;
        }
    </script>
</body>
</html>"""

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO projects (id, title, prompt, code, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
        (project_id, payload.title, "Initial Setup", default_code, now, now)
    )
    conn.commit()
    conn.close()

    return {"id": project_id, "title": payload.title, "code": default_code}

# GET SINGLE PROJECT
@app.get("/api/projects/{project_id}")
async def get_project(project_id: str):
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Project not found")
    return dict(row)

# UPDATE PROJECT
@app.put("/api/projects/{project_id}")
async def update_project(project_id: str, payload: ProjectUpdate):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Build dynamic update query
    updates = []
    params = []
    
    if payload.title is not None:
        updates.append("title = ?")
        params.append(payload.title)
    if payload.prompt is not None:
        updates.append("prompt = ?")
        params.append(payload.prompt)
    if payload.code is not None:
        updates.append("code = ?")
        params.append(payload.code)
        
    if not updates:
        conn.close()
        return {"status": "no updates provided"}
        
    now = datetime.utcnow().isoformat()
    updates.append("updated_at = ?")
    params.append(now)
    
    params.append(project_id)
    query = f"UPDATE projects SET {', '.join(updates)} WHERE id = ?"
    
    cursor.execute(query, tuple(params))
    conn.commit()
    conn.close()
    return {"status": "success", "updated_at": now}

# DELETE PROJECT
@app.delete("/api/projects/{project_id}")
async def delete_project(project_id: str):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM projects WHERE id = ?", (project_id,))
    conn.commit()
    conn.close()
    return {"status": "success"}

# GENERATE WITH GEMINI
@app.post("/api/generate")
async def generate_code(request: GenerationRequest):
    if not request.prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt cannot be empty.")
    
    code = await call_gemini_api(request.prompt, request.apiKey)
    return {"code": code}

# -----------------------------------------------------------------------------
# HIGH FIDELITY FRONTEND - EMBEDDED JINJA/HTML
# -----------------------------------------------------------------------------
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Vibe Code Platform</title>
    <!-- Tailwind CSS -->
    <script src="https://cdn.tailwindcss.com"></script>
    <!-- Lucide Icons -->
    <script src="https://unpkg.com/lucide@latest"></script>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;500;600&family=Plus+Jakarta+Sans:wght@300;400;500;600;700&display=swap');
        body {
            font-family: 'Plus Jakarta Sans', sans-serif;
        }
        .code-font {
            font-family: 'JetBrains Mono', monospace;
        }
        /* Custom scrollbars to match modern design */
        ::-webkit-scrollbar {
            width: 6px;
            height: 6px;
        }
        ::-webkit-scrollbar-track {
            background: #f4f4f5;
        }
        ::-webkit-scrollbar-thumb {
            background: #d4d4d8;
            border-radius: 4px;
        }
        ::-webkit-scrollbar-thumb:hover {
            background: #a1a1aa;
        }
    </style>
</head>
<body class="bg-zinc-50 text-zinc-900 min-h-screen flex flex-col antialiased">

    <!-- Top Navigation Bar -->
    <header class="bg-white border-b border-zinc-200 h-16 flex items-center justify-between px-6 z-10 shrink-0">
        <div class="flex items-center gap-3">
            <div class="w-8 h-8 rounded-lg bg-zinc-900 flex items-center justify-center text-white">
                <i data-lucide="terminal" class="w-4 h-4"></i>
            </div>
            <div>
                <span class="font-bold tracking-tight text-zinc-950">Vibe</span>
                <span class="text-zinc-500 font-medium">Coder</span>
            </div>
            <div class="h-4 w-[1px] bg-zinc-200 mx-2"></div>
            <div class="flex items-center gap-2">
                <input id="project-title" type="text" value="Loading project..." 
                       class="text-sm font-semibold text-zinc-800 bg-transparent hover:bg-zinc-100 focus:bg-white focus:outline-none focus:ring-1 focus:ring-zinc-300 rounded px-2 py-1 w-64 transition-all"
                       onchange="updateProjectTitle(this.value)"/>
                <span id="save-status" class="text-xs text-zinc-400 flex items-center gap-1">
                    <i data-lucide="cloud-check" class="w-3.5 h-3.5 text-zinc-400"></i> Saved
                </span>
            </div>
        </div>

        <div class="flex items-center gap-4">
            <!-- Setup Gemini Key -->
            <div class="flex items-center gap-2 bg-zinc-100 p-1.5 rounded-lg border border-zinc-200">
                <i data-lucide="key" class="w-4 h-4 text-zinc-500 ml-1.5"></i>
                <input id="api-key-input" type="password" placeholder="Gemini API Key" 
                       class="bg-transparent text-xs w-48 focus:outline-none border-none text-zinc-700 font-mono"
                       onchange="saveApiKey(this.value)" />
            </div>

            <button onclick="saveCurrentCode()" class="flex items-center gap-2 bg-zinc-900 text-white text-sm font-medium px-4 py-2 rounded-lg hover:bg-zinc-800 active:scale-95 transition-all">
                <i data-lucide="save" class="w-4 h-4"></i>
                Save
            </button>
        </div>
    </header>

    <!-- Main Workspace Frame -->
    <div class="flex-1 flex overflow-hidden">
        
        <!-- Sidebar: Projects Dashboard List -->
        <aside class="w-72 bg-white border-r border-zinc-200 flex flex-col justify-between shrink-0 h-full">
            <div class="p-4 flex flex-col flex-1 overflow-hidden">
                <div class="flex items-center justify-between mb-4">
                    <h2 class="text-xs font-bold uppercase tracking-wider text-zinc-400">My Projects</h2>
                    <button onclick="createNewProject()" class="text-xs bg-zinc-100 hover:bg-zinc-200 text-zinc-700 px-2 py-1 rounded flex items-center gap-1 transition-all">
                        <i data-lucide="plus" class="w-3 h-3"></i> New
                    </button>
                </div>
                
                <!-- Dynamic Projects List Container -->
                <div id="projects-list" class="flex-1 overflow-y-auto space-y-1">
                    <!-- Dynamic rendering happens here -->
                </div>
            </div>

            <!-- Developer Info / Footer -->
            <div class="p-4 border-t border-zinc-200 bg-zinc-50 flex flex-col gap-1.5">
                <div class="text-[11px] text-zinc-400 font-mono flex items-center justify-between">
                    <span>Host: LOCAL</span>
                    <span>v1.0.2</span>
                </div>
                <div class="text-xs text-zinc-500 flex items-center gap-2">
                    <span class="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
                    <span>Vibe Server Running</span>
                </div>
            </div>
        </aside>

        <!-- Dynamic Work Area -->
        <main class="flex-1 flex flex-col lg:flex-row overflow-hidden bg-zinc-100">
            
            <!-- Left Workspace: Input / AI Prompt & Editor -->
            <section class="w-full lg:w-1/2 flex flex-col border-b lg:border-b-0 lg:border-r border-zinc-200 h-1/2 lg:h-full">
                
                <!-- Tab Switching Bar -->
                <div class="bg-white border-b border-zinc-200 px-4 h-12 flex items-center justify-between shrink-0">
                    <div class="flex gap-2">
                        <button onclick="switchTab('prompt')" id="tab-btn-prompt" class="px-3 py-1.5 rounded-md text-xs font-semibold flex items-center gap-1.5 bg-zinc-100 text-zinc-900">
                            <i data-lucide="sparkles" class="w-3.5 h-3.5"></i> Vibe Prompt
                        </button>
                        <button onclick="switchTab('editor')" id="tab-btn-editor" class="px-3 py-1.5 rounded-md text-xs font-medium flex items-center gap-1.5 text-zinc-500 hover:text-zinc-800">
                            <i data-lucide="code-2" class="w-3.5 h-3.5"></i> Raw Code
                        </button>
                    </div>
                    <span class="text-xs font-mono text-zinc-400" id="current-filename">index.html</span>
                </div>

                <!-- Tab Content: Prompt Interface -->
                <div id="tab-content-prompt" class="flex-1 flex flex-col p-6 overflow-y-auto">
                    <div class="mb-4">
                        <h3 class="text-lg font-bold text-zinc-900">What are we vibing today?</h3>
                        <p class="text-sm text-zinc-500">Describe the web interface, application, dashboard, or component you want to build.</p>
                    </div>

                    <textarea id="prompt-input" placeholder="e.g., Build a gorgeous modern landing page for a personal trainer SaaS startup. Include structured pricing cards, contact form, dark-mode styling, and functional FAQs using CSS transitions." 
                              class="w-full flex-1 min-h-[160px] p-4 text-sm border border-zinc-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-zinc-300 bg-white placeholder-zinc-400 shadow-sm resize-none mb-4"></textarea>

                    <div class="flex items-center gap-3">
                        <button onclick="generateProjectCode()" class="flex-1 flex items-center justify-center gap-2 bg-zinc-950 text-white font-medium text-sm py-3 px-6 rounded-xl hover:bg-zinc-800 transition-all active:scale-98">
                            <i data-lucide="sparkles" class="w-4 h-4 text-zinc-300"></i>
                            Generate & Apply Web UI
                        </button>
                    </div>

                    <!-- Quick Prompts / Examples -->
                    <div class="mt-8 border-t border-zinc-200 pt-6">
                        <h4 class="text-xs font-bold uppercase tracking-wider text-zinc-400 mb-3">Quick Inspirations</h4>
                        <div class="grid grid-cols-1 md:grid-cols-2 gap-2.5">
                            <button onclick="applyQuickPrompt('Minimalist Pomodoro Timer with dark mode toggle, crisp audio bell, sound effects, stats tracking and interactive circles.')" 
                                    class="text-left p-3 bg-white hover:bg-zinc-50 border border-zinc-200 rounded-lg text-xs font-medium text-zinc-600 hover:text-zinc-900 transition-all">
                                <span class="font-bold text-zinc-800 block">🍅 Pomodoro Timer</span>
                                Beautiful minimal aesthetics, stats tracker.
                            </button>
                            <button onclick="applyQuickPrompt('Advanced Budget & Analytics tracker dashboard showing mock interactive expense charts using Canvas, recent list, filter tabs and dynamic dynamic progress indicators.')" 
                                    class="text-left p-3 bg-white hover:bg-zinc-50 border border-zinc-200 rounded-lg text-xs font-medium text-zinc-600 hover:text-zinc-900 transition-all">
                                <span class="font-bold text-zinc-800 block">📊 Analytics Dashboard</span>
                                Charts, dynamic filters and tables.
                            </button>
                            <button onclick="applyQuickPrompt('Stunning minimal Weather forecast app. Displays current temperature, hourly stats, clean visual icons based on temperature, background gradient transition, and a search mock function.')" 
                                    class="text-left p-3 bg-white hover:bg-zinc-50 border border-zinc-200 rounded-lg text-xs font-medium text-zinc-600 hover:text-zinc-900 transition-all">
                                <span class="font-bold text-zinc-800 block">☀️ Weather Platform</span>
                                Clean ambient layouts, daily statistics.
                            </button>
                            <button onclick="applyQuickPrompt('A modern markdown live editor with dual panels (input and dynamic HTML markup parse preview), syntax highlight, character count and markdown table generator.')" 
                                    class="text-left p-3 bg-white hover:bg-zinc-50 border border-zinc-200 rounded-lg text-xs font-medium text-zinc-600 hover:text-zinc-900 transition-all">
                                <span class="font-bold text-zinc-800 block">📝 Markdown Editor</span>
                                Live parsing, syntax highlight & counters.
                            </button>
                        </div>
                    </div>
                </div>

                <!-- Tab Content: Live Code Editor -->
                <div id="tab-content-editor" class="hidden flex-1 flex flex-col overflow-hidden relative">
                    <div class="flex-1 flex overflow-hidden">
                        <!-- Line Numbers Bar -->
                        <div class="w-12 bg-zinc-900 text-zinc-600 select-none text-right pr-2 pt-4 font-mono text-xs leading-6 border-r border-zinc-800 flex flex-col overflow-hidden" id="line-numbers">
                            <!-- Populated with JS -->
                        </div>
                        <textarea id="code-textarea" oninput="handleCodeInput()" 
                                  class="flex-1 p-4 bg-zinc-950 text-zinc-100 code-font text-xs leading-6 resize-none focus:outline-none overflow-y-auto focus:ring-0 select-text" 
                                  spellcheck="false"></textarea>
                    </div>
                    <div class="bg-zinc-900 px-4 py-2 border-t border-zinc-800 flex items-center justify-between text-xs text-zinc-400 font-mono">
                        <span>Lines: <span id="line-count">1</span></span>
                        <span>UTF-8</span>
                    </div>
                </div>

            </section>

            <!-- Right Workspace: Sandbox Iframe Preview -->
            <section class="w-full lg:w-1/2 flex flex-col h-1/2 lg:h-full bg-zinc-100">
                <div class="bg-white border-b border-zinc-200 px-4 h-12 flex items-center justify-between shrink-0">
                    <div class="flex items-center gap-1.5 text-zinc-600 text-xs font-medium">
                        <span class="w-2.5 h-2.5 rounded-full bg-emerald-500"></span>
                        <span>Live Sandbox Preview</span>
                    </div>
                    <div class="flex items-center gap-2">
                        <button onclick="refreshPreview()" class="p-1.5 text-zinc-500 hover:text-zinc-800 hover:bg-zinc-100 rounded transition-all" title="Reload Frame">
                            <i data-lucide="rotate-cw" class="w-4 h-4"></i>
                        </button>
                        <button onclick="openSandboxWindow()" class="p-1.5 text-zinc-500 hover:text-zinc-800 hover:bg-zinc-100 rounded transition-all" title="Open in New Tab">
                            <i data-lucide="external-link" class="w-4 h-4"></i>
                        </button>
                    </div>
                </div>

                <!-- Iframe Container -->
                <div class="flex-1 p-4 bg-zinc-100 flex items-center justify-center">
                    <div class="w-full h-full bg-white rounded-xl shadow-sm border border-zinc-200 overflow-hidden relative flex flex-col">
                        <iframe id="preview-sandbox" class="w-full h-full border-none bg-white"></iframe>
                    </div>
                </div>
            </section>

        </main>
    </div>

    <!-- API LOADING / GENERATING OVERLAY -->
    <div id="loading-overlay" class="fixed inset-0 bg-zinc-950/80 backdrop-blur-sm hidden flex-col items-center justify-center z-50 text-white select-none">
        <div class="bg-zinc-900 border border-zinc-800 p-8 rounded-2xl max-w-sm text-center flex flex-col items-center shadow-xl">
            <!-- Spinner -->
            <div class="relative w-16 h-16 mb-4">
                <div class="absolute inset-0 rounded-full border-4 border-zinc-800"></div>
                <div class="absolute inset-0 rounded-full border-4 border-t-zinc-100 border-r-transparent animate-spin"></div>
            </div>
            <h3 class="text-base font-bold text-zinc-100 mb-1">Applying Vibe Coding...</h3>
            <p id="loading-subtitle" class="text-xs text-zinc-400 max-w-[260px] leading-relaxed">Gemini is architecting clean HTML layout structures, design styling tokens, and code logic layers.</p>
        </div>
    </div>

    <!-- ERROR CUSTOM TOAST MODAL -->
    <div id="error-modal" class="fixed inset-0 bg-zinc-950/50 backdrop-blur-sm hidden flex-col items-center justify-center z-50 text-zinc-900 select-none">
        <div class="bg-white border border-zinc-200 p-6 rounded-xl max-w-md w-full text-center flex flex-col items-center shadow-lg mx-4">
            <div class="w-12 h-12 rounded-full bg-rose-50 flex items-center justify-center text-rose-500 mb-4">
                <i data-lucide="alert-triangle" class="w-6 h-6"></i>
            </div>
            <h3 class="text-base font-bold text-zinc-900 mb-1">Execution Interrupted</h3>
            <p id="error-message" class="text-xs text-zinc-500 leading-relaxed mb-6"></p>
            <button onclick="closeErrorModal()" class="w-full bg-zinc-950 text-white font-medium text-sm py-2.5 rounded-lg hover:bg-zinc-800 transition-all">
                Dismiss Error
            </button>
        </div>
    </div>

    <script>
        // App State
        let currentProjectId = null;
        let projects = [];
        let currentCode = "";
        let activeTab = "prompt";

        // DOM Elements
        const promptInput = document.getElementById("prompt-input");
        const codeTextarea = document.getElementById("code-textarea");
        const previewIframe = document.getElementById("preview-sandbox");
        const projectTitleInput = document.getElementById("project-title");
        const saveStatusLabel = document.getElementById("save-status");
        const keyInput = document.getElementById("api-key-input");
        const projectsList = document.getElementById("projects-list");
        const lineNumbersColumn = document.getElementById("line-numbers");
        const lineCountSpan = document.getElementById("line-count");
        const loadingOverlay = document.getElementById("loading-overlay");
        const errorModal = document.getElementById("error-modal");
        const errorMessageDiv = document.getElementById("error-message");

        // Initialization
        window.addEventListener("DOMContentLoaded", async () => {
            lucide.createIcons();
            
            // Load key from localStorage
            const savedKey = localStorage.getItem("vibe_api_key") || "";
            keyInput.value = savedKey;

            // Load list of projects
            await loadProjects();
            
            // If projects exist, load the first one. Otherwise create a new one.
            if (projects.length > 0) {
                await selectProject(projects[0].id);
            } else {
                await createNewProject();
            }
        });

        // ---------------------------------------------------------------------
        // PROJECTS CRUD
        // ---------------------------------------------------------------------
        async function loadProjects() {
            try {
                const response = await fetch("/api/projects");
                projects = await response.json();
                renderProjectsList();
            } catch (err) {
                showError("Failed to fetch projects from the sqlite database backend.");
            }
        }

        function renderProjectsList() {
            projectsList.innerHTML = "";
            projects.forEach(project => {
                const isSelected = project.id === currentProjectId;
                const date = new Date(project.updated_at).toLocaleDateString(undefined, {
                    month: 'short',
                    day: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit'
                });

                const projectEl = document.createElement("div");
                projectEl.className = `group flex items-center justify-between p-3 rounded-lg cursor-pointer transition-all ${
                    isSelected ? 'bg-zinc-100' : 'hover:bg-zinc-50'
                }`;
                projectEl.setAttribute("onclick", `selectProject('${project.id}')`);

                projectEl.innerHTML = `
                    <div class="flex items-center gap-2.5 min-w-0 flex-1">
                        <i data-lucide="file-code" class="w-4 h-4 shrink-0 ${isSelected ? 'text-zinc-900' : 'text-zinc-400'}"></i>
                        <div class="min-w-0 flex-1">
                            <p class="text-xs font-semibold truncate ${isSelected ? 'text-zinc-950' : 'text-zinc-700'}">${escapeHtml(project.title)}</p>
                            <p class="text-[10px] text-zinc-400 mt-0.5 truncate">${date}</p>
                        </div>
                    </div>
                    <button onclick="event.stopPropagation(); confirmDeleteProject('${project.id}')" 
                            class="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-zinc-200/80 text-zinc-400 hover:text-zinc-700 transition-all"
                            title="Delete Project">
                        <i data-lucide="trash" class="w-3.5 h-3.5"></i>
                    </button>
                `;
                projectsList.appendChild(projectEl);
            });
            lucide.createIcons();
        }

        async function createNewProject() {
            try {
                const response = await fetch("/api/projects", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ title: "New Vibe UI Project" })
                });
                const project = await response.json();
                currentProjectId = project.id;
                
                await loadProjects();
                await selectProject(project.id);
            } catch (err) {
                showError("Could not create new project session.");
            }
        }

        async function selectProject(id) {
            currentProjectId = id;
            try {
                const response = await fetch(`/api/projects/${id}`);
                if (!response.ok) throw new Error();
                const project = await response.json();

                currentCode = project.code;
                projectTitleInput.value = project.title;
                codeTextarea.value = project.code;
                promptInput.value = project.prompt || "";
                
                // Synchronize preview
                updatePreviewFrame(project.code);
                updateLineNumbers();
                renderProjectsList();
                
                setSaveStatus(true);
            } catch (err) {
                showError("Unable to load project contents.");
            }
        }

        async function updateProjectTitle(newTitle) {
            if (!currentProjectId || !newTitle.trim()) return;
            try {
                setSaveStatus(false);
                await fetch(`/api/projects/${currentProjectId}`, {
                    method: "PUT",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ title: newTitle.trim() })
                });
                setSaveStatus(true);
                await loadProjects();
            } catch (err) {
                showError("Failed to update project title.");
            }
        }

        async function saveCurrentCode() {
            if (!currentProjectId) return;
            try {
                setSaveStatus(false);
                await fetch(`/api/projects/${currentProjectId}`, {
                    method: "PUT",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ code: currentCode })
                });
                setSaveStatus(true);
                
                // Highlight saving state on sidebar
                await loadProjects();
            } catch (err) {
                showError("Error committing current build version to SQLite database.");
            }
        }

        async function confirmDeleteProject(id) {
            if (!confirm("Are you sure you want to permanently delete this project? This action cannot be undone.")) return;
            try {
                await fetch(`/api/projects/${id}`, { method: "DELETE" });
                
                // If we deleted our current project, switch to another
                if (currentProjectId === id) {
                    currentProjectId = null;
                }
                await loadProjects();
                if (!currentProjectId && projects.length > 0) {
                    await selectProject(projects[0].id);
                } else if (projects.length === 0) {
                    await createNewProject();
                }
            } catch (err) {
                showError("Could not execute project deletion.");
            }
        }

        // ---------------------------------------------------------------------
        // CODE & REAL-TIME PREVIEW LOGIC
        // ---------------------------------------------------------------------
        function updatePreviewFrame(htmlCode) {
            const iframeDoc = previewIframe.contentDocument || previewIframe.contentWindow.document;
            iframeDoc.open();
            iframeDoc.write(htmlCode);
            iframeDoc.close();
        }

        function handleCodeInput() {
            currentCode = codeTextarea.value;
            updatePreviewFrame(currentCode);
            updateLineNumbers();
            
            // Auto save debounce effect (visual)
            setSaveStatus(false);
            debounceSave();
        }

        // Debounce Auto-Save Helper
        let saveTimeout;
        function debounceSave() {
            clearTimeout(saveTimeout);
            saveTimeout = setTimeout(async () => {
                await saveCurrentCode();
            }, 1200);
        }

        // Keep local Line numbering column synced with textarea scrolling and content
        function updateLineNumbers() {
            const lines = codeTextarea.value.split("\\n");
            const lineCount = lines.length;
            
            lineCountSpan.innerText = lineCount;
            
            let html = "";
            for (let i = 1; i <= lineCount; i++) {
                html += `<div>${i}</div>`;
            }
            lineNumbersColumn.innerHTML = html;
        }

        // Sync vertical scroll of Line Number strip with editor container
        codeTextarea.addEventListener("scroll", () => {
            lineNumbersColumn.scrollTop = codeTextarea.scrollTop;
        });

        function refreshPreview() {
            updatePreviewFrame(currentCode);
        }

        function openSandboxWindow() {
            const newWindow = window.open();
            if (newWindow) {
                newWindow.document.write(currentCode);
                newWindow.document.close();
            } else {
                showError("Pop-up blocked. Please allow popups to open the sandbox preview in a new window.");
            }
        }

        // ---------------------------------------------------------------------
        // AI VIBE GENERATION WORKER
        // ---------------------------------------------------------------------
        async function generateProjectCode() {
            const prompt = promptInput.value.trim();
            if (!prompt) {
                showError("Please enter a coding prompt to start vibe generation!");
                return;
            }

            const apiKey = localStorage.getItem("vibe_api_key") || "";
            showLoading(true);

            try {
                const response = await fetch("/api/generate", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ prompt, apiKey })
                });

                if (!response.ok) {
                    const errObj = await response.json();
                    throw new Error(errObj.detail || "Server failed to invoke Vibe coding API.");
                }

                const data = await response.json();
                
                // Set code
                currentCode = data.code;
                codeTextarea.value = currentCode;
                updatePreviewFrame(currentCode);
                updateLineNumbers();

                // Save automatically on backend db
                setSaveStatus(false);
                await fetch(`/api/projects/${currentProjectId}`, {
                    method: "PUT",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ code: currentCode, prompt: prompt })
                });
                setSaveStatus(true);
                
                // Show raw code panel to let users inspect code
                switchTab("editor");
            } catch (err) {
                showError(err.message || "An unexpected error occurred during rendering.");
            } finally {
                showLoading(false);
            }
        }

        function applyQuickPrompt(text) {
            promptInput.value = text;
            promptInput.focus();
        }

        // ---------------------------------------------------------------------
        // UI HELPERS
        // ---------------------------------------------------------------------
        function switchTab(tab) {
            activeTab = tab;
            const tabBtnPrompt = document.getElementById("tab-btn-prompt");
            const tabBtnEditor = document.getElementById("tab-btn-editor");
            const tabContentPrompt = document.getElementById("tab-content-prompt");
            const tabContentEditor = document.getElementById("tab-content-editor");

            if (tab === "prompt") {
                tabBtnPrompt.className = "px-3 py-1.5 rounded-md text-xs font-semibold flex items-center gap-1.5 bg-zinc-100 text-zinc-900";
                tabBtnEditor.className = "px-3 py-1.5 rounded-md text-xs font-medium flex items-center gap-1.5 text-zinc-500 hover:text-zinc-800";
                tabContentPrompt.classList.remove("hidden");
                tabContentEditor.classList.add("hidden");
            } else {
                tabBtnEditor.className = "px-3 py-1.5 rounded-md text-xs font-semibold flex items-center gap-1.5 bg-zinc-100 text-zinc-900";
                tabBtnPrompt.className = "px-3 py-1.5 rounded-md text-xs font-medium flex items-center gap-1.5 text-zinc-500 hover:text-zinc-800";
                tabContentEditor.classList.remove("hidden");
                tabContentPrompt.classList.add("hidden");
                updateLineNumbers();
            }
        }

        function saveApiKey(value) {
            localStorage.setItem("vibe_api_key", value.trim());
        }

        function setSaveStatus(saved) {
            if (saved) {
                saveStatusLabel.innerHTML = `<i data-lucide="cloud-check" class="w-3.5 h-3.5 text-emerald-500"></i> <span class="text-zinc-500">Saved</span>`;
            } else {
                saveStatusLabel.innerHTML = `<span class="inline-block w-2 h-2 rounded-full bg-amber-500 animate-pulse mr-1"></span> <span class="text-zinc-500 font-mono">saving...</span>`;
            }
            lucide.createIcons();
        }

        function showLoading(show) {
            if (show) {
                loadingOverlay.classList.remove("hidden");
                loadingOverlay.classList.add("flex");
            } else {
                loadingOverlay.classList.add("hidden");
                loadingOverlay.classList.remove("flex");
            }
        }

        function showError(message) {
            errorMessageDiv.innerText = message;
            errorModal.classList.remove("hidden");
            errorModal.classList.add("flex");
        }

        function closeErrorModal() {
            errorModal.classList.add("hidden");
            errorModal.classList.remove("flex");
        }

        function escapeHtml(text) {
            return text
                .replace(/&/g, "&amp;")
                .replace(/</g, "&lt;")
                .replace(/>/g, "&gt;")
                .replace(/"/g, "&quot;")
                .replace(/'/g, "&#039;");
        }
    </script>
</body>
</html>"""
# -----------------------------------------------------------------------------
# APPLICATION STARTUP
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    print(f"[*] Starting Production Vibe Coding Platform Server at: http://127.0.0.1:{port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
