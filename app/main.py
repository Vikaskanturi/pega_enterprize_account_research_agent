"""
Main FastAPI application entry point.
"""
import os
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from dotenv import load_dotenv

load_dotenv()

from app.api.routes import router
from app.agent.tools.browser_tool import get_browser, close_browser


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Pre-launch browser
    try:
        await get_browser()
        print("✅ Browser initialized")
    except Exception as e:
        print(f"⚠️  Browser init failed (will retry on first use): {e}")
    yield
    # Cleanup
    await close_browser()
    print("🛑 Browser closed")


app = FastAPI(
    title="Pega Enterprise Account Research Agent",
    description="AI-powered B2B sales account research for Pega opportunities",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow frontend to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes
app.include_router(router)

# Serve frontend static files
frontend_path = Path(__file__).parent.parent / "frontend"
if frontend_path.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_path)), name="static")

    @app.get("/")
    async def serve_frontend():
        return FileResponse(str(frontend_path / "index.html"))

    @app.get("/{path:path}")
    async def serve_spa(path: str):
        file = frontend_path / path
        if file.exists() and file.is_file():
            return FileResponse(str(file))
        return FileResponse(str(frontend_path / "index.html"))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=os.getenv("APP_HOST", "0.0.0.0"),
        port=int(os.getenv("APP_PORT", "8000")),
        reload=True,
        log_level=os.getenv("LOG_LEVEL", "info"),
    )
