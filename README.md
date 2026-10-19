# UNCLONE — Verified-Agent Badge

Customer-side agent that verifies the bank's agent on a live phone call,
every 6 seconds, before any money moves.

**Team:** Team 39 — Gokula  
**Track:** UNCLONE Track 3  
**Demo:** https://unclone-verified-agent.onrender.com  
**Source:** https://github.com/Lion4467cat/verified-agent-badge

---

## What it does

A customer gets a call that sounds exactly like their bank's agent — because
it can be a real-time clone. Caller ID is spoofable, the caller already knows
the customer's details, and "the bank never asks for X" fails when the caller
sounds like the bank.

This product sits on the customer's side and verifies the caller before the
customer approves anything. The demo runs staged call clips and a live mic
through the same pipeline: every 6-second slice is checked against the enrolled
bank agent's voice, with a deepfake check and app-side forensics/replay signals.

The badge is the decision:

- **Green — GO:** real agent voice, no machine parts. Call continues.
- **Amber — DOUBLE-CHECK:** can't be sure. Confirm the payment in the app.
- **Red — STOP:** a fake was caught. The call is cut and the payment blocked.

The red light is not just a warning. In the demo the audio stops mid-sentence
and the transaction flips to "payment blocked".

---

## What's in this repo

- `app/` — the FastAPI backend + static frontend for the live demo.
- `app/static/index.html` — the in-product demo page.
- `Team-39-Gokula-verified-agent-badge.pptx` — combined presentation
  (Day 1 + Day 2) built for this submission.
- `screenshots/` — slide screenshots of the combined deck.
- Judge-facing docs: `IMPACT.md`, `CALIBRATION.md`, `SCALE.md`, `SPEC.md`.

## Try it

Open https://unclone-verified-agent.onrender.com in a fresh tab — no login.
Then:

1. Click **Call 1 · Genuine agent** — green throughout, transaction proceeds.
2. Click **Call 2 · Mid-call hijack** — badge flips to HELD and the audio
   pauses when the hold lands.
3. Click **Call 3 · Subtle hijack** — identity passes, aggregate says "real",
   but one segment scores 0.999+ and the transaction is held. This is the case
   where an average-based policy would approve.
4. Use **Enrol my voice / Verify me now / Discrimination test** for unseen
   audio. If the mic is blocked, use the upload fallback — that's an intended
   design path, not a failure.

## Honest limits

- The live demo is a prototype. Microphone permissions are venue-dependent.
- The agent-to-agent handshake in the demo runs in one process for this
  submission; it is a live server attestation, not two independent services
  establishing mutual trust.
- Like any voice-verification system, it can miss out-of-domain TTS it was not
  trained on. That is why forensics and replay are layered, and why the honest
  posture is "the engine plus the policy", not "perfect detection".

## Built with

DetectifAI (speaker verification + deepfake detection), FastAPI, Python,
edge-tts (team-generated attacker voice), ffmpeg, Render, GitHub.

Submitted as part of the UNCLONE Track 3 project by Team 39 (Gokula).
