from __future__ import annotations
import asyncio
import os
from datetime import datetime
from pathlib import Path

from mcp.server.models import InitializationOptions
import mcp.types as types
from mcp.server import NotificationOptions, Server
import mcp.server.stdio

from .providers import (
    BaseVoiceCloningProvider,
    MAX_AUDIO_RESPONSE_BYTES,
    register_tts,
    list_tts as get_all_tts,
    register_sfx,
    list_sfx as get_all_sfx,
    validate_audio_sample_path,
)
from .providers.fish_audio import FishAudioProvider
from .providers.elevenlabs import (
    ElevenLabsTTSProvider,
    ElevenLabsVoiceCloningProvider,
    ElevenLabsSFXProvider,
)

AUDIO_OUTPUT_DIR = os.getenv("AUDIO_OUTPUT_DIR", os.path.join(os.getcwd(), "output"))
MAX_AUDIO_OUTPUT_BYTES = MAX_AUDIO_RESPONSE_BYTES
MAX_PATH_CHARS = 4_096
MAX_TTS_TEXT_CHARS = 10_000
MAX_SFX_PROMPT_CHARS = 2_000
MAX_VOICE_ID_CHARS = 256
MAX_VOICE_NAME_CHARS = 100
MAX_DESCRIPTION_CHARS = 1_000
MAX_PROVIDER_NAME_CHARS = 64
MIN_SPEECH_SPEED = 0.7
MAX_SPEECH_SPEED = 1.2
MIN_SFX_DURATION = 0.5
MAX_SFX_DURATION = 30.0
MAX_LISTED_VOICES = 100
MAX_TOOL_OUTPUT_CHARS = 20_000

server = Server("mcp-voice-clone")

# Voice cloning providers (separate from TTS registry since they implement a different interface)
_voice_cloning_providers: dict[str, BaseVoiceCloningProvider] = {}


def _init_providers() -> None:
    """Register providers based on available environment variables."""
    fish_key = os.getenv("FISH_AUDIO_API_KEY", "")
    if fish_key:
        fish = FishAudioProvider(fish_key)
        register_tts(fish)  # FishAudioProvider is both TTS and voice cloning
        _voice_cloning_providers["fish-audio"] = fish

    elevenlabs_key = os.getenv("ELEVENLABS_API_KEY", "")
    if elevenlabs_key:
        register_tts(ElevenLabsTTSProvider(elevenlabs_key))
        _voice_cloning_providers["elevenlabs"] = ElevenLabsVoiceCloningProvider(
            elevenlabs_key
        )
        register_sfx(ElevenLabsSFXProvider(elevenlabs_key))


_init_providers()


def _default_tts_name() -> str | None:
    """Return the default TTS provider name (prefer fish-audio for Chinese)."""
    providers = get_all_tts()
    for name in ("fish-audio", "elevenlabs"):
        if name in providers:
            return name
    return None


def _default_cloning_name() -> str | None:
    """Return the default voice cloning provider name."""
    for name in ("fish-audio", "elevenlabs"):
        if name in _voice_cloning_providers:
            return name
    return None


def _validate_string(value: object, field: str, maximum: int) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a string")
    if not value.strip():
        raise ValueError(f"{field} must not be empty")
    if len(value) > maximum:
        raise ValueError(f"{field} must be at most {maximum} characters")
    return value


def _validate_number(
    value: object,
    field: str,
    minimum: float,
    maximum: float,
) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} must be a number")
    number = float(value)
    if not minimum <= number <= maximum:
        raise ValueError(f"{field} must be between {minimum} and {maximum}")
    return number


def _audio_output_path(
    output_dir: str,
    prefix: str,
    output_path: str | None = None,
) -> Path:
    if output_path is not None:
        filepath = Path(_validate_string(output_path, "output_path", MAX_PATH_CHARS))
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filepath = Path(output_dir) / f"{prefix}_{timestamp}.mp3"
    if filepath.suffix.lower() != ".mp3":
        raise ValueError("output_path must use the .mp3 extension")
    if filepath.exists():
        raise FileExistsError(f"Output file already exists: {filepath}")
    return filepath


