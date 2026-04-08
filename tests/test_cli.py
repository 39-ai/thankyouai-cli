"""Unit tests for thankyouai CLI commands.

Uses the Click test runner and `responses` to mock HTTP calls.
No real network requests are made.
"""

from __future__ import annotations

import json
from unittest.mock import patch, MagicMock

import pytest
import responses as resp_lib
from click.testing import CliRunner

from thankyouai.cli import main
from thankyouai.utils import emit, progress_bar


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def env(monkeypatch):
    monkeypatch.setenv("TY_KEY", "tk_test_key")
    monkeypatch.setenv("TY_WS", "ws_test")


BASE = "https://api.thankyouai.com/open/v1"


# ---------------------------------------------------------------------------
# CLI bootstrap
# ---------------------------------------------------------------------------


class TestVersion:
    def test_version(self, runner):
        result = runner.invoke(main, ["--version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output

    def test_help(self, runner):
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "generate" in result.output


# ---------------------------------------------------------------------------
# models command
# ---------------------------------------------------------------------------


class TestModels:
    @resp_lib.activate
    def test_lists_models_human(self, runner, env):
        resp_lib.add(
            resp_lib.GET,
            f"{BASE}/models",
            json={"models": [
                {"id": "google/nano-banana/text-to-image", "category": "image-generation", "display_name": "Nano Banana"},
            ]},
        )
        result = runner.invoke(main, ["models"])
        assert result.exit_code == 0
        assert "nano-banana" in result.output

    @resp_lib.activate
    def test_lists_models_json(self, runner, env):
        resp_lib.add(
            resp_lib.GET,
            f"{BASE}/models",
            json={"models": [{"id": "m1", "category": "image-generation", "display_name": "M1"}]},
        )
        result = runner.invoke(main, ["--json", "models"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert isinstance(data, list)
        assert data[0]["id"] == "m1"

    @resp_lib.activate
    def test_category_filter(self, runner, env):
        resp_lib.add(
            resp_lib.GET,
            f"{BASE}/models",
            json={"models": [
                {"id": "img-model", "category": "image-generation", "display_name": "Img"},
                {"id": "vid-model", "category": "video-generation", "display_name": "Vid"},
            ]},
        )
        result = runner.invoke(main, ["models", "--category", "image-generation"])
        assert result.exit_code == 0
        assert "img-model" in result.output
        assert "vid-model" not in result.output


# ---------------------------------------------------------------------------
# voices command
# ---------------------------------------------------------------------------


class TestVoices:
    @resp_lib.activate
    def test_lists_voices(self, runner, env):
        resp_lib.add(
            resp_lib.GET,
            f"{BASE}/voices",
            json=[{"voice_id": "v123", "name": "Alice"}],
        )
        result = runner.invoke(main, ["voices"])
        assert result.exit_code == 0
        assert "v123" in result.output
        assert "Alice" in result.output


# ---------------------------------------------------------------------------
# generate image
# ---------------------------------------------------------------------------


class TestGenerateImage:
    @resp_lib.activate
    def test_no_wait_returns_gen_id(self, runner, env):
        resp_lib.add(
            resp_lib.POST,
            f"{BASE}/generate",
            json={"id": "gen_abc", "status": "queued"},
        )
        result = runner.invoke(
            main, ["generate", "image", "A cat", "--no-wait"]
        )
        assert result.exit_code == 0
        assert "gen_abc" in result.output

    @resp_lib.activate
    def test_wait_prints_output_url(self, runner, env):
        resp_lib.add(resp_lib.POST, f"{BASE}/generate", json={"id": "gen_xyz", "status": "queued"})
        resp_lib.add(
            resp_lib.GET,
            f"{BASE}/generations/gen_xyz",
            json={"id": "gen_xyz", "status": "succeeded", "output": [{"url": "https://cdn.example.com/img.png"}], "progress": 1.0},
        )
        result = runner.invoke(main, ["generate", "image", "A cat"])
        assert result.exit_code == 0
        assert "https://cdn.example.com/img.png" in result.output

    @resp_lib.activate
    def test_wait_failed_exits_nonzero(self, runner, env):
        resp_lib.add(resp_lib.POST, f"{BASE}/generate", json={"id": "gen_f", "status": "queued"})
        resp_lib.add(
            resp_lib.GET,
            f"{BASE}/generations/gen_f",
            json={"id": "gen_f", "status": "failed", "error": {"code": "provider_failed", "message": "provider error: bad input"}, "progress": 0.0},
        )
        result = runner.invoke(main, ["generate", "image", "A cat"])
        assert result.exit_code != 0

    @resp_lib.activate
    def test_with_aspect_ratio(self, runner, env):
        resp_lib.add(resp_lib.POST, f"{BASE}/generate", json={"id": "gen_ar", "status": "queued"})
        result = runner.invoke(
            main, ["generate", "image", "Landscape", "--aspect-ratio", "16:9", "--no-wait"]
        )
        assert result.exit_code == 0
        body = json.loads(resp_lib.calls[0].request.body)
        assert body["input"]["aspect_ratio"] == "16:9"

    @resp_lib.activate
    def test_with_reference_url(self, runner, env):
        resp_lib.add(resp_lib.POST, f"{BASE}/generate", json={"id": "gen_ref", "status": "queued"})
        result = runner.invoke(
            main,
            ["generate", "image", "Edit this", "--reference", "https://example.com/img.jpg", "--no-wait"],
        )
        assert result.exit_code == 0
        body = json.loads(resp_lib.calls[0].request.body)
        assert body["input"]["reference_assets"][0]["url"] == "https://example.com/img.jpg"

    @resp_lib.activate
    def test_json_output_no_wait(self, runner, env):
        resp_lib.add(resp_lib.POST, f"{BASE}/generate", json={"id": "gen_j", "status": "queued"})
        result = runner.invoke(main, ["--json", "generate", "image", "A cat", "--no-wait"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["id"] == "gen_j"


# ---------------------------------------------------------------------------
# generate video
# ---------------------------------------------------------------------------


class TestGenerateVideo:
    @resp_lib.activate
    def test_text_to_video_no_wait(self, runner, env):
        resp_lib.add(resp_lib.POST, f"{BASE}/generate", json={"id": "gen_vid", "status": "queued"})
        result = runner.invoke(main, ["generate", "video", "A sunset", "--no-wait"])
        assert result.exit_code == 0
        assert "gen_vid" in result.output
        body = json.loads(resp_lib.calls[0].request.body)
        assert body["input"]["prompt"] == "A sunset"
        assert body["model"] == "wan/v2.6/text-to-video"

    @resp_lib.activate
    def test_text_to_video_wait_prints_url(self, runner, env):
        resp_lib.add(resp_lib.POST, f"{BASE}/generate", json={"id": "gen_v2", "status": "queued"})
        resp_lib.add(
            resp_lib.GET,
            f"{BASE}/generations/gen_v2",
            json={"id": "gen_v2", "status": "succeeded", "output": [{"url": "https://cdn.example.com/video.mp4"}], "progress": 1.0},
        )
        result = runner.invoke(main, ["generate", "video", "Ocean waves"])
        assert result.exit_code == 0
        assert "https://cdn.example.com/video.mp4" in result.output

    @resp_lib.activate
    def test_image_to_video(self, runner, env):
        resp_lib.add(resp_lib.POST, f"{BASE}/generate", json={"id": "gen_i2v", "status": "queued"})
        result = runner.invoke(
            main,
            ["generate", "video", "Animate this", "--image", "https://example.com/img.jpg",
             "--model", "wan/v2.6/image-to-video", "--no-wait"],
        )
        assert result.exit_code == 0
        body = json.loads(resp_lib.calls[0].request.body)
        assets = body["input"]["reference_assets"]
        assert assets[0]["role"] == "first_frame"
        assert assets[0]["url"] == "https://example.com/img.jpg"

    @resp_lib.activate
    def test_first_last_frame(self, runner, env):
        resp_lib.add(resp_lib.POST, f"{BASE}/generate", json={"id": "gen_fl", "status": "queued"})
        result = runner.invoke(
            main,
            ["generate", "video", "--image", "https://example.com/start.jpg",
             "--end-image", "https://example.com/end.jpg",
             "--model", "kling/v3.0/pro/image-to-video", "--no-wait"],
        )
        assert result.exit_code == 0
        body = json.loads(resp_lib.calls[0].request.body)
        assets = body["input"]["reference_assets"]
        roles = {a["role"] for a in assets}
        assert "first_frame" in roles
        assert "last_frame" in roles

    @resp_lib.activate
    def test_with_aspect_ratio_and_duration(self, runner, env):
        resp_lib.add(resp_lib.POST, f"{BASE}/generate", json={"id": "gen_vx", "status": "queued"})
        result = runner.invoke(
            main,
            ["generate", "video", "Landscape", "--aspect-ratio", "16:9", "--duration", "10", "--no-wait"],
        )
        assert result.exit_code == 0
        body = json.loads(resp_lib.calls[0].request.body)
        assert body["input"]["aspect_ratio"] == "16:9"
        assert body["input"]["duration"] == 10

    def test_no_prompt_no_image_errors(self, runner, env):
        result = runner.invoke(main, ["generate", "video"])
        assert result.exit_code != 0

    @resp_lib.activate
    def test_failed_video_exits_nonzero(self, runner, env):
        resp_lib.add(resp_lib.POST, f"{BASE}/generate", json={"id": "gen_vf", "status": "queued"})
        resp_lib.add(
            resp_lib.GET,
            f"{BASE}/generations/gen_vf",
            json={"id": "gen_vf", "status": "failed", "error": {"message": "provider error"}, "progress": 0.0},
        )
        result = runner.invoke(main, ["generate", "video", "A cat"])
        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# generate audio
# ---------------------------------------------------------------------------


class TestGenerateAudio:
    @resp_lib.activate
    def test_no_wait(self, runner, env):
        resp_lib.add(resp_lib.POST, f"{BASE}/generate", json={"id": "gen_audio", "status": "queued"})
        result = runner.invoke(
            main, ["generate", "audio", "Hello", "--voice-id", "v123", "--no-wait"]
        )
        assert result.exit_code == 0
        assert "gen_audio" in result.output

    @resp_lib.activate
    def test_wait_prints_url(self, runner, env):
        resp_lib.add(resp_lib.POST, f"{BASE}/generate", json={"id": "gen_a2", "status": "queued"})
        resp_lib.add(
            resp_lib.GET,
            f"{BASE}/generations/gen_a2",
            json={"id": "gen_a2", "status": "succeeded", "output": [{"url": "https://cdn.example.com/audio.mp3"}], "progress": 1.0},
        )
        result = runner.invoke(
            main, ["generate", "audio", "Hello", "--voice-id", "v123"]
        )
        assert result.exit_code == 0
        assert "https://cdn.example.com/audio.mp3" in result.output

    @resp_lib.activate
    def test_passes_format(self, runner, env):
        resp_lib.add(resp_lib.POST, f"{BASE}/generate", json={"id": "gen_wav", "status": "queued"})
        result = runner.invoke(
            main, ["generate", "audio", "Hi", "--voice-id", "v1", "--format", "wav", "--no-wait"]
        )
        assert result.exit_code == 0
        body = json.loads(resp_lib.calls[0].request.body)
        assert body["input"]["format"] == "wav"


# ---------------------------------------------------------------------------
# status command
# ---------------------------------------------------------------------------


class TestStatus:
    @resp_lib.activate
    def test_get_status(self, runner, env):
        resp_lib.add(
            resp_lib.GET,
            f"{BASE}/generations/gen_abc",
            json={"id": "gen_abc", "status": "running", "progress": 0.5},
        )
        result = runner.invoke(main, ["status", "gen_abc"])
        assert result.exit_code == 0
        assert "running" in result.output

    @resp_lib.activate
    def test_poll_status(self, runner, env):
        resp_lib.add(
            resp_lib.GET,
            f"{BASE}/generations/gen_abc",
            json={"id": "gen_abc", "status": "succeeded", "progress": 1.0},
        )
        result = runner.invoke(main, ["status", "gen_abc", "--poll"])
        assert result.exit_code == 0
        assert "succeeded" in result.output


# ---------------------------------------------------------------------------
# generations list
# ---------------------------------------------------------------------------


class TestGenerations:
    @resp_lib.activate
    def test_lists_generations(self, runner, env):
        resp_lib.add(
            resp_lib.GET,
            f"{BASE}/generations",
            json={"generations": [{"id": "gen_1", "status": "succeeded", "model": "m1", "created_at": "2026-04-08T00:00:00Z"}], "total": 1, "page": 1, "page_size": 20},
        )
        result = runner.invoke(main, ["generations"])
        assert result.exit_code == 0
        assert "gen_1" in result.output
        assert "succeeded" in result.output


# ---------------------------------------------------------------------------
# upload command
# ---------------------------------------------------------------------------


class TestUpload:
    @resp_lib.activate
    def test_upload_returns_url(self, runner, env, tmp_path):
        img = tmp_path / "test.jpg"
        img.write_bytes(b"\xff\xd8\xff" + b"x" * 100)

        resp_lib.add(
            resp_lib.POST,
            f"{BASE}/files",
            json={
                "file_id": "file_abc",
                "upload_url": "https://storage.example.com/put?sig=abc",
                "url": "https://cdn.example.com/file_abc.jpg",
                "content_type": "image/jpeg",
                "size_bytes": 103,
                "url_expires_at": "2026-04-09T00:00:00Z",
                "upload_url_expires_at": "2026-04-08T00:15:00Z",
            },
        )
        resp_lib.add(resp_lib.PUT, "https://storage.example.com/put", status=200, body=b"")
        result = runner.invoke(main, ["upload", str(img)])
        assert result.exit_code == 0
        assert "https://cdn.example.com/file_abc.jpg" in result.output


# ---------------------------------------------------------------------------
# usage command
# ---------------------------------------------------------------------------


class TestUsage:
    @resp_lib.activate
    def test_usage_human(self, runner, env):
        resp_lib.add(
            resp_lib.GET,
            f"{BASE}/usage",
            json={
                "period_days": 30,
                "total_tasks": 42,
                "total_succeeded": 40,
                "total_failed": 2,
                "total_cost": 3.14,
                "currency": "points",
                "by_model": [{"model": "google/nano-banana/text-to-image", "total_tasks": 42, "total_cost": 3.14}],
                "daily": [],
            },
        )
        result = runner.invoke(main, ["usage"])
        assert result.exit_code == 0
        assert "42" in result.output
        assert "3.14" in result.output


# ---------------------------------------------------------------------------
# utils
# ---------------------------------------------------------------------------


class TestUtils:
    def test_emit_json(self, capsys):
        emit({"key": "value"}, json_output=True)
        out = capsys.readouterr().out
        assert json.loads(out) == {"key": "value"}

    def test_emit_human_message(self, capsys):
        emit({"key": "value"}, json_output=False, message="Hello")
        out = capsys.readouterr().out
        assert "Hello" in out
        assert "key" in out

    def test_emit_list(self, capsys):
        emit(["a", "b"], json_output=False)
        out = capsys.readouterr().out
        assert "a" in out
        assert "b" in out

    def test_progress_bar_shows_percent(self, capsys):
        progress_bar({"status": "running", "progress": 0.5})
        err = capsys.readouterr().err
        assert "50" in err
