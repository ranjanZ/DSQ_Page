# main.py
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from routers import video, nifty500, info, partners   # import all routers

# Ensure required directories exist
Path("templates").mkdir(exist_ok=True)
Path("static").mkdir(exist_ok=True)
Path("temp_videos").mkdir(exist_ok=True)

templates = Jinja2Templates(directory="templates")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Clean expired videos on startup
    video.cleanup_expired_videos(remove_files=True)

    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        video.cleanup_expired_videos,
        trigger=IntervalTrigger(seconds=60),
        kwargs={"remove_files": True},
    )
    scheduler.start()
    yield
    scheduler.shutdown()

app = FastAPI(
    title="Dalal Street Quants",
    description="Algorithmic trading strategies, quant research, and temporary video sharing.",
    version="1.0.0",
    lifespan=lifespan,
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Include all modular routers
app.include_router(video.router)
app.include_router(nifty500.router)
app.include_router(info.router)        # if present
app.include_router(partners.router)    # if present

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)