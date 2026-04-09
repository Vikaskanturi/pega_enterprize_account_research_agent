"""API Routes — REST endpoints + WebSocket for real-time research progress."""
import uuid
import asyncio
import os
from typing import Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from dotenv import load_dotenv
load_dotenv(override=True)

from app.api.models import ResearchRequest, ResearchResult, ApiKeysConfig
from app.agent.orchestrator import run_research
from app.agent.tools.llm_tool import AVAILABLE_MODELS

router = APIRouter()

@router.get("/api/settings")
async def get_settings():
    """Return configured keys (masked) for the UI."""
    from dotenv import dotenv_values
    _env = dotenv_values()
    
    def mask(val):
        """Mask the key for the frontend so it's not fully exposed."""
        v = (val or "").strip()
        if len(v) > 8:
            return v[:4] + "*" * 12 + v[-4:]
        return "" if not v else "***"
        
    return {
        "gemini": mask(_env.get("GEMINI_API_KEY", "")),
        "openai": mask(_env.get("OPENAI_API_KEY", "")),
        "anthropic": mask(_env.get("ANTHROPIC_API_KEY", "")),
        "groq": mask(_env.get("GROQ_API_KEY", "")),
        "huggingface": mask(_env.get("HUGGINGFACE_API_KEY", "")),
        "serpapi": mask(_env.get("SERPAPI_KEY", "")),
        "tavily": mask(_env.get("TAVILY_API_KEY", "")),
    }

@router.post("/api/settings")
async def save_settings(config: ApiKeysConfig):
    """Save keys to the .env file and update environment."""
    env_file = ".env"
    
    # Read existing
    lines = []
    import os
    if os.path.exists(env_file):
        with open(env_file, "r") as f:
            lines = f.readlines()
            
    # Helper to replace or append
    def set_key(key_name, map_val):
        if map_val is None: return # Don't update if nothing passed
        if "***" in map_val: return # It's a masked key, so the user didn't change it
        
        found = False
        val = map_val.strip()
        for i, line in enumerate(lines):
            if line.startswith(f"{key_name}="):
                lines[i] = f"{key_name}={val}\n"
                found = True
                break
        if not found:
            # Drop a new line if it doesnt exist
            if lines and not lines[-1].endswith("\n"): lines[-1] += "\n"
            lines.append(f"{key_name}={val}\n")
            
        os.environ[key_name] = val # Immediately set it for the running process
        
    set_key("GEMINI_API_KEY", config.gemini)
    set_key("OPENAI_API_KEY", config.openai)
    set_key("ANTHROPIC_API_KEY", config.anthropic)
    set_key("GROQ_API_KEY", config.groq)
    set_key("HUGGINGFACE_API_KEY", config.huggingface)
    set_key("SERPAPI_KEY", config.serpapi)
    set_key("TAVILY_API_KEY", config.tavily)
    
    # Write back
    with open(env_file, "w") as f:
        f.writelines(lines)
        
    return {"status": "success", "message": "API keys saved to .env"}


# ── Health Check ──────────────────────────────────────────────────────────────

