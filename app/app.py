"""UNCLONE Track 3 — verified-agent badge (Day 2).

FastAPI backend. The browser plays a staged call and verifies it in 6-second
windows; every window is a real DetectifAI verify + deepfake call. The
server-side policy turns the evidence into one action: proceed / step_up / hold.

Why windowed? DetectifAI has no streaming endpoint, so continuous checking is
an application-layer concern: slice the call, verify each slice, stitch the
2-second segment scores into one timeline. 6 s windows satisfy both API floors
(verify >= 3 s, deepfake > 4 s) and stay far inside the 30 ops/min budget.

Key handling: DETECTIF_API_KEY env var, or a file at ~/.detectif_key.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import pathlib
import secrets
import time
from datetime import datetime, timezone
from typing import Optional

import httpx
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.policy import PUBLIC as POLICY_PUBLIC, decide, worst

BASE_DIR = pathlib.Path(__file__).resolve().parent.parent  # unclone/
API_BASE = "https://platform.detectif.ai/v1"

MODEL_SPEAKER = {"name": "eidos", "version": "b2adcc85166a"}
MODEL_DEEPFAKE = {"name": "aletheia", "version": "2db8deca47bf"}

ATTEST_TTL_SECONDS = 300
VERDICT_TTL_SECONDS = 900

# Ephemeral per-process secret: session tokens are demo-lifetime artefacts.
SESSION_SECRET = os.environ.get("SESSION_SECRET") or secrets.token_hex(32)


def _load_key() -> str:
    key = os.environ.get("DETECTIF_API_KEY", "").strip()
    if key:
        return key
    keyfile = pathlib.Path.home() / ".detectif_key"
    if keyfile.is_file():
        return keyfile.read_text().strip()
    return ""


API_KEY = _load_key()

app = FastAPI(title="UNCLONE Track 3 — Verified-Agent Badge")


def _headers(idempotency: Optional[str]) -> dict:
    headers = {"Authorization": f"Bearer {API_KEY}"}
    if idempotency:
        headers["Idempotency-Key"] = idempotency
    return headers


def _error_payload(code: str, message: str, error_type: str = "upstream_error") -> dict:
    return {"error": {"type": error_type, "code": code, "message": message}}


# In-memory demo state: fresh verdicts for the handshake, single-use challenges.
_VERDICTS: dict[str, dict] = {}
_CHALLENGES: dict[str, float] = {}


def _prune(store: dict, ttl: int) -> None:
    now = time.time()
    for key, value in list(store.items()):
        ts = value["ts"] if isinstance(value, dict) else value
        if now - ts > ttl:
            store.pop(key, None)


def _remember_verdict(operation_id: str, payload: dict, speaker_id: str) -> None:
    _prune(_VERDICTS, VERDICT_TTL_SECONDS)
    _VERDICTS[operation_id] = {
        "ts": time.time(),
        "speaker_id": speaker_id,
        "policy": payload["policy"],
    }


def _fingerprint(speaker: dict) -> str:
    raw = "|".join(
        str(speaker.get(key))
        for key in ("speaker_id", "samples", "created_at", "updated_at")
    )
    return "sha256:" + hashlib.sha256(raw.encode()).hexdigest()[:20]


@app.get("/api/status")
async def status():
    """Small status endpoint the page polls: key present? credits? health?"""
    out = {
        "api_key_present": bool(API_KEY),
        "api_ok": False,
        "credits": None,
        "credits_available": None,
        "policy": POLICY_PUBLIC,
    }
    if not API_KEY:
        out["message"] = "DETECTIF_API_KEY not set — add ~/.detectif_key or export the env var."
        return out
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            health = await client.get(f"{API_BASE}/health", headers=_headers(None))
            out["api_ok"] = health.status_code == 200
            if health.status_code == 200:
                credits = await client.get(f"{API_BASE}/credits", headers=_headers(None))
                if credits.status_code == 200:
                    body = credits.json()
                    out["credits"] = body
                    out["credits_available"] = body.get("available")
    except Exception as exc:  # noqa: BLE001 - status must never raise
        out["message"] = f"Health check failed: {exc}"
    return out


@app.post("/api/enroll")
async def enroll(
    file: UploadFile = File(...),
    speaker_id: str = Form("bank_agent_1"),
):
    """Enroll the genuine agent voice (15–60 s clip, >=10 s of speech)."""
    if not API_KEY:
        raise HTTPException(status_code=503, detail="DETECTIF_API_KEY not set")
    data = await file.read()
    idem = "enroll-" + hashlib.sha256(data).hexdigest()[:32]
    async with httpx.AsyncClient(timeout=120) as client:
        response = await client.post(
            f"{API_BASE}/speakers/enroll",
            headers=_headers(idem),
            files={"file": (file.filename, data)},
            data={"speaker_id": speaker_id},
        )
    if response.status_code >= 500:
        return JSONResponse(
            status_code=503,
            content={
                "error": {"code": "upstream_busy", "message": "Enrollment upstream busy."},
                "retry_after": response.headers.get("Retry-After", "5"),
            },
        )
    return JSONResponse(status_code=response.status_code, content=response.json())


@app.post("/api/verify")
async def verify(
    file: UploadFile = File(...),
    speaker_id: str = Form("bank_agent_1"),
    detect_deepfake: bool = Form(True),
):
    """Verify one window of the call.

    Returns the DetectifAI payload verbatim plus a server-side ``policy``
    object. The page renders the policy; it never derives its own decision.
    """
    if not API_KEY:
        raise HTTPException(status_code=503, detail="DETECTIF_API_KEY not set")

    data = await file.read()
    if not data:
        payload = _error_payload("empty_file", "No audio was uploaded.")
        payload["policy"] = decide(payload)
        return JSONResponse(status_code=400, content=payload)

    idem = "verify-" + hashlib.sha256(data).hexdigest()[:32]
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                f"{API_BASE}/speakers/verify",
                headers=_headers(idem),
                files={"file": (file.filename, data)},
                data={
                    "speaker_id": speaker_id,
                    "detect_deepfake": str(detect_deepfake).lower(),
                },
            )
    except httpx.HTTPError as exc:
        payload = _error_payload(
            "upstream_unreachable", f"Could not reach DetectifAI: {exc}", "network_error"
        )
        payload["policy"] = decide(payload)
        return JSONResponse(status_code=502, content=payload)

    try:
        payload = response.json()
    except ValueError:
        payload = _error_payload(
            "invalid_upstream_response",
            response.text[:200] or "Upstream returned a non-JSON body.",
        )

    payload["policy"] = decide(payload)
    payload["upstream_status"] = response.status_code

    if response.status_code < 300:
        operation_id = payload.get("operation_id")
        if operation_id:
            _remember_verdict(operation_id, payload, speaker_id)
        return JSONResponse(status_code=200, content=payload)

    if response.status_code in (429, 503):
        payload["retry_after"] = response.headers.get("Retry-After", "5")
    return JSONResponse(status_code=response.status_code, content=payload)


@app.get("/api/attest")
async def attest(speaker_id: str = "bank_agent_1"):
    """Bank-agent attestation + single-use challenge for the mutual handshake."""
    if not API_KEY:
        raise HTTPException(status_code=503, detail="DETECTIF_API_KEY not set")
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(
                f"{API_BASE}/speakers/{speaker_id}", headers=_headers(None)
            )
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"DetectifAI unreachable: {exc}")

    if response.status_code != 200:
        return JSONResponse(
            status_code=404,
            content={
                "error": {"code": "speaker_not_found", "message": "Enroll the agent first."}
            },
        )

    speaker = response.json()
    _prune(_CHALLENGES, ATTEST_TTL_SECONDS)
    challenge = secrets.token_urlsafe(18)
    _CHALLENGES[challenge] = time.time()
    return {
        "speaker": speaker,
        "fingerprint": _fingerprint(speaker),
        "models": {"speaker": MODEL_SPEAKER, "deepfake": MODEL_DEEPFAKE},
        "challenge": challenge,
        "expires_in": ATTEST_TTL_SECONDS,
        "policy": POLICY_PUBLIC,
    }


@app.post("/api/handshake")
async def handshake(body: dict):
    """Complete the agent-to-agent attestation.

    Trust is issued only when *the server's own record* holds a fresh
    ``proceed`` verdict for a valid, unexpired challenge. The client cannot
    assert trust by itself.
    """
    challenge = str(body.get("challenge") or "")
    operation_id = str(body.get("operation_id") or "")

    issued = _CHALLENGES.get(challenge)
    if not issued or time.time() - issued > ATTEST_TTL_SECONDS:
        return JSONResponse(
            status_code=409,
            content={"mutual": False, "error": "challenge_expired"},
        )

    record = _VERDICTS.get(operation_id)
    if not record or record["policy"].get("action") != "proceed":
        return JSONResponse(
            status_code=409,
            content={"mutual": False, "error": "no_fresh_proceed_verdict"},
        )

    _CHALLENGES.pop(challenge, None)  # single use
    token = hmac.new(
        SESSION_SECRET.encode(),
        f"{challenge}|{operation_id}".encode(),
        hashlib.sha256,
    ).hexdigest()[:32]

    return {
        "mutual": True,
        "session_token": token,
        "expires_in": ATTEST_TTL_SECONDS,
        "verified_at": datetime.now(timezone.utc).isoformat(),
        "speaker_id": record["speaker_id"],
        "operation_id": operation_id,
        "policy": record["policy"],
    }


# Static page + local audio assets (agent lines, attacker clones, windows).
# mkdir first: git does not track empty dirs, so a fresh clone may lack them.
for _dir in (BASE_DIR / "app" / "audio", BASE_DIR / "app" / "static"):
    _dir.mkdir(parents=True, exist_ok=True)
app.mount("/audio", StaticFiles(directory=str(BASE_DIR / "app" / "audio")), name="audio")
app.mount("/", StaticFiles(directory=str(BASE_DIR / "app" / "static"), html=True), name="static")
