# UNCLONE Day 2 — adversarial audit, pessimistic scoring, full-marks spec

_Read-only audit, 2026-10-17. **No code was changed.** Evidence is file/line references and live probes, not claims._

---

## 0. Verdict

| | Score |
|---|---|
| **Pessimistic rubric score** | **46 / 70** |
| SPEC | 5.5 / 10 |
| DESIGN | 5.0 / 10 |
| CORRECTNESS | 6.0 / 10 |
| QUALITY | 5.0 / 10 |

**One sentence:** the *detection logic* is genuinely strong; the *product* around it is a staged recording player. There is no bank agent, no user-side agent, no live audio path, and no action in any system.

**What full marks requires:** convert the harness into a **live two-agent loop with a real action**, and move Impact and Scale from assertion to evidence. Everything else is polish.

---

## 1. "How does this work live?" — answered plainly

You are right to be uneasy. Here is the actual data path, end to end:

```
button click                      index.html: run(id)
  → new Audio("/audio/call_genuine.mp3")     ← a file on disk, served by StaticFiles
  → for each window: fetch("/audio/chunks/genuine_0.wav")   ← more files on disk
  → POST /api/verify                         app/app.py:verify  (a proxy)
  → DetectifAI POST /v1/speakers/verify
  → decide(payload) → policy                 app/policy.py
  → badge text + #decision innerHTML         index.html:169 — an empty <div>
```

### Where is the actual bank agent?

**There isn't one.** The "bank agent" is `app/audio/agent_turn_1.mp3` — a teammate reading a script, recorded yesterday, looped to 18 seconds. No process decides to call anyone, generates a line, speaks, listens, or acts.

### Where is our agent that does something?

**There isn't one either.** "Our agent" is a `for` loop in a browser tab:

```js
for (let i = 0; i < s.windows.length; i++) { ... const res = await verifyWindow(w.src, i, my); ... }
```

No goal, no tools, no memory, no action. The "transaction decision" is `decision.innerHTML = "<b>Transaction HELD.</b>"` — text in a `<div>`. Nothing is blocked, because nothing exists to block.

### Proof (grep, not opinion)

| Primitive | Occurrences in `app/` |
|---|---|
| `getUserMedia` (mic capture) | **0** |
| `MediaRecorder` (live chunking) | **0** |
| `RTCPeerConnection` / `WebSocket` (a call) | **0** |
| `SpeechSynthesis` (an agent that speaks) | **0** |
| Any LLM / tool call / agent loop | **0** |
| A transaction object with state | **0** |

### Why this costs marks

- **DetectifAI (20).** The rubric asks whether DetectifAI is "the engine of the product, end to end." Today it is the engine of a *classifier*, wrapped in a demo harness. A hostile judge: *"show me this on audio that isn't already on your disk."*
- **Working prototype (10).** "Core flow runs live in front of judges." The API calls are live; **the call is not.** A judge cannot speak, cannot upload, cannot break it.
- **Demo (10).** Four buttons is a slide with a play button. It survives questions only if nobody asks to try it.
- **Perception bug.** The deployed `/api/verify` returns `idempotent_replay: true, charged: 0` for every demo run. Honest — but a judge reading the raw JSON (which we invite, via the "DetectifAI response (raw)" disclosure) sees the words *replay* and *0 credits* and concludes *pre-recorded*.

### What "live" must actually mean — three levels

| Level | What it is | What it proves | Effort | Risk |
|---|---|---|---|---|
| **L1 — live input** | Browser mic → 6 s windows → same pipeline. Judge speaks; the badge reacts. | The pipeline works on **unseen** audio. Kills the "pre-recorded" objection outright. | 2–3 h | Low (permissions, venue noise) |
| **L2 — live two-agent call** | A real call between a **bank agent** (LLM + TTS, server-side) and a **user-side verifier agent** that taps the call audio, verifies each window, and **acts** (warns, mutes, holds, escalates). Attacker injects a cloned voice mid-call. | There *is* an agent that does something, and DetectifAI drives its action. | 6–10 h | Medium (WebRTC/audio plumbing) |
| **L3 — telephony** | Twilio/Telnyx media stream; the user-side agent joins as a monitor; STIR/SHAKEN + carrier metadata. | The real product. | Days + cost | High |

**Recommendation for a 3–6 h finals window: L1 + a minimal L2.** Concretely:

