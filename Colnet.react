import React, { useState, useEffect, useRef } from 'react';
import { 
  Terminal, 
  Cloud, 
  Save, 
  Plus, 
  FileCode, 
  Trash2, 
  Sparkles, 
  Code, 
  RotateCw, 
  ExternalLink, 
  Key, 
  AlertTriangle, 
  Check,
  ChevronRight,
  Info
} from 'lucide-react';

// Default starter template
const DEFAULT_CODE = `<!DOCTYPE html>
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
</html>`;

export default function App() {
  // App State
  const [projects, setProjects] = useState([]);
  const [currentProject, setCurrentProject] = useState(null);
  const [activeTab, setActiveTab] = useState('prompt'); // 'prompt' | 'editor'
  const [prompt, setPrompt] = useState('');
  const [code, setCode] = useState('');
  const [apiKey, setApiKey] = useState('');
  const [saveStatus, setSaveStatus] = useState('saved'); // 'saved' | 'saving' | 'unsaved'
  const [isLoading, setIsLoading] = useState(false);
  const [loadingSubtitle, setLoadingSubtitle] = useState('');
  
  // Custom Modals/Toasts
  const [errorMsg, setErrorMsg] = useState('');
  const [deleteConfirmId, setDeleteConfirmId] = useState(null);

  // Refs for Scroll Sync & Preview
  const textareaRef = useRef(null);
  const lineNumbersRef = useRef(null);
  const iframeRef = useRef(null);
  const debounceRef = useRef(null);

  // Load Key & Projects on Mount
  useEffect(() => {
    const savedKey = localStorage.getItem('vibe_api_key') || '';
    setApiKey(savedKey);

    // Load projects from LocalStorage to run fully client-side inside Canvas
    // while remaining fully prepared for a local backend.
    const savedProjects = localStorage.getItem('vibe_projects');
    if (savedProjects) {
      const parsed = JSON.parse(savedProjects);
      setProjects(parsed);
      if (parsed.length > 0) {
        loadProject(parsed[0]);
      } else {
        createFirstProject();
      }
    } else {
      createFirstProject();
    }
  }, []);

  // Update Preview & Scroll sync whenever code changes
  useEffect(() => {
    if (iframeRef.current && code) {
      const iframeDoc = iframeRef.current.contentDocument || iframeRef.current.contentWindow.document;
      iframeDoc.open();
      iframeDoc.write(code);
      iframeDoc.close();
    }
    syncLineNumbers();
  }, [code]);

  // Sync scroll of Line Numbers column and Code Area
  const handleScroll = () => {
    if (textareaRef.current && lineNumbersRef.current) {
      lineNumbersRef.current.scrollTop = textareaRef.current.scrollTop;
    }
  };

  const syncLineNumbers = () => {
    if (!textareaRef.current) return;
    const lines = code.split('\n');
    const totalLines = Math.max(lines.length, 1);
    
    if (lineNumbersRef.current) {
      lineNumbersRef.current.innerHTML = Array.from(
        { length: totalLines }, 
        (_, i) => `<div>${i + 1}</div>`
      ).join('');
    }
  };

  // ---------------------------------------------------------------------------
  // PROJECT UTILITIES
  // ---------------------------------------------------------------------------
  const createFirstProject = () => {
    const initialProject = {
      id: 'default-project-id',
      title: 'Starter Dashboard Project',
      prompt: 'A starting template',
      code: DEFAULT_CODE,
      updated_at: new Date().toISOString()
    };
    const initialList = [initialProject];
    setProjects(initialList);
    localStorage.setItem('vibe_projects', JSON.stringify(initialList));
    loadProject(initialProject);
  };

  const loadProject = (project) => {
    setCurrentProject(project);
    setCode(project.code);
    setPrompt(project.prompt || '');
  };

  const createNewProject = () => {
    const newId = `proj-${Date.now()}`;
    const newProj = {
      id: newId,
      title: 'New Vibe UI Project',
      prompt: '',
      code: DEFAULT_CODE,
      updated_at: new Date().toISOString()
    };
    const updated = [newProj, ...projects];
    setProjects(updated);
    localStorage.setItem('vibe_projects', JSON.stringify(updated));
    loadProject(newProj);
  };

  const updateCurrentProject = (updatedFields) => {
    if (!currentProject) return;

    const updatedProject = {
      ...currentProject,
      ...updatedFields,
      updated_at: new Date().toISOString()
    };

    setCurrentProject(updatedProject);

    // Sync back to lists
    const updatedList = projects.map(p => p.id === currentProject.id ? updatedProject : p);
    // Sort so most recently modified is at the top
    const sortedList = updatedList.sort((a, b) => new Date(b.updated_at) - new Date(a.updated_at));
    setProjects(sortedList);
    localStorage.setItem('vibe_projects', JSON.stringify(sortedList));
  };

  const handleTitleChange = (val) => {
    updateCurrentProject({ title: val });
  };

  const handleCodeChange = (e) => {
    const newCode = e.target.value;
    setCode(newCode);
    setSaveStatus('unsaved');

    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      updateCurrentProject({ code: newCode });
      setSaveStatus('saved');
    }, 1000);
  };

  const requestDeleteProject = (id, e) => {
    e.stopPropagation();
    setDeleteConfirmId(id);
  };

  const executeDeleteProject = () => {
    const id = deleteConfirmId;
    const filtered = projects.filter(p => p.id !== id);
    setProjects(filtered);
    localStorage.setItem('vibe_projects', JSON.stringify(filtered));
    setDeleteConfirmId(null);

    if (currentProject?.id === id) {
      if (filtered.length > 0) {
        loadProject(filtered[0]);
      } else {
        createFirstProject();
      }
    }
  };

  const handleApiKeyChange = (val) => {
    setApiKey(val);
    localStorage.setItem('vibe_api_key', val.trim());
  };

  // ---------------------------------------------------------------------------
  // AI CODE GENERATION (GEMINI CLIENT WITH EXPONENTIAL BACKOFF)
  // ---------------------------------------------------------------------------
  const callGeminiAPI = async (userPrompt) => {
    const keyToUse = apiKey.trim();
    if (!keyToUse) {
      throw new Error("Gemini API Key is missing. Please provide it in the top settings bar.");
    }

    const url = `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-09-2025:generateContent?key=${keyToUse}`;
    
    const systemInstruction = (
      "You are an expert web development AI. Generate a fully responsive, visually beautiful, " +
      "and complete single-file web application using standard HTML, inline CSS (or Tailwind CDN), " +
      "and clean JavaScript. Do not write any markdown wrappers, explanations, introduction, or " +
      "conclusions. You MUST return only the clean, executable code starting with <!DOCTYPE html> " +
      "and ending with </html>."
    );

    const payload = {
      contents: [{
        parts: [{ text: userPrompt }]
      }],
      systemInstruction: {
        parts: [{ text: systemInstruction }]
      }
    };

    let retries = 5;
    let delay = 1000;

    for (let i = 0; i < retries; i++) {
      try {
        const response = await fetch(url, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });

        if (response.status === 200) {
          const data = await response.json();
          const rawText = data.candidates?.[0]?.content?.parts?.[0]?.text || "";
          
          if (!rawText) {
            throw new Error("Received empty content block from Gemini.");
          }

          // Clean up markdown markers if any got through instructions
          let cleaned = rawText.replace(/^```html\s*/i, "");
          cleaned = cleaned.replace(/^```xml\s*/i, "");
          cleaned = cleaned.replace(/^```\s*/i, "");
          cleaned = cleaned.replace(/```$/, "");
          return cleaned.trim();
        } else if ([429, 500, 502, 503, 504].includes(response.status)) {
          // Retryable error
          await new Promise(res => setTimeout(res, delay));
          delay *= 2;
        } else {
          // Hard error
          const text = await response.text();
          throw new Error(`Gemini API returned status ${response.status}: ${text}`);
        }
      } catch (err) {
        if (i === retries - 1) {
          throw err;
        }
        await new Promise(res => setTimeout(res, delay));
        delay *= 2;
      }
    }
    throw new Error("Max API connection retries reached. Please check your network and API Key.");
  };

  const handleGenerate = async () => {
    if (!prompt.trim()) {
      setErrorMsg("Please write a creative prompt before generating.");
      return;
    }

    setIsLoading(true);
    setLoadingSubtitle("Connecting to Gemini and planning site architecture...");

    try {
      const generatedCode = await callGeminiAPI(prompt);
      setCode(generatedCode);
      updateCurrentProject({ code: generatedCode, prompt });
      setSaveStatus('saved');
      
      // Navigate to Code editor tab automatically to let users inspect code changes
      setActiveTab('editor');
    } catch (err) {
      setErrorMsg(err.message || "An unexpected error occurred during rendering.");
    } finally {
      setIsLoading(false);
    }
  };

  const applyQuickPrompt = (text) => {
    setPrompt(text);
  };

  const refreshPreview = () => {
    if (iframeRef.current) {
      const iframeDoc = iframeRef.current.contentDocument || iframeRef.current.contentWindow.document;
      iframeDoc.open();
      iframeDoc.write(code);
      iframeDoc.close();
    }
  };

  const openSandboxWindow = () => {
    const newWindow = window.open();
    if (newWindow) {
      newWindow.document.write(code);
      newWindow.document.close();
    } else {
      setErrorMsg("Pop-up blocked. Please allow popups to open the design in a full browser tab.");
    }
  };

  return (
    <div className="bg-zinc-50 text-zinc-900 min-h-screen flex flex-col antialiased select-none font-sans">
      
      {/* HEADER BAR */}
      <header className="bg-white border-b border-zinc-200 h-16 flex items-center justify-between px-6 shrink-0 z-10">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-zinc-950 flex items-center justify-center text-white">
            <Terminal className="w-4 h-4" />
          </div>
          <div>
            <span class="font-bold tracking-tight text-zinc-955">Vibe</span>
            <span className="text-zinc-500 font-medium">Coder</span>
          </div>
          <div className="h-4 w-[1px] bg-zinc-200 mx-2"></div>
          
          <div className="flex items-center gap-2">
            <input 
              type="text" 
              value={currentProject?.title || ''} 
              onChange={(e) => handleTitleChange(e.target.value)}
              className="text-sm font-semibold text-zinc-800 bg-transparent hover:bg-zinc-100 focus:bg-white focus:outline-none focus:ring-1 focus:ring-zinc-300 rounded px-2 py-1 w-64 transition-all"
            />
            <span className="text-xs text-zinc-400 flex items-center gap-1 ml-1">
              <Cloud className={`w-3.5 h-3.5 ${saveStatus === 'saved' ? 'text-emerald-500' : 'text-amber-500 animate-pulse'}`} /> 
              {saveStatus === 'saved' ? 'Saved' : 'Saving...'}
            </span>
          </div>
        </div>

        <div className="flex items-center gap-4">
          {/* Gemini API Key input */}
          <div className="flex items-center gap-2 bg-zinc-100 p-1.5 rounded-lg border border-zinc-200">
            <Key className="w-4 h-4 text-zinc-500 ml-1.5" />
            <input 
              type="password" 
              placeholder="Gemini API Key" 
              value={apiKey}
              onChange={(e) => handleApiKeyChange(e.target.value)}
              className="bg-transparent text-xs w-48 focus:outline-none border-none text-zinc-700 font-mono"
            />
          </div>

          <button 
            onClick={() => updateCurrentProject({ code })} 
            className="flex items-center gap-2 bg-zinc-950 text-white text-sm font-medium px-4 py-2 rounded-lg hover:bg-zinc-850 active:scale-95 transition-all"
          >
            <Save className="w-4 h-4" />
            Save
          </button>
        </div>
      </header>

      {/* WORKSPACE AREA */}
      <div className="flex-1 flex overflow-hidden">
        
        {/* SIDEBAR */}
        <aside className="w-72 bg-white border-r border-zinc-200 flex flex-col justify-between shrink-0 h-full">
          <div className="p-4 flex flex-col flex-1 overflow-hidden">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xs font-bold uppercase tracking-wider text-zinc-400">My Projects</h2>
              <button 
                onClick={createNewProject} 
                className="text-xs bg-zinc-100 hover:bg-zinc-200 text-zinc-700 px-2.5 py-1 rounded-md flex items-center gap-1 transition-all"
              >
                <Plus className="w-3.5 h-3.5" /> New
              </button>
            </div>
            
            {/* Project items */}
            <div className="flex-1 overflow-y-auto space-y-1">
              {projects.map((project) => {
                const isSelected = project.id === currentProject?.id;
                const formattedDate = new Date(project.updated_at).toLocaleDateString(undefined, {
                  month: 'short',
                  day: 'numeric',
                  hour: '2-digit',
                  minute: '2-digit'
                });

                return (
                  <div 
                    key={project.id}
                    onClick={() => loadProject(project)}
                    className={`group flex items-center justify-between p-3 rounded-lg cursor-pointer transition-all ${
                      isSelected ? 'bg-zinc-100' : 'hover:bg-zinc-50'
                    }`}
                  >
                    <div className="flex items-center gap-2.5 min-w-0 flex-1">
                      <FileCode className={`w-4 h-4 shrink-0 ${isSelected ? 'text-zinc-900' : 'text-zinc-400'}`} />
                      <div className="min-w-0 flex-1">
                        <p className={`text-xs font-semibold truncate ${isSelected ? 'text-zinc-950' : 'text-zinc-700'}`}>{project.title}</p>
                        <p className="text-[10px] text-zinc-400 mt-0.5 truncate">{formattedDate}</p>
                      </div>
                    </div>
                    <button 
                      onClick={(e) => requestDeleteProject(project.id, e)}
                      className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-zinc-200 text-zinc-450 hover:text-rose-600 transition-all"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                );
              })}
            </div>
          </div>

          <div className="p-4 border-t border-zinc-200 bg-zinc-50 flex flex-col gap-2">
            <div className="flex items-center gap-2 text-xs text-zinc-500">
              <div className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse"></div>
              <span>Vibe State: Active Preview</span>
            </div>
            <p className="text-[10px] text-zinc-400 font-mono">React v18.3 • Tailwind Integration</p>
          </div>
        </aside>

        {/* EDITOR / PREVIEW DIVISION PANEL */}
        <main className="flex-1 flex flex-col lg:flex-row overflow-hidden bg-zinc-100">
          
          {/* EDITOR SECTION */}
          <section className="w-full lg:w-1/2 flex flex-col border-b lg:border-b-0 lg:border-r border-zinc-200 h-1/2 lg:h-full bg-white">
            
            {/* Tabs */}
            <div className="bg-white border-b border-zinc-200 px-4 h-12 flex items-center justify-between shrink-0">
              <div className="flex gap-2">
                <button 
                  onClick={() => setActiveTab('prompt')} 
                  className={`px-3 py-1.5 rounded-md text-xs font-semibold flex items-center gap-1.5 transition-all ${
                    activeTab === 'prompt' ? 'bg-zinc-100 text-zinc-955' : 'text-zinc-500 hover:text-zinc-800'
                  }`}
                >
                  <Sparkles className="w-3.5 h-3.5" /> Vibe Prompt
                </button>
                <button 
                  onClick={() => setActiveTab('editor')} 
                  className={`px-3 py-1.5 rounded-md text-xs font-semibold flex items-center gap-1.5 transition-all ${
                    activeTab === 'editor' ? 'bg-zinc-100 text-zinc-955' : 'text-zinc-500 hover:text-zinc-800'
                  }`}
                >
                  <Code className="w-3.5 h-3.5" /> Raw Code
                </button>
              </div>
              <span className="text-xs font-mono text-zinc-400">index.html</span>
            </div>

            {/* TAB 1: AI Prompt Input */}
            {activeTab === 'prompt' && (
              <div className="flex-1 flex flex-col p-6 overflow-y-auto">
                <div className="mb-4">
                  <h3 className="text-lg font-bold text-zinc-900">What design style are we vibing?</h3>
                  <p className="text-xs text-zinc-500">Provide high-fidelity specifications. Gemini will convert your description into clean code structure.</p>
                </div>

                <textarea 
                  value={prompt}
                  onChange={(e) => setPrompt(e.target.value)}
                  placeholder="e.g. Build an executive portfolio site for a brand designer. Minimal dark theme, grid project displays, interactive filters, smooth accordion dropdowns, and micro-animations using custom JS trigger classes." 
                  className="w-full flex-1 min-h-[160px] p-4 text-sm border border-zinc-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-zinc-300 bg-zinc-50/50 placeholder-zinc-450 resize-none mb-4 font-normal"
                />

                <button 
                  onClick={handleGenerate}
                  className="flex items-center justify-center gap-2 bg-zinc-950 text-white font-medium text-sm py-3 px-6 rounded-xl hover:bg-zinc-800 transition-all active:scale-98 shadow-sm"
                >
                  <Sparkles className="w-4 h-4 text-zinc-300" />
                  Generate & Compile View
                </button>

                {/* Templates Grid */}
                <div className="mt-8 border-t border-zinc-200 pt-5">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-zinc-400 mb-3 flex items-center gap-1">
                    <Info className="w-3.5 h-3.5" /> Inspiration Starters
                  </h4>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5">
                    <button 
                      onClick={() => applyQuickPrompt('Pomodoro productivity workspace featuring a beautiful circular progress SVG, clean dashboard stats, history log table, customized sound triggers, and light/dark mode switch.')}
                      className="text-left p-3 bg-white hover:bg-zinc-50 border border-zinc-200 rounded-lg text-xs font-medium text-zinc-600 hover:text-zinc-900 transition-all"
                    >
                      <span className="font-bold text-zinc-800 block">🍅 Minimalist Timer</span>
                      Stateful workflow with custom sound triggers.
                    </button>
                    <button 
                      onClick={() => applyQuickPrompt('Build a beautiful crypto portfolio tracker web app dashboard. Present interactive canvas trends charts, latest price list feed, simulated buy/sell actions modal, and customizable alerts.')}
                      className="text-left p-3 bg-white hover:bg-zinc-50 border border-zinc-200 rounded-lg text-xs font-medium text-zinc-600 hover:text-zinc-900 transition-all"
                    >
                      <span className="font-bold text-zinc-800 block">📊 Crypto Analytics</span>
                      Live charts dashboard, alerts, transaction tables.
                    </button>
                    <button 
                      onClick={() => applyQuickPrompt('Single-page interactive visual resume for a frontend developer. Elegant zinc styling, interactive timeline sliders, functional code sandbox emulator card, and responsive custom layout.')}
                      className="text-left p-3 bg-white hover:bg-zinc-50 border border-zinc-200 rounded-lg text-xs font-medium text-zinc-600 hover:text-zinc-900 transition-all"
                    >
                      <span className="font-bold text-zinc-850 block">💼 Interactive Resume</span>
                      Polished layout transitions, responsive columns.
                    </button>
                    <button 
                      onClick={() => applyQuickPrompt('Stunning minimal weather dashboard. Clean ambient dynamic backdrops matching local time, search filters, details charts, and functional widget views.')}
                      className="text-left p-3 bg-white hover:bg-zinc-50 border border-zinc-200 rounded-lg text-xs font-medium text-zinc-600 hover:text-zinc-900 transition-all"
                    >
                      <span className="font-bold text-zinc-850 block">☀️ Weather Dashboard</span>
                      Elegant layouts with adaptive atmosphere UI.
                    </button>
                  </div>
                </div>
              </div>
            )}

            {/* TAB 2: Raw Code Area */}
            {activeTab === 'editor' && (
              <div className="flex-1 flex flex-col overflow-hidden relative">
                <div className="flex-1 flex overflow-hidden">
                  <div 
                    ref={lineNumbersRef}
                    className="w-12 bg-zinc-900 text-zinc-600 select-none text-right pr-2.5 pt-4 font-mono text-xs leading-6 border-r border-zinc-800 flex flex-col overflow-hidden text-right"
                  >
                    {/* Synchronized programmatically */}
                  </div>
                  <textarea 
                    ref={textareaRef}
                    value={code}
                    onChange={handleCodeChange}
                    onScroll={handleScroll}
                    className="flex-1 p-4 bg-zinc-950 text-zinc-100 font-mono text-xs leading-6 resize-none focus:outline-none overflow-y-auto select-text selection:bg-zinc-700 selection:text-white"
                    spellCheck="false"
                  />
                </div>
                <div className="bg-zinc-900 px-4 py-2 border-t border-zinc-800 flex items-center justify-between text-xs text-zinc-500 font-mono">
                  <span>Lines: {code.split('\n').length}</span>
                  <span>UTF-8</span>
                </div>
              </div>
            )}

          </section>

          {/* PREVIEW CONTAINER SECTION */}
          <section className="w-full lg:w-1/2 flex flex-col h-1/2 lg:h-full bg-zinc-100">
            <div className="bg-white border-b border-zinc-200 px-4 h-12 flex items-center justify-between shrink-0">
              <div className="flex items-center gap-1.5 text-zinc-700 text-xs font-semibold">
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse"></span>
                <span>Live Sandbox Preview</span>
              </div>
              <div className="flex items-center gap-1">
                <button 
                  onClick={refreshPreview} 
                  className="p-1.5 text-zinc-500 hover:text-zinc-800 hover:bg-zinc-100 rounded-lg transition-all" 
                  title="Reload Frame"
                >
                  <RotateCw className="w-4 h-4" />
                </button>
                <button 
                  onClick={openSandboxWindow} 
                  className="p-1.5 text-zinc-500 hover:text-zinc-800 hover:bg-zinc-100 rounded-lg transition-all" 
                  title="Open Sandbox in New Tab"
                >
                  <ExternalLink className="w-4 h-4" />
                </button>
              </div>
            </div>

            <div className="flex-1 p-4 bg-zinc-100 flex items-center justify-center">
              <div className="w-full h-full bg-white rounded-xl shadow-sm border border-zinc-200 overflow-hidden relative flex flex-col">
                <iframe 
                  ref={iframeRef}
                  title="Live Output Sandbox"
                  className="w-full h-full border-none bg-white"
                />
              </div>
            </div>
          </section>

        </main>
      </div>

      {/* LOADER SPLASH SCREEN OVERLAY */}
      {isLoading && (
        <div className="fixed inset-0 bg-zinc-950/80 backdrop-blur-sm flex flex-col items-center justify-center z-50 text-white select-none animate-fadeIn">
          <div class="bg-zinc-900 border border-zinc-850 p-8 rounded-2xl max-w-sm text-center flex flex-col items-center shadow-2xl">
            <div className="relative w-16 h-16 mb-4">
              <div className="absolute inset-0 rounded-full border-4 border-zinc-800"></div>
              <div className="absolute inset-0 rounded-full border-4 border-t-zinc-100 border-r-transparent animate-spin"></div>
            </div>
            <h3 className="text-base font-bold text-zinc-100 mb-1">Applying Vibe Code Base...</h3>
            <p className="text-xs text-zinc-400 max-w-[260px] leading-relaxed">{loadingSubtitle}</p>
          </div>
        </div>
      )}

      {/* ERROR MODAL */}
      {errorMsg && (
        <div className="fixed inset-0 bg-zinc-950/60 backdrop-blur-sm flex flex-col items-center justify-center z-50 text-zinc-900 select-none">
          <div className="bg-white border border-zinc-200 p-6 rounded-xl max-w-md w-full text-center flex flex-col items-center shadow-xl mx-4 animate-scaleUp">
            <div className="w-12 h-12 rounded-full bg-rose-50 flex items-center justify-center text-rose-500 mb-4">
              <AlertTriangle className="w-6 h-6" />
            </div>
            <h3 className="text-base font-bold text-zinc-900 mb-1">Execution Interrupted</h3>
            <p className="text-xs text-zinc-500 leading-relaxed mb-6">{errorMsg}</p>
            <button 
              onClick={() => setErrorMsg('')} 
              className="w-full bg-zinc-950 text-white font-medium text-sm py-2.5 rounded-lg hover:bg-zinc-800 transition-all active:scale-98"
            >
              Dismiss Notification
            </button>
          </div>
        </div>
      )}

      {/* CONFIRM DELETE MODAL */}
      {deleteConfirmId && (
        <div className="fixed inset-0 bg-zinc-950/50 backdrop-blur-sm flex flex-col items-center justify-center z-50 text-zinc-950 select-none">
          <div className="bg-white border border-zinc-200 p-6 rounded-xl max-w-sm w-full text-center flex flex-col items-center shadow-xl mx-4">
            <div className="w-12 h-12 rounded-full bg-zinc-100 flex items-center justify-center text-zinc-700 mb-4 animate-bounce">
              <Trash2 className="w-5 h-5" />
            </div>
            <h3 className="text-base font-bold text-zinc-900 mb-1">Delete Project?</h3>
            <p className="text-xs text-zinc-500 leading-relaxed mb-6">Are you sure you want to delete this design? This operation cannot be undone.</p>
            <div className="flex gap-2 w-full">
              <button 
                onClick={() => setDeleteConfirmId(null)} 
                className="flex-1 bg-zinc-100 hover:bg-zinc-200 text-zinc-800 font-medium text-xs py-2.5 rounded-lg transition-all"
              >
                Keep File
              </button>
              <button 
                onClick={executeDeleteProject} 
                className="flex-1 bg-rose-600 hover:bg-rose-700 text-white font-medium text-xs py-2.5 rounded-lg transition-all"
              >
                Delete File
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}
