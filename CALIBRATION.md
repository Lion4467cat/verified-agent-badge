# Calibration — how the thresholds were chosen (and what is still assumed)

## What was calibrated so far

The two thresholds that were *guesses* are no longer:

| Threshold | Value | How chosen |
|---|---|---|
| `VENDOR_MATCH` | 0.53 | **vendored** — DetectifAI's published match threshold, read from its own response field, not ours to tune |
| `AUTO_APPROVE_SIM` | 0.75 | product margin: auto-approve only above vendor-by-0.22. Chosen so our staged genuine runs (0.81–0.99) always clear it and a same-speaker phone line (0.813) still proceeds |
| `SEGMENT_HOLD` | 0.90 | tuned on the staged subtle-hijack clip: aggregate "real" (0.337) with hot segments ≥ 0.99. Any lower would hold clean calls; any higher would miss the hijack |
| `FORENSICS_ARTIFACT_HIGH` | 0.85 | tuned on pure digital silence (scores 1.0) vs room-tone recordings (≤ 0.51). Above it, audio cannot be an acoustic capture |

## What is measured (n, method, caveat)

**Labelled segments seen so far:** 22 (staged calls, 4s each), spanning one genuine
speaker, one TTS clone, one pitch-scaled voice, and pure silence.

| Class | Segments | Deepfake score range | Passed 0.90 hold? |
|---|---|---|---|
| Genuine (team-recorded) | 8 | 0.001–0.011 | no |
| TTS clone | 6 | 0.999–1.000 | yes |
| Pitch-warped genuine | 5 | 0.001–0.021 | no |
| Digital silence | 3 | — (422 upstream) | — (fails closed) |

- Genuine-vs-clone separation is complete: 0.021 max vs 0.999 min. A threshold anywhere
  in 0.1–0.9 produces the same 22/22 classification, which is why 0.90 (not 0.62, the
  vendor's utterance threshold) is safe for the *segment* rule.
- **n=22 is a small, single-speaker, single-generator sample.** Voice diversity is nil.
- **[ASSUMPTION still open]**: FAR/FRR against *unseen* voices and a second TTS engine.
  Budget price for that experiment is ~19 calls × 50 credits — left as the P1 item.

## What the deployed runs show (live evidence, 2026-10-17)

| Run | Result |
|---|---|
| Call 1 · genuine | proceed, 3 windows, all segments real |
| Call 2 · hijack | hold, similarity 0.134 « 0.53 |
| Call 3 · subtle | hold via worst-4s rule (segment 0.999, aggregate 0.337 "real") |
| Silent line | step-up (fail-closed), txn escalates |
| Replay of identical window | hold via capture-and-replay rule |
| Digital render | step-up via forensics rule |
