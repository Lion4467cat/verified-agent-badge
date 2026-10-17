# Rehearsal pack & demo script — Verified-Agent Badge

_Link: https://unclone-verified-agent.onrender.com · open in a fresh tab, nothing to log in to._
_Total demo length: 4 minutes 30 seconds. Practise twice with a stopwatch; if you cannot
land inside 5:30 with margin, cut the Edge-case button from Script 2, never the live mic._
_Presented as part of the preparation flow on 2026-10-17._

---

## 0. Before the room fills (10 min, one person owns this)

| # | Do | Check |
|---|---|---|
| 1 | Open the link on the presentation laptop **and** on a phone hotspot | badge "DetectifAI reachable" green, file:'fresh 0/12', no spinners |
| 2 | Click Call 1 once | everything green, transactions shows "PROCEEDS" |
| 3 | Click the handshake once | trust strip turns green |
| 4 | Press Win+Shift+R / Cmd+Shift+R after the warm click so the run starts on a clean page | page loads fast (Render is warm now — never present on a cold first load) |
| 5 | If hotspot > deployment > Wi-Fi: whichever loads the page in <5 s wins | keep the losing one as backup, don't switch mid-demo |

If the site is totally unreachable: `stream run: local fallback http://127.0.0.1:8787/`
from the repo laptop (uvicorn must be running there; the demo controller knows how).

---

## 1. The 4:30 script (who says what, second by second)

**Presenter 0:00–0:25 — frame the scene (no clicking yet)**
> "A customer gets a call about a ₹86,499 payment. The caller sounds exactly like the bank's agent — because it *is* a clone. Caller ID is spoofed, KYC answers are stolen, and 'the bank never asks that' fails because a cloned agent doesn't need to ask. Our product is on the *customer's* side: it verifies the bank's agent before any money moves."

**Presenter 1: 0:25–1:15 — Call 1, the genuine case (click Call 1)**
> "This call is genuine. Watch the timeline — each coloured block is a 6-second window of real audio being checked."
(The three blocks go green one by one; badge shows VERIFIED, the txn card flips to PROCEEDS / payment released.)
> "Voice matched with margin, every segment real. The badge is green, the transaction is released. Every claim I just made is a number in the raw JSON under each window — open one if you like."

**Presenter 2: 1:15–2:10 — Call 2, the mid-call hijack (click Call 2)**
> "Same bank agent starts the call… and halfway through, the voice is swapped for a clone."
(At the 6 s mark the block turns red; badge flips to HELD; **the audio stops playing**; txn card: payment blocked · agent call terminated.)
> "The check caught the mismatch before the customer read out anything. And notice — the app didn't just show a warning. It **terminated the call and blocked the payment**. The transaction API records the full handoff. That's the difference between a dashboard and a decision."

