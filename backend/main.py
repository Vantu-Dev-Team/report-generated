"""
Sento Analytics Builder — FastAPI backend
Proxy to Ubidots API + HTML report generator
"""
import os
from fastapi import FastAPI, HTTPException, Request, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional
from dotenv import load_dotenv
from backend.ubidots import UbidotsService
import backend.db as db

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

app = FastAPI(title="Sento Analytics Builder")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

ubidots = UbidotsService()

ENV_TOKEN = os.getenv("UBIDOTS_TOKEN", "")


def get_token(x_ubidots_token: Optional[str] = Header(default=None)) -> str:
    """Read token from X-Ubidots-Token header, fall back to env var."""
    token = x_ubidots_token or ENV_TOKEN
    if not token:
        raise HTTPException(status_code=401, detail="No Ubidots token provided")
    return token


# ──────────────────────────────────────────
# Device endpoints
# ──────────────────────────────────────────

@app.get("/api/devices")
async def api_get_devices(
    page: int = 1,
    page_size: int = 50,
    search: str = "",
    x_ubidots_token: Optional[str] = Header(default=None),
):
    token = x_ubidots_token or ENV_TOKEN
    if not token:
        raise HTTPException(status_code=401, detail="No Ubidots token provided")
    return await ubidots.get_devices(token, page, page_size, search)


@app.get("/api/devices/{device_label}/variables")
async def api_get_variables(
    device_label: str,
    page: int = 1,
    page_size: int = 100,
    search: str = "",
    x_ubidots_token: Optional[str] = Header(default=None),
):
    token = x_ubidots_token or ENV_TOKEN
    if not token:
        raise HTTPException(status_code=401, detail="No Ubidots token provided")
    return await ubidots.get_variables(token, device_label, page, page_size, search)


# ──────────────────────────────────────────
# Data endpoints
# ──────────────────────────────────────────

class FetchValuesRequest(BaseModel):
    device_label: str
    var_label: str
    start_ms: int
    end_ms: int
    tz_offset: float = -5


@app.post("/api/data/values")
async def api_fetch_values(
    req: FetchValuesRequest,
    x_ubidots_token: Optional[str] = Header(default=None),
):
    token = x_ubidots_token or ENV_TOKEN
    if not token:
        raise HTTPException(status_code=401, detail="No Ubidots token provided")
    points = await ubidots.fetch_values_all_pages(
        token,
        req.device_label,
        req.var_label,
        req.start_ms,
        req.end_ms,
        req.tz_offset,
    )
    return {"points": points}


# ──────────────────────────────────────────
# Report generation
# ──────────────────────────────────────────

class GenerateRequest(BaseModel):
    config: dict
    components: list
    all_data: dict


@app.post("/api/generate")
async def api_generate(
    req: GenerateRequest,
    x_ubidots_token: Optional[str] = Header(default=None),
):
    html = ubidots.generate_html(req.config, req.components, req.all_data)
    return {"html": html}


# ──────────────────────────────────────────
# Saved configurations (DynamoDB / local)
# ──────────────────────────────────────────

class SaveConfigRequest(BaseModel):
    name: str
    config: dict
    components: list
    hist_rows: list = []


class UpdateConfigRequest(BaseModel):
    name: str
    config: dict
    components: list
    hist_rows: list = []


@app.get("/api/configs")
async def api_list_configs():
    items = db.list_configs()
    return {"items": items, "backend": db.storage_backend()}


@app.get("/api/configs/{config_id}")
async def api_get_config(config_id: str):
    item = db.get_config(config_id)
    if not item:
        raise HTTPException(status_code=404, detail="Config not found")
    return item


@app.post("/api/configs")
async def api_save_config(req: SaveConfigRequest):
    item = db.save_config(req.name, req.config, req.components, req.hist_rows)
    return item


@app.put("/api/configs/{config_id}")
async def api_update_config(config_id: str, req: UpdateConfigRequest):
    item = db.update_config(config_id, req.name, req.config, req.components, req.hist_rows)
    if not item:
        raise HTTPException(status_code=404, detail="Config not found")
    return item


@app.delete("/api/configs/{config_id}")
async def api_delete_config(config_id: str):
    ok = db.delete_config(config_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Config not found")
    return {"ok": True}


# ──────────────────────────────────────────
# Serve built React frontend
# ──────────────────────────────────────────
_DIST = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")
if os.path.isdir(_DIST):
    app.mount("/assets", StaticFiles(directory=os.path.join(_DIST, "assets")), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str):
        return FileResponse(os.path.join(_DIST, "index.html"))
