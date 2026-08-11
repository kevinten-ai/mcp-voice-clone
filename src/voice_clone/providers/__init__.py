from __future__ import annotations
import json
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path


MAX_CLONE_SAMPLE_BYTES = 25 * 1024 * 1024
MAX_AUDIO_RESPONSE_BYTES = 50 * 1024 * 1024
MAX_ERROR_RESPONSE_BYTES = 64 * 1024
MAX_JSON_RESPONSE_BYTES = 5 * 1024 * 1024
AUDIO_SAMPLE_CONTENT_TYPES = {
    ".mp3": "audio/mpeg",
    ".wav": "audio/wav",
    ".flac": "audio/flac",
    ".ogg": "audio/ogg",
    ".m4a": "audio/mp4",
    ".aac": "audio/aac",
    ".webm": "audio/webm",
}


def validate_audio_sample_path(audio_path: str) -> tuple[Path, str]:
    if not isinstance(audio_path, str) or not audio_path.strip():
        raise ValueError("audio_path must be a non-empty string")
    path = Path(os.path.expanduser(audio_path))
    if not path.is_file():
        raise FileNotFoundError(f"Audio file not found: {path}")
    content_type = AUDIO_SAMPLE_CONTENT_TYPES.get(path.suffix.lower())
    if content_type is None:
        supported = ", ".join(sorted(AUDIO_SAMPLE_CONTENT_TYPES))
        raise ValueError(
            f"Unsupported audio sample format. Supported extensions: {supported}"
        )
    size = path.stat().st_size
    if size > MAX_CLONE_SAMPLE_BYTES:
        raise ValueError(
            f"Audio sample is too large ({size} bytes); maximum is {MAX_CLONE_SAMPLE_BYTES} bytes"
        )
    if size == 0:
        raise ValueError("Audio sample is empty")
    return path, content_type


def load_audio_sample(audio_path: str) -> tuple[str, bytes, str]:
    path, content_type = validate_audio_sample_path(audio_path)
    with path.open("rb") as source:
        data = source.read(MAX_CLONE_SAMPLE_BYTES + 1)
    if len(data) > MAX_CLONE_SAMPLE_BYTES:
        raise ValueError(
            f"Audio sample is too large ({len(data)} bytes); maximum is {MAX_CLONE_SAMPLE_BYTES} bytes"
        )
    return path.name, data, content_type


async def read_limited_stream(response, limit: int) -> bytes:
    data = bytearray()
    async for chunk in response.aiter_bytes():
        if len(data) + len(chunk) > limit:
            raise ValueError(
                f"Provider response is too large; maximum is {limit} bytes"
            )
        data.extend(chunk)
    return bytes(data)


async def read_error_text(response) -> str:
    try:
        data = await read_limited_stream(response, MAX_ERROR_RESPONSE_BYTES)
    except ValueError:
        return "provider error response exceeded the safe preview limit"
    return data.decode("utf-8", errors="replace").strip()[:1_000] or "unknown error"


async def read_limited_json(response):
    data = await read_limited_stream(response, MAX_JSON_RESPONSE_BYTES)
    try:
        return json.loads(data)
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        raise ValueError("Provider returned invalid JSON") from e


def validate_audio_content_type(value: str | None) -> None:
    if not value:
        return
    media_type = value.split(";", 1)[0].strip().lower()
    if media_type.startswith("text/") or media_type in {
        "application/json",
        "application/problem+json",
    }:
        raise ValueError(f"Provider returned non-audio content type: {media_type}")


@dataclass
class AudioResult:
    status: str  # "success", "failed"
    audio_data: bytes | None = None
    file_path: str | None = None
    error: str | None = None


@dataclass
class VoiceInfo:
    voice_id: str
    name: str
    description: str | None = None
    provider: str | None = None


class BaseTTSProvider(ABC):
    """Base class for TTS / voice cloning providers."""

    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    @abstractmethod
    def description(self) -> str: ...

    @abstractmethod
    async def speak(
        self,
        text: str,
        voice_id: str,
        speed: float = 1.0,
    ) -> AudioResult: ...

    @abstractmethod
    async def list_voices(self) -> list[VoiceInfo]: ...


class BaseVoiceCloningProvider(ABC):
    """Base class for providers that support voice cloning."""

    @abstractmethod
    async def clone_voice(
        self,
        audio_path: str,
        name: str,
        description: str | None = None,
    ) -> VoiceInfo: ...


class BaseSFXProvider(ABC):
    """Base class for sound effects generation providers."""

    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    async def generate_sfx(
        self,
        prompt: str,
        duration: float | None = None,
    ) -> AudioResult: ...


# Provider registry
_tts_providers: dict[str, BaseTTSProvider] = {}
_sfx_providers: dict[str, BaseSFXProvider] = {}


def register_tts(provider: BaseTTSProvider) -> None:
    _tts_providers[provider.name] = provider


def get_tts(name: str) -> BaseTTSProvider | None:
    return _tts_providers.get(name)


def list_tts() -> dict[str, BaseTTSProvider]:
    return dict(_tts_providers)


def register_sfx(provider: BaseSFXProvider) -> None:
    _sfx_providers[provider.name] = provider


def get_sfx(name: str) -> BaseSFXProvider | None:
    return _sfx_providers.get(name)


def list_sfx() -> dict[str, BaseSFXProvider]:
    return dict(_sfx_providers)
