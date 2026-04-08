#!/usr/bin/env python3
"""ThankYou AI CLI — async generation platform client.

Usage (quick-start):
    export TY_KEY="tk_..."
    thankyouai models
    thankyouai generate image "A mountain lake at golden hour"
    thankyouai generate audio "Hello from ThankYou AI." --voice-id <id>
    thankyouai status <generation_id>
    thankyouai upload ./photo.jpg
    thankyouai usage
"""

from __future__ import annotations

import json
import sys
from typing import Optional

import click

from thankyouai import __version__
from thankyouai import client as api
from thankyouai.utils import emit, error_exit, progress_bar

# ---------------------------------------------------------------------------
# Root group
# ---------------------------------------------------------------------------


@click.group()
@click.version_option(__version__, prog_name="thankyouai")
@click.option("--api-key", envvar="TY_KEY", default=None, help="API key (or set TY_KEY)")
@click.option("--workspace-id", envvar="TY_WS", default=None, help="Workspace ID (or set TY_WS)")
@click.option("--json", "json_output", is_flag=True, default=False, help="Output raw JSON")
@click.pass_context
def main(ctx, api_key: str, workspace_id: str, json_output: bool):
    """ThankYou AI — async image/audio/video generation CLI."""
    ctx.ensure_object(dict)
    ctx.obj["api_key"] = api_key
    ctx.obj["workspace_id"] = workspace_id
    ctx.obj["json_output"] = json_output


# ---------------------------------------------------------------------------
# models
# ---------------------------------------------------------------------------


@main.command()
@click.option("--category", default=None, help="Filter by category (e.g. image-generation)")
@click.pass_context
def models(ctx, category: Optional[str]):
    """List available generation models."""
    try:
        items = api.list_models(ctx.obj["api_key"], ctx.obj["workspace_id"])
    except Exception as e:
        error_exit(str(e))

    if category:
        items = [m for m in items if m.get("category") == category]

    jo = ctx.obj["json_output"]
    if jo:
        emit(items, json_output=True)
    else:
        click.echo(f"{'ID':<50} {'Category':<20} {'Name'}")
        click.echo("-" * 90)
        for m in items:
            click.echo(f"{m.get('id',''):<50} {m.get('category',''):<20} {m.get('display_name','')}")


@main.command("model-detail")
@click.argument("model_id")
@click.pass_context
def model_detail(ctx, model_id: str):
    """Show field schema for MODEL_ID."""
    try:
        detail = api.get_model_detail(model_id, ctx.obj["api_key"], ctx.obj["workspace_id"])
    except Exception as e:
        error_exit(str(e))

    emit(detail, json_output=ctx.obj["json_output"])


# ---------------------------------------------------------------------------
# voices
# ---------------------------------------------------------------------------


@main.command()
@click.pass_context
def voices(ctx):
    """List available TTS voices."""
    try:
        items = api.list_voices(ctx.obj["api_key"], ctx.obj["workspace_id"])
    except Exception as e:
        error_exit(str(e))

    jo = ctx.obj["json_output"]
    if jo:
        emit(items, json_output=True)
    else:
        if isinstance(items, list):
            for v in items:
                if isinstance(v, dict):
                    vid = v.get("voice_id") or v.get("id", "")
                    name = v.get("name", "")
                    click.echo(f"{vid:<38} {name}")
                else:
                    click.echo(str(v))
        else:
            emit(items, json_output=False)


# ---------------------------------------------------------------------------
# generate group
# ---------------------------------------------------------------------------


@main.group()
def generate():
    """Submit a generation task (image or audio)."""