1. **L1 mic mode** — `getUserMedia` → `MediaRecorder` 6 s chunks → existing `/api/verify`. Add a "🎙 Verify my voice" button that enrolls the judge's voice (`/api/enroll`) and then verifies live windows against it. Takes minutes to add, and it is the single most persuasive thing in the room.
2. **A real action** — give the backend a transaction object (`pending → verified | held | step_up`), have `/api/verify` transitions write to it, and have the "bank agent" (TTS) *stop talking* when the state flips to `held`. Then the decision is not text; it is an effect.
3. **A fresh-run path** — add a per-run nonce to the audio (e.g., prepend 0.2 s of silence generated at request time) or expose a "live, uncached" mode so the raw JSON shows `idempotent_replay: false` and `charged: 100`. That single line in the payload is worth marks.

---

## 2. Pessimistic rubric score

| Criterion | Max | Ours | A hostile judge says | What full marks needs |
|---|---|---|---|---|
| **DetectifAI integration** | 20 | **15** | "Real depth on thresholds and segments — but it's one API call on a stored file. Take the file away and there's nothing to verify." | Live audio path; fresh (non-replay) runs; explicit calibration; a second signal layer so depth is architectural, not just thresholding. |
| **Working prototype** | 10 | **7** | "Four buttons. No judge input, no way to break it, no action. And the raw JSON says *replay*." | Unseen input handled live; a genuine and a fake produced **during** the demo; a real state change. |
| **Problem & user insight** | 10 | **7** | "Good story, but it's inherited from Day 1. Where is the registration artifact? Any user evidence at all?" | The registered use case on screen; 3–5 interviews or public incident data mapped onto the exact workflow. |
| **Impact** | 10 | **5** | "10,000 checks is a cost ratio, not an impact. How many frauds, how much money?" | Incidence × loss × detection × intervention, with a money number and named assumptions. |
| **Scale & viability** | 10 | **5** | "Who buys a *user-side* verifier? The bank whose agent is being cloned? The channel conflict isn't answered, and a bank cannot deploy an unvalidated model." | Buyer + channel logic resolved; model-risk validation package; a named pilot design. |
| **Demo & communication** | 10 | **7** | "Dense slide, one narrator, no rehearsal, no failure path." | Rehearsed, one owner per section, live-failure fallback, every member answers. |
| **Total** | **70** | **46** | | **70** |

**Note on honesty of the score:** 46 is deliberately below where a friendly judge would land (I would guess 54–58 in the room). The gap between those two numbers *is* the demo risk: everything that could collapse under a skeptical question.

---

## 3. Four-dimension audit

### SPEC — 5.5 / 10

Judged against the request: *a prototype that demonstrates the idea, implements the scaling points, and is aimed at full marks.*

- **Not delivered:** an agent that does something. This is the core of the ask and it is absent (§1).
- **Scale point 2 is theatre.** `Attest` + `handshake` is one process attesting to itself: `_VERDICTS` (app.py:72) and `_CHALLENGES` (app.py:73) are in-memory dicts in the *same* service that answers the verify call. There is no second party, no cross-service trust, no verification of anything the first party did not just say itself. The UI's "MUTUAL AGENT TRUST ESTABLISHED" overpromises.
- **Scale point 3 (phone channel) is skipped** — declared out of scope in the map, which is legitimate, but it is one of three promises.
- **"Streaming" is windowed batch.** Correct and honestly labelled in the deck — but the *claim* of acting on the Day-1 scaling promise is thinner than it reads.
- **Overclaim on Impact:** "~10,000 checks funded by one prevented scam" is a cost-equivalence, not an impact (§2).

### DESIGN — 5.0 / 10

- **Three owners for one policy.** The thresholds live as constants in `app/policy.py`, as literal text in the table at `index.html:153–160`, and as drawn bars in `.scratch/build_deck_day2.py`. **29 literal copies** across the three files (7 / 12 / 10). `PUBLIC` is already served from `/api/status` and ignored by the UI. Change 0.90 once and three artefacts disagree.
- **`app/static/index.html` (495 lines) is a monolith** owning scenario config, transport, rendering, policy display, handshake, and audio control. No modules, no testable seam; the only way to check rendering is to run a browser.
- **`app/app.py` (301 lines) mixes** the DetectifAI client, policy application, attestation, challenge-response, status, enrollment, and static mounting — six concerns in one module.
- **Implicit state ownership.** `_VERDICTS` / `_CHALLENGES` are module globals; `SESSION_SECRET` is ephemeral (app.py:42). A restart silently invalidates every token; a second worker breaks the handshake entirely. For a demo it works; it is not a protocol.
- **Dead code.** `worst` is imported at `app/app.py:30` and never called — worst-wins is implemented client-side in JS instead, so the server's authoritative policy helper is unused by the server.

