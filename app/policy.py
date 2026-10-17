"""Decision policy for the user-side verified-agent badge.

DetectifAI returns evidence, not a decision. This module turns that evidence
into exactly one action: ``proceed``, ``step_up`` or ``hold``.

It is deliberately fail-closed:

* any missing, partial, or errored evidence can never yield ``proceed``;
* auto-approval needs a margin above the vendor's match threshold;
* a single hot deepfake *segment* overrides a reassuring aggregate, because
  the aggregate is an average and an attacker only needs a few seconds.
"""
from __future__ import annotations

from typing import Any, Optional

# Published vendor thresholds. Read from each response when present.
VENDOR_MATCH = 0.53
VENDOR_DEEPFAKE = 0.62

# Product policy: never auto-approve on a thin identity margin.
AUTO_APPROVE_SIM = 0.75

# A single 4-second window this synthetic is decisive on its own.
SEGMENT_HOLD = 0.90

# Second signal (app.forensics): provenance-quality only. A high score means
# "clean digital render, no acoustic capture" — escalation evidence, never proof
# of fraud on its own, so it can reach step_up and no further.
FORENSICS_ARTIFACT_HIGH = 0.85

ACTION_RANK = {"proceed": 0, "step_up": 1, "hold": 2}

PUBLIC = {
    "vendor_match_threshold": VENDOR_MATCH,
    "auto_approve_similarity": AUTO_APPROVE_SIM,
    "deepfake_threshold": VENDOR_DEEPFAKE,
    "segment_hold": SEGMENT_HOLD,
    "forensics_artifact_high": FORENSICS_ARTIFACT_HIGH,
    "second_signal": "forensics (stdlib) — escalation only: reaches step_up, never hold",
    "replay_rule": "identical content re-sent within one call -> hold",
    "actions": {
        "proceed": "Voice matches with margin and the whole call is real.",
        "step_up": "Evidence is thin, partial or unavailable: move to in-app confirmation.",
        "hold": "Identity or authenticity failed: hold the transaction.",
    },
}


def _num(value: Any, default: Optional[float] = None) -> Optional[float]:
    try:
        if value is None or isinstance(value, bool):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _out(action: str, severity: str, reason: str, evidence: dict) -> dict:
    return {
        "action": action,
        "severity": severity,
        "reason": reason,
        "evidence": evidence,
    }