@generate.command("image")
@click.argument("prompt")
@click.option(
    "--model",
    default="google/nano-banana/text-to-image",
    show_default=True,
    help="Model ID",
)
@click.option("--aspect-ratio", default=None, help="e.g. 16:9, 1:1, 9:16")
@click.option("--size", default=None, help="e.g. 1024x1024 (used by /pro and /v2)")
@click.option("--seed", type=int, default=None, help="Reproducibility seed")
@click.option("--num-images", type=int, default=None, help="Number of images (model-dependent)")
@click.option("--reference", default=None, metavar="URL", help="Reference image URL")
@click.option(
    "--wait/--no-wait",
    default=True,
    show_default=True,
    help="Poll until complete and print output URL(s)",
)
@click.option("--timeout", type=float, default=300.0, show_default=True, help="Poll timeout (s)")
@click.pass_context
def generate_image(
    ctx,
    prompt: str,
    model: str,
    aspect_ratio: Optional[str],
    size: Optional[str],
    seed: Optional[int],
    num_images: int,
    reference: Optional[str],
    wait: bool,
    timeout: float,
):
    """Generate an image from PROMPT."""
    params: dict = {"prompt": prompt}
    if num_images is not None:
        params["num_images"] = num_images
    if aspect_ratio:
        params["aspect_ratio"] = aspect_ratio
    if size:
        params["image_size"] = size
    if seed is not None:
        params["seed"] = seed
    if reference:
        params["reference_assets"] = [{"role": "reference", "url": reference}]

    jo = ctx.obj["json_output"]
    try:
        gen = api.submit_generation(model, params, ctx.obj["api_key"], ctx.obj["workspace_id"])
    except Exception as e:
        error_exit(str(e))

    if not wait:
        emit(gen, json_output=jo, message=f"Queued: {gen.get('id')}")
        return

    gen_id = gen["id"]
    click.echo(f"Queued {gen_id} — polling…", err=True)
    try:
        result = api.poll_generation(
            gen_id,
            timeout=timeout,
            api_key=ctx.obj["api_key"],
            workspace_id=ctx.obj["workspace_id"],
            on_progress=progress_bar if not jo else None,
        )
    except Exception as e:
        error_exit(str(e))

    if jo:
        emit(result, json_output=True)
    else:
        status = result.get("status")
        if status == "succeeded":
            for out in result.get("output", []):
                click.echo(out.get("url", out))
        else:
            err = result.get("error") or {}
            click.echo(f"Failed: {err.get('message', status)}", err=True)
            sys.exit(1)


@generate.command("audio")
@click.argument("text")
@click.option(
    "--model",
    default="fish-audio/text-to-speech",
    show_default=True,
    help="Model ID",
)
@click.option("--voice-id", required=True, help="Voice model ID (see `thankyouai voices`)")
@click.option(
    "--format",
    "fmt",
    default="mp3",
    type=click.Choice(["mp3", "wav", "ogg"]),
    show_default=True,
)
@click.option("--temperature", type=float, default=None, help="Expressiveness (0–1)")
@click.option("--top-p", type=float, default=None, help="Nucleus sampling threshold (0–1)")
@click.option(
    "--latency",
    default=None,
    type=click.Choice(["normal", "balanced", "fast"]),
)
@click.option(
    "--wait/--no-wait",
    default=True,
    show_default=True,
    help="Poll until complete and print output URL",
)
@click.option("--timeout", type=float, default=60.0, show_default=True, help="Poll timeout (s)")
@click.pass_context
def generate_audio(
    ctx,
    text: str,
    model: str,
    voice_id: str,
    fmt: str,
    temperature: Optional[float],
    top_p: Optional[float],
    latency: Optional[str],
    wait: bool,
    timeout: float,
):
    """Generate speech from TEXT."""
    params: dict = {"text": text, "voice_id": voice_id, "format": fmt}
    if temperature is not None:
        params["temperature"] = temperature
    if top_p is not None:
        params["top_p"] = top_p
    if latency:
        params["latency"] = latency

    jo = ctx.obj["json_output"]
    try:
        gen = api.submit_generation(model, params, ctx.obj["api_key"], ctx.obj["workspace_id"])
    except Exception as e:
        error_exit(str(e))

    if not wait:
        emit(gen, json_output=jo, message=f"Queued: {gen.get('id')}")
        return

    gen_id = gen["id"]
    click.echo(f"Queued {gen_id} — polling…", err=True)
    try:
        result = api.poll_generation(
            gen_id,
            interval=3.0,
            timeout=timeout,
            api_key=ctx.obj["api_key"],
            workspace_id=ctx.obj["workspace_id"],
            on_progress=progress_bar if not jo else None,
        )
    except Exception as e:
        error_exit(str(e))

    if jo:
        emit(result, json_output=True)
    else:
        status = result.get("status")
        if status == "succeeded":
            for out in result.get("output", []):
                click.echo(out.get("url", out))
        else:
            err = result.get("error") or {}
            click.echo(f"Failed: {err.get('message', status)}", err=True)
            sys.exit(1)