### CORRECTNESS — 6.0 / 10

Graded from behaviour actually exercised (local four scenarios + handshake; deployed genuine, subtle, and handshake; policy selftest 10/10).

Working: all four policy outcomes; windowed streaming; fail-closed on 422; idempotent replays; deployed at the public link; console clean.

Not exercised, so not credited: the deployed hijack and silent paths individually; the 503/Retry-After branch; multi-worker or restart behaviour; any **live** audio (none exists).

Concrete defects:

1. **The raw payload contradicts the live claim.** `idempotent_replay: true`, `credits.charged: 0` on every demo run.
2. **The handshake cannot fail for the right reason.** It checks its own store, so "the server holds a fresh proceed verdict" is circular — it will also be true if a bug wrote a proceed verdict for the wrong audio.
3. **Restart-sensitivity:** an ephemeral `SESSION_SECRET` plus in-memory challenges means an in-demo restart shows "handshake refused" for no visible reason.
4. **`call_subtle.wav` is the only scenario that proves segment depth**, and it is a *batch* single-call path — the live-streaming path never exercises a segment-level hold.

### QUALITY — 5.0 / 10

- Duplicated thresholds (×3) and duplicated narrative copy (banner / deck markdown / deck builder).
- Dead scaffolding retained: `.scratch/assets/*.html` (10 files), `.scratch/make_assets.py`, `.scratch/build_deck.py` from Day 1, plus the unused `worst` import.
- `index.html` carries a full CSS block, a policy table, a scenario registry, and six render functions; extracting `render.js` + a policy-driven table would remove ~35 % of the file and 12 of the literal copies.
- **Estimate: the same behaviour fits in ~65 % of the current code**, with one owner per concern.

---

## 4. Beyond DetectifAI — the informed choice

Competition constraint: DetectifAI must remain the engine (20 marks). The question is therefore *what else to measure*, not *what to replace it with*.

### 4.1 Detection signals

| Signal | Answers | Blind spot that matters to us | Evidence | Where it runs |
|---|---|---|---|---|
| **Speaker verification** (ECAPA-TDNN / x-vector) | "Does this resemble the enrolled agent?" | **A voice conversion that preserves the target's timbre passes by design.** This is our Call 3. | ECAPA 0.87–1.01 % EER (VoxCeleb1); 6.2 M / 14.7 M params | Server; browser feasible (ONNX/WASM/WebGPU) |
| **Synthetic-speech detection** (AASIST-L, RawNet2) | "Does this speech sound generated?" | Unseen generators and codecs. **EER collapses out of domain.** | AASIST **0.83 %** EER on ASVspoof 2019 → **29.1 %** on ASVspoof 5 Track 1; RawNet2 3.15 % → **37.8 %** on In-the-Wild | Server/local; AASIST-L is **85 K params** |
| **SSL encoders** (Wav2Vec2/XLS-R, WavLM, Whisper) | Same question, better transfer | Cost; usually utterance-level | XLS-R 300 M **13.4 %** EER ITW; 1 B **4.8 %** (much slower) | Server |
| **Segment / partial-spoof localisation** (PartialSpoof, BAM) | "Which seconds are fake?" | Immature; needs partial-spoof training; sliding a window over an utterance-level model is **not** validated localisation | PartialSpoof: localisation is materially harder than utterance detection | Server |
| **Replay / liveness** (pop noise, HF loss, phase, RIR) | "Was this played through a speaker?" | Clean replays; says nothing about digital VC | ASVspoof 2017: best **6.73 %** EER, primary avg **25.9 %** | Browser/server, light |
| **Watermark** (AudioSeal, ElevenLabs) | "Did a cooperating generator make this?" | **Absence is not evidence of a human.** Strippable. | ElevenLabs: **99 % precision / 80 % recall** on unmodified ElevenLabs audio | Server |
| **Provenance** (C2PA) | "Who signed this asset?" | Not a liveness or deepfake test | valid / invalid signature | Browser/server, cheap |
| **Telecom trust** (STIR/SHAKEN A/B/C, carrier metadata, number reputation) | "Does the carrier attest the number?" | Not voice; an **A-attested call can still be fraud**; no detection accuracy at all | n/a | Provider integration |
| **Behavioural / content** (OTP ask, urgency, gift cards, remote access) | "Is this a scam script?" | Privacy, false positives, language coverage | n/a | Server (LLM) |