@router.get("/api/health")
async def health_check():
    """
    Live validation of all configured API keys and services.
    Returns a status for each integration so the UI can show users
    which features are available before they start a research run.
    """
    from dotenv import dotenv_values
    _env = dotenv_values()  # read directly from .env file, always fresh
    results = {}

    # ── Gemini ──────────────────────────────────────────────────────────────
    gemini_key = (_env.get("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY", "")).strip()
    if not gemini_key or gemini_key == "your_gemini_api_key_here":
        results["gemini"] = {"ok": False, "reason": "API key not set"}
    else:
        try:
            import google.generativeai as genai
            genai.configure(api_key=gemini_key)
            loop = asyncio.get_event_loop()
            def _test_gemini():
                model_id = os.getenv("DEFAULT_LLM_MODEL", "gemini-2.5-flash")
                model = genai.GenerativeModel(model_id)
                resp = model.generate_content("Reply with the single word: OK")
                return resp.text.strip()
            text = await asyncio.wait_for(loop.run_in_executor(None, _test_gemini), timeout=15)
            results["gemini"] = {"ok": True, "reason": f"Responded: {text[:30]}"}
        except Exception as e:
            results["gemini"] = {"ok": False, "reason": str(e)[:120]}

    # ── OpenAI ──────────────────────────────────────────────────────────────
    openai_key = (_env.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY", "")).strip()
    if not openai_key:
        results["openai"] = {"ok": False, "reason": "API key not set"}
    else:
        try:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=openai_key)
            resp = await asyncio.wait_for(
                client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": "Reply with the single word: OK"}],
                    max_tokens=5,
                ),
                timeout=15,
            )
            results["openai"] = {"ok": True, "reason": f"Responded: {resp.choices[0].message.content[:30]}"}
        except Exception as e:
            results["openai"] = {"ok": False, "reason": str(e)[:120]}

    # ── Anthropic ────────────────────────────────────────────────────────────
    anthropic_key = (_env.get("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_API_KEY", "")).strip()
    if not anthropic_key:
        results["anthropic"] = {"ok": False, "reason": "API key not set"}
    else:
        try:
            import anthropic
            client = anthropic.AsyncAnthropic(api_key=anthropic_key)
            resp = await asyncio.wait_for(
                client.messages.create(
                    model="claude-haiku-3-5",
                    messages=[{"role": "user", "content": "Reply with the single word: OK"}],
                    max_tokens=5,
                ),
                timeout=15,
            )
            results["anthropic"] = {"ok": True, "reason": f"Responded: {resp.content[0].text[:30]}"}
        except Exception as e:
            results["anthropic"] = {"ok": False, "reason": str(e)[:120]}

    # ── Groq ─────────────────────────────────────────────────────────────────
    groq_key = (_env.get("GROQ_API_KEY") or os.getenv("GROQ_API_KEY", "")).strip()
    if not groq_key:
        results["groq"] = {"ok": False, "reason": "API key not set"}
    else:
        try:
            from groq import AsyncGroq
            client = AsyncGroq(api_key=groq_key)
            resp = await asyncio.wait_for(
                client.chat.completions.create(
                    model="llama3-8b-8192",
                    messages=[{"role": "user", "content": "Reply with the single word: OK"}],
                    max_tokens=5,
                ),
                timeout=15,
            )
            results["groq"] = {"ok": True, "reason": f"Responded: {resp.choices[0].message.content[:30]}"}
        except Exception as e:
            results["groq"] = {"ok": False, "reason": str(e)[:120]}

    # ── Hugging Face ─────────────────────────────────────────────────────────
    hf_key = (_env.get("HUGGINGFACE_API_KEY") or os.getenv("HUGGINGFACE_API_KEY", "")).strip()
    if not hf_key:
        results["huggingface"] = {"ok": False, "reason": "API key not set"}
    else:
        try:
            from huggingface_hub import AsyncInferenceClient
            client = AsyncInferenceClient(token=hf_key)
            resp = await asyncio.wait_for(
                client.chat_completion(
                    model="meta-llama/Meta-Llama-3-8B-Instruct",
                    messages=[{"role": "user", "content": "Reply with the single word: OK"}],
                    max_tokens=5,
                ),
                timeout=15,
            )
            results["huggingface"] = {"ok": True, "reason": f"Responded: {resp.choices[0].message.content[:30]}"}
        except Exception as e:
            results["huggingface"] = {"ok": False, "reason": str(e)[:120]}

    # ── SerpAPI ──────────────────────────────────────────────────────────────
    serpapi_key = (_env.get("SERPAPI_KEY") or os.getenv("SERPAPI_KEY", "")).strip()
    if not serpapi_key:
        results["serpapi"] = {"ok": False, "reason": "API key not set"}
    else:
        try:
            import httpx
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    "https://serpapi.com/account",
                    params={"api_key": serpapi_key},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    searches_left = data.get("searches_left", "?")
                    results["serpapi"] = {"ok": True, "reason": f"Valid — {searches_left} searches remaining"}
                else:
                    results["serpapi"] = {"ok": False, "reason": f"HTTP {resp.status_code}: {resp.text[:80]}"}
        except Exception as e:
            results["serpapi"] = {"ok": False, "reason": str(e)[:120]}

    # ── Playwright Browser ───────────────────────────────────────────────────
    try:
        from app.agent.tools.browser_tool import get_browser
        browser = await asyncio.wait_for(get_browser(), timeout=10)
        results["browser"] = {"ok": True, "reason": "Playwright browser running"}
    except Exception as e:
        results["browser"] = {"ok": False, "reason": str(e)[:120]}

    overall_ok = results.get("gemini", {}).get("ok", False)  # Gemini is the primary dependency
    return {
        "status": "ready" if overall_ok else "degraded",
        "services": results,
    }

