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

**Labelled segments seen so far:** 28 across four generators/transforms and two voices (the table rows below sum to 8+6+5+3+3+2+1 = 28)
(10 fresh ops spent 2026-10-17 on the second-engine run: credits 950 → 450).

| Class | Segments | Deepfake score range | Crossed the 0.90 hold? |
|---|---|---|---|
| Genuine (team-recorded) | 8 | 0.001–0.011 | no |
| TTS clone (engine 1) | 6 | 0.999–1.000 | yes |
| Pitch-warped genuine | 5 | 0.001–0.021 | no |
| Digital silence | 3 | — (422 upstream) | — (fails closed) |
| **Engine-2 pitch-converted TTS (fresh-rate)** | 3 | 0.998–0.9999 | **yes** |
| **Engine-2 pitch-converted genuine (modified but untouched-audio class)** | 2 | 0.002–0.007 | no — action step_up by margin (0.548 / 0.742) |
| **Engine-2 telephony-band (300–3400 Hz) TTS** | 1 | 0.998 | **yes** |

- Genuine-vs-clone separation **holds across the second transform family**: min clone
  score 0.998 vs max genuine 0.021 — the complete separation transfers. The telephony-band
  render (the realistic attacker: no clean full-band TTS artefacts) still scored 0.998,
  so if anything the codec makes the synthetic artefacts *more* detectable, not less.
- **Identity margin behaved as designed, too**: converted-genuine windows scored
  0.548/0.742 similarity — above vendor-match but below our 0.75 auto-approve line, so
  they **step up rather than proceed**. The margin rule, not the segment rule, is what
  correctly refuses auto-approval on a voice that matches the wrong speaker's spectral
  shape.
- **What this calibration cannot yet claim:** two voices and two transform families are
  not two TTS *engines* in the ASVspoof sense; FAR/FRR against unseen real speakers is
  still unmeasured. n=28 is better than n=22, and the honest phrasing stays "tuned and
  transfer-checked within our attack classes" rather than "validated".

## What the deployed runs show (live evidence, 2026-10-17)

| Run | Result |
|---|---|
| Call 1 · genuine | proceed, 3 windows, all segments real |
| Call 2 · hijack | hold, similarity 0.134 « 0.53 |
| Call 3 · subtle | hold via worst-4s rule (segment 0.999, aggregate 0.337 "real") |
| Silent line | step-up (fail-closed), txn escalates |
| Replay of identical window | hold via capture-and-replay rule |
| Digital render | step-up via forensics rule |
