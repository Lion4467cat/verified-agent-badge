# UNCLONE Day 2 — full-marks spec, audited and corrected

_Corrected 2026-10-17 after auditing `AUDIT-day2.md` §5. The old spec was not executable as
written: three of its rows were unbuildable in this environment and three were human tasks
disguised as acceptance tests. This file is the gate: nothing is built until every row here is
buildable, testable, and owned._

---

## A. Audit of the previous spec — 14 gaps

| # | Gap in `AUDIT-day2.md` §5 | Why it fails | Resolution in this spec |
|---|---|---|---|
| **G1** | §5.1.2 "TTS generated **during** the demo from a prompt the judge chooses" | **Unbuildable.** No `espeak`/`pico2wave`/`flite`/`festival` on the host, no `flite` filter in ffmpeg, no TTS API key, and the deploy image is `python:3.12-slim`. | Replace with **in-session voice conversion**: the genuine recorded voice is resynthesised in the browser at demo time (Web Audio pitch + spectral transform). It is unseen audio, it is a *real* attack primitive, and it needs no vendor. |
| **G2** | §5.1.4 "FAR/FRR on **≥20 labelled clips**" | **Impossible on this budget.** `price_per_operation: 50`, `available: 950` → **19 fresh calls total**, and any content change mints a new idempotency key (a charge). | Calibrate at **segment level**, which is the granularity the policy actually uses. Each call returns ~2–3 labelled 4 s segments, so ~8 calls yield **≥20 labelled segments**. Report n explicitly with a confidence caveat. |
| **G3** | §5.3.2 "3–5 interviews" | **Human task.** An agent cannot interview fraud-ops staff. | Spec requires **≥3 published incident figures** mapped onto this exact workflow (agent-buildable) and marks interviews **TEAM**, with a question bank supplied. |
| **G4** | §5.6.3/§5.6.4 "two rehearsed run-throughs, every member answers" | **Human task.** | Marked **TEAM**; the agent supplies the artefacts (timed run-sheet, ownership matrix, unscripted-question bank) rather than claiming the mark. |
| **G5** | §5.1.6 "a second signal … with its weight stated" | Named but **not specified and not buildable as named**: AASIST-L needs torch, STIR/SHAKEN needs a carrier, and the image has no numpy. | Specify **`forensics`**: a pure-stdlib signal-forensics layer (digital-silence fraction, clipping, HF rolloff, periodicity, noise-floor stationarity). Zero new dependencies, runs in the deploy image. |
| **G6** | §5.1.1 "raw payload shows `idempotent_replay: false`" | **Hidden trade-off.** Idempotency is exactly what makes judge replays free. Demanding freshness by default burns 50 credits on every replay. | Freshness becomes an explicit **`fresh=1` opt-in** with a visible credit cost; the default stays idempotent and free. The judge can demand a fresh run and watch it charge. |
| **G7** | Mic path assumed to work | **No failure path.** Permission denied, no microphone, or venue noise silently kills the headline feature. | Add a **file-upload fallback** and an explicit permission-failure state. Live mode is never a dead end. |
| **G8** | Live enroll → verify | **Circular.** Verifying a voice against its own enrolment always matches, so it proves nothing. | Require a **discriminating live test**: enrol the judge's voice, verify the judge (proceed) *and* verify the enrolled-clone audio against that same enrolment (hold). Both outcomes in one session. |
| **G9** | Live mode cost | **No budget guard.** An unauthenticated endpoint that spends 50 credits per window is a credit-burn vector and a demo-day incident. | Per-session window cap, upload size cap, and a **live credit meter**. Fail closed to idempotent replay when the budget is exhausted. |
| **G10** | §5.1.3 segment-level hold on the live path | Not testable as written — the live path had no segment-level hold. | The mic path must surface per-segment scores and must be capable of a segment-level HOLD; demonstrated on the staged subtle clip and asserted for live. |
| **G11** | §6 "cut the handshake" | §5 never says what **replaces** it, leaving scale-point-2 unaddressed. | Keep the mechanism, **remove the overclaim**: relabel as "bank attestation + server-recorded verdict", state plainly in-UI that both roles run in one process for the demo. No "MUTUAL TRUST" language. |
| **G12** | Impact §5.4.3 "p50/p95 time-to-decision" | Named but never instrumented, so it can never be reported. | Instrument every window with a latency sample; expose **measured p50/p95** from real runs. |
| **G13** | "Opens in a clean profile; mobile-width renders" | Asserted, never tested. | Explicit acceptance test on the **deployed** URL at 390 px and in a clean profile. |
| **G14** | No definition of "max score" | "Repeat until max" is **unfalsifiable** if the ceiling is undefined. | Define the ceiling in §C: 70 marks split into an **agent-buildable** subtotal and a **team** subtotal. The loop terminates when no further code change raises the pessimistic score. |

---

## B. Corrected spec — acceptance criteria

