# app/main.py
import traceback
import logging
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.chat import router as chat_router
from app.api.v1.leads import router as leads_router
from app.api.v1.ui import router as ui_router
from app.core.config import settings

# Logging
logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))
log = logging.getLogger("uvicorn.error")
log.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))

# Get the static directory path
static_dir = Path(__file__).parent.parent / "static"

app = FastAPI(
    title="Strict RAG Chatbot API",
    version="0.1.0",
    debug=settings.DEBUG,
)

allowed_origins = settings.allowed_origins_list()
allow_all_origins = "*" in allowed_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins if allowed_origins else [],
    allow_credentials=not allow_all_origins,
    allow_methods=["*"],
    allow_headers=["*"],
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

# Include leads router on legacy and versioned paths.
# Some production gateways forward only /v1/*, so keep both.
app.include_router(leads_router, prefix="/submit-lead")
app.include_router(leads_router, prefix="/v1/submit-lead")

# Include the UI router
app.include_router(ui_router)

@app.get("/")
async def root():
    # Serve the index.html file at the root URL
    index_path = static_dir / "index.html"
    return FileResponse(index_path)


@app.get("/healthz")
async def healthz():
    return {"status": "ok", "env": settings.APP_ENV}
