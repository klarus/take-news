from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from dotenv import load_dotenv
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
load_dotenv()

from .routers.news import router as news_router

app = FastAPI(
    title="Take News API",
    description="Sintesi notizie multi-fonte con verifica AI",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(news_router)

STATIC_DIR = os.path.join(os.path.dirname(__file__), "..", "static")

gemini_key = os.getenv("GEMINI_API_KEY", "")
logger.info("GEMINI_API_KEY presente: %s", bool(gemini_key))


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
