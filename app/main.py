# app/main.py
import traceback
import logging
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.v1.chat import router as chat_router
from app.api.v1.leads import router as leads_router  # ✅ NEW IMPORT

# Enable detailed logging
logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger("uvicorn.error")
log.setLevel(logging.DEBUG)

# Get the static directory path
static_dir = Path(__file__).parent.parent / "static"

app = FastAPI(
    title="Strict RAG Chatbot API",
    version="0.1.0",
    debug=True,  # Enable debug mode
)

# Serve static files from the "static" directory
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Add middleware to catch and print ALL errors
@app.middleware("http")
async def catch_exceptions_middleware(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception:
        # Print full traceback to terminal
        print("🚨 ERROR TRACEBACK:")
        traceback.print_exc()
        raise

# Include the chat router
app.include_router(chat_router)

# Include the leads router (no prefix so /submit-lead works directly)
app.include_router(leads_router)  # ✅ NEW ROUTER

@app.get("/")
async def root():
    # Serve the index.html file at the root URL
    index_path = static_dir / "index.html"
    return FileResponse(index_path)
