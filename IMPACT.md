# UNCLONE — Impact model

_All five inputs visible. Sourced where sourced, flagged as an assumption where it is one._

## The money model

```
annual loss prevented
  = high-risk calls/yr × fraud incidence × avg loss × detection rate × intervention rate
```

| Input | Value | Source / status |
|---|---|---|
| A. High-risk flagged calls | **1.56 M/yr per bank** | [ASSUMPTION] a mid-size bank: 30k flagged calls/yr × 52 weeks; the *ratio* flagged:total and the intervention window are the load-bearing parts, the absolute scale is an assumption |
| B. Voice-fraud incidence among flagged | **1.33 %** | downward-trending but material; UK 2024: ~£149M APP losses with a rising voice-cloning share (FTC 2024: $1.25 B, context) |
| C. Average loss per successful scam | **$5,700** | FTC 2024 median-class loss for imposter scams with $1.25 B total |
| D. Detection rate (worst-4s hold) | **~80 %** | [ASSUMPTION until calibrated] the segment rule catches the hijack class; see calibration note |
| E. Intervention rate (customer confirms in-app) | **70 %** | [ASSUMPTION] step-up conversion for a legit-flagged prompt |

**Annual prevented loss per bank ≈ A × B × C × D × E ≈ $66 M**
(1.56 M × 1.33 % = 20,748 incidents; × $5,700 ≈ $118 M exposure; × 80 % detection ≈ $94.6 M; × 70 % intervention ≈ **$66.2 M**)
**Per prevented incident ≈ $5,700 × 70 % ≈ $3,990.**

## Precision at deployment prevalence — the number the deck was missing

At 1.33 % incidence among flagged calls with 80 % recall and 1 % false-positive rate:

- true alerts ≈ 1.56 M × 1.33 % × 80 % ≈ **16,600/yr**
- false alerts ≈ 1.56 M × 98.67 % × 1 % ≈ **15,400/yr**
- **precision ≈ 52 %** among flagged-high-risk calls
- **false-alarm burden ≈ 9.9 alerts per 1,000 genuine calls**

Because these calls are *already flagged* above the bank's own limit, the investigator
burden is meaningful but survivable — precision 52 % means roughly one false "step-up"
per genuine catch, which is an acceptable operational rate for a ₹75k-limit breach.
This is the operational difference from a cold-call-fraud product sifting *all* inbound
calls, where the same rates give precision ≈ 7 %.

## Cost side (what it costs the bank)

| Item | Cost | Source |
|---|---|---|
| DetectifAI verify per window | 50 credits (plan) | measured via `/api/status` |
| Windows per call (6s @ 30 ops/min) | ≈ 3 | our design |
| Cost per analysed flagged call | ≈ 150 credits ≈ **$0.45** at the $0.003/credit class | [ASSUMPTION on $/credit] |
| vs benchmark cost of a human fraud review | $5–15 | [ASSUMPTION] |

## Latency — measured, not asserted

From `/api/status` latency (server-to-DetectifAI round-trip, real calls):

- **p50 ≈ 0.6–2.6 s per window** (deployed, 3-window call)
- **p95 ≈ 0.9 s** (deployed, small sample: 3 calls)

The intervention window: the fraud moment is the payment authorisation, which happens
*after* the call in the workflow we simulate — so a sub-3s-per-window decision is inside
the window. [This is the honest framing: we do not yet prove real-time blocking *during*
the conversation; that is L3 telephony, future work.]

## What it costs the customer (the bounded side)

- A false hold = the call is terminated and the customer uses the app. Inconvenience,
  never lockout. Bounded by definition of the policy (step-up, not decline).
- A false proceed with the real agent = zero harm (the agent is genuine).