def _save_audio_bytes(
    data: bytes,
    output_dir: str,
    prefix: str,
    ext: str = "mp3",
    output_path: str | None = None,
) -> str:
    """Save raw audio bytes to disk."""
    if ext.lower() != "mp3":
        raise ValueError("Only MP3 output is supported")
    if not isinstance(data, bytes) or not data:
        raise ValueError("Provider returned no audio data")
    if len(data) > MAX_AUDIO_OUTPUT_BYTES:
        raise ValueError(
            f"Provider audio is too large ({len(data)} bytes); maximum is {MAX_AUDIO_OUTPUT_BYTES} bytes"
        )
    filepath = _audio_output_path(output_dir, prefix, output_path)
    filepath.parent.mkdir(parents=True, exist_ok=True)
    created = False
    try:
        with filepath.open("xb") as handle:
            created = True
            handle.write(data)
    except Exception:
        if created:
            filepath.unlink(missing_ok=True)
        raise
    return str(filepath)


def _bounded_error(value: object) -> str:
    return str(value or "unknown error")[:1_000]


@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    tts_providers = get_all_tts()
    tts_names = list(tts_providers.keys())
    default_tts = _default_tts_name()

    cloning_names = list(_voice_cloning_providers.keys())
    default_cloning = _default_cloning_name()

    sfx_providers = get_all_sfx()
    sfx_names = list(sfx_providers.keys())

    tools: list[types.Tool] = []

    # clone_voice tool
    if cloning_names:
        tools.append(
            types.Tool(
                name="clone_voice",
                description=f"Clone a voice from an audio sample. The returned voice_id can be used with the speak tool. Available providers: {', '.join(cloning_names)}. Default: {default_cloning}.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "audio_path": {
                            "type": "string",
                            "minLength": 1,
                            "maxLength": MAX_PATH_CHARS,
                            "description": "Path to the reference voice audio sample (mp3, wav, flac, m4a, etc.)",
                        },
                        "name": {
                            "type": "string",
                            "minLength": 1,
                            "maxLength": MAX_VOICE_NAME_CHARS,
                            "description": "Name for the cloned voice",
                        },
                        "description": {
                            "type": "string",
                            "minLength": 1,
                            "maxLength": MAX_DESCRIPTION_CHARS,
                            "description": "Optional description of the voice",
                        },
                        "provider": {
                            "type": "string",
                            "minLength": 1,
                            "maxLength": MAX_PROVIDER_NAME_CHARS,
                            "description": f"Provider to use: {', '.join(cloning_names)}. Default: {default_cloning}",
                            "enum": cloning_names,
                        },
                    },
                    "required": ["audio_path", "name"],
                },
            )
        )

    # speak tool
    if tts_names:
        tools.append(
            types.Tool(
                name="speak",
                description=f"Generate speech with a cloned or preset voice. Available providers: {', '.join(tts_names)}. Default: {default_tts}.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "text": {
                            "type": "string",
                            "minLength": 1,
                            "maxLength": MAX_TTS_TEXT_CHARS,
                            "description": "The text to convert to speech",
                        },
                        "voice_id": {
                            "type": "string",
                            "minLength": 1,
                            "maxLength": MAX_VOICE_ID_CHARS,
                            "description": "Voice ID to use (from clone_voice result or list_voices). Fish Audio: use reference_id from cloned voice. ElevenLabs: use voice_id.",
                        },
                        "provider": {
                            "type": "string",
                            "minLength": 1,
                            "maxLength": MAX_PROVIDER_NAME_CHARS,
                            "description": f"TTS provider: {', '.join(tts_names)}. Default: {default_tts}",
                            "enum": tts_names,
                        },
                        "speed": {
                            "type": "number",
                            "description": "Speech speed multiplier (0.7-1.2). Default: 1.0",
                            "default": 1.0,
                            "minimum": MIN_SPEECH_SPEED,
                            "maximum": MAX_SPEECH_SPEED,
                        },
                        "output_path": {
                            "type": "string",
                            "minLength": 1,
                            "maxLength": MAX_PATH_CHARS,
                            "pattern": r"\.[mM][pP]3$",
                            "description": "Full file path to save the audio. If not provided, saves to output directory with auto-generated name.",
                        },
                    },
                    "required": ["text", "voice_id"],
                },
            )
        )

    # list_voices tool
    if tts_names:
        tools.append(
            types.Tool(
                name="list_voices",
                description=f"List available voices for a provider. Available providers: {', '.join(tts_names)}. Default: {default_tts}.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "provider": {
                            "type": "string",
                            "minLength": 1,
                            "maxLength": MAX_PROVIDER_NAME_CHARS,
                            "description": f"Provider to list voices from: {', '.join(tts_names)}. Default: {default_tts}",
                            "enum": tts_names,
                        },
                    },
                    "required": [],
                },
            )
        )

    # generate_sfx tool
    if sfx_names:
        tools.append(
            types.Tool(
                name="generate_sfx",
                description=f"Generate sound effects from a text description. Available providers: {', '.join(sfx_names)}.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "prompt": {
                            "type": "string",
                            "minLength": 1,
                            "maxLength": MAX_SFX_PROMPT_CHARS,
                            "description": "Text description of the sound effect to generate (e.g. 'thunderstorm with heavy rain', 'cat meowing softly')",
                        },
                        "duration": {
                            "type": "number",
                            "description": "Duration in seconds. Optional — provider will choose a default if omitted.",
                            "minimum": MIN_SFX_DURATION,
                            "maximum": MAX_SFX_DURATION,
                        },
                        "output_path": {
                            "type": "string",
                            "minLength": 1,
                            "maxLength": MAX_PATH_CHARS,
                            "pattern": r"\.[mM][pP]3$",
                            "description": "Full file path to save the audio. If not provided, saves to output directory with auto-generated name.",
                        },
                    },
                    "required": ["prompt"],
                },
            )
        )

    # list_providers tool (always available)
    tools.append(
        types.Tool(
            name="list_providers",
            description="List all available voice cloning, TTS, and sound effects providers.",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        )
    )

    return tools


