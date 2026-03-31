# CLAUDE.md — mcp-voice-clone

## Project Overview

Multi-provider MCP server for voice cloning, advanced TTS, and sound effects. Fish Audio (best Chinese voice cloning) + ElevenLabs (English TTS + SFX) under one unified interface.

## Architecture

- **Entry**: `src/voice_clone/__init__.py` → `server.main()` via asyncio
- **Core**: `src/voice_clone/server.py` — 5 MCP tool handlers, provider registry init, audio save helpers
- **Providers**: `src/voice_clone/providers/` — one file per provider, all implement base classes

## Key Design Decisions

- **Registry pattern**: Providers register at import time via `_init_providers()`, gated by env var presence
- **Multi-interface providers**: FishAudioProvider implements both BaseTTSProvider and BaseVoiceCloningProvider
- **Separate cloning registry**: Voice cloning providers tracked in `_voice_cloning_providers` dict (separate from TTS registry) since they implement a different ABC
- **Raw audio responses**: Both Fish Audio and ElevenLabs return raw audio bytes (not base64), saved directly to disk
- **Output flexibility**: `output_path` param allows exact file path; defaults to auto-generated timestamped filename in `AUDIO_OUTPUT_DIR`

## Provider Patterns

All providers follow these base classes:

1. `BaseTTSProvider` — `speak(text, voice_id, speed)` → `AudioResult`
2. `BaseVoiceCloningProvider` — `clone_voice(audio_path, name, description)` → `VoiceInfo`
3. `BaseSFXProvider` — `generate_sfx(prompt, duration)` → `AudioResult`

Fish Audio implements both TTS + cloning. ElevenLabs splits into 3 classes (TTS, cloning, SFX).

## Common Pitfalls

- **Fish Audio model endpoint**: Voice cloning uses `/model` (not `/v1/voices`), listing also uses `/model`
- **Fish Audio TTS**: Uses `/v1/tts` with `reference_id` field (not `voice_id`)
- **ElevenLabs auth header**: Uses `xi-api-key` header (not `Authorization: Bearer`)
- **ElevenLabs SFX**: Returns audio bytes stream directly, accept header must be `audio/mpeg`
- **File path resolution**: `os.path.expanduser()` is called on audio_path to handle `~` paths
- **Speed parameter**: Fish Audio uses `prosody.speed`, ElevenLabs does not support speed adjustment in the same way

## Development

```bash
uv sync           # install deps
uv run voice-clone  # run server
npx @modelcontextprotocol/inspector uv --directory . run voice-clone  # debug
```