**Presenter 1: 2:10–3:00 — Call 3, the aggregate-blind case (the marks beat)**
> "Here's the hardest attack for any voice-verification system, including ours. The *identity* check passes — 0.767 similarity. The *whole-call* deepfake score says 'real'. Any system that averages its evidence over the call would approve this. But look at the strip: between seconds 9 and 13 the segment score is 0.999 — synthetic. Our policy acts on the **worst 4 seconds**, not the average. Transaction held."
(Point at the segment strip while talking; this slide is worth rubbing into the judges' memory.)

**Presenter 2: 3:00–3:40 — THE LIVE MOMENT (the piece every judge remembers)**
> "Two of our judges have asked — everything so far is staged clips. So here's unseen audio: one of us, right now." Press **Enrol my voice**; speak for the full 20 s — read something natural, don't whisper, don't fill the pause with silence.
> Press **Verify me now**. The check is against **your own enrolment** (created in step 1), so on a clean mic expect **green PROCEED**; a noisy room may give amber — narrate whichever appears honestly:
> "We enrolled my voice as its own reference — exactly how the bank enrols its agent. It recognises me."
> Press **Discrimination test** (the impostor clip against your own enrolment). Expect **red HOLD**:
> "A stranger's clip against my enrolment is held. Accept-me + reject-a-stranger in one session is the proof this isn't a rubber stamp."

**Presenter 1: 3:40–4:10 — Edge case + one number (click Silent line)**
> "No evidence should never mean no decision. A silent line is treated as *unverifiable*, and we fail **closed** — the badge steps up, never approves. Same for API failures and re-sent audio: the system has a ladder and every rung is safe." Then one number:
> "At realistic prevalence we screen *flagged* traffic, precision ≈ 52% — one false step-up per real catch — at about $42 per fraud caught ($60 per prevented), a ≈13× return against the $800 median consumer loss per imposter-scam incident (FTC 2024 Data Book)."

**Presenter 2: 4:10–4:30 — close on the architecture, hand to questions**
> "DetectifAI is the engine. The product is the policy around it — the action ladder, the replay and forensics signals, the audited transaction — which is what a bank buys and what our Impact, Calibration and Scale pages in the top banner evidence. Questions?"

---

## 2. Failure playbook — each recovery ≤ 10 seconds, rehearsed

| What goes wrong | On-screen sign | Who speaks (line) | Who does (action) |
|---|---|---|---|
| **Cold start / slow page** | spinner on "checking API" | P2: "While it warms: our policy runs on the worst segment of a call, which metric is that? — it's the max deepfake score per 4-second window." | P1 keeps refresh going; never present on page 1 |
| **Render unreachable entirely** | browser error | P2: "Also have this locally —" | P1 opens the local fallback URL; the demo proceeds identically |
| **Mic permission denied** | amber "MIC BLOCKED — allow it, or use Upload a clip" | P2: "The judge's environment has our upload fallback — exactly what we designed." | P1 clicks **Fallback · upload a clip**, picks any audio file from the desktop, presses run — the flow continues through the same pipeline |
| **API returns 503 / rate-limit** | badge goes amber RETRYING, count-down | P2: "The vendor is rate-limiting us — the policy's already showing: partial evidence can't approve, so it's stepping up until the retry clears." | P1 waits; when the block returns green, resume; if after retry ×2 it's still bad and the room is impatient: P2: "we've documented the retry ladder in calibration" — P1 moves on to the live-mic beat (which is independent of the rate limit) |
| **Judge's mic is noisy / enrolment fails to match** | amber again after step 2 | P2: "That's the margin rule again — the recording quality was below our auto-approve score, which is exactly what saves customers in a bad phone line." | Never argue; tie it to the product. This is a *feature* of fail-closed. |
| **Site appears fully down** | nothing loads | P2 (stays standing, never looks rattled): "'Load' for us means the cloud demo *or* the local mirror — same code." | P1 to local fallback, laptop already on the table |

Golden rule: **whoever's talking never stops talking.** The moving piece is the other
presenter's. If the demo fails technically, thebackup is *narrating the segment-strip*
slide 3 diagram by hand: "identity passed, aggregate said real, one segment = 0.999" is
the story even rendered as a static picture.

---

## 3. Reserved questions the judges like to pick (prep these answers aloud)

| Q | Answer in ≤ 15 seconds |
|---|---|
| How do you get the training data? | "We don't train. Enrolment is 15–60 s of the bank's *own* agent's voice — the bank already records compliance calls. No corpus, no cold start. The runbook's on our Scale page." |
| Why would a bank pay for *my* side of the call? | "Because the verifier is the *customer's* control, not the contact-centre's. It's the only thing that protects against a *perfect* clone of their own agent." |
| What if I speak with a cold / the mic is bad? | "Then it steps up instead of approving. We never gate the money on one noisy signal — the ladder is designed for exactly that." |
| Is this really 'streaming'? | "Continuous *windowed* verification — DetectifAI has no streaming endpoint, and we say so honestly. Six-second windows, verified live while the call plays." |
| What can't it catch? | "Out-of-domain TTS it wasn't trained on — we say so in calibration. That's why forensics and replay are layered, and why the honest posture is 'the engine + the policy', not 'perfect detection'." |

---

## 4. Ownership

| Beat | Owner (write in) |
|---|---|
| Slides 1–2 narration | ____________ |
| Call 1/3 live demo + live-mic section | ____________ |
| Call 2 live demo + edge case | ____________ |
| Numbers (impact / latency / cost) | ____________ |
| Failure playbook owner (never narrates) | ____________ |
| Q&A first-responder | ____________ |
