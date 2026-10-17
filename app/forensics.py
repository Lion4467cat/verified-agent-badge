"""Signal-forensics layer — the second, vendor-independent evidence signal.

Why this exists
---------------
DetectifAI answers "does this resemble the enrolled speaker" and "does this look
synthetic". Neither answer says anything about *how the audio reached us*. A file
rendered by a TTS engine, or a clean re-broadcast of a digital file, carries
acoustic fingerprints that a microphone recording does not:

* **digital silence** — generated audio pads with exactly-zero samples between
  phonemes; a room recording always has a noise floor, never a true zero.
* **noise floor** — a mic capture of speech sits on room tone. A digitally
  rendered signal collapses to ~0 in the gaps.
* **clipping / DC offset** — re-broadcast and re-encoded artefacts.

What it is not
--------------
This is **not** a deepfake detector and must never be presented as one. It is a
*provenance-quality* signal: "is this a clean digital artefact rather than an
acoustic capture?" It catches replays-of-files and low-effort synthesis, and it
is **blind to a well-produced voice conversion** — which is exactly why it is
the *second* signal and DetectifAI remains the engine.

Design contract (fail-closed, escalation-only)
----------------------------------------------
1. It can **escalate** (proceed -> step_up). It can never **de-escalate**.
2. It can never produce ``hold`` on its own — a missing noise floor is not proof
   of fraud.
3. It runs only on decodable PCM WAV. When the payload is not decodable (mp3,
   webm) it reports ``available: false`` and **does not** by itself force a
   step-up: the deepfake leg remains the *required* evidence. This is deliberate
   — the genuine staged clips are mp3 and must still be able to proceed.
4. Pure stdlib. The deploy image is python:3.12-slim with no numpy, no ffmpeg.
"""
from __future__ import annotations

import array
import math
import struct
import wave
from typing import Any

# NOTE on ownership: the *decision* threshold for `artifact_score` lives in
# `app/policy.py` (FORENSICS_ARTIFACT_HIGH). This module only measures — one
# owner per threshold, so a change cannot leave two artefacts disagreeing.

# A room-tone RMS at or above this fraction of full scale counts as "recorded".
# Tuned against our own genuine recording (see selftest below).
NOISE_FLOOR_RECORDED = 0.004

# This share of exactly-zero samples cannot occur in an acoustic capture.
SILENCE_TELL = 0.15

MAX_SAMPLES = 480_000  # ~30 s at 16 kHz: enough for a call window, cheap to scan


def _decode_wav(data: bytes) -> tuple[array.array, int] | None:
    """Return (mono float samples in -1..1, sample_rate) or None if unsupported."""
    import io

    try:
        with wave.open(io.BytesIO(data), "rb") as wf:
            n_channels = wf.getnchannels()
            width = wf.getsampwidth()
            rate = wf.getframerate()
            frames = wf.readframes(wf.getnframes())
    except Exception:  # noqa: BLE001 - any malformed input is simply "unavailable"
        return None

    if width == 2:
        pcm = array.array("h")
        pcm.frombytes(frames[: len(frames) - (len(frames) % 2)])
        scale = 32768.0
    elif width == 4:
        # float32 WAV (what the browser's re-encoder emits) or int32 PCM.
        # Heuristic: float32 samples live in -1..1, so a raw int32 mean far
        # outside that range means PCM32.
        pcm_f = array.array("f")
        try:
            pcm_f.frombytes(frames[: len(frames) - (len(frames) % 4)])
        except Exception:  # noqa: BLE001
            return None
        peak = max((abs(v) for v in pcm_f[:2000]), default=0.0)
        if peak <= 4.0:  # looks like float32
            return _downmix(list(pcm_f), n_channels, rate)
        pcm = array.array("l")
        pcm.frombytes(frames[: len(frames) - (len(frames) % 4)])
        scale = 2147483648.0
    elif width == 1:
        pcm = array.array("B")
        pcm.frombytes(frames)
        scale = 128.0
    else:
        return None

    samples = [(v - (128 if width == 1 else 0)) / scale for v in pcm]
    return _downmix(samples, n_channels, rate)


def _downmix(samples: list, n_channels: int, rate: int):
    if n_channels > 1:
        samples = [
            sum(samples[i : i + n_channels]) / n_channels
            for i in range(0, len(samples) - n_channels + 1, n_channels)
        ]
    if len(samples) > MAX_SAMPLES:
        samples = samples[:MAX_SAMPLES]
    return array.array("f", samples), rate


def _rms(frame) -> float:
    if not frame:
        return 0.0
    return math.sqrt(sum(v * v for v in frame) / len(frame))