@generate.command("video")
@click.argument("prompt", default="", required=False)
@click.option(
    "--model",
    default="wan/v2.6/text-to-video",
    show_default=True,
    help="Model ID (text-to-video, image-to-video, etc.)",
)
@click.option("--image", default=None, metavar="URL", help="Start image URL (image-to-video)")
@click.option("--end-image", default=None, metavar="URL", help="End image URL (first-last-frame)")
@click.option("--duration", type=int, default=None, help="Duration in seconds (5 or 10)")
@click.option(
    "--aspect-ratio",
    default=None,
    type=click.Choice(["16:9", "9:16", "1:1", "4:3", "3:4"]),
    help="Video aspect ratio",
)
@click.option("--negative-prompt", default=None, help="What to avoid in the video")
@click.option("--seed", type=int, default=None)
@click.option(
    "--wait/--no-wait",
    default=True,
    show_default=True,
    help="Poll until complete and print output URL",
)
@click.option("--timeout", type=float, default=600.0, show_default=True, help="Poll timeout (s)")
@click.pass_context
def generate_video(
    ctx,
    prompt: str,
    model: str,
    image: Optional[str],
    end_image: Optional[str],
    duration: Optional[int],
    aspect_ratio: Optional[str],
    negative_prompt: Optional[str],
    seed: Optional[int],
    wait: bool,
    timeout: float,
):
    """Generate a video from PROMPT (and optional reference images).

    \b
    Modes (determined by --model and --image flags):
      text-to-video      thankyouai generate video "A sunset over ocean"
      image-to-video     thankyouai generate video "Animate it" --image URL
      first-last-frame   thankyouai generate video "" --image START_URL --end-image END_URL
    """
    if not prompt and not image:
        raise click.UsageError("Provide PROMPT or --image (or both).")

    # Determine mode from flags
    if image and end_image:
        mode = "first-last-frame-to-video"
    elif image:
        mode = "image-to-video"
    else:
        mode = "text-to-video"

    params: dict = {}
    if prompt:
        params["prompt"] = prompt
    if negative_prompt:
        params["negative_prompt"] = negative_prompt
    if aspect_ratio:
        params["aspect_ratio"] = aspect_ratio
    if duration is not None:
        params["duration"] = duration
    if seed is not None:
        params["seed"] = seed

    # Build reference_assets for image inputs
    if image and end_image:
        params["reference_assets"] = [
            {"role": "first_frame", "url": image},
            {"role": "last_frame", "url": end_image},
        ]
    elif image:
        params["reference_assets"] = [{"role": "first_frame", "url": image}]

    jo = ctx.obj["json_output"]
    try:
        gen = api.submit_generation(model, params, ctx.obj["api_key"], ctx.obj["workspace_id"])
    except Exception as e:
        error_exit(str(e))

    if not wait:
        emit(gen, json_output=jo, message=f"Queued: {gen.get('id')} [{mode}]")
        return

    gen_id = gen["id"]
    click.echo(f"Queued {gen_id} [{mode}] — polling…", err=True)
    try:
        result = api.poll_generation(
            gen_id,
            interval=8.0,
            timeout=timeout,
            api_key=ctx.obj["api_key"],
            workspace_id=ctx.obj["workspace_id"],
            on_progress=progress_bar if not jo else None,
        )
    except Exception as e:
        error_exit(str(e))

    if jo:
        emit(result, json_output=True)
    else:
        status = result.get("status")
        if status == "succeeded":
            for out in result.get("output", []):
                click.echo(out.get("url", out))
        else:
            err = result.get("error") or {}
            click.echo(f"Failed: {err.get('message', status)}", err=True)
            sys.exit(1)


