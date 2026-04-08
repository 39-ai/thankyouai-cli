#!/usr/bin/env python3
"""E2E smoke tests — hits the real ThankYou AI API.

Usage:
    export TY_KEY="tk_..."
    python tests/e2e.py
"""

from __future__ import annotations

import os
import sys
import json
import time
from typing import Callable

import requests

BASE = os.environ.get("TY_BASE", "https://api.thankyouai.com/open/v1")
KEY = os.environ.get("TY_KEY", "")
WS = os.environ.get("TY_WS", "")


def headers():
    h = {"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}
    if WS:
        h["x-workspace-id"] = WS
    return h


# ─── helpers ───────────────────────────────────────────────────────────────

OK = "\033[32m✓\033[0m"
FAIL = "\033[31m✗\033[0m"
SKIP = "\033[33m-\033[0m"
results: list[tuple[str, str, str]] = []  # (name, status, detail)


def run(name: str, fn: Callable) -> None:
    print(f"  {name} … ", end="", flush=True)
    try:
        detail = fn() or ""
        print(f"{OK} {detail}")
        results.append((name, "pass", detail))
    except AssertionError as e:
        print(f"{FAIL} {e}")
        results.append((name, "fail", str(e)))
    except Exception as e:
        print(f"{FAIL} {e}")
        results.append((name, "error", str(e)))


def submit(model: str, input_params: dict, submit_timeout: float = 60) -> str:
    r = requests.post(f"{BASE}/generate", json={"model": model, "input": input_params}, headers=headers(), timeout=submit_timeout)
    r.raise_for_status()
    data = r.json()
    return data["id"]


def poll(gen_id: str, timeout: float = 300, interval: float = 5) -> dict:
    deadline = time.time() + timeout
    while True:
        r = requests.get(f"{BASE}/generations/{gen_id}", headers=headers(), timeout=15)
        r.raise_for_status()
        data = r.json()
        status = data.get("status")
        print(f"\n    [{status}] {int(data.get('progress', 0)*100)}%", end="", flush=True)
        if status in ("succeeded", "failed", "cancelled"):
            print()
            return data
        if time.time() > deadline:
            raise TimeoutError(f"timed out after {timeout}s")
        time.sleep(interval)


# ─── test cases ────────────────────────────────────────────────────────────

def test_models_list():
    r = requests.get(f"{BASE}/models", headers=headers(), timeout=15)
    r.raise_for_status()
    models = r.json().get("models", [])
    assert len(models) > 0, "no models returned"
    return f"{len(models)} models"


def test_voices_list():
    r = requests.get(f"{BASE}/voices", headers=headers(), timeout=15)
    r.raise_for_status()
    data = r.json()
    voices = data if isinstance(data, list) else data.get("voices", [])
    assert len(voices) > 0, "no voices returned"
    return f"{len(voices)} voices"


def test_nano_banana_t2i():
    gen_id = submit("google/nano-banana/text-to-image", {
        "prompt": "a white cat sitting on a wooden table, studio lighting",
        "aspect_ratio": "1:1",
    })
    result = poll(gen_id, timeout=120)
    assert result["status"] == "succeeded", f"status={result['status']} err={result.get('error')}"
    url = result["output"][0]["url"]
    assert url.startswith("http"), f"bad url: {url}"
    return url.split("/")[-1]


def test_seedance_v2_t2v():
    # Seedance V2 can be slow; retry once on retryable provider errors
    params = {
        "prompt": "a red ball bouncing on a wooden floor, slow motion",
        "aspect_ratio": "16:9",
        "duration": 5,
    }
    for attempt in range(2):
        gen_id = submit("bytedance/seedance/v2/text-to-video", params, submit_timeout=120)
        result = poll(gen_id, timeout=600, interval=10)
        err = result.get("error") or {}
        if result["status"] == "succeeded":
            break
        if err.get("retryable") and attempt == 0:
            print(f"\n    retrying (attempt {attempt+1}): {err.get('message')}", flush=True)
            continue
        assert False, f"status={result['status']} err={err}"
    url = result["output"][0]["url"]
    assert url.startswith("http"), f"bad url: {url}"
    return url.split("/")[-1]


def test_wan_t2v():
    """Faster video test using Wan 2.6 (default video model)."""
    gen_id = submit("wan/v2.6/text-to-video", {
        "prompt": "a calm ocean wave rolling onto a sandy beach",
        "size": "1280*720",
        "duration": 5,
    }, submit_timeout=120)
    result = poll(gen_id, timeout=300, interval=8)
    assert result["status"] == "succeeded", f"status={result['status']} err={result.get('error')}"
    url = result["output"][0]["url"]
    assert url.startswith("http"), f"bad url: {url}"
    return url.split("/")[-1]


def test_fish_audio_basic():
    # Get first available voice
    r = requests.get(f"{BASE}/voices", headers=headers(), timeout=15)
    r.raise_for_status()
    data = r.json()
    voices = data if isinstance(data, list) else data.get("voices", [])
    assert voices, "no voices available"
    voice_id = voices[0].get("voice_id") or voices[0].get("id")

    gen_id = submit("fish-audio/text-to-speech", {
        "text": "Hello! This is a test of the ThankYou AI text to speech API.",
        "voice_id": voice_id,
        "format": "mp3",
    })
    result = poll(gen_id, timeout=60, interval=3)
    assert result["status"] == "succeeded", f"status={result['status']} err={result.get('error')}"
    url = result["output"][0]["url"]
    assert url.startswith("http"), f"bad url: {url}"
    return f"voice={voice_id[:12]}… → {url.split('/')[-1]}"


def test_fish_audio_advanced():
    r = requests.get(f"{BASE}/voices", headers=headers(), timeout=15)
    r.raise_for_status()
    data = r.json()
    voices = data if isinstance(data, list) else data.get("voices", [])
    voice_id = voices[0].get("voice_id") or voices[0].get("id")

    gen_id = submit("fish-audio/text-to-speech", {
        "text": "Advanced voice synthesis test with custom parameters.",
        "voice_id": voice_id,
        "format": "wav",
        "temperature": 0.7,
        "top_p": 0.9,
        "latency": "balanced",
    })
    result = poll(gen_id, timeout=60, interval=3)
    assert result["status"] == "succeeded", f"status={result['status']} err={result.get('error')}"
    url = result["output"][0]["url"]
    return url.split("/")[-1]


def test_status_and_list():
    # Just check the generations list endpoint
    r = requests.get(f"{BASE}/generations", params={"page": 1, "page_size": 5}, headers=headers(), timeout=15)
    r.raise_for_status()
    data = r.json()
    items = data.get("generations", [])
    return f"{len(items)} recent generations"


# ─── main ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if not KEY:
        print("Error: set TY_KEY environment variable")
        sys.exit(1)

    print(f"\nThankYou AI E2E — {BASE}\n")

    print("[ API / Meta ]")
    run("models list", test_models_list)
    run("voices list", test_voices_list)
    run("generations list", test_status_and_list)

    print("\n[ Image — nano-banana ]")
    run("text-to-image", test_nano_banana_t2i)

    print("\n[ Audio — fish-audio ]")
    run("TTS basic (mp3)", test_fish_audio_basic)
    run("TTS advanced (wav, temp+latency)", test_fish_audio_advanced)

    print("\n[ Video ]")
    run("wan/v2.6 text-to-video", test_wan_t2v)
    if "--slow" in sys.argv:
        run("seedance/v2 text-to-video (slow, ~10min)", test_seedance_v2_t2v)
    else:
        print(f"  {SKIP} seedance/v2 text-to-video — skipped (pass --slow to run)")

    # ── summary ──
    passed = sum(1 for _, s, _ in results if s == "pass")
    failed = sum(1 for _, s, _ in results if s != "pass")
    total = len(results)
    print(f"\n{'─'*50}")
    print(f"Results: {passed}/{total} passed", end="")
    if failed:
        print(f"  ({failed} failed)")
        for name, status, detail in results:
            if status != "pass":
                print(f"  {FAIL} {name}: {detail}")
    else:
        print(f"  {OK}")
    print()
    sys.exit(0 if failed == 0 else 1)