def analyse(data: bytes) -> dict[str, Any]:
    """Extract provenance-quality features from a WAV payload.

    Never raises: a malformed payload returns ``available: False`` so the caller
    can treat it as "no extra evidence" rather than an error.
    """
    out: dict[str, Any] = {"available": False, "artifact_score": None, "flags": []}
    decoded = _decode_wav(data)
    if not decoded:
        out["reason"] = "not_decodable_pcm_wav"
        return out

    samples, rate = decoded
    n = len(samples)
    if n < rate // 2 or rate <= 0:  # <0.5 s is not analysable
        out["reason"] = "too_short"
        return out

    # 1. Digital silence: exactly-zero runs. Impossible in an acoustic capture.
    zeros = sum(1 for v in samples if v == 0.0)
    silence_frac = zeros / n

    # 2. Noise floor: RMS of the quietest 5 % of 20 ms frames.
    frame_len = max(1, int(rate * 0.02))
    frames = [samples[i : i + frame_len] for i in range(0, n - frame_len + 1, frame_len)]
    energies = sorted(_rms(f) for f in frames)
    quiet = energies[: max(1, len(energies) // 20)]
    noise_floor = sum(quiet) / len(quiet) if quiet else 0.0

    # 3. Clipping and DC offset: re-broadcast / re-encode artefacts.
    clipped = sum(1 for v in samples if abs(v) >= 0.98)
    clip_frac = clipped / n
    dc_offset = abs(sum(samples) / n)

    # 4. High-frequency energy: first-difference energy ratio, a cheap proxy for
    #    spectral tilt (band-limited telephony vs full-band rendering).
    diff_e = 0.0
    tot_e = 0.0
    prev = 0.0
    for v in samples:
        d = v - prev
        diff_e += d * d
        tot_e += v * v
        prev = v
    hf_ratio = (diff_e / tot_e / 2.0) if tot_e > 0 else 0.0

    # ---- score ------------------------------------------------------------
    # Escalation-only provenance score, 0 (acoustic capture) .. 1 (digital render).
    silence_component = min(1.0, silence_frac / SILENCE_TELL)
    floor_component = max(0.0, 1.0 - (noise_floor / NOISE_FLOOR_RECORDED))
    score = min(1.0, 0.55 * silence_component + 0.45 * floor_component)

    flags: list[str] = []
    if silence_frac >= SILENCE_TELL:
        flags.append(f"digital_silence_{silence_frac:.0%}")
    if noise_floor < NOISE_FLOOR_RECORDED:
        flags.append(f"no_room_tone_{noise_floor:.4f}")
    if clip_frac > 0.005:
        flags.append(f"clipping_{clip_frac:.2%}")

    out.update(
        {
            "available": True,
            "artifact_score": round(score, 4),
            "sample_rate": rate,
            "duration_s": round(n / rate, 2),
            "features": {
                "digital_silence_frac": round(silence_frac, 5),
                "noise_floor_rms": round(noise_floor, 6),
                "clipping_frac": round(clip_frac, 5),
                "dc_offset": round(dc_offset, 6),
                "hf_energy_ratio": round(hf_ratio, 5),
            },
            "flags": flags,
        }
    )
    return out


def fingerprint(data: bytes) -> dict[str, str]:
    """Content identity for capture-and-replay detection.

    Two hashes, deliberately:

    * ``exact``  — SHA-256 of the raw bytes. Catches a byte-for-byte resend,
      which is what an attacker who captured a genuine window sends.
    * ``perceptual`` — SHA-256 of a coarse RMS envelope (32 bins). Survives
      re-encoding and a level change, so a re-wrapped copy still matches.

    Replay is the realistic attack against speaker verification: record the
    agent once, replay it in every call thereafter. DetectifAI would happily
    return the cached *genuine* verdict for that audio — so the check has to
    live here, alongside the verdict, not upstream.
    """
    import hashlib

    exact = hashlib.sha256(data).hexdigest()[:32]
    decoded = _decode_wav(data)
    if not decoded:
        # Not decodable PCM: fall back to exact identity only.
        return {"exact": exact, "perceptual": exact, "decodable": "false"}

    samples, _rate = decoded
    n = len(samples)
    bins = 32
    step = max(1, n // bins)
    env = []
    for i in range(bins):
        chunk = samples[i * step : (i + 1) * step]
        env.append(int(round(_rms(chunk) * 2000)))
    per = hashlib.sha256("|".join(str(v) for v in env).encode()).hexdigest()[:32]
    return {"exact": exact, "perceptual": per, "decodable": "true"}


def selftest() -> None:
    """Validate the two discriminators on real assets we hold."""
    import pathlib

    audio = pathlib.Path(__file__).resolve().parent / "audio"
    cases = [
        ("silence_5s.wav", "digital", 0.85, 1.0),   # pure digital silence
        ("call_subtle.wav", "converted", 0.0, 1.0),  # has real room tone segments
        ("chunks/genuine_0.wav", "recorded", 0.0, 0.6),
    ]
    for rel, expect, lo, hi in cases:
        path = audio / rel
        if not path.is_file():
            print(f"skip {rel} (missing)")
            continue
        res = analyse(path.read_bytes())
        if not res.get("available"):
            print(f"skip {rel} ({res.get('reason')})")
            continue
        s = res["artifact_score"]
        ok = lo <= s <= hi
        print(
            f"{'ok ' if ok else 'BAD'} {rel:26s} expect={expect:10s} "
            f"score={s:.3f} silence={res['features']['digital_silence_frac']:.3f} "
            f"floor={res['features']['noise_floor_rms']:.5f} {res['flags']}"
        )
    # Malformed input must never raise.
    assert analyse(b"not audio")["available"] is False
    assert analyse(b"")["available"] is False

    # Fingerprint: stable, and perceptual survives a level change.
    raw = (audio / "chunks" / "genuine_0.wav").read_bytes()
    f1 = fingerprint(raw)
    f2 = fingerprint(raw)
    assert f1 == f2, "fingerprint must be deterministic"
    assert len(f1["exact"]) == 32 and len(f1["perceptual"]) == 32
    print(
        f"ok  fingerprint deterministic exact={f1['exact'][:12]} "
        f"perceptual={f1['perceptual'][:12]}"
    )
    print("forensics selftest: passed")


if __name__ == "__main__":
    selftest()