# In-memory job store (replace with Redis for production)
jobs: dict[str, dict] = {}


# ── WebSocket endpoint (real-time streaming) ──────────────────────────────────

@router.websocket("/ws/research")
async def websocket_research(websocket: WebSocket):
    """
    WebSocket endpoint for streaming research progress.
    Client sends: {"company_name": "...", "llm_model": "..."}
    Server emits step-by-step progress events.
    """
    await websocket.accept()
    try:
        data = await websocket.receive_json()
        company_name = data.get("company_name", "").strip()
        llm_model = data.get("llm_model", None)

        if not company_name:
            await websocket.send_json({"type": "error", "message": "company_name is required"})
            return

        job_id = str(uuid.uuid4())

        async def broadcast(event: dict):
            try:
                await websocket.send_json(event)
            except Exception:
                pass

        await websocket.send_json({"type": "job_id", "job_id": job_id})
        
        # Run research in a background task so we can cancel it
        research_task = asyncio.create_task(
            run_research(
                company_name=company_name,
                llm_model=llm_model,
                progress_callback=broadcast,
            )
        )

        # Listen for messages from client (like "stop")
        async def listen_for_stop():
            try:
                while True:
                    incoming = await websocket.receive_json()
                    if incoming.get("action") == "stop":
                        research_task.cancel()
                        break
            except Exception:
                research_task.cancel()

        listener_task = asyncio.create_task(listen_for_stop())

        try:
            state = await research_task
            jobs[job_id] = state.to_dict()
        except asyncio.CancelledError:
            await broadcast({"type": "fatal_error", "message": "Research manually stopped by user."})
            # Also update jobs dict if we want history
            jobs[job_id] = {"status": "cancelled", "company_name": company_name}
        finally:
            listener_task.cancel()

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_json({"type": "fatal_error", "message": str(e)})
        except Exception:
            pass


# ── REST API ──────────────────────────────────────────────────────────────────

@router.post("/api/research/start")
async def start_research(req: ResearchRequest, background_tasks: BackgroundTasks):
    """Start a research job in the background. Returns a job_id to poll."""
    job_id = str(uuid.uuid4())
    jobs[job_id] = {"status": "queued", "company_name": req.company_name}

    async def _run():
        jobs[job_id]["status"] = "running"
        try:
            state = await run_research(company_name=req.company_name, llm_model=req.llm_model)
            jobs[job_id] = {"status": "complete", **state.to_dict()}
        except Exception as e:
            jobs[job_id] = {"status": "error", "error": str(e)}

    background_tasks.add_task(_run)
    return {"job_id": job_id, "status": "queued"}


