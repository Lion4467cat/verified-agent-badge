# Scale and viability — the bank-grade answers

## Who buys, and why the user-side verifier is worth paying for

**Buyer:** the bank's fraud-operations and digital-channels team — not the contact centre.

**Why a user-side verifier despite the channel conflict.** The bank has two interests
that conflict: complete the call (revenue, service cost) and stop the scam (loss,
liability). Today both sit with the *human agent*, which is exactly what gets cloned.
A user-side verifier resolves the conflict by construction, because it is the
**customer's** control, not the contact centre's:

- it protects the call **even when the agent's voice is perfectly cloned** — the one
  case the contact centre cannot detect from inside the call;
- it creates the audit surface regulators ask for (the decision log is the txn object:
  which window, which score, which action, when);
- it works on calls the bank's own infra never sees (e.g. the customer is called back
  on a personal line).

**Distribution route:** shipping as an SDK inside the bank's existing app (the same
place the step-up prompt already lives), or CCaaS-side for banks without app reach.
Telephony (L3) is the later expansion, cited as future work.

## Model-risk validation package (what SR 11-7-style review expects)

| Requirement | Where it lives |
|---|---|
| Data provenance | enrolment = the bank's own call recordings (compliance retention); no third-party corpus. See runbook below |
| Threshold rationale | [CALIBRATION.md](CALIBRATION.md) — every threshold sourced or tuned-with-n |
| Segment / channel breakdown | segment strips in-product, per-window latency in `/api/status` |
| Known limitations | documented in-product ("streaming" = windowed batch at 6s; identity is not a safety property; small-n calibration) |
| Monitoring | credits + latency + fresh-cap counters exposed in `/api/status`; every decision logged with evidence |

## Unit economics

- ≈ 150 credits ≈ **$0.45** per analysed flagged call (measured plan price × our 3-window design).
- Compare: a human fraud review of a flagged call is $5–15 (assumption).
- At the 1-in-94 catch rate from [IMPACT.md](IMPACT.md) (1.33 % incidence × 80 % detection among analysed flagged calls): cost per caught fraud ≈ 94 × $0.45 ≈ **$42**, and ≈ **$60** per *prevented* fraud after the 70 % intervention step — a ≈ **13×** return against the $800 median loss per imposter-scam incident (FTC 2024 Data Book). _Corrected 2026-10-17: an earlier draft divided the per-call cost by alert precision ($0.87), which ignored that the analysis cost is paid on every flagged call, not only on alerts._
- Cost falls linearly with volume; the verify call is charged per operation, idle is free, so a bank pays only for flagged traffic.

## Pilot design (one workflow, one metric, one duration, one threshold)

- **Workflow:** inbound calls to the bank that trigger the existing above-limit flag; the SDK offers the customer a "verify this caller" button before any payment step.
- **Metric:** prevented-loss on flagged calls, tracked alongside false-step-up rate (must stay ≤ 2 % of genuine flagged calls, from the IMPACT false-alarm figure).
- **Duration:** 6 weeks.
- **Success threshold:** ≥ 1 confirmed prevented voice-fraud incident with a full decision log (txn object + per-window DetectifAI evidence), and false-step-up within bound.

## The dataset answer, productised (enrolment runbook — no training corpus)

1. **Who provides the audio:** the contact-centre's existing compliance recordings of the *specific agent roster assigned to payment-confirmation calls* (15–60 s of clean speech per agent).
2. **Under what basis:** already-captured for regulatory compliance; used for verification requires the same privacy basis as the recordings themselves — no new capture, no biometric-template export (the speaker template stays inside DetectifAI; we hold only ids and scores).
3. **Stored how:** enrolment via the vendor's speaker-enrolment API; our side keeps only `speaker_id` and a content fingerprint, no raw audio.
4. **Deleted when:** on agent offboarding — one deletion call per speaker, evidenced in the decision log.
