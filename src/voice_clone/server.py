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
    register_tts,
    list_tts as get_all_tts,
    register_sfx,
    list_sfx as get_all_sfx,
)
from .providers.fish_audio import FishAudioProvider
from .providers.elevenlabs import (
    ElevenLabsTTSProvider,
    ElevenLabsVoiceCloningProvider,
    ElevenLabsSFXProvider,
)

AUDIO_OUTPUT_DIR = os.getenv("AUDIO_OUTPUT_DIR", os.path.join(os.getcwd(), "output"))

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
        _voice_cloning_providers["elevenlabs"] = ElevenLabsVoiceCloningProvider(elevenlabs_key)
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


def _save_audio_bytes(data: bytes, output_dir: str, prefix: str, ext: str = "mp3") -> str:
    """Save raw audio bytes to disk."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = out / f"{prefix}_{timestamp}.{ext}"
    filepath.write_bytes(data)
    return str(filepath)


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
        tools.append(types.Tool(
            name="clone_voice",
            description=f"Clone a voice from an audio sample. The returned voice_id can be used with the speak tool. Available providers: {', '.join(cloning_names)}. Default: {default_cloning}.",
            inputSchema={
                "type": "object",
                "properties": {
                    "audio_path": {
                        "type": "string",
                        "description": "Path to the reference voice audio sample (mp3, wav, flac, m4a, etc.)",
                    },
                    "name": {
                        "type": "string",
                        "description": "Name for the cloned voice",
                    },
                    "description": {
                        "type": "string",
                        "description": "Optional description of the voice",
                    },
                    "provider": {
                        "type": "string",
                        "description": f"Provider to use: {', '.join(cloning_names)}. Default: {default_cloning}",
                        "enum": cloning_names,
                    },
                },
                "required": ["audio_path", "name"],
            },
        ))

    # speak tool
    if tts_names:
        tools.append(types.Tool(
            name="speak",
            description=f"Generate speech with a cloned or preset voice. Available providers: {', '.join(tts_names)}. Default: {default_tts}.",
            inputSchema={
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "The text to convert to speech",
                    },
                    "voice_id": {
                        "type": "string",
                        "description": "Voice ID to use (from clone_voice result or list_voices). Fish Audio: use reference_id from cloned voice. ElevenLabs: use voice_id.",
                    },
                    "provider": {
                        "type": "string",
                        "description": f"TTS provider: {', '.join(tts_names)}. Default: {default_tts}",
                        "enum": tts_names,
                    },
                    "speed": {
                        "type": "number",
                        "description": "Speech speed multiplier (0.5-2.0). Default: 1.0",
                        "default": 1.0,
                    },
                    "output_path": {
                        "type": "string",
                        "description": "Full file path to save the audio. If not provided, saves to output directory with auto-generated name.",
                    },
                },
                "required": ["text", "voice_id"],
            },
        ))

    # list_voices tool
    if tts_names:
        tools.append(types.Tool(
            name="list_voices",
            description=f"List available voices for a provider. Available providers: {', '.join(tts_names)}. Default: {default_tts}.",
            inputSchema={
                "type": "object",
                "properties": {
                    "provider": {
                        "type": "string",
                        "description": f"Provider to list voices from: {', '.join(tts_names)}. Default: {default_tts}",
                        "enum": tts_names,
                    },
                },
                "required": [],
            },
        ))

    # generate_sfx tool
    if sfx_names:
        tools.append(types.Tool(
            name="generate_sfx",
            description=f"Generate sound effects from a text description. Available providers: {', '.join(sfx_names)}.",
            inputSchema={
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "Text description of the sound effect to generate (e.g. 'thunderstorm with heavy rain', 'cat meowing softly')",
                    },
                    "duration": {
                        "type": "number",
                        "description": "Duration in seconds. Optional — provider will choose a default if omitted.",
                    },
                    "output_path": {
                        "type": "string",
                        "description": "Full file path to save the audio. If not provided, saves to output directory with auto-generated name.",
                    },
                },
                "required": ["prompt"],
            },
        ))

    # list_providers tool (always available)
    tools.append(types.Tool(
        name="list_providers",
        description="List all available voice cloning, TTS, and sound effects providers.",
        inputSchema={
            "type": "object",
            "properties": {},
        },
    ))

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
            return [types.TextContent(type="text", text="No providers configured. Set FISH_AUDIO_API_KEY or ELEVENLABS_API_KEY.")]
        return [types.TextContent(type="text", text="\n".join(lines))]

    if name == "clone_voice":
        audio_path = arguments.get("audio_path")
        voice_name = arguments.get("name")
        if not audio_path or not voice_name:
            return [types.TextContent(type="text", text="Missing required parameters: audio_path and name")]

        provider_name = arguments.get("provider") or _default_cloning_name()
        if not provider_name:
            return [types.TextContent(type="text", text="No voice cloning providers configured. Set FISH_AUDIO_API_KEY or ELEVENLABS_API_KEY.")]

        provider = _voice_cloning_providers.get(provider_name)
        if not provider:
            available = ", ".join(_voice_cloning_providers.keys())
            return [types.TextContent(type="text", text=f"Unknown provider: {provider_name}. Available: {available}")]

        description = arguments.get("description")

        try:
            voice_info = await provider.clone_voice(audio_path, voice_name, description=description)
        except FileNotFoundError as e:
            return [types.TextContent(type="text", text=f"Error: {e}")]
        except RuntimeError as e:
            return [types.TextContent(type="text", text=f"Clone failed: {e}")]
        except Exception as e:
            return [types.TextContent(type="text", text=f"Clone failed: {e}")]

        return [types.TextContent(
            type="text",
            text=(
                f"Voice cloned successfully via **{provider_name}**!\n"
                f"Voice ID: `{voice_info.voice_id}`\n"
                f"Name: {voice_info.name}\n"
                f"Use this voice_id with the `speak` tool to generate speech."
            ),
        )]

    if name == "speak":
        text = arguments.get("text")
        voice_id = arguments.get("voice_id")
        if not text or not voice_id:
            return [types.TextContent(type="text", text="Missing required parameters: text and voice_id")]

        tts_providers = get_all_tts()
        if not tts_providers:
            return [types.TextContent(type="text", text="No TTS providers configured. Set FISH_AUDIO_API_KEY or ELEVENLABS_API_KEY.")]

        provider_name = arguments.get("provider") or _default_tts_name()
        provider = tts_providers.get(provider_name) if provider_name else None
        if not provider:
            available = ", ".join(tts_providers.keys())
            return [types.TextContent(type="text", text=f"Unknown TTS provider: {provider_name}. Available: {available}")]

        speed = arguments.get("speed", 1.0)

        result = await provider.speak(text, voice_id=voice_id, speed=speed)

        if result.status == "failed":
            return [types.TextContent(type="text", text=f"TTS failed: {result.error}")]

        # Save audio
        output_path = arguments.get("output_path")
        if output_path:
            out = Path(output_path)
            out.parent.mkdir(parents=True, exist_ok=True)
            if result.audio_data:
                out.write_bytes(result.audio_data)
                filepath = str(out)
            else:
                return [types.TextContent(type="text", text="No audio data returned")]
        else:
            output_dir = AUDIO_OUTPUT_DIR
            if result.audio_data:
                filepath = _save_audio_bytes(result.audio_data, output_dir, f"speak_{provider_name}")
            else:
                return [types.TextContent(type="text", text="No audio data returned")]

        return [types.TextContent(type="text", text=f"Speech generated via **{provider_name}**.\nSaved to: {filepath}")]

    if name == "list_voices":
        tts_providers = get_all_tts()
        if not tts_providers:
            return [types.TextContent(type="text", text="No TTS providers configured. Set FISH_AUDIO_API_KEY or ELEVENLABS_API_KEY.")]

        provider_name = arguments.get("provider") or _default_tts_name()
        provider = tts_providers.get(provider_name) if provider_name else None
        if not provider:
            available = ", ".join(tts_providers.keys())
            return [types.TextContent(type="text", text=f"Unknown provider: {provider_name}. Available: {available}")]

        try:
            voices = await provider.list_voices()
        except Exception as e:
            return [types.TextContent(type="text", text=f"Failed to list voices: {e}")]

        if not voices:
            return [types.TextContent(type="text", text=f"No voices found for provider **{provider_name}**.")]

        lines = [f"**Voices for {provider_name}** ({len(voices)} total):"]
        for v in voices:
            desc = f" - {v.description}" if v.description else ""
            lines.append(f"  `{v.voice_id}` **{v.name}**{desc}")

        return [types.TextContent(type="text", text="\n".join(lines))]

    if name == "generate_sfx":
        prompt = arguments.get("prompt")
        if not prompt:
            return [types.TextContent(type="text", text="Missing required parameter: prompt")]

        sfx_providers = get_all_sfx()
        if not sfx_providers:
            return [types.TextContent(type="text", text="No SFX providers configured. Set ELEVENLABS_API_KEY.")]

        # Only ElevenLabs supports SFX for now
        provider_name = list(sfx_providers.keys())[0]
        provider = sfx_providers[provider_name]

        duration = arguments.get("duration")

        result = await provider.generate_sfx(prompt, duration=duration)

        if result.status == "failed":
            return [types.TextContent(type="text", text=f"SFX generation failed: {result.error}")]

        # Save audio
        output_path = arguments.get("output_path")
        if output_path:
            out = Path(output_path)
            out.parent.mkdir(parents=True, exist_ok=True)
            if result.audio_data:
                out.write_bytes(result.audio_data)
                filepath = str(out)
            else:
                return [types.TextContent(type="text", text="No audio data returned")]
        else:
            output_dir = AUDIO_OUTPUT_DIR
            if result.audio_data:
                filepath = _save_audio_bytes(result.audio_data, output_dir, "sfx")
            else:
                return [types.TextContent(type="text", text="No audio data returned")]

        return [types.TextContent(type="text", text=f"Sound effect generated.\nSaved to: {filepath}")]

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