**The single most valuable insight here.** Our Call 3 ("voice identity passes, aggregate says real, one segment gives it away") is not a nice edge case — it is *the* structural weakness of speaker verification, and the research confirms it: a converter's whole job is to match the target's timbre. So the honest message is not "identity + synthetic = safe." It is:

> **Voice identity is not a safety property. Only a synthetic-speech signal, evaluated per segment, catches a same-voice conversion — and that signal degrades badly out of domain, so it must be layered with channel, provenance and behavioural evidence.**

That is a genuine depth insight, and it is worth more than any extra API call. It also reframes "our agent": our agent is the thing that *decides how much to trust each signal*, which is exactly what a bank buys.

### 4.2 Evaluation metrics (how to measure, and how to choose)

| Metric | What it is | Use it for | Trap |
|---|---|---|---|
| **EER** | threshold where FAR = FRR | comparing detectors | rarely the bank's operating point |
| **minDCF** | lowest weighted error cost over thresholds | threshold selection given stated costs | needs stated priors; an oracle bound |
| **t-DCF** | tandem spoof + ASV cost | the *combined* system | not a standalone metric |
| **FAR / FRR at the operating point** | rates at the chosen threshold | the numbers a buyer actually trusts | state the positive class explicitly |
| **Precision at deployment prevalence** | share of alerts that are real | investigator capacity | collapses at low prevalence |
| **Brier / ECE** | calibration | turning a score into a risk | ECE depends on binning |
| **Conformal / abstention** | coverage + "don't decide" | step-up routing | marginal coverage ≠ per-class |
| **Time-to-decision (p50/p95)** | latency that matters | the intervention window | inference ≠ end-to-end |
| **False-alarm burden** | alerts per 1,000 genuine calls | operations | — |

**Prevalence is the number our deck is missing.** 10,000 calls, 0.1 % fraud (10 cases), 80 % recall, 1 % false-positive rate → 8 true alerts and ~100 false alerts → **precision ≈ 7.4 %**. Recall flatters a model that would bury a fraud team in alerts. Reporting precision *at realistic prevalence*, plus false-alarms-per-1,000, is what separates a student project from a bank proposal.

### 4.3 The recommended architecture

Treat DetectifAI as **one provider behind an internal evidence interface**, not the product:

```
Capture (mic / call) → window → Evidence{ identity, synthetic, segment_max, quality, channel, provenance, behaviour }
                                   ↑ DetectifAI          ↑ AASIST-L (local)   ↑ STIR/SHAKEN + txn context
                                   └──────────────► Decision policy (calibrated fusion) ──────────────► ACT
```

- DetectifAI still drives the decision (competition rule satisfied, and it is the strongest single signal).
- The product's defensible asset becomes the **fusion + calibration + action layer**, which is vendor-agnostic and is what a bank actually integrates.
- A one-day experiment to make the choice informed: take 20 clips (10 genuine, 10 clones across 3 TTS engines, all pushed through a telephony codec) and report **per detector**: EER, FAR@FRR=1 %, segment-localisation hit rate, p95 latency, and cost per check. That table on a slide answers "why this stack" far better than any vendor claim.

---

## 5. Full-marks spec — acceptance criteria per criterion

Written as **pass/fail tests a hostile judge can run**. Full marks means every row passes.

### 5.1 DetectifAI integration — 20/20

| # | Requirement | Acceptance test |
|---|---|---|
| 1 | Live-path evidence, both checks | A judge speaks (or a fresh clip is generated in-session); the badge reacts, and the raw payload shows `idempotent_replay: false`. |
| 2 | Genuine vs fake produced live | TTS is generated **during** the demo from a prompt the judge chooses; the clone is caught in the same session. |
| 3 | Segment-level decision is exercised on the live path | A live window with a moderate aggregate but a ≥0.90 segment flips the decision to HOLD. |
| 4 | Thresholds are calibrated, not asserted | A one-slide calibration: FAR/FRR at 2–3 candidate thresholds on ≥20 labelled clips, with the chosen operating point justified. |
| 5 | Fail-closed is demonstrated, not described | Silence, truncated audio, and a forced 5xx each produce STEP UP; none produces proceed. |
| 6 | Depth is architectural | At least one *second* signal (local AASIST-L, replay check, or STIR/SHAKEN) feeds the score, with its weight stated. |

