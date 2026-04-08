"""ThankYou AI API client — thin wrapper over requests."""

from __future__ import annotations

import os
import time
from pathlib import Path

import requests

BASE_URL = os.environ.get("TY_BASE", "https://api.thankyouai.com/open/v1")
ENV_KEY = "TY_KEY"
ENV_WS = "TY_WS"

POLL_TERMINAL = {"succeeded", "failed", "cancelled"}


def _get_api_key() -> str:
    key = os.environ.get(ENV_KEY, "")
    if not key:
        raise RuntimeError(
            f"API key not set. Export {ENV_KEY}=<your_key> or pass --api-key."
        )
    return key


def _headers(api_key: str | None = None, workspace_id: str | None = None) -> dict:
    key = api_key or _get_api_key()
    h = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }
    ws = workspace_id or os.environ.get(ENV_WS)
    if ws:
        h["x-workspace-id"] = ws
    return h


def list_models(api_key: str | None = None, workspace_id: str | None = None) -> list:
    r = requests.get(
        f"{BASE_URL}/models",
        headers=_headers(api_key, workspace_id),
        timeout=30,
    )
    r.raise_for_status()
    return r.json().get("models", [])


def get_model_detail(
    model_id: str,
    api_key: str | None = None,
    workspace_id: str | None = None,
) -> dict:
    r = requests.get(
        f"{BASE_URL}/models/detail",
        params={"model_id": model_id},
        headers=_headers(api_key, workspace_id),
        timeout=30,
    )
    r.raise_for_status()
    return r.json()


def list_voices(api_key: str | None = None, workspace_id: str | None = None) -> list:
    r = requests.get(
        f"{BASE_URL}/voices",
        headers=_headers(api_key, workspace_id),
        timeout=30,
    )
    r.raise_for_status()
    data = r.json()
    return data if isinstance(data, list) else data.get("voices", [data])


def submit_generation(
    model: str,
    input_params: dict,
    api_key: str | None = None,
    workspace_id: str | None = None,
) -> dict:
    r = requests.post(
        f"{BASE_URL}/generate",
        json={"model": model, "input": input_params},
        headers=_headers(api_key, workspace_id),
        timeout=60,
    )
    r.raise_for_status()
    return r.json()


def get_generation(
    gen_id: str,
    api_key: str | None = None,
    workspace_id: str | None = None,
) -> dict:
    r = requests.get(
        f"{BASE_URL}/generations/{gen_id}",
        headers=_headers(api_key, workspace_id),
        timeout=30,
    )
    r.raise_for_status()
    return r.json()


def list_generations(
    page: int = 1,
    page_size: int = 20,
    api_key: str | None = None,
    workspace_id: str | None = None,
) -> dict:
    r = requests.get(
        f"{BASE_URL}/generations",
        params={"page": page, "page_size": page_size},
        headers=_headers(api_key, workspace_id),
        timeout=30,
    )
    r.raise_for_status()
    return r.json()


def poll_generation(
    gen_id: str,
    interval: float = 5.0,
    timeout: float = 300.0,
    api_key: str | None = None,
    workspace_id: str | None = None,
    on_progress=None,
) -> dict:
    """Poll until terminal status, calling on_progress(result) each tick."""
    deadline = time.time() + timeout
    while True:
        result = get_generation(gen_id, api_key, workspace_id)
        if on_progress:
            on_progress(result)
        if result.get("status") in POLL_TERMINAL:
            return result
        if time.time() >= deadline:
            raise TimeoutError(f"Generation {gen_id!r} did not complete within {timeout}s")
        time.sleep(interval)


def upload_file(
    file_path: str,
    content_type: str | None = None,
    api_key: str | None = None,
    workspace_id: str | None = None,
) -> dict:
    """Upload a local file via presigned PUT and return the session response."""
    p = Path(file_path)
    size = p.stat().st_size

    if content_type is None:
        suffix = p.suffix.lower()
        content_type = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
            ".webp": "image/webp",
            ".mp3": "audio/mpeg",
            ".wav": "audio/wav",
            ".mp4": "video/mp4",
        }.get(suffix, "application/octet-stream")

    # Step 1: create upload session
    h = _headers(api_key, workspace_id)
    del h["Content-Type"]  # let requests set for JSON body
    h["Content-Type"] = "application/json"
    r = requests.post(
        f"{BASE_URL}/files",
        json={"content_type": content_type, "size_bytes": size, "filename": p.name},
        headers=h,
        timeout=30,
    )
    r.raise_for_status()
    session = r.json()

    # Step 2: PUT file bytes to presigned URL
    with open(file_path, "rb") as f:
        put_r = requests.put(
            session["upload_url"],
            data=f,
            headers={"Content-Type": content_type},
            timeout=120,
        )
    put_r.raise_for_status()

    return session


def get_usage(
    period_days: int = 30,
    api_key: str | None = None,
    workspace_id: str | None = None,
) -> dict:
    r = requests.get(
        f"{BASE_URL}/usage",
        params={"period_days": period_days},
        headers=_headers(api_key, workspace_id),
        timeout=30,
    )
    r.raise_for_status()
    return r.json()