def decide(payload: dict) -> dict:
    """Map a DetectifAI verify response (or an error envelope) to a decision."""
    payload = payload or {}

    # 1. Transport or upstream error: never approve.
    if payload.get("error"):
        err = payload.get("error")
        if isinstance(err, dict):
            code = err.get("code") or err.get("type") or "upstream_error"
        else:
            code = "upstream_error"
        return _out(
            "step_up",
            "amber",
            f"Unverifiable input ({code}) \u2014 fail closed, step up.",
            {"error_code": code},
        )

    result = payload.get("result") or {}
    if not result:
        return _out(
            "step_up", "amber", "No verification result \u2014 fail closed, step up.", {}
        )

    similarity = _num(result.get("similarity"))
    sim_threshold = _num(result.get("threshold"), VENDOR_MATCH)
    decision = result.get("decision")
    if similarity is None or decision is None:
        return _out(
            "step_up", "amber", "Incomplete verification result \u2014 fail closed.", {}
        )

    deepfake = payload.get("deepfake") or {}
    if not isinstance(deepfake, dict):
        deepfake = {}
    verdict = deepfake.get("verdict")
    df_score = _num(deepfake.get("score"))
    df_threshold = _num(deepfake.get("threshold"), VENDOR_DEEPFAKE)
    df_error = deepfake.get("error")

    segments = [s for s in (deepfake.get("segments") or []) if isinstance(s, dict)]
    scored = [(s, _num(s.get("score"))) for s in segments]
    scored = [(s, v) for s, v in scored if v is not None]
    worst_segment: Optional[dict] = None
    max_segment: Optional[float] = None
    if scored:
        worst_segment, max_segment = max(scored, key=lambda pair: pair[1])

    evidence = {
        "similarity": similarity,
        "similarity_threshold": sim_threshold,
        "deepfake_verdict": verdict,
        "deepfake_score": df_score,
        "deepfake_threshold": df_threshold,
        "max_segment": max_segment,
    }
    if worst_segment is not None:
        evidence["worst_segment"] = {
            "start": worst_segment.get("start"),
            "end": worst_segment.get("end"),
            "score": max_segment,
        }

    # 2. Capture-and-replay: identical audio already verified in this call.
    #    Record the agent once, resend it every call — identity would match and
    #    the aggregate would look clean, so this has to be checked on content.
    forensics = payload.get("forensics")
    if not isinstance(forensics, dict):
        forensics = {}
    replay = forensics.get("replay")
    if isinstance(replay, dict) and replay.get("detected"):
        matched = replay.get("matched") or "content"
        count = replay.get("count") or 2
        return _out(
            "hold",
            "red",
            f"Capture-and-replay: identical audio already verified {count} times "
            f"in this call ({matched} match). A recorded window cannot be re-sent. "
            "Transaction held.",
            evidence,
        )

    # 3. Identity failed: the speaker is not the enrolled agent.
    if decision != "match" or similarity < sim_threshold:
        return _out(
            "hold",
            "red",
            f"Voice does not match the enrolled agent "
            f"(similarity {similarity:.3f} < {sim_threshold:.2f}). Transaction held.",
            evidence,
        )

    # 3. A single synthetic window is decisive, even if the aggregate is calm.
    if max_segment is not None and max_segment >= SEGMENT_HOLD:
        start = worst_segment.get("start") if worst_segment else None
        end = worst_segment.get("end") if worst_segment else None
        where = (
            f" at {start:.1f}\u2013{end:.1f}s"
            if isinstance(start, (int, float)) and isinstance(end, (int, float))
            else ""
        )
        aggregate = (
            f"aggregate {df_score:.3f} said {verdict}"
            if df_score is not None and verdict
            else "aggregate was inconclusive"
        )
        return _out(
            "hold",
            "red",
            f"Synthetic speech detected{where} "
            f"(segment {max_segment:.3f}; {aggregate}). Transaction held.",
            evidence,
        )

    # 4. The deepfake leg says synthetic.
    if verdict == "fake":
        score_text = f"{df_score:.3f}" if df_score is not None else "n/a"
        return _out(
            "hold",
            "red",
            f"Deepfake detector says synthetic (score {score_text} \u2265 {df_threshold:.2f}). "
            "Transaction held.",
            evidence,
        )

    # 5. Partial or unavailable deepfake evidence: cannot approve.
    if df_error or verdict is None or df_score is None:
        return _out(
            "step_up",
            "amber",
            "Deepfake check unavailable \u2014 partial evidence can never be approved; step up.",
            evidence,
        )

    if verdict == "not_sure" or df_score >= df_threshold:
        return _out(
            "step_up",
            "amber",
            "Deepfake detector is unsure \u2014 step up to in-app confirmation.",
            evidence,
        )

    # 6. Identity passes, but without enough margin to auto-approve.
    if similarity < AUTO_APPROVE_SIM:
        return _out(
            "step_up",
            "amber",
            f"Voice matches but the margin is thin "
            f"({similarity:.3f} < {AUTO_APPROVE_SIM:.2f}) \u2014 step up.",
            evidence,
        )

    # 7. Provenance forensics: escalation only. Above the threshold the audio
    #    looks like a digital render rather than an acoustic capture — enough to
    #    refuse auto-approval, never enough to convict.
    artifact = forensics.get("artifact_score")
    if artifact is not None and artifact >= FORENSICS_ARTIFACT_HIGH:
        flags = ", ".join(forensics.get("flags") or []) or "digital render"
        return _out(
            "step_up",
            "amber",
            f"Provenance forensics: audio reads as a digital render "
            f"(artifact {artifact:.3f} >= {FORENSICS_ARTIFACT_HIGH:.2f}: {flags}). "
            "Second signal refuses auto-approval — step up.",
            evidence,
        )

    return _out(
        "proceed",
        "green",
        f"Voice matches ({similarity:.3f}) and every segment is real "
        f"(deepfake {df_score:.3f}, max segment {max_segment if max_segment is not None else 0:.3f}).",
        evidence,
    )