### 5.2 Working prototype — 10/10

| # | Requirement | Acceptance test |
|---|---|---|
| 1 | No-login public link | Opens in a clean profile; no prompt; mobile-width renders. |
| 2 | Unseen input | Judge-supplied or live audio processed end to end. |
| 3 | A real action | The transaction object transitions and the "bank agent" visibly stops/escalates; the state is readable via an API. |
| 4 | Genuine and fake differ, live | Two runs in the room with opposite outcomes and no manual intervention. |
| 5 | No hitch | Pre-warmed instance; a rehearsed recovery for each failure in §5.6. |

### 5.3 Problem and user insight — 10/10

| # | Requirement | Acceptance test |
|---|---|---|
| 1 | The registration artifact on screen | The exact registered use-case text (or screenshot) is shown and matches the demo. |
| 2 | Primary evidence | 3–5 short interviews (fraud ops, contact-centre agent, a customer) or ≥3 published incident figures mapped onto *this* workflow. |
| 3 | Why today's process fails, specifically | Named controls (caller ID, KYC questions, "we never ask for X") and the exact point each one breaks. |

### 5.4 Impact — 10/10

| # | Requirement | Acceptance test |
|---|---|---|
| 1 | A money number with a model | `high-risk calls × fraud incidence × avg loss × detection × intervention` with all five inputs visible and sourced (or flagged as an assumption). |
| 2 | Precision at prevalence | Reports precision **and** false-alarms per 1,000 genuine calls at the chosen threshold. |
| 3 | Time-to-decision | p50/p95 window latency vs the bank's intervention window. |
| 4 | Bounded false-alarm cost | Step-up, never lockout; the customer-cost side is estimated, not ignored. |

### 5.5 Scale and viability — 10/10

| # | Requirement | Acceptance test |
|---|---|---|
| 1 | Buyer and channel conflict resolved | A named buyer with a stated reason a **user-side** verifier is worth paying for (brand-protection, scam-loss, or app engagement), plus the distribution route (CCaaS / telco / banking app SDK). |
| 2 | Model-risk validation package | Because the buyer is a bank: data provenance, threshold rationale, segment/channel breakdown, limitations, monitoring — mapped to the Fed's model-risk guidance for vendor models. |
| 3 | Unit economics | Cost per analysed high-risk interaction vs the ~$0.30 benchmark; where the cost falls as volume rises. |
| 4 | A pilot design | One workflow, one metric, one duration, one success threshold. |
| 5 | The dataset answer, productised | "No training corpus" turned into an onboarding runbook: who provides the 15–60 s samples, under what basis, stored how, deleted when. |

### 5.6 Demo and communication — 10/10

| # | Requirement | Acceptance test |
|---|---|---|
| 1 | Five slides, required order | Structural check; no sixth slide, no appendix in the deck. |
| 2 | One idea per slide | Slide 3 shows one thing (the aggregate-blind hold), not five claims. |
| 3 | Rehearsed, timed | Two full run-throughs, inside the slot, with a stopwatch. |
| 4 | Every member owns a section | Explicit assignment; each answers unscripted questions in their own area. |
| 5 | Failure path | Live-Wi-Fi failure, cold start, and API 503 each have a rehearsed 10-second recovery. |
| 6 | Day-1 feedback visibly acted on | The judge's dataset question is answered in the product and on a slide, with the artefact that shows it. |

---

## 6. Prioritised plan (if the team chooses to build)

| Priority | Work | Effort | Rubric lift |
|---|---|---|---|
| **P0** | L1 live-mic verify + enroll; a real transaction object with an action; a fresh-run path so `idempotent_replay: false` | 2–3 h | +5 prototype, +2 DetectifAI |
| **P0** | Impact model with precision-at-prevalence; registration artefact on screen | 1 h | +4 impact, +2 problem |
| **P1** | L2 two-agent call (TTS bank agent + verifier agent that acts); attacker injection mid-call | 3–5 h | +3 DetectifAI, +2 demo |
| **P1** | Second signal (local AASIST-L) + calibration table on 20 clips | 2–3 h | +3 DetectifAI, +2 scale |
| **P2** | Channel-conflict answer; model-risk validation one-pager; pilot design | 1–2 h | +4 scale |
| **P2** | Rehearsals; slide-3 split; per-member ownership | 1 h | +3 demo |

