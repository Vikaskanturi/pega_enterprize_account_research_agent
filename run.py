"""
Simple run script — use this to launch the application.
Usage: python run.py
"""
import sys
import os
import uvicorn
from dotenv import load_dotenv

# Force UTF-8 output to avoid UnicodeEncodeError on Windows
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        os.environ['PYTHONUTF8'] = '1'

load_dotenv()

if __name__ == "__main__":
    port = int(os.getenv('APP_PORT', '8000'))
    host = os.getenv('APP_HOST', '0.0.0.0')
    model = f"{os.getenv('DEFAULT_LLM_PROVIDER', 'gemini')} / {os.getenv('DEFAULT_LLM_MODEL', 'gemini-2.0-flash')}"

    print("Pega Enterprise Account Research Agent")
    print("=" * 42)
    print(f"   URL: http://localhost:{port}")
    print(f"   LLM: {model}")
    print("   Press Ctrl+C to stop\n")

    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=False,
        log_level=os.getenv("LOG_LEVEL", "info"),
    )
