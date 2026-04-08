# thankyouai

Command-line interface for the [ThankYou AI](https://thankyouai.com) async generation platform — images, audio, and more.

## Installation

```bash
pip install thankyouai
# or install from source:
pip install -e .
```

## Authentication

```bash
export TY_KEY="tk_YOUR_API_KEY"
export TY_WS="YOUR_WORKSPACE_ID"   # optional if key has a default workspace
```

Or pass flags directly: `--api-key` / `--workspace-id`.

## Quick Start

```bash
# List models
thankyouai models
thankyouai models --category image-generation
thankyouai models --category "Text to Video"

# Generate an image (waits for result, prints URL)
thankyouai generate image "A serene mountain lake at golden hour"

# Generate with options
thankyouai generate image "Futuristic cityscape" \
  --model google/nano-banana/pro/text-to-image \
  --aspect-ratio 16:9 \
  --seed 42

# Image editing — pass a reference image
thankyouai upload ./photo.jpg          # prints CDN URL
thankyouai generate image "Make it painterly" \
  --reference https://cdn.example.com/photo.jpg

# Generate a video — text-to-video (default: Wan 2.6)
thankyouai generate video "A sunset over the ocean, cinematic"

# Image-to-video — animate an image
thankyouai generate video "Gentle waves lapping the shore" \
  --model wan/v2.6/image-to-video \
  --image https://cdn.example.com/beach.jpg

# First-last frame interpolation
thankyouai generate video \
  --model kling/v3.0/pro/image-to-video \
  --image https://cdn.example.com/start.jpg \
  --end-image https://cdn.example.com/end.jpg

# Video options
thankyouai generate video "City at night" \
  --model kling/v3.0/standard/text-to-video \
  --aspect-ratio 16:9 \
  --duration 10

# Text-to-speech
thankyouai voices                      # list available voices
thankyouai generate audio "Hello from ThankYou AI." --voice-id <voice_id>

# Advanced TTS
thankyouai generate audio "Testing voice." \
  --voice-id <voice_id> \
  --format wav \
  --temperature 0.7 \
  --latency balanced

# Check generation status
thankyouai status gen_abc123
thankyouai status gen_abc123 --poll    # keep polling until done

# List past generations
thankyouai generations
thankyouai generations --page 2 --page-size 10

# Usage summary
thankyouai usage
thankyouai usage --days 7
```

## JSON Output

Any command supports `--json` for machine-readable output:

```bash
thankyouai --json generate image "A cat" --no-wait
# {"id": "gen_...", "status": "queued", ...}

thankyouai --json status gen_abc123
```

## Commands

| Command | Description |
|---------|-------------|
| `models [--category]` | List available models |
| `model-detail MODEL_ID` | Show field schema for a model |
| `voices` | List TTS voices |
| `generate image PROMPT` | Generate an image |
| `generate video [PROMPT]` | Generate video (text-to-video, image-to-video, first-last-frame) |
| `generate audio TEXT` | Generate speech |
| `status GEN_ID [--poll]` | Get or poll generation status |
| `generations` | List past generations |
| `upload FILE` | Upload a reference file, print URL |
| `usage [--days N]` | Show usage/billing summary |

## Environment Variables

| Variable | Description |
|----------|-------------|
| `TY_KEY` | API key (required) |
| `TY_WS` | Workspace ID (optional if key has a default workspace) |
| `TY_BASE` | API base URL (default: `https://api.thankyouai.com/open/v1`) |

## License

MIT