**Cut to buy this time:**
- The **handshake** as currently built — it is the weakest-evidenced claim on the deck. Either make it a real two-party protocol (one agent calls another over HTTP with a signed challenge) or drop it from the demo and keep it as a slide. It currently costs credibility more than it buys.
- The **hardcoded policy table** in `index.html` (drive it from `/api/status`).
- The **fourth scenario** if rehearsal time is tight — three outcomes (proceed / hold-on-segment / step-up) tell the whole story.
- Day-1 scaffolding in `.scratch/assets/`.

---

## 7. Hostile-judge checklist

Every "no" is a lost mark.

| # | Question | Now |
|---|---|---|
| 1 | Can I speak and have it verified? | **No** |
| 2 | Is the audio I'm hearing generated in front of me? | **No** |
| 3 | Does the raw API response look like a fresh call? | **No** (`replay`, `0 credits`) |
| 4 | Does anything actually happen when the decision is HELD? | **No** (text only) |
| 5 | Is there an agent that decides anything? | **No** |
| 6 | Can I see what was registered? | **No** |
| 7 | Is the impact a money number? | **No** (cost ratio) |
| 8 | Why would a bank pay for *my* side of the call? | **Unanswered** |
| 9 | Is the model validated the way a bank requires? | **No** |
| 10 | Does the demo survive a Wi-Fi drop? | **Partly** (fallbacks written, not rehearsed) |
| 11 | Does one slide make one point? | **Partly** (slide 3 is dense) |
| 12 | Can every member answer in their area? | **Untested** |

---

## 8. Sources

Audit evidence: repo files (`app/app.py`, `app/policy.py`, `app/static/index.html`), live probes against `https://unclone-verified-agent.onrender.com`, and the full text of [`app/audio/`](app/audio) manifests.

Research (primary sources, read in full by the research agents):

- Generalisation: [Does Audio Deepfake Detection Generalize?](https://arxiv.org/html/2203.16263) · [ASVspoof 5 challenge](https://arxiv.org/html/2408.08739v1) · [AASIST](https://arxiv.org/html/2110.01200) · [AASIST code](https://github.com/clovaai/aasist) · [ASVspoof 2019 DB](https://datashare.ed.ac.uk/handle/10283/3336) · [ASVspoof 2021](https://www.asvspoof.org/index2021.html) · [SSL anti-spoofing](https://github.com/TakHemlata/SSL_Anti-spoofing) · [PartialSpoof](https://zenodo.org/records/5766198) · [BAM](https://arxiv.org/html/2407.21611) · [backbone transfer study](https://arxiv.org/html/2507.01750v1)
- Verification, liveness, provenance: [ECAPA-TDNN](https://arxiv.org/html/2005.07143v3) · [WavLM](https://arxiv.org/abs/2110.13900) · [VC vs ASV](https://www.isca-archive.org/interspeech_2013/wu13_interspeech.html) · [ASVspoof 2017](https://www.asvspoof.org/index2017.html) · [replay vs deepfake detection](https://arxiv.org/html/2505.14862v1) · [AudioSeal](https://proceedings.mlr.press/v235/san-roman24a.html) · [C2PA](https://c2pa.org/faqs/) · [ONNX Runtime Web](https://onnxruntime.ai/docs/tutorials/web/)
- Metrics and validation: [t-DCF](https://arxiv.org/html/1804.09618) · [Fed model-risk guidance](https://www.federalreserve.gov/frrs/guidance/supervisory-guidance-on-model-risk-management.htm) · [NIST SRE12](https://www.nist.gov/itl/iad/mltg/sre12-results) · [calibration](https://arxiv.org/html/2501.19047v2) · [selective classification](https://arxiv.org/html/2208.12084v2) · [FTC 2024 fraud](https://www.ftc.gov/news-events/news/press-releases/2025/03/new-ftc-data-show-big-jump-reported-losses-fraud-125-billion-2024)

---

## 9. The single most valuable next pass

**Build L1: a live microphone path with a real action.**

It is a few hours, it is low-risk, and it is the only change that simultaneously converts: the "pre-recorded" objection (DetectifAI +2..3), the "four buttons" objection (prototype +3), the "no agent" objection (the verifier now has to react to unseen audio), and the demo's failure mode (a judge can *try it*). Everything else in this document is either evidence-gathering (impact, scale) or polish.
