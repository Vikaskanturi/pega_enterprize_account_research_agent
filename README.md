# 🔍 Pega Enterprise Account Research Agent

An AI-powered **multi-step research pipeline** that automates B2B sales account intelligence for Pega opportunities. Given a company name, the agent runs a **13-step pipeline** covering LinkedIn headcounts, GCC detection, Pega usage verification, and enterprise-type classification — then exports a structured **33-column Excel report**.

---

## ✨ Features

- **13-Step Research Pipeline** — fully automated end-to-end
- **Multi-Model LLM Support** — Gemini, OpenAI GPT-4o, Anthropic Claude, Groq, Ollama, LM Studio
- **Tavily AI Search** — AI-optimised web search, deep research, content extraction and site crawling
- **8-Tool Agentic Search** — LLM autonomously picks the best tool for each research task
- **Live WebSocket Streaming** — real-time step-by-step progress in the UI
- **LinkedIn Scraping** — authenticated headcount scraping (Engineering / IT / QA) using cookies
- **Automatic Cookie Sanitizer** — any browser-exported LinkedIn cookies are auto-cleaned before use
- **GCC Detection** — identifies India Global Capability Centres
- **Pega Usage Verification** — LinkedIn + Google corroboration
- **Enterprise Type Classification** — E1 / E1.1 / E2 / E3
- **Master Excel File** — all runs append to a single persistent `output/research_results.xlsx`
- **API Key Manager in UI** — configure all keys from the browser settings modal
- **Live Health Check** — `/api/health` validates all services before you start a run
- **Premium Dark UI** — glassmorphism design with real-time updates

---

## 🚀 Quick Start & Setup

### 1. Clone the repository

```bash
git clone https://github.com/Vikaskanturi/pega_enterprize_account_research_agent.git
cd pega_enterprize_account_research_agent
```

### 2. Install dependencies

```bash
python -m venv .venv

# Activate on Windows:
.venv\Scripts\activate
# Activate on Mac/Linux:
source .venv/bin/activate

pip install -r requirements.txt
python -m playwright install chromium
```

### 3. Configure API Keys

You can either edit `.env` directly **or** use the ⚙️ **Settings panel** in the browser UI after launching.

```env
# Minimum required — Gemini has a free tier at https://ai.google.dev
GEMINI_API_KEY=your_actual_key_here

# Optional LLM providers
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
GROQ_API_KEY=

# Optional search providers (Tavily is recommended — free tier available)
TAVILY_API_KEY=tvly-...
SERPAPI_KEY=

# App defaults
DEFAULT_LLM_PROVIDER=gemini
DEFAULT_LLM_MODEL=gemini-2.5-flash
APP_PORT=8000
```

> **Search priority:** `Tavily` → `SerpAPI` → `DuckDuckGo` (automatic fallback chain)

### 4. Setup Local LLMs (Ollama / LM Studio) *Optional*