Legend: **[A]** agent-buildable in this repo · **[T]** team/human, agent supplies the artefact.

### B.1 DetectifAI integration — 20

| # | Requirement | Test | Own |
|---|---|---|---|
| 1 | Live-path evidence | Judge speaks; badge reacts; raw payload shows `idempotent_replay: false` on a `fresh=1` run | A |
| 2 | Genuine **and** fake produced in-session | In-session voice conversion of the genuine voice is verified and caught in the same session | A |
| 3 | Segment-level HOLD on the live path | Per-segment scores rendered; a ≥0.90 segment flips to HOLD | A |
| 4 | Calibrated thresholds | FAR/FRR at 2–3 candidate thresholds over **≥20 labelled 4 s segments**, chosen operating point justified | A |
| 5 | Fail-closed demonstrated | Silence, empty upload, truncated audio and a forced 5xx each → STEP UP; none → proceed | A |
| 6 | Depth is architectural | `forensics` second signal feeds the score, weight stated, fail-closed | A |

### B.2 Working prototype — 10

| # | Requirement | Test | Own |
|---|---|---|---|
| 1 | No-login public link | Opens in a clean profile; 390 px renders | A |
| 2 | Unseen input | Judge-supplied audio end to end | A |
| 3 | A real action | Transaction object `pending → verified / held / step_up`, readable via API, and the call visibly stops | A |
| 4 | Genuine and fake differ, live | Two runs, opposite outcomes, no manual intervention | A |
| 5 | No hitch | Pre-warmed instance; rehearsed recovery per failure | A + T |

### B.3 Problem and user insight — 10

| # | Requirement | Test | Own |
|---|---|---|---|
| 1 | Registered problem on screen | The registered user + problem (Rule 3.7) shown verbatim and matched to the demo | A |
| 2 | Primary evidence | ≥3 published incident figures mapped to this workflow | A |
| 3 | Named controls and their failure point | Caller ID, KYC questions, "we never ask for X" — where each breaks | A |
| 4 | Interviews | 3–5 fraud-ops / contact-centre interviews | **T** (question bank supplied) |

### B.4 Impact — 10

| # | Requirement | Test | Own |
|---|---|---|---|
| 1 | Money model | `high-risk calls × incidence × avg loss × detection × intervention`, five inputs visible and sourced/flagged | A |
| 2 | Precision at prevalence | Precision **and** false-alarms per 1,000 genuine calls at the chosen threshold | A |
| 3 | Time-to-decision | **Measured** p50/p95 vs the intervention window | A |
| 4 | Bounded false-alarm cost | Step-up, never lockout; customer cost estimated | A |

### B.5 Scale and viability — 10

| # | Requirement | Test | Own |
|---|---|---|---|
| 1 | Buyer + channel | Named buyer, why a **user-side** verifier is worth paying for, distribution route | A |
| 2 | Model-risk package | Provenance, threshold rationale, segment/channel breakdown, limitations, monitoring | A |
| 3 | Unit economics | Cost per high-risk interaction vs the $0.30-class benchmark | A |
| 4 | Pilot design | One workflow, one metric, one duration, one success threshold | A |
| 5 | Dataset answer productised | Enrolment runbook: who provides 15–60 s, on what basis, stored how, deleted when | A |

### B.6 Demo and communication — 10

| # | Requirement | Test | Own |
|---|---|---|---|
| 1 | Five slides, required order | Structural check | A |
| 2 | One idea per slide | Slide 3 shows the aggregate-blind hold only | A |
| 3 | Rehearsed, timed | Two run-throughs inside the slot | **T** (timed run-sheet supplied) |
| 4 | Every member owns a section | Ownership matrix + unscripted-question bank | **T** (artefacts supplied) |
| 5 | Failure path | Wi-Fi drop, cold start, API 503 → 10-second recovery each | A (scripts) + T (rehearsal) |
| 6 | Day-1 feedback acted on | Dataset question answered in-product and on a slide | A |

---

## C. The ceiling, defined (G14)

70 marks total. Code cannot earn the human rows, so the loop's maximum is bounded:

| Bucket | Marks | Owner |
|---|---|---|
| Agent-buildable | **58** | this build |
| Team/human (interviews, rehearsal, per-member questioning) | **12** | the team |

**Termination condition for the audit loop:** stop when no further code change raises the
pessimistic score against the **58-mark agent subtotal**, and the remaining gap is exclusively
[T]-owned. Claiming 70/70 from code alone would be exactly the overclaim this audit exists to
catch.

---

## D. Execution order (dependency-driven)

1. `forensics` (pure-stdlib second signal) — policy depends on it.
2. Transaction object + orchestrator (the action) — the UI depends on it.
3. `fresh=1` path + credit meter + caps.
4. Live mic (enrol / verify / fallback).
5. Calibration run over real segments → thresholds.
6. Impact + scale artefacts, registration strip.
7. Deploy, then re-audit and re-score.
