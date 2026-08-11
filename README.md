# mcp-voice-clone

<p align="center">
  <a href="https://opensource.org/licenses/MIT"><img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License: MIT"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.10+-blue.svg" alt="Python 3.10+"></a>
  <a href="https://modelcontextprotocol.io/"><img src="https://img.shields.io/badge/MCP-compatible-green.svg" alt="MCP"></a>
  <img src="https://img.shields.io/badge/version-1.0.0-blue.svg" alt="Version 1.0.0">
</p>

<p align="center">
  <strong>Voice cloning and advanced TTS MCP server.</strong><br>
  Clone voices from audio samples, generate speech with cloned voices, and create sound effects.<br>
  Works with Claude Code, Claude Desktop, Cursor, and any MCP-compatible client.
</p>

<p align="center">
  <a href="README_CN.md">中文文档</a>
</p>

## Features

- **Voice cloning** — Clone any voice from a short audio sample (Fish Audio + ElevenLabs)
- **Advanced TTS** — Generate speech with cloned or preset voices
- **Sound effects** — Generate SFX from text descriptions (ElevenLabs)
- **Best Chinese voice cloning** — Fish Audio excels at Chinese voice cloning, very affordable
- **Premium English voices** — ElevenLabs for natural, expressive English speech
- **Provider switching** — Choose the best provider per request via `provider` parameter
- **Safe auto-save** — MP3 output uses microsecond filenames and never overwrites existing files
- **Bounded media** — Clone samples are capped at 25 MiB and provider audio responses at 50 MiB
- **Validated requests** — TTS speed, SFX duration, text lengths, formats, and provider errors are bounded in Schema and runtime

## Supported Providers

| Provider | Capabilities | Best for | Pricing | Env Var |
|---|---|---|---|---|
| **Fish Audio** | Voice Cloning, TTS | Chinese voice cloning | ~$0.01/request | `FISH_AUDIO_API_KEY` |
| **ElevenLabs** | Voice Cloning, TTS, SFX | English TTS, sound effects | Free tier + paid plans | `ELEVENLABS_API_KEY` |

### Provider Selection Guide

```
Need voice cloning?
  ├─ Chinese voice?
  │   └─ fish-audio ✅ (best Chinese cloning, very affordable)
  │
  ├─ English voice?
  │   └─ elevenlabs ✅ (premium quality, natural sounding)
  │
  └─ Sound effects?
      └─ elevenlabs (SFX generation from text)
```

## Quick Start

### 1. Clone & install

```bash
git clone https://github.com/kevinten-ai/mcp-voice-clone.git
cd mcp-voice-clone
uv sync
```

### 2. Use the Codex task profile

The local server is registered disabled by default. Start a new Codex session with
only the voice profile enabled:

```bash
codex-mcp run voice -- --cd /path/to/project
```

The profile applies only to the new Codex session and does not modify the base
Codex configuration. Configure provider keys in the registered local server rather
than placing real keys in repository files or command history.

### 3. Compatibility configuration

Configure the providers you want to use. At least one API key is required.

<details>
<summary><b>Claude Code (CLI) — recommended</b></summary>

```bash
# Fish Audio only (Chinese voice cloning)
claude mcp add -s user mcp-voice-clone \
  --env FISH_AUDIO_API_KEY=your_key \
  -- uv --directory /path/to/mcp-voice-clone run voice-clone

# ElevenLabs only (English TTS + SFX)
claude mcp add -s user mcp-voice-clone \
  --env ELEVENLABS_API_KEY=your_key \
  -- uv --directory /path/to/mcp-voice-clone run voice-clone

# Both providers (full features)
claude mcp add -s user mcp-voice-clone \
  --env FISH_AUDIO_API_KEY=your_fish_key \
  --env ELEVENLABS_API_KEY=your_elevenlabs_key \
  -- uv --directory /path/to/mcp-voice-clone run voice-clone
```

</details>

<details>
<summary><b>Claude Desktop / Cursor (JSON config)</b></summary>

```json
{
  "mcpServers": {
    "mcp-voice-clone": {
      "command": "uv",
      "args": ["--directory", "/path/to/mcp-voice-clone", "run", "voice-clone"],
      "env": {
        "FISH_AUDIO_API_KEY": "your_fish_key",
        "ELEVENLABS_API_KEY": "your_elevenlabs_key"
      }
    }
  }
}
```

</details>

### 4. Use it

Clone a voice and generate speech:

```
"Clone this voice from /path/to/sample.mp3, name it 'MyVoice'"
"Use MyVoice to say 'Hello, this is a test of voice cloning'"
"Generate a sound effect of thunder rumbling"
```

## Tools (5 total)

### Voice Cloning
- **clone_voice** — Clone a voice from an audio sample. Params: `audio_path` (required), `name` (required), `description`, `provider` (fish-audio/elevenlabs). Returns: voice_id for use with `speak`.

### Speech
- **speak** — Generate speech with a cloned or preset voice. Params: `text` (required, at most 10,000 characters), `voice_id` (required), `provider` (fish-audio/elevenlabs), `speed` (0.7-1.2), `output_path` (new `.mp3` only).
- **list_voices** — List available voices for a provider. Params: `provider` (fish-audio/elevenlabs).

### Sound Effects
- **generate_sfx** — Generate sound effects from a text description. Params: `prompt` (required, at most 2,000 characters), `duration` (0.5-30 seconds), `output_path` (new `.mp3` only). Provider: ElevenLabs.

