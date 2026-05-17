# routers/video.py
import os
import uuid
import mimetypes
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict

from fastapi import APIRouter, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse, FileResponse

UPLOAD_DIR = Path("./temp_videos")
UPLOAD_DIR.mkdir(exist_ok=True)

# In a real app you might share metadata via a dependency or a store.
# For simplicity we keep metadata in a module‑level dict,
# but you could move it to a shared state object.
video_metadata: Dict[str, dict] = {}

MAX_FILE_SIZE = 200 * 1024 * 1024
ALLOWED_MIME_TYPES = {
    "video/mp4", "video/x-msvideo", "video/quicktime",
    "video/x-matroska", "video/webm", "video/mpeg",
}

router = APIRouter(tags=["videos"])

def cleanup_expired_videos(remove_files: bool = True):
    now = datetime.now(timezone.utc)
    expired = [fid for fid, m in video_metadata.items() if m["expires_at"] <= now]
    for fid in expired:
        meta = video_metadata.pop(fid, None)
        if meta and remove_files and meta["path"].exists():
            meta["path"].unlink()

def is_allowed_file(content_type: str, filename: str) -> bool:
    if content_type in ALLOWED_MIME_TYPES:
        return True
    mime_guess, _ = mimetypes.guess_type(filename)
    return mime_guess in ALLOWED_MIME_TYPES

# ---- Endpoints ----
@router.post("/api/upload-video")
async def upload_video(file: UploadFile = File(...)):
    content_type = file.content_type or ""
    if not is_allowed_file(content_type, file.filename):
        raise HTTPException(status_code=400, detail="Unsupported file type")

    file_data = bytearray()
    file_size = 0
    chunk_size = 1024 * 1024
    while chunk := await file.read(chunk_size):
        file_size += len(chunk)
        if file_size > MAX_FILE_SIZE:
            raise HTTPException(status_code=413, detail="File too large")
        file_data.extend(chunk)

    file_id = str(uuid.uuid4())
    ext = Path(file.filename).suffix
    safe_name = f"{file_id}{ext}"
    file_path = UPLOAD_DIR / safe_name
    file_path.write_bytes(file_data)

    expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
    video_metadata[file_id] = {
        "path": file_path,
        "expires_at": expires_at,
        "original_name": file.filename,
    }

    return JSONResponse({
        "success": True,
        "file_id": file_id,
        "expires_at": expires_at.isoformat(),
        "expires_in_seconds": int((expires_at - datetime.now(timezone.utc)).total_seconds()),
        "video_url": f"/video/{file_id}",
    })

@router.get("/api/videos")
async def list_active_videos():
    now = datetime.now(timezone.utc)
    active = []
    for fid, meta in video_metadata.items():
        if meta["expires_at"] > now:
            active.append({
                "file_id": fid,
                "expires_at": meta["expires_at"].isoformat(),
                "original_name": meta.get("original_name", "video"),
                "video_url": f"/video/{fid}",
            })
    active.sort(key=lambda x: x["expires_at"])
    return {"videos": active}

@router.get("/video/{file_id}")
async def serve_video(file_id: str):
    meta = video_metadata.get(file_id)
    if not meta:
        raise HTTPException(status_code=404, detail="Video not found")
    if meta["expires_at"] <= datetime.now(timezone.utc):
        cleanup_expired_videos(remove_files=True)
        raise HTTPException(status_code=410, detail="Video expired")
    path = meta["path"]
    if not path.exists():
        raise HTTPException(status_code=404, detail="File missing")
    media_type, _ = mimetypes.guess_type(str(path))
    return FileResponse(path=path, media_type=media_type or "video/mp4",
                        filename=meta.get("original_name", f"{file_id}.mp4"))

@router.delete("/api/delete-video/{file_id}")
async def delete_video(file_id: str):
    meta = video_metadata.pop(file_id, None)
    if not meta:
        raise HTTPException(status_code=404, detail="Video not found")
    if meta["path"].exists():
        meta["path"].unlink()
    return JSONResponse({"success": True, "message": "Video deleted"})