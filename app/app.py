"""UNCLONE Track 3 — high-value transaction confirmation agent.

FastAPI backend. The browser page plays staged call turns; each agent-line
audio blob is forwarded to DetectifAI verify (speaker match + deepfake check).
The API result drives the badge/decision: proceed or hold the transaction.

Key handling: DETECTIF_API_KEY env var, or a file at ~/.detectif_key.
"""
from __future__ import annotations

import os
import time
import uuid
import hashlib
import pathlib
from typing import Optional

import httpx
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

BASE_DIR = pathlib.Path(__file__).resolve().parent.parent  # unclone/
API_BASE = "https://platform.detectif.ai/v1"


def _load_key() -> str:
    key = os.environ.get("DETECTIF_API_KEY", "").strip()
    if key:
        return key
    keyfile = pathlib.Path.home() / ".detectif_key"
    if keyfile.is_file():
        return keyfile.read_text().strip()
    return ""


API_KEY = _load_key()

app = FastAPI(title="UNCLONE Track 3 — Transaction Confirmation Agent")


def _headers(idempotency: Optional[str]) -> dict:
    h = {"Authorization": f"Bearer {API_KEY}"}
    if idempotency:
        h["Idempotency-Key"] = idempotency
    return h


@app.get("/api/status")
async def status():
    """Small status endpoint the page polls: key present? credits? health?"""
    out = {"api_key_present": bool(API_KEY), "api_ok": False, "credits": None}
    if not API_KEY:
        out["message"] = "DETECTIF_API_KEY not set — add ~/.detectif_key or export the env var."
        return out
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            health = await client.get(f"{API_BASE}/health", headers=_headers(None))
            out["api_ok"] = health.status_code == 200
            if health.status_code == 200:
                try:
                    credits = await client.get(f"{API_BASE}/credits", headers=_headers(None))
                    if credits.status_code == 200:
                        out["credits"] = credits.json()
                except Exception:
                    pass
    except Exception as e:
        out["message"] = f"Health check failed: {e}"
    return out


@app.post("/api/enroll")
async def enroll(
    file: UploadFile = File(...),
    speaker_id: str = Form("bank_agent_1"),
):
    """Enroll the genuine agent voice (15–60 s clip, ≥10 s speech)."""
    if not API_KEY:
        raise HTTPException(status_code=503, detail="DETECTIF_API_KEY not set")
    data = await file.read()
    idem = "enroll-" + hashlib.sha256(data).hexdigest()[:32]
    async with httpx.AsyncClient(timeout=120) as client:
        r = await client.post(
            f"{API_BASE}/speakers/enroll",
            headers=_headers(idem),
            files={"file": (file.filename, data)},
            data={"speaker_id": speaker_id},
        )
    if r.status_code >= 500:
        # Busy/retryable: surface Retry-After so the UI can schedule it.
        retry_after = r.headers.get("Retry-After", "5")
        return JSONResponse(
            status_code=503,
            content={"error": "upstream_busy", "retry_after": retry_after},
        )
    return JSONResponse(status_code=r.status_code, content=r.json())


@app.post("/api/verify")
async def verify(
    file: UploadFile = File(...),
    speaker_id: str = Form("bank_agent_1"),
    detect_deepfake: bool = Form(True),
):
    """Verify one spoken turn: does it match the enrolled agent, and is it real?

    The result object is returned verbatim; the page maps it to
    green (match + real) / red (no_match or synthetic) / amber (error).
    """
    if not API_KEY:
        raise HTTPException(status_code=503, detail="DETECTIF_API_KEY not set")
    data = await file.read()
    idem = "verify-" + hashlib.sha256(data).hexdigest()[:32]
    async with httpx.AsyncClient(timeout=120) as client:
        r = await client.post(
            f"{API_BASE}/speakers/verify",
            headers=_headers(idem),
            files={"file": (file.filename, data)},
            data={"speaker_id": speaker_id, "detect_deepfake": str(detect_deepfake).lower()},
        )
    if r.status_code == 503 or r.status_code == 429:
        retry_after = r.headers.get("Retry-After", "5")
        return JSONResponse(
            status_code=503,
            content={"error": "upstream_busy", "retry_after": retry_after, "status": r.status_code},
        )
    return JSONResponse(status_code=r.status_code, content=r.json())


# Static page + local audio assets (agent lines, attacker clones).
# mkdir first: git does not track empty dirs, so a fresh clone may lack them.
for _d in (BASE_DIR / "app" / "audio", BASE_DIR / "app" / "static"):
    _d.mkdir(parents=True, exist_ok=True)
app.mount("/audio", StaticFiles(directory=str(BASE_DIR / "app" / "audio")), name="audio")
app.mount("/", StaticFiles(directory=str(BASE_DIR / "app" / "static"), html=True), name="static")
