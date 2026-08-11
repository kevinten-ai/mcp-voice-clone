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
- **Bounded streaming audio**: Provider MP3 responses are streamed with a 50 MiB cap; obvious JSON/text responses are rejected
- **Safe output**: `output_path` must be a new `.mp3`; defaults use microsecond timestamps in `AUDIO_OUTPUT_DIR`
- **Bounded cloning input**: Samples use extension-specific MIME types and are limited to 25 MiB
- **Schema/runtime parity**: Text, identifier, speed, duration, path, metadata, and output limits are enforced at both boundaries

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
- **Speed parameter**: The unified 0.7–1.2 range is sent as Fish Audio `prosody.speed` and ElevenLabs `voice_settings.speed`
- **Codex boundary**: Enable with `codex-mcp run voice`; image/video generation remains on AnyCap CLI

## Development

```bash
uv sync           # install deps
uv run voice-clone  # run server
npx @modelcontextprotocol/inspector uv --directory . run voice-clone  # debug
```