### Utility
- **list_providers** — Show all configured voice cloning, TTS, and SFX providers.

## API Key Registration Guide

<details>
<summary><b>1. Fish Audio — Best Chinese Voice Cloning</b></summary>

| Item | Detail |
|---|---|
| Platform | Fish Audio |
| URL | https://fish.audio |
| Pricing | Very affordable, ~$0.01/request |
| Env Var | `FISH_AUDIO_API_KEY` |

**Steps:**
1. Visit https://fish.audio → Sign Up
2. Go to **API Keys**: https://fish.audio/account/api-keys
3. Click "Create API Key" → copy
4. Create a dedicated key with the narrowest provider permissions available and set `FISH_AUDIO_API_KEY` in your local MCP config

**Voice Cloning Tips:**
- Upload a clear, 10-30 second audio sample for best results
- Mono audio works better than stereo
- Minimize background noise in the sample
- Supports MP3, WAV, FLAC, M4A formats

</details>

<details>
<summary><b>2. ElevenLabs — Premium English TTS + SFX</b></summary>

| Item | Detail |
|---|---|
| Platform | ElevenLabs |
| URL | https://elevenlabs.io |
| Free Tier | 10,000 characters/month free |
| Env Var | `ELEVENLABS_API_KEY` |

**Steps:**
1. Visit https://elevenlabs.io → Sign Up
2. Go to **Profile + API Key**: https://elevenlabs.io/app/settings/api-keys
3. Click "Create API Key" → copy
4. Create a restricted API key that only grants the required voice capabilities and set `ELEVENLABS_API_KEY` in your local MCP config

**Features:**
- Instant voice cloning from a short audio sample (paid plans)
- 29+ languages supported
- Sound effects generation from text descriptions
- Pre-built high-quality voices available on free tier

</details>

## Environment Variables

| Variable | Provider | Required |
|---|---|---|
| `FISH_AUDIO_API_KEY` | Fish Audio (voice cloning + TTS) | At least one |
| `ELEVENLABS_API_KEY` | ElevenLabs (TTS + cloning + SFX) | provider required |
| `AUDIO_OUTPUT_DIR` | Output directory | Optional, default: `./output` |

## Troubleshooting

### Common Errors

| Error | Root Cause | Solution |
|---|---|---|
| `No providers configured` | No API keys set | Set at least one API key |
| `Unknown provider: xxx` | Typo or provider not configured | Check `list_providers` for available options |
| `Audio file not found` | Invalid audio_path | Check the file path exists and is accessible |
| `Output file already exists` | Output would overwrite a file | Choose a new `.mp3` path or remove the old file explicitly |
| `Unsupported audio sample format` | Clone sample extension is not supported | Use MP3, WAV, FLAC, OGG, M4A, AAC, or WebM |
| `Audio sample is too large` | Clone sample exceeds the local 25 MiB safety limit | Trim or compress the sample before cloning |
| `Provider response is too large` | Generated audio exceeds the 50 MiB safety limit | Shorten the text or requested duration |

### Provider-Specific Errors

| Error | Provider | Solution |
|---|---|---|
| `HTTP 401` | Fish Audio | Check `FISH_AUDIO_API_KEY` is valid |
| `HTTP 401` | ElevenLabs | Check `ELEVENLABS_API_KEY` is valid |
| `HTTP 422` | Fish Audio | Audio format not supported or file too large |
| `quota_exceeded` | ElevenLabs | Free tier limit reached, upgrade plan or wait for reset |
| `voice_not_found` | Either | Voice ID is invalid, use `list_voices` to check |

### Tips

- **Fish Audio** is significantly cheaper for Chinese voice cloning than ElevenLabs
- **ElevenLabs** free tier includes 10,000 characters/month for TTS and access to preset voices
- **Voice cloning** quality depends heavily on the audio sample quality — use clean, clear recordings
- **Sound effects** via ElevenLabs accept natural language descriptions, be descriptive for best results
- Custom output paths must use `.mp3` and must not already exist. Output validation happens before a billable provider request.
- Provider audio is streamed with a 50 MiB cap; JSON metadata and error previews also have bounded sizes.

## Project Structure

```
src/voice_clone/
├── __init__.py
├── __main__.py
├── server.py              # MCP server + tool handlers
└── providers/
    ├── __init__.py        # Base classes (BaseTTSProvider, BaseVoiceCloningProvider, BaseSFXProvider) + registry
    ├── fish_audio.py      # Fish Audio — Chinese voice cloning + TTS
    └── elevenlabs.py      # ElevenLabs — English TTS + voice cloning + SFX
```

### Adding a New Provider

1. Create `src/voice_clone/providers/your_provider.py`
2. Implement the relevant base class(es): `BaseTTSProvider`, `BaseVoiceCloningProvider`, or `BaseSFXProvider`
3. Register in `server.py:_init_providers()` with env var check
4. Provider appears automatically in tools and `list_providers`

## Local Development

```bash
git clone https://github.com/kevinten-ai/mcp-voice-clone.git
cd mcp-voice-clone
uv sync

# Run directly
uv run voice-clone

# Debug with MCP Inspector
npx @modelcontextprotocol/inspector uv --directory . run voice-clone
```

## Related Media Workflow

Image generation, image editing, and video generation use AnyCap CLI by default;
the image/video MCP projects are compatibility-only. Enable this MCP through the
`voice` profile only when an agent needs live voice cloning, TTS, voice lookup, or
sound-effect generation during its reasoning loop.

## License

MIT — see [LICENSE](LICENSE) for details.