# ---------------------------------------------------------------------------
# status
# ---------------------------------------------------------------------------


@main.command()
@click.argument("generation_id")
@click.option("--poll", is_flag=True, help="Keep polling until terminal state")
@click.option("--timeout", type=float, default=300.0, show_default=True)
@click.pass_context
def status(ctx, generation_id: str, poll: bool, timeout: float):
    """Get or poll the status of GENERATION_ID."""
    jo = ctx.obj["json_output"]
    try:
        if poll:
            result = api.poll_generation(
                generation_id,
                timeout=timeout,
                api_key=ctx.obj["api_key"],
                workspace_id=ctx.obj["workspace_id"],
                on_progress=progress_bar if not jo else None,
            )
        else:
            result = api.get_generation(
                generation_id, ctx.obj["api_key"], ctx.obj["workspace_id"]
            )
    except Exception as e:
        error_exit(str(e))

    emit(result, json_output=jo)


# ---------------------------------------------------------------------------
# generations list
# ---------------------------------------------------------------------------


@main.command()
@click.option("--page", type=int, default=1, show_default=True)
@click.option("--page-size", type=int, default=20, show_default=True)
@click.pass_context
def generations(ctx, page: int, page_size: int):
    """List past generations."""
    try:
        data = api.list_generations(page, page_size, ctx.obj["api_key"], ctx.obj["workspace_id"])
    except Exception as e:
        error_exit(str(e))

    jo = ctx.obj["json_output"]
    if jo:
        emit(data, json_output=True)
    else:
        items = data.get("generations", [])
        total = data.get("total", len(items))
        click.echo(f"{'ID':<28} {'Status':<12} {'Model':<40} Created")
        click.echo("-" * 100)
        for g in items:
            click.echo(
                f"{g.get('id',''):<28} {g.get('status',''):<12} "
                f"{g.get('model',''):<40} {g.get('created_at','')}"
            )
        click.echo(f"\n{len(items)}/{total} generations shown (page {page})")


# ---------------------------------------------------------------------------
# upload
# ---------------------------------------------------------------------------


@main.command()
@click.argument("file_path", type=click.Path(exists=True))
@click.option("--content-type", default=None, help="Override MIME type")
@click.pass_context
def upload(ctx, file_path: str, content_type: Optional[str]):
    """Upload FILE_PATH as a reference asset and print its public URL."""
    try:
        session = api.upload_file(
            file_path, content_type, ctx.obj["api_key"], ctx.obj["workspace_id"]
        )
    except Exception as e:
        error_exit(str(e))

    jo = ctx.obj["json_output"]
    if jo:
        emit(session, json_output=True)
    else:
        click.echo(session.get("url", ""))


# ---------------------------------------------------------------------------
# usage
# ---------------------------------------------------------------------------


@main.command()
@click.option("--days", type=int, default=30, show_default=True, help="Period in days")
@click.pass_context
def usage(ctx, days: int):
    """Show API usage summary for the past DAYS days."""
    try:
        data = api.get_usage(days, ctx.obj["api_key"], ctx.obj["workspace_id"])
    except Exception as e:
        error_exit(str(e))

    jo = ctx.obj["json_output"]
    if jo:
        emit(data, json_output=True)
    else:
        click.echo(f"Period: {data.get('period_days')} days")
        click.echo(f"Total tasks:     {data.get('total_tasks', 0)}")
        click.echo(f"  Succeeded:     {data.get('total_succeeded', 0)}")
        click.echo(f"  Failed:        {data.get('total_failed', 0)}")
        click.echo(
            f"Total cost:      {data.get('total_cost', 0.0)} {data.get('currency', 'points')}"
        )
        by_model = data.get("by_model", [])
        if by_model:
            click.echo("\nBy model:")
            click.echo(f"  {'Model':<45} {'Tasks':>6} {'Cost':>10}")
            click.echo("  " + "-" * 65)
            for m in by_model:
                click.echo(
                    f"  {m.get('model',''):<45} {m.get('total_tasks',0):>6} "
                    f"{m.get('total_cost',0.0):>10.4f}"
                )