def worst(decisions: list[dict]) -> dict:
    """Worst-wins across the windows of a call."""
    if not decisions:
        return _out("step_up", "amber", "No windows verified \u2014 fail closed.", {})
    return max(decisions, key=lambda d: ACTION_RANK.get(d.get("action"), 2))


if __name__ == "__main__":
    def payload(sim, dec, verdict, score, segs):
        return {
            "result": {"similarity": sim, "decision": dec, "threshold": 0.53},
            "deepfake": {
                "verdict": verdict,
                "score": score,
                "threshold": 0.62,
                "segments": [
                    {"start": s, "end": e, "score": sc} for s, e, sc in segs
                ],
            },
        }

    cases = [
        ("genuine full", payload(0.98735, "match", "real", 0.00821,
                                 [(0, 4, 0.0015), (2, 6, 0.001)]), "proceed"),
        ("genuine 6s", payload(0.888378, "match", "real", 0.001247,
                               [(0, 4, 0.0015), (2, 6, 0.001)]), "proceed"),
        ("phone-line genuine", payload(0.813204, "match", "real", 0.011167,
                                       [(0, 4, 0.021)]), "proceed"),
        ("hijack", payload(0.150605, "no_match", "fake", 0.999422,
                           [(0, 4, 0.9999)]), "hold"),
        ("aggregate-blind subtle", payload(0.767332, "match", "real", 0.336505,
                                           [(0, 4, 0.0015), (8, 12, 0.9913),
                                            (9, 13, 0.9989)]), "hold"),
        ("thin margin", payload(0.60, "match", "real", 0.01,
                                [(0, 4, 0.01)]), "step_up"),
        ("not sure", payload(0.80, "match", "not_sure", 0.50,
                             [(0, 4, 0.10)]), "step_up"),
        ("partial deepfake", {
            "result": {"similarity": 0.9, "decision": "match", "threshold": 0.53},
            "deepfake": {"error": {"code": "inference_failed"}},
        }, "step_up"),
        ("silent", {"error": {"type": "unprocessable_audio",
                              "code": "silent_audio"}}, "step_up"),
        ("empty", {}, "step_up"),
        # --- second signal -------------------------------------------------
        # Replay of genuine-sounding audio: identity would match, content betrays it.
        ("replay", {
            "result": {"similarity": 0.98735, "decision": "match", "threshold": 0.53},
            "deepfake": {"verdict": "real", "score": 0.00821, "threshold": 0.62,
                         "segments": [{"start": 0, "end": 4, "score": 0.0015}]},
            "forensics": {"available": True, "artifact_score": 0.21,
                          "replay": {"detected": True, "matched": "perceptual",
                                     "count": 3}},
        }, "hold"),
        # Digital render with a clean verdict: escalate, do not convict.
        ("digital render", {
            "result": {"similarity": 0.98735, "decision": "match", "threshold": 0.53},
            "deepfake": {"verdict": "real", "score": 0.00821, "threshold": 0.62,
                         "segments": [{"start": 0, "end": 4, "score": 0.0015}]},
            "forensics": {"available": True, "artifact_score": 0.97,
                          "flags": ["digital_silence_61%", "no_room_tone_0.0000"]},
        }, "step_up"),
        # Below threshold: forensics must not disturb a clean genuine verdict.
        ("forensics calm", {
            "result": {"similarity": 0.98735, "decision": "match", "threshold": 0.53},
            "deepfake": {"verdict": "real", "score": 0.00821, "threshold": 0.62,
                         "segments": [{"start": 0, "end": 4, "score": 0.0015}]},
            "forensics": {"available": True, "artifact_score": 0.505},
        }, "proceed"),
        # Unavailable forensics is not missing *required* evidence: no change.
        ("forensics n/a", {
            "result": {"similarity": 0.98735, "decision": "match", "threshold": 0.53},
            "deepfake": {"verdict": "real", "score": 0.00821, "threshold": 0.62,
                         "segments": [{"start": 0, "end": 4, "score": 0.0015}]},
            "forensics": {"available": False, "reason": "not_decodable_pcm_wav"},
        }, "proceed"),
    ]

    for name, case, expected in cases:
        got = decide(case)
        assert got["action"] == expected, f"{name}: expected {expected}, got {got}"
        print(f"ok  {name:24s} -> {got['action']:8s} | {got['reason']}")
    print("policy selftest: all passed")
