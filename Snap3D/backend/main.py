import os
import sys
import json
import uuid
import time
import logging
import asyncio
from pathlib import Path
from typing import Dict

from fastapi import FastAPI, UploadFile, File, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

# Add parent so tsr module is importable, and backend dir for local imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))

from triposr_pipeline import load_model, process_image

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Snap3D API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "outputs")
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# WebSocket connections
ws_connections: Dict[str, WebSocket] = {}


@app.on_event("startup")
async def startup_event():
    logger.info("Preloading TripoSR model...")
    load_model()
    logger.info("Model preloaded. Server ready.")


@app.get("/health")
async def health():
    return {"status": "ok", "service": "Snap3D"}


@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await websocket.accept()
    ws_connections[client_id] = websocket
    logger.info(f"WebSocket connected: {client_id}")
    try:
        while True:
            # Keep alive - wait for messages
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
    except WebSocketDisconnect:
        ws_connections.pop(client_id, None)
        logger.info(f"WebSocket disconnected: {client_id}")


async def send_ws_progress(client_id: str, stage: str, progress: int, message: str):
    ws = ws_connections.get(client_id)
    if ws:
        try:
            await ws.send_text(
                json.dumps(
                    {
                        "type": "progress",
                        "stage": stage,
                        "progress": progress,
                        "message": message,
                    }
                )
            )
        except Exception:
            ws_connections.pop(client_id, None)


@app.post("/upload")
async def upload_image(file: UploadFile = File(...), client_id: str = ""):
    job_id = str(uuid.uuid4())[:8]
    timestamp = int(time.time())
    filename = f"{timestamp}_{job_id}"

    # Save uploaded file
    ext = os.path.splitext(file.filename or "image.png")[1] or ".png"
    upload_path = os.path.join(UPLOAD_DIR, f"{filename}{ext}")

    contents = await file.read()
    with open(upload_path, "wb") as f:
        f.write(contents)

    await send_ws_progress(client_id, "uploading", 5, "Image uploaded successfully")

    # Run processing in executor to not block event loop
    loop = asyncio.get_event_loop()

    def progress_callback(stage: str, progress: int, message: str):
        asyncio.run_coroutine_threadsafe(
            send_ws_progress(client_id, stage, progress, message), loop
        )

    try:
        result = await loop.run_in_executor(
            None, process_image, upload_path, OUTPUT_DIR, progress_callback
        )
    except Exception as e:
        logger.error(f"Processing failed: {e}")
        await send_ws_progress(client_id, "error", 0, str(e))
        return JSONResponse(
            status_code=500,
            content={"error": f"Processing failed: {str(e)}"},
        )

    model_basename = os.path.basename(result["model_path"])
    preview_basename = os.path.basename(result["preview_path"])

    await send_ws_progress(client_id, "done", 100, "3D model ready!")

    return {
        "model_url": f"/models/{model_basename}",
        "preview_url": f"/previews/{preview_basename}",
        "job_id": job_id,
        "vertices": result["vertices"],
        "faces": result["faces"],
        "file_size": result["file_size"],
        "filename": model_basename,
        "created_at": timestamp,
    }


@app.get("/models/list")
async def list_models():
    models = []
    if os.path.exists(OUTPUT_DIR):
        for f in os.listdir(OUTPUT_DIR):
            if f.endswith(".glb"):
                file_path = os.path.join(OUTPUT_DIR, f)
                stat = os.stat(file_path)
                base = os.path.splitext(f)[0]
                preview = f"{base}_preview.png"
                preview_exists = os.path.exists(os.path.join(OUTPUT_DIR, preview))
                models.append(
                    {
                        "filename": f,
                        "model_url": f"/models/{f}",
                        "preview_url": f"/previews/{preview}" if preview_exists else None,
                        "file_size": stat.st_size,
                        "created_at": int(stat.st_mtime),
                    }
                )
    models.sort(key=lambda m: m["created_at"], reverse=True)
    return {"models": models}


@app.get("/models/{filename}")
async def get_model(filename: str):
    # Sanitize filename to prevent path traversal
    safe_name = os.path.basename(filename)
    file_path = os.path.join(OUTPUT_DIR, safe_name)
    if not os.path.exists(file_path):
        return JSONResponse(status_code=404, content={"error": "Model not found"})
    # No Content-Disposition attachment — inline serving is required for GLTFLoader
    return FileResponse(
        file_path,
        media_type="model/gltf-binary",
        headers={"Cache-Control": "public, max-age=86400"},
    )


@app.get("/previews/{filename}")
async def get_preview(filename: str):
    safe_name = os.path.basename(filename)
    file_path = os.path.join(OUTPUT_DIR, safe_name)
    if not os.path.exists(file_path):
        return JSONResponse(status_code=404, content={"error": "Preview not found"})
    return FileResponse(file_path, media_type="image/png")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)
