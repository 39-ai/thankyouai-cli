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
| `models` | List available models |
| `model-detail MODEL_ID` | Show field schema for a model |
| `voices` | List TTS voices |
| `generate image PROMPT` | Generate an image |
| `generate audio TEXT` | Generate speech |
| `status GEN_ID` | Get generation status |
| `generations` | List past generations |
| `upload FILE` | Upload a reference file, print URL |
| `usage` | Show usage/billing summary |

## Environment Variables

| Variable | Description |
|----------|-------------|
| `TY_KEY` | API key (required) |
| `TY_WS` | Workspace ID (optional if key has a default workspace) |
| `TY_BASE` | API base URL (default: `https://api.thankyouai.com/open/v1`) |

## License

MIT
