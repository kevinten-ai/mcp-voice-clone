from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass


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