**For Ollama:**
1. Install [Ollama](https://ollama.com/) and pull a model: `ollama pull llama3`
2. Update your `.env`:
   ```env
   OLLAMA_BASE_URL=http://localhost:11434
   OLLAMA_MODEL=llama3
   ```

**For LM Studio:**
1. Install [LM Studio](https://lmstudio.ai/) and load a model.
2. Start the **Local Server** (default port `1234`).
3. The agent auto-detects LM Studio models. Select them from the model dropdown in the UI.

**LM Studio MCP (Web Search for local models):**

Add this to LM Studio's MCP server configuration to give local models web search capability:
```json
{
  "mcpServers": {
    "tavily-remote-mcp": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "https://mcp.tavily.com/mcp/?tavilyApiKey=YOUR_TAVILY_KEY"],
      "env": {}
    }
  }
}
```
> Requires [Node.js](https://nodejs.org/) for `npx`.

### 5. LinkedIn Cookies (Optional but Recommended)

Providing authenticated LinkedIn cookies unlocks accurate headcount data for Steps 6–11.

1. Log into LinkedIn in your browser.
2. Use the **"Cookie Editor"** browser extension to export cookies as JSON.
3. Save the file to `data/linkedin_cookies.json`.

> **Auto-fix:** The agent automatically sanitizes cookie formats exported from any browser extension — invalid `sameSite` values like `no_restriction` or `unspecified` are corrected before use.

### 6. Launch the server

```bash
python run.py
```

Then open **http://localhost:8000** in your browser.

---

## 🧠 Agentic Search — 8 Tools

The LLM autonomously selects the best tool for each research task:

| Tool | Best For |
|------|---------|
| `web_search` | Broad public info, news, firmographic data |
| `linkedin_search` | Employee profiles, job titles, Pega certifications |
| `browser_visit` | Full page content of a specific URL |
| `llm_knowledge` | Well-known Fortune 500 intrinsic facts |
| `tavily_extract` | Clean structured extraction from a specific URL |
| `tavily_research` | Deep multi-source AI research on complex queries |
| `tavily_crawl` | Recursively find sub-pages on a domain |
| `tavily_map` | Generate a full site map of a domain |

---

## 🔬 The 13-Step Pipeline

| Step | Name | Tools Used |
|------|------|-----------|
| 1 | Input & Classification | Excel lookup (Pega reference) |
| 2 | Revenue Classification | Web search + LLM |
| 3 | Basic Firmographics | Web search + LLM |
| 4 | Corporate Structure | Web search + LLM |
| 5 | GCC Check (India) | Web search + LLM |
| 6 | LinkedIn Discovery | Search + Browser |
| 7 | Employee Count | LinkedIn scraping |
| 8 | Engineering / IT / QA Headcount | LinkedIn scraping |
| 9 | Pega Usage Verification | LinkedIn + Google + LLM |
| 10 | Competing Platforms | LinkedIn scraping |
| 11 | Service Company Check | Search + LinkedIn + LLM |
| 12 | Final Categorization | LLM (strongest model) |
| 13 | Research Notes & Completion | Rule-based |

---

## 📊 Output — 33 Columns

The master Excel file (`output/research_results.xlsx`) grows with each run. Columns include:
- Company identity (name, parent, India subsidiary, industry, HQ, revenue)
- Pega relationship (customer/partner, usage confirmed, evidence)
- GCC presence in India (count, locations, main GCC)
- Headcount breakdown (total, India, Engineering, IT, QA/SDET — global & India)
- Development model (in-house / outsourced / mixed)
- Service company signals, competing platforms
- Enterprise Type (E1 / E1.1 / E2 / E3)
- Research notes

---

## 🤖 Enterprise Type Definitions

| Type | Label | Description |
|------|-------|-------------|
| **E1** | Fully Outsourced | Development fully outsourced, minimal internal engineering |
| **E1.1** | Transitioning In-House | Currently outsourced, actively building internal team |
| **E2** | Non-Software Enterprise | Core business is non-software (banking, insurance, manufacturing) |
| **E3** | Software-First Enterprise | Software IS the business; strong build-over-buy culture |

---

## 📁 Project Structure

```
pega_enterprise_account_research/
├── app/
│   ├── main.py                  # FastAPI entry point
│   ├── agent/
│   │   ├── orchestrator.py      # Pipeline controller
│   │   ├── state.py             # 33-column research state
│   │   ├── steps/               # Steps 1–13
│   │   └── tools/
│   │       ├── llm_tool.py      # Multi-provider LLM client
│   │       ├── search_tool.py   # Tavily / SerpAPI / DDG search + agentic router
│   │       ├── browser_tool.py  # Playwright scraper + cookie sanitizer
│   │       └── excel_tool.py    # Master Excel upsert logic
│   └── api/
│       ├── routes.py            # REST + WebSocket + health check endpoints
│       └── models.py            # Pydantic schemas
├── frontend/
│   ├── index.html               # Single-page app
│   ├── app.js                   # Reactive frontend with settings modal
│   └── style.css                # Glassmorphism dark theme
├── data/
│   ├── pega_accounts.xlsx       # Pega partner/customer reference list
│   └── linkedin_cookies.json    # Your LinkedIn session cookies (gitignored)
├── output/                      # Generated Excel reports (gitignored)
├── .env                         # API keys and configuration (gitignored)
├── requirements.txt
└── run.py
```

---

## 🛠 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `WS` | `/ws/research` | Real-time research streaming |
| `POST` | `/api/research/start` | Start a background research job |
| `GET` | `/api/research/{job_id}` | Get job status & results |
| `GET` | `/api/download` | Download master Excel file |
| `POST` | `/api/export` | Export & download current research as Excel |
| `POST` | `/api/save_local` | Append research to the master Excel file |
| `GET` | `/api/health` | Live validation of all API keys & services |
| `GET` | `/api/settings` | Get masked API key status |
| `POST` | `/api/settings` | Save API keys to `.env` from the UI |
| `GET` | `/api/models` | List available LLM models |
| `GET` | `/api/jobs` | List all research jobs |
