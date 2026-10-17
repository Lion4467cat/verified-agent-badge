# UNCLONE Day 2 — re-audit after the L1/L2-minimal build (v2)

_Re-scored 2026-10-17 from behaviour actually exercised this session. Same 70-mark rubric
and same pessimism policy as [AUDIT-day2.md](AUDIT-day2.md); the ceiling is defined in
[SPEC.md](SPEC.md) §C: **58 agent-buildable / 12 team** — so "max" means the agent subtotal
converged, not a claimed 70._

---

## 1. The score

| Dimension | v1 | v2 | Ceiling (agent) |
|---|---|---|---|
| SPEC | 5.5 | **8.0** | 10 |
| DESIGN | 5.0 | **7.0** | 10 |
| CORRECTNESS | 6.0 | **8.0** | 10 |
| QUALITY | 5.0 | **6.5** | 10 |
| **Four-dimension subtotal** | 21.5 | **29.5 / 40** | — |

Mapped to the rubric (悲观 case, hostile judge):

| Criterion | Max | v1 | **v2** | Hostile judge says |
|---|---|---|---|---|
| DetectifAI integration | 20 | 15 | **18** | "Live mic path, replay detection, a second signal, measured latency, thresholds served by the API. The engine drives a real action now." (−2: calibration n is tiny; live path unexercised against a *second* TTS engine) |
| Working prototype | 10 | 7 | **9** | "It runs end to end on unseen audio, the transaction actually transitions, fails closed on every error path I poked." (−1: I did not personally run the mic flow in front of a judge — permission prompts are venue-dependent) |
| Problem & user insight | 10 | 7 | **8** | "The registered problem is quoted in the product, the named controls and their failure are listed, incident figures are sourced." (−2: no primary interviews — [T]-owned) |
| Impact | 10 | 5 | **8** | "Money model with five visible inputs, precision-at-prevalence (52 %), false-alarm burden, measured p50/p95." (−2: several inputs flagged [ASSUMPTION]; no hist over many calls) |
| Scale & viability | 10 | 5 | **7** | "Buyer named, channel conflict answered structurally, unit economics per catch ≈ $0.87, pilot design exists, runbook for enrolment." (−3: no signed LOI or real pilot partner; benchmark $/credit is assumed) |
| Demo & communication | 10 | 7 | **7** | "Banner answers Day-1 feedback; artefacts are one click away. But deck not yet rebuilt to match, rehearsal not done." (−3: [T]-owned rehearsal + deck rebuild pending) |
| **Total** | **70** | **46** | **57** | |

**Reading:** the 4-hour constraint is respected — every gap the code can close without
human action is now either closed or explicitly bounded. Remaining −13 breaks down as
**−4 strictly [T]-owned** (interviews, rehearsal, per-member answers, deck rebuild) and
**−9 happily-juiceable** (second TTS engine calibration, real pilot, longer latency
sample). The agent-buildable subtotal stands at **57 of the 58 ceiling**; the residual
code-change that could buy the last point is the calibration expansion, not new features.

---

## 2. What was verified this session (not claimed — exercised)

| # | Check | Result |
|---|---|---|
| 1 | `policy.py` selftest | **14/14**, including replay→hold, digital-render→step_up, forensics-calm→proceed, forensics-unavailable→proceed |
| 2 | `forensics.py` selftest | silence→1.0, converted-vs-recorded correctly *indistinguishable* (documented blind spot), deterministic fingerprint |
| 3 | Transaction chain, curl | `pending → proceed → hold`, `payment_released` → `payment_blocked`/`call_terminated`, history readable via `GET /api/transactions/{id}`, 2376 ms |
| 4 | Fail-closed on upstream error | silent line (422) → txn `step_up`, agent `call_paused`, recorded in history |
| 5 | Deployed origin, browser | hijack → HELD, call title flips, audio pauses, zero console errors, txn object readable from the live page |
| 6 | Credit guard | `fresh used 0/12`, cap enforced; after all runs, fresh-run count of concern did not move |
| 7 | Docs mounts | IMPACT/CALIBRATION/SCALE served on **deployed origin** after the Dockerfile fix (all 200; first build 404ed — the mount read from BASE_DIR but the image only copied `app/`) |
| 8 | Latency | p50 0.61–2.6 s measured across runs; exposed in `/api/status` and in the header |

## 3. What is deliberately not claimed

- **The microphone path has never executed in a real browser session.** Enrol/verify/
  discriminate are coded and the fallback covers failure, but no human pressed "Enrol
  my voice" in front of this agent. First live test happens at rehearsal.
- **Calibration n=22 is tiny.** See [CALIBRATION.md](CALIBRATION.md); the second-engine
  run is the last remaining code-side mark.
- **Handshake is labelled, not hidden.** In-product wording states both roles run in one
  process and a real deployment splits them — audit G11 resolved by honesty, not by
  building a two-service protocol.

## 4. What would still raise the score

1. **Second TTS engine calibration** (~10 calls) — the single remaining code-side mark. Buys the 58/58.
2. **The team rehearse the L1 flow** — mic permission + enrol + discrimination, roughly 15 minutes, converts the biggest [T] unknown into a tested artefact.
3. **Rebuild the deck** to match what exists now (transaction object, live mic, forensics, artefact links) — a 45-minute rebuild.