@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent]:
    if not arguments:
        arguments = {}

    if name == "list_providers":
        lines = []
        tts = get_all_tts()
        if tts:
            lines.append("**TTS Providers:**")
            for p in tts.values():
                lines.append(f"  **{p.name}** - {p.description}")
        cloning = _voice_cloning_providers
        if cloning:
            lines.append("\n**Voice Cloning Providers:**")
            for pname, p in cloning.items():
                lines.append(f"  **{pname}** - Voice cloning support")
        sfx = get_all_sfx()
        if sfx:
            lines.append("\n**Sound Effects Providers:**")
            for p in sfx.values():
                lines.append(f"  **{p.name}** - Sound effects generation")
        if not lines:
            return [
                types.TextContent(
                    type="text",
                    text="No providers configured. Set FISH_AUDIO_API_KEY or ELEVENLABS_API_KEY.",
                )
            ]
        return [types.TextContent(type="text", text="\n".join(lines))]

    if name == "clone_voice":
        audio_path = arguments.get("audio_path")
        voice_name = arguments.get("name")
        if not audio_path or not voice_name:
            return [
                types.TextContent(
                    type="text", text="Missing required parameters: audio_path and name"
                )
            ]

        try:
            audio_path = _validate_string(audio_path, "audio_path", MAX_PATH_CHARS)
            validate_audio_sample_path(audio_path)
            voice_name = _validate_string(voice_name, "name", MAX_VOICE_NAME_CHARS)
            description = arguments.get("description")
            if description is not None:
                description = _validate_string(
                    description, "description", MAX_DESCRIPTION_CHARS
                )
        except (ValueError, FileNotFoundError, OSError) as e:
            return [types.TextContent(type="text", text=str(e))]

        requested_provider = arguments.get("provider")
        if requested_provider is not None:
            try:
                requested_provider = _validate_string(
                    requested_provider, "provider", MAX_PROVIDER_NAME_CHARS
                )
            except ValueError as e:
                return [types.TextContent(type="text", text=str(e))]
        provider_name = requested_provider or _default_cloning_name()
        if not provider_name:
            return [
                types.TextContent(
                    type="text",
                    text="No voice cloning providers configured. Set FISH_AUDIO_API_KEY or ELEVENLABS_API_KEY.",
                )
            ]

        provider = _voice_cloning_providers.get(provider_name)
        if not provider:
            available = ", ".join(_voice_cloning_providers.keys())
            return [
                types.TextContent(
                    type="text",
                    text=f"Unknown provider: {provider_name}. Available: {available}",
                )
            ]

        try:
            voice_info = await provider.clone_voice(
                audio_path, voice_name, description=description
            )
        except FileNotFoundError as e:
            return [types.TextContent(type="text", text=f"Error: {e}")]
        except RuntimeError as e:
            return [
                types.TextContent(
                    type="text", text=f"Clone failed: {_bounded_error(e)}"
                )
            ]
        except Exception as e:
            return [
                types.TextContent(
                    type="text", text=f"Clone failed: {_bounded_error(e)}"
                )
            ]

        return [
            types.TextContent(
                type="text",
                text=(
                    f"Voice cloned successfully via **{provider_name}**!\n"
                    f"Voice ID: `{str(voice_info.voice_id)[:MAX_VOICE_ID_CHARS]}`\n"
                    f"Name: {str(voice_info.name)[:MAX_VOICE_NAME_CHARS]}\n"
                    f"Use this voice_id with the `speak` tool to generate speech."
                ),
            )
        ]

    if name == "speak":
        text = arguments.get("text")
        voice_id = arguments.get("voice_id")
        if not text or not voice_id:
            return [
                types.TextContent(
                    type="text", text="Missing required parameters: text and voice_id"
                )
            ]

        tts_providers = get_all_tts()
        if not tts_providers:
            return [
                types.TextContent(
                    type="text",
                    text="No TTS providers configured. Set FISH_AUDIO_API_KEY or ELEVENLABS_API_KEY.",
                )
            ]

        requested_provider = arguments.get("provider")
        if requested_provider is not None:
            try:
                requested_provider = _validate_string(
                    requested_provider, "provider", MAX_PROVIDER_NAME_CHARS
                )
            except ValueError as e:
                return [types.TextContent(type="text", text=str(e))]
        provider_name = requested_provider or _default_tts_name()
        provider = tts_providers.get(provider_name) if provider_name else None
        if not provider:
            available = ", ".join(tts_providers.keys())
            return [
                types.TextContent(
                    type="text",
                    text=f"Unknown TTS provider: {provider_name}. Available: {available}",
                )
            ]

        try:
            text = _validate_string(text, "text", MAX_TTS_TEXT_CHARS)
            voice_id = _validate_string(voice_id, "voice_id", MAX_VOICE_ID_CHARS)
            speed = _validate_number(
                arguments.get("speed", 1.0),
                "speed",
                MIN_SPEECH_SPEED,
                MAX_SPEECH_SPEED,
            )
            output_target = _audio_output_path(
                AUDIO_OUTPUT_DIR,
                f"speak_{provider_name}",
                arguments.get("output_path"),
            )
        except (ValueError, FileExistsError) as e:
            return [types.TextContent(type="text", text=str(e))]

        try:
            result = await provider.speak(text, voice_id=voice_id, speed=speed)
        except Exception as e:
            return [
                types.TextContent(type="text", text=f"TTS failed: {_bounded_error(e)}")
            ]

        if result.status == "failed":
            return [
                types.TextContent(
                    type="text", text=f"TTS failed: {_bounded_error(result.error)}"
                )
            ]

        try:
            filepath = _save_audio_bytes(
                result.audio_data,
                AUDIO_OUTPUT_DIR,
                f"speak_{provider_name}",
                output_path=str(output_target),
            )
        except (ValueError, FileExistsError, OSError) as e:
            return [types.TextContent(type="text", text=str(e))]

        return [
            types.TextContent(
                type="text",
                text=f"Speech generated via **{provider_name}**.\nSaved to: {filepath}",
            )
        ]

    if name == "list_voices":
        tts_providers = get_all_tts()
        if not tts_providers:
            return [
                types.TextContent(
                    type="text",
                    text="No TTS providers configured. Set FISH_AUDIO_API_KEY or ELEVENLABS_API_KEY.",
                )
            ]

        requested_provider = arguments.get("provider")
        if requested_provider is not None:
            try:
                requested_provider = _validate_string(
                    requested_provider, "provider", MAX_PROVIDER_NAME_CHARS
                )
            except ValueError as e:
                return [types.TextContent(type="text", text=str(e))]
        provider_name = requested_provider or _default_tts_name()
        provider = tts_providers.get(provider_name) if provider_name else None
        if not provider:
            available = ", ".join(tts_providers.keys())
            return [
                types.TextContent(
                    type="text",
                    text=f"Unknown provider: {provider_name}. Available: {available}",
                )
            ]

        try:
            voices = await provider.list_voices()
        except Exception as e:
            return [
                types.TextContent(
                    type="text", text=f"Failed to list voices: {_bounded_error(e)}"
                )
            ]

        if not voices:
            return [
                types.TextContent(
                    type="text",
                    text=f"No voices found for provider **{provider_name}**.",
                )
            ]

        lines = [f"**Voices for {provider_name}** ({len(voices)} total):"]
        for v in voices[:MAX_LISTED_VOICES]:
            desc = f" - {str(v.description)[:300]}" if v.description else ""
            lines.append(
                f"  `{str(v.voice_id)[:MAX_VOICE_ID_CHARS]}` "
                f"**{str(v.name)[:MAX_VOICE_NAME_CHARS]}**{desc}"
            )
        if len(voices) > MAX_LISTED_VOICES:
            lines.append(f"... ({len(voices) - MAX_LISTED_VOICES} more voices omitted)")

        return [
            types.TextContent(
                type="text", text="\n".join(lines)[:MAX_TOOL_OUTPUT_CHARS]
            )
        ]

    if name == "generate_sfx":
        prompt = arguments.get("prompt")
        if not prompt:
            return [
                types.TextContent(
                    type="text", text="Missing required parameter: prompt"
                )
            ]

        sfx_providers = get_all_sfx()
        if not sfx_providers:
            return [
                types.TextContent(
                    type="text",
                    text="No SFX providers configured. Set ELEVENLABS_API_KEY.",
                )
            ]

        # Only ElevenLabs supports SFX for now
        provider_name = list(sfx_providers.keys())[0]
        provider = sfx_providers[provider_name]

        try:
            prompt = _validate_string(prompt, "prompt", MAX_SFX_PROMPT_CHARS)
            duration = arguments.get("duration")
            if duration is not None:
                duration = _validate_number(
                    duration,
                    "duration",
                    MIN_SFX_DURATION,
                    MAX_SFX_DURATION,
                )
            output_target = _audio_output_path(
                AUDIO_OUTPUT_DIR,
                "sfx",
                arguments.get("output_path"),
            )
        except (ValueError, FileExistsError) as e:
            return [types.TextContent(type="text", text=str(e))]

        try:
            result = await provider.generate_sfx(prompt, duration=duration)
        except Exception as e:
            return [
                types.TextContent(
                    type="text", text=f"SFX generation failed: {_bounded_error(e)}"
                )
            ]

        if result.status == "failed":
            return [
                types.TextContent(
                    type="text",
                    text=f"SFX generation failed: {_bounded_error(result.error)}",
                )
            ]

        try:
            filepath = _save_audio_bytes(
                result.audio_data,
                AUDIO_OUTPUT_DIR,
                "sfx",
                output_path=str(output_target),
            )
        except (ValueError, FileExistsError, OSError) as e:
            return [types.TextContent(type="text", text=str(e))]

        return [
            types.TextContent(
                type="text", text=f"Sound effect generated.\nSaved to: {filepath}"
            )
        ]

    return [types.TextContent(type="text", text=f"Unknown tool: {name}")]


async def main():
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="mcp-voice-clone",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


if __name__ == "__main__":
    asyncio.run(main())