@router.get("/api/research/{job_id}")
async def get_research(job_id: str):
    """Get the current status and results of a research job."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    return jobs[job_id]


MASTER_EXCEL_PATH = "output/research_results.xlsx"


@router.post("/api/export")
async def export_excel_from_state(payload: dict):
    """
    Upsert the provided research state into the single shared master Excel file
    (output/research_results.xlsx) and serve it as a download.
    - If the file does not exist it is created fresh.
    - If a row for the same company already exists it is updated in-place.
    - Otherwise a new row is appended.
    """
    import os
    from app.agent.tools.excel_tool import upsert_to_master_excel

    columns = payload.get("columns", {})

    if not columns:
        raise HTTPException(status_code=400, detail="No research data provided to export.")

    os.makedirs("output", exist_ok=True)
    upsert_to_master_excel(columns, output_path=MASTER_EXCEL_PATH)

    filename = "pega_research_results.xlsx"
    return FileResponse(
        path=MASTER_EXCEL_PATH,
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
        },
    )


@router.post("/api/save_local")
async def save_local_master_excel(payload: dict):
    """
    Upsert the current research data into the single shared master Excel file
    (output/research_results.xlsx).  Creates the file if it doesn't exist.
    """
    import os
    from app.agent.tools.excel_tool import upsert_to_master_excel
    columns = payload.get("columns", {})
    if not columns:
        raise HTTPException(status_code=400, detail="No research data provided to save.")

    os.makedirs("output", exist_ok=True)
    try:
        path = upsert_to_master_excel(columns, output_path=MASTER_EXCEL_PATH)
        return {"status": "success", "message": f"Saved to master file: {path}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save: {str(e)}")


@router.get("/api/download")
async def download_master_excel():
    """
    Serve the single shared master Excel file as a download.
    Returns 404 if no research has been run yet.
    """
    import os
    if not os.path.exists(MASTER_EXCEL_PATH):
        raise HTTPException(status_code=404, detail="No research results file found yet.")

    return FileResponse(
        path=MASTER_EXCEL_PATH,
        filename="pega_research_results.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": 'attachment; filename="pega_research_results.xlsx"',
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
        },
    )


@router.get("/api/research/{job_id}/download/pega_research_results.xlsx")
async def download_excel(job_id: str):
    """Download the Excel output for a completed research job."""
    import os
    output_path = "output/research_results.xlsx"
    if not os.path.exists(output_path):
        raise HTTPException(status_code=404, detail="Excel file not yet generated")

    if job_id == "latest" or not job_id or len(job_id) < 5:
        down_name = "pega_research_results.xlsx"
    else:
        short_id = str(job_id)[:8]
        down_name = f"pega_research_{short_id}.xlsx"

    return FileResponse(
        path=output_path,
        filename=down_name,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="{down_name}"',
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
        },
    )



@router.get("/api/models")
async def list_models():
    """Return available LLM models for the model selector UI."""
    return {"models": AVAILABLE_MODELS}


@router.get("/api/jobs")
async def list_jobs():
    """List all research jobs (summary view)."""
    summary = []
    for job_id, data in jobs.items():
        summary.append({
            "job_id": job_id,
            "company_name": data.get("company_name", ""),
            "status": data.get("status", "unknown"),
            "completed": data.get("completed", False),
            "enterprise_type": data.get("columns", {}).get("Enterprise Type", ""),
            "started_at": data.get("started_at", ""),
        })
    return {"jobs": summary}


@router.delete("/api/jobs/{job_id}")
async def delete_job(job_id: str):
    """Remove a job from the store."""
    jobs.pop(job_id, None)
    return {"deleted": job_id}


# ── LM Studio Proxies ────────────────────────────────────────────────────────
import httpx

@router.get("/api/lmstudio/models")
async def get_lmstudio_models():
    try:
        hosts = ["http://127.0.0.1:1234", "http://192.168.56.1:1234"]
        async with httpx.AsyncClient(timeout=5) as client:
            for host in hosts:
                try:
                    resp = await client.get(f"{host}/api/v1/models")
                    if resp.status_code == 200: return resp.json()
                except Exception:
                    pass
                try:
                    resp = await client.get(f"{host}/v1/models")
                    if resp.status_code == 200: return resp.json()
                except Exception:
                    pass
            return {"error": "Could not connect to LM Studio on any known host."}
    except Exception as e:
        return {"error": str(e)}

@router.post("/api/lmstudio/load")
async def load_lmstudio_model(data: dict):
    try:
        hosts = ["http://127.0.0.1:1234", "http://192.168.56.1:1234"]
        async with httpx.AsyncClient(timeout=60) as client:
            for host in hosts:
                try:
                    resp = await client.post(f"{host}/api/v1/models/load", json=data)
                    return resp.json()
                except Exception:
                    pass
            return {"error": "Could not connect to LM Studio."}
    except Exception as e:
        return {"error": str(e)}
