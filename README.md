# 🔍 Pega Enterprise Account Research Agent

An AI-powered **multi-step research pipeline** that automates B2B sales account intelligence for Pega opportunities. Given a company name, the agent runs a 13-step pipeline covering LinkedIn headcounts, GCC detection, Pega usage verification, and enterprise-type classification — then exports a structured 33-column Excel report.

---

## ✨ Features

- **13-Step Research Pipeline** — fully automated end-to-end
- **Multi-Model LLM Support** — Gemini, OpenAI GPT-4o, Anthropic Claude, Ollama (local)
- **Live WebSocket Streaming** — real-time step-by-step progress in the UI
- **LinkedIn Scraping** — employee counts, functional headcounts (Engineering / IT / QA)
- **GCC Detection** — identifies India Global Capability Centres
- **Pega Usage Verification** — LinkedIn + Google corroboration
- **Enterprise Type Classification** — E1 / E1.1 / E2 / E3
- **33-Column Excel Export** — formatted and color-coded output
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

### 2. Configure API Keys

Edit `.env` and add your API keys:

```env
GEMINI_API_KEY=your_actual_key_here     # Required for default model
OPENAI_API_KEY=                          # Optional
ANTHROPIC_API_KEY=                       # Optional
```

> **Minimum**: You need at least one LLM API key. Gemini has a free tier at [ai.google.dev](https://ai.google.dev).

### 3. Setup Local LLMs (Ollama / LMStudio) *Optional*

If you prefer to run models locally for privacy or cost reasons, the agent supports **Ollama** and **LM Studio**.

**For Ollama:**
1. Install [Ollama](https://ollama.com/) and download a model (e.g., `ollama pull llama3`).
2. Ensure Ollama is running, then update your `.env` file:
   ```env
   OLLAMA_BASE_URL=http://localhost:11434
   OLLAMA_MODEL=llama3
   ```

**For LM Studio:**
1. Install [LM Studio](https://lmstudio.ai/).
2. Load a model and start the **Local Server** (ensure it is running on the default port `1234`).
3. The Pega Research Agent will automatically detect models running on LM Studio. You can also manage and switch models directly from the agent's web UI.

### 4. Launch the server

```bash
python run.py
```

Then open **http://localhost:8000** in your browser.

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

The Excel output includes:
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

## 💡 Model Selector

Switch LLM models globally from the UI, or configure per-step defaults in `.env`:

```env
DEFAULT_LLM_PROVIDER=gemini        # gemini | openai | anthropic | ollama
DEFAULT_LLM_MODEL=gemini-2.0-flash
```

---

## 🔐 LinkedIn Access

LinkedIn scraping works best with authentication. To use logged-in LinkedIn access:

1. Export your LinkedIn cookies (use a browser extension like "Cookie Editor")
2. Save as JSON to `data/linkedin_cookies.json`
3. Set the path in `.env`: `LINKEDIN_COOKIES_FILE=data/linkedin_cookies.json`

Without cookies, the agent uses public page data (may have limited access).

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
│   │   └── tools/               # LLM, browser, search, Excel tools
│   └── api/
│       ├── routes.py            # REST + WebSocket endpoints
│       └── models.py            # Pydantic schemas
├── frontend/
│   ├── index.html               # Single-page app
│   ├── app.js                   # Vue 3-style reactive frontend
│   └── style.css                # Glassmorphism dark theme
├── data/
│   └── pega_accounts.xlsx       # Pega partner/customer reference list
├── output/                      # Generated Excel reports
├── .env                         # API keys and configuration
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
| `GET` | `/api/research/{job_id}/download` | Download Excel output |
| `GET` | `/api/models` | List available LLM models |
| `GET` | `/api/jobs` | List all research jobs |
